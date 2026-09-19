# `grab_medium` & `InvestigateMedia` - Deutsche API-Dokumentation

Dieses Dokument bietet eine detaillierte technische Dokumentation für alle Python-Module, Klassen und Funktionen im `grab_medium`-Quellcode.

---

## 1. Modul: `grab_medium.config`

### Klasse: `Config`
Datenmodell zur Repräsentation der Ausführungskonfiguration.

- **Attribute**:
  - `data_path` (`str`): Pfad zum Medien-Verzeichnisbaum.
  - `db_path` (`str`): Pfad zur DuckDB-Datenbankdatei.

### Funktion: `resolve_config(data_path=None, db_path=None, config_path=None)`
Ermittelt die aktiven Konfigurationspfade unter Einhaltung der folgenden Rangfolge:

- **Parameter**:
  - `data_path` (`Optional[str]`): CLI-Übersteuerung für den Medien-Pfad.
  - `db_path` (`Optional[str]`): CLI-Übersteuerung für den DuckDB-Datenbankpfad.
  - `config_path` (`Optional[str]`): Pfad zur `db.cfg` JSON-Datei.
- **Rückgabe**: `Tuple[str, str]` - Aufgelöstes Paar `(data_path, db_path)`.
- **Ausnahmen**: `FileNotFoundError` bei fehlender Konfigurationsdatei, `ValueError` bei unvollständigen Parametern.

### Funktion: `load_config(config_path=None, config_file=None, db_path_override=None, data_path_override=None, **kwargs)`
Lädt die Konfiguration und gibt eine `Config`-Instanz zurück. Akzeptiert flexible Parameter-Aliase zur Kompatibilität.

- **Rückgabe**: `Config`

---

## 2. Modul: `grab_medium.database`

### Klasse: `Database(db_path="grab_medium.duckdb")`
Verwaltet die permanente DuckDB-Verbindung und Schema-Erstellung gemäß der Single-Connection-Policy.

- **Methoden**:
  - `get_connection() -> duckdb.DuckDBPyConnection`: Gibt die einzige persistente DuckDB-Verbindungsinstanz zurück.
  - `init_schema() -> None`: Initialisiert Sequenzen, Tabellen (`media`, `entries`, `notes`) und Indizes (`idx_entries_ext`, `idx_entries_created`, `idx_entries_parent`, `idx_entries_media`, `idx_entries_hash`, `idx_notes_target`).
  - `media_exists(name: str) -> bool`: Prüft, ob eine Medien-Sammlung mit dem angegebenen Namen bereits existiert.
  - `close() -> None`: Schließt die aktive DuckDB-Verbindung.

---

## 3. Modul: `grab_medium.hasher`

### Funktion: `compute_quick_hash(file_path, chunk_size=1024*1024)`
Berechnet einen schnellen pragmatischen SHA-256-Hash unter Verwendung von Dateigröße, dem ersten 1 MB Chunk und dem letzten 1 MB Chunk.

- **Parameter**:
  - `file_path` (`Union[str, Path]`): Pfad zur Zieldatei.
  - `chunk_size` (`int`): Chunk-Größe in Bytes (Standard: 1.048.576 Bytes).
- **Rückgabe**: `str` - Hash-Zeichenkette mit Präfix `q:`.

### Funktion: `compute_full_hash(file_path, read_chunk_size=64*1024)`
Berechnet den vollständigen SHA-256-Hash des gesamten Dateiinhalts.

- **Rückgabe**: `str` - Hash-Zeichenkette mit Präfix `f:`.

---

## 4. Modul: `grab_medium.orchestrator`

### Klasse: `Orchestrator(db, log_path="grab_medium_errors.log")`
Orchestriert Dateisystem-Scans, DuckDB-Metadaten-Streaming, Auto-Readme-Import und Synchronisation.

