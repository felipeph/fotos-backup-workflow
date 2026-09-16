from pathlib import Path
from datetime import datetime
from src.metadata_extractor import MediaMetadata
from src.namer import generate_target_filename, sanitize_filename
from src.config import NamingConfig

def test_sanitize_filename():
    assert sanitize_filename('test:file*name?_f1.8') == 'test-file-name_f1-8'
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
        aperture_str="f6-5",
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
    assert res == "2026-09-06_14-25-30_SX60_1365mm_f6-5_1-1000s_ISO400_IMG_9821.jpg"

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
        aperture_str="f1-8",
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
    assert res == "2026-09-06_18-40-12_T6_50mm_f1-8_1-200s_ISO800_IMG_4512.jpg"

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

def test_generate_photo_filename_gopro_hero5():
    meta = MediaMetadata(
        file_path=Path("G0016773.JPG"),
        is_video=False,
        date_str="2026-09-06",
        time_str="16-06-24",
        timestamp=datetime(2026, 9, 6, 16, 6, 24),
        camera_model="HERO5-Black",
        camera_make="GoPro",
        focal_length_equiv=17.0,
        focal_str="17mm",
        aperture_str="f2-8",
        shutter_str="1-2283s",
        iso_str="ISO100",
        resolution_str="12MP",
        fps_str="",
        duration_str="",
        original_stem="G0016773",
        extension="JPG",
        is_raw=False,
    )
    res = generate_target_filename(meta)
    # Checks that spaces and mmmm are not present, and both make and model appear cleanly
    assert res == "2026-09-06_16-06-24_GoPro_HERO5-Black_17mm_f2-8_1-2283s_ISO100_G0016773.jpg"

def test_generate_filename_with_dimensions_and_megapixels():
    meta = MediaMetadata(
        file_path=Path("IMG_1234.JPG"),
        is_video=False,
        date_str="2026-09-16",
        time_str="10-00-00",
        timestamp=datetime(2026, 9, 16, 10, 0, 0),
        camera_model="EOS-R5",
        camera_make="Canon",
        focal_length_equiv=50.0,
        focal_str="50mm",
        aperture_str="f2-8",
        shutter_str="1-500s",
        iso_str="ISO100",
        resolution_str="45MP",
        fps_str="",
        duration_str="",
        original_stem="IMG_1234",
        extension="JPG",
        is_raw=False,
        width=8192,
        height=5464,
    )
    
    # Test custom pattern with width, height, megapixels, dimensions
    config = NamingConfig(
        photo_pattern="{date}_{camera}_{width}x{height}_{megapixels}_{original}.{ext}"
    )
    res = generate_target_filename(meta, config)
    assert res == "2026-09-16_Canon_EOS-R5_8192x5464_45MP_IMG_1234.jpg"

    config_dim = NamingConfig(
        photo_pattern="{date}_{camera}_{dimensions}_{mp}_{original}.{ext}"
    )
    res_dim = generate_target_filename(meta, config_dim)
    assert res_dim == "2026-09-16_Canon_EOS-R5_8192x5464_45MP_IMG_1234.jpg"

def test_generate_video_filename_with_dimensions():
    meta = MediaMetadata(
        file_path=Path("GH010001.MP4"),
        is_video=True,
        date_str="2026-09-16",
        time_str="10-30-00",
        timestamp=datetime(2026, 9, 16, 10, 30, 0),
        camera_model="HERO11-Black",
        camera_make="GoPro",
        focal_length_equiv=0.0,
        focal_str="",
        aperture_str="",
        shutter_str="",
        iso_str="",
        resolution_str="4K",
        fps_str="60fps",
        duration_str="02m30s",
        original_stem="GH010001",
        extension="MP4",
        is_raw=False,
        width=3840,
        height=2160,
    )

    config = NamingConfig(
        video_pattern="{date}_{camera}_{width}x{height}_{resolution}_{fps}_{duration}_{original}.{ext}"
    )
    res = generate_target_filename(meta, config)
    assert res == "2026-09-16_GoPro_HERO11-Black_3840x2160_4K_60fps_02m30s_GH010001.mp4"

