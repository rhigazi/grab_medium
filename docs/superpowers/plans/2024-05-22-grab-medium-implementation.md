# Implementierungsplan: grab_medium (Python-Edition)

**Datum:** 2024-05-22
**Status:** Draft
**Bezug:** [Design-Spezifikation](docs/superpowers/specs/2024-05-22-grab-medium-design.md)

## 1. Zielsetzung
Implementierung eines hochperformanten CLI-Tools zur Ingestion von Medienverzeichnissen in eine DuckDB-Datenbank unter Verwendung von Python, plattformspezifischen nativen Skripten und Streaming-Techniken.

## 2. Strategie: Test-Driven Development (TDD)
Jede Phase beginnt mit der Definition der Anforderungen und der Erstellung von Tests, bevor die eigentliche Implementierung erfolgt.

---

## 3. Phasen der Implementierung

### Phase 1: Projekt-Setup & Scaffolding
**Ziel:** Grundstruktur des Python-Pakets und Abhängigkeitsmanagement erstellen.
- [ ] Verzeichnisstruktur anlegen:
  ```text
  grab_medium/
  ├── grab_medium/
  │   ├── __init__.py
  │   ├── cli.py
  │   ├── orchestrator.py
  │   ├── database.py
  │   └── scanners/
  │       ├── __init__.py
  │       ├── bash_scanner.sh
  │       └── ps_scanner.ps1
  ├── tests/
  ├── pyproject.toml
  └── README.md
  ```
- [ ] `pyproject.toml` erstellen (Abhängigkeiten: `duckdb`, `click`).
- [ ] Basistests für das Projekt-Setup konfigurieren (`pytest`).

### Phase 2: Entwicklung der OS-Native Module (Der Muskel)
**Ziel:** Hochperformante Scanner mit korrekter Pfad-Normalisierung und Delimiter-Logik.
- [ ] **Bash-Scanner (`bash_scanner.sh`):**
  - Implementierung mit `find` und `stat`.
  - Logik zur Unterscheidung zwischen GNU und BSD `stat`.
  - Strikte Normalisierung auf Forward-Slashes (`/`) und Entfernung von Trailing Slashes.
  - Implementierung des Zeitstempel-Fallbacks.
  - Test: Manueller Aufruf des Skripts mit verschiedenen Verzeichnisstrukturen (inkl. Sonderzeichen in Namen).
- [ ] **PowerShell-Scanner (`ps_scanner.ps1`):**
  - Implementierung via `.NET` (`[System.IO.Directory]`).
  - Strikte Normalisierung auf Forward-Slashes (`/`) und Entfernung von Trailing Slashes.
  - Test: Manueller Aufruf unter Windows-ähnlicher Umgebung.

### Phase 3: Datenbank-Layer & Schema (Das Gedächtnis)
**Ziel:** Robuste DuckDB-Verbindung und korrektes Schema.
- [ ] `database.py` implementieren:
  - Funktion zur Erstellung/Verifizierung des Schemas (`media`, `entries`).
  - Sicherstellung der `parent_rel_path`-Spalte im `entries`-Schema.
  - Implementierung der Index-Erstellung.
- [ ] **Tests:** 
  - Unit-Tests für die Schema-Erstellung.
  - Test der `ON CONFLICT` Logik (Upsert).

### Phase 4: Orchestrator & Ingestion-Logik (Das Gehirn)
**Ziel:** Die komplexe Streaming- und Transaktionslogik implementieren.
- [ ] `orchestrator.py` Kernimplementierung:
  - **Single-Connection-Policy:** Eine Verbindung für alle Schritte.
  - **Subprozess-Management:** Starten der Scanner mit `stderr`-Umleitung in eine Datei.
  - **Streaming-Ingestion:** Implementierung der Ingestion via `duckdb.from_df` oder `read_csv(proc.stdout)`.
  - **Hierarchie-Auflösung (Self-Join):** Implementierung der 3-stufigen Logik:
    1. `INSERT INTO entries ...`
    2. `UPDATE entries SET parent_id = ... FROM entries p ...` (Self-Join)
    3. `UPDATE entries SET parent_rel_path = NULL ...` (Cleanup)
- [ ] **Tests:**
  - Integrationstest: Ein kompletter Scan-Zyklus in einer Test-DB.
  - Test der Transaktions-Atomarität (Abbruch während des Scans).
  - Test der Hierarchie-Auflösung mit komplexen Verzeichnisstrukturen.

### Phase 5: CLI & Error Handling
**Ziel:** Benutzerfreundliche Oberfläche und Fehlerprotokollierung.
- [ ] `cli.py` Implementierung:
  - Argumente `--name` und `--path`.
  - Fortschrittsanzeige (Einzeiler).
- [ ] Fehlerbehandlung:
  - Korrekte Protokollierung von Subprozess-Fehlern in `grab_medium_errors.log`.
  - Sauberes Rollback bei Fehlern.

---

## 4. Definition of Done (DoD)
- [ ] Alle Tests (`pytest`) laufen erfolgreich durch.
- [ ] Das Tool kann Millionen von Zeilen effizient verarbeiten (Performance-Check).
- [ ] Die Hierarchie wird in der Datenbank korrekt abgebildet (Verifikation via SQL).
- [ ] Die Dokumentation (README) ist aktuell.
- [ ] Keine Speicherlecks oder Deadlocks bei großen Scans beobachtet.
