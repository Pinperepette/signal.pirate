#!/usr/bin/env python3
"""
Il Volto è un Vettore — Pipeline Face ID smontata pezzo per pezzo.

1. Legge la mesh 3D del volto (OBJ da ARKit)
2. La visualizza in 3D
3. Genera embedding 128D da foto
4. Confronta volti con distanza coseno
"""

import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import face_recognition
import cv2
import sys
import os
from scipy.spatial.distance import cosine


# ============================================================
# PARTE 1 — Leggere la mesh 3D
# ============================================================

def load_obj(path):
    """Legge un file OBJ e ritorna vertici e facce."""
    vertices = []
    faces = []
    with open(path, 'r') as f:
        for line in f:
            if line.startswith('v '):
                parts = line.strip().split()
                vertices.append([float(parts[1]), float(parts[2]), float(parts[3])])
            elif line.startswith('f '):
                parts = line.strip().split()
                faces.append([int(p) - 1 for p in parts[1:]])
    return np.array(vertices), np.array(faces)


# ============================================================
# PARTE 2 — Visualizzare la mesh 3D
# ============================================================

def render_mesh(vertices, faces, output_path='face_mesh_3d.png'):
    """Renderizza la mesh 3D del volto e salva l'immagine."""
    fig = plt.figure(figsize=(14, 5))
    fig.patch.set_facecolor('#0a0a0a')

    # Vista frontale
    ax1 = fig.add_subplot(131, projection='3d')
    plot_mesh(ax1, vertices, faces, elev=0, azim=0, title='FRONTALE')

    # Vista laterale
    ax2 = fig.add_subplot(132, projection='3d')
    plot_mesh(ax2, vertices, faces, elev=0, azim=90, title='LATERALE')

    # Vista dall\'alto
    ax3 = fig.add_subplot(133, projection='3d')
    plot_mesh(ax3, vertices, faces, elev=90, azim=0, title='DALL\'ALTO')

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight',
                facecolor='#0a0a0a', edgecolor='none')
    plt.close()
    print(f"[+] Mesh 3D salvata: {output_path}")


def plot_mesh(ax, vertices, faces, elev=0, azim=0, title=''):
    """Plotta una singola vista della mesh."""
    ax.set_facecolor('#0a0a0a')

    # Disegna i triangoli
    mesh_polys = []
    for face in faces:
        poly = [vertices[i] for i in face]
        mesh_polys.append(poly)

    collection = Poly3DCollection(mesh_polys, alpha=0.6,
                                   facecolor='#00ff41',
                                   edgecolor='#004d14',
                                   linewidths=0.1)
    ax.add_collection3d(collection)

    # Limiti
    max_range = np.max(np.abs(vertices)) * 1.1
    ax.set_xlim(-max_range, max_range)
    ax.set_ylim(-max_range, max_range)
    ax.set_zlim(-max_range, max_range)

    ax.view_init(elev=elev, azim=azim)
    ax.set_title(title, color='#00ff41', fontsize=10, fontfamily='monospace')
    ax.set_axis_off()


# ============================================================
# PARTE 3 — Da foto a 128 numeri (embedding)
# ============================================================

def get_embedding(image_path):
    """Carica un'immagine e ritorna l'embedding 128D del volto."""
    img = face_recognition.load_image_file(image_path)
    encodings = face_recognition.face_encodings(img)

    if len(encodings) == 0:
        print(f"[!] Nessun volto trovato in: {image_path}")
        return None

    embedding = encodings[0]
    print(f"[+] Embedding estratto da: {os.path.basename(image_path)}")
    print(f"    Dimensioni: {embedding.shape[0]}D")
    print(f"    Primi 5 valori: [{', '.join(f'{v:.4f}' for v in embedding[:5])}]")
    print(f"    Norma: {np.linalg.norm(embedding):.4f}")

    return embedding


# ============================================================
# PARTE 4 — Distanza coseno (il cuore di Face ID)
# ============================================================

def compare_faces(emb1, emb2, label1='A', label2='B'):
    """Confronta due embedding con distanza coseno."""
    dist = cosine(emb1, emb2)
    similarity = 1 - dist
    euclidean = np.linalg.norm(emb1 - emb2)

    print(f"\n{'='*50}")
    print(f"CONFRONTO: {label1} vs {label2}")
    print(f"{'='*50}")
    print(f"  Distanza coseno:   {dist:.6f}")
    print(f"  Similarità coseno: {similarity:.6f}")
    print(f"  Distanza euclidea: {euclidean:.6f}")

    # Soglia tipica face_recognition: 0.6 euclidea
    if euclidean < 0.6:
        print(f"  Verdetto: STESSA PERSONA (< 0.6)")
    else:
        print(f"  Verdetto: PERSONA DIVERSA (>= 0.6)")

    return dist, similarity, euclidean


# ============================================================
# PARTE 5 — Visualizzazione embedding
# ============================================================

