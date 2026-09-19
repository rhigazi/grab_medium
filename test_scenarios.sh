#!/bin/bash

# =============================================================================
# grab_medium Test-Skript
# Verschiedene Szenarien für grab_medium und investigate-media
# =============================================================================

set -e  # Bei Fehler stoppen

DB_PATH="/content/grab_medium_test.duckdb"
ERROR_LOG="/content/test_errors.log"

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
# SCENARIO 1: Erstmaliger Scan eines Verzeichnisses
# =============================================================================
print_header "SCENARIO 1: Erstmaliger Scan"

print_step "Scanne /content/grab_medium als 'test_scan'..."
grab-medium --name "test_scan" --path "/content/grab_medium" --db-path "$DB_PATH" --log-path "$ERROR_LOG"
print_success "Scan abgeschlossen"

print_step "Verifiziere Anzahl der Dateien..."
investigate-media query "SELECT COUNT(*) as file_count FROM entries WHERE media_id = (SELECT id FROM media WHERE name = 'test_scan')"

# =============================================================================
# SCENARIO 2: Baumansicht anzeigen
# =============================================================================
print_header "SCENARIO 2: Baumansicht"

print_step "Zeige Baumstruktur von 'test_scan' (Tiefe 3)..."
investigate-media tree-view test_scan

# =============================================================================
# SCENARIO 3: Dateien nach Typ suchen
# =============================================================================
print_header "SCENARIO 3: Dateien nach Typ suchen"

print_step "Suche alle Python-Dateien (.py)..."
investigate-media search-file-type test_scan .py

print_step "Suche alle Markdown-Dateien (.md)..."
investigate-media search-file-type test_scan .md

# =============================================================================
# SCENARIO 4: Inhalt suchen
# =============================================================================
print_header "SCENARIO 4: Inhalt in Dateipfaden suchen"

print_step "Suche nach 'cli' in Dateipfaden..."
investigate-media search-content "cli"

print_step "Suche nach 'test' in Dateipfaden..."
investigate-media search-content "test"

# =============================================================================
# SCENARIO 5: SQL-Abfragen
# =============================================================================
print_header "SCENARIO 5: SQL-Abfragen"

print_step "Liste alle Dateien mit Größe > 10KB..."
investigate-media query "
    SELECT name, extension, size_bytes 
    FROM entries 
    WHERE media_id = (SELECT id FROM media WHERE name = 'test_scan')
      AND size_bytes > 10240
    ORDER BY size_bytes DESC
    LIMIT 10
"

print_step "Zeige Dateityp-Verteilung..."
investigate-media query "
    SELECT 
        CASE 
            WHEN extension IS NULL OR extension = '' THEN 'no_ext'
            ELSE LOWER(extension)
        END as file_type,
        COUNT(*) as count
    FROM entries
    WHERE media_id = (SELECT id FROM media WHERE name = 'test_scan')
    GROUP BY file_type
    ORDER BY count DESC
"

print_step "Zeige größte Dateien..."
investigate-media query "
    SELECT name, 
           ROUND(size_bytes / 1024.0, 2) as size_kb,
           modified_at
    FROM entries
    WHERE media_id = (SELECT id FROM media WHERE name = 'test_scan')
      AND is_dir = false
    ORDER BY size_bytes DESC
    LIMIT 5
"

# =============================================================================
# SCENARIO 6: Sync-Modus (Dateien hinzugefügt/geändert)
# =============================================================================
print_header "SCENARIO 6: Sync-Modus"

print_step "Erstelle Testdatei..."
echo "Dies ist ein Test-File für Sync" > /content/grab_medium/test_sync_file.txt
print_success "Testdatei erstellt"

print_step "Führe Dry-Run Sync durch..."
grab-medium --name "test_scan" --path "/content/grab_medium" --db-path "$DB_PATH" --sync --dry-run
print_success "Dry-Run abgeschlossen (keine Änderungen)"

print_step "Führe echten Sync durch..."
grab-medium --name "test_scan" --path "/content/grab_medium" --db-path "$DB_PATH" --sync
print_success "Sync abgeschlossen"

print_step "Verifiziere neue Datei..."
investigate-media query "SELECT name, relative_path FROM entries WHERE media_id = (SELECT id FROM media WHERE name = 'test_scan') AND name = 'test_sync_file.txt'"

# =============================================================================
# SCENARIO 7: Notizen hinzufügen
# =============================================================================
print_header "SCENARIO 7: Notizen"

print_step "Füge Notiz zum Media hinzu..."
investigate-media add-note -t collection -i 1 -m "Dies ist ein Test-Notiz für das gesamte Media"
print_success "Media-Notiz hinzugefügt"

print_step "Füge Notiz zu einer Datei hinzu..."
FILE_ID=$(investigate-media query "SELECT id FROM entries WHERE media_id = (SELECT id FROM media WHERE name = 'test_scan') AND name = 'README.md' LIMIT 1" | grep -o '[0-9]\+' | head -1)
investigate-media add-note -t file -i "$FILE_ID" -m "Wichtige Dokumentation für das Projekt"
print_success "Datei-Notiz hinzugefügt"

print_step "Liste alle Notizen..."
investigate-media list-notes

# =============================================================================
# SCENARIO 8: Datenbank-Info
# =============================================================================
print_header "SCENARIO 8: Datenbank-Informationen"

print_step "Zeige Datenbank-Schema..."
investigate-media info

print_step "Liste alle Medien-Sammlungen..."
investigate-media list-media

# =============================================================================
# SCENARIO 9: Import aus anderem Verzeichnis
# =============================================================================
print_header "SCENARIO 9: Zweiter Scan (tests)"

print_step "Scanne /content/grab_medium/tests als 'test_tests'..."
grab-medium --name "test_tests" --path "/content/grab_medium/tests" --db-path "$DB_PATH"
print_success "Scan abgeschlossen"

print_step "Vergleiche Dateizahlen..."
investigate-media query "
    SELECT 
        m.name as media_name,
        COUNT(e.id) as file_count
    FROM media m
    LEFT JOIN entries e ON e.media_id = m.id
    GROUP BY m.name
    ORDER BY m.name
"

# =============================================================================
# SCENARIO 10: Aufräumen
# =============================================================================
print_header "SCENARIO 10: Aufräumen"

print_step "Entferne Testdatei..."
rm -f /content/grab_medium/test_sync_file.txt
print_success "Testdatei entfernt"

print_step "Finale Sync-Prüfung..."
grab-medium --name "test_scan" --path "/content/grab_medium" --db-path "$DB_PATH" --sync --dry-run
print_success "Dry-Run abgeschlossen"

# =============================================================================
# Zusammenfassung
# =============================================================================
print_header "ZUSAMMENFASSUNG"

echo ""
echo -e "${GREEN}Alle Tests erfolgreich durchgeführt!${NC}"
echo ""
echo "Datenbank: $DB_PATH"
echo "Fehlerlog: $ERROR_LOG"
echo ""
echo "Verfügbare Medien:"
investigate-media list-media
echo ""
echo "Nützliche Befehle zum Weiterarbeiten:"
echo "  investigate-media tree-view test_scan"
echo "  investigate-media search-file-type test_scan --ext .py"
echo "  investigate-media query \"SELECT * FROM entries LIMIT 10\""
echo ""
