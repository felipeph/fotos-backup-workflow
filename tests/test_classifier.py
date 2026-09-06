from pathlib import Path
from datetime import datetime, timedelta
from src.metadata_extractor import MediaMetadata
from src.classifier import classify_media_batch
from src.config import PipelineConfig

def create_mock_photo(name: str, ts: datetime, cam: str = "SX60", focal: float = 50.0, is_raw: bool = False, ext: str = "JPG"):
    return MediaMetadata(
        file_path=Path(name),
        is_video=False,
        date_str=ts.strftime("%Y-%m-%d"),
        time_str=ts.strftime("%H-%M-%S"),
        timestamp=ts,
        camera_model=cam,
        focal_length_equiv=focal,
        focal_str=f"{int(focal)}mm",
        aperture_str="f4.0",
        shutter_str="1-500s",
        iso_str="ISO200",
        resolution_str="16MP",
        fps_str="",
        duration_str="",
        original_stem=Path(name).stem,
        extension=ext,
        is_raw=is_raw,
    )

def test_classifier_burst_and_avulsas():
    base_t = datetime(2026, 9, 6, 14, 0, 0)
    config = PipelineConfig(burst_interval_seconds=3.0)

    # 3 burst photos (interval 1s)
    p1 = create_mock_photo("IMG_001.JPG", base_t)
    p2 = create_mock_photo("IMG_002.JPG", base_t + timedelta(seconds=1))
    p3 = create_mock_photo("IMG_003.JPG", base_t + timedelta(seconds=2))

    # 1 single photo (gap 10s)
    p4 = create_mock_photo("IMG_004.JPG", base_t + timedelta(seconds=12))

    classified = classify_media_batch([p1, p2, p3, p4], config)
    assert len(classified) == 4

    burst_items = [c for c in classified if c.category == "rajada"]
    single_items = [c for c in classified if c.category == "avulsa"]

    assert len(burst_items) == 3
    assert len(single_items) == 1

    # Verify destination directories
    assert "rajada_14-00-00" in str(burst_items[0].relative_dest_dir)
    assert "avulsas" in str(single_items[0].relative_dest_dir)

def test_classifier_astro_moon_raw():
    base_t = datetime(2026, 9, 6, 21, 30, 0)
    config = PipelineConfig(moon_zoom_threshold_mm=1200.0)

    # CR2 RAW with telephoto zoom on SX60
    p1 = create_mock_photo("IMG_1001.CR2", base_t, cam="SX60", focal=1365.0, is_raw=True, ext="CR2")
    p2 = create_mock_photo("IMG_1002.CR2", base_t + timedelta(seconds=5), cam="SX60", focal=1365.0, is_raw=True, ext="CR2")

    classified = classify_media_batch([p1, p2], config)
    assert len(classified) == 2
    for item in classified:
        assert item.category == "astro_lua"
        assert "Astrofotografia" in str(item.relative_dest_dir)
        assert "Lua" in str(item.relative_dest_dir)

def test_classifier_gopro_timelapse():
    base_t = datetime(2026, 9, 6, 8, 0, 0)
    config = PipelineConfig()

    p1 = create_mock_photo("GOPR001.JPG", base_t, cam="GoPro")
    p2 = create_mock_photo("GOPR002.JPG", base_t + timedelta(seconds=5), cam="GoPro")

    classified = classify_media_batch([p1, p2], config)
    assert len(classified) == 2
    for item in classified:
        assert item.category == "timelapse_gopro"
        assert "Timelapses" in str(item.relative_dest_dir)
        assert "GoPro" in str(item.relative_dest_dir)
