import subprocess
import json
import shutil
import re
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime

PHOTO_EXTENSIONS = {".jpg", ".jpeg", ".cr2", ".png", ".dng", ".tif", ".tiff"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".m4v"}

@dataclass
class MediaMetadata:
    file_path: Path
    is_video: bool
    date_str: str          # YYYY-MM-DD
    time_str: str          # HH-mm-SS
    timestamp: datetime
    camera_model: str      # e.g. "SX60", "SX50", "T6", "GoPro", "Camera"
    focal_length_equiv: float # e.g. 1365.0, 50.0
    focal_str: str         # e.g. "1365mm"
    aperture_str: str      # e.g. "f6.5"
    shutter_str: str       # e.g. "1-1000s"
    iso_str: str           # e.g. "ISO400"
    resolution_str: str    # e.g. "16MP" ou "1080p"
    fps_str: str           # e.g. "60fps"
    duration_str: str      # e.g. "01m45s"
    original_stem: str     # e.g. "IMG_1234"
    extension: str         # e.g. "JPG"
    is_raw: bool

def sanitize_camera_name(raw_model: str) -> str:
    if not raw_model:
        return "Cam"
    raw_upper = raw_model.upper()
    if "SX60" in raw_upper:
        return "SX60"
    elif "SX50" in raw_upper:
        return "SX50"
    elif "REBEL T6" in raw_upper or "1300D" in raw_upper:
        return "T6"
    elif "GOPRO" in raw_upper or "HERO" in raw_upper:
        return "GoPro"
    elif "CANON" in raw_upper:
        return "Canon"
    
    # Generic cleanup
    clean = re.sub(r"[^A-Za-z0-9]", "", raw_model)
    return clean[:8] if clean else "Cam"

def format_shutter(exposure_time) -> str:
    if exposure_time is None:
        return "auto"
    try:
        val = float(exposure_time)
        if val <= 0:
            return "auto"
        if val < 1.0:
            frac = round(1.0 / val)
            return f"1-{frac}s"
        else:
            if val.is_integer():
                return f"{int(val)}s"
            return f"{val:.1f}s"
    except (ValueError, TypeError):
        s = str(exposure_time).replace("/", "-")
        return f"{s}s"

def format_aperture(fnumber) -> str:
    if fnumber is None:
        return "f0"
    try:
        val = float(fnumber)
        if val.is_integer():
            return f"f{int(val)}"
        return f"f{val:.1f}"
    except (ValueError, TypeError):
        return f"f{fnumber}"

def format_focal(focal_35mm, focal_real) -> tuple[float, str]:
    target = focal_35mm if focal_35mm else focal_real
    if target is None:
        return 0.0, "0mm"
    try:
        val = float(target)
        return val, f"{round(val)}mm"
    except (ValueError, TypeError):
        return 0.0, f"{target}mm"

