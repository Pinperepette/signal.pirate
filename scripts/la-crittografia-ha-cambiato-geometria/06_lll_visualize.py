"""
06_lll_visualize.py
LLL in azione su un reticolo 2D non banale.

Base cattiva: b1 = (13, 21), b2 = (5, 8). det = 13*8 - 21*5 = -1.
Quindi il reticolo è Z^2 stesso, ma la base parte storta:
||b1|| ≈ 24.7, ||b2|| ≈ 9.4. Dopo LLL la base si riduce a vettori corti
e quasi ortogonali (idealmente (1,0)/(0,1)).

Visualizziamo:
  pannello sinistro: reticolo + parallelogramma fondamentale della base CATTIVA
  pannello destro:   reticolo + parallelogramma fondamentale della base RIDOTTA da LLL

Output: lll_visualize.png
"""
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon


# Pure-Python LLL (stessa di 02_lll_scaling.py, semplificata)
def gram_schmidt(B):
    n = B.shape[0]
    Bstar = np.zeros_like(B, dtype=float)
    mu = np.zeros((n, n), dtype=float)
    for i in range(n):
        Bstar[i] = B[i].astype(float)
        for j in range(i):
            mu[i, j] = np.dot(B[i], Bstar[j]) / np.dot(Bstar[j], Bstar[j])
            Bstar[i] -= mu[i, j] * Bstar[j]
    return Bstar, mu


def lll(B, delta=0.75):
    B = B.astype(np.int64).copy()
    n = B.shape[0]
    Bstar, mu = gram_schmidt(B)
    norms2 = np.array([np.dot(Bstar[i], Bstar[i]) for i in range(n)])
    k = 1
    while k < n:
        for j in range(k - 1, -1, -1):
            q = round(mu[k, j])
            if q != 0:
                B[k] = B[k] - q * B[j]
                mu[k, :j + 1] = mu[k, :j + 1] - q * mu[j, :j + 1]
                mu[k, j] = mu[k, j] - q
        if norms2[k] >= (delta - mu[k, k - 1] ** 2) * norms2[k - 1]:
            k += 1
        else:
            B[[k - 1, k]] = B[[k, k - 1]]
            Bstar, mu = gram_schmidt(B)
            norms2 = np.array([np.dot(Bstar[i], Bstar[i]) for i in range(n)])
            k = max(k - 1, 1)
    return B


B_bad = np.array([[13, 21], [5, 8]])
det = round(np.linalg.det(B_bad))
assert abs(det) == 1, f"Base non unimodulare, det={det}"
print(f"det(B_bad) = {det}  -> reticolo Z^2 stesso di base (1,0)/(0,1)")
print(f"||b1|| = {np.linalg.norm(B_bad[0]):.2f}, ||b2|| = {np.linalg.norm(B_bad[1]):.2f}")

B_red = lll(B_bad.copy(), delta=0.75)
print(f"Dopo LLL:")
print(f"  b1' = {tuple(B_red[0])}  ||b1'|| = {np.linalg.norm(B_red[0]):.2f}")
print(f"  b2' = {tuple(B_red[1])}  ||b2'|| = {np.linalg.norm(B_red[1]):.2f}")

# Lattice points (Z^2 perché det=1)
RANGE = 8
points = np.array([[a, b] for a in range(-RANGE, RANGE + 1)
                   for b in range(-RANGE, RANGE + 1)])

# Plot setup
fig, (ax_l, ax_r) = plt.subplots(1, 2, figsize=(14, 7), facecolor='#0d1117')
GREEN = '#00ff88'
PURPLE = '#7c4dff'
RED = '#ff6b6b'
ORANGE = '#ff9b4d'
TEXT_DIM = '#888'
SPINE = '#333'

# ---------------- PANNELLO SINISTRO: base cattiva ----------------
ax_l.set_facecolor('#0d1117')
ax_l.scatter(points[:, 0], points[:, 1], s=14, c=GREEN, alpha=0.65, zorder=2)
ax_l.scatter([0], [0], s=70, c=RED, marker='*', edgecolors='white',
             linewidths=0.5, zorder=5)
# Base vectors
for vec, color in [(B_bad[0], PURPLE), (B_bad[1], ORANGE)]:
    ax_l.annotate('', xy=vec, xytext=(0, 0),
                  arrowprops=dict(arrowstyle='->', color=color, lw=2.5))
