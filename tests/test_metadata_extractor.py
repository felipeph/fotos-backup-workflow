import tempfile
from pathlib import Path
from src.metadata_extractor import extract_metadata_batch, parse_camera_generic, format_focal

def test_extract_metadata_batch_empty():
    res = extract_metadata_batch([])
    assert res == []

def test_extract_metadata_batch_files():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_p = Path(tmpdir)
        files = []
        for i in range(5):
            f = tmp_p / f"sample_{i}.jpg"
            f.write_bytes(b"dummy image bytes")
            files.append(f)

        progress_calls = []
        def on_prog(done, total):
            progress_calls.append((done, total))

        metas = extract_metadata_batch(files, progress_callback=on_prog)
        assert len(metas) == 5
        assert metas[0].extension == "JPG"
        assert metas[0].original_stem == "sample_0"

def test_parse_camera_generic():
    # GoPro
    make, model, comb = parse_camera_generic("GoPro", "HERO5 Black")
    assert make == "GoPro"
    assert model == "HERO5-Black"
    assert comb == "GoPro_HERO5-Black"

    # Canon with brand repeated in model
    make, model, comb = parse_camera_generic("Canon", "Canon PowerShot SX60 HS")
    assert make == "Canon"
    assert model == "PowerShot-SX60-HS"
    assert comb == "Canon_PowerShot-SX60-HS"

    # Nikon with corporate noise
    make, model, comb = parse_camera_generic("NIKON CORPORATION", "NIKON D750")
    assert make == "NIKON"
    assert model == "D750"
    assert comb == "NIKON_D750"

    # Sony
    make, model, comb = parse_camera_generic("SONY", "ILCE-7M4")
    assert make == "SONY"
    assert model == "ILCE-7M4"
    assert comb == "SONY_ILCE-7M4"

    # Empty
    make, model, comb = parse_camera_generic("", "")
    assert make == "Cam"
    assert model == "Cam"
    assert comb == "Cam"

def test_format_focal():
    # String from exiftool without -n
    val, f_str = format_focal("17 mm", None)
    assert val == 17.0
    assert f_str == "17mm"

    val, f_str = format_focal("1365.0 mm", None)
    assert val == 1365.0
    assert f_str == "1365mm"

    # Float / Int
    val, f_str = format_focal(50.0, None)
    assert val == 50.0
    assert f_str == "50mm"

    # None
    val, f_str = format_focal(None, None)
    assert val == 0.0
    assert f_str == "0mm"

def test_parse_duration_seconds():
    from src.metadata_extractor import parse_duration_seconds
    # Clock formats
    assert parse_duration_seconds("0:00:41") == 41.0
    assert parse_duration_seconds("0:01:48") == 108.0
    assert parse_duration_seconds("01:23:45") == 5025.0
    assert parse_duration_seconds("0:01:48.50") == 108.5
    assert parse_duration_seconds("1:00") == 60.0

    # Numeric and unit strings
    assert parse_duration_seconds(40.507) == 40.507
    assert parse_duration_seconds("40.5 s") == 40.5
    assert parse_duration_seconds("12s") == 12.0
    assert parse_duration_seconds("12.34") == 12.34

    # None and invalid
    assert parse_duration_seconds(None) is None
    assert parse_duration_seconds("") is None
    assert parse_duration_seconds("invalid") is None

def test_format_duration():
    from src.metadata_extractor import format_duration
    # None or non-positive
    assert format_duration(None) == "00s"
    assert format_duration(0) == "00s"
    assert format_duration(-5) == "00s"

    # Seconds only
    assert format_duration(0.3) == "01s"
    assert format_duration(40.507) == "41s"
    assert format_duration(41.0) == "41s"

    # Minutes and seconds
    assert format_duration(59.8) == "01m00s"
    assert format_duration(60.0) == "01m00s"
    assert format_duration(108.1) == "01m48s"
    assert format_duration(125.0) == "02m05s"

    # Hours
    assert format_duration(3661) == "01h01m01s"
    assert format_duration(7200) == "02h00m00s"

