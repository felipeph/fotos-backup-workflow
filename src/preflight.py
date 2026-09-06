import shutil
import sys
import os
from pathlib import Path
from dataclasses import dataclass

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

    @property
    def all_ok(self) -> bool:
        return self.python_ok and self.exiftool_ok and self.ffprobe_ok and self.destination_writable

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

def check_preflight(destination_root: str | Path) -> PreflightResult:
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
    )
