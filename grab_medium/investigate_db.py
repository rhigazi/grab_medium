"""Query engine and database interaction module for InvestigateMedia."""

from typing import Any, Dict, List, Optional, Tuple, Union
from grab_medium.database import Database


class InvestigateDB:
    """Provides querying capabilities for media and entries stored in DuckDB."""

    def __init__(self, db: Database):
        self.db = db

    def resolve_media_id(self, medium: Union[str, int]) -> int:
        """Resolves medium parameter (name or numeric ID) to a numeric media_id."""
        conn = self.db.get_connection()

        if isinstance(medium, int) or (isinstance(medium, str) and medium.isdigit()):
            m_id = int(medium)
            res = conn.execute("SELECT id FROM media WHERE id = ?", [m_id]).fetchone()
            if res:
                return res[0]

        res = conn.execute("SELECT id FROM media WHERE name = ?", [str(medium)]).fetchone()
        if res:
            return res[0]

        raise ValueError(f"Media '{medium}' not found in database.")

    def get_schema_info(self) -> List[Dict[str, Any]]:
        """Returns database schema information including tables, column names, and data types."""
        conn = self.db.get_connection()
        query = """
            SELECT table_name, column_name, data_type
            FROM information_schema.columns
            WHERE table_schema = 'main'
            ORDER BY table_name, ordinal_position;
        """
        res = conn.execute(query).fetchall()
        return [
            {"table_name": row[0], "column_name": row[1], "data_type": row[2]}
            for row in res
        ]

    def list_media(self) -> List[Dict[str, Any]]:
        """Returns a list of all recorded media collections."""
        conn = self.db.get_connection()
        query = "SELECT id, name, scanned_at FROM media ORDER BY id ASC;"
        res = conn.execute(query).fetchall()
        return [
            {"id": row[0], "name": row[1], "scanned_at": str(row[2])}
            for row in res
        ]

    def search_content(self, text: str) -> List[Dict[str, Any]]:
        """Searches for text in entry names, relative paths, or notes content using case-insensitive matching."""
        conn = self.db.get_connection()
        query = """
            SELECT DISTINCT e.id, m.name AS media_name, e.relative_path, e.name, e.is_dir, e.size_bytes, n.content AS note_content
            FROM entries e
            JOIN media m ON e.media_id = m.id
            LEFT JOIN notes n ON (
                (n.target_type = 'file' AND n.target_id = e.id) OR
                (n.target_type = 'directory' AND n.target_id = e.id) OR
                (n.target_type = 'collection' AND n.target_id = m.id)
            )
            WHERE e.name ILIKE ? OR e.relative_path ILIKE ? OR n.content ILIKE ?
            ORDER BY e.media_id, e.relative_path;
        """
        pattern = f"%{text}%"
        res = conn.execute(query, [pattern, pattern, pattern]).fetchall()
        return [
            {
                "id": row[0],
                "media_name": row[1],
                "relative_path": row[2],
                "name": row[3],
                "is_dir": row[4],
                "size_bytes": row[5],
                "note_content": row[6],
            }
            for row in res
        ]

    def search_file_type(self, medium: Union[str, int], extension: str) -> List[Dict[str, Any]]:
        """Filters files in a given medium by extension (case-insensitive)."""
        media_id = self.resolve_media_id(medium)
        ext_clean = extension.lstrip(".").lower()

        conn = self.db.get_connection()
        query = """
            SELECT id, name, relative_path, size_bytes, created_at, modified_at
            FROM entries
            WHERE media_id = ? AND LOWER(extension) = ?
            ORDER BY relative_path;
        """
        res = conn.execute(query, [media_id, ext_clean]).fetchall()
        return [
            {
                "id": row[0],
                "name": row[1],
                "relative_path": row[2],
                "size_bytes": row[3],
                "created_at": str(row[4]) if row[4] else None,
                "modified_at": str(row[5]) if row[5] else None,
            }
            for row in res
        ]

    def add_note(
        self,
        target_type: str,
        target_id: int,
        content: str,
        source: str = "manual",
    ) -> int:
        """Adds a note for a collection, directory, or file target."""
        target_type = target_type.lower()
        if target_type not in ("collection", "directory", "file"):
            raise ValueError(f"Invalid target_type '{target_type}'. Must be 'collection', 'directory', or 'file'.")

        conn = self.db.get_connection()

        if target_type == "collection":
            res = conn.execute("SELECT 1 FROM media WHERE id = ?", [target_id]).fetchone()
            if not res:
                raise ValueError(f"Media collection with id {target_id} not found.")
        elif target_type == "directory":
            res = conn.execute("SELECT 1 FROM entries WHERE id = ? AND is_dir = TRUE", [target_id]).fetchone()
            if not res:
                raise ValueError(f"Directory entry with id {target_id} not found.")
        elif target_type == "file":
            res = conn.execute("SELECT 1 FROM entries WHERE id = ? AND is_dir = FALSE", [target_id]).fetchone()
            if not res:
                raise ValueError(f"File entry with id {target_id} not found.")

        row = conn.execute(
            """
            INSERT INTO notes (target_type, target_id, source, content, created_at)
            VALUES (?, ?, ?, ?, NOW()) RETURNING id
            """,
            [target_type, target_id, source, content],
        ).fetchone()

        assert row is not None
        return row[0]

    def list_notes(
        self,
        target_type: Optional[str] = None,
        target_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Lists notes, optionally filtered by target_type and target_id."""
        conn = self.db.get_connection()
        query = "SELECT id, target_type, target_id, source, content, created_at FROM notes"
        params: List[Any] = []
        conditions: List[str] = []

        if target_type:
            conditions.append("target_type = ?")
            params.append(target_type.lower())
        if target_id is not None:
            conditions.append("target_id = ?")
            params.append(target_id)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY id ASC;"

        res = conn.execute(query, params).fetchall()
        return [
            {
                "id": row[0],
                "target_type": row[1],
                "target_id": row[2],
                "source": row[3],
                "content": row[4],
                "created_at": str(row[5]),
            }
            for row in res
        ]

    def execute_query(self, sql: str) -> Tuple[List[str], List[Tuple[Any, ...]]]:
        """Executes direct SQL query and returns column names and result rows."""
        conn = self.db.get_connection()
        cur = conn.execute(sql)
        description = cur.description
        columns = [col[0] for col in description] if description else []
        rows = cur.fetchall()
        return columns, rows
