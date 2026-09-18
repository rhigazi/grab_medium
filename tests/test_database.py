import pytest
from grab_medium.database import Database


def test_database_init_and_schema(tmp_path):
    db_file = str(tmp_path / "test.duckdb")
    db = Database(db_file)
    db.init_schema()

    conn = db.get_connection()

    # Check tables existence
    tables = [r[0] for r in conn.execute("SHOW TABLES").fetchall()]
    assert "media" in tables
    assert "entries" in tables

    db.close()


def test_database_single_connection_policy(tmp_path):
    db_file = str(tmp_path / "test.duckdb")
    db = Database(db_file)
    conn1 = db.get_connection()
    conn2 = db.get_connection()

    assert conn1 is conn2
    db.close()


def test_media_exists_check(tmp_path):
    db_file = str(tmp_path / "test.duckdb")
    db = Database(db_file)
    db.init_schema()

    assert not db.media_exists("test_media")

    conn = db.get_connection()
    conn.execute("INSERT INTO media (name, scanned_at) VALUES ('test_media', NOW())")

    assert db.media_exists("test_media")
    db.close()
