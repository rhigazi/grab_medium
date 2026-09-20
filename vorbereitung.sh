#!/bin/bash

# =============================================================================
# grab_medium - Vorbereitungsskript für den ersten Start
# =============================================================================
# Führt alle notwendigen Schritte aus, um grab_medium einsatzbereit zu machen
# und die Test-Szenarien auszuführen.
# =============================================================================

set -e  # Bei Fehler stoppen

# Farben für Output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_header() {
    echo ""
    echo -e "${BLUE}====================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}====================================================${NC}"
}

print_step() {
    echo -e "${YELLOW}>> $1${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

# =============================================================================
# HAUPTPROGRAMM
# =============================================================================

print_header "GRAB_MEDIUM - ERSTEINRICHTUNG"

# 1. Prüfen ob wir im richtigen Verzeichnis sind
PROJECT_DIR="/content/grab_medium"
if [[ ! -f "$PROJECT_DIR/pyproject.toml" ]]; then
    print_error "pyproject.toml nicht gefunden. Bitte Skript aus /content/grab_medium ausführen."
    exit 1
fi

cd "$PROJECT_DIR"
print_step "Arbeitsverzeichnis: $(pwd)"

# 0. Alte Test-Datenbanken bereinigen (für sauberen Neustart)
print_header "0. ALTEN TEST-DATEN BEREINIGEN"
print_step "Entferne alte Test-Datenbanken und Logs..."
rm -f /content/grab_medium_test.duckdb
rm -f /content/test_errors.log
rm -f /content/grab_medium_errors.log
rm -f grab_medium_errors.log
print_success "Alte Test-Dateien entfernt"

# 2. Python-Umgebung prüfen
print_header "1. PYTHON-UMGEBUNG PRÜFEN"
print_step "Python-Version: $(python3 --version)"
print_step "Pip-Version: $(pip --version)"

# 3. Paket im Entwicklungsmodus installieren
print_header "2. PAKET INSTALLIEREN (EDITABLE MODE)"
print_step "Installiere grab_medium mit Dev-Dependencies..."
pip install -e .[dev]
print_success "Paket erfolgreich installiert"

# 4. CLI-Befehle verifizieren
print_header "3. CLI-BEFEHLE VERIFIZIEREN"
print_step "Prüfe grab-medium..."
if command -v grab-medium &> /dev/null; then
    print_success "grab-medium verfügbar: $(which grab-medium)"
    grab-medium --help | head -20
else
    print_error "grab-medium nicht gefunden!"
    exit 1
fi

print_step "Prüfe investigate-media..."
if command -v investigate-media &> /dev/null; then
    print_success "investigate-media verfügbar: $(which investigate-media)"
    investigate-media --help | head -20
else
    print_error "investigate-media nicht gefunden!"
    exit 1
fi

# 5. Test-Skript ausführbar machen
print_header "4. TEST-SKRIPT VORBEREITEN"
TEST_SCRIPT="$PROJECT_DIR/test_scenarios.sh"
if [[ -f "$TEST_SCRIPT" ]]; then
    chmod +x "$TEST_SCRIPT"
    print_success "test_scenarios.sh ist jetzt ausführbar"
else
    print_error "test_scenarios.sh nicht gefunden!"
    exit 1
fi

# 6. Unit-Tests ausführen (optional, aber empfohlen)
print_header "5. UNIT-TESTS AUSFÜHREN (OPTIONAL)"
print_step "Führe pytest aus..."
if python -m pytest tests/ -v --tb=short; then
    print_success "Alle Unit-Tests bestanden"
else
    print_error "Einige Unit-Tests fehlgeschlagen"
    echo -e "${YELLOW}Möchtest du trotzdem fortfahren? (j/N)${NC}"
    read -r response
    if [[ ! "$response" =~ ^[Jj]$ ]]; then
        exit 1
    fi
fi

# 7. Test-Szenarien ausführen
print_header "6. TEST-SZENARIEN AUSFÜHREN"
print_step "Starte test_scenarios.sh..."
echo ""
"$TEST_SCRIPT"

# 8. Abschluss
print_header "EINRICHTUNG ABGESCHLOSSEN"
echo ""
print_success "grab_medium ist einsatzbereit!"
echo ""
echo -e "${BLUE}Erstellte Dateien:${NC}"
echo "  - Datenbank: /content/grab_medium_test.duckdb"
echo "  - Fehlerlog: /content/test_errors.log (bzw. grab_medium_errors.log)"
echo ""
echo -e "${BLUE}Verfügbare Medien:${NC}"
investigate-media list-media
echo ""
echo -e "${BLUE}Nützliche Befehle:${NC}"
echo "  investigate-media tree-view test_scan"
echo "  investigate-media search-file-type test_scan --ext .py"
echo "  investigate-media query \"SELECT * FROM entries LIMIT 10\""
echo "  grab-medium --name \"mein_projekt\" --path \"/pfad/zu/daten\" --db-path \"meine_db.duckdb\""
echo ""
echo -e "${GREEN}Viel Erfolg mit grab_medium!${NC}"