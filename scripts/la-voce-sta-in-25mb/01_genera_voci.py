#!/usr/bin/env python3
"""
01_genera_voci.py — Genera tutte le 8 voci con la stessa frase.
pip install https://github.com/KittenML/KittenTTS/releases/download/0.8.1/kittentts-0.8.1-py3-none-any.whl
pip install soundfile numpy
"""

import os
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
import time
import numpy as np
import soundfile as sf
from kittentts import KittenTTS

OUT_DIR = "output/voci"
os.makedirs(OUT_DIR, exist_ok=True)

FRASE = "Signal Pirate. I take things apart, study how they work, and write down what I find. Twenty five megabytes is all it takes for a human voice."

MODELLO = "KittenML/kitten-tts-mini-0.8"

print(f"[*] Carico modello: {MODELLO}")
model = KittenTTS(MODELLO)

voci = model.available_voices
print(f"[*] Voci disponibili: {voci}")

risultati = []

for voce in voci:
    print(f"\n[>] Genero: {voce}")
    t0 = time.time()
    audio = model.generate(FRASE, voice=voce, speed=1.0, clean_text=True)
    dt = time.time() - t0

    path = os.path.join(OUT_DIR, f"{voce.lower()}.wav")
    sf.write(path, audio, 24000)

    durata_audio = len(audio) / 24000
    char_per_sec = len(FRASE) / dt

    risultati.append({
        "voce": voce,
        "durata_audio_sec": round(durata_audio, 2),
        "tempo_generazione_sec": round(dt, 2),
        "char_per_sec": round(char_per_sec, 1),
        "campioni": len(audio),
    })

    print(f"    Audio: {durata_audio:.2f}s | Generato in: {dt:.2f}s | {char_per_sec:.0f} char/s")
    print(f"    Salvato: {path}")

print("\n" + "=" * 60)
print(f"{'Voce':<12} {'Audio (s)':<12} {'Gen (s)':<12} {'char/s':<10}")
print("-" * 60)
for r in risultati:
    print(f"{r['voce']:<12} {r['durata_audio_sec']:<12} {r['tempo_generazione_sec']:<12} {r['char_per_sec']:<10}")
print("=" * 60)
