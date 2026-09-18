# Gesamtkonzept: `InvestigateMedia`

**Ziel:** Ein hochperformantes CLI-Tool in Python zur Analyse, Durchsuchung und Visualisierung von Mediendaten, die in einer DuckDB-Datenbank erfasst wurden. Es dient als flexible Schnittstelle sowohl für menschliche Benutzer (interaktives CLI) als auch für KI-Agenten (strukturierter Datenabruf).

---

## 1. Konfigurationsverwaltung (`db.cfg`)

Das Tool liest beim Start automatisch die Konfigurationsdatei `db.cfg` aus dem aktuellen Ausführungsverzeichnis (oder über eine Umgebungsvariable) ein:

```json
{
  "data_path": "/pfad/zu/den/medien",
  "db_path": "grab_medium.duckdb"
}

```

* **`db_path`**: Steuert zentral, welche DuckDB-Datenbank für alle Abfragen genutzt wird.
* **`data_path`**: Dient als Referenzpfad für Relativpfad-Auflösungen oder Verzeichnis-Validierungen.
* **Fallback / Fehlerbehandlung**: Fehlt die Konfigurationsdatei oder ist sie ungültig, bricht das Tool mit einer klaren Fehlermeldung ab.

---

## 2. CLI-Interface & Befehlsübersicht

* **`info`**: Gibt die Schemastruktur der Datenbank, Spaltennamen und Datentypen aus, damit KI-Agenten die Tabellenstruktur verstehen und präzise SQL-Abfragen generieren können.
* **`list-media`**: Listet alle erfassten Medien mit Namen und Erfassungszeitpunkt auf.
* **`search-content <Text>`**: Durchsucht Notizen oder Pfade nach einem bestimmten Schlagwort.
* **`search-file-type <Medium> <Endung>`**: Filtert Dateien nach Medium und Dateiendung.
* **`tree-view <Medium>`**: Erzeugt eine visuelle Verzeichnis-Baumstruktur im Terminal.
* **`tree-view-with-size <Medium>`**: Zeigt die Baumstruktur mit aggregierter Dateigröße pro Ordner/Verzeichnis an, um Speicherfresser auf einen Blick zu identifizieren.
* **`query <SQL>`**: Führt direkte SQL-SELECT-Abfragen aus. Bietet den höchsten Freiheitsgrad für KI-Agenten zur komplexen Datenanalyse.

---

## 3. Ausgabemodi & Formatierung

Jeder Befehl unterstützt flexible Ausgabeformate über CLI-Flags (`--format`):

* **Standard (Terminal)**: Menschlich gut lesbare Formate (Tabellen/Zeilen via `Rich`).
* **JSON**: Strukturiertes Datenformat für APIs, Skripte und KI-Agenten.
* **CSV**: Tabellarische Ausgabe für Dateiexporte, Weiterverarbeitung und Data-Science-Pipelines.

---

## 4. Technische Architektur & Systemanforderungen

* **Technologie-Stack**: Python 3.10+, DuckDB (persistent), Click (CLI), Rich (Terminal-Formatierung), Pandas (Daten-Transformationen).
* **Config-Loader (`config.py`)**: Einlesen und Validieren der `db.cfg` vor dem Starten von Datenbankoperationen.
* **Verbindungsmanagement**: Eine einzelne, persistente DuckDB-Verbindung über die gesamte Laufzeit verhindert File-Locking-Konflikte.
* **Pfad-Normalisierung**: Alle Ausgabepfade werden strikt als Forward-Slashes (`/`) formatiert.
* **Hierarchieauflösung**: Nutzt rekursive SQL-Abfragen (`WITH RECURSIVE`) und Aggregationen über `size_bytes` der Kinder-Einträge.

---

## 5. Phasenbasierter Entwicklungsplan

1. **Phase 1: Scaffolding & Config-Loader**: Modulstruktur aufsetzen, Abhängigkeiten in `pyproject.toml` definieren, `config.py` zum Einlesen der `db.cfg` umsetzen.
2. **Phase 2: Datenbankmodul (`db.py`)**: Anbindung der DuckDB-Datenbank über den konfigurierten `db_path` und Bereitstellung der `info`-Funktion.
3. **Phase 3: Query-Engine & Basis-Befehle**: Entwicklung von `list-media`, `search-content`, `search-file-type` und `query`.
4. **Phase 4: Baumstruktur & Größensummen (`tree.py`)**: Logik zur Erzeugung von `tree-view` und `tree-view-with-size`.
5. **Phase 5: Formatierer (`formatter.py`)**: Umwandlung aller Abfrageergebnisse in Standard-, JSON- und CSV-Formate.
6. **Phase 6: CLI & Integration (`cli.py`)**: Zusammenführung aller Komponenten via `click` und Absicherung mit verständlicher Fehlerbehandlung.
