"""Query engine and database interaction module for InvestigateMedia."""

from typing import Any, Dict, List, Tuple, Union
from grab_medium.database import Database


class InvestigateDB:
    """Provides querying capabilities for media and entries stored in DuckDB."""

    def __init__(self, db: Database):
        self.db = db

    def resolve_media_id(self, medium: Union[str, int]) -> int:
        """Resolves medium parameter (name or numeric ID) to a numeric media_id."""
        conn = self.db.get_connection()

        # If medium looks like an integer or is an integer
        if isinstance(medium, int) or (isinstance(medium, str) and medium.isdigit()):
            m_id = int(medium)
            res = conn.execute("SELECT id FROM media WHERE id = ?", [m_id]).fetchone()
            if res:
                return res[0]

        # Otherwise try searching by name
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
        """Searches for text in entry names or relative paths using case-insensitive matching."""
        conn = self.db.get_connection()
        query = """
            SELECT e.id, m.name AS media_name, e.relative_path, e.name, e.is_dir, e.size_bytes
            FROM entries e
            JOIN media m ON e.media_id = m.id
            WHERE e.name ILIKE ? OR e.relative_path ILIKE ?
            ORDER BY e.media_id, e.relative_path;
        """
        pattern = f"%{text}%"
        res = conn.execute(query, [pattern, pattern]).fetchall()
        return [
            {
                "id": row[0],
                "media_name": row[1],
                "relative_path": row[2],
                "name": row[3],
                "is_dir": row[4],
                "size_bytes": row[5],
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

    def execute_query(self, sql: str) -> Tuple[List[str], List[Tuple[Any, ...]]]:
        """Executes direct SQL query and returns column names and result rows."""
        conn = self.db.get_connection()
        cur = conn.execute(sql)
        description = cur.description
        columns = [col[0] for col in description] if description else []
        rows = cur.fetchall()
        return columns, rows
