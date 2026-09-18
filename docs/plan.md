# Design Spec: grab_medium (Python Edition)

**Date:** 2024-05-22
**Status:** Final

## 1. Overview

`grab_medium` is a lightweight, high-performance CLI tool written in Python designed to orchestrate the scanning of large media directories. It uses native operating system scripts (Bash on Unix-like systems, PowerShell on Windows) to traverse the filesystem and extract metadata efficiently. The resulting data is streamed via a pipe directly into a DuckDB database using native Python bindings to minimize memory footprint and disk I/O.

## 2. Architecture

The system consists of three primary layers:

### 2.1 Python Orchestrator (The Brain)
The core application (`grab_medium`) responsible for:
- Parsing CLI arguments (via `argparse` or `click`).
- Verifying the target media name in the database via the `duckdb` Python package.
- Spawning and managing the lifecycle of the OS-specific sub-process via `subprocess.Popen`.
- Managing the streaming pipe between the sub-process `stdout` and DuckDB's ingestion engine.
- **Transaction Management:** Wrapping the creation of the `media` record, the `entries` ingestion, and hierarchy resolution within a single SQL transaction (`BEGIN TRANSACTION` ... `COMMIT`) to ensure atomicity.
- **Post-Ingestion Hierarchy Resolution:** Executing an `UPDATE` statement to resolve `parent_id` based on relative paths and clearing the temporary `parent_rel_path` column.
- Capturing `stderr` from the sub-process and writing it to `grab_medium_errors.log`.
- Providing minimalist, single-line progress updates to the user.

### 2.2 OS Native Modules (The Muscle)
Platform-specific scripts that handle the heavy lifting of filesystem traversal:
- **Linux/macOS (Unix-based):** A Bash module utilizing `find` and `stat`.
    - **OS Detection:** Uses `uname -s` to distinguish between GNU `stat` (Linux) and BSD `stat` (macOS) to ensure correct parameter usage.
    - **Timestamp Fallback:** If `created_at` is unavailable via `stat`, the script implements a fallback: Check sibling files -> Use `modified_at` -> Use `scanned_at`.
- **Windows:** A PowerShell module utilizing `.NET` (`[System.IO.Directory]::EnumerateFileSystemEntries`) for high-performance, low-memory streaming.
- **Data Integrity & Escaping:** 
    - To prevent collisions with filenames containing commas, quotes, or newlines, the modules will use a **Unit Separator (`\x1f`)** as the CSV delimiter.
    - All output must be strictly UTF-8 encoded.
- **Constraints:** These modules must strictly ignore symlinks/junction points.

### 2.3 DuckDB Engine (The Memory)
A relational database used for high-speed ingestion and storage of the metadata, managed via Python's native `duckdb` module.
- **Lifecycle:** The orchestrator creates the DB and schema if missing, or verifies the schema if the file exists.
- **Ingestion:** Uses the `COPY` command with explicit delimiter specification:
  `COPY entries(media_id, name, extension, relative_path, parent_rel_path, is_dir, size_bytes, created_at, modified_at) FROM STDIN (DELIMITER hex('1f'), HEADER false, FORMAT csv);`

## 3. Data Model

### 3.1 Tables

#### `media` (Metadata about the scan session)
| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | `BIGINT` | `PRIMARY KEY` | Unique identifier for the media collection. |
| `name` | `VARCHAR` | `UNIQUE` | The human-readable name provided via `--name`. |
| `scanned_at` | `TIMESTAMP` | | When the scan occurred. |

#### `entries` (Metadata about individual files)
| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | `BIGINT` | `PRIMARY KEY` | Unique identifier for the file entry. |
| `media_id` | `BIGINT` | `FOREIGN KEY (media.id)` | Link to the parent media collection. |
| `parent_id` | `BIGINT` | `FOREIGN KEY (entries.id)` | Link to the parent directory entry (NULL if root). |
| `name` | `VARCHAR` | | Filename. |
| `extension` | `VARCHAR` | | File extension (for indexing). |
| `relative_path`| `VARCHAR` | | Path relative to the scan root. |
| `parent_rel_path`| `VARCHAR` | | Temporary column used for hierarchy resolution. |
| `is_dir` | `BOOLEAN` | | True if directory, False if file. |
| `size_bytes` | `BIGINT` | | Size in bytes. |
| `created_at` | `TIMESTAMP` | | File creation timestamp (with fallback logic). |
| `modified_at` | `TIMESTAMP` | | File modification timestamp. |

### 3.2 Indexing
- `idx_entries_ext` on `extension`
- `idx_entries_created` on `created_at`
- `idx_entries_parent` on `parent_id`
- `idx_entries_media` on `media_id`

## 4. Detailed Design

### 4.1 The Streaming Pipe (Data Flow)
To achieve maximum performance and minimum memory usage, `grab_medium` will implement the following flow:
1. **Initialization:** Python orchestrator validates `--name` against `media.name` via SQL `SELECT`. Aborts immediately if the name exists.
2. **Transaction Start:** Execute `BEGIN TRANSACTION;` on the DuckDB connection.
3. **Media Insertion:** Insert new record into `media` table and retrieve `media_id`.
4. **Process Spawn:** Orchestrator spawns the OS script via `subprocess.Popen` with `stdout=subprocess.PIPE` and `stderr=subprocess.PIPE`.
5. **Piped Ingestion:** 
   - Python passes `proc.stdout` stream into DuckDB's connection using `COPY entries(...) FROM STDIN (DELIMITER hex('1f'), ...)`.
6. **Hierarchy Resolution & Cleanup:** After `COPY` completes, the orchestrator runs:
   `UPDATE entries SET parent_id = p.id FROM entries p WHERE entries.parent_rel_path = p.relative_path AND entries.media_id = p.media_id;`
   `UPDATE entries SET parent_rel_path = NULL WHERE media_id = ?;`
7. **Commit:** `COMMIT;`
8. **Error Handling:** If any exception occurs or the sub-process exits with a non-zero code, the orchestrator issues `ROLLBACK;`. Errors captured from `stderr` are logged to `grab_medium_errors.log`.
9. **Completion:** Reports status summary (`Success` or `Completed with errors`).

### 4.2 Upsert Logic
To prevent duplicate entries and keep metadata fresh, the `entries` table will utilize an `ON CONFLICT` clause during ingestion. The conflict target will be the combination of `(media_id, relative_path)`.

### 4.3 User Interface
The CLI will use a single line in the terminal to show status:
- `[Scanning <path>...]`
- `[Ingesting metadata...]`
- `[Done! (Errors logged to grab_medium_errors.log)]`

## 5. Non-Functional Requirements
- **Performance:** Ingest millions of rows in seconds using DuckDB's native Python C-extension bindings and `COPY`.
- **Memory:** The Python orchestrator maintains a near-constant memory footprint by streaming `stdout` directly to DuckDB instead of loading data into Python lists.
- **Robustness:** Handles permission errors gracefully by logging them to file without crashing the main process.
- **Atomicity:** Database transactions ensure incomplete scans are rolled back on interruption or failure.