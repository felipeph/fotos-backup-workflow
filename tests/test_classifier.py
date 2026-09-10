from pathlib import Path
from datetime import datetime, timedelta
from src.metadata_extractor import MediaMetadata
from src.classifier import classify_media_batch
from src.config import PipelineConfig

def create_mock_photo(name: str, ts: datetime, cam: str = "SX60", focal: float = 50.0, is_raw: bool = False, ext: str = "JPG", make: str = "Cam"):
    return MediaMetadata(
        file_path=Path(name),
        is_video=False,
        date_str=ts.strftime("%Y-%m-%d"),
        time_str=ts.strftime("%H-%M-%S"),
        timestamp=ts,
        camera_model=cam,
        camera_make=make,
        focal_length_equiv=focal,
        focal_str=f"{int(focal)}mm",
        aperture_str="f4",
        shutter_str="1-500s",
        iso_str="ISO200",
        resolution_str="16MP",
        fps_str="",
        duration_str="",
        original_stem=Path(name).stem,
        extension=ext,
        is_raw=is_raw,
    )

def test_classifier_photos_organized_directly_by_day_when_bursts_disabled():
    base_t = datetime(2026, 9, 6, 14, 0, 0)
    config = PipelineConfig()  # enable_burst_detection defaults to False

    # 3 photos in 1s interval + 1 photo after 10s
    p1 = create_mock_photo("IMG_001.JPG", base_t)
    p2 = create_mock_photo("IMG_002.JPG", base_t + timedelta(seconds=1))
    p3 = create_mock_photo("IMG_003.JPG", base_t + timedelta(seconds=2))
    p4 = create_mock_photo("IMG_004.JPG", base_t + timedelta(seconds=12))

    classified = classify_media_batch([p1, p2, p3, p4], config)
    assert len(classified) == 4

    expected_dir = Path("Biblioteca") / "2026" / "09" / "06"
    for item in classified:
        assert item.relative_dest_dir == expected_dir
        assert "rajada" not in str(item.relative_dest_dir)
        assert "avulsas" not in str(item.relative_dest_dir)
        assert item.category == "avulsa"

def test_classifier_burst_and_avulsas_when_enabled():
    base_t = datetime(2026, 9, 6, 14, 0, 0)
    config = PipelineConfig(enable_burst_detection=True, burst_interval_seconds=3.0)

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

def test_classifier_gopro_normal_photos():
    base_t = datetime(2026, 9, 6, 8, 0, 0)
    config = PipelineConfig(timelapse_min_photos=500, enable_burst_detection=True, burst_interval_seconds=3.0)

    # GoPro photos under 500 count: should be burst (if close) or avulsa
    p1 = create_mock_photo("GOPR001.JPG", base_t, cam="HERO5-Black", make="GoPro")
    p2 = create_mock_photo("GOPR002.JPG", base_t + timedelta(seconds=2), cam="HERO5-Black", make="GoPro")
    p3 = create_mock_photo("GOPR003.JPG", base_t + timedelta(seconds=30), cam="HERO5-Black", make="GoPro")

    classified = classify_media_batch([p1, p2, p3], config)
    assert len(classified) == 3

    burst_items = [c for c in classified if c.category == "rajada"]
    single_items = [c for c in classified if c.category == "avulsa"]

    assert len(burst_items) == 2
    assert len(single_items) == 1
    assert "rajada_08-00-00" in str(burst_items[0].relative_dest_dir)
    assert "Biblioteca" in str(burst_items[0].relative_dest_dir)
    assert "avulsas" in str(single_items[0].relative_dest_dir)

def test_classifier_true_timelapse_500_photos():
    base_t = datetime(2026, 9, 6, 8, 0, 0)
    config = PipelineConfig(timelapse_min_photos=500)

    # 500 sequential photos taken at 1s regular intervals (GoPro or Canon)
    photos = [
        create_mock_photo(f"G00{i:04d}.JPG", base_t + timedelta(seconds=i), cam="HERO5-Black", make="GoPro")
        for i in range(500)
    ]

    classified = classify_media_batch(photos, config)
    assert len(classified) == 500
    for item in classified:
        assert item.category == "timelapse"
        assert "Timelapses" in str(item.relative_dest_dir)
        assert "GoPro" in str(item.relative_dest_dir)
        assert "timelapse_08-00-00" in str(item.relative_dest_dir)

def test_classifier_long_burst_under_500_is_rajada():
    base_t = datetime(2026, 9, 6, 10, 0, 0)
    config = PipelineConfig(timelapse_min_photos=500, enable_burst_detection=True, burst_interval_seconds=3.0)

    # 200 sports burst photos taken at 0.5s intervals: NOT timelapse because < 500 photos
    photos = [
        create_mock_photo(f"EOS_{i:04d}.JPG", base_t + timedelta(milliseconds=i * 500), cam="EOS-R5", make="Canon")
        for i in range(200)
    ]

    classified = classify_media_batch(photos, config)
    assert len(classified) == 200
    for item in classified:
        assert item.category == "rajada"
        assert "Biblioteca" in str(item.relative_dest_dir)
        assert "rajada_10-00-00" in str(item.relative_dest_dir)

