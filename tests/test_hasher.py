"""Tests for hashing module in grab_medium.hasher."""

import pytest
from grab_medium.hasher import compute_quick_hash, compute_full_hash


def test_compute_quick_and_full_hash_small_file(tmp_path):
    f = tmp_path / "small.txt"
    f.write_text("Hello World!")

    qh = compute_quick_hash(f)
    fh = compute_full_hash(f)

    assert qh.startswith("q:")
    assert fh.startswith("f:")
    assert len(qh) > 10
    assert len(fh) > 10


def test_compute_quick_hash_large_file(tmp_path):
    f = tmp_path / "large.bin"
    # Create a 3 MB file
    data = b"A" * (3 * 1024 * 1024)
    f.write_bytes(data)

    qh = compute_quick_hash(f)
    fh = compute_full_hash(f)

    assert qh.startswith("q:")
    assert fh.startswith("f:")


def test_hash_missing_file_raises_error(tmp_path):
    f = tmp_path / "missing.txt"

    with pytest.raises(FileNotFoundError):
        compute_quick_hash(f)

    with pytest.raises(FileNotFoundError):
        compute_full_hash(f)
