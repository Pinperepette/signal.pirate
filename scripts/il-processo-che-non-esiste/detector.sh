#!/bin/bash
# ============================================================
# detector.sh — Rileva rootkit basati su ftrace hook
# Signal Pirate
#
# Questo script cerca le tracce che un rootkit kernel lascia:
#   1. Hook ftrace attivi su syscall
#   2. Discrepanze tra /proc e strutture kernel
#   3. Moduli nascosti (in memoria ma non in lsmod)
#   4. Porte TCP aperte ma non visibili
#
# Esegui come root: sudo ./detector.sh
# ============================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}=== Signal Pirate — Rootkit Detector ===${NC}"
echo ""

if [ "$EUID" -ne 0 ]; then
    echo "Esegui come root: sudo ./detector.sh"
    exit 1
fi

SCORE=0

# ---- CHECK 1: ftrace hooks su syscall ----
echo -e "${YELLOW}[CHECK 1] Hook ftrace su syscall${NC}"

FTRACE_ENABLED="/sys/kernel/debug/tracing/enabled_functions"
if [ -f "$FTRACE_ENABLED" ]; then
    SUSPICIOUS=$(grep -iE "sys_getdents|sys_read|sys_write|sys_open|tcp.*seq_show|sys_kill" "$FTRACE_ENABLED" 2>/dev/null || true)
    if [ -n "$SUSPICIOUS" ]; then
        echo -e "  ${RED}TROVATO: hook ftrace su funzioni sensibili:${NC}"
        echo "$SUSPICIOUS" | while read line; do
            echo -e "    ${RED}-> $line${NC}"
        done
        SCORE=$((SCORE + 30))
    else
        echo -e "  ${GREEN}Nessun hook sospetto${NC}"
    fi
else
    echo -e "  ${YELLOW}debugfs non montato, monto...${NC}"
    mount -t debugfs none /sys/kernel/debug 2>/dev/null || true
    if [ -f "$FTRACE_ENABLED" ]; then
        SUSPICIOUS=$(grep -iE "sys_getdents|tcp.*seq_show" "$FTRACE_ENABLED" 2>/dev/null || true)
        if [ -n "$SUSPICIOUS" ]; then
            echo -e "  ${RED}TROVATO: $SUSPICIOUS${NC}"
            SCORE=$((SCORE + 30))
        else
            echo -e "  ${GREEN}Nessun hook sospetto${NC}"
        fi
    else
        echo -e "  ${YELLOW}Impossibile accedere a debugfs${NC}"
    fi
fi
echo ""

# ---- CHECK 2: Discrepanza conteggio processi ----
echo -e "${YELLOW}[CHECK 2] Discrepanza conteggio processi${NC}"

PS_COUNT=$(ps aux 2>/dev/null | wc -l)
PROC_COUNT=$(ls -d /proc/[0-9]* 2>/dev/null | wc -l)
# Conta direttamente dalla task list del kernel via /proc/sched_debug
SCHED_COUNT=0
if [ -f /proc/sched_debug ]; then
    SCHED_COUNT=$(grep -c "^R\|^S\|^D\|^T\|^I" /proc/sched_debug 2>/dev/null || echo 0)
fi

echo "  ps count:         $PS_COUNT"
echo "  /proc count:      $PROC_COUNT"
if [ "$SCHED_COUNT" -gt 0 ]; then
    echo "  sched_debug count: $SCHED_COUNT"
fi

DIFF=$((PROC_COUNT - PS_COUNT))
if [ "$DIFF" -lt -2 ]; then
    echo -e "  ${RED}SOSPETTO: /proc mostra meno processi di ps ($DIFF)${NC}"
    echo -e "  ${RED}Possibile hook su getdents64${NC}"
    SCORE=$((SCORE + 25))
else
    echo -e "  ${GREEN}Conteggi coerenti${NC}"
fi
echo ""

# ---- CHECK 3: Porte aperte non visibili ----
echo -e "${YELLOW}[CHECK 3] Porte TCP aperte ma nascoste${NC}"

