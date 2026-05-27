# La Crittografia Ha Cambiato Geometria — Lab

Quattro script auto-contenuti che riproducono gli esperimenti dell'articolo.

## Setup

Servono Python 3.10+ e tre pacchetti:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install numpy matplotlib cryptography
```

`cryptography` deve essere ≥ 44 (mlkem nativo).

## Script

### `01_lattice_2d.py`
Visualizza Z² con due basi diverse: ortogonale `(1,0)/(0,1)` e quasi-collineare `(101,100)/(100,99)`. Stesso reticolo (|det| = 1), geometrie percepite opposte. Mostra che SVP banale nella base buona corrisponde a sottrarre due vettori lunghi ~141 nella base cattiva.

Output: `lattice_2d.png`

### `02_lll_scaling.py`
LLL pure-Python (Lenstra-Lenstra-Lovász 1982, δ=0.75) su basi q-ary random a dimensioni crescenti. Misura tempo wall-clock e norma del primo vettore della base ridotta. Mostra il muro polinomiale alto: pure-Python LLL in dimensione 60 impiega due minuti, oltre esplode.

Per crittoanalisi seria usare `fpylll`/`flatter`/BKZ. Questa implementazione è di riferimento, non ottimizzata.

Output: `lll_scaling.png`, `lll_scaling_data.json`

### `03_lwe_toy.py`
LWE giocattolo stile Regev (2005). Parametri Kyber-like: n=256, m=512, q=3329, σ=3.2. Cifra/decifra 1 bit per volta. Test:
1. **Round-trip**: 1000 bit con σ=3.2 → 0 errori.
2. **Sigma sweep**: σ ∈ {0.5, 1, 2, 3.2, 5, 8, 15, 30, 60, 120}. Mostra la finestra di correttezza: sotto σ=15 il rumore non è abbastanza da rompere la decifratura, sopra σ=30 il rumore comincia a saltare oltre q/4 e i bit si invertono.

Output: `lwe_sigma_sweep.png`, `lwe_toy_results.json`

### `04_kyber_demo.py`
ML-KEM-768 (Kyber768, FIPS 203) via `pyca/cryptography` (backend OpenSSL).
- Genera coppia, encapsulate, decapsulate, verifica round-trip.
- Stampa dimensioni reali: PK 1184 B, CT 1088 B, SS 32 B.
- Benchmark mediano su 2000 run: KeyGen, Encapsulate, Decapsulate.
- Confronto fianco-a-fianco con X25519 (curva ellittica pre-quantum): dimensioni e tempi.

Su CPU Intel x86_64 con OpenSSL: Encap ~150 µs, Decap ~230 µs. Implementazioni AVX2 ottimizzate (PQClean, AWS-LC) scendono a 25-50 µs.

### `05_high_dim_geometry.py`
Concentrazione di misura, prova empirica. 50.000 campioni per dim ∈ {1, 10, 100, 768}:
1. Norma di gaussiano N(0, I_n) → collassa su √n con std O(1).
2. Prodotto scalare di vettori uniformi su S^(n-1) → collassa su 0 con scala 1/√n.

Output: `high_dim_geometry.png`. È la visualizzazione del "bolla cava" + "quasi-ortogonalità".

### `06_lll_visualize.py`
LLL before/after su Z² con base cattiva (13, 21)/(5, 8) (det = −1, quindi reticolo Z² stesso). Mostra la riduzione da norme 24.7 e 9.4 a norme 1 e 1, con parallelogramma fondamentale prima/dopo.

Output: `lll_visualize.png`.

### `07_lwe_window.py`
Per σ ∈ {3.2, 30, 120}, 5000 cifrature di μ=0 e 5000 di μ=1. Plotta istogrammi del valore decifrato d = (v − uᵀs) mod q, sovrapposti. Mostra visivamente come la finestra di sicurezza si chiude: a σ=3.2 due cluster separati, a σ=120 distribuzioni uniformi.

Output: `lwe_window.png`.

## Run

```bash
python 01_lattice_2d.py             # < 1s
python 02_lll_scaling.py            # ~4 min su laptop moderno
python 03_lwe_toy.py                # ~5s
python 04_kyber_demo.py             # ~30s (2000 run per benchmark)
python 05_high_dim_geometry.py      # ~3s
python 06_lll_visualize.py          # < 1s
python 07_lwe_window.py             # ~20s
```

## Note onestà

- L'LLL pure-Python è didattico. Per attacchi seri usare fpylll.
- I parametri LWE-toy NON sono crypto reale: q=3329 è il modulo Kyber ma senza Module-LWE / NTT / FIPS 203 il tutto resta un giocattolo dimostrativo.
- Kyber è invece la vera ML-KEM-768 standardizzata.
