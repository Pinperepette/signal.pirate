#!/bin/sh
# Esegue il lab dentro un container Linux privilegiato: nessuna rete reale
# viene toccata, tutto vive in network namespace effimeri dentro il container.
# Uso: ./run.sh
set -eu
cd "$(dirname "$0")"
exec docker run --rm --privileged -v "$PWD":/lab frrouting/frr:latest sh /lab/lab.sh
