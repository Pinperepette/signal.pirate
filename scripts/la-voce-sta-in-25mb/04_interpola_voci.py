#!/usr/bin/env python3
"""
04_interpola_voci.py — Interpola tra due voci nello spazio latente.
Genera audio per ogni step dell'interpolazione.
pip install kittentts soundfile numpy huggingface_hub
"""

import os
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
import json
import numpy as np
import soundfile as sf
import onnxruntime as ort
from huggingface_hub import hf_hub_download
from kittentts.onnx_model import KittenTTS_1_Onnx

OUT_DIR = "output/interpolazione"
os.makedirs(OUT_DIR, exist_ok=True)

# Config
VOCE_A = "expr-voice-2-f"   # Bella
VOCE_B = "expr-voice-2-m"   # Jasper
NOME_A = "Bella"
NOME_B = "Jasper"
STEPS = 7  # 0.0, ~0.17, ~0.33, 0.5, ~0.67, ~0.83, 1.0
FRASE = "The voice you are hearing does not exist. It is a point halfway between two speakers."

# Scarica modello
repo_id = "KittenML/kitten-tts-mini-0.8"
config_path = hf_hub_download(repo_id=repo_id, filename="config.json")
with open(config_path) as f:
    config = json.load(f)

model_path = hf_hub_download(repo_id=repo_id, filename=config["model_file"])
voices_path = hf_hub_download(repo_id=repo_id, filename=config["voices"])

# Carica modello e voci
model = KittenTTS_1_Onnx(
    model_path=model_path,
    voices_path=voices_path,
    speed_priors=config.get("speed_priors", {}),
    voice_aliases=config.get("voice_aliases", {})
)

voices = np.load(voices_path)
vec_a = voices[VOCE_A]
vec_b = voices[VOCE_B]

print(f"[*] Interpolazione: {NOME_A} -> {NOME_B}")
print(f"[*] Shape vettori: A={vec_a.shape}, B={vec_b.shape}")
print(f"[*] Frase: {FRASE}")
print(f"[*] Steps: {STEPS}")

# Per ogni step, interpola i vettori e genera
alphas = np.linspace(0.0, 1.0, STEPS)

for i, alpha in enumerate(alphas):
    print(f"\n[>] Step {i}/{STEPS - 1} — alpha={alpha:.2f} ({NOME_A} {100 * (1 - alpha):.0f}% / {NOME_B} {100 * alpha:.0f}%)")

    # Interpola il vettore di stile
    ref_id = min(len(FRASE), min(vec_a.shape[0], vec_b.shape[0]) - 1)
    style_a = vec_a[ref_id:ref_id + 1]
    style_b = vec_b[ref_id:ref_id + 1]
    style_mix = (1.0 - alpha) * style_a + alpha * style_b

    # Prepara input manualmente
    phonemes_list = model.phonemizer.phonemize([FRASE])
    from kittentts.onnx_model import basic_english_tokenize
    phonemes = basic_english_tokenize(phonemes_list[0])
    phonemes = ' '.join(phonemes)
    tokens = model.text_cleaner(phonemes)
    tokens.insert(0, 0)
    tokens.append(10)
    tokens.append(0)

    input_ids = np.array([tokens], dtype=np.int64)

    onnx_inputs = {
        "input_ids": input_ids,
        "style": style_mix.astype(np.float32),
        "speed": np.array([1.0], dtype=np.float32),
    }

    outputs = model.session.run(None, onnx_inputs)
    audio = outputs[0][..., :-5000]

    fname = f"step_{i:02d}_alpha_{alpha:.2f}.wav"
    path = os.path.join(OUT_DIR, fname)
    sf.write(path, audio.flatten(), 24000)
    print(f"    Salvato: {path} ({len(audio.flatten()) / 24000:.2f}s)")

print(f"\n[OK] {STEPS} file generati in {OUT_DIR}/")
print(f"[*] Ascolta in sequenza per sentire la transizione {NOME_A} -> {NOME_B}")
