#!/bin/bash
# 04_what_docker_really_is.sh — Docker smontato: cosa c'e' sotto
#
# Mostra che un "container" e' solo un processo Linux con namespace
# e cgroup. Niente di magico. Lo ricostruiamo a mano.
#
# Uso:
#     chmod +x 04_what_docker_really_is.sh
#     ./04_what_docker_really_is.sh

set -e

SEP="============================================================"

echo ""
echo "$SEP"
echo "  STEP 1: Un container e' solo un processo"
echo "$SEP"
echo ""

echo "> Lancio un container che dorme per 30 secondi..."
CONTAINER_ID=$(docker run -d --name demo_process alpine sleep 30)
echo "Container ID: $CONTAINER_ID"
echo ""

echo "> Dall'host (la VM Docker), vediamo il processo:"
docker top demo_process
echo ""

echo "> Il PID dentro il container:"
docker exec demo_process sh -c 'echo "PID 1 nel container: $$"'
echo ""

echo "> Il PID reale sull'host:"
docker inspect --format '{{.State.Pid}}' demo_process
echo ""

echo "[!] Stesso processo. Due PID diversi. Il namespace PID"
echo "[!] fa credere al processo di essere PID 1 (init)."
echo "[!] In realta' e' un processo qualsiasi sull'host."
echo ""

docker rm -f demo_process > /dev/null 2>&1

echo ""
echo "$SEP"
echo "  STEP 2: I cgroup — il guinzaglio"
echo "$SEP"
echo ""

echo "> Lancio un container con limiti di risorse..."
CONTAINER_ID=$(docker run -d --name demo_cgroup --memory=64m --cpus=0.5 alpine sleep 30)
echo "Container: $CONTAINER_ID"
echo ""

echo "> Limiti di memoria:"
docker stats --no-stream --format "table {{.Name}}\t{{.MemUsage}}\t{{.MemPerc}}\t{{.CPUPerc}}" demo_cgroup
echo ""

echo "> Ispeziono i limiti:"
docker inspect --format '{{.HostConfig.Memory}}' demo_cgroup | awk '{printf "Memoria max: %d MB\n", $1/1024/1024}'
docker inspect --format '{{.HostConfig.NanoCpus}}' demo_cgroup | awk '{printf "CPU max: %.1f core\n", $1/1000000000}'
echo ""

echo "[!] I cgroup limitano le RISORSE (CPU, RAM, I/O)."
echo "[!] I namespace limitano la VISIBILITA' (processi, rete, filesystem)."
echo "[!] Insieme, creano l'ILLUSIONE di una macchina separata."
echo "[!] Ma e' un'illusione. Il kernel e' lo stesso."
echo ""

docker rm -f demo_cgroup > /dev/null 2>&1

echo ""
echo "$SEP"
echo "  STEP 3: Riassunto — cos'e' davvero Docker"
echo "$SEP"
echo ""
echo "  Docker container ="
echo ""
echo "    processo Linux"
echo "    + namespace PID    (vede solo i suoi processi)"
echo "    + namespace NET    (ha la sua interfaccia di rete)"
echo "    + namespace MNT    (ha il suo filesystem)"
echo "    + namespace UTS    (ha il suo hostname)"
echo "    + namespace IPC    (ha la sua memoria condivisa)"
echo "    + namespace USER   (ha i suoi utenti)"
echo "    + cgroup            (ha limiti di CPU/RAM/I/O)"
echo "    + overlay filesystem (immagine a strati)"
echo ""
echo "  Non e' una VM. Non e' una sandbox. Non e' magia."
echo "  E' un processo con delle regole. Le regole si possono rompere."
echo ""
