#!/usr/bin/env python3
"""
Costruisce i dati dei grafici dell'articolo "L'eccezione e' gia' nella regola".

Ogni valore che finisce in un grafico sta in fonti.csv con la sua fonte, l'URL e il
livello di affidabilita' (A primaria, B secondaria affidabile, C advocacy o stampa,
da ricontrollare). Questo script non scarica niente: valida il CSV, lo trasforma nella
struttura che il grafico si aspetta e la scrive in grafici.json.

    python3 build_data.py                 valida e scrive grafici.json
    python3 build_data.py --check         valida soltanto, non scrive nulla
    python3 build_data.py --inject FILE   scrive anche il blocco DATI dentro l'articolo

L'output e' deterministico: nessun timestamp, chiavi ordinate. Rilanciarlo due volte
di fila produce byte identici, cosi' un diff sporco significa che sono cambiati i dati
e non l'orologio.
"""

import argparse
import csv
import hashlib
import json
import re
import sys
from pathlib import Path

QUI = Path(__file__).resolve().parent
CSV_FONTI = QUI / "fonti.csv"
JSON_OUT = QUI / "grafici.json"

AFFIDABILITA = {"A", "B", "C"}

# Come va letto ogni grafico. "valori" dice se le righe devono avere una y numerica.
SPEC = {
    "g1": {"tipo": "dumbbell", "valori": True},
    "g2": {"tipo": "forbice", "valori": "misto"},
    "g3": {"tipo": "filiera", "valori": False},
    "g4": {"tipo": "stack", "valori": False},
    "g5": {"tipo": "gradino", "valori": "misto"},
    "g6": {"tipo": "barre", "valori": True},
    "g7": {"tipo": "discesa", "valori": True},
    "g8": {"tipo": "confronto", "valori": True},
}

TITOLI = {
    "g1": "Il peso dell'autonomia personale prima e dopo la dichiarazione dell'OMS",
    "g2": "Le opinioni tornano indietro, le leggi no",
    "g3": "Cambiano le giustificazioni, non l'architettura",
    "g4": "Lo stack biometrico europeo: ogni strato resta",
    "g5": "Chat Control: novantasei giorni senza base giuridica",
    "g6": "Quanto rumore produce la scansione automatica",
    "g7": "Il consenso si sgretola appena la misura diventa concreta",
    "g8": "Rispetto al 2004 i britannici sono piu' diffidenti, non meno",
}

ASSI = {
    "g1": {"x": "importanza relativa attribuita all'attributo (%)"},
    "g2": {"sx": "quota di americani che ritiene necessario rinunciare a liberta' civili (%)",
           "dx": "paesi con leggi antiterrorismo nuove o riviste dal settembre 2001"},
    "g5": {"x": "base giuridica per la scansione delle comunicazioni private"},
    "g6": {"x": "quota di segnalazioni che non regge (%)"},
    "g7": {"x": "favorevoli (%)"},
    "g8": {"x": "quota di intervistati (%)"},
}


class ErroreDati(Exception):
    pass


def leggi_csv(percorso: Path):
    if not percorso.exists():
        raise ErroreDati(f"manca il file delle fonti: {percorso}")
    with percorso.open(encoding="utf-8", newline="") as f:
        righe = list(csv.DictReader(f))
    if not righe:
        raise ErroreDati("fonti.csv e' vuoto")
    attese = {"grafico", "serie", "label", "x", "y", "unita",
              "fonte", "url", "affidabilita", "nota"}
    mancanti = attese - set(righe[0].keys())
    if mancanti:
        raise ErroreDati(f"colonne mancanti in fonti.csv: {sorted(mancanti)}")
    return righe


def valida(righe):
    errori = []
    for n, r in enumerate(righe, start=2):  # riga 1 = intestazione
        g = r["grafico"].strip()
        if g not in SPEC:
            errori.append(f"riga {n}: grafico sconosciuto '{g}'")
            continue
        if not r["fonte"].strip() or not r["url"].strip():
            errori.append(f"riga {n}: ogni valore deve avere fonte e url")
        if r["affidabilita"].strip() not in AFFIDABILITA:
            errori.append(f"riga {n}: affidabilita' '{r['affidabilita']}' non in A/B/C")
        if not r["label"].strip():
            errori.append(f"riga {n}: label vuota")
        y = r["y"].strip()
        richiede = SPEC[g]["valori"]
        if y:
            try:
                float(y)
            except ValueError:
                errori.append(f"riga {n}: y '{y}' non e' un numero")
        elif richiede is True:
            errori.append(f"riga {n}: il grafico {g} richiede un valore numerico")
        elif richiede is False and r["serie"].strip() not in ("evento",) and g in ("g3", "g4"):
            pass  # filiera e stack sono per costruzione senza valori
    if errori:
        raise ErroreDati("\n".join(errori))