# Fundamental parallelogram (translucid)
para = np.array([[0, 0], B_bad[0], B_bad[0] + B_bad[1], B_bad[1]])
poly = Polygon(para, alpha=0.10, facecolor=PURPLE, edgecolor=PURPLE, linewidth=1)
ax_l.add_patch(poly)
ax_l.text(B_bad[0, 0], B_bad[0, 1] + 0.8,
          f"$b_1' = (13, 21)$\n$\\|b_1'\\| = {np.linalg.norm(B_bad[0]):.2f}$",
          color=PURPLE, family='monospace', fontsize=10, ha='center')
ax_l.text(B_bad[1, 0], B_bad[1, 1] - 1.5,
          f"$b_2' = (5, 8)$\n$\\|b_2'\\| = {np.linalg.norm(B_bad[1]):.2f}$",
          color=ORANGE, family='monospace', fontsize=10, ha='center')
ax_l.set_xlim(-RANGE, RANGE * 3)
ax_l.set_ylim(-RANGE, RANGE * 3)
ax_l.set_aspect('equal')
ax_l.set_title('Base cattiva: vettori lunghi, parallelogramma allungato',
               color='white', fontsize=12, family='monospace', pad=10)
ax_l.tick_params(colors=TEXT_DIM, labelsize=8)
for s in ax_l.spines.values():
    s.set_color(SPINE)
ax_l.axhline(0, color='#1a1a2e', lw=0.5)
ax_l.axvline(0, color='#1a1a2e', lw=0.5)

# ---------------- PANNELLO DESTRO: base ridotta ----------------
ax_r.set_facecolor('#0d1117')
ax_r.scatter(points[:, 0], points[:, 1], s=14, c=GREEN, alpha=0.65, zorder=2)
ax_r.scatter([0], [0], s=70, c=RED, marker='*', edgecolors='white',
             linewidths=0.5, zorder=5)
for vec, color in [(B_red[0], PURPLE), (B_red[1], ORANGE)]:
    ax_r.annotate('', xy=vec, xytext=(0, 0),
                  arrowprops=dict(arrowstyle='->', color=color, lw=2.5))
para_r = np.array([[0, 0], B_red[0], B_red[0] + B_red[1], B_red[1]])
poly_r = Polygon(para_r, alpha=0.20, facecolor=GREEN, edgecolor=GREEN, linewidth=1)
ax_r.add_patch(poly_r)
ax_r.text(B_red[0, 0] + 0.4, B_red[0, 1] + 0.4,
          f"$b_1 = {tuple(int(x) for x in B_red[0])}$\n$\\|b_1\\| = {np.linalg.norm(B_red[0]):.2f}$",
          color=PURPLE, family='monospace', fontsize=10)
ax_r.text(B_red[1, 0] + 0.4, B_red[1, 1] - 1.0,
          f"$b_2 = {tuple(int(x) for x in B_red[1])}$\n$\\|b_2\\| = {np.linalg.norm(B_red[1]):.2f}$",
          color=ORANGE, family='monospace', fontsize=10)
# Same zoom for comparison fairness
ax_r.set_xlim(-RANGE, RANGE * 3)
ax_r.set_ylim(-RANGE, RANGE * 3)
ax_r.set_aspect('equal')
ax_r.set_title('Base ridotta da LLL: vettori corti, base ortogonale',
               color='white', fontsize=12, family='monospace', pad=10)
ax_r.tick_params(colors=TEXT_DIM, labelsize=8)
for s in ax_r.spines.values():
    s.set_color(SPINE)
ax_r.axhline(0, color='#1a1a2e', lw=0.5)
ax_r.axvline(0, color='#1a1a2e', lw=0.5)

fig.suptitle('LLL su $\\mathbb{Z}^2$: stesso reticolo, base ridotta',
             color='white', fontsize=14, family='monospace', y=0.99)
fig.text(0.5, 0.02,
         'Stesso insieme di punti, stessa griglia, stessa determinante. LLL trova due vettori '
         'più corti e più ortogonali. In 2D è facile, in 768D no.',
         color=TEXT_DIM, family='monospace', fontsize=9.5, ha='center')

plt.tight_layout(rect=[0, 0.04, 1, 0.96])

out = 'lll_visualize.png'
plt.savefig(out, dpi=140, facecolor='#0d1117', bbox_inches='tight')
print(f"Saved: {out}")
