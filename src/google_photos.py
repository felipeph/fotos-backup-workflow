import json
import os
import mimetypes
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime
import requests
from src.config import GooglePhotosConfig
from src.storage import compute_sha256

SCOPES = [
    "https://www.googleapis.com/auth/photoslibrary.appendonly",
    "https://www.googleapis.com/auth/photoslibrary.sharing",
]

@dataclass
class UploadResult:
    file_path: Path
    status: str  # "uploaded", "already_uploaded", "error", "skipped"
    upload_token: str = ""
    error_message: str = ""

class GooglePhotosManager:
    def __init__(self, config: GooglePhotosConfig, base_dir: Path):
        self.config = config
        self.base_dir = base_dir
        self.manifest_path = base_dir / ".uploaded_manifest.json"
        self._manifest: dict[str, dict] = self._load_manifest()
        self._credentials = None

    def _load_manifest(self) -> dict:
        if self.manifest_path.exists():
            try:
                with open(self.manifest_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save_manifest(self):
        try:
            with open(self.manifest_path, "w", encoding="utf-8") as f:
                json.dump(self._manifest, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[WARN] Não foi possível salvar manifesto de upload: {e}")

    def authenticate(self) -> bool:
        """Authenticates with Google OAuth2."""
        cred_file = Path(self.config.credentials_file)
        token_file = Path(self.config.token_file)

        if not cred_file.exists() and not token_file.exists():
            print("\n[INFO] 'credentials.json' do Google não encontrado.")
            print("Para habilitar upload automático via API do Google Fotos:")
            print("1. Acesse https://console.cloud.google.com/")
            print("2. Crie um projeto e ative a 'Photos Library API'")
            print("3. Em 'Credenciais', crie um 'ID do cliente OAuth' (Desktop)")
            print("4. Baixe o arquivo JSON e salve como 'credentials.json' nesta pasta.\n")
            return False

        try:
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from google.auth.transport.requests import Request

            creds = None
            if token_file.exists():
                creds = Credentials.from_authorized_user_file(str(token_file), SCOPES)

            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    if not cred_file.exists():
                        print(f"[ERRO] {cred_file} não existe para renovar login.")
                        return False
                    flow = InstalledAppFlow.from_client_secrets_file(str(cred_file), SCOPES)
                    creds = flow.run_local_server(port=0)

                # Save token for next runs
                with open(token_file, "w", encoding="utf-8") as f:
                    f.write(creds.to_json())

            self._credentials = creds
            return True
        except ImportError:
            print("[ERRO] Bibliotecas do Google não instaladas. Rode: pip install -r requirements.txt")
            return False
        except Exception as e:
            print(f"[ERRO] Falha na autenticação do Google Fotos: {e}")
            return False

    def upload_file(self, file_path: Path) -> UploadResult:
        rel_key = str(file_path.relative_to(self.base_dir) if file_path.is_relative_to(self.base_dir) else file_path)
        sha = compute_sha256(file_path)

        # Check if already uploaded
        if rel_key in self._manifest and self._manifest[rel_key].get("sha256") == sha:
            return UploadResult(file_path=file_path, status="already_uploaded")

        if not self._credentials:
            return UploadResult(file_path=file_path, status="skipped", error_message="Não autenticado")

        # Step 1: Upload bytes
        upload_url = "https://photoslibrary.googleapis.com/v1/uploads"
        headers = {
            "Authorization": f"Bearer {self._credentials.token}",
            "Content-type": "application/octet-stream",
            "X-Goog-Upload-Content-Type": mimetypes.guess_type(file_path)[0] or "application/octet-stream",
            "X-Goog-Upload-Protocol": "raw",
        }

        try:
            with open(file_path, "rb") as f:
                resp = requests.post(upload_url, data=f, headers=headers, timeout=60)
            
            if resp.status_code != 200:
                return UploadResult(file_path=file_path, status="error", error_message=f"HTTP {resp.status_code}: {resp.text}")

            upload_token = resp.text.strip()

            # Step 2: Create media item
            create_url = "https://photoslibrary.googleapis.com/v1/mediaItems:batchCreate"
            create_headers = {
                "Authorization": f"Bearer {self._credentials.token}",
                "Content-type": "application/json",
            }
            create_body = {
                "newMediaItems": [
                    {
                        "description": file_path.name,
                        "simpleMediaItem": {
                            "uploadToken": upload_token,
                            "fileName": file_path.name,
                        }
                    }
                ]
            }

            c_resp = requests.post(create_url, json=create_body, headers=create_headers, timeout=30)
            if c_resp.status_code == 200:
                data = c_resp.json()
                res_status = data.get("newMediaItemResults", [{}])[0].get("status", {}).get("message", "")
                if res_status in ("Success", ""):
                    # Update manifest
                    self._manifest[rel_key] = {
                        "sha256": sha,
                        "uploaded_at": datetime.now().isoformat(),
                        "file_name": file_path.name,
                    }
                    self._save_manifest()
                    return UploadResult(file_path=file_path, status="uploaded", upload_token=upload_token)
                else:
                    return UploadResult(file_path=file_path, status="error", error_message=res_status)
            else:
                return UploadResult(file_path=file_path, status="error", error_message=f"HTTP {c_resp.status_code}: {c_resp.text}")

        except Exception as e:
            return UploadResult(file_path=file_path, status="error", error_message=str(e))

    def upload_pending_in_biblioteca(self, biblioteca_dir: Path) -> list[UploadResult]:
        """Scans Biblioteca directory for non-uploaded JPG/JPEG files and uploads them."""
        results = []
        if not biblioteca_dir.exists():
            print(f"[AVISO] Pasta da biblioteca não existe: {biblioteca_dir}")
            return results

        # Find all JPGs in avulsas and rajadas (ignoring raw and videos)
        jpgs = []
        for p in biblioteca_dir.rglob("*"):
            if p.is_file() and p.suffix.lower() in (".jpg", ".jpeg"):
                # Ensure it's not inside a 'videos' folder
                if "videos" not in [part.lower() for part in p.parts]:
                    jpgs.append(p)

        print(f"\n[GOOGLE FOTOS] Analisando {len(jpgs)} fotos na biblioteca...")
        if not self.authenticate():
            return [UploadResult(file_path=p, status="skipped", error_message="Autenticação pendente") for p in jpgs]

        for idx, p in enumerate(jpgs, start=1):
            sys_stdout_status = f"[{idx}/{len(jpgs)}] Enviando {p.name}..."
            print(sys_stdout_status, end="\r", flush=True)
            res = self.upload_file(p)
            results.append(res)
            if res.status == "uploaded":
                print(f"[{idx}/{len(jpgs)}] ✅ {p.name} enviado!")
            elif res.status == "already_uploaded":
                pass
            else:
                print(f"[{idx}/{len(jpgs)}] ⚠️ {p.name}: {res.error_message}")

        return results
