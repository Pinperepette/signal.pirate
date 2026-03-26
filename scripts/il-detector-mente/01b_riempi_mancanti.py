#!/usr/bin/env python3
"""
01b_riempi_mancanti.py — Ritenta solo i campioni falliti
Legge output/campioni.json, trova quelli con testo=None, li rigenera.
Sovrascrive il file con i risultati aggiornati.

Usa un timeout piu' lungo per Ollama (300s) e riprova fino a 3 volte.
"""

import json
import os
import time

# riusa le funzioni di generazione dallo script principale
from importlib.util import spec_from_file_location, module_from_spec
spec = spec_from_file_location('gen', os.path.join(os.path.dirname(__file__), '01_genera_campioni.py'))
gen = module_from_spec(spec)
spec.loader.exec_module(gen)

INPUT_FILE = 'output/campioni.json'
MAX_RETRIES = 3
OLLAMA_TIMEOUT = None  # nessun timeout, il modello locale ci mette quanto ci mette


def genera_ollama_lento(prompt):
    """Ollama con timeout piu' lungo."""
    import requests
    resp = requests.post(
        f'{gen.OLLAMA_URL}/api/generate',
        json={
            'model': gen.OLLAMA_MODEL,
            'prompt': prompt,
            'stream': False,
            'options': {'num_predict': 1024},
        },
        timeout=OLLAMA_TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()['response']


def main():
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        campioni = json.load(f)

    mancanti = [(i, c) for i, c in enumerate(campioni) if c.get('testo') is None]
    print(f'Campioni mancanti: {len(mancanti)}')

    if not mancanti:
        print('Niente da fare.')
        return

    generatori = {
        'claude': gen.genera_claude,
        'chatgpt': gen.genera_chatgpt,
        'ollama': genera_ollama_lento,
    }

    recuperati = 0
    falliti = 0

    for idx, campione in mancanti:
        modello = campione['modello']
        prompt = campione['prompt']
        fn = generatori.get(modello)

        if fn is None:
            print(f'  {campione["id"]}: modello sconosciuto "{modello}", salto')
            falliti += 1
            continue

        print(f'  {campione["id"]} ({modello})...', end=' ', flush=True)

        for tentativo in range(1, MAX_RETRIES + 1):
            try:
                t0 = time.time()
                testo = fn(prompt)
                dt = time.time() - t0

                campioni[idx] = {
                    'id': campione['id'],
                    'modello': modello,
                    'prompt': prompt,
                    'testo': testo,
                    'lunghezza': len(testo),
                    'tempo_s': round(dt, 2),
                }
                print(f'OK ({len(testo)} char, {dt:.1f}s)')
                recuperati += 1
                break

            except Exception as e:
                if tentativo < MAX_RETRIES:
                    print(f'retry {tentativo}/{MAX_RETRIES}...', end=' ', flush=True)
                    time.sleep(3)
                else:
                    print(f'FALLITO dopo {MAX_RETRIES} tentativi: {e}')
                    falliti += 1

        time.sleep(1)

    # salva
    with open(INPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(campioni, f, ensure_ascii=False, indent=2)

    ok = sum(1 for c in campioni if c.get('testo') is not None)
    ancora = sum(1 for c in campioni if c.get('testo') is None)

    print(f'\n=== Risultato ===')
    print(f'Recuperati: {recuperati}')
    print(f'Ancora falliti: {falliti}')
    print(f'Totale OK: {ok}/{len(campioni)}')
    if ancora:
        print(f'Mancanti rimanenti: {ancora} (rilancia lo script)')


if __name__ == '__main__':
    main()
