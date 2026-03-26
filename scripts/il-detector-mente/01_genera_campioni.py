#!/usr/bin/env python3
"""
01_genera_campioni.py — Genera campioni di testo da tre modelli
Chiede lo stesso prompt a Claude, ChatGPT e un modello locale (Ollama).
Salva i risultati in output/campioni.json

Requisiti:
  pip install anthropic openai requests

Configurazione:
  export ANTHROPIC_API_KEY=...
  export OPENAI_API_KEY=...
  Ollama deve girare su localhost:11434 con un modello scaricato (default: llama3.1)
"""

import json
import os
import time
import sys

# --- Configurazione ---
N_CAMPIONI = 50
OLLAMA_MODEL = os.environ.get('OLLAMA_MODEL', 'llama3.1:8b')
OLLAMA_URL = os.environ.get('OLLAMA_URL', 'http://localhost:11434')
OUTPUT_DIR = 'output'

# Prompt vari per avere diversita' nei campioni
PROMPTS = [
    'Spiega come funziona il protocollo TCP in modo tecnico.',
    'Descrivi il funzionamento di una hash table e le strategie di collision resolution.',
    'Spiega la differenza tra processi e thread in un sistema operativo moderno.',
    'Come funziona il garbage collector in Java? Descrivi le generazioni e gli algoritmi.',
    'Spiega il teorema CAP nei sistemi distribuiti con esempi concreti.',
    'Descrivi come funziona TLS 1.3 e cosa cambia rispetto a TLS 1.2.',
    'Spiega il funzionamento di un B-tree e perche\' i database lo usano per gli indici.',
    'Come funziona il meccanismo di attention nei transformer?',
    'Descrivi il protocollo Raft per il consenso distribuito.',
    'Spiega come funziona la memoria virtuale e il page fault handling.',
    'Descrivi l\'architettura di un compilatore moderno, dal lexer al codegen.',
    'Come funziona il protocollo BGP e perche\' e\' critico per Internet?',
    'Spiega il funzionamento di ECDSA e perche\' si usa nelle blockchain.',
    'Descrivi come funziona un container Linux a livello di kernel (namespaces, cgroups).',
    'Spiega il funzionamento di MapReduce e i suoi limiti.',
    'Come funziona il branch prediction in un processore moderno?',
    'Descrivi il protocollo DNS e gli attacchi possibili (cache poisoning, DNS rebinding).',
    'Spiega come funziona WebAssembly e quali problemi risolve.',
    'Descrivi il funzionamento di un SSD a livello di NAND flash e FTL.',
    'Come funziona il protocollo QUIC e perche\' sostituisce TCP+TLS?',
    'Spiega il funzionamento di consistent hashing e dove si usa.',
    'Descrivi come funziona un debugger a livello di sistema (ptrace, breakpoint).',
    'Spiega il funzionamento di ZFS: copy-on-write, checksum, self-healing.',
    'Come funziona il meccanismo di backpressure nei sistemi reactive?',
    'Descrivi il funzionamento di un bloom filter e i suoi falsi positivi.',
]

os.makedirs(OUTPUT_DIR, exist_ok=True)


def genera_claude(prompt):
    """Genera un campione con Claude."""
    import anthropic
    client = anthropic.Anthropic()
    resp = client.messages.create(
        model='claude-sonnet-4-20250514',
        max_tokens=1024,
        messages=[{'role': 'user', 'content': prompt}],
    )
    return resp.content[0].text


def genera_chatgpt(prompt):
    """Genera un campione con ChatGPT."""
    import openai
    resp = openai.ChatCompletion.create(
        model='gpt-4o',
        max_tokens=1024,
        messages=[{'role': 'user', 'content': prompt}],
    )
    return resp.choices[0].message.content


def genera_ollama(prompt):
    """Genera un campione con Ollama (modello locale)."""
    import requests
    resp = requests.post(
        f'{OLLAMA_URL}/api/generate',
        json={
            'model': OLLAMA_MODEL,
            'prompt': prompt,
            'stream': False,
            'options': {'num_predict': 1024},
        },
    )
    resp.raise_for_status()
    return resp.json()['response']


def salva(campioni):
    """Salva il JSON dopo ogni campione, cosi' non si perde niente."""
    out_path = os.path.join(OUTPUT_DIR, 'campioni.json')
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(campioni, f, ensure_ascii=False, indent=2)


def carica_esistenti():
    """Carica campioni gia' generati, se esistono."""
    out_path = os.path.join(OUTPUT_DIR, 'campioni.json')
    if os.path.exists(out_path):
        with open(out_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []


def main():
    campioni = carica_esistenti()

    # trova quali ID gia' esistono
    ids_fatti = {c['id'] for c in campioni if c.get('testo') is not None}
    if ids_fatti:
        print(f'Trovati {len(ids_fatti)} campioni gia\' generati, riprendo da dove ero rimasto.\n')

    generatori = {
        'claude': genera_claude,
        'chatgpt': genera_chatgpt,
        'ollama': genera_ollama,
    }

    for i in range(N_CAMPIONI):
        prompt = PROMPTS[i % len(PROMPTS)]

        # controlla se tutti e 3 i modelli per questo indice sono gia' fatti
        tutti_fatti = all(f'{nome}_{i:03d}' in ids_fatti for nome in generatori)
        if tutti_fatti:
            continue

        print(f'\n--- Campione {i+1}/{N_CAMPIONI} ---')
        print(f'Prompt: {prompt[:60]}...')

        for nome, fn in generatori.items():
            campione_id = f'{nome}_{i:03d}'
            if campione_id in ids_fatti:
                print(f'  {nome}... gia\' fatto, salto')
                continue

            try:
                print(f'  {nome}...', end=' ', flush=True)
                t0 = time.time()
                testo = fn(prompt)
                dt = time.time() - t0
                campioni.append({
                    'id': campione_id,
                    'modello': nome,
                    'prompt': prompt,
                    'testo': testo,
                    'lunghezza': len(testo),
                    'tempo_s': round(dt, 2),
                })
                print(f'{len(testo)} char, {dt:.1f}s')
            except Exception as e:
                print(f'ERRORE: {e}')
                campioni.append({
                    'id': campione_id,
                    'modello': nome,
                    'prompt': prompt,
                    'testo': None,
                    'lunghezza': 0,
                    'tempo_s': 0,
                    'errore': str(e),
                })

            # salva dopo ogni singolo campione
            salva(campioni)

        # pausa tra batch per rate limit
        time.sleep(1)

    # statistiche finali
    ok = [c for c in campioni if c['testo'] is not None]
    per_modello = {}
    for c in ok:
        per_modello.setdefault(c['modello'], []).append(c)

    print(f'\n=== Risultati ===')
    print(f'Totale campioni: {len(ok)}/{len(campioni)}')
    for m, cc in sorted(per_modello.items()):
        lunghezze = [c['lunghezza'] for c in cc]
        media = sum(lunghezze) / len(lunghezze)
        print(f'  {m}: {len(cc)} campioni, lunghezza media {media:.0f} char')

    print(f'\nSalvato in {os.path.join(OUTPUT_DIR, "campioni.json")}')


if __name__ == '__main__':
    main()
