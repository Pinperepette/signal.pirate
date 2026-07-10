# La Rotta Rubata - lab

Dimostra un BGP hijack di tipo sub-prefix e la difesa via policy, tutto dentro
network namespace effimeri con `bgpd` di FRRouting. Nessuna rete reale viene
toccata.

## File

- `best_route.py` - il modello del piano di forwarding (longest prefix match).
  Mostra perche' un /25 vince sul /24 anche con un AS_PATH piu' lungo.
  Gira nativo: `python3 best_route.py`.
- `lab.sh` - il lab vero: 4 AS (netns) con `bgpd`, fase pulita, hijack, difesa.
  Va eseguito dentro un container Linux privilegiato.
- `run.sh` - wrapper che avvia `lab.sh` in un container FRR privilegiato.

## Come si esegue

```sh
python3 best_route.py     # il modello, ovunque
./run.sh                  # il lab completo, richiede Docker
```

Il lab e' stato provato con l'immagine `frrouting/frr:latest` (FRR 8.x, Alpine).
Serve un host con supporto ai network namespace (Linux, oppure la VM Linux di
Docker Desktop). Il container gira `--privileged` solo perche' crea netns e
veth al suo interno.

## Topologia

```
AS100 vittima --(10.1.12.0/30)-- AS200 transito --(10.1.23.0/30)-- AS300 client
                                       |
                                 (10.1.26.0/30)
                                       |
                                 AS666 attaccante
```

La vittima annuncia `10.10.0.0/24` e serve `10.10.0.5`. L'attaccante annuncia
`10.10.0.0/25` (meta' del /24, non suo). Un banner letto dal client dice chi
risponde davvero sull'IP: `VICTIM` o `ATTACKER`.
