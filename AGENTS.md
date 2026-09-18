# AGENTS.md

Willkommen im Projekt, **Jules**! Du bist als Implementierer für die Umsetzung von `grab_medium` verantwortlich. Bitte halte dich strikt an die vorgegebenen Spezifikationen und den Test-Driven-Development (TDD) Ansatz.

---

## Projekt-Ordnerstruktur (Verzeichnisbaum)

Verwende die folgende Verzeichnisstruktur als Arbeitsgrundlage für deine Dokumentation und Umsetzung:

```text
.
├── docs/
│   ├── plan-de.md
│   ├── plan.md
│   └── superpowers/
│       ├── plans/
│       │   └── 2024-05-22-grab-medium-implementation.md
│       └── specs/
│           └── 2024-05-22-grab-medium-design.md
└── grab_medium/
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

---

## Primäre Arbeitsanweisungen für Jules

1. **Grundlagendokumente beachten:**
* **Spezifikation:** `docs/superpowers/specs/2024-05-22-grab-medium-design.md`

* **Implementierungsplan:** `docs/superpowers/plans/2024-05-22-grab-medium-implementation.md`



2. **TDD-Workflow einhalten:**
* Erstelle vor jeder Implementierungsphase die entsprechenden Unit- und Integrationstests unter `tests/`.


* Nutze `pytest` zur kontinuierlichen Validierung.




3. **Kritische Kernanforderungen berücksichtigen:**
* **Single-Connection-Policy:** Öffne für Pre-Check, Transaction, Ingestion und Cleanup stets **dieselbe, einzige** DuckDB-Verbindung, um Lock-Issues zu vermeiden.


* **Unit-Separator Delimiter:** Verwende bei allen CSV-Streams das Steuerzeichen `\x1f` (`chr(31)`).


* **Pfadnormalisierung:** Achte darauf, dass alle Scanner Pfade strikt mit Vorwärts-Slashes (`/`) ausgeben und keine Trailing-Slashes enthalten.


* **Subprozess-Handling:** Leite `stderr` der Subprozesse direkt in ein Dateihandle (`grab_medium_errors.log`) um, um OS-Buffer-Deadlocks zu verhindern.


* **Hierarchie-Auflösung:** Führe den Self-Join über `parent_rel_path` sauber in 3 Schritten durch (Insert -> Update Self-Join -> Cleanup).