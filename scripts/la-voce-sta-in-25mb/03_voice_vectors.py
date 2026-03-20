#!/usr/bin/env python3
"""
03_voice_vectors.py — Estrae i vettori di stile dal .npz e li visualizza.
t-SNE, heatmap delle distanze, distribuzione per dimensione.
pip install numpy matplotlib scikit-learn huggingface_hub
"""

import os
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
import json
import numpy as np
import matplotlib.pyplot as plt
from sklearn.manifold import TSNE
from sklearn.metrics.pairwise import cosine_distances
from huggingface_hub import hf_hub_download

OUT_DIR = "output/voice_vectors"
os.makedirs(OUT_DIR, exist_ok=True)

# Scarica voci dal modello mini (piu' ricco)
repo_id = "KittenML/kitten-tts-mini-0.8"
config_path = hf_hub_download(repo_id=repo_id, filename="config.json")
with open(config_path) as f:
    config = json.load(f)
voices_path = hf_hub_download(repo_id=repo_id, filename=config["voices"])

voices = np.load(voices_path)

NOMI = ['Bella', 'Jasper', 'Luna', 'Bruno', 'Rosie', 'Hugo', 'Kiki', 'Leo']
KEYS = [
    'expr-voice-2-f', 'expr-voice-2-m', 'expr-voice-3-f', 'expr-voice-3-m',
    'expr-voice-4-f', 'expr-voice-4-m', 'expr-voice-5-f', 'expr-voice-5-m'
]
ALIAS = dict(zip(NOMI, KEYS))

print("[*] Struttura voci:")
for nome, key in ALIAS.items():
    v = voices[key]
    print(f"  {nome:>8} ({key}): shape={v.shape}, dtype={v.dtype}")

# === 1. t-SNE di tutti i vettori ===
print("\n[*] Calcolo t-SNE...")

all_vecs = []
all_labels = []
all_colors = []
colors = plt.cm.Set1(np.linspace(0, 1, len(NOMI)))

for i, (nome, key) in enumerate(ALIAS.items()):
    vecs = voices[key]
    # Prendi un campione (ogni 5 per non sovraccaricare)
    step = max(1, len(vecs) // 20)
    for j in range(0, len(vecs), step):
        all_vecs.append(vecs[j].flatten())
        all_labels.append(nome)
        all_colors.append(colors[i])

X = np.array(all_vecs)
print(f"  Matrice: {X.shape}")

tsne = TSNE(n_components=2, perplexity=min(30, len(X) - 1), random_state=42)
X_2d = tsne.fit_transform(X)

fig, ax = plt.subplots(figsize=(10, 8))
for i, nome in enumerate(NOMI):
    mask = [l == nome for l in all_labels]
    points = X_2d[mask]
    ax.scatter(points[:, 0], points[:, 1], c=[colors[i]], label=nome, s=50, alpha=0.7)
ax.legend(fontsize=10)
ax.set_title("t-SNE dei Voice Vectors — 8 voci nello spazio latente", fontsize=13)
ax.set_xlabel("t-SNE 1")
ax.set_ylabel("t-SNE 2")
plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, "tsne_voci.png"), dpi=150, bbox_inches='tight')
print(f"  Salvato: {OUT_DIR}/tsne_voci.png")

# === 2. Matrice distanze coseno (vettore medio per voce) ===
print("\n[*] Matrice distanze coseno...")

mean_vecs = []
for nome, key in ALIAS.items():
    vecs = voices[key]
    mean_vecs.append(vecs.mean(axis=0).flatten())

mean_matrix = np.array(mean_vecs)
dist_matrix = cosine_distances(mean_matrix)

fig, ax = plt.subplots(figsize=(8, 7))
im = ax.imshow(dist_matrix, cmap='magma_r', interpolation='nearest')
ax.set_xticks(range(len(NOMI)))
ax.set_yticks(range(len(NOMI)))
ax.set_xticklabels(NOMI, rotation=45, ha='right', fontsize=10)
ax.set_yticklabels(NOMI, fontsize=10)

for i in range(len(NOMI)):
    for j in range(len(NOMI)):
        ax.text(j, i, f"{dist_matrix[i, j]:.3f}", ha='center', va='center',
                fontsize=8, color='white' if dist_matrix[i, j] > 0.3 else 'black')

plt.colorbar(im, ax=ax, label="Distanza coseno")
ax.set_title("Distanza coseno tra voci (vettore medio)", fontsize=13)
plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, "distanze_coseno.png"), dpi=150, bbox_inches='tight')
print(f"  Salvato: {OUT_DIR}/distanze_coseno.png")

# === 3. Come cambia lo stile con la lunghezza del testo ===
print("\n[*] Variazione stile per lunghezza testo...")

fig, axes = plt.subplots(2, 4, figsize=(16, 8))
for idx, (nome, key) in enumerate(ALIAS.items()):
    ax = axes[idx // 4][idx % 4]
    vecs = voices[key]

    # Norma L2 di ogni vettore
    norms = np.linalg.norm(vecs.reshape(len(vecs), -1), axis=1)
    ax.plot(norms, color=colors[idx], linewidth=1.5)
    ax.set_title(nome, fontsize=11)
    ax.set_xlabel("Indice (~ lunghezza testo)")
    ax.set_ylabel("Norma L2")
    ax.grid(alpha=0.3)

plt.suptitle("Norma L2 dei voice vectors per posizione — lo stile cambia con la lunghezza", fontsize=13)
plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, "norme_per_posizione.png"), dpi=150, bbox_inches='tight')
print(f"  Salvato: {OUT_DIR}/norme_per_posizione.png")

print("\n[OK] Tutti i grafici generati.")
