"""Orchestrator for scanning directories and ingesting metadata into DuckDB."""

import sys
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Tuple, Union
from grab_medium.database import Database
from grab_medium.hasher import compute_quick_hash

BATCH_SIZE = 5000


class Orchestrator:
    """Orchestrates filesystem scanning, DuckDB ingestion, and synchronization."""

    def __init__(self, db: Database, log_path: str = "grab_medium_errors.log"):
        self.db = db
        self.log_path = log_path

    def run_scan(
        self,
        name: str,
        target_path: str,
        sync: bool = False,
        dry_run: bool = False,
    ) -> Union[int, Dict[str, int]]:
        """Runs the full scan or sync pipeline for the given target path and media name.

        If sync=True, syncs filesystem state with existing media collection.
        If dry_run=True, simulates changes without committing.
        Returns generated media_id (or summary dict if dry_run=True).
        """
        self.db.init_schema()

        target_path_obj = Path(target_path).resolve()
        if not target_path_obj.exists() or not target_path_obj.is_dir():
            raise ValueError(f"Target path '{target_path}' is not a valid directory.")

        conn = self.db.get_connection()
        media_exists = self.db.media_exists(name)

        if not sync:
            if media_exists:
                raise ValueError(f"Media with name '{name}' already exists in database.")
            return self._run_initial_scan(name, target_path_obj, conn)

        # Sync mode
        if not media_exists:
            return self._run_initial_scan(name, target_path_obj, conn)

        return self._run_sync_scan(name, target_path_obj, conn, dry_run=dry_run)

    def _execute_scanner(self, target_path_obj: Path, media_id: int) -> List[Tuple[Any, ...]]:
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

        scanned_items = []
        with open(self.log_path, "a", encoding="utf-8") as err_log:
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=err_log)
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

                scanned_items.append((
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

            exit_code = proc.wait()
            if exit_code != 0:
                raise RuntimeError(f"Scanner process failed with exit code {exit_code}")

        return scanned_items

    def _run_initial_scan(self, name: str, target_path_obj: Path, conn) -> int:
        conn.execute("BEGIN TRANSACTION;")
        try:
            media_row = conn.execute(
                "INSERT INTO media (name, scanned_at) VALUES (?, NOW()) RETURNING id",
                [name],
            ).fetchone()
            assert media_row is not None
            media_id = media_row[0]

            scanned_items = self._execute_scanner(target_path_obj, media_id)
            insert_sql = """
                INSERT INTO entries (
                    media_id, name, extension, relative_path, parent_rel_path,
                    is_dir, size_bytes, created_at, modified_at, content_hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (media_id, relative_path) DO NOTHING
            """

            batch = []
            for item in scanned_items:
                m_id, fname, ext, rel_p, parent_p, is_dir, size_bytes, created_at, modified_at = item
                qhash = None
                if not is_dir:
                    fp = target_path_obj / rel_p
                    if fp.is_file():
                        try:
                            qhash = compute_quick_hash(fp)
                        except Exception:
                            qhash = None

                batch.append((
                    m_id, fname, ext, rel_p, parent_p, is_dir, size_bytes, created_at, modified_at, qhash
                ))

                if len(batch) >= BATCH_SIZE:
                    conn.executemany(insert_sql, batch)
                    batch.clear()

            if batch:
                conn.executemany(insert_sql, batch)
                batch.clear()

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

            conn.execute("UPDATE entries SET parent_rel_path = NULL WHERE media_id = ?;", [media_id])
            self._ingest_auto_readmes(conn, media_id, target_path_obj)
            conn.execute("COMMIT;")
            return media_id

        except Exception:
            conn.execute("ROLLBACK;")
            raise

    def _run_sync_scan(
        self,
        name: str,
        target_path_obj: Path,
        conn,
        dry_run: bool = False,
    ) -> Union[int, Dict[str, int]]:
        media_row = conn.execute("SELECT id FROM media WHERE name = ?", [name]).fetchone()
        assert media_row is not None
        media_id = media_row[0]

        scanned_items = self._execute_scanner(target_path_obj, media_id)
        scanned_map = {item[3]: item for item in scanned_items}

        db_rows = conn.execute(
            """
            SELECT id, relative_path, name, is_dir, size_bytes, strftime(modified_at, '%Y-%m-%d %H:%M:%S'), content_hash
            FROM entries WHERE media_id = ?
            """,
            [media_id],
        ).fetchall()
        db_rel_map = {row[1]: row for row in db_rows}

        stats = {"matched": 0, "moved": 0, "changed": 0, "new": 0, "deleted": 0}

        unmatched_scanned: Dict[str, Tuple[Any, ...]] = {}
        unmatched_db: Dict[int, Tuple[Any, ...]] = {}

        if not dry_run:
            conn.execute("BEGIN TRANSACTION;")

        try:
            for rel_p, scanned in scanned_map.items():
                if rel_p in db_rel_map:
                    db_item = db_rel_map[rel_p]
                    db_id, db_rel, db_name, db_is_dir, db_size, db_mtime, db_hash = db_item
                    scanned_is_dir = scanned[5]
                    scanned_size = scanned[6]
                    scanned_mtime = scanned[8]

                    if db_is_dir == scanned_is_dir:
                        if db_is_dir:
                            stats["matched"] += 1
                        else:
                            if db_size == scanned_size and (db_mtime == scanned_mtime or not db_mtime):
                                stats["matched"] += 1
                            else:
                                full_file_path = target_path_obj / rel_p
                                qhash = compute_quick_hash(full_file_path) if full_file_path.exists() else None
                                if qhash and db_hash and qhash == db_hash:
                                    stats["matched"] += 1
                                    if not dry_run:
                                        conn.execute(
                                            "UPDATE entries SET modified_at = ?, size_bytes = ? WHERE id = ?",
                                            [scanned_mtime, scanned_size, db_id],
                                        )
                                else:
                                    stats["changed"] += 1
                                    if not dry_run:
                                        conn.execute(
                                            "UPDATE entries SET modified_at = ?, size_bytes = ?, content_hash = ? WHERE id = ?",
                                            [scanned_mtime, scanned_size, qhash, db_id],
                                        )
                    else:
                        unmatched_scanned[rel_p] = scanned
                        unmatched_db[db_id] = db_item
                else:
                    unmatched_scanned[rel_p] = scanned

            for db_item in db_rows:
                db_id = db_item[0]
                db_rel = db_item[1]
                if db_rel not in scanned_map:
                    unmatched_db[db_id] = db_item

            # MOVED detection
            scanned_hashes = {}
            db_hashes = {}

            for rel_p, item in unmatched_scanned.items():
                is_dir = item[5]
                if not is_dir:
                    file_p = target_path_obj / rel_p
                    if file_p.is_file():
                        scanned_hashes[rel_p] = compute_quick_hash(file_p)

            for db_id, db_item in list(unmatched_db.items()):
                db_rel, db_is_dir, db_hash = db_item[1], db_item[3], db_item[6]
                if not db_is_dir:
                    if db_hash:
                        db_hashes[db_id] = db_hash

            moved_scanned = set()
            moved_db = set()

            for scanned_rel, s_hash in scanned_hashes.items():
                for db_id, d_hash in db_hashes.items():
                    if db_id not in moved_db and s_hash == d_hash:
                        stats["moved"] += 1
                        moved_scanned.add(scanned_rel)
                        moved_db.add(db_id)

                        if not dry_run:
                            item = unmatched_scanned[scanned_rel]
                            fname, ext, parent_p, size_b, created_at, modified_at = (
                                item[1], item[2], item[4], item[6], item[7], item[8]
                            )
                            conn.execute(
                                """
                                UPDATE entries
                                SET relative_path = ?, name = ?, extension = ?, parent_rel_path = ?, size_bytes = ?, modified_at = ?, content_hash = ?
                                WHERE id = ?
                                """,
                                [scanned_rel, fname, ext, parent_p, size_b, modified_at, s_hash, db_id],
                            )
                        break

            # NEW entries
            for rel_p, item in unmatched_scanned.items():
                if rel_p not in moved_scanned:
                    stats["new"] += 1
                    if not dry_run:
                        m_id_str, fname, ext, rel_p, parent_p, is_dir, size_bytes, created_at, modified_at = item
                        qhash = None
                        if not is_dir:
                            fp = target_path_obj / rel_p
                            if fp.is_file():
                                qhash = compute_quick_hash(fp)
                        conn.execute(
                            """
                            INSERT INTO entries (
                                media_id, name, extension, relative_path, parent_rel_path,
                                is_dir, size_bytes, created_at, modified_at, content_hash
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            [media_id, fname, ext, rel_p, parent_p if parent_p else None, is_dir, size_bytes, created_at, modified_at, qhash],
                        )

            # DELETED entries
            for db_id, db_item in unmatched_db.items():
                if db_id not in moved_db:
                    stats["deleted"] += 1
                    if not dry_run:
                        db_is_dir = db_item[3]
                        target_type = "directory" if db_is_dir else "file"
                        conn.execute(
                            "DELETE FROM notes WHERE target_type = ? AND target_id = ?",
                            [target_type, db_id],
                        )
                        conn.execute("DELETE FROM entries WHERE id = ?", [db_id])

            if not dry_run:
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
                conn.execute("UPDATE entries SET parent_rel_path = NULL WHERE media_id = ?;", [media_id])
                conn.execute("UPDATE media SET scanned_at = NOW() WHERE id = ?;", [media_id])
                self._ingest_auto_readmes(conn, media_id, target_path_obj)
                conn.execute("COMMIT;")
                return media_id

            return stats

        except Exception:
            if not dry_run:
                conn.execute("ROLLBACK;")
            raise

    def _ingest_auto_readmes(self, conn, media_id: int, target_path_obj: Path) -> None:
        """Post-processing step to scan directories for README files and store them as notes."""
        readme_filenames = {"readme.md", "readme.txt", ".description"}
        max_bytes = 256 * 1024  # 256 KB

        if target_path_obj.is_dir():
            for child in target_path_obj.iterdir():
                if child.is_file() and child.name.lower() in readme_filenames:
                    try:
                        with open(child, "r", encoding="utf-8", errors="replace") as rf:
                            content = rf.read(max_bytes)
                        conn.execute(
                            "DELETE FROM notes WHERE target_type = 'collection' AND target_id = ? AND source = 'auto_readme'",
                            [media_id],
                        )
                        conn.execute(
                            """
                            INSERT INTO notes (target_type, target_id, source, content, created_at)
                            VALUES ('collection', ?, 'auto_readme', ?, NOW())
                            """,
                            [media_id, content],
                        )
                    except Exception:
                        pass
                    break

        dir_entries = conn.execute(
            "SELECT id, relative_path FROM entries WHERE media_id = ? AND is_dir = TRUE",
            [media_id],
        ).fetchall()

        for entry_id, rel_path in dir_entries:
            folder_path = target_path_obj / rel_path
            if not folder_path.exists() or not folder_path.is_dir():
                if rel_path == target_path_obj.name:
                    folder_path = target_path_obj
                elif rel_path.startswith(target_path_obj.name + "/"):
                    clean_rel = rel_path[len(target_path_obj.name) + 1 :]
                    folder_path = target_path_obj / clean_rel

            if folder_path.is_dir():
                for child in folder_path.iterdir():
                    if child.is_file() and child.name.lower() in readme_filenames:
                        try:
                            with open(child, "r", encoding="utf-8", errors="replace") as rf:
                                content = rf.read(max_bytes)
                            conn.execute(
                                "DELETE FROM notes WHERE target_type = 'directory' AND target_id = ? AND source = 'auto_readme'",
                                [entry_id],
                            )
                            conn.execute(
                                """
                                INSERT INTO notes (target_type, target_id, source, content, created_at)
                                VALUES ('directory', ?, 'auto_readme', ?, NOW())
                                """,
                                [entry_id, content],
                            )
                        except Exception:
                            pass
                        break