def format_duration(seconds: float | None) -> str:
    if seconds is None or seconds <= 0:
        return "00s"
    m = int(seconds // 60)
    s = int(seconds % 60)
    if m > 0:
        return f"{m:02d}m{s:02d}s"
    return f"{s:02d}s"

def extract_metadata_batch(file_paths: list[Path]) -> list[MediaMetadata]:
    """Extracts metadata for a batch of files using exiftool and ffprobe."""
    if not file_paths:
        return []

    exiftool_bin = shutil.which("exiftool") or ("C:\\Windows\\exiftool.exe" if Path("C:\\Windows\\exiftool.exe").exists() else None)
    results = []

    # Map of path -> raw exif dict
    exif_map: dict[str, dict] = {}

    if exiftool_bin:
        try:
            cmd = [
                exiftool_bin,
                "-json",
                "-DateTimeOriginal",
                "-CreateDate",
                "-ModifyDate",
                "-Model",
                "-Make",
                "-FocalLengthIn35mmFormat",
                "-FocalLength",
                "-FNumber",
                "-ExposureTime",
                "-ISO",
                "-ImageWidth",
                "-ImageHeight",
                "-Duration",
                "-VideoFrameRate",
            ] + [str(p) for p in file_paths]

            proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
            if proc.returncode == 0 and proc.stdout:
                parsed = json.loads(proc.stdout)
                for item in parsed:
                    src_file = Path(item.get("SourceFile", "")).resolve()
                    exif_map[str(src_file)] = item
        except Exception as e:
            print(f"[WARN] Falha ao rodar exiftool em lote: {e}")

    for p in file_paths:
        p_res = p.resolve()
        ext = p.suffix.lower()
        is_video = ext in VIDEO_EXTENSIONS
        is_raw = ext in {".cr2", ".dng"}
        raw_exif = exif_map.get(str(p_res), {})

        # Date parsing
        date_raw = raw_exif.get("DateTimeOriginal") or raw_exif.get("CreateDate") or raw_exif.get("ModifyDate")
        dt = None
        if date_raw:
            try:
                # Exif dates are usually "YYYY:MM:DD HH:MM:SS"
                clean_dt = str(date_raw)[:19].replace("-", ":")
                dt = datetime.strptime(clean_dt, "%Y:%m:%d %H:%M:%S")
            except Exception:
                pass
        
        if dt is None:
            # Fallback to file mtime
            mtime = p.stat().st_mtime
            dt = datetime.fromtimestamp(mtime)

        date_str = dt.strftime("%Y-%m-%d")
        time_str = dt.strftime("%H-%M-%S")

        # Camera
        model = sanitize_camera_name(raw_exif.get("Model") or raw_exif.get("Make") or "")

        # Focal
        focal_val, focal_str = format_focal(
            raw_exif.get("FocalLengthIn35mmFormat"),
            raw_exif.get("FocalLength")
        )

        # Aperture
        aperture_str = format_aperture(raw_exif.get("FNumber"))

        # Shutter
        shutter_str = format_shutter(raw_exif.get("ExposureTime"))

        # ISO
        iso_raw = raw_exif.get("ISO")
        iso_str = f"ISO{iso_raw}" if iso_raw else "auto"

        # Resolution / Duration / FPS
        w = raw_exif.get("ImageWidth")
        h = raw_exif.get("ImageHeight")
        res_str = ""
        fps_str = ""
        dur_str = ""

        if is_video:
            # Check video duration / fps
            dur_raw = raw_exif.get("Duration")
            # Duration can be e.g. "12.34 s" or 12.34
            dur_sec = None
            if dur_raw:
                try:
                    dur_sec = float(str(dur_raw).replace("s", "").strip())
                except ValueError:
                    pass
            
            dur_str = format_duration(dur_sec)
            
            fps_raw = raw_exif.get("VideoFrameRate")
            if fps_raw:
                try:
                    fps_str = f"{round(float(fps_raw))}fps"
                except ValueError:
                    fps_str = f"{fps_raw}fps"
            else:
                fps_str = "30fps"

            if h:
                if h >= 2160:
                    res_str = "4K"
                elif h >= 1080:
                    res_str = "1080p"
                elif h >= 720:
                    res_str = "720p"
                else:
                    res_str = f"{h}p"
            else:
                res_str = "1080p"
        else:
            if w and h:
                mp = (w * h) / 1_000_000
                res_str = f"{round(mp)}MP" if mp >= 1 else f"{w}x{h}"
            else:
                res_str = ""

        meta = MediaMetadata(
            file_path=p,
            is_video=is_video,
            date_str=date_str,
            time_str=time_str,
            timestamp=dt,
            camera_model=model,
            focal_length_equiv=focal_val,
            focal_str=focal_str,
            aperture_str=aperture_str,
            shutter_str=shutter_str,
            iso_str=iso_str,
            resolution_str=res_str,
            fps_str=fps_str,
            duration_str=dur_str,
            original_stem=p.stem,
            extension=p.suffix.lstrip(".").upper(),
            is_raw=is_raw,
        )
        results.append(meta)

    return results