def visualize_embedding(embedding, output_path='embedding_128d.png', label=''):
    """Visualizza i 128 numeri come barchart — la tua faccia è questo."""
    fig, ax = plt.subplots(figsize=(14, 3))
    fig.patch.set_facecolor('#0a0a0a')
    ax.set_facecolor('#0a0a0a')

    colors = ['#00ff41' if v >= 0 else '#ff4141' for v in embedding]
    ax.bar(range(128), embedding, color=colors, width=1.0, edgecolor='none')

    ax.set_xlim(0, 127)
    ax.set_xlabel('Dimensione', color='#00ff41', fontfamily='monospace')
    ax.set_ylabel('Valore', color='#00ff41', fontfamily='monospace')
    ax.set_title(f'LA TUA FACCIA IN 128 NUMERI {label}',
                 color='#00ff41', fontsize=12, fontfamily='monospace')
    ax.tick_params(colors='#00ff41')
    for spine in ax.spines.values():
        spine.set_color('#004d14')

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight',
                facecolor='#0a0a0a', edgecolor='none')
    plt.close()
    print(f"[+] Embedding visualizzato: {output_path}")


def visualize_comparison(emb1, emb2, label1, label2, output_path='confronto.png'):
    """Confronto visuale di due embedding sovrapposti."""
    fig, axes = plt.subplots(3, 1, figsize=(14, 8))
    fig.patch.set_facecolor('#0a0a0a')

    for ax in axes:
        ax.set_facecolor('#0a0a0a')
        ax.tick_params(colors='#00ff41')
        for spine in ax.spines.values():
            spine.set_color('#004d14')

    # Embedding 1
    colors1 = ['#00ff41' if v >= 0 else '#ff4141' for v in emb1]
    axes[0].bar(range(128), emb1, color=colors1, width=1.0, edgecolor='none')
    axes[0].set_title(label1, color='#00ff41', fontfamily='monospace')
    axes[0].set_xlim(0, 127)

    # Embedding 2
    colors2 = ['#00aaff' if v >= 0 else '#ff8800' for v in emb2]
    axes[1].bar(range(128), emb2, color=colors2, width=1.0, edgecolor='none')
    axes[1].set_title(label2, color='#00aaff', fontfamily='monospace')
    axes[1].set_xlim(0, 127)

    # Differenza
    diff = emb1 - emb2
    dist = cosine(emb1, emb2)
    colors_diff = ['#ffff00' for _ in diff]
    axes[2].bar(range(128), diff, color=colors_diff, width=1.0, edgecolor='none')
    axes[2].set_title(f'DIFFERENZA (distanza coseno: {dist:.6f})',
                      color='#ffff00', fontfamily='monospace')
    axes[2].set_xlim(0, 127)
    axes[2].set_xlabel('Dimensione', color='#00ff41', fontfamily='monospace')

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight',
                facecolor='#0a0a0a', edgecolor='none')
    plt.close()
    print(f"[+] Confronto visualizzato: {output_path}")


# ============================================================
# MAIN
# ============================================================

if __name__ == '__main__':
    output_dir = os.path.dirname(os.path.abspath(__file__))

    # --- MESH 3D ---
    mesh_path = os.path.expanduser('~/Desktop/face_mesh.obj')
    if os.path.exists(mesh_path):
        print("\n" + "="*50)
        print("PARTE 1 — MESH 3D DEL VOLTO")
        print("="*50)
        vertices, faces = load_obj(mesh_path)
        print(f"[+] Mesh caricata: {len(vertices)} vertici, {len(faces)} triangoli")
        render_mesh(vertices, faces, os.path.join(output_dir, 'face_mesh_3d.png'))
    else:
        print(f"[!] Mesh non trovata: {mesh_path}")

    # --- EMBEDDING DA FOTO ---
    photos_dir = os.path.expanduser('~/Downloads')
    face_photos = []
    for f in sorted(os.listdir(photos_dir)):
        if f.startswith('IMG_') and f.upper().endswith(('.JPG', '.JPEG', '.PNG')):
            face_photos.append(os.path.join(photos_dir, f))

    if not face_photos:
        print("\n[!] Nessuna foto trovata in ~/Downloads/")
        print("    Metti le foto del volto (IMG_*.JPG) in ~/Downloads/")
        sys.exit(0)

    print("\n" + "="*50)
    print("PARTE 2 — DA FOTO A 128 NUMERI")
    print("="*50)

    embeddings = {}
    for photo in face_photos[:5]:  # max 5 foto
        name = os.path.basename(photo)
        emb = get_embedding(photo)
        if emb is not None:
            embeddings[name] = emb
            visualize_embedding(emb,
                os.path.join(output_dir, f'embedding_{name}.png'),
                label=name)

    # --- CONFRONTI ---
    if len(embeddings) >= 2:
        print("\n" + "="*50)
        print("PARTE 3 — CONFRONTI (DISTANZA COSENO)")
        print("="*50)

        names = list(embeddings.keys())
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                compare_faces(
                    embeddings[names[i]], embeddings[names[j]],
                    names[i], names[j]
                )
                visualize_comparison(
                    embeddings[names[i]], embeddings[names[j]],
                    names[i], names[j],
                    os.path.join(output_dir, f'confronto_{i}_{j}.png')
                )

    print("\n[+] Fatto. Controlla i file in:", output_dir)
