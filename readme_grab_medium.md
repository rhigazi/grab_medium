# grab_medium

**grab_medium** is a high-performance Python CLI application and library designed for scanning massive filesystem media directory trees and streaming metadata directly into DuckDB.

---

## Key Features

- **High Performance Scanning**: Leverages OS-native scanner scripts (`bash_scanner.sh` on Linux/macOS and `ps_scanner.ps1` on Windows) for maximum filesystem traversal speed.
- **Direct DuckDB Streaming**: Streams directory metadata directly into DuckDB using `\x1f` (Unit Separator) delimited streams with batching.
- **Hierarchy Resolution**: Automatically builds parent-child directory and file relationships in DuckDB via single-connection transaction self-joins.
- **Automatic Configuration (`db.cfg`)**: Automatically creates and maintains a `db.cfg` configuration file storing the last used media directory path (`data_path`) and database location (`db_path`).
- **Deadlock-Free Logging**: Process `stderr` streams are piped directly to disk log files (`grab_medium_errors.log`), avoiding OS memory buffer deadlocks during heavy scans.

---

## Configuration (`db.cfg`)

`grab_medium` automatically manages a `db.cfg` JSON file in the execution directory.

### Example `db.cfg`:
```json
{
  "data_path": "/path/to/media/library",
  "db_path": "grab_medium.duckdb"
}
```

### Configuration Behavior:
1. **Explicit CLI Options**: Passing `--path` or `--db-path` via CLI overrides any value in `db.cfg` and automatically updates `db.cfg` with the new values.
2. **Fallback to `db.cfg`**: If `--path` or `--db-path` are omitted when invoking the command, `grab_medium` reads the configured paths from `db.cfg`.
3. **Default Database Path**: If `db_path` is not specified in CLI or `db.cfg`, it defaults to `grab_medium.duckdb`.

---

## Installation & Setup

1. **Clone Repository**:
   ```bash
   git clone <repository-url>
   cd grab_medium
   ```

2. **Install Package**:
   ```bash
   pip install -e .[dev]
   ```

3. **Run Tests**:
   ```bash
   python3 -m pytest
   ```

---

## CLI Usage

### First Run (Specifying Path and Collection Name)
```bash
grab-medium --name "vacation_2024" --path "/Volumes/Media/Photos"
```
*This command scans `/Volumes/Media/Photos`, creates `grab_medium.duckdb`, populates metadata under collection `vacation_2024`, and creates `db.cfg` storing the configuration.*

### Subsequent Runs (Using `db.cfg`)
Once `db.cfg` exists, you can omit `--path`:
```bash
grab-medium --name "vacation_2025"
```
*This automatically uses `data_path` from `db.cfg`.*

### Overriding Configuration
```bash
grab-medium --name "movies" --path "/Volumes/Media/Movies" --db-path "movies.duckdb"
```
*This updates `db.cfg` with the new `data_path` and `db_path`.*

---

## Command Line Options

| Option | Required | Description | Default |
| ------ | -------- | ----------- | ------- |
| `--name` | **Yes** | Unique identifier/label for the media collection scan. | N/A |
| `--path` | Optional | Target directory path to scan. Reads from `db.cfg` if omitted. | `db.cfg` value |
| `--db-path` | Optional | Path to DuckDB database file. Reads from `db.cfg` if omitted. | `grab_medium.duckdb` |
| `--log-path` | Optional | Error log file path. | `grab_medium_errors.log` |
| `--config-path` | Optional | Configuration file location. | `db.cfg` |

---

## Primary Use Cases

### Use Case 1: Large Media Library Cataloging
Quickly catalog terabytes of media files (photos, videos, audio collections) across external hard drives or network attached storage (NAS) into DuckDB for fast querying, deduplication, and analytics.

### Use Case 2: Multi-Collection Tracking over Time
Perform incremental scans of different folders or drives into a single unified DuckDB database by giving each scan a distinct `--name` (e.g. `--name photos_archive_2023`, `--name photos_archive_2024`).

### Use Case 3: Automated / Scheduled Backup Indexing
Integrate `grab-medium` into cron jobs or automated backup scripts. Because `db.cfg` remembers the target `data_path` and `db_path`, scheduled executions only require specifying the scan execution name.

### Use Case 4: Fast Analytics & File Insights via SQL
Query file size distributions, extension counts, creation/modification timelines, and directory depth directly using DuckDB SQL or Python analytics frameworks (Pandas, Polars).

---

## Database Schema

`grab_medium` initializes two primary tables in DuckDB:

### Table `media`
| Column | Type | Description |
| ------ | ---- | ----------- |
| `id` | `BIGINT PRIMARY KEY` | Auto-incrementing collection ID |
| `name` | `VARCHAR UNIQUE` | Collection scan name |
| `scanned_at` | `TIMESTAMP` | Timestamp of scan execution |

### Table `entries`
| Column | Type | Description |
| ------ | ---- | ----------- |
| `id` | `BIGINT PRIMARY KEY` | Auto-incrementing entry ID |
| `media_id` | `BIGINT REFERENCES media(id)` | Associated media collection ID |
| `parent_id` | `BIGINT` | ID of parent directory entry (resolved via self-join) |
| `name` | `VARCHAR` | File or directory name |
| `extension` | `VARCHAR` | File extension (lowercase) |
| `relative_path` | `VARCHAR` | Normalized relative path from root scan directory |
| `is_dir` | `BOOLEAN` | `TRUE` for directories, `FALSE` for files |
| `size_bytes` | `BIGINT` | File size in bytes (0 for directories) |
| `created_at` | `TIMESTAMP` | Entry creation timestamp |
| `modified_at` | `TIMESTAMP` | Entry last modification timestamp |

---

## Example SQL Queries

```sql
-- Count total files and total size (in GB) per collection
SELECT
    m.name AS collection,
    COUNT(*) AS total_files,
    ROUND(SUM(e.size_bytes) / 1024 / 1024 / 1024, 2) AS size_gb
FROM entries e
JOIN media m ON e.media_id = m.id
WHERE e.is_dir = FALSE
GROUP BY m.name;

-- Top 10 file extensions by volume
SELECT
    extension,
    COUNT(*) AS file_count,
    ROUND(SUM(size_bytes) / 1024 / 1024, 2) AS total_mb
FROM entries
WHERE is_dir = FALSE
GROUP BY extension
ORDER BY total_mb DESC
LIMIT 10;
```
