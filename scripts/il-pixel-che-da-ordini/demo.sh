#!/bin/sh
# GhostCommit — catena end-to-end, lato meccanico.
#
# Questo script NON usa un agente AI: dimostra che la *macchina* dell'attacco
# funziona (payload -> exfil -> ricostruzione). Il pezzo mancante, cioe' un
# agente che legge il PNG e obbedisce, si prova a parte (vedi README: il test
# con un subagent reale). Qui mostriamo che se un agente cade, il segreto esce.
set -eu
cd "$(dirname "$0")"

# .env non e' versionato (ignorato da git): lo provvisioniamo dai segreti finti.
[ -f repo-vittima/.env ] || cp repo-vittima/env.example repo-vittima/.env

echo "== 1. genero l'arma: build-spec.png =="
python3 make_payload_png.py
echo

echo "== 2. simulo l'agente avvelenato: .env -> provenance.py (interi) =="
python3 encode_exfil.py repo-vittima/.env > repo-vittima/provenance.py
echo "   provenance.py committato insieme alla feature legittima:"
sed -n '1,3p' repo-vittima/provenance.py
echo "   ..."
echo

echo "== 3. lato attaccante: leggo provenance.py dai commit pubblici =="
python3 decode_exfil.py repo-vittima/provenance.py
echo

echo "== fatto. Nessun segreto in chiaro nel diff: solo una tupla di interi. =="
