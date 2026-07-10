#!/usr/bin/env python3
"""
La Rotta Rubata - perche' un annuncio piu' specifico dirotta il traffico.

Attenzione a non confondere due piani distinti:

1) BGP best-path selection: sceglie UNA rotta migliore PER OGNI prefisso.
   Confronta rotte con lo STESSO prefisso e usa policy locali in ordine:
   prima il peso/LOCAL_PREF (decisi dall'operatore), poi, tra le altre cose,
   la lunghezza dell'AS_PATH. Il /24 e il /25 sono prefissi DIVERSI, quindi
   non si confrontano qui: convivono, ognuno con la sua rotta migliore.

2) Forwarding (FIB): quando arriva un pacchetto, il piano di inoltro sceglie
   la rotta col prefisso PIU' SPECIFICO che contiene l'indirizzo (longest
   prefix match). Qui l'AS_PATH non c'entra piu' niente.

Il sub-prefix hijack vive nel piano 2: annunciando un /25 dentro il /24 della
vittima, l'attaccante crea una rotta piu' specifica. Ovunque quella rotta
venga accettata e installata, il forwarding la preferisce, a prescindere dal
percorso. Questo file modella il piano 2 per mostrarlo.
"""
import ipaddress

# La FIB del router: ogni prefisso ha gia' la SUA rotta migliore (piano 1).
# Il /24 arriva dalla vittima (percorso corto), il /25 dall'attaccante
# (percorso volutamente piu' lungo e lontano).
fib = [
    {"prefix": "10.10.0.0/24", "as_path": [200, 100],      "chi": "VITTIMA  (AS100)"},
    {"prefix": "10.10.0.0/25", "as_path": [200, 42, 7, 666], "chi": "ATTACCANTE (AS666)"},
]


def forward(dest, fib):
    """Longest prefix match: la regola del piano di forwarding."""
    ip = ipaddress.ip_address(dest)
    match = [r for r in fib if ip in ipaddress.ip_network(r["prefix"])]
    if not match:
        return None
    # vince il prefisso piu' specifico. L'AS_PATH non viene nemmeno guardato.
    return max(match, key=lambda r: ipaddress.ip_network(r["prefix"]).prefixlen)


if __name__ == "__main__":
    dest = "10.10.0.5"
    r = forward(dest, fib)
    print(f"destinazione       : {dest}")
    print(f"rotte che lo coprono:")
    for x in fib:
        n = ipaddress.ip_network(x["prefix"])
        print(f"   {x['prefix']:<16} /{n.prefixlen}  AS_PATH={x['as_path']}  -> {x['chi']}")
    print(f"forwarding sceglie : {r['prefix']}  ->  {r['chi']}")
    print(f"nota               : il /25 vince pur avendo l'AS_PATH piu' LUNGO "
          f"({len(fib[1]['as_path'])} vs {len(fib[0]['as_path'])}).")
