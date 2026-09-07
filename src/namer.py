import re
from pathlib import Path
from src.metadata_extractor import MediaMetadata
from src.config import NamingConfig

def sanitize_filename(name: str) -> str:
    # Replace illegal Windows filename chars and dots with hyphen
    clean = re.sub(r'[\\/*?:"<>|.]', "-", name)
    # Replace any spaces with hyphen
    clean = re.sub(r"\s+", "-", clean)
    # Remove multiple consecutive underscores or hyphens
    clean = re.sub(r"_+", "_", clean)
    clean = re.sub(r"-+", "-", clean)
    clean = clean.replace("-_", "_").replace("_-", "_")
    return clean.strip("._- ")

def generate_target_filename(meta: MediaMetadata, config: NamingConfig | None = None) -> str:
    if config is None:
        config = NamingConfig()

    original_clean = re.sub(r"[^A-Za-z0-9_-]", "", meta.original_stem)

    make = getattr(meta, "camera_make", "Cam") or "Cam"
    model = meta.camera_model or "Cam"
    if make == "Cam" or make.lower() == model.lower() or make.lower() in model.lower():
        camera_str = model
    else:
        camera_str = f"{make}_{model}"

    if meta.is_video:
        pattern = config.video_pattern
        res = pattern.format(
            date=meta.date_str,
            time=meta.time_str,
            camera=camera_str,
            make=make,
            model=model,
            camera_make=make,
            camera_model=model,
            resolution=meta.resolution_str or "1080p",
            fps=meta.fps_str or "30fps",
            duration=meta.duration_str or "00s",
            original=original_clean,
            ext=meta.extension.lower(),
        )
    else:
        # Photo
        pattern = config.photo_pattern
        res = pattern.format(
            date=meta.date_str,
            time=meta.time_str,
            camera=camera_str,
            make=make,
            model=model,
            camera_make=make,
            camera_model=model,
            focal=meta.focal_str or "",
            aperture=meta.aperture_str or "",
            shutter=meta.shutter_str or "",
            iso=meta.iso_str or "",
            resolution=meta.resolution_str or "",
            original=original_clean,
            ext=meta.extension.lower(),
        )

    # Split name and ext to sanitize base name
    dot_idx = res.rfind(".")
    if dot_idx != -1:
        base = res[:dot_idx]
        ext = res[dot_idx + 1:]
    else:
        base = res
        ext = meta.extension.lower()

    base_clean = sanitize_filename(base)
    return f"{base_clean}.{ext}"
