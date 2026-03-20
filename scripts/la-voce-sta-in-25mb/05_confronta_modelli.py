#!/usr/bin/env python3
"""
05_confronta_modelli.py — Confronta mel spectrogram tra le 4 varianti del modello.
Genera la stessa frase con mini/micro/nano/nano-int8 e confronta.
pip install kittentts soundfile numpy matplotlib librosa
"""

import os
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
import time
import numpy as np
import soundfile as sf
import matplotlib.pyplot as plt
import librosa
import librosa.display
from kittentts import KittenTTS

OUT_DIR = "output/confronto"
os.makedirs(OUT_DIR, exist_ok=True)

FRASE = "Reverse engineering digital attention. The pirate takes everything apart."
VOCE = "Jasper"
SR = 24000

MODELLI = [
    ("mini (80M)", "KittenML/kitten-tts-mini-0.8"),
    ("micro (40M)", "KittenML/kitten-tts-micro-0.8"),
    ("nano fp32 (15M)", "KittenML/kitten-tts-nano-0.8-fp32"),
    ("nano int8 (15M)", "KittenML/kitten-tts-nano-0.8-int8"),
]

risultati = []

fig, axes = plt.subplots(len(MODELLI), 1, figsize=(14, 4 * len(MODELLI)))

for idx, (nome, repo_id) in enumerate(MODELLI):
    print(f"\n[*] Carico: {nome}")
    model = KittenTTS(repo_id)

    t0 = time.time()
    audio = model.generate(FRASE, voice=VOCE, speed=1.0, clean_text=True)
    dt = time.time() - t0

    # Salva WAV
    wav_path = os.path.join(OUT_DIR, f"{nome.split()[0].lower()}.wav")
    sf.write(wav_path, audio, SR)

    durata = len(audio) / SR
    risultati.append({
        "modello": nome,
        "tempo_gen": round(dt, 3),
        "durata_audio": round(durata, 2),
        "campioni": len(audio),
        "rtf": round(dt / durata, 4),
    })

    print(f"  Generato in {dt:.3f}s | Audio: {durata:.2f}s | RTF: {dt / durata:.4f}")

    # Mel spectrogram
    ax = axes[idx]
    S = librosa.feature.melspectrogram(y=audio.astype(np.float32), sr=SR, n_mels=80, fmax=8000)
    S_db = librosa.power_to_db(S, ref=np.max)
    librosa.display.specshow(S_db, sr=SR, x_axis='time', y_axis='mel', ax=ax, cmap='magma')
    ax.set_title(f"{nome} — RTF: {dt / durata:.4f}", fontsize=12)
    ax.set_ylabel("Mel")

plt.suptitle(f'Mel Spectrogram — "{FRASE[:50]}..." — Voce: {VOCE}', fontsize=14)
plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, "mel_confronto.png"), dpi=150, bbox_inches='tight')
print(f"\n[OK] Salvato: {OUT_DIR}/mel_confronto.png")

# Tabella riepilogo
print(f"\n{'=' * 70}")
print(f"{'Modello':<22} {'Gen (s)':<10} {'Audio (s)':<12} {'RTF':<10} {'Campioni':<12}")
print("-" * 70)
for r in risultati:
    print(f"  {r['modello']:<22} {r['tempo_gen']:<10} {r['durata_audio']:<12} {r['rtf']:<10} {r['campioni']:<12}")

# === Differenza spettrale tra mini e nano-int8 ===
print(f"\n[*] Calcolo differenza spettrale mini vs nano-int8...")
audio_mini, _ = sf.read(os.path.join(OUT_DIR, "mini.wav"))
audio_nano, _ = sf.read(os.path.join(OUT_DIR, "nano.wav"))

# Allinea lunghezze
min_len = min(len(audio_mini), len(audio_nano))
audio_mini = audio_mini[:min_len].astype(np.float32)
audio_nano = audio_nano[:min_len].astype(np.float32)

S_mini = librosa.feature.melspectrogram(y=audio_mini, sr=SR, n_mels=80, fmax=8000)
S_nano = librosa.feature.melspectrogram(y=audio_nano, sr=SR, n_mels=80, fmax=8000)

S_mini_db = librosa.power_to_db(S_mini, ref=np.max)
S_nano_db = librosa.power_to_db(S_nano, ref=np.max)

min_t = min(S_mini_db.shape[1], S_nano_db.shape[1])
diff = np.abs(S_mini_db[:, :min_t] - S_nano_db[:, :min_t])

fig2, ax2 = plt.subplots(figsize=(14, 4))
im = ax2.imshow(diff, aspect='auto', origin='lower', cmap='hot', interpolation='nearest')
plt.colorbar(im, ax=ax2, label='|dB|')
ax2.set_title("Differenza spettrale: mini (80M) vs nano-int8 (15M) — dove si perde qualita'", fontsize=12)
ax2.set_xlabel("Frame")
ax2.set_ylabel("Mel bin")
plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, "diff_spettrale.png"), dpi=150, bbox_inches='tight')
print(f"[OK] Salvato: {OUT_DIR}/diff_spettrale.png")
print(f"[*] Differenza media: {diff.mean():.2f} dB | Max: {diff.max():.2f} dB")
