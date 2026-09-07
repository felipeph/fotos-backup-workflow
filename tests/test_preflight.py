import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch

from src.preflight import scan_source_media, check_preflight, PreflightResult
from src.metadata_extractor import RAW_EXTENSIONS, PHOTO_EXTENSIONS, VIDEO_EXTENSIONS

def test_scan_source_media_with_messy_nested_folder():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)

        # 1. Create non-media files in various nested folders
        (root / "docs").mkdir(parents=True)
        (root / "docs" / "notes.txt").write_bytes(b"x" * 1000)
        (root / "docs" / "spreadsheets").mkdir()
        (root / "docs" / "spreadsheets" / "budget.xlsx").write_bytes(b"x" * 5000)

        (root / "downloads").mkdir()
        (root / "downloads" / "software.zip").write_bytes(b"x" * 100000)
        (root / "downloads" / "installer.exe").write_bytes(b"x" * 200000)

        # Hidden dir and file (should be ignored)
        (root / ".git").mkdir()
        (root / ".git" / "config").write_bytes(b"gitconfig")
        (root / ".DS_Store").write_bytes(b"dsstore")

        # 2. Create valid photos (Standard & RAW) and videos across nested folders
        (root / "nested_a" / "nested_b" / "nested_c").mkdir(parents=True)
        jpg = root / "nested_a" / "nested_b" / "nested_c" / "IMG_0001.JPG"
        jpg.write_bytes(b"x" * 2048)

        cr3 = root / "nested_a" / "IMG_0002.CR3"  # Canon RAW
        cr3.write_bytes(b"x" * 4096)

        arw = root / "docs" / "DSC_0003.ARW"  # Sony RAW inside docs folder!
        arw.write_bytes(b"x" * 8192)

        nef = root / "photos" / "nikon"
        nef.mkdir(parents=True)
        nef_file = nef / "DSC_0004.NEF"  # Nikon RAW
        nef_file.write_bytes(b"x" * 16384)

        dng = root / "photos" / "drone"
        dng.mkdir()
        dng_file = dng / "DJI_0005.DNG"  # DNG RAW
        dng_file.write_bytes(b"x" * 32768)

        mp4 = root / "videos"
        mp4.mkdir()
        mp4_file = mp4 / "GOPR0006.MP4"  # MP4 Video
        mp4_file.write_bytes(b"x" * 65536)

        mov = root / "nested_a" / "nested_b" / "CLIP_0007.MOV"  # QuickTime Video
        mov_file = mov.parent / "CLIP_0007.MOV"
        mov_file.write_bytes(b"x" * 131072)

        # Expected media files: 7 files
        # Expected media bytes: 2048 + 4096 + 8192 + 16384 + 32768 + 65536 + 131072 = 260096
        # Non-media bytes: 1000 + 5000 + 100000 + 200000 = 306000 (ignored!)

        media_files, total_bytes = scan_source_media(root)

        assert len(media_files) == 7
        assert total_bytes == 260096

        file_names = {p.name for p in media_files}
        assert "IMG_0001.JPG" in file_names
        assert "IMG_0002.CR3" in file_names
        assert "DSC_0003.ARW" in file_names
        assert "DSC_0004.NEF" in file_names
        assert "DJI_0005.DNG" in file_names
        assert "GOPR0006.MP4" in file_names
        assert "CLIP_0007.MOV" in file_names

        # Verify non-media files were excluded
        assert "notes.txt" not in file_names
        assert "budget.xlsx" not in file_names
        assert "software.zip" not in file_names
        assert "installer.exe" not in file_names
        assert ".DS_Store" not in file_names
        assert "config" not in file_names

def test_raw_extensions_coverage():
    assert ".cr2" in RAW_EXTENSIONS
    assert ".cr3" in RAW_EXTENSIONS
    assert ".arw" in RAW_EXTENSIONS
    assert ".nef" in RAW_EXTENSIONS
    assert ".raf" in RAW_EXTENSIONS
    assert ".rw2" in RAW_EXTENSIONS
    assert ".orf" in RAW_EXTENSIONS
    assert ".dng" in RAW_EXTENSIONS
    assert ".gpr" in RAW_EXTENSIONS

    for ext in RAW_EXTENSIONS:
        assert ext in PHOTO_EXTENSIONS

def test_check_preflight_with_source_space_ok():
    with tempfile.TemporaryDirectory() as td:
        dest = Path(td) / "dest"
        source = Path(td) / "source"
        dest.mkdir()
        source.mkdir()

        # 5 MB of photos
        (source / "pic1.jpg").write_bytes(b"x" * (2 * 1024 * 1024))
        (source / "pic2.cr3").write_bytes(b"x" * (3 * 1024 * 1024))
        # 50 MB of non-media junk (should NOT count)
        (source / "archive.zip").write_bytes(b"x" * (50 * 1024 * 1024))

        pf = check_preflight(destination_root=dest, source_path=source)

        assert pf.destination_writable is True
        assert pf.source_media_count == 2
        assert pf.source_media_bytes == 5 * 1024 * 1024
        # Destination on standard OS temp dir has multiple GBs free
        assert pf.has_enough_space is True
        assert pf.space_warning == ""

def test_check_preflight_insufficient_space_mock():
    with tempfile.TemporaryDirectory() as td:
        dest = Path(td) / "dest"
        source = Path(td) / "source"
        dest.mkdir()
        source.mkdir()

        (source / "video.mp4").write_bytes(b"x" * (10 * 1024 * 1024))

        # Mock shutil.disk_usage to simulate only 1MB free disk space
        with patch("shutil.disk_usage") as mock_usage:
            # total, used, free
            mock_usage.return_value = (100 * 1024 ** 3, 99 * 1024 ** 3, 1024 * 1024)
            pf = check_preflight(destination_root=dest, source_path=source)

            assert pf.source_media_count == 1
            assert pf.has_enough_space is False
            assert "Espaço insuficiente" in pf.space_warning
            assert pf.all_ok is False

def test_check_preflight_nonexistent_source():
    with tempfile.TemporaryDirectory() as td:
        dest = Path(td) / "dest"
        dest.mkdir()
        fake_source = Path(td) / "nao_existe"

        pf = check_preflight(destination_root=dest, source_path=fake_source)
        assert pf.has_enough_space is False
        assert "não encontrada" in pf.space_warning
