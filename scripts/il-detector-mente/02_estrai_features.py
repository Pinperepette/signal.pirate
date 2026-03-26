#!/usr/bin/env python3
"""
02_estrai_features.py — Estrai feature stilometriche dai campioni
Legge output/campioni.json, calcola feature statistiche per ogni testo,
salva output/features.csv

Feature estratte:
  - lunghezza totale (char)
  - n. frasi
  - lunghezza media frasi (parole)
  - deviazione standard lunghezza frasi
  - type-token ratio (vocabolario / parole totali)
  - hapax ratio (parole usate una volta / vocabolario)
  - frequenza punteggiatura (per 1000 char)
  - frequenza virgole, punti, due punti, punto e virgola
  - rapporto parole lunghe (>= 8 char)
  - entropia caratteri (Shannon)
  - ripetizione bigrammi (% bigrammi ripetuti)
  - lunghezza media parole
  - % frasi che iniziano con congiunzione

Requisiti: nessuno (solo stdlib)
"""

import json
import csv
import math
import re
import os
from collections import Counter

INPUT_FILE = 'output/campioni.json'
OUTPUT_FILE = 'output/features.csv'


def tokenizza_frasi(testo):
    """Split in frasi usando punteggiatura forte."""
    frasi = re.split(r'[.!?]+', testo)
    return [f.strip() for f in frasi if f.strip() and len(f.strip()) > 5]


def tokenizza_parole(testo):
    """Estrai parole (alfanumeriche)."""
    return re.findall(r'\b\w+\b', testo.lower())


def shannon_entropy(testo):
    """Entropia di Shannon sui caratteri."""
    if not testo:
        return 0.0
    freq = Counter(testo)
    n = len(testo)
    return -sum((c / n) * math.log2(c / n) for c in freq.values())


def bigrammi(parole):
    """Genera bigrammi da lista parole."""
    return [(parole[i], parole[i+1]) for i in range(len(parole) - 1)]


def estrai_features(testo):
    """Calcola tutte le feature per un testo."""
    if not testo:
        return None

    frasi = tokenizza_frasi(testo)
    parole = tokenizza_parole(testo)

    if len(parole) < 10 or len(frasi) < 3:
        return None

    # lunghezze frasi in parole
    len_frasi = [len(tokenizza_parole(f)) for f in frasi]
    len_frasi = [l for l in len_frasi if l > 0]

    if not len_frasi:
        return None

    media_len_frasi = sum(len_frasi) / len(len_frasi)
    std_len_frasi = (sum((l - media_len_frasi)**2 for l in len_frasi) / len(len_frasi)) ** 0.5

    # type-token ratio
    vocab = set(parole)
    ttr = len(vocab) / len(parole)

    # hapax ratio
    freq_parole = Counter(parole)
    hapax = sum(1 for w, c in freq_parole.items() if c == 1)
    hapax_ratio = hapax / len(vocab) if vocab else 0

    # punteggiatura
    n_char = len(testo)
    n_virgole = testo.count(',')
    n_punti = testo.count('.')
    n_due_punti = testo.count(':')
    n_punto_virgola = testo.count(';')
    n_punti_escl = testo.count('!')
    n_punti_interr = testo.count('?')
    n_trattini = testo.count('—') + testo.count('–') + testo.count('-')
    freq_punct = (n_virgole + n_punti + n_due_punti + n_punto_virgola +
                  n_punti_escl + n_punti_interr) / n_char * 1000

    # parole lunghe
    parole_lunghe = sum(1 for p in parole if len(p) >= 8)
    ratio_lunghe = parole_lunghe / len(parole)

    # lunghezza media parole
    media_len_parole = sum(len(p) for p in parole) / len(parole)

    # entropia
    entropia = shannon_entropy(testo)

    # bigrammi ripetuti
    bg = bigrammi(parole)
    if bg:
        freq_bg = Counter(bg)
        ripetuti = sum(1 for b, c in freq_bg.items() if c > 1)
        ratio_bg_rip = ripetuti / len(freq_bg)
    else:
        ratio_bg_rip = 0

    # frasi che iniziano con congiunzione
    congiunzioni = {'e', 'ma', 'pero', 'però', 'quindi', 'inoltre', 'tuttavia',
                    'and', 'but', 'however', 'therefore', 'moreover', 'furthermore',
                    'additionally', 'consequently', 'nevertheless'}
    n_conj_start = 0
    for f in frasi:
        prima_parola = tokenizza_parole(f)
        if prima_parola and prima_parola[0] in congiunzioni:
            n_conj_start += 1
    ratio_conj_start = n_conj_start / len(frasi) if frasi else 0

    # paragrafi (stima: doppio newline)
    paragrafi = [p.strip() for p in testo.split('\n\n') if p.strip()]
    n_paragrafi = len(paragrafi)

    return {
        'lunghezza_char': n_char,
        'n_parole': len(parole),
        'n_frasi': len(frasi),
        'media_len_frasi': round(media_len_frasi, 2),
        'std_len_frasi': round(std_len_frasi, 2),
        'ttr': round(ttr, 4),
        'hapax_ratio': round(hapax_ratio, 4),
        'media_len_parole': round(media_len_parole, 2),
        'ratio_parole_lunghe': round(ratio_lunghe, 4),
        'entropia_char': round(entropia, 4),
        'freq_punct_1k': round(freq_punct, 2),
        'virgole_1k': round(n_virgole / n_char * 1000, 2),
        'punti_1k': round(n_punti / n_char * 1000, 2),
        'due_punti_1k': round(n_due_punti / n_char * 1000, 2),
        'punto_virgola_1k': round(n_punto_virgola / n_char * 1000, 2),
        'trattini_1k': round(n_trattini / n_char * 1000, 2),
        'ratio_bg_ripetuti': round(ratio_bg_rip, 4),
        'ratio_conj_start': round(ratio_conj_start, 4),
        'n_paragrafi': n_paragrafi,
    }


def main():
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        campioni = json.load(f)

    risultati = []
    scartati = 0

    for c in campioni:
        if c.get('testo') is None:
            scartati += 1
            continue

        feat = estrai_features(c['testo'])
        if feat is None:
            scartati += 1
            continue

        riga = {
            'id': c['id'],
            'modello': c['modello'],
            'prompt': c['prompt'][:80],
        }
        riga.update(feat)
        risultati.append(riga)

    if not risultati:
        print('Nessun campione valido trovato.')
        return

    # salva CSV
    fieldnames = list(risultati[0].keys())
    with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(risultati)

    # statistiche
    per_modello = {}
    for r in risultati:
        per_modello.setdefault(r['modello'], []).append(r)

    print(f'=== Feature estratte ===')
    print(f'Campioni validi: {len(risultati)} (scartati: {scartati})')
    print()

    metriche_chiave = ['media_len_frasi', 'ttr', 'entropia_char', 'virgole_1k',
                       'ratio_parole_lunghe', 'ratio_bg_ripetuti']

    header = f'{"Modello":<12}'
    for m in metriche_chiave:
        header += f'{m:>22}'
    print(header)
    print('-' * len(header))

    for modello, righe in sorted(per_modello.items()):
        riga = f'{modello:<12}'
        for m in metriche_chiave:
            vals = [r[m] for r in righe]
            media = sum(vals) / len(vals)
            riga += f'{media:>22.4f}'
        print(riga)

    print(f'\nSalvato in {OUTPUT_FILE}')


if __name__ == '__main__':
    main()
