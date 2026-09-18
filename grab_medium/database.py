"""Database management for grab_medium using DuckDB."""

from typing import Optional
import duckdb


class Database:
    """Manages persistent DuckDB connection and schema creation."""

    def __init__(self, db_path: str = "grab_medium.duckdb"):
        self.db_path = db_path
        self._conn: Optional[duckdb.DuckDBPyConnection] = None

    def get_connection(self) -> duckdb.DuckDBPyConnection:
        """Returns the single persistent connection instance."""
        if self._conn is None:
            self._conn = duckdb.connect(self.db_path)
        return self._conn

    def init_schema(self) -> None:
        """Initializes database schema and indexes."""
        conn = self.get_connection()

        conn.execute("CREATE SEQUENCE IF NOT EXISTS seq_media_id START 1;")
        conn.execute("CREATE SEQUENCE IF NOT EXISTS seq_entries_id START 1;")

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS media (
                id BIGINT PRIMARY KEY DEFAULT nextval('seq_media_id'),
                name VARCHAR UNIQUE NOT NULL,
                scanned_at TIMESTAMP NOT NULL
            );
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS entries (
                id BIGINT PRIMARY KEY DEFAULT nextval('seq_entries_id'),
                media_id BIGINT REFERENCES media(id),
                parent_id BIGINT,
                name VARCHAR,
                extension VARCHAR,
                relative_path VARCHAR,
                parent_rel_path VARCHAR,
                is_dir BOOLEAN,
                size_bytes BIGINT,
                created_at TIMESTAMP,
                modified_at TIMESTAMP,
                UNIQUE (media_id, relative_path)
            );
            """
        )

        conn.execute("CREATE INDEX IF NOT EXISTS idx_entries_ext ON entries(extension);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_entries_created ON entries(created_at);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_entries_parent ON entries(parent_id);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_entries_media ON entries(media_id);")

    def media_exists(self, name: str) -> bool:
        """Checks if a media collection name already exists."""
        conn = self.get_connection()
        res = conn.execute("SELECT 1 FROM media WHERE name = ?", [name]).fetchone()
        return res is not None

    def close(self) -> None:
        """Closes the DuckDB connection if open."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None
