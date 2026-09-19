"""Tests for InvestigateDB query engine."""

import pytest
from grab_medium.database import Database
from grab_medium.investigate_db import InvestigateDB


@pytest.fixture
def db_with_data(tmp_path):
    db_file = str(tmp_path / "test.duckdb")
    db = Database(db_file)
    db.init_schema()
    conn = db.get_connection()

    conn.execute(
        "INSERT INTO media (id, name, scanned_at) VALUES (1, 'vacation_2023', '2023-08-01 10:00:00')"
    )
    conn.execute(
        "INSERT INTO media (id, name, scanned_at) VALUES (2, 'work_docs', '2023-09-01 12:00:00')"
    )

    conn.execute(
        """
        INSERT INTO entries (id, media_id, parent_id, name, extension, relative_path, is_dir, size_bytes, created_at, modified_at)
        VALUES
        (10, 1, NULL, 'vacation_2023', NULL, 'vacation_2023', TRUE, 0, '2023-08-01 10:00:00', '2023-08-01 10:00:00'),
        (11, 1, 10, 'photos', NULL, 'vacation_2023/photos', TRUE, 0, '2023-08-01 10:00:00', '2023-08-01 10:00:00'),
        (12, 1, 11, 'beach.jpg', 'jpg', 'vacation_2023/photos/beach.jpg', FALSE, 2048576, '2023-08-01 10:00:00', '2023-08-01 10:00:00'),
        (13, 1, 11, 'sunset.PNG', 'PNG', 'vacation_2023/photos/sunset.PNG', FALSE, 4096000, '2023-08-01 10:00:00', '2023-08-01 10:00:00'),
        (14, 1, 10, 'notes.txt', 'txt', 'vacation_2023/notes.txt', FALSE, 512, '2023-08-01 10:00:00', '2023-08-01 10:00:00'),
        (20, 2, NULL, 'work_docs', NULL, 'work_docs', TRUE, 0, '2023-09-01 12:00:00', '2023-09-01 12:00:00'),
        (21, 2, 20, 'report.pdf', 'pdf', 'work_docs/report.pdf', FALSE, 102400, '2023-09-01 12:00:00', '2023-09-01 12:00:00')
        """
    )
    yield db
    db.close()


def test_resolve_media_id(db_with_data):
    inv_db = InvestigateDB(db_with_data)
    assert inv_db.resolve_media_id("vacation_2023") == 1
    assert inv_db.resolve_media_id("1") == 1
    assert inv_db.resolve_media_id(1) == 1
    assert inv_db.resolve_media_id("work_docs") == 2

    with pytest.raises(ValueError, match="Media 'non_existent' not found"):
        inv_db.resolve_media_id("non_existent")


def test_get_schema_info(db_with_data):
    inv_db = InvestigateDB(db_with_data)
    info = inv_db.get_schema_info()
    tables = {row["table_name"] for row in info}
    assert "media" in tables
    assert "entries" in tables
    assert "notes" in tables


def test_list_media(db_with_data):
    inv_db = InvestigateDB(db_with_data)
    media = inv_db.list_media()
    assert len(media) == 2
    names = [m["name"] for m in media]
    assert "vacation_2023" in names
    assert "work_docs" in names


def test_add_and_list_notes(db_with_data):
    inv_db = InvestigateDB(db_with_data)
    note_id = inv_db.add_note(target_type="directory", target_id=11, content="Photos directory note")
    assert note_id > 0

    notes = inv_db.list_notes(target_type="directory", target_id=11)
    assert len(notes) == 1
    assert notes[0]["content"] == "Photos directory note"
    assert notes[0]["source"] == "manual"


def test_search_content_with_notes(db_with_data):
    inv_db = InvestigateDB(db_with_data)
    inv_db.add_note(target_type="file", target_id=12, content="Sunny day at Paradise beach")

    results = inv_db.search_content("Paradise")
    assert len(results) == 1
    assert results[0]["name"] == "beach.jpg"
    assert results[0]["note_content"] == "Sunny day at Paradise beach"


def test_search_file_type(db_with_data):
    inv_db = InvestigateDB(db_with_data)
    results_jpg = inv_db.search_file_type("vacation_2023", "jpg")
    assert len(results_jpg) == 1
    assert results_jpg[0]["name"] == "beach.jpg"

    results_png = inv_db.search_file_type(1, ".png")
    assert len(results_png) == 1
    assert results_png[0]["name"] == "sunset.PNG"


def test_execute_query(db_with_data):
    inv_db = InvestigateDB(db_with_data)
    cols, rows = inv_db.execute_query("SELECT id, name FROM media ORDER BY id")
    assert cols == ["id", "name"]
    assert len(rows) == 2
    assert rows[0] == (1, "vacation_2023")
    assert rows[1] == (2, "work_docs")
