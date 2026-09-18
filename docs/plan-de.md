# Design-Spezifikation: grab_medium (Python-Edition)

**Datum:** 22.05.2024
**Status:** Final

## 1. Übersicht

`grab_medium` ist ein leichtgewichtiges, hochperformantes CLI-Tool in Python, das für die Orchestrierung des Scannens großer Medienverzeichnisse entwickelt wurde. Es nutzt native Betriebssystem-Skripte (Bash unter Unix-ähnlichen Systemen, PowerShell unter Windows), um das Dateisystem effizient zu durchlaufen und Metadaten zu extrahieren. Die resultierenden Daten werden über eine Pipe direkt in eine DuckDB-Datenbank gestreamt, wobei native Python-Bindings verwendet werden, um den Speicherbedarf und die Festplatten-I/O zu minimieren.

## 2. Architektur

Das System besteht aus drei primären Schichten:

### 2.1 Python Orchestrator (Das Gehirn)
Die Kernanwendung (`grab_medium`), verantwortlich für:
- Parsen von CLI-Argumenten (via `argparse` oder `click`).
- Verifizieren des Ziel-Mediennamens in der Datenbank über das `duckdb` Python-Paket.
- Starten und Verwalten des Lebenszyklus des Betriebssystem-spezifischen Subprozesses via `subprocess.Popen`.
- Verwalten des Streaming-Pipes zwischen dem `stdout` des Subprozesses und der Ingestion-Engine von DuckDB.
- **Transaktionsmanagement:** Umschließen der Erstellung des `media`-Datensatzes, der `entries`-Ingestion und der Hierarchie-Auflösung innerhalb einer einzigen SQL-Transaktion (`BEGIN TRANSACTION` ... `COMMIT`), um Atomarität zu gewährleisten.
- **Post-Ingestion Hierarchy Resolution:** Ausführen eines `UPDATE`-Statements zur Auflösung der `parent_id` basierend auf relativen Pfaden und Bereinigen der temporären Spalte `parent_rel_path`.
- Erfassen von `stderr` des Subprozesses und Schreiben in `grab_medium_errors.log`.
- Bereitstellen minimalistischer, einzeiliger Fortschrittsaktualisierungen für den Benutzer.

### 2.2 OS Native Module (Der Muskel)
Plattformspezifische Skripte, die die schwere Arbeit des Dateisystem-Durchlaufens übernehmen:
- **Linux/macOS (Unix-basiert):** Ein Bash-Modul unter Verwendung von `find` und `stat`.
    - **OS-Erkennung:** Nutzt `uname -s`, um zwischen GNU `stat` (Linux) und BSD `stat` (macOS) zu unterscheiden, um die korrekte Parameternutzung sicherzustellen.
    - **Zeitstempel-Fallback:** Wenn `created_at` über `stat` nicht verfügbar ist, implementiert das Skript einen Fallback: Geschwisterdateien prüfen -> `modified_at` verwenden -> `scanned_at` verwenden.
- **Windows:** Ein PowerShell-Modul unter Verwendung von `.NET` (`[System.IO.Directory]::EnumerateFileSystemEntries`) für hochperformantes, speicherschonendes Streaming.
- **Datenintegrität & Escaping:** 
    - Um Kollisionen mit Dateinamen zu vermeiden, die Kommas, Anführungszeichen oder Zeilenumbrüche enthalten, verwenden die Module ein **Unit Separator (`\x1f`)** als CSV-Delimiter.
    - Alle Ausgaben müssen strikt UTF-8 kodiert sein.
- **Einschränkungen:** Diese Module müssen Symlinks/Junction-Points strikt ignorieren.

### 2.3 DuckDB Engine (Das Gedächtnis)
Eine relationale Datenbank, die für Hochgeschwindigkeits-Ingestion und Speicherung der Metadaten verwendet wird, verwaltet über das native `duckdb` Modul von Python.
- **Lebenszyklus:** Der Orchestrator erstellt die DB und das Schema, falls sie fehlen, oder verifiziert das Schema, falls die Datei existiert.
- **Ingestion:** Verwendet den `COPY`-Befehl mit expliziter Delimiter-Angabe:
  `COPY entries(media_id, name, extension, relative_path, parent_rel_path, is_dir, size_bytes, created_at, modified_at) FROM STDIN (DELIMITER hex('1f'), HEADER false, FORMAT csv);`

## 3. Datenmodell

### 3.1 Tabellen

#### `media` (Metadaten über die Scan-Sitzung)
| Spalte | Typ | Constraints | Beschreibung |
|---|---|---|---|
| `id` | `BIGINT` | `PRIMARY KEY` | Eindeutige Kennung für die Medienkollektion. |
| `name` | `VARCHAR` | `UNIQUE` | Der menschenlesbare Name, der via `--name` angegeben wird. |
| `scanned_at` | `TIMESTAMP` | | Zeitpunkt des Scans. |

