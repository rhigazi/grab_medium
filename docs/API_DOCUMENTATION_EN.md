# `grab_medium` & `InvestigateMedia` - English API Documentation

This document provides detailed technical documentation for all Python modules, classes, and functions implemented in the `grab_medium` codebase.

---

## 1. Module: `grab_medium.config`

### Class: `Config`
Data model representing runtime configuration settings.

- **Attributes**:
  - `data_path` (`str`): Path to the media directory tree.
  - `db_path` (`str`): Path to the DuckDB database file.

### Function: `resolve_config(data_path=None, db_path=None, config_path=None)`
Resolves the active configuration paths using a strict precedence order.

- **Parameters**:
  - `data_path` (`Optional[str]`): CLI override for media root path.
  - `db_path` (`Optional[str]`): CLI override for DuckDB database file path.
  - `config_path` (`Optional[str]`): Path to `db.cfg` JSON file.
- **Returns**: `Tuple[str, str]` - Resolved `(data_path, db_path)`.
- **Raises**: `FileNotFoundError` if configuration file is missing, `ValueError` if configuration parameters are incomplete.

### Function: `load_config(config_path=None, config_file=None, db_path_override=None, data_path_override=None, **kwargs)`
Loads configuration and returns a `Config` dataclass instance. Accepts flexible argument aliases for caller compatibility.

- **Returns**: `Config`

---

## 2. Module: `grab_medium.database`

### Class: `Database(db_path="grab_medium.duckdb")`
Manages the persistent DuckDB connection and schema setup following a single-connection policy.

- **Methods**:
  - `get_connection() -> duckdb.DuckDBPyConnection`: Returns the single persistent DuckDB connection instance.
  - `init_schema() -> None`: Initializes sequences, tables (`media`, `entries`, `notes`), and indexes (`idx_entries_ext`, `idx_entries_created`, `idx_entries_parent`, `idx_entries_media`, `idx_entries_hash`, `idx_notes_target`).
  - `media_exists(name: str) -> bool`: Checks if a media collection name already exists.
  - `close() -> None`: Closes the active DuckDB connection if open.

---

## 3. Module: `grab_medium.hasher`

### Function: `compute_quick_hash(file_path, chunk_size=1024*1024)`
Calculates a fast pragmatic SHA-256 hash using file size, the first 1 MB chunk, and the last 1 MB chunk.

- **Parameters**:
  - `file_path` (`Union[str, Path]`): Target file path.
  - `chunk_size` (`int`): Chunk size in bytes (default: 1,048,576 bytes).
- **Returns**: `str` - Hash string prefixed with `q:`.

### Function: `compute_full_hash(file_path, read_chunk_size=64*1024)`
Calculates a complete SHA-256 hash of the entire file content.

- **Returns**: `str` - Hash string prefixed with `f:`.

---

## 4. Module: `grab_medium.orchestrator`

### Class: `Orchestrator(db, log_path="grab_medium_errors.log")`
Orchestrates filesystem scanning, DuckDB metadata streaming, auto-readme ingestion, and synchronization.

- **Methods**:
  - `run_scan(name, target_path, sync=False, dry_run=False)`: Executes initial scan or sync mode. Returns `media_id` or summary statistics dict in `dry_run` mode.
  - `_execute_scanner(target_path_obj, media_id)`: Spawns the OS-native scanner script (`bash_scanner.sh` or `ps_scanner.ps1`) and parses Unit Separator delimited metadata stdout.
  - `_run_initial_scan(name, target_path_obj, conn)`: Conducts complete initial scan and batch inserts metadata.
  - `_run_sync_scan(name, target_path_obj, conn, dry_run=False)`: Conducts sync comparison classifying items into `MATCH`, `MOVED`, `CHANGED`, `NEW`, and `DELETED`, with cascading cleanup of deleted entries' notes.
  - `_ingest_auto_readmes(conn, media_id, target_path_obj)`: Post-processing step scanning directories for `README.md`, `README.txt`, or `.description` files (truncated at 256 KB) and persisting them as `auto_readme` notes.

---

## 5. Module: `grab_medium.investigate_db`

### Class: `InvestigateDB(db)`
Query engine providing database introspection, content search, and note management.

- **Methods**:
  - `resolve_media_id(medium)`: Resolves a collection name or numeric string ID to an integer `media_id`.
  - `get_schema_info()`: Returns list of table columns and data types from `information_schema.columns`.
  - `list_media()`: Returns list of recorded media collections with ID, name, and scan timestamp.
  - `search_content(text)`: Performs case-insensitive search across entry names, relative paths, and note contents.
  - `search_file_type(medium, extension)`: Filters files within a media collection by file extension.
  - `add_note(target_type, target_id, content, source="manual")`: Adds a note to a collection, directory, or file.
  - `list_notes(target_type=None, target_id=None)`: Lists notes filtered optionally by target type or target ID.
  - `execute_query(sql)`: Executes arbitrary SELECT query returning `(columns, rows)`.

---

## 6. Module: `grab_medium.tree`

### Class: `TreeNode`
Represents a filesystem node in the rendered directory tree.

- **Attributes**: `entry_id`, `name`, `relative_path`, `is_dir`, `size_bytes`, `has_note`, `children`.
- **Method**: `compute_aggregated_size() -> int`: Recursively calculates folder size totals.

### Helper Functions:
- `format_human_size(bytes_val: int) -> str`: Formats bytes into human-readable units (KB, MB, GB) with exact byte count in parentheses.
- `build_media_tree(db, media_id)`: Fetches entries and constructs in-memory `TreeNode` tree.
- `render_terminal_tree(roots, include_size=False)`: Renders styled terminal tree string using `Rich` with `[NOTE]` indicators.
- `render_json_tree(roots, include_size=False)`: Converts tree hierarchy to nested dict list.
- `render_csv_tree(roots, include_size=False)`: Flattens tree hierarchy into list of dicts for CSV output.

---

## 7. Module: `grab_medium.formatter`

### Class: `FormatType(str, Enum)`
Enum representing output formats: `TERMINAL`, `JSON`, `CSV`.

### Function: `format_output(data, fmt=FormatType.TERMINAL)`
Formats input dictionaries, query tuples, or pre-rendered strings into specified output format.

---

## 8. CLI Entry Points

- **`grab_medium.cli:cli`**: Command line interface for scanning and synchronizing media directory trees (`grab-medium`).
- **`grab_medium.investigate_cli:cli`**: Command line interface for querying and visualizing DuckDB media databases (`investigate-media`).
