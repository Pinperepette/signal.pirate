#!/usr/bin/env python3
"""
06_benchmark.py — Benchmark completo: tempo di inferenza, RTF, throughput.
Testa frasi di lunghezza crescente su tutti i modelli.
pip install kittentts soundfile numpy matplotlib
"""

import os
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
import time
import numpy as np
import matplotlib.pyplot as plt
from kittentts import KittenTTS

OUT_DIR = "output/benchmark"
os.makedirs(OUT_DIR, exist_ok=True)

FRASI = [
    ("corta", "Signal Pirate."),
    ("media", "I take things apart, study how they work, and write down what I find."),
    ("lunga", "Twenty five megabytes for a human voice. No GPU, no server, no connection. Just a file and a terminal. The model generates audio in real time on CPU, offline, without leaving a trace. The voice you hear belongs to no one."),
    ("molto lunga", "In twenty twenty three you needed four GPUs to train a human level text to speech model. In twenty twenty six all you need is a pip install and a twenty five megabyte file. The original model had eight modules, two training stages, a discriminator with three hundred million parameters. What remains at runtime is fifteen million frozen parameters and eight voices compressed in a numpy array. They removed the diffusion, the discriminator, the style encoders. Everything that was needed for training. The result still works because the heavy lifting was already done offline."),
]

MODELLI = [
    ("mini", "KittenML/kitten-tts-mini-0.8"),
    ("micro", "KittenML/kitten-tts-micro-0.8"),
    ("nano-fp32", "KittenML/kitten-tts-nano-0.8-fp32"),
    ("nano-int8", "KittenML/kitten-tts-nano-0.8-int8"),
]

RIPETIZIONI = 3

# Carica tutti i modelli
modelli_caricati = {}
for nome, repo_id in MODELLI:
    print(f"[*] Carico {nome}...")
    modelli_caricati[nome] = KittenTTS(repo_id)

# Benchmark
risultati = {}  # {modello: {frase: {tempo, rtf, durata}}}

for nome_modello, model in modelli_caricati.items():
    risultati[nome_modello] = {}
    print(f"\n{'=' * 50}")
    print(f"BENCHMARK: {nome_modello}")
    print(f"{'=' * 50}")

    for nome_frase, frase in FRASI:
        tempi = []
        durate = []

        for rep in range(RIPETIZIONI):
            t0 = time.time()
            audio = model.generate(frase, voice="Jasper", speed=1.0, clean_text=True)
            dt = time.time() - t0
            tempi.append(dt)
            durate.append(len(audio) / 24000)

        tempo_medio = np.mean(tempi)
        durata_media = np.mean(durate)
        rtf = tempo_medio / durata_media

        risultati[nome_modello][nome_frase] = {
            "tempo": round(tempo_medio, 4),
            "durata": round(durata_media, 2),
            "rtf": round(rtf, 4),
            "char_per_sec": round(len(frase) / tempo_medio, 1),
        }

        print(f"  {nome_frase:>12}: {tempo_medio:.3f}s gen | {durata_media:.2f}s audio | RTF {rtf:.4f} | {len(frase) / tempo_medio:.0f} char/s")

# === Grafico RTF per modello e lunghezza ===
fig, ax = plt.subplots(figsize=(12, 6))
x_labels = [nome for nome, _ in FRASI]
x = np.arange(len(x_labels))
width = 0.18
colors = ['#7c4dff', '#00ff88', '#4ecdc4', '#ff6b6b']

for i, (nome_modello, _) in enumerate(MODELLI):
    rtfs = [risultati[nome_modello][nome_frase]["rtf"] for nome_frase, _ in FRASI]
    ax.bar(x + i * width, rtfs, width, label=nome_modello, color=colors[i], alpha=0.85)

ax.set_xlabel("Lunghezza frase", fontsize=12)
ax.set_ylabel("Real-Time Factor (RTF) — piu' basso = piu' veloce", fontsize=11)
ax.set_title("RTF per modello e lunghezza frase — CPU only", fontsize=14)
ax.set_xticks(x + width * 1.5)
ax.set_xticklabels([f"{n}\n({len(f)} char)" for n, f in FRASI])
ax.legend(fontsize=10)
ax.axhline(y=1.0, color='red', linestyle='--', alpha=0.5, label='Tempo reale')
ax.grid(axis='y', alpha=0.3)
plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, "rtf_benchmark.png"), dpi=150, bbox_inches='tight')
print(f"\n[OK] Salvato: {OUT_DIR}/rtf_benchmark.png")

# === Grafico char/s ===
fig2, ax2 = plt.subplots(figsize=(12, 6))
for i, (nome_modello, _) in enumerate(MODELLI):
    cps = [risultati[nome_modello][nome_frase]["char_per_sec"] for nome_frase, _ in FRASI]
    ax2.bar(x + i * width, cps, width, label=nome_modello, color=colors[i], alpha=0.85)

ax2.set_xlabel("Lunghezza frase", fontsize=12)
ax2.set_ylabel("Caratteri / secondo", fontsize=11)
ax2.set_title("Throughput per modello — caratteri elaborati al secondo su CPU", fontsize=14)
ax2.set_xticks(x + width * 1.5)
ax2.set_xticklabels([f"{n}\n({len(f)} char)" for n, f in FRASI])
ax2.legend(fontsize=10)
ax2.grid(axis='y', alpha=0.3)
plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, "throughput_benchmark.png"), dpi=150, bbox_inches='tight')
print(f"[OK] Salvato: {OUT_DIR}/throughput_benchmark.png")

# Tabella finale
print(f"\n\n{'=' * 80}")
print("RIEPILOGO COMPLETO")
print(f"{'=' * 80}")
for nome_frase, frase in FRASI:
    print(f"\n  Frase: '{frase[:60]}...' ({len(frase)} char)")
    print(f"  {'Modello':<15} {'Gen (s)':<10} {'Audio (s)':<12} {'RTF':<10} {'char/s':<10}")
    print(f"  {'-' * 55}")
    for nome_modello, _ in MODELLI:
        r = risultati[nome_modello][nome_frase]
        print(f"  {nome_modello:<15} {r['tempo']:<10} {r['durata']:<12} {r['rtf']:<10} {r['char_per_sec']:<10}")
