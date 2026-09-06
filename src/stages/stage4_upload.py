import sys
import os
import tempfile
from pathlib import Path
from datetime import datetime
from PIL import Image

from src.project import Project
from src.config import PipelineConfig
from src.google_photos import GooglePhotosManager

def optimize_for_storage_saver(input_path: Path, output_path: Path, max_megapixels: float = 16.0, quality: int = 85):
    """
    Otimiza a imagem para a especificação exata de 'Economia de Armazenamento' do Google Fotos:
    - Redimensiona fotos maiores que 16MP proporcionalmente.
    - Aplica compressão JPEG de alta qualidade (85) preservando EXIF.
    """
    with Image.open(input_path) as img:
        exif = img.info.get("exif")
        w, h = img.size
        mp = (w * h) / 1_000_000.0

        if mp > max_megapixels:
            scale = (max_megapixels / mp) ** 0.5
            new_w = int(w * scale)
            new_h = int(h * scale)
            img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

        # Convert to RGB if needed (e.g. RGBA)
        if img.mode != "RGB":
            img = img.convert("RGB")

        save_kwargs = {"format": "JPEG", "quality": quality, "optimize": True}
        if exif:
            save_kwargs["exif"] = exif

        img.save(output_path, **save_kwargs)

def run_stage4(project: Project, config: PipelineConfig) -> bool:
    """
    Etapa 4: Upload das fotos normais (avulsas e rajadas, excluindo astro e timelapses)
    para o Google Fotos na configuração de economia de armazenamento.
    """
    if project.current_stage < 3 or not project.items:
        print("[ERRO] Arquivos ainda não foram organizados. Execute a Etapa 3 primeiro.")
        return False

    upload_candidates = [
        it for it in project.items
        if it.category in ("rajada", "avulsa") and not it.uploaded_at
    ]

    if not upload_candidates:
        print("\nℹ️  [ETAPA 4] Nenhuma foto normal pendente de upload no projeto.")
        project.current_stage = max(project.current_stage, 4)
        project.save()
        return True

    print(f"\n☁️  [ETAPA 4] Iniciando upload de {len(upload_candidates)} fotos para o Google Fotos (Economia de Armazenamento)...")

    gp_mgr = GooglePhotosManager(config.google_photos, config.biblioteca_path)
    if not gp_mgr.authenticate():
        print("⚠️  [ETAPA 4] Autenticação com o Google Fotos não concluída. Upload pulado.")
        return False

    log_dir = Path("logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"{project.project_id}_stage4_upload.log"

    success_count = 0
    with open(log_file, "a", encoding="utf-8") as log:
        log.write(f"=== INÍCIO ETAPA 4 (UPLOAD): {datetime.now().isoformat()} ===\n\n")

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)

            for idx, it in enumerate(upload_candidates, start=1):
                org_file = Path(it.organized_path)
                if not org_file.exists():
                    log.write(f"[{idx}/{len(upload_candidates)}] ARQUIVO NÃO ENCONTRADO: {org_file}\n")
                    continue

                # Optimize to Storage Saver
                opt_file = tmp_path / f"opt_{org_file.name}"
                try:
                    optimize_for_storage_saver(org_file, opt_file)
                    target_to_upload = opt_file
                except Exception as e:
                    # Fallback to original if optimization fails
                    log.write(f"[AVISO] Falha ao otimizar {org_file.name}, enviando original: {e}\n")
                    target_to_upload = org_file

                sys.stdout.write(f"\r[{idx}/{len(upload_candidates)}] ☁️  Enviando {org_file.name[:35]:<35}...")
                sys.stdout.flush()

                res = gp_mgr.upload_file(target_to_upload)

                if res.status in ("uploaded", "already_uploaded"):
                    it.uploaded_at = datetime.now().isoformat()
                    it.upload_token = res.upload_token
                    success_count += 1
                    log.write(f"[{idx}/{len(upload_candidates)}] OK | {res.status} | {org_file.name}\n")
                    sys.stdout.write(f"\r[{idx}/{len(upload_candidates)}] ✅ {org_file.name[:35]:<35} Enviado com sucesso!\n")
                else:
                    log.write(f"[{idx}/{len(upload_candidates)}] ERRO | {res.error_message} | {org_file.name}\n")
                    print(f"\n❌ Erro ao enviar {org_file.name}: {res.error_message}")

                opt_file.unlink(missing_ok=True)

    project.current_stage = 4
    project.save()

    print(f"\n✨ Upload concluído: {success_count}/{len(upload_candidates)} fotos enviadas com sucesso!")
    return success_count > 0 or len(upload_candidates) == 0
