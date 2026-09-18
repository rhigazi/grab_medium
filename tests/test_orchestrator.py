import pytest
from pathlib import Path
from grab_medium.database import Database
from grab_medium.orchestrator import Orchestrator


def test_orchestrator_full_scan(tmp_path):
    scan_root = tmp_path / "scan_target"
    scan_root.mkdir()

    sub_dir = scan_root / "photos"
    sub_dir.mkdir()
    deep_dir = sub_dir / "2024"
    deep_dir.mkdir()

    file1 = scan_root / "root.txt"
    file1.write_text("root file")

    file2 = sub_dir / "photo.jpg"
    file2.write_bytes(b"photo bytes")

    file3 = deep_dir / "sunset.png"
    file3.write_bytes(b"sunset bytes")

    db_path = str(tmp_path / "test_orchestrator.duckdb")
    log_path = str(tmp_path / "errors.log")

    db = Database(db_path)
    orchestrator = Orchestrator(db, log_path=log_path)

    media_id = orchestrator.run_scan(name="my_media", target_path=str(scan_root))
    assert media_id > 0

    conn = db.get_connection()

    # Check media table
    media_rows = conn.execute("SELECT id, name FROM media").fetchall()
    assert len(media_rows) == 1
    assert media_rows[0][0] == media_id
    assert media_rows[0][1] == "my_media"

    # Check entries count
    entries = conn.execute(
        "SELECT id, parent_id, name, relative_path, parent_rel_path, is_dir FROM entries WHERE media_id = ?",
        [media_id]
    ).fetchall()
    assert len(entries) == 5

    by_path = {r[3]: r for r in entries}

    # Verify parent_rel_path is cleaned up (NULL) for all
    for r in entries:
        assert r[4] is None

    photos_id = by_path["photos"][0]
    assert by_path["photos"][1] is None
    assert by_path["root.txt"][1] is None

    deep_dir_id = by_path["photos/2024"][0]
    assert by_path["photos/2024"][1] == photos_id
    assert by_path["photos/photo.jpg"][1] == photos_id

    assert by_path["photos/2024/sunset.png"][1] == deep_dir_id

    db.close()


def test_orchestrator_duplicate_media_name(tmp_path):
    scan_root = tmp_path / "target"
    scan_root.mkdir()

    db_path = str(tmp_path / "test_dup.duckdb")
    db = Database(db_path)
    orchestrator = Orchestrator(db)

    orchestrator.run_scan(name="dup_test", target_path=str(scan_root))

    with pytest.raises(ValueError, match="already exists"):
        orchestrator.run_scan(name="dup_test", target_path=str(scan_root))

    db.close()


def test_orchestrator_invalid_path(tmp_path):
    db_path = str(tmp_path / "test_invalid.duckdb")
    db = Database(db_path)
    orchestrator = Orchestrator(db)

    with pytest.raises(ValueError, match="not a valid directory"):
        orchestrator.run_scan(name="invalid_test", target_path=str(tmp_path / "nonexistent"))

    db.close()


def test_orchestrator_error_log_file_created(tmp_path):
    scan_root = tmp_path / "target"
    scan_root.mkdir()
    (scan_root / "a.txt").write_text("content")

    db_path = str(tmp_path / "test_log.duckdb")
    log_path = str(tmp_path / "errors.log")

    db = Database(db_path)
    orchestrator = Orchestrator(db, log_path=log_path)

    orchestrator.run_scan(name="log_test", target_path=str(scan_root))

    assert Path(log_path).exists()
    db.close()
