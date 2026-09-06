from pathlib import Path
from datetime import datetime
from src.metadata_extractor import MediaMetadata
from src.namer import generate_target_filename, sanitize_filename
from src.config import NamingConfig

def test_sanitize_filename():
    assert sanitize_filename('test:file*name?.jpg') == 'test-file-name-.jpg'
    assert sanitize_filename('clean_name') == 'clean_name'

def test_generate_photo_filename_sx60():
    meta = MediaMetadata(
        file_path=Path("IMG_9821.JPG"),
        is_video=False,
        date_str="2026-09-06",
        time_str="14-25-30",
        timestamp=datetime(2026, 9, 6, 14, 25, 30),
        camera_model="SX60",
        focal_length_equiv=1365.0,
        focal_str="1365mm",
        aperture_str="f6.5",
        shutter_str="1-1000s",
        iso_str="ISO400",
        resolution_str="16MP",
        fps_str="",
        duration_str="",
        original_stem="IMG_9821",
        extension="JPG",
        is_raw=False,
    )
    res = generate_target_filename(meta)
    assert res == "2026-09-06_14-25-30_SX60_1365mm_f6.5_1-1000s_ISO400_IMG_9821.jpg"

def test_generate_photo_filename_t6():
    meta = MediaMetadata(
        file_path=Path("IMG_4512.JPG"),
        is_video=False,
        date_str="2026-09-06",
        time_str="18-40-12",
        timestamp=datetime(2026, 9, 6, 18, 40, 12),
        camera_model="T6",
        focal_length_equiv=50.0,
        focal_str="50mm",
        aperture_str="f1.8",
        shutter_str="1-200s",
        iso_str="ISO800",
        resolution_str="18MP",
        fps_str="",
        duration_str="",
        original_stem="IMG_4512",
        extension="JPG",
        is_raw=False,
    )
    res = generate_target_filename(meta)
    assert res == "2026-09-06_18-40-12_T6_50mm_f1.8_1-200s_ISO800_IMG_4512.jpg"

def test_generate_video_filename():
    meta = MediaMetadata(
        file_path=Path("MVI_9822.MP4"),
        is_video=True,
        date_str="2026-09-06",
        time_str="15-10-00",
        timestamp=datetime(2026, 9, 6, 15, 10, 0),
        camera_model="SX60",
        focal_length_equiv=0.0,
        focal_str="",
        aperture_str="",
        shutter_str="",
        iso_str="",
        resolution_str="1080p",
        fps_str="60fps",
        duration_str="01m45s",
        original_stem="MVI_9822",
        extension="MP4",
        is_raw=False,
    )
    res = generate_target_filename(meta)
    assert res == "2026-09-06_15-10-00_SX60_1080p_60fps_01m45s_MVI_9822.mp4"
