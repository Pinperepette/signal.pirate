"""
05_high_dim_geometry.py
Visualizzazione di due fenomeni di concentrazione di misura in alta dimensione,
quelli che fanno funzionare lattice-crypto:

  1) Norma di un vettore gaussiano isotropo N(0, I_n) si concentra su sqrt(n).
     (Il "rumore vive in una buccia, non in una palla")

  2) Prodotto scalare di due vettori uniformi sulla sfera unitaria si concentra a 0.
     (Due vettori "a caso" sono quasi sempre ortogonali)

Per dim = 1, 10, 100, 768. Il valore 768 e' la dimensione effettiva di Kyber768.

Output: high_dim_geometry.png
"""
import numpy as np
import matplotlib.pyplot as plt
import time

RNG = np.random.default_rng(seed=2026)
DIMS = [1, 10, 100, 768]
N_SAMPLES = 50000

print(f"Generating {N_SAMPLES:,} samples per dimension, dimensions = {DIMS}")
t0 = time.time()

# Pre-compute statistics for plotting and reporting
gaussian_norms = {}
inner_products = {}
for n in DIMS:
    # Norm of standard gaussian in dim n
    g = RNG.standard_normal((N_SAMPLES, n))
    norms = np.linalg.norm(g, axis=1)
    gaussian_norms[n] = norms

    # Inner product of two random unit vectors in dim n
    u = RNG.standard_normal((N_SAMPLES, n))
    u /= np.linalg.norm(u, axis=1, keepdims=True)
    v = RNG.standard_normal((N_SAMPLES, n))
    v /= np.linalg.norm(v, axis=1, keepdims=True)
    dots = np.einsum('ij,ij->i', u, v)
    inner_products[n] = dots

    sqrtn = float(np.sqrt(n))
    mean_norm = float(norms.mean())
    std_norm = float(norms.std())
    abs_dot_mean = float(np.abs(dots).mean())
    one_over_sqrtn = 1.0 / np.sqrt(n) if n > 0 else float('nan')
    print(f"  n={n:4d}  ||g||: mean={mean_norm:7.3f}  sqrt(n)={sqrtn:7.3f}  std={std_norm:.3f}"
          f"   |<u,v>| mean={abs_dot_mean:.4f}  1/sqrt(n)={one_over_sqrtn:.4f}")

print(f"Sampling done in {time.time() - t0:.1f}s.")

# ---- Plot ----
fig, axes = plt.subplots(2, 4, figsize=(16, 8.5), facecolor='#0d1117')

ACCENT_GREEN = '#00ff88'
ACCENT_PURPLE = '#7c4dff'
ACCENT_RED = '#ff6b6b'
TEXT_DIM = '#888'
SPINE = '#333'

for col, n in enumerate(DIMS):
    # ---- TOP: norm of gaussian ----
    ax = axes[0, col]
    ax.set_facecolor('#0d1117')
    data = gaussian_norms[n]
    sqrtn = np.sqrt(n)

    # adapt x-range to where the mass actually is
    lo, hi = data.min(), data.max()
    ax.hist(data, bins=70, range=(lo, hi),
            color=ACCENT_GREEN, alpha=0.85, density=True, edgecolor='none')
    ax.axvline(sqrtn, color=ACCENT_RED, linestyle='--', alpha=0.85, linewidth=1.5)
    ax.text(sqrtn, ax.get_ylim()[1] * 0.92, f' $\\sqrt{{n}}={sqrtn:.2f}$',
            color=ACCENT_RED, fontsize=10, family='monospace', ha='left', va='top')

    ax.set_title(f'n = {n}', color='white', fontsize=12, family='monospace', pad=8)
    if col == 0:
        ax.set_ylabel('Norma di $X \\sim \\mathcal{N}(0,I_n)$\n(densità)',
                      color=TEXT_DIM, family='monospace', fontsize=10)
    ax.tick_params(colors=TEXT_DIM, labelsize=8)
    for s in ax.spines.values():
        s.set_color(SPINE)
    ax.grid(True, alpha=0.1, color='#444')

    # ---- BOTTOM: inner product ----
    ax = axes[1, col]
    ax.set_facecolor('#0d1117')
    data = inner_products[n]
    # Same x-range for all bottom panels to compare collapse
    ax.hist(data, bins=70, range=(-1.05, 1.05),
            color=ACCENT_PURPLE, alpha=0.85, density=True, edgecolor='none')
    ax.axvline(0, color=ACCENT_RED, linestyle='--', alpha=0.85, linewidth=1.5)
    one_over_sqrtn = 1.0 / np.sqrt(n) if n > 0 else 0
    ax.text(0.0, ax.get_ylim()[1] * 0.92,
            f' $1/\\sqrt{{n}}={one_over_sqrtn:.3f}$',
            color=ACCENT_RED, fontsize=10, family='monospace', ha='left', va='top')

    if col == 0:
        ax.set_ylabel('$\\langle u,v\\rangle$ di vettori\nuniformi su $S^{n-1}$',
                      color=TEXT_DIM, family='monospace', fontsize=10)
    ax.set_xlim(-1.05, 1.05)
    ax.tick_params(colors=TEXT_DIM, labelsize=8)
    for s in ax.spines.values():
        s.set_color(SPINE)
    ax.grid(True, alpha=0.1, color='#444')

fig.suptitle('Geometria in alta dimensione: due fenomeni di concentrazione',
             color='white', fontsize=14, family='monospace', y=0.995)
fig.text(0.5, 0.45,
         'Sopra: la norma del rumore gaussiano collassa su $\\sqrt{n}$. La "palla di rumore" è una buccia.\n'
         'Sotto: due vettori a caso sono quasi sempre ortogonali. In $n=768$, |⟨u,v⟩| ≈ 0.036.',
         color=TEXT_DIM, family='monospace', fontsize=9.5, ha='center', va='center')

plt.tight_layout(rect=[0, 0, 1, 0.96])
plt.subplots_adjust(hspace=0.55)

out = 'high_dim_geometry.png'
plt.savefig(out, dpi=140, facecolor='#0d1117', bbox_inches='tight')
print(f"Saved: {out}")
