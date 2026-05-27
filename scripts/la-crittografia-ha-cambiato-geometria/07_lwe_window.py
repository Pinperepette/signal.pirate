"""
07_lwe_window.py
Visualizza la "finestra di LWE" come istogrammi di v - u^T s mod q.

Per ogni sigma in {3.2, 30, 120}, esegue molte cifrature toy:
  - 5000 di mu=0
  - 5000 di mu=1
Misura il valore decifrato d = (v - u^T s) mod q.

Per mu=0  -> d concentrato intorno a 0
Per mu=1  -> d concentrato intorno a q/2 = 1664

Quando sigma è piccolo, i due cluster sono separati: decifratura banale.
Quando sigma cresce, i cluster si allargano e si toccano al confine q/4 = 832.
A sigma molto grande, le due distribuzioni diventano indistinguibili da uniformi
su [0, q) e il bit non si recupera.

Output: lwe_window.png
"""
import numpy as np
import matplotlib.pyplot as plt

N, M, Q = 256, 512, 3329
N_TRIALS = 5000
RNG = np.random.default_rng(seed=42)


def keygen(sigma):
    A = RNG.integers(0, Q, size=(M, N))
    s = RNG.integers(0, Q, size=N)
    e = np.round(RNG.normal(0, sigma, M)).astype(np.int64)
    b = (A @ s + e) % Q
    return (A, b), s


def measure_d(pk, sk, mu, n_trials):
    """Restituisce array di d = (v - u^T s) mod q per n_trials cifrature di mu."""
    A, b = pk
    out = np.zeros(n_trials, dtype=np.int64)
    for i in range(n_trials):
        r = RNG.integers(0, 2, size=M)
        u = (r @ A) % Q
        v = (int(r @ b) + mu * (Q // 2)) % Q
        d = int(v - u @ sk) % Q
        out[i] = d
    return out


SIGMAS = [3.2, 30.0, 120.0]
results = {}
print(f"n={N}, m={M}, q={Q}, q/2={Q//2}, q/4={Q//4}")
print(f"Sigma sweep with {N_TRIALS} trials each for mu=0 and mu=1\n")

for sigma in SIGMAS:
    pk, sk = keygen(sigma)
    d0 = measure_d(pk, sk, 0, N_TRIALS)
    d1 = measure_d(pk, sk, 1, N_TRIALS)
    results[sigma] = (d0, d1)

    # report
    print(f"sigma={sigma:6.1f}")
    print(f"  mu=0: d in [{d0.min()}, {d0.max()}], "
          f"mass near 0 = {(np.minimum(d0, Q-d0) < Q//4).mean():.1%}")
    print(f"  mu=1: d in [{d1.min()}, {d1.max()}], "
          f"mass near q/2 = {(np.abs(d1 - Q//2) < Q//4).mean():.1%}")

# ---- Plot ----
fig, axes = plt.subplots(1, 3, figsize=(16, 5.5), facecolor='#0d1117')

GREEN = '#00ff88'
PURPLE = '#7c4dff'
RED = '#ff6b6b'
TEXT_DIM = '#888'
SPINE = '#333'

for col, sigma in enumerate(SIGMAS):
    ax = axes[col]
    ax.set_facecolor('#0d1117')
    d0, d1 = results[sigma]
    bins = np.linspace(0, Q, 80)
    ax.hist(d0, bins=bins, color=GREEN, alpha=0.65, density=True,
            edgecolor='none', label='$\\mu=0$ (bit 0)')
    ax.hist(d1, bins=bins, color=PURPLE, alpha=0.65, density=True,
            edgecolor='none', label='$\\mu=1$ (bit 1)')
    # Decision boundaries
    ax.axvline(Q // 2, color=RED, linestyle='--', alpha=0.6, linewidth=1.2)
    ax.axvline(Q // 4, color='#777', linestyle=':', alpha=0.5, linewidth=1)
    ax.axvline(3 * Q // 4, color='#777', linestyle=':', alpha=0.5, linewidth=1)
    ax.text(Q // 2, ax.get_ylim()[1] * 0.95, f'  q/2 = {Q//2}',
            color=RED, family='monospace', fontsize=9, ha='left', va='top')

    title_color = GREEN if sigma <= 8 else (PURPLE if sigma <= 50 else RED)
    ax.set_title(f'$\\sigma = {sigma}$',
                 color=title_color, fontsize=13, family='monospace', pad=8)
    ax.set_xlabel('$d = (v - u^\\top s) \\;\\mathrm{mod}\\; q$',
                  color=TEXT_DIM, family='monospace', fontsize=10)
    if col == 0:
        ax.set_ylabel('Densità', color=TEXT_DIM, family='monospace', fontsize=10)
    ax.set_xlim(0, Q)
    ax.tick_params(colors=TEXT_DIM, labelsize=8)
    for s in ax.spines.values():
        s.set_color(SPINE)
    ax.grid(True, alpha=0.1, color='#444')
    ax.legend(loc='upper right', facecolor='#0d1117', edgecolor='#333',
              labelcolor=TEXT_DIM, fontsize=9, framealpha=0.9)

fig.suptitle('La finestra di LWE: come il rumore sigma chiude la decifratura',
             color='white', fontsize=14, family='monospace', y=1.0)
fig.text(0.5, -0.03,
         'Sinistra: due cluster separati, bit recuperabile a colpo d\'occhio.   '
         'Centro: cluster che cominciano a sconfinare oltre q/4.   '
         'Destra: distribuzioni quasi uniformi, indistinguibili da random.',
         color=TEXT_DIM, family='monospace', fontsize=9.5, ha='center')

plt.tight_layout()
out = 'lwe_window.png'
plt.savefig(out, dpi=140, facecolor='#0d1117', bbox_inches='tight')
print(f"\nSaved: {out}")
