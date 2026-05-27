"""
02_lll_scaling.py
LLL pure-Python su basi q-ary random a dimensioni crescenti.
Misura tempo wall-clock e norma del primo vettore della base ridotta.

Implementazione di riferimento (Lenstra-Lenstra-Lovász 1982), delta=0.75.
Non ottimizzata: serve per mostrare il MURO dello scaling, non per produzione.
Per crittoanalisi seria usare fpylll/flatter/BKZ.

Output: lll_scaling.png + lll_scaling_data.json
"""
import numpy as np
import time, json

# ----------------------------------------------------------
# LLL puro (pseudo-Cohen, "A Course in Computational Algebraic Number Theory" 2.6.3)
# ----------------------------------------------------------
def gram_schmidt(B):
    """Restituisce Bstar (GS ortogonalizzati) e mu (coefficienti)."""
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
    """LLL reduction in place. Restituisce la base ridotta come int64 numpy array."""
    B = B.astype(np.int64).copy()
    n = B.shape[0]
    Bstar, mu = gram_schmidt(B)
    norms2 = np.array([np.dot(Bstar[i], Bstar[i]) for i in range(n)])
    k = 1
    while k < n:
        # size-reduce b_k contro b_{k-1}, b_{k-2}, ..., b_0
        for j in range(k - 1, -1, -1):
            q = round(mu[k, j])
            if q != 0:
                B[k] = B[k] - q * B[j]
                mu[k, :j + 1] = mu[k, :j + 1] - q * mu[j, :j + 1]
                mu[k, j] = mu[k, j] - q
        # condizione di Lovász
        if norms2[k] >= (delta - mu[k, k - 1] ** 2) * norms2[k - 1]:
            k += 1
        else:
            B[[k - 1, k]] = B[[k, k - 1]]
            # ricalcolo locale di GS sulle righe k-1 e k (semplice ma corretto)
            Bstar, mu = gram_schmidt(B)
            norms2 = np.array([np.dot(Bstar[i], Bstar[i]) for i in range(n)])
            k = max(k - 1, 1)
    return B


# ----------------------------------------------------------
# Generazione base q-ary (canonical hard instance)
# ----------------------------------------------------------
def qary_basis(n, q_bits=20, seed=None):
    """
    Costruisce una base n x n con struttura q-ary:
      [ q*I_{n/2}   0         ]
      [ A           I_{n/2}   ]
    dove A è random in Z_q^{(n/2) x (n/2)} e q ha q_bits bit.
    Questa è l'istanza "hard" standard per benchmark LLL.
    """
    rng = np.random.default_rng(seed)
    half = n // 2
    q = int(2 ** q_bits + rng.integers(1, 100))  # primo-ish, per il benchmark va bene
    A = rng.integers(0, q, size=(half, half), dtype=np.int64)
    B = np.zeros((n, n), dtype=np.int64)
    for i in range(half):
        B[i, i] = q
    for i in range(half):
        B[half + i, :half] = A[i]
        B[half + i, half + i] = 1
    return B, q


# ----------------------------------------------------------
# Benchmark
# ----------------------------------------------------------
DIMS = [10, 20, 30, 40, 50, 60]    # pure-Python: oltre 60 il pendiente esplode
TIME_BUDGET_S = 300                 # interrompi se una singola riduzione supera 5 min

results = []
print(f"{'n':>4} | {'t_lll':>10} | {'||b1||':>12} | {'q':>10}", flush=True)
print("-" * 50, flush=True)
for n in DIMS:
    B, q = qary_basis(n, q_bits=20, seed=42)
    t0 = time.time()
    try:
        Br = lll(B, delta=0.75)
    except KeyboardInterrupt:
        print(f"n={n}: interrotto", flush=True)
        break
    dt = time.time() - t0
    norm_b1 = float(np.linalg.norm(Br[0]))
    results.append({"n": n, "t_seconds": round(dt, 3), "norm_b1": norm_b1, "q": q})
    print(f"{n:>4} | {dt:>9.3f}s | {norm_b1:>12.3e} | {q:>10}", flush=True)
    if dt > TIME_BUDGET_S:
        print(f"Time budget exceeded at n={n}, fermando il benchmark.", flush=True)
        break

# ----------------------------------------------------------
# Persist results + plot
# ----------------------------------------------------------
with open("lll_scaling_data.json", "w") as f:
    json.dump(results, f, indent=2)
print("\nSaved: lll_scaling_data.json")

import matplotlib.pyplot as plt
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5.5), facecolor='#0d1117')

ns = [r["n"] for r in results]
ts = [r["t_seconds"] for r in results]
norms = [r["norm_b1"] for r in results]

# pannello sinistro: tempo
ax1.set_facecolor('#0d1117')
ax1.semilogy(ns, ts, 'o-', color='#00ff88', lw=2, markersize=8)
ax1.set_xlabel('Dimensione n', color='#888', family='monospace')
ax1.set_ylabel('Tempo LLL [s] (log)', color='#888', family='monospace')
ax1.set_title('Wall-clock LLL pure-Python (scala log)',
              color='white', fontsize=12, family='monospace', pad=10)
ax1.grid(True, alpha=0.15, color='#444')
ax1.tick_params(colors='#888')
for spine in ax1.spines.values():
    spine.set_color('#333')

# pannello destro: qualità output (norma di b1)
ax2.set_facecolor('#0d1117')
ax2.semilogy(ns, norms, 'o-', color='#7c4dff', lw=2, markersize=8)
ax2.set_xlabel('Dimensione n', color='#888', family='monospace')
ax2.set_ylabel('Norma di b1 dopo LLL (log)', color='#888', family='monospace')
ax2.set_title('Qualità output: cresce esponenziale',
              color='white', fontsize=12, family='monospace', pad=10)
ax2.grid(True, alpha=0.15, color='#444')
ax2.tick_params(colors='#888')
for spine in ax2.spines.values():
    spine.set_color('#333')

fig.suptitle('LLL su basi q-ary: il muro della dimensione',
             color='white', fontsize=14, family='monospace', y=0.99)
plt.tight_layout()
plt.savefig("lll_scaling.png", dpi=140, facecolor='#0d1117', bbox_inches='tight')
print("Saved: lll_scaling.png")
