from dataclasses import dataclass
from pathlib import Path
from datetime import datetime
from src.metadata_extractor import MediaMetadata
from src.config import PipelineConfig
from src.namer import generate_target_filename

@dataclass
class ClassifiedItem:
    metadata: MediaMetadata
    category: str  # "astro_lua", "timelapse_gopro", "video", "rajada", "avulsa"
    relative_dest_dir: Path
    target_filename: str

def classify_media_batch(items: list[MediaMetadata], config: PipelineConfig) -> list[ClassifiedItem]:
    if not items:
        return []

    # Sort all items chronologically
    sorted_items = sorted(items, key=lambda x: x.timestamp)
    classified: list[ClassifiedItem] = []

    # Separate items into categories:
    # 1. Astro Moon RAW
    # 2. Timelapse GoPro
    # 3. Videos
    # 4. Standard Photos (to be grouped into Bursts or Singles)

    astro_items: list[MediaMetadata] = []
    gopro_timelapse_items: list[MediaMetadata] = []
    video_items: list[MediaMetadata] = []
    general_photo_items: list[MediaMetadata] = []

    for item in sorted_items:
        # 1. Astro Moon
        if item.is_raw and (item.focal_length_equiv >= config.moon_zoom_threshold_mm or "sx60" in item.camera_model.lower() or "sx50" in item.camera_model.lower()):
            astro_items.append(item)
        # 2. GoPro Photos
        elif not item.is_video and (getattr(item, "camera_make", "").lower() == "gopro" or "gopro" in item.camera_model.lower()):
            gopro_timelapse_items.append(item)
        # 3. Video
        elif item.is_video:
            video_items.append(item)
        # 4. General Photos
        else:
            general_photo_items.append(item)

    # Process Astro Moon items (Group into sessions if separated by > 60s)
    if astro_items:
        current_session = [astro_items[0]]
        astro_sessions = [current_session]
        for prev, curr in zip(astro_items[:-1], astro_items[1:]):
            delta = (curr.timestamp - prev.timestamp).total_seconds()
            if delta <= 60.0:
                current_session.append(curr)
            else:
                current_session = [curr]
                astro_sessions.append(current_session)

        for session in astro_sessions:
            first = session[0]
            y, m, d = first.date_str.split("-")
            session_dir = Path("Astrofotografia") / "Lua" / y / m / d / f"sessao_{first.time_str}"
            for it in session:
                target_name = generate_target_filename(it, config.naming)
                classified.append(ClassifiedItem(
                    metadata=it,
                    category="astro_lua",
                    relative_dest_dir=session_dir,
                    target_filename=target_name,
                ))

    # Process GoPro Timelapse items (Group sequences if gap > 15s)
    if gopro_timelapse_items:
        current_tl = [gopro_timelapse_items[0]]
        tl_sessions = [current_tl]
        for prev, curr in zip(gopro_timelapse_items[:-1], gopro_timelapse_items[1:]):
            delta = (curr.timestamp - prev.timestamp).total_seconds()
            if delta <= 15.0:
                current_tl.append(curr)
            else:
                current_tl = [curr]
                tl_sessions.append(current_tl)

        for tl in tl_sessions:
            first = tl[0]
            y, m, d = first.date_str.split("-")
            tl_dir = Path("Timelapses") / "GoPro" / y / m / d / f"timelapse_{first.time_str}"
            for it in tl:
                target_name = generate_target_filename(it, config.naming)
                classified.append(ClassifiedItem(
                    metadata=it,
                    category="timelapse_gopro",
                    relative_dest_dir=tl_dir,
                    target_filename=target_name,
                ))

    # Process Videos
    for it in video_items:
        y, m, d = it.date_str.split("-")
        vdir = Path("Biblioteca") / y / m / d / "videos"
        target_name = generate_target_filename(it, config.naming)
        classified.append(ClassifiedItem(
            metadata=it,
            category="video",
            relative_dest_dir=vdir,
            target_filename=target_name,
        ))

    # Process General Photos (Burst vs Avulsas)
    if general_photo_items:
        current_burst = [general_photo_items[0]]
        burst_groups = [current_burst]

        for prev, curr in zip(general_photo_items[:-1], general_photo_items[1:]):
            delta = (curr.timestamp - prev.timestamp).total_seconds()
            # Only consider burst if same camera and delta <= burst_interval_seconds
            if prev.camera_model == curr.camera_model and 0.0 <= delta <= config.burst_interval_seconds:
                current_burst.append(curr)
            else:
                current_burst = [curr]
                burst_groups.append(current_burst)

        for group in burst_groups:
            first = group[0]
            y, m, d = first.date_str.split("-")
            if len(group) >= 2:
                # Burst!
                bdir = Path("Biblioteca") / y / m / d / f"rajada_{first.time_str}"
                cat = "rajada"
            else:
                # Single photo
                bdir = Path("Biblioteca") / y / m / d / "avulsas"
                cat = "avulsa"

            for it in group:
                target_name = generate_target_filename(it, config.naming)
                classified.append(ClassifiedItem(
                    metadata=it,
                    category=cat,
                    relative_dest_dir=bdir,
                    target_filename=target_name,
                ))

    return classified
