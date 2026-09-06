from pathlib import Path
import tempfile
import os
from src.storage import safe_copy_file, compute_sha256

def test_safe_copy_and_deduplication():
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        src_file = tmp_path / "original.jpg"
        src_file.write_bytes(b"sample photo content 12345")

        dest_dir = tmp_path / "dest"

        # 1. First copy
        res1 = safe_copy_file(src_file, dest_dir, "target.jpg")
        assert res1.status == "copied"
        assert (dest_dir / "target.jpg").exists()
        assert compute_sha256(src_file) == compute_sha256(dest_dir / "target.jpg")

        # 2. Duplicate copy
        res2 = safe_copy_file(src_file, dest_dir, "target.jpg")
        assert res2.status == "skipped_duplicate"

        # 3. Collision with different content
        different_src = tmp_path / "different.jpg"
        different_src.write_bytes(b"completely different image content")

        res3 = safe_copy_file(different_src, dest_dir, "target.jpg")
        assert res3.status == "copied"
        # Should have saved as target (1).jpg
        assert (dest_dir / "target (1).jpg").exists()
        assert compute_sha256(different_src) == compute_sha256(dest_dir / "target (1).jpg")
