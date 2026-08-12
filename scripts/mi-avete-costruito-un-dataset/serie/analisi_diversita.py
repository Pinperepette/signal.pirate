# -*- coding: utf-8 -*-
"""Banco di prova per le misure di diversita' e concentrazione.

Non produce grafici: stampa numeri, per decidere cosa regge e cosa no
prima di metterlo nell'articolo. Tutto deterministico (seed fisso).
"""
import collections, itertools, math, importlib.util, os
import numpy as np

import dati as serie


def carica(nome, percorso):
    spec = importlib.util.spec_from_file_location(nome, percorso)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


QUI = os.path.dirname(os.path.abspath(__file__))
libri = carica("dati_libri", os.path.join(QUI, "..", "libri", "dati.py"))

DATASET = {
    "serie": (serie.RECS, {k: v[3] for k, v in serie.SERIE.items()}),
    "libri": (libri.RECS, {k: v[3] for k, v in libri.BOOKS.items()}),
}


def conteggi(recs):
    return np.array(sorted(collections.Counter(k for _, k in recs).values()),
                    dtype=float)[::-1]


# ---------------------------------------------------------------- 1 & 2. Hill
def hill(c, q):
    """Numeri di Hill: q=0 ricchezza, q=1 perplexity (exp H), q=2 1/HHI."""
    p = c / c.sum()
    if q == 1:
        return math.exp(-(p * np.log(p)).sum())
    if q == 0:
        return float(len(p))
    return float((p ** q).sum() ** (1 / (1 - q)))


def entropia(c):
    p = c / c.sum()
    return -(p * np.log(p)).sum()


def miller_madow(c):
    """Correzione del bias di sottocampionamento sull'entropia plug-in."""
    return entropia(c) + (len(c) - 1) / (2 * c.sum())


# ------------------------------------------------------------------- 3. Gini
def gini(c):
    x = np.sort(c)
    n = len(x)
    return float((2 * np.arange(1, n + 1) - n - 1).dot(x) / (n * x.sum()))


# -------------------------------------------------------------- 4. Zipf / MLE
def alpha_mle(c, xmin=1):
    """Clauset-Shalizi-Newman per dati discreti, stima numerica di alpha.
       Sui conteggi dei titoli (non sui ranghi): power law discreta."""
    x = c[c >= xmin]
    if len(x) < 5:
        return None, None, len(x)

    def loglik(a):
        # zeta di Hurwitz troncata: somma fino a un tetto ampio
        z = sum(k ** (-a) for k in range(int(xmin), 5000))
        return -len(x) * math.log(z) - a * np.log(x).sum()

    griglia = np.arange(1.05, 6.0, 0.005)
    valori = [loglik(a) for a in griglia]
    a = float(griglia[int(np.argmax(valori))])

    # KS contro la power law discreta stimata
    z = sum(k ** (-a) for k in range(int(xmin), 5000))
    supporto = np.arange(int(xmin), int(x.max()) + 1)
    cdf_teo = np.cumsum(supporto ** (-a) / z)
    emp = np.array([(x <= s).mean() for s in supporto])
    ks = float(np.abs(emp - cdf_teo).max())
    return a, ks, len(x)


# ------------------------------------------- 5. informazione mutua, riformulata
def mutua_persona_genere(recs, genere):
    """I(persona; genere). NON I(titolo; genere), che e' degenere:
       il titolo determina il genere, quindi H(genere|titolo)=0 e
       I(titolo; genere) = H(genere) per costruzione, sempre."""
    coppie = collections.Counter((p, genere[k]) for p, k in recs)
    N = sum(coppie.values())
    pj = {k: v / N for k, v in coppie.items()}
    px = collections.Counter()
    py = collections.Counter()
    for (a, b), v in pj.items():
        px[a] += v
        py[b] += v
    I = sum(v * math.log(v / (px[a] * py[b])) for (a, b), v in pj.items())
    Hy = -sum(v * math.log(v) for v in py.values())
    return I, Hy, I / Hy


# ---------------------------------------------- 6. Jaccard fra persone + null
def jaccard_stats(recs, rng, repliche=400):
    liste = collections.defaultdict(set)
    for p, k in recs:
        liste[p].add(k)
    liste = {p: s for p, s in liste.items()}
    persone = sorted(liste)
    titoli = sorted({k for _, k in recs})

    def misura(mappa):
        vals, positivi = [], 0
        for a, b in itertools.combinations(persone, 2):
            A, B = mappa[a], mappa[b]
            u = len(A | B)
            j = len(A & B) / u if u else 0.0
            vals.append(j)
            positivi += j > 0
        vals = np.array(vals)
        return positivi / len(vals), vals.mean()

    oss_frac, oss_media = misura(liste)

    # null model: stessa lunghezza di lista per persona, titoli estratti
    # con probabilita' proporzionale alla loro popolarita' osservata
    peso = np.array([sum(1 for _, k in recs if k == t) for t in titoli], dtype=float)
    peso /= peso.sum()
    nulli_frac, nulli_media = [], []
    for _ in range(repliche):
        finto = {p: set(rng.choice(len(titoli), size=len(liste[p]),
                                   replace=False, p=peso)) for p in persone}
        f, m = misura(finto)
        nulli_frac.append(f)
        nulli_media.append(m)
    return oss_frac, np.mean(nulli_frac), oss_media, np.mean(nulli_media)


