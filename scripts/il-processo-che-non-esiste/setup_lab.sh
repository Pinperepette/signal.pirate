#!/bin/bash
# ============================================================
# setup_lab.sh — Prepara Ubuntu per il lab rootkit
# Signal Pirate
#
# Testato su: Ubuntu 22.04 LTS / 24.04 LTS
# Esegui:     chmod +x setup_lab.sh && ./setup_lab.sh
# ============================================================

set -e

echo "=== Signal Pirate — Rootkit Lab Setup ==="
echo ""

# Controlla che siamo su Ubuntu/Debian
if ! command -v apt &>/dev/null; then
    echo "ERRORE: questo script richiede apt (Ubuntu/Debian)"
    exit 1
fi

# Controlla che siamo root o sudo
if [ "$EUID" -ne 0 ]; then
    echo "Esegui con sudo: sudo ./setup_lab.sh"
    exit 1
fi

echo "[1/4] Aggiorno i pacchetti..."
apt update -qq

echo "[2/4] Installo build-essential e kernel headers..."
apt install -y -qq build-essential linux-headers-$(uname -r) gcc make

echo "[3/4] Verifico che i kernel headers siano al posto giusto..."
KDIR="/lib/modules/$(uname -r)/build"
if [ ! -d "$KDIR" ]; then
    echo "ERRORE: kernel headers non trovati in $KDIR"
    echo "Prova: apt install linux-headers-$(uname -r)"
    exit 1
fi
echo "  OK: $KDIR"

echo "[4/4] Installo strumenti di debug..."
apt install -y -qq net-tools procps

echo ""
echo "=== Setup completato ==="
echo ""
echo "Kernel:  $(uname -r)"
echo "Headers: $KDIR"
echo "GCC:     $(gcc --version | head -1)"
echo ""
echo "Prossimi passi:"
echo "  cd scripts/"
echo "  make"
echo "  sudo insmod rootkit.ko hidden_pid=\$(pgrep -f 'sleep 9999')"
echo ""
echo "RICORDA: questo lab va eseguito SOLO in una VM."
