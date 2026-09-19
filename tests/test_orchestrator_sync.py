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


def test_orchestrator_sync_move_path_similarity(tmp_path):
    scan_root = tmp_path / "media_root"
    scan_root.mkdir()

    d1 = scan_root / "album_a"
    d1.mkdir()
    d2 = scan_root / "album_b"
    d2.mkdir()

    f1 = d1 / "photo.jpg"
    f2 = d2 / "photo.jpg"

    content = b"IDENTICAL_PHOTO_DATA_999"
    f1.write_bytes(content)
    f2.write_bytes(content)

    db_path = str(tmp_path / "test_sim.duckdb")
    db = Database(db_path)
    orchestrator = Orchestrator(db)

    m_id = orchestrator.run_scan("similarity_test", str(scan_root))
    conn = db.get_connection()

    # Rename photo.jpg in album_a to photo_renamed.jpg in album_a
    f1.unlink()
    f1_renamed = d1 / "photo_renamed.jpg"
    f1_renamed.write_bytes(content)

    id_album_a = conn.execute("SELECT id FROM entries WHERE relative_path = 'album_a/photo.jpg'").fetchone()[0]
    id_album_b = conn.execute("SELECT id FROM entries WHERE relative_path = 'album_b/photo.jpg'").fetchone()[0]

    # Sync
    res_id = orchestrator.run_scan("similarity_test", str(scan_root), sync=True, dry_run=False)
    assert res_id == m_id

    # The entry in album_a should be updated to photo_renamed.jpg because of parent folder similarity
    updated_a = conn.execute("SELECT relative_path FROM entries WHERE id = ?", [id_album_a]).fetchone()[0]
    assert updated_a == "album_a/photo_renamed.jpg"

    # album_b/photo.jpg should remain untouched
    updated_b = conn.execute("SELECT relative_path FROM entries WHERE id = ?", [id_album_b]).fetchone()[0]
    assert updated_b == "album_b/photo.jpg"

    db.close()


def test_orchestrator_sync_deleted_directory_cascading_notes(tmp_path):
    scan_root = tmp_path / "media_root"
    scan_root.mkdir()

    parent_dir = scan_root / "parent"
    parent_dir.mkdir()
    sub_dir = parent_dir / "sub"
    sub_dir.mkdir()

    f1 = sub_dir / "item.txt"
    f1.write_text("item content")

    db_path = str(tmp_path / "test_dir_del.duckdb")
    db = Database(db_path)
    orchestrator = Orchestrator(db)

    m_id = orchestrator.run_scan("dir_del_test", str(scan_root))
    conn = db.get_connection()

    p_id = conn.execute("SELECT id FROM entries WHERE relative_path = 'parent'").fetchone()[0]
    s_id = conn.execute("SELECT id FROM entries WHERE relative_path = 'parent/sub'").fetchone()[0]
    f_id = conn.execute("SELECT id FROM entries WHERE relative_path = 'parent/sub/item.txt'").fetchone()[0]

    # Attach notes to parent_dir, sub_dir, and file
    conn.execute("INSERT INTO notes (target_type, target_id, source, content) VALUES ('directory', ?, 'manual', 'Note parent')", [p_id])
    conn.execute("INSERT INTO notes (target_type, target_id, source, content) VALUES ('directory', ?, 'manual', 'Note sub')", [s_id])
    conn.execute("INSERT INTO notes (target_type, target_id, source, content) VALUES ('file', ?, 'manual', 'Note file')", [f_id])

    # Remove parent_dir from disk
    f1.unlink()
    sub_dir.rmdir()
    parent_dir.rmdir()

    # Sync
    res_id = orchestrator.run_scan("dir_del_test", str(scan_root), sync=True, dry_run=False)
    assert res_id == m_id

    # Verify directory entries deleted
    entries_rem = conn.execute("SELECT count(*) FROM entries WHERE media_id = ?", [m_id]).fetchone()[0]
    assert entries_rem == 0

    # Verify notes deleted
    notes_rem = conn.execute("SELECT count(*) FROM notes").fetchone()[0]
    assert notes_rem == 0

    db.close()


def test_orchestrator_sync_hierarchy_re_resolution(tmp_path):
    scan_root = tmp_path / "media_root"
    scan_root.mkdir()

    f1 = scan_root / "root_file.txt"
    f1.write_text("root content")

    db_path = str(tmp_path / "test_hierarchy.duckdb")
    db = Database(db_path)
    orchestrator = Orchestrator(db)

    m_id = orchestrator.run_scan("hierarchy_test", str(scan_root))
    conn = db.get_connection()

    # Add a new directory and new file inside it
    new_dir = scan_root / "new_folder"
    new_dir.mkdir()
    f2 = new_dir / "nested_file.txt"
    f2.write_text("nested content")

    # Sync
    res_id = orchestrator.run_scan("hierarchy_test", str(scan_root), sync=True, dry_run=False)
    assert res_id == m_id

    dir_id = conn.execute("SELECT id FROM entries WHERE relative_path = 'new_folder'").fetchone()[0]
    file_id, parent_id = conn.execute("SELECT id, parent_id FROM entries WHERE relative_path = 'new_folder/nested_file.txt'").fetchone()

    assert parent_id == dir_id

    db.close()


def test_orchestrator_sync_move_file_to_root(tmp_path):
    scan_root = tmp_path / "media_root"
    scan_root.mkdir()

    sub = scan_root / "subfolder"
    sub.mkdir()
    f = sub / "move_me.txt"
    f.write_text("root move test content")

    db_path = str(tmp_path / "test_root_move.duckdb")
    db = Database(db_path)
    orchestrator = Orchestrator(db)

    m_id = orchestrator.run_scan("root_move_test", str(scan_root))
    conn = db.get_connection()

    file_id, initial_parent_id = conn.execute(
        "SELECT id, parent_id FROM entries WHERE relative_path = 'subfolder/move_me.txt'"
    ).fetchone()
    assert initial_parent_id is not None

    # Move file from subfolder to root
    f.unlink()
    root_f = scan_root / "move_me.txt"
    root_f.write_text("root move test content")

    # Sync
    res_id = orchestrator.run_scan("root_move_test", str(scan_root), sync=True, dry_run=False)
    assert res_id == m_id

    updated_file_id, updated_parent_id, updated_rel_path = conn.execute(
        "SELECT id, parent_id, relative_path FROM entries WHERE id = ?", [file_id]
    ).fetchone()

    assert updated_file_id == file_id
    assert updated_rel_path == "move_me.txt"
    assert updated_parent_id is None  # parent_id cleared to NULL when moved to root!

    db.close()
