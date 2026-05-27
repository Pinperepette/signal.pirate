"""
01_lattice_2d.py
Visualizza lo stesso reticolo Z^2 con due basi diverse:
  - base buona (1,0)/(0,1): ortogonale, SVP banale
  - base cattiva (101,100)/(100,99): quasi-collineare, SVP nascosto
Stesso reticolo (|det B| = 1), geometrie percepite opposte.
Output: lattice_2d.png nella stessa cartella.
"""
import numpy as np
import matplotlib.pyplot as plt

B_good = np.array([[1, 0], [0, 1]])
B_bad  = np.array([[101, 100], [100, 99]])

det_good = round(np.linalg.det(B_good))
det_bad  = round(np.linalg.det(B_bad))
print(f"det(B_good) = {det_good}")
print(f"det(B_bad)  = {det_bad}")
print(f"Stesso reticolo: |det| = {abs(det_good)} = {abs(det_bad)}")

# punti del reticolo dentro una finestra
RANGE = 6
coeffs = [(a, b) for a in range(-RANGE, RANGE + 1) for b in range(-RANGE, RANGE + 1)]
pts_good = np.array([a * B_good[0] + b * B_good[1] for a, b in coeffs])
pts_bad  = np.array([a * B_bad[0]  + b * B_bad[1]  for a, b in coeffs])

# SVP con base cattiva: (1,0) = -99*b1' + 100*b2'
# 101*(-99) + 100*100 = -9999 + 10000 = 1
# 100*(-99) +  99*100 = -9900 +  9900 = 0
svp_via_bad = -99 * B_bad[0] + 100 * B_bad[1]
print(f"SVP con base cattiva: -99*b1' + 100*b2' = {tuple(svp_via_bad)}  (norma {np.linalg.norm(svp_via_bad):.3f})")
print(f"Sottrazione di due vettori lunghi ~141 per ottenere un vettore lungo 1.")

fig, axes = plt.subplots(1, 2, figsize=(14, 6.5), facecolor='#0d1117')

# ---------- pannello sinistro: base buona ----------
ax = axes[0]
ax.set_facecolor('#0d1117')
ax.scatter(pts_good[:, 0], pts_good[:, 1], s=18, c='#00ff88', alpha=0.85, zorder=3)
# evidenzia il vettore corto
ax.annotate('', xy=B_good[0], xytext=(0, 0),
            arrowprops=dict(arrowstyle='->', color='#7c4dff', lw=2.5))
ax.annotate('', xy=B_good[1], xytext=(0, 0),
            arrowprops=dict(arrowstyle='->', color='#7c4dff', lw=2.5))
ax.scatter([0], [0], s=80, c='#ff6b6b', zorder=4, marker='*', edgecolors='white', linewidths=0.5)
ax.text(1.15, 0.05, r'$b_1=(1,0)$', color='#7c4dff', fontsize=11, family='monospace')
ax.text(0.05, 1.15, r'$b_2=(0,1)$', color='#7c4dff', fontsize=11, family='monospace')
ax.text(0, -RANGE - 0.5, 'SVP banale: ||b1|| = 1', color='#00ff88',
        fontsize=12, family='monospace', ha='center')
ax.set_xlim(-RANGE, RANGE)
ax.set_ylim(-RANGE, RANGE)
ax.set_aspect('equal')
ax.set_title('Base buona: (1,0) / (0,1)', color='white', fontsize=13, family='monospace', pad=12)
ax.tick_params(colors='#888')
for spine in ax.spines.values():
    spine.set_color('#333')
ax.axhline(0, color='#222', lw=0.5)
ax.axvline(0, color='#222', lw=0.5)

# ---------- pannello destro: base cattiva ----------
ax = axes[1]
ax.set_facecolor('#0d1117')
# vista a scala più larga per vedere i due freccione
LARGE = 250
coeffs_zoom = [(a, b) for a in range(-3, 4) for b in range(-3, 4)]
pts_bad_zoom = np.array([a * B_bad[0] + b * B_bad[1] for a, b in coeffs_zoom])
ax.scatter(pts_bad_zoom[:, 0], pts_bad_zoom[:, 1], s=18, c='#00ff88', alpha=0.85, zorder=3)
ax.annotate('', xy=B_bad[0], xytext=(0, 0),
            arrowprops=dict(arrowstyle='->', color='#7c4dff', lw=2.5))
ax.annotate('', xy=B_bad[1], xytext=(0, 0),
            arrowprops=dict(arrowstyle='->', color='#7c4dff', lw=2.5))
ax.scatter([0], [0], s=80, c='#ff6b6b', zorder=4, marker='*', edgecolors='white', linewidths=0.5)
# evidenzia il punto corto (1, 0) nascosto fra i punti del reticolo
ax.scatter([1], [0], s=140, c='none', edgecolor='#ff6b6b', linewidth=2, zorder=5)
ax.text(110, 105, r"$b_1'=(101,100)$", color='#7c4dff', fontsize=11, family='monospace')
ax.text(105, 90, r"$b_2'=(100,99)$", color='#7c4dff', fontsize=11, family='monospace')
ax.text(0, -LARGE - 20, "SVP nascosto: ||b1'|| ≈ 142 ma il vero SVP è ancora 1\n(serve la combinazione 99 b2' - 100 b1')",
        color='#ff6b6b', fontsize=11, family='monospace', ha='center')
ax.set_xlim(-LARGE, LARGE)
ax.set_ylim(-LARGE, LARGE)
ax.set_aspect('equal')
ax.set_title("Base cattiva: (101,100) / (100,99)  —  stesso reticolo",
             color='white', fontsize=13, family='monospace', pad=12)
ax.tick_params(colors='#888')
for spine in ax.spines.values():
    spine.set_color('#333')
ax.axhline(0, color='#222', lw=0.5)
ax.axvline(0, color='#222', lw=0.5)

fig.suptitle('Z² con due basi diverse — la geometria del segreto in lattice crypto',
             color='white', fontsize=14, family='monospace', y=0.98)
plt.tight_layout()

out_path = 'lattice_2d.png'
plt.savefig(out_path, dpi=140, facecolor='#0d1117', bbox_inches='tight')
print(f"Saved: {out_path}")