- **Methoden**:
  - `run_scan(name, target_path, sync=False, dry_run=False)`: Führt den initialen Scan oder Sync-Modus aus. Gibt `media_id` oder ein Dictionary mit Zusammenfassungsstatistiken im `dry_run`-Modus zurück.
  - `_execute_scanner(target_path_obj, media_id)`: Startet das OS-spezifische Scanner-Skript (`bash_scanner.sh` oder `ps_scanner.ps1`) und liest die per Unit Separator getrennten Metadaten.
  - `_run_initial_scan(name, target_path_obj, conn)`: Führt den vollständigen Erstscan durch und fügt Metadaten stapelweise ein.
  - `_run_sync_scan(name, target_path_obj, conn, dry_run=False)`: Führt den Synchronisationsabgleich durch und klassifiziert Einträge in `MATCH`, `MOVED`, `CHANGED`, `NEW` und `DELETED` (inkl. kaskadierender Bereinigung zugehöriger Notizen).
  - `_ingest_auto_readmes(conn, media_id, target_path_obj)`: Post-Processing-Schritt zur automatischen Erfassung von `README.md`-, `README.txt`- oder `.description`-Dateien (max. 256 KB) als `auto_readme`-Notizen.

---

## 5. Modul: `grab_medium.investigate_db`

### Klasse: `InvestigateDB(db)`
Abfrage-Engine zur Introspektion, Inhaltssuche und Notiz-Verwaltung.

- **Methoden**:
  - `resolve_media_id(medium)`: Löst einen Sammlungsnamen oder eine numerische ID in eine `media_id` auf.
  - `get_schema_info()`: Gibt Tabellenspalten und Datentypen aus `information_schema.columns` zurück.
  - `list_media()`: Listet alle erfassten Medien-Sammlungen mit ID, Name und Erfassungszeitpunkt auf.
  - `search_content(text)`: Durchsucht Dateinamen, Relativpfade und Notiz-Inhalte ohne Berücksichtigung von Groß-/Kleinschreibung.
  - `search_file_type(medium, extension)`: Filtert Dateien einer Medien-Sammlung nach Dateiendung.
  - `add_note(target_type, target_id, content, source="manual")`: Fügt einer Sammlung, einem Verzeichnis oder einer Datei eine Notiz hinzu.
  - `list_notes(target_type=None, target_id=None)`: Listet Notizen auf, optional gefiltert nach Zieltyp oder Ziel-ID.
  - `execute_query(sql)`: Führt direkte SQL-SELECT-Abfragen aus und gibt `(columns, rows)` zurück.

---

## 6. Modul: `grab_medium.tree`

### Klasse: `TreeNode`
Repräsentiert einen Verzeichnis- oder Dateiknoten im auszugebenden Baum.

- **Attribute**: `entry_id`, `name`, `relative_path`, `is_dir`, `size_bytes`, `has_note`, `children`.
- **Methode**: `compute_aggregated_size() -> int`: Berechnet rekursiv die Gesamtegröße von Ordnern.

### Hilfsfunktionen:
- `format_human_size(bytes_val: int) -> str`: Formatiert Bytes in menschenlesbare Einheiten (KB, MB, GB) mit exakter Byteseingabe in Klammern.
- `build_media_tree(db, media_id)`: Liest Einträge und baut einen `TreeNode`-Baum im Speicher auf.
- `render_terminal_tree(roots, include_size=False)`: Rendert eine formatierte Terminal-Baumstruktur mittels `Rich` mit `[NOTE]`-Indikatoren.
- `render_json_tree(roots, include_size=False)`: Wandelt die Baumhierarchie in eine verschachtelte Dictionary-Struktur für JSON um.
- `render_csv_tree(roots, include_size=False)`: Flacht die Baumhierarchie in eine Liste von Dictionaries für CSV-Export ab.

---

## 7. Modul: `grab_medium.formatter`

### Klasse: `FormatType(str, Enum)`
Enum für Ausgabeformate: `TERMINAL`, `JSON`, `CSV`.

### Funktion: `format_output(data, fmt=FormatType.TERMINAL)`
Formatiert Dictionaries, Abfragetupel oder vorgerenderte Strings in das gewünschte Zielformat.

---

## 8. CLI-Einstiegspunkte

- **`grab_medium.cli:cli`**: Befehlszeilenschnittstelle zum Scannen und Synchronisieren von Medien-Verzeichnissen (`grab-medium`).
- **`grab_medium.investigate_cli:cli`**: Befehlszeilenschnittstelle zum Analysieren, Durchsuchen und Visualisieren der DuckDB-Datenbank (`investigate-media`).
