"""Tests for orchestrator sync and dry-run functionality."""

import pytest
from pathlib import Path
from grab_medium.database import Database
from grab_medium.orchestrator import Orchestrator


def test_orchestrator_sync_detect_moved_file(tmp_path):
    scan_root = tmp_path / "media_root"
    scan_root.mkdir()

    sub1 = scan_root / "dir1"
    sub1.mkdir()
    sub2 = scan_root / "dir2"
    sub2.mkdir()

    f1 = sub1 / "data.bin"
    f1.write_bytes(b"UNIQUE_FILE_CONTENT_12345")

    db_path = str(tmp_path / "test_sync.duckdb")
    db = Database(db_path)
    orchestrator = Orchestrator(db)

    # Initial scan
    m_id = orchestrator.run_scan("sync_test", str(scan_root))
    conn = db.get_connection()

    initial_entries = conn.execute("SELECT id, relative_path FROM entries WHERE is_dir = FALSE").fetchall()
    assert len(initial_entries) == 1
    file_id = initial_entries[0][0]
    assert initial_entries[0][1] == "dir1/data.bin"

    # Attach note to the file
    conn.execute(
        "INSERT INTO notes (target_type, target_id, source, content) VALUES ('file', ?, 'manual', 'Note on file')",
        [file_id],
    )

    # MOVE file from dir1 to dir2
    f1.unlink()
    f2 = sub2 / "data_moved.bin"
    f2.write_bytes(b"UNIQUE_FILE_CONTENT_12345")

    # Dry-run sync
    stats = orchestrator.run_scan("sync_test", str(scan_root), sync=True, dry_run=True)
    assert isinstance(stats, dict)
    assert stats["moved"] == 1

    # Actual sync
    res_id = orchestrator.run_scan("sync_test", str(scan_root), sync=True, dry_run=False)
    assert res_id == m_id

    updated_entries = conn.execute("SELECT id, relative_path FROM entries WHERE is_dir = FALSE").fetchall()
    assert len(updated_entries) == 1
    assert updated_entries[0][0] == file_id  # ID preserved on MOVE!
    assert updated_entries[0][1] == "dir2/data_moved.bin"

    # Verify note is still attached to preserved file_id
    notes = conn.execute("SELECT content FROM notes WHERE target_type = 'file' AND target_id = ?", [file_id]).fetchall()
    assert len(notes) == 1
    assert notes[0][0] == "Note on file"

    db.close()


def test_orchestrator_sync_detect_deleted_file_and_notes_cleanup(tmp_path):
    scan_root = tmp_path / "media_root"
    scan_root.mkdir()

    f1 = scan_root / "temp.txt"
    f1.write_text("temporary file")

    db_path = str(tmp_path / "test_del.duckdb")
    db = Database(db_path)
    orchestrator = Orchestrator(db)

    m_id = orchestrator.run_scan("del_test", str(scan_root))
    conn = db.get_connection()

    file_entry = conn.execute("SELECT id FROM entries WHERE relative_path = 'temp.txt'").fetchone()
    assert file_entry is not None
    file_id = file_entry[0]

    # Attach note to file
    conn.execute(
        "INSERT INTO notes (target_type, target_id, source, content) VALUES ('file', ?, 'manual', 'Deleting soon')",
        [file_id],
    )

    # Delete file from disk
    f1.unlink()

    # Sync
    stats = orchestrator.run_scan("del_test", str(scan_root), sync=True, dry_run=False)
    assert stats == m_id

    # Verify file entry deleted
    entry_after = conn.execute("SELECT 1 FROM entries WHERE id = ?", [file_id]).fetchone()
    assert entry_after is None

    # Verify associated note deleted
    note_after = conn.execute("SELECT 1 FROM notes WHERE target_type = 'file' AND target_id = ?", [file_id]).fetchone()
    assert note_after is None

    db.close()
