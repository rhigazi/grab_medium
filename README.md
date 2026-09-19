# grab_medium

A high-performance CLI tool in Python for orchestrating the scanning of large media directories, tracking updates, and streaming filesystem metadata directly into DuckDB.

---

## Features

- **High-Performance Streaming Scanner**: Utilizes OS-native scanner scripts (`bash_scanner.sh` / `ps_scanner.ps1`) using Unit Separator (`\x1f`) delimiters to stream metadata directly into DuckDB without loading large datasets into RAM.
- **Pragmatic Hashing & File Sync (`--sync`)**:
  - Detects moved files based on quick hashes (first/last 1 MB chunk + file size) without re-hashing terabytes of unchanged data.
  - Automatically updates modified paths and metadata.
  - Removes deleted files and performs cascading cleanup of associated notes.
- **Dry Run Simulation (`--dry-run`)**: Simulates synchronization changes and provides summary statistics (`matched`, `moved`, `changed`, `new`, `deleted`) without committing database modifications.
- **Auto-Readme Ingestion**: Automatically ingests directory description files (`README.md`, `README.txt`, `.description`) up to 256 KB as metadata notes during scanning.

---

## Installation

```bash
# Standard installation
pip install .

# Editable development installation
pip install -e .[dev]
```

---

## Usage

### Initial Directory Scan
To create a new media collection snapshot:

```bash
grab-medium --name "vacation_2023" --path "/path/to/media" --db-path "grab_medium.duckdb"
```

### Sync Existing Media Collection (`--sync`)
To update an existing collection snapshot based on current filesystem state:

```bash
grab-medium --name "vacation_2023" --path "/path/to/media" --db-path "grab_medium.duckdb" --sync
```

### Dry Run Simulation (`--dry-run`)
To preview changes without modifying DuckDB:

```bash
grab-medium --name "vacation_2023" --path "/path/to/media" --db-path "grab_medium.duckdb" --sync --dry-run
```

---

## CLI Reference

- `--name`: Name of the media collection.
- `--path`: Directory path to scan or sync.
- `--db-path`: Path to DuckDB database file (default: `grab_medium.duckdb`).
- `--log-path`: Path to error log file (default: `grab_medium_errors.log`).
- `--sync`: Enable update/sync mode for an existing media collection.
- `--dry-run`: Simulate sync without committing changes to database.
