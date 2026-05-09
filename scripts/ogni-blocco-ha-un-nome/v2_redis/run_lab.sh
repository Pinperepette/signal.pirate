#!/usr/bin/env bash
# Lab orchestrator: spin up Redis, init state, launch 3 daemons + 3 agents
# in parallel, wait, run compare, tear down.
set -e

cd "$(dirname "$0")"
mkdir -p output

echo "[1/6] starting redis container ..."
docker-compose up -d > /dev/null
# wait for healthcheck
for i in $(seq 1 20); do
  if docker exec agd-lab-redis redis-cli ping > /dev/null 2>&1; then break; fi
  sleep 0.2
done

echo "[2/6] init state ..."
python3 lab_redis.py --mode init

echo "[3/6] launch daemons ..."
python3 lab_redis.py --mode daemon-md   > output/daemon-md.stdout   2>&1 &
DM=$!
python3 lab_redis.py --mode daemon-html > output/daemon-html.stdout 2>&1 &
DH=$!
# AGD daemon: native Rust binary (agdd) using the library API directly,
# no subprocess fork-and-exec per op. Built from /Users/pinperepette/Porgetti/MDF2/agd
AGDD="${AGDD:-$HOME/.cargo/bin/agdd}"
if [ ! -x "$AGDD" ]; then
  AGDD="/Users/pinperepette/Porgetti/MDF2/agd/target/release/agdd"
fi
"$AGDD" \
  --redis-url redis://127.0.0.1:6391/ \
  --stream agd-lab:agd:ops \
  --state-key agd-lab:agd:state \
  --group daemon-agd \
  --consumer daemon-agd-1 \
  > output/daemon-agd.log 2> output/daemon-agd.stdout &
DA=$!

# Give daemons a moment to register on their groups
sleep 0.3

echo "[4/6] launch agents ..."
python3 lab_redis.py --mode agent-analyst   > output/agent-analyst.stdout   2>&1 &
A1=$!
python3 lab_redis.py --mode agent-responder > output/agent-responder.stdout 2>&1 &
A2=$!
python3 lab_redis.py --mode agent-auditor   > output/agent-auditor.stdout   2>&1 &
A3=$!

# Wait for agents to finish emitting
wait $A1 $A2 $A3

echo "[5/6] waiting for daemons to drain queues ..."
wait $DM $DH $DA

echo "[6/6] compare ..."
python3 lab_redis.py --mode compare

echo
echo "Tear down: docker-compose down"
docker-compose down > /dev/null
echo "Done. Artefacts in output/"
