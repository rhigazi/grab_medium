# Design-Spezifikation: grab_medium (Python-Edition)

**Datum:** 2024-05-22
**Status:** Finalized (Review by User - Bulletproof Version)

## 1. Übersicht

`grab_medium` ist ein leichtgewichtiges, hochperformantes CLI-Tool in Python, das für die Orchestrierung des Scannens großer Medienverzeichnisse entwickelt wurde. Es nutzt native Betriebssystem-Skripte (Bash unter Unix-ähnlichen Systemen, PowerShell unter Windows), um das Dateisystem effizient zu durchlaufen und Metadaten zu extrahieren. Die resultierenden Daten werden über eine Pipe direkt in eine DuckDB-Datenbank gestreamt, wobei native Python-Bindings verwendet werden, um den Speicherbedarf und den Festplatten-I/O zu minimieren.

## 2. Architektur

Das System besteht aus drei primären Schichten:

### 2.1 Python Orchestrator (Das Gehirn)
Die Kernanwendung (`grab_medium`), verantwortlich für:
- Parsen von CLI-Argumenten (via `argparse` oder `click`).
- Verifizieren des Ziel-Mediennamens in der Datenbank über eine **einzelne, persistente DuckDB-Verbindung** (Vermeidung von File-Locks).
- Starten und Verwalten des Lebenszyklus des Betriebssystem-spezifischen Subprozesses via `subprocess.Popen`.
- **Fehler-Streaming:** Um Deadlocks zu vermeiden, wird `stderr` des Subprozesses direkt in das File-Handle `grab_medium_errors.log` umgeleitet, anstatt einen Pipe-Buffer zu verwenden.
- Verwalten der Ingestion-Pipeline (Streaming der Daten vom Scanner in die Datenbank).
- **Transaktionsmanagement:** Umschließen der Erstellung des `media`-Datensatzes, der `entries`-Ingestion und der Hierarchie-Auflösung innerhalb einer einzigen SQL-Transaktion (`BEGIN TRANSACTION` ... `COMMIT`), um Atomarität zu gewährleisten.
- **Post-Ingestion Hierarchy Resolution (Self-Join Approach):** Um das "Hühne-Ei-Problem" (leere Zieltabelle) zu lösen, werden die Daten zuerst in `entries` eingefügt (inkl. `parent_rel_path`). Danach wird ein `UPDATE`-Statement innerhalb der gleichen `media_id` ausgeführt, welches die `parent_id` über einen Self-Join auf `relative_path` auflöst.
- Bereitstellen minimalistischer, einzeiliger Fortschrittsaktualisierungen für den Benutzer.

### 2.2 OS Native Module (Der Muskel)
Plattformspezifische Skripte, die die schwere Arbeit des Dateisystem-Durchlaufens übernehmen:
- **Linux/macOS (Unix-basiert):** Ein Bash-Modul unter Verwendung von `find` und `stat`.
    - **OS-Erkennung:** Nutzt `uname -s`, um zwischen GNU `stat` (Linux) und BSD `stat` (macOS) zu unterscheiden.
    - **Zeitstempel-Fallback:** Wenn `created_at` über `stat` nicht verfügbar ist, implementiert das Skript einen Fallback: Geschwisterdateien prüfen -> `modified_at` verwenden -> `scanned_at` verwenden.
- **Windows:** Ein PowerShell-Modul unter Verwendung von `.NET` (`[System.IO.Directory]::EnumerateFileSystemEntries`) für hochperformantes, speicherschonendes Streaming.
- **Datenintegrität & Escaping:** 
    - Um Kollisionen mit Dateinamen zu vermeiden, die Kommas, Anführungszeichen oder Zeilenumbrüche enthalten, verwenden die Module ein **Unit Separator (`\x1f`)** als CSV-Delimiter.
    - Alle Ausgaben müssen strikt UTF-8 kodiert sein.
- **Pfad-Normalisierung:** 
    - Alle Pfade werden zu **Forward-Slashes (`/`)** normalisiert.
    - **No-Trailing-Slash Policy:** Es wird strikt darauf geachtet, dass Pfade (außer dem absoluten Root) nicht mit einem Slash enden, um Equality-Joins in SQL absolut sicher zu machen.
- **Einschränkungen:** Diese Module müssen Symlinks/Junction-Points strikt ignorieren.

### 2.3 DuckDB Engine (Das Gedächtnis)
Eine relationale Datenbank, die für Hochgeschwindigkeits-Ingestion und Speicherung der Metadaten verwendet wird, verwaltet über das native `duckdb` Modul von Python.
- **Lebenszyklus:** Der Orchestrator erstellt die DB und das Schema, falls sie fehlen, oder verifiziert das Schema, falls die Datei existiert.
- **Ingestion:** Verwendet hochperformante Methoden wie `read_csv` auf dem Subprozess-Stream oder `COPY FROM STDIN`, um die Daten in die Tabelle `entries` zu laden.

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
| `parent_rel_path`| `VARCHAR` | | Permanente, nullable Spalte zur Auflösung der Hierarchie. |
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
1. **Initialisierung:** Der Python Orchestrator validiert `--name` gegen `media.name` über die bestehende Verbindung. Bricht sofort ab, falls der Name existiert.
2. **Transaktionsstart:** Führt `BEGIN TRANSACTION;` auf der DuckDB-Verbindung aus.
3. **Medien-Einfügung:** Fügt einen neuen Datensatz in die Tabelle `media` ein und ruft die `media_id` ab.
4. **Prozess-Start:** Der Orchestrator startet das OS-Skript via `subprocess.Popen`. 
    - `stdout` wird für die Ingestion verwendet.
    - `stderr` wird direkt in `grab_medium_errors.log` umgeleitet, um Puffer-Deadlocks zu verhindern.
5. **Gepipte Ingestion:** 
   - Python streamt die Daten vom `proc.stdout` direkt in die Tabelle `entries`.
6. **Hierarchie-Auflösung (Self-Join):** 
   - Nach Abschluss des Imports wird ein `UPDATE`-Statement ausgeführt:
     `UPDATE entries SET parent_id = p.id FROM entries p WHERE entries.media_id = ? AND p.media_id = ? AND entries.parent_rel_path = p.relative_path;`
   - Zur Speicheroptimierung wird die Spalte geleert: `UPDATE entries SET parent_rel_path = NULL WHERE media_id = ?;`
7. **Commit:** `COMMIT;`
8. **Fehlerbehandlung:** Wenn eine Exception auftritt oder der Subprozess mit einem nicht-null Code beendet wird, führt der Orchestrator ein `ROLLBACK;` aus.
9. **Abschluss:** Meldet die Statuszusammenfassung (`Success` oder `Completed with errors`).

### 4.2 Upsert-Logik
Um doppelte Einträge zu vermeiden, nutzt die Tabelle `entries` eine `ON CONFLICT`-Klausel während der Ingestion auf die Kombination von `(media_id, relative_path)`.

## 5. Nicht-funktionale Anforderungen
- **Performance:** Ingestion von Millionen von Zeilen in Sekunden mittels hochoptimierter SQL-Logik und Streaming.
- **Speicher:** Konstanter Speicherverbrauch durch Streaming via `stdout`.
- **Robustheit:** Atomarität durch SQL-Transaktionen, Vermeidung von Subprozess-Deadlocks, strikte Pfad-Normalisierung und detailliertes Error-Logging.
