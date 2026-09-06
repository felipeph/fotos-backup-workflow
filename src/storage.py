import hashlib
import shutil
import os
import sys
from pathlib import Path
from dataclasses import dataclass

@dataclass
class TransferResult:
    source_path: Path
    target_path: Path
    status: str  # "copied", "skipped_duplicate", "error"
    file_size_bytes: int
    sha256: str
    error_message: str = ""

def compute_sha256(path: Path, block_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(block_size):
            h.update(chunk)
    return h.hexdigest()

def safe_copy_file(src: Path, dest_dir: Path, target_filename: str) -> TransferResult:
    """
    Safely copies a file to dest_dir / target_filename verifying SHA-256.
    Avoids overwriting files. If an identical file already exists, it is skipped.
    If a different file exists with the same name, a collision rename is applied.
    Source file is NEVER deleted.
    """
    try:
        dest_dir.mkdir(parents=True, exist_ok=True)
        src_size = src.stat().st_size
        target = dest_dir / target_filename

        # If file exists, check hash
        if target.exists():
            if target.stat().st_size == src_size:
                src_hash = compute_sha256(src)
                dest_hash = compute_sha256(target)
                if src_hash == dest_hash:
                    return TransferResult(
                        source_path=src,
                        target_path=target,
                        status="skipped_duplicate",
                        file_size_bytes=src_size,
                        sha256=src_hash,
                    )

            # Collision: different file exists
            idx = 1
            stem = target.stem
            ext = target.suffix
            while target.exists():
                target = dest_dir / f"{stem} ({idx}){ext}"
                idx += 1

        src_hash = compute_sha256(src)
        temp_target = dest_dir / f".tmp_{target.name}"
        shutil.copy2(src, temp_target)

        # Verify integrity
        temp_hash = compute_sha256(temp_target)
        if src_hash != temp_hash:
            temp_target.unlink(missing_ok=True)
            return TransferResult(
                source_path=src,
                target_path=target,
                status="error",
                file_size_bytes=src_size,
                sha256=src_hash,
                error_message=f"Falha de integridade SHA-256: {src_hash} != {temp_hash}"
            )

        # Atomically rename
        if target.exists():
            target.unlink()
        temp_target.rename(target)

        return TransferResult(
            source_path=src,
            target_path=target,
            status="copied",
            file_size_bytes=src_size,
            sha256=src_hash,
        )

    except Exception as e:
        return TransferResult(
            source_path=src,
            target_path=dest_dir / target_filename,
            status="error",
            file_size_bytes=0,
            sha256="",
            error_message=str(e),
        )
