"""
04_kyber_demo.py
Demo Kyber768 (ML-KEM-768, FIPS 203) usando pyca/cryptography stabile.

- KeyGen, Encapsulate, Decapsulate verifica
- Misura dimensioni reali pk / sk / ciphertext
- Benchmark micro: ops/sec di encapsulate e decapsulate
- Confronto con X25519 (ECDHE) per dare scala al "prezzo del post-quantum"
"""
import time
import statistics
from cryptography.hazmat.primitives.asymmetric import mlkem, x25519


def bench(func, n_runs=2000):
    """Restituisce tempo per op in microsecondi, mediana."""
    samples = []
    for _ in range(n_runs):
        t0 = time.perf_counter()
        func()
        samples.append((time.perf_counter() - t0) * 1e6)
    return statistics.median(samples)


# ----------------------------------------------------------
# Kyber768 / ML-KEM-768
# ----------------------------------------------------------
print("=" * 60)
print("ML-KEM-768 (Kyber768) — FIPS 203")
print("=" * 60)

sk = mlkem.MLKEM768PrivateKey.generate()
pk = sk.public_key()

pk_bytes = pk.public_bytes_raw()
sk_bytes = sk.private_bytes_raw()
ss_alice, ct = pk.encapsulate()
ss_bob = sk.decapsulate(ct)

print(f"Public key size : {len(pk_bytes)} byte")
print(f"Private key size: {len(sk_bytes)} byte")
print(f"Ciphertext size : {len(ct)} byte")
print(f"Shared secret   : {len(ss_alice)} byte")
print(f"Round-trip OK   : {ss_alice == ss_bob}")
print(f"Shared secret hex: {ss_alice.hex()}")

# Benchmark
def kyber_keygen():
    sk = mlkem.MLKEM768PrivateKey.generate()
    _ = sk.public_key()

def kyber_encap():
    _ct, _ss = pk.encapsulate()

# precompute ct for decap benchmark
_, ct_for_decap = pk.encapsulate()
def kyber_decap():
    _ss = sk.decapsulate(ct_for_decap)

print(f"\nBenchmark (mediana su 2000 run):")
t_kg = bench(kyber_keygen, 500)
t_en = bench(kyber_encap, 2000)
t_de = bench(kyber_decap, 2000)
print(f"  KeyGen      : {t_kg:8.2f} µs/op")
print(f"  Encapsulate : {t_en:8.2f} µs/op")
print(f"  Decapsulate : {t_de:8.2f} µs/op")

# ----------------------------------------------------------
# X25519 (curva ellittica, pre-quantum) per confronto
# ----------------------------------------------------------
print("\n" + "=" * 60)
print("X25519 (curve ellittiche, pre-quantum) — confronto")
print("=" * 60)

x_sk = x25519.X25519PrivateKey.generate()
x_pk = x_sk.public_key()
x_pk_bytes = x_pk.public_bytes_raw()
x_sk_bytes = x_sk.private_bytes_raw()
x_peer = x25519.X25519PrivateKey.generate().public_key()
x_ss = x_sk.exchange(x_peer)

print(f"Public key size : {len(x_pk_bytes)} byte")
print(f"Private key size: {len(x_sk_bytes)} byte")
print(f"Shared secret   : {len(x_ss)} byte")

def x_keygen():
    _ = x25519.X25519PrivateKey.generate()

def x_exchange():
    _ = x_sk.exchange(x_peer)

print(f"\nBenchmark:")
xt_kg = bench(x_keygen, 2000)
xt_ex = bench(x_exchange, 2000)
print(f"  KeyGen      : {xt_kg:8.2f} µs/op")
print(f"  Key exchange: {xt_ex:8.2f} µs/op")

# ----------------------------------------------------------
# Tabella confronto
# ----------------------------------------------------------
print("\n" + "=" * 60)
print("CONFRONTO Kyber768 vs X25519")
print("=" * 60)
print(f"{'metrica':<22} {'X25519':>12} {'Kyber768':>12} {'rapporto':>12}")
print("-" * 60)
print(f"{'public key (B)':<22} {len(x_pk_bytes):>12} {len(pk_bytes):>12} {len(pk_bytes)/len(x_pk_bytes):>11.1f}x")
print(f"{'private key (B)':<22} {len(x_sk_bytes):>12} {len(sk_bytes):>12} {len(sk_bytes)/len(x_sk_bytes):>11.1f}x")
print(f"{'wire (ct/dh) (B)':<22} {len(x_pk_bytes):>12} {len(ct):>12} {len(ct)/len(x_pk_bytes):>11.1f}x")
print(f"{'keygen (µs)':<22} {xt_kg:>12.1f} {t_kg:>12.1f} {t_kg/xt_kg:>11.1f}x")
print(f"{'encap / exchange (µs)':<22} {xt_ex:>12.1f} {t_en:>12.1f} {t_en/xt_ex:>11.1f}x")
print(f"{'decap (µs)':<22} {'-':>12} {t_de:>12.1f} {'-':>12}")
