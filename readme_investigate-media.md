# InvestigateMedia (`investigate-media`)

`investigate-media` is a high-performance CLI tool in Python designed for querying, searching, analyzing, and visualizing media filesystem metadata stored in DuckDB. It serves as an interactive CLI interface for human users as well as a structured data retrieval tool for AI agents and scripts.

---

## 1. Installation

### Requirements
- Python 3.10 or higher
- DuckDB >= 0.9.0
- Click >= 8.0.0
- Rich >= 12.0.0
- Pandas >= 1.5.0

### Installing the Package
To install `grab_medium` along with the `investigate-media` command:

```bash
# Standard installation
pip install .

# Editable development installation with dev tools
pip install -e .[dev]
```

After installation, the executable `investigate-media` is available directly in your shell environment.

---

## 2. Configuration Management

`investigate-media` connects to the DuckDB database created by `grab_medium`. Configuration can be managed via file, environment variables, or CLI options.

### `db.cfg` Configuration File
By default, the tool looks for a `db.cfg` JSON file in the current working directory:

```json
{
  "data_path": "/path/to/media",
  "db_path": "grab_medium.duckdb"
}
```

* **`db_path`**: Path to the DuckDB database file containing scanned filesystem metadata.
* **`data_path`**: Reference root directory path for relative path resolutions.

### Configuration Precedence & Overrides
1. **CLI Flag Overrides**: `--db-path` and `--data-path` passed directly to `investigate-media` override any config file settings.
2. **Custom Config File Flag**: `--config` or `-c` allows specifying a custom path to `db.cfg`.
3. **Environment Variables**:
   - `INVESTIGATE_MEDIA_CONFIG`: Path to custom configuration file.
   - `GRAB_MEDIUM_CONFIG`: Fallback environment variable for configuration file path.
4. **Default Working Directory**: `db.cfg` in the current working directory.

---

## 3. Command Overview & Features

### Subcommands

#### 1. `info`
Displays the database schema structure, including table names, column names, and data types.

```bash
investigate-media info
```

#### 2. `list-media`
Lists all recorded media collections along with their unique IDs, names, and scan timestamps.

```bash
investigate-media list-media
```

#### 3. `search-content <Text>`
Performs a case-insensitive search across entry names, relative paths, and notes content for the given text snippet.

```bash
investigate-media search-content "beach"
```

#### 4. `search-file-type <Medium> <Endung>`
Filters entries within a specific media collection by file extension. `<Medium>` accepts either the collection name (e.g. `"vacation_2023"`) or numeric `media_id` (e.g. `1`). The extension can be specified with or without a leading dot (e.g., `jpg` or `.jpg`).

```bash
investigate-media search-file-type vacation_2023 jpg
investigate-media search-file-type 1 .png
```

#### 5. `add-note --type <type> --target-id <id> --text <text>`
Adds a manual note to a collection, directory, or file.
* `--type` (`-t`): `collection`, `directory`, or `file`.
* `--target-id` (`-i`): Database ID of the target.
* `--text` (`-m`): Content text of the note.

```bash
investigate-media add-note --type directory --target-id 12 --text "Contains high resolution vacation photos"
```

#### 6. `list-notes [--type <type>] [--target-id <id>]`
Lists notes stored in the database, optionally filtered by target type and target ID.

```bash
investigate-media list-notes
investigate-media list-notes --type directory --target-id 12
```

#### 7. `tree-view <Medium>`
Generates a visual directory tree structure of the specified media collection. Entries with attached notes display a `[NOTE]` indicator.

```bash
investigate-media tree-view vacation_2023
```

#### 8. `tree-view-with-size <Medium>`
Displays the visual directory tree structure with recursively aggregated file sizes for each folder. Terminal output displays human-readable units (KB, MB, GB) with exact byte counts.

```bash
investigate-media tree-view-with-size vacation_2023
```

#### 9. `query <SQL>`
Executes direct SQL `SELECT` queries on the DuckDB database.

```bash
investigate-media query "SELECT extension, COUNT(*) as file_count, SUM(size_bytes) as total_bytes FROM entries GROUP BY extension ORDER BY total_bytes DESC"
```

---

## 4. Automatic Readme Ingestion (Auto-Notes)

During filesystem scanning via `grab-medium`:
- Directories containing `README.md`, `README.txt`, or `.description` automatically have their text ingested into the `notes` table with `source = 'auto_readme'`.
- Description files larger than **256 KB** are truncated to prevent excessive memory usage.
- Ingested notes automatically trigger the visual `[NOTE]` indicator in `tree-view` and are searchable via `search-content`.

---

## 5. Output Formatting Options (`--format` / `-f`)

Every subcommand supports flexible output formatting via the `--format` (`-f`) global option.

Supported formats:
- **`terminal`** (Default): Human-readable tables (powered by Rich) or styled terminal trees.
- **`json`**: Structured JSON format for APIs, scripts, and AI agent integration.
- **`csv`**: Tabular CSV export format for data processing and spreadsheets.
