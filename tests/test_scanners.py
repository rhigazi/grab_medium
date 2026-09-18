import os
import subprocess
from pathlib import Path

BASH_SCANNER = Path(__file__).parent.parent / "grab_medium" / "scanners" / "bash_scanner.sh"


def test_bash_scanner_basic(tmp_path):
    sub_dir = tmp_path / "subdir"
    sub_dir.mkdir()
    file1 = tmp_path / "file1.txt"
    file1.write_text("hello")
    file2 = sub_dir / "file2.JPG"
    file2.write_text("world")

    res = subprocess.run(
        [str(BASH_SCANNER), str(tmp_path), "42"],
        capture_output=True,
        text=True,
        check=True
    )

    lines = [line for line in res.stdout.strip().split("\n") if line]
    assert len(lines) == 3

    parsed = [line.split("\x1f") for line in lines]
    records = {r[3]: r for r in parsed}

    assert "subdir" in records
    assert records["subdir"][0] == "42"
    assert records["subdir"][1] == "subdir"
    assert records["subdir"][2] == ""
    assert records["subdir"][4] == ""
    assert records["subdir"][5] == "true"

    assert "file1.txt" in records
    assert records["file1.txt"][1] == "file1.txt"
    assert records["file1.txt"][2] == "txt"
    assert records["file1.txt"][4] == ""
    assert records["file1.txt"][5] == "false"
    assert records["file1.txt"][6] == "5"

    assert "subdir/file2.JPG" in records
    assert records["subdir/file2.JPG"][1] == "file2.JPG"
    assert records["subdir/file2.JPG"][2] == "jpg"
    assert records["subdir/file2.JPG"][4] == "subdir"
    assert records["subdir/file2.JPG"][5] == "false"


def test_bash_scanner_special_characters(tmp_path):
    special_dir = tmp_path / "dir with spaces, and commas"
    special_dir.mkdir()
    special_file = special_dir / "file, with space.mp4"
    special_file.write_bytes(b"123456789")

    res = subprocess.run(
        [str(BASH_SCANNER), str(tmp_path), "10"],
        capture_output=True,
        text=True,
        check=True
    )

    lines = [line for line in res.stdout.strip().split("\n") if line]
    parsed = [line.split("\x1f") for line in lines]
    records = {r[3]: r for r in parsed}

    rel_dir = "dir with spaces, and commas"
    rel_file = "dir with spaces, and commas/file, with space.mp4"

    assert rel_dir in records
    assert records[rel_dir][1] == "dir with spaces, and commas"

    assert rel_file in records
    assert records[rel_file][1] == "file, with space.mp4"
    assert records[rel_file][2] == "mp4"
    assert records[rel_file][4] == rel_dir
    assert records[rel_file][6] == "9"


def test_bash_scanner_ignores_symlinks(tmp_path):
    real_file = tmp_path / "real.txt"
    real_file.write_text("data")
    symlink_file = tmp_path / "link.txt"
    try:
        os.symlink(real_file, symlink_file)
    except OSError:
        pass

    res = subprocess.run(
        [str(BASH_SCANNER), str(tmp_path), "1"],
        capture_output=True,
        text=True,
        check=True
    )

    lines = [line for line in res.stdout.strip().split("\n") if line]
    parsed = [line.split("\x1f") for line in lines]
    rel_paths = [r[3] for r in parsed]

    assert "real.txt" in rel_paths
    assert "link.txt" not in rel_paths
