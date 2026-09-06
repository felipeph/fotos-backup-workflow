import tempfile
from pathlib import Path
from src.metadata_extractor import extract_metadata_batch

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