#### `entries` (Metadaten über einzelne Dateien)
| Spalte | Typ | Constraints | Beschreibung |
|---|---|---|---|
| `id` | `BIGINT` | `PRIMARY KEY` | Eindeutige Kennung für den Dateyeintrag. |
| `media_id` | `BIGINT` | `FOREIGN KEY (media.id)` | Verknüpfung zur übergeordneten Medienkollektion. |
| `parent_id` | `BIGINT` | `FOREIGN KEY (entries.id)` | Verknüpfung zum übergeordneten Verzeichniseintrag (NULL falls Root). |
| `name` | `VARCHAR` | | Dateiname. |
| `extension` | `VARCHAR` | | Dateiendung (für Indizierung). |
| `relative_path`| `VARCHAR` | | Pfad relativ zum Scan-Root. |
| `parent_rel_path`| `VARCHAR` | | Temporäre Spalte zur Hierarchie-Auflösung. |
| `is_dir` | `BOOLEAN` | | True wenn Verzeichnis, False wenn Datei. |
| `size_bytes` | `BIGINT` | | Größe in Bytes. |
| `created_at` | `TIMESTAMP` | | Datei-Erstellungszeitstempel (mit Fallback-Logik). |
| `modified_at` | `TIMESTAMP` | | Datei-Änderungszeitstempel. |

### 3.2 Indizierung
- `idx_entries_ext` auf `extension`
- `idx_entries_created` auf `created_at`
- `idx_entries_parent` auf `parent_id`
- `idx_entries_media` auf `media_id`

## 4. Detailliertes Design

### 4.1 Die Streaming-Pipe (Datenfluss)
Um maximale Performance und minimalen Speicherverbrauch zu erreichen, implementiert `grab_medium` folgenden Ablauf:
1. **Initialisierung:** Der Python Orchestrator validiert `--name` gegen `media.name` via SQL `SELECT`. Bricht sofort ab, falls der Name existiert.
2. **Transaktionsstart:** Führt `BEGIN TRANSACTION;` auf der DuckDB-Verbindung aus.
3. **Medien-Einfügung:** Fügt einen neuen Datensatz in die Tabelle `media` ein und ruft die `media_id` ab.
4. **Prozess-Start:** Der Orchestrator startet das OS-Skript via `subprocess.Popen` mit `stdout=subprocess.PIPE` und `stderr=subprocess.PIPE`.
5. **Gepipte Ingestion:** 
   - Python übergibt den `proc.stdout` Stream an die DuckDB-Verbindung mittels `COPY entries(...) FROM STDIN (DELIMITER hex('1f'), ...)`.
6. **Hierarchie-Auflösung & Bereinigung:** Nach Abschluss von `COPY` führt der Orchestrator aus:
   `UPDATE entries SET parent_id = p.id FROM entries p WHERE entries.parent_rel_path = p.relative_path AND entries.media_id = p.media_id;`
   `UPDATE entries SET parent_rel_path = NULL WHERE media_id = ?;`
7. **Commit:** `COMMIT;`
8. **Fehlerbehandlung:** Wenn eine Exception auftritt oder der Subprozess mit einem nicht-null Code beendet wird, führt der Orchestrator ein `ROLLBACK;` aus. Aus `stderr` erfasste Fehler werden in `grab_medium_errors.log` protokolliert.
9. **Abschluss:** Meldet die Statuszusammenfassung (`Success` oder `Completed with errors`).

### 4.2 Upsert-Logik
Um doppelte Einträge zu vermeiden und Metadaten aktuell zu halten, nutzt die Tabelle `entries` eine `ON CONFLICT`-Klausel während der Ingestion. Das Konfliktziel ist die Kombination aus `(media_id, relative_path)`.

### 4.3 Benutzeroberfläche
Das CLI zeigt eine einzige Zeile im Terminal an, um den Status anzuzeigen:
- `[Scanning <path>...]`
- `[Ingesting metadata...]`
- `[Done! (Errors logged to grab_medium_errors.log)]`

## 5. Nicht-funktionale Anforderungen
- **Performance:** Ingestion von Millionen von Zeilen in Sekunden unter Verwendung der nativen DuckDB Python C-Extension Bindings und `COPY`.
- **Speicher:** Der Python Orchestrator hält einen nahezu konstanten Speicherverbrauch aufrecht, indem er `stdout` direkt an DuckDB streamt, anstatt Daten in Python-Listen zu laden.
- **Robustheit:** Behandelt Berechtigungsfehler elegant, indem sie im Log protokolliert werden, ohne den Hauptprozess zum Absturz zu bringen.
- **Atomarität:** Datenbanktransaktionen stellen sicher, dass unvollständige Scans bei Unterbrechung oder Fehler rückgängig gemacht werden.