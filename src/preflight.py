import shutil
import sys
import os
from pathlib import Path
from dataclasses import dataclass

from src.metadata_extractor import PHOTO_EXTENSIONS, VIDEO_EXTENSIONS

@dataclass
class PreflightResult:
    python_ok: bool
    python_version: str
    exiftool_ok: bool
    exiftool_path: str
    ffprobe_ok: bool
    ffprobe_path: str
    destination_writable: bool
    free_disk_space_gb: float
    removable_drives: list[str]
    source_path: str | None = None
    source_media_count: int = 0
    source_media_bytes: int = 0
    source_media_size_gb: float = 0.0
    has_enough_space: bool = True
    space_warning: str = ""

    @property
    def all_ok(self) -> bool:
        base_ok = self.python_ok and self.exiftool_ok and self.ffprobe_ok and self.destination_writable
        if self.source_path is not None:
            return base_ok and self.has_enough_space
        return base_ok

def find_removable_drives() -> list[str]:
    """Lists available removable drives on Windows."""
    drives = []
    if sys.platform == "win32":
        import ctypes
        bitmask = ctypes.windll.kernel32.GetLogicalDrives()
        for letter in range(26):
            if bitmask & (1 << letter):
                drive_letter = f"{chr(65 + letter)}:\\"
                drive_type = ctypes.windll.kernel32.GetDriveTypeW(drive_letter)
                # DRIVE_REMOVABLE = 2
                if drive_type == 2:
                    drives.append(drive_letter)
    return drives

def scan_source_media(source_path: str | Path) -> tuple[list[Path], int]:
    """
    Varre recursivamente a pasta de origem (mesmo bagunçada e com múltiplas subpastas),
    filtrando EXCLUSIVAMENTE fotos (incluindo todos os formatos RAW) e vídeos.
    Arquivos não-mídia (PDF, ZIP, TXT, EXE, etc.) e ocultos são ignorados.
    Retorna: (lista_de_paths_das_midias, total_bytes_apenas_dessas_midias)
    """
    src = Path(source_path)
    if not src.exists() or not src.is_dir():
        return [], 0

    valid_exts = PHOTO_EXTENSIONS | VIDEO_EXTENSIONS
    media_files: list[Path] = []
    total_bytes = 0

    for root, dirs, files in os.walk(src):
        # Ignora pastas ocultas (e.g. .git, .Trash, .vscode)
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for f in files:
            if f.startswith("."):
                continue
            p = Path(root) / f
            if p.suffix.lower() in valid_exts:
                try:
                    sz = p.stat().st_size
                    media_files.append(p)
                    total_bytes += sz
                except (OSError, PermissionError):
                    pass

    return media_files, total_bytes

def check_preflight(
    destination_root: str | Path,
    source_path: str | Path | None = None
) -> PreflightResult:
    dest = Path(destination_root)

    # 1. Python version
    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    py_ok = sys.version_info >= (3, 10)

    # 2. Exiftool
    exiftool_cmd = shutil.which("exiftool") or ("C:\\Windows\\exiftool.exe" if os.path.exists("C:\\Windows\\exiftool.exe") else "")
    exiftool_ok = bool(exiftool_cmd)

    # 3. FFprobe
    ffprobe_cmd = shutil.which("ffprobe") or ""
    ffprobe_ok = bool(ffprobe_cmd)

    # 4. Destination writable & disk space
    dest_writable = False
    free_gb = 0.0
    try:
        dest.mkdir(parents=True, exist_ok=True)
        test_file = dest / ".preflight_write_test"
        test_file.write_text("ok", encoding="utf-8")
        test_file.unlink()
        dest_writable = True
        
        usage = shutil.disk_usage(dest)
        free_gb = usage.free / (1024 ** 3)
    except Exception:
        dest_writable = False

    drives = find_removable_drives()

    # 5. Verificação de espaço da pasta fonte (apenas fotos e vídeos)
    src_path_str: str | None = None
    media_count = 0
    media_bytes = 0
    media_gb = 0.0
    has_enough_space = True
    space_warning = ""

    if source_path is not None:
        src_path_str = str(Path(source_path).resolve())
        src_p = Path(source_path)
        if not src_p.exists():
            has_enough_space = False
            space_warning = f"Pasta de origem não encontrada: {source_path}"
        else:
            media_files, media_bytes = scan_source_media(src_p)
            media_count = len(media_files)
            media_gb = round(media_bytes / (1024 ** 3), 2)

            if media_gb > free_gb:
                has_enough_space = False
                space_warning = (
                    f"Espaço insuficiente no destino: necessário {media_gb} GB "
                    f"(para {media_count} fotos/vídeos), mas há apenas {round(free_gb, 2)} GB livres."
                )

    return PreflightResult(
        python_ok=py_ok,
        python_version=py_ver,
        exiftool_ok=exiftool_ok,
        exiftool_path=exiftool_cmd or "NÃO ENCONTRADO",
        ffprobe_ok=ffprobe_ok,
        ffprobe_path=ffprobe_cmd or "NÃO ENCONTRADO",
        destination_writable=dest_writable,
        free_disk_space_gb=round(free_gb, 2),
        removable_drives=drives,
        source_path=src_path_str,
        source_media_count=media_count,
        source_media_bytes=media_bytes,
        source_media_size_gb=media_gb,
        has_enough_space=has_enough_space,
        space_warning=space_warning,
    )