def num(v):
    v = (v or "").strip()
    return float(v) if v else None


def punto(r):
    """Riga del CSV -> punto del grafico, con la fonte attaccata addosso."""
    p = {
        "label": r["label"].strip(),
        "serie": r["serie"].strip(),
        "fonte": r["fonte"].strip(),
        "url": r["url"].strip(),
        "affidabilita": r["affidabilita"].strip(),
    }
    x = r["x"].strip()
    if x:
        p["x"] = x
    y = num(r["y"])
    if y is not None:
        p["y"] = y
    if r["unita"].strip():
        p["unita"] = r["unita"].strip()
    if r["nota"].strip():
        p["nota"] = r["nota"].strip()
    return p


def costruisci(righe):
    grafici = {}
    for g, spec in SPEC.items():
        punti = [punto(r) for r in righe if r["grafico"].strip() == g]
        if not punti:
            raise ErroreDati(f"nessun dato per il grafico {g}")
        livelli = sorted({p["affidabilita"] for p in punti})
        grafici[g] = {
            "id": g,
            "tipo": spec["tipo"],
            "titolo": TITOLI[g],
            "assi": ASSI.get(g, {}),
            "affidabilita": livelli,
            "punti": punti,
        }
    return grafici


def sha256(percorso: Path) -> str:
    return hashlib.sha256(percorso.read_bytes()).hexdigest()


def riepilogo(grafici):
    conta = {"A": 0, "B": 0, "C": 0}
    for g in grafici.values():
        for p in g["punti"]:
            conta[p["affidabilita"]] += 1
    tot = sum(conta.values())
    print(f"  {len(grafici)} grafici, {tot} valori")
    print(f"  affidabilita': A={conta['A']}  B={conta['B']}  C={conta['C']}")
    incerti = [g["id"] for g in grafici.values() if "C" in g["affidabilita"]]
    if incerti:
        print(f"  contengono almeno un dato [C] da riverificare: {', '.join(incerti)}")


def inietta(percorso: Path, dati: str):
    """Sostituisce il blocco fra i marcatori DATI:INIZIO e DATI:FINE dentro l'articolo."""
    if not percorso.exists():
        raise ErroreDati(f"file da aggiornare non trovato: {percorso}")
    testo = percorso.read_text(encoding="utf-8")
    marcatori = re.compile(
        r"(/\* DATI:INIZIO[^\n]*\*/\n).*?(\n\s*/\* DATI:FINE \*/)",
        re.DOTALL,
    )
    if not marcatori.search(testo):
        raise ErroreDati("marcatori /* DATI:INIZIO */ e /* DATI:FINE */ non trovati")
    nuovo = marcatori.sub(lambda m: m.group(1) + "const DATI = " + dati + ";" + m.group(2), testo)
    if nuovo != testo:
        percorso.write_text(nuovo, encoding="utf-8")
        print(f"  aggiornato {percorso.name}")
    else:
        print(f"  {percorso.name} era gia' allineato")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="valida soltanto, non scrive")
    ap.add_argument("--inject", metavar="FILE", help="inietta i dati nell'articolo HTML")
    args = ap.parse_args()

    try:
        righe = leggi_csv(CSV_FONTI)
        valida(righe)
        grafici = costruisci(righe)
    except ErroreDati as e:
        print(f"errore nei dati:\n{e}", file=sys.stderr)
        return 1

    print(f"fonti.csv  sha256 {sha256(CSV_FONTI)[:16]}")
    riepilogo(grafici)

    documento = {
        "articolo": "L'eccezione e' gia' nella regola",
        "generato_da": "build_data.py",
        "fonti": "fonti.csv",
        "fonti_sha256": sha256(CSV_FONTI),
        "legenda_affidabilita": {
            "A": "fonte primaria o istituzionale verificata",
            "B": "fonte secondaria affidabile",
            "C": "fonte advocacy o giornalistica, da ricontrollare prima di pubblicare",
        },
        "grafici": grafici,
    }
    testo = json.dumps(documento, ensure_ascii=False, indent=2, sort_keys=True)

    if args.check:
        print("  solo verifica: niente scritto")
        return 0

    JSON_OUT.write_text(testo + "\n", encoding="utf-8")
    print(f"  scritto {JSON_OUT.name}")

    if args.inject:
        try:
            inietta(Path(args.inject), json.dumps(documento["grafici"], ensure_ascii=False))
        except ErroreDati as e:
            print(f"errore in iniezione: {e}", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