# ----------------------------------------- 7. assortativita' del grafo titoli
def grafo_titoli(recs, min_voti=4, min_arco=2):
    voti = collections.Counter(k for _, k in recs)
    liste = collections.defaultdict(set)
    for p, k in recs:
        liste[p].add(k)
    coppie = collections.Counter()
    for s in liste.values():
        for a, b in itertools.combinations(sorted(s), 2):
            coppie[(a, b)] += 1
    return [(a, b, n) for (a, b), n in coppie.items()
            if n >= min_arco and voti[a] >= min_voti and voti[b] >= min_voti]


def assortativita(archi, genere, pesata=True):
    """Newman 2003, attributo categorico: r = (sum e_ii - sum a_i b_i)/(1 - sum a_i b_i)."""
    cats = sorted({genere[a] for a, b, _ in archi} | {genere[b] for a, b, _ in archi})
    idx = {c: i for i, c in enumerate(cats)}
    e = np.zeros((len(cats), len(cats)))
    for a, b, n in archi:
        w = n if pesata else 1
        i, j = idx[genere[a]], idx[genere[b]]
        e[i, j] += w / 2
        e[j, i] += w / 2
    e /= e.sum()
    tr = np.trace(e)
    s = float((e.sum(0) * e.sum(1)).sum())
    return (tr - s) / (1 - s)


def assort_permutazione(archi, genere, rng, repliche=2000):
    r = assortativita(archi, genere)
    nodi = sorted({a for a, b, _ in archi} | {b for a, b, _ in archi})
    etichette = [genere[n] for n in nodi]
    nulli = []
    for _ in range(repliche):
        mescolate = list(rng.permutation(etichette))
        g = dict(zip(nodi, mescolate))
        nulli.append(assortativita(archi, g))
    nulli = np.array(nulli)
    p = float((np.abs(nulli) >= abs(r)).mean())
    return r, nulli.mean(), nulli.std(), p


# ======================================================================= run
rng = np.random.default_rng(20260812)

print("=" * 74)
for nome, (recs, genere) in DATASET.items():
    c = conteggi(recs)
    N = int(c.sum())
    print(f"\n### {nome.upper()}  ({len(c)} titoli, {N} menzioni)")
    print(f"  Hill q=0 (ricchezza)      {hill(c,0):8.1f}")
    print(f"  Hill q=1 (perplexity)     {hill(c,1):8.1f}")
    print(f"  Hill q=2 (1/HHI)          {hill(c,2):8.1f}")
    print(f"  HHI                       {(c/c.sum()).dot(c/c.sum()):8.5f}")
    print(f"  H plug-in / Miller-Madow  {entropia(c):8.3f} / {miller_madow(c):.3f}"
          f"   (log K = {math.log(len(c)):.3f})")
    print(f"  H normalizzata            {entropia(c)/math.log(len(c)):8.3f}")
    print(f"  Gini                      {gini(c):8.3f}")
    a, ks, n = alpha_mle(c)
    print(f"  Zipf alpha (MLE, xmin=1)  {a:8.2f}   KS={ks:.3f}  su {n} titoli"
          f"   (max voti = {int(c[0])})")
    I, Hy, frac = mutua_persona_genere(recs, genere)
    print(f"  I(persona;genere)         {I:8.3f} nat   H(genere)={Hy:.3f}"
          f"   ridotta del {100*frac:.0f}%")

# --- confronto onesto: stessa taglia di campione ---------------------------
print("\n" + "=" * 74)
print("A PARITA' DI CAMPIONE (223 menzioni sorteggiate, 500 repliche)")
PARI = int(conteggi(DATASET["libri"][0]).sum())
for nome, (recs, _) in DATASET.items():
    c = conteggi(recs)
    urna = np.repeat(np.arange(len(c)), c.astype(int))
    q0, q1, q2, gi = [], [], [], []
    for _ in range(500):
        estratto = rng.choice(urna, size=PARI, replace=False)
        cc = np.array(sorted(collections.Counter(estratto).values()),
                      dtype=float)[::-1]
        q0.append(hill(cc, 0)); q1.append(hill(cc, 1))
        q2.append(hill(cc, 2)); gi.append(gini(cc))
    print(f"  {nome:6s}  q0={np.mean(q0):6.1f}  q1={np.mean(q1):6.1f}  "
          f"q2={np.mean(q2):6.1f}  Gini={np.mean(gi):.3f}")

# --- 6. somiglianza fra persone -------------------------------------------
print("\n" + "=" * 74)
print("SOMIGLIANZA FRA PERSONE (Jaccard su tutte le coppie)")
for nome, (recs, _) in DATASET.items():
    of, nf, om, nm = jaccard_stats(recs, rng)
    print(f"  {nome:6s}  coppie con almeno un titolo in comune: "
          f"osservato {100*of:5.2f}%  atteso a caso {100*nf:5.2f}%  "
          f"(x{of/nf if nf else float('nan'):.2f})   J medio {om:.4f} vs {nm:.4f}")

# --- 7. assortativita' ------------------------------------------------------
print("\n" + "=" * 74)
print("ASSORTATIVITA' DEL GRAFO TITOLO-TITOLO rispetto al genere")
for nome, (recs, genere) in DATASET.items():
    archi = grafo_titoli(recs)
    if len(archi) < 10:
        print(f"  {nome:6s}  solo {len(archi)} archi sopra soglia: non calcolabile")
        continue
    r, mu, sd, p = assort_permutazione(archi, genere, rng)
    cross = sum(1 for a, b, _ in archi if genere[a] != genere[b])
    print(f"  {nome:6s}  archi={len(archi):3d}  cross-genere={cross} "
          f"({100*cross/len(archi):.0f}%)")
    print(f"          r = {r:+.3f}   null {mu:+.3f} ± {sd:.3f}   p = {p:.3f}")
print("=" * 74)
