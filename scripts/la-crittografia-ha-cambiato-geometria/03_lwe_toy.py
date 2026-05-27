"""
03_lwe_toy.py
LWE giocattolo: cifra/decifra 1 bit alla volta usando Regev (2005).

Schema:
  pk = (A, b = A s + e)   con A uniforme, s segreto, e gaussiano piccolo
  enc(mu): r in {0,1}^m, u = r^T A, v = r^T b + mu * floor(q/2)
  dec(u, v): d = v - u^T s = r^T e + mu * floor(q/2)
            mu' = 1 sse |d - q/2| < |d|  (in metrica circolare modulo q)

Parametri stile Kyber-toy: n=256, m=512, q=3329, sigma=3.2
Decryption failure: ~2^-30 con questi parametri (decisamente sicuro per 1000 bit).

Output: lwe_toy_results.json + lwe_sigma_sweep.png
"""
import numpy as np
import json

N, M, Q = 256, 512, 3329
SIGMA_DEFAULT = 3.2
RNG = np.random.default_rng(seed=2026)


def keygen(sigma):
    A = RNG.integers(0, Q, size=(M, N))
    s = RNG.integers(0, Q, size=N)
    e = np.round(RNG.normal(0, sigma, M)).astype(np.int64)
    b = (A @ s + e) % Q
    return (A, b), s


def encrypt(pk, mu):
    A, b = pk
    r = RNG.integers(0, 2, size=M)               # ephemeral sparse vector
    u = (r @ A) % Q
    v = (int(r @ b) + mu * (Q // 2)) % Q
    return u, v


def decrypt(sk, ct):
    u, v = ct
    d = int(v - u @ sk) % Q
    # distanza circolare a 0 vs a q/2
    d_to_0 = min(d, Q - d)
    d_to_half = abs(d - Q // 2)
    return 1 if d_to_half < d_to_0 else 0


# ----------------------------------------------------------
# Test 1: round-trip 1000 bit con sigma standard
# ----------------------------------------------------------
print(f"=== Round-trip test ===")
print(f"Parametri: n={N}, m={M}, q={Q}, sigma={SIGMA_DEFAULT}")
pk, sk = keygen(SIGMA_DEFAULT)
print(f"Public key sizes: A={pk[0].shape}, b={pk[1].shape}")

bits = list(np.tile([0, 1], 500))
RNG.shuffle(bits)
errors = 0
for mu in bits:
    ct = encrypt(pk, int(mu))
    mu_dec = decrypt(sk, ct)
    if mu_dec != mu:
        errors += 1
print(f"Bit cifrati/decifrati: {len(bits)}")
print(f"Errori: {errors}")
print(f"Failure rate empirico: {errors}/{len(bits)} = {errors/len(bits):.6f}")

# ----------------------------------------------------------
# Test 2: sigma sweep -- mostra la finestra di sicurezza
# ----------------------------------------------------------
print(f"\n=== Sigma sweep (1000 bit per sigma) ===")
SIGMAS = [0.5, 1.0, 2.0, 3.2, 5.0, 8.0, 15.0, 30.0, 60.0, 120.0]
sweep_results = []
for sigma in SIGMAS:
    pk, sk = keygen(sigma)
    err = 0
    n_trials = 1000
    test_bits = RNG.integers(0, 2, size=n_trials)
    for mu in test_bits:
        ct = encrypt(pk, int(mu))
        if decrypt(sk, ct) != mu:
            err += 1
    rate = err / n_trials
    sweep_results.append({"sigma": sigma, "errors": err, "rate": rate})
    print(f"sigma={sigma:6.2f}  err={err:4d}/{n_trials}  rate={rate:.4f}")

with open("lwe_toy_results.json", "w") as f:
    json.dump({
        "params": {"n": N, "m": M, "q": Q, "sigma": SIGMA_DEFAULT},
        "roundtrip": {"bits": len(bits), "errors": errors},
        "sigma_sweep": sweep_results,
    }, f, indent=2)
print("\nSaved: lwe_toy_results.json")

# ----------------------------------------------------------
# Plot finestra di correttezza
# ----------------------------------------------------------
import matplotlib.pyplot as plt
fig, ax = plt.subplots(figsize=(10, 6), facecolor='#0d1117')
ax.set_facecolor('#0d1117')
sigmas = [r["sigma"] for r in sweep_results]
rates = [max(r["rate"], 1e-4) for r in sweep_results]  # floor per la log
ax.semilogy(sigmas, rates, 'o-', color='#00ff88', lw=2, markersize=10)
ax.axhline(0.5, color='#ff6b6b', linestyle='--', alpha=0.5)
ax.axvline(SIGMA_DEFAULT, color='#7c4dff', linestyle='--', alpha=0.6)
ax.text(SIGMA_DEFAULT * 1.1, 1e-3, f'sigma={SIGMA_DEFAULT}\n(Kyber-like)',
        color='#7c4dff', family='monospace', fontsize=10)
ax.text(70, 0.55, 'random guess (50%)',
        color='#ff6b6b', family='monospace', fontsize=10)
ax.set_xscale('log')
ax.set_xlabel('Sigma (deviazione standard del rumore)', color='#888', family='monospace')
ax.set_ylabel('Failure rate empirico (log)', color='#888', family='monospace')
ax.set_title('La finestra di LWE: troppo poco rumore = insicuro, troppo = decifratura rotta',
             color='white', fontsize=12, family='monospace', pad=12)
ax.grid(True, alpha=0.15, color='#444')
ax.tick_params(colors='#888')
for spine in ax.spines.values():
    spine.set_color('#333')

plt.tight_layout()
plt.savefig("lwe_sigma_sweep.png", dpi=140, facecolor='#0d1117', bbox_inches='tight')
print("Saved: lwe_sigma_sweep.png")
