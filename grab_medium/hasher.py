"""Pragmatic hashing module for file verification and sync."""

import hashlib
from pathlib import Path
from typing import Union

QUICK_CHUNK_SIZE = 1024 * 1024  # 1 MB


def compute_quick_hash(file_path: Union[str, Path], chunk_size: int = QUICK_CHUNK_SIZE) -> str:
    """Computes a quick hash using file size, first chunk, and last chunk of file."""
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"File '{file_path}' not found.")

    file_size = path.stat().st_size
    hasher = hashlib.sha256()
    hasher.update(str(file_size).encode("utf-8"))

    if file_size <= 2 * chunk_size:
        with open(path, "rb") as f:
            hasher.update(f.read())
    else:
        with open(path, "rb") as f:
            hasher.update(f.read(chunk_size))
            f.seek(file_size - chunk_size)
            hasher.update(f.read(chunk_size))

    return f"q:{hasher.hexdigest()}"


def compute_full_hash(file_path: Union[str, Path], read_chunk_size: int = 64 * 1024) -> str:
    """Computes full SHA-256 hash of entire file content."""
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"File '{file_path}' not found.")

    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(read_chunk_size):
            hasher.update(chunk)

    return f"f:{hasher.hexdigest()}"
