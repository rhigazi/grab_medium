"""Orchestrator for scanning directories and ingesting metadata into DuckDB."""

import sys
import subprocess
from pathlib import Path
from grab_medium.database import Database

BATCH_SIZE = 5000


class Orchestrator:
    """Orchestrates filesystem scanning and DuckDB ingestion."""

    def __init__(self, db: Database, log_path: str = "grab_medium_errors.log"):
        self.db = db
        self.log_path = log_path

    def run_scan(self, name: str, target_path: str) -> int:
        """Runs the full scan and ingestion pipeline for the given target path and media name.

        Returns the generated media_id.
        """
        # Ensure schema initialized
        self.db.init_schema()

        # 1. Pre-check media name uniqueness
        if self.db.media_exists(name):
            raise ValueError(f"Media with name '{name}' already exists in database.")

        target_path_obj = Path(target_path).resolve()
        if not target_path_obj.exists() or not target_path_obj.is_dir():
            raise ValueError(f"Target path '{target_path}' is not a valid directory.")

        conn = self.db.get_connection()

        # 2. Begin transaction
        conn.execute("BEGIN TRANSACTION;")

        try:
            # 3. Insert media record
            media_row = conn.execute(
                "INSERT INTO media (name, scanned_at) VALUES (?, NOW()) RETURNING id",
                [name],
            ).fetchone()
            assert media_row is not None
            media_id = media_row[0]

            # 4. Resolve scanner command
            scanner_dir = Path(__file__).parent / "scanners"
            if sys.platform == "win32":
                ps_script = scanner_dir / "ps_scanner.ps1"
                cmd = [
                    "powershell.exe",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(ps_script),
                    "-TargetDir",
                    str(target_path_obj),
                    "-MediaId",
                    str(media_id),
                ]
            else:
                bash_script = scanner_dir / "bash_scanner.sh"
                cmd = [str(bash_script), str(target_path_obj), str(media_id)]

            # 5. Spawn subprocess redirecting stderr directly to log file handle
            batch = []
            insert_sql = """
                INSERT INTO entries (
                    media_id, name, extension, relative_path, parent_rel_path,
                    is_dir, size_bytes, created_at, modified_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (media_id, relative_path) DO NOTHING
            """

            with open(self.log_path, "a", encoding="utf-8") as err_log:
                proc = subprocess.Popen(
                    cmd, stdout=subprocess.PIPE, stderr=err_log
                )

                assert proc.stdout is not None
                for line in proc.stdout:
                    line_str = line.decode("utf-8", errors="replace").rstrip("\r\n")
                    if not line_str:
                        continue
                    parts = line_str.split("\x1f")
                    if len(parts) != 9:
                        continue

                    m_id_str, fname, ext, rel_p, parent_p, is_dir_str, size_str, created_at, modified_at = parts

                    is_dir = True if is_dir_str.lower() == "true" else False
                    try:
                        size_bytes = int(size_str) if size_str else 0
                    except ValueError:
                        size_bytes = 0

                    batch.append((
                        int(m_id_str),
                        fname,
                        ext,
                        rel_p,
                        parent_p if parent_p else None,
                        is_dir,
                        size_bytes,
                        created_at if created_at else None,
                        modified_at if modified_at else None,
                    ))

                    if len(batch) >= BATCH_SIZE:
                        conn.executemany(insert_sql, batch)
                        batch.clear()

                if batch:
                    conn.executemany(insert_sql, batch)
                    batch.clear()

                exit_code = proc.wait()
                if exit_code != 0:
                    raise RuntimeError(f"Scanner process failed with exit code {exit_code}")

            # 6. Hierarchy resolution (Self-Join)
            conn.execute(
                """
                UPDATE entries
                SET parent_id = p.id
                FROM entries p
                WHERE entries.media_id = ?
                  AND p.media_id = ?
                  AND entries.parent_rel_path = p.relative_path;
                """,
                [media_id, media_id],
            )

            # Cleanup parent_rel_path
            conn.execute(
                "UPDATE entries SET parent_rel_path = NULL WHERE media_id = ?;",
                [media_id],
            )

            # 7. Commit
            conn.execute("COMMIT;")
            return media_id

        except Exception:
            conn.execute("ROLLBACK;")
            raise