def test_classifier_nightlapse_regular_cadence():
    base_t = datetime(2026, 9, 6, 22, 0, 0)
    config = PipelineConfig(timelapse_min_photos=500, timelapse_max_interval_seconds=120.0)

    # 500 nightlapse photos taken at regular 30s intervals with a Sony camera
    photos = [
        create_mock_photo(f"DSC_{i:04d}.ARW", base_t + timedelta(seconds=i * 30), cam="ILCE-7M4", make="Sony", is_raw=True, ext="ARW")
        for i in range(500)
    ]

    classified = classify_media_batch(photos, config)
    assert len(classified) == 500
    for item in classified:
        assert item.category == "timelapse"
        assert "Timelapses" in str(item.relative_dest_dir)
        assert "Sony" in str(item.relative_dest_dir)
        assert "timelapse_22-00-00" in str(item.relative_dest_dir)

def test_classifier_timelapse_isolated_from_surrounding_singles():
    base_t = datetime(2026, 9, 6, 12, 0, 0)
    config = PipelineConfig(timelapse_min_photos=500)

    # 3 single photos spaced by 60s
    singles_before = [
        create_mock_photo(f"PRE_{i}.JPG", base_t + timedelta(seconds=i * 60), cam="HERO5-Black", make="GoPro")
        for i in range(3)
    ]

    # 500 timelapse photos with 1s interval starting 10 minutes later
    tl_base = base_t + timedelta(minutes=10)
    tl_photos = [
        create_mock_photo(f"TL_{i:04d}.JPG", tl_base + timedelta(seconds=i), cam="HERO5-Black", make="GoPro")
        for i in range(500)
    ]

    # 2 single photos spaced by 60s starting 10 minutes after timelapse ends
    after_base = tl_base + timedelta(seconds=500) + timedelta(minutes=10)
    singles_after = [
        create_mock_photo(f"POST_{i}.JPG", after_base + timedelta(seconds=i * 60), cam="HERO5-Black", make="GoPro")
        for i in range(2)
    ]

    all_photos = singles_before + tl_photos + singles_after
    classified = classify_media_batch(all_photos, config)

    assert len(classified) == 3 + 500 + 2
    tl_items = [c for c in classified if c.category == "timelapse"]
    single_items = [c for c in classified if c.category == "avulsa"]

    assert len(tl_items) == 500
    assert len(single_items) == 5
    for item in tl_items:
        assert "Timelapses" in str(item.relative_dest_dir)
    for item in single_items:
        assert "Biblioteca" in str(item.relative_dest_dir)

def test_classifier_multi_camera_concurrent_isolation():
    base_t = datetime(2026, 9, 6, 15, 0, 0)
    config = PipelineConfig(timelapse_min_photos=500)

    # GoPro timelapse of 500 photos at 1s intervals
    gopro_tl = [
        create_mock_photo(f"GOPR_{i:04d}.JPG", base_t + timedelta(seconds=i), cam="HERO5-Black", make="GoPro")
        for i in range(500)
    ]

    # Canon photos taken concurrently during the same timeframe (interleaved)
    canon_photos = [
        create_mock_photo("IMG_C1.JPG", base_t + timedelta(seconds=50), cam="SX60", make="Canon"),
        create_mock_photo("IMG_C2.JPG", base_t + timedelta(seconds=120), cam="SX60", make="Canon"),
        create_mock_photo("IMG_C3.JPG", base_t + timedelta(seconds=300), cam="SX60", make="Canon"),
    ]

    combined = gopro_tl + canon_photos
    classified = classify_media_batch(combined, config)

    assert len(classified) == 503
    tl_items = [c for c in classified if c.category == "timelapse"]
    canon_items = [c for c in classified if c.metadata.camera_make == "Canon"]

    assert len(tl_items) == 500
    assert len(canon_items) == 3
    for it in canon_items:
        assert it.category == "avulsa"
        assert "Biblioteca" in str(it.relative_dest_dir)
    for it in tl_items:
        assert "Timelapses" in str(it.relative_dest_dir)
        assert "GoPro" in str(it.relative_dest_dir)

def test_classifier_timelapse_with_buffer_jitter():
    base_t = datetime(2026, 9, 6, 16, 0, 0)
    config = PipelineConfig(timelapse_min_photos=500)

    # 500 photos where frame 250 had a slight card write lag (2s instead of 1s)
    photos = []
    current_time = base_t
    for i in range(500):
        photos.append(create_mock_photo(f"G_{i:04d}.JPG", current_time, cam="HERO5-Black", make="GoPro"))
        if i == 250:
            current_time += timedelta(seconds=2)
        else:
            current_time += timedelta(seconds=1)

    classified = classify_media_batch(photos, config)
    assert len(classified) == 500
    for item in classified:
        assert item.category == "timelapse"

def test_classifier_video_duplication():
    base_t = datetime(2026, 9, 6, 17, 30, 0)
    config = PipelineConfig()
    video = MediaMetadata(
        file_path=Path("MVI_0001.MP4"),
        is_video=True,
        date_str=base_t.strftime("%Y-%m-%d"),
        time_str=base_t.strftime("%H-%M-%S"),
        timestamp=base_t,
        camera_model="SX60",
        camera_make="Canon",
        focal_length_equiv=0.0,
        focal_str="",
        aperture_str="",
        shutter_str="",
        iso_str="",
        resolution_str="1080p",
        fps_str="60fps",
        duration_str="00-01-30",
        original_stem="MVI_0001",
        extension="MP4",
        is_raw=False,
    )

    classified = classify_media_batch([video], config)
    assert len(classified) == 1
    item = classified[0]
    assert item.category == "video"
    assert item.relative_dest_dir == Path("Biblioteca") / "2026" / "09" / "06" / "videos"
    assert len(item.extra_dest_dirs) == 1
    assert item.extra_dest_dirs[0] == Path("Videos") / "2026" / "09" / "06" / "videos"


