#!/bin/bash
# 03_namespace_demo.sh — Container vs VM: la differenza che nessuno spiega
#
# Dimostra che i container condividono il kernel dell'host.
# Un container vede lo stesso kernel, le stesse vulnerabilita',
# lo stesso hardware. Non e' una macchina virtuale.
#
# Uso:
#     chmod +x 03_namespace_demo.sh
#     ./03_namespace_demo.sh

set -e

SEP="============================================================"

echo ""
echo "$SEP"
echo "  STEP 1: Cosa condividono i container con l'host"
echo "$SEP"
echo ""

echo "> Kernel dell'host (la VM LinuxKit su Docker Desktop Mac):"
docker run --rm alpine uname -a
echo ""

echo "> Kernel di un secondo container:"
docker run --rm ubuntu uname -a
echo ""

echo "> Kernel di un terzo container (distro diversa):"
docker run --rm debian uname -a
echo ""

echo "[!] Stesso kernel. Tre 'sistemi operativi' diversi, stesso kernel."
echo "[!] Una vulnerabilita' nel kernel li buca tutti e tre."
echo ""

echo ""
echo "$SEP"
echo "  STEP 2: I namespace — l'illusione dell'isolamento"
echo "$SEP"
echo ""

echo "> Cosa vede un container dei propri namespace:"
docker run --rm alpine sh -c '
    echo "--- PID namespace ---"
    echo "PID 1 nel container: $(cat /proc/1/cmdline | tr "\0" " ")"
    echo "Processi visibili: $(ls /proc | grep -c "^[0-9]")"
    echo ""
    echo "--- Network namespace ---"
    echo "Interfacce: $(ip link show | grep "^[0-9]" | wc -l)"
    ip addr show eth0 2>/dev/null | grep "inet "
    echo ""
    echo "--- Mount namespace ---"
    echo "Mount points: $(mount | wc -l)"
    echo "Root filesystem: $(mount | grep "on / " | head -1)"
    echo ""
    echo "--- User ---"
    echo "UID: $(id -u) ($(whoami))"
    echo "Hostname: $(hostname)"
'

echo ""
echo "[!] Il container CREDE di essere solo. Vede solo i suoi processi,"
echo "[!] la sua rete, il suo filesystem. Ma sotto c'e' lo stesso kernel."
echo ""

echo ""
echo "$SEP"
echo "  STEP 3: Cosa vede un container privilegiato"
echo "$SEP"
echo ""

echo "> Con --privileged e --pid=host, l'illusione svanisce:"
docker run --rm --privileged --pid=host alpine sh -c '
    echo "--- Processi host visibili ---"
    echo "Processi totali: $(ls /proc | grep -c "^[0-9]")"
    echo ""
    echo "Primi 15 processi:"
    ps aux 2>/dev/null | head -15 || ls /proc | grep "^[0-9]" | sort -n | head -15
    echo ""
    echo "--- Dispositivi host ---"
    ls /dev/ | head -20
    echo ""
    echo "[!] Il container ora vede TUTTO: processi host, dispositivi, kernel."
    echo "[!] L'"'"'isolamento era solo un namespace. Un flag lo rimuove."
'

echo ""
echo "$SEP"
echo "  CONFRONTO: Container vs VM"
echo "$SEP"
echo ""
echo "  Container                          VM"
echo "  ─────────────────────────────────  ─────────────────────────────────"
echo "  Condivide il kernel dell'host      Ha il proprio kernel"
echo "  Isolamento = namespace (software)  Isolamento = hypervisor (hardware)"
echo "  Escape = exploit kernel            Escape = exploit hypervisor (raro)"
echo "  Un bug kernel buca tutti           Un bug kernel buca solo quella VM"
echo "  Avvio in millisecondi              Avvio in secondi"
echo "  Leggero (~MB)                      Pesante (~GB)"
echo ""
echo "  I container sono fantastici per il deploy."
echo "  Ma NON sono una sandbox di sicurezza."
echo ""