# Lista porte da ss
SS_PORTS=$(ss -tlnH 2>/dev/null | awk '{print $4}' | grep -oE '[0-9]+$' | sort -n | uniq)

# Prova connessione su porte comuni sospette
HIDDEN_FOUND=false
for PORT in 4444 4445 5555 6666 7777 8888 31337; do
    # La porta risponde?
    if timeout 1 bash -c "echo > /dev/tcp/127.0.0.1/$PORT" 2>/dev/null; then
        # E' nella lista di ss?
        if ! echo "$SS_PORTS" | grep -qx "$PORT"; then
            echo -e "  ${RED}TROVATO: porta $PORT aperta ma NON in ss/netstat${NC}"
            SCORE=$((SCORE + 30))
            HIDDEN_FOUND=true
        fi
    fi
done

if [ "$HIDDEN_FOUND" = false ]; then
    echo -e "  ${GREEN}Nessuna porta nascosta trovata (range testato: 4444-31337)${NC}"
fi
echo ""

# ---- CHECK 4: Moduli sospetti in memoria ----
echo -e "${YELLOW}[CHECK 4] Moduli kernel sospetti${NC}"

# Cerca simboli di moduli non in lsmod
LSMOD_LIST=$(lsmod | awk 'NR>1 {print $1}' | sort)
KALLSYMS_MODS=$(cat /proc/kallsyms 2>/dev/null | awk '{print $3}' | grep '\[' | sed 's/\[//;s/\]//' | sort -u)

HIDDEN_MODS=""
for MOD in $KALLSYMS_MODS; do
    if ! echo "$LSMOD_LIST" | grep -qx "$MOD"; then
        HIDDEN_MODS="$HIDDEN_MODS $MOD"
    fi
done

if [ -n "$HIDDEN_MODS" ]; then
    echo -e "  ${RED}TROVATO: moduli in kallsyms ma non in lsmod:${NC}"
    for MOD in $HIDDEN_MODS; do
        echo -e "    ${RED}-> $MOD${NC}"
        # Mostra i simboli di quel modulo
        grep "\[$MOD\]" /proc/kallsyms 2>/dev/null | head -5 | while read line; do
            echo -e "      $line"
        done
    done
    SCORE=$((SCORE + 40))
else
    echo -e "  ${GREEN}Tutti i moduli in kallsyms corrispondono a lsmod${NC}"
fi
echo ""

# ---- CHECK 5: /proc entries sospette ----
echo -e "${YELLOW}[CHECK 5] /proc entries sospette${NC}"

SUSPICIOUS_PROC=$(ls /proc/ 2>/dev/null | grep -iE "^sp_|^rootkit|^hide|^backdoor|^shell" || true)
if [ -n "$SUSPICIOUS_PROC" ]; then
    echo -e "  ${RED}TROVATO: entry sospette in /proc:${NC}"
    echo "$SUSPICIOUS_PROC" | while read entry; do
        echo -e "    ${RED}-> /proc/$entry${NC}"
    done
    SCORE=$((SCORE + 20))
else
    echo -e "  ${GREEN}Nessuna entry sospetta${NC}"
fi
echo ""

# ---- RISULTATO ----
echo -e "${CYAN}=== Risultato ===${NC}"
echo ""
if [ "$SCORE" -eq 0 ]; then
    echo -e "  ${GREEN}Score: $SCORE/100 — Nessun indicatore di rootkit trovato${NC}"
elif [ "$SCORE" -lt 30 ]; then
    echo -e "  ${YELLOW}Score: $SCORE/100 — Indicatori deboli, possibile falso positivo${NC}"
elif [ "$SCORE" -lt 60 ]; then
    echo -e "  ${RED}Score: $SCORE/100 — Indicatori moderati, indagare${NC}"
else
    echo -e "  ${RED}Score: $SCORE/100 — FORTE INDICAZIONE di rootkit attivo${NC}"
fi
echo ""
