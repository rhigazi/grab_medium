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


def test_quick_hash_collision_full_hash_differs(tmp_path):
    # Two files with identical size (3MB), identical 1MB prefix, identical 1MB suffix,
    # but differing middle 1MB chunk.
    chunk1 = b"A" * (1024 * 1024)
    chunk2_f1 = b"B" * (1024 * 1024)
    chunk2_f2 = b"C" * (1024 * 1024)
    chunk3 = b"D" * (1024 * 1024)

    f1 = tmp_path / "file1.bin"
    f2 = tmp_path / "file2.bin"

    f1.write_bytes(chunk1 + chunk2_f1 + chunk3)
    f2.write_bytes(chunk1 + chunk2_f2 + chunk3)

    qh1 = compute_quick_hash(f1)
    qh2 = compute_quick_hash(f2)

    # Quick hashes are identical because file size, first chunk, and last chunk are identical
    assert qh1 == qh2

    # Full hashes differ because middle chunk is different
    fh1 = compute_full_hash(f1)
    fh2 = compute_full_hash(f2)

    assert fh1 != fh2
