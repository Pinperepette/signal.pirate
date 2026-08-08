#!/usr/bin/env python3
"""
Quando abbiamo smesso di decidere da soli - tutti i conti dell'articolo.

L'idea di fondo: non decido io le date. Le faccio scegliere agli algoritmi.

  1. Bai-Perron su otto serie indipendenti: quante rotture ci sono e dove,
     con il numero scelto dal BIC e la posizione dalla programmazione dinamica
  2. intervalli di confidenza sulle date, con bootstrap a blocchi
  3. quanto sono robuste le date se cambio la lunghezza minima dei segmenti
  4. regressione a coefficienti variabili con filtro di Kalman: quanto pesa
     la Germania e quanto pesano gli Stati Uniti nel tasso ufficiale italiano,
     mese per mese, dal 1964 al 1998
  5. il conto: crescita per regime, convergenza, quota salari, salari reali,
     partite correnti

Il motore matematico sta in motore.py, con i suoi test di verifica.

Uso:
    pip install pandas numpy
    python3 analisi.py
"""
import json
import os

import numpy as np
import pandas as pd

import motore as M

SEME = 20260808
N_BOOT = 1000
BLOCCO = 12

QUI = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(QUI, "dati")
rng = np.random.default_rng(SEME)


def tit(n, t):
    print("\n" + "=" * 76 + f"\n{n}. {t}\n" + "=" * 76)


def leggi(nome, mensile=True):
    p = os.path.join(D, nome + ".csv")
    d = pd.read_csv(p, parse_dates=[0], index_col=0) if mensile else pd.read_csv(p, index_col=0)
    return d


tassi = leggi("tassi_ufficiali")
cpi_it = leggi("cpi_italia").iloc[:, 0]
cpi_de = leggi("cpi_germania").iloc[:, 0]
bot = leggi("bot_italia").iloc[:, 0]
lira = leggi("lira_dollaro").iloc[:, 0]
marco = leggi("marco_dollaro").iloc[:, 0]
ann = pd.read_csv(os.path.join(D, "italia_annuale.csv"), index_col="anno")
eur = pd.read_csv(os.path.join(D, "europa_lunga.csv"))
sal = pd.read_csv(os.path.join(D, "salari_reali_ocse.csv"), index_col="TIME_PERIOD")
EU = lambda s: eur[eur.serie == s].pivot(index="anno", columns="paese", values="v")

infl_it = cpi_it.pct_change(12, fill_method=None) * 100
infl_de = cpi_de.pct_change(12, fill_method=None) * 100
lira_marco = lira / marco


# ------------------------------------------------------------------ 1
tit(1, "Le rotture, scelte dai dati")

MENSILI = {
    "tasso ufficiale, Italia meno Germania": (tassi.IT - tassi.DE).dropna(),
    "inflazione, Italia meno Germania": (infl_it - infl_de).loc["1961":"1998"].dropna(),
    "tasso ufficiale italiano": tassi.IT.dropna(),
    "BOT reale ex-post": (bot - infl_it).loc["1978":"1998"].dropna(),
    "lira/marco, variazione a 12 mesi": (lira_marco.pct_change(12, fill_method=None) * 100).loc["1972":"1998"].dropna(),
}
ANNUALI = {
    "quota salari sul Pil": EU("quota_salari")["ITA"].loc[1960:2000].dropna(),
    "saldo primario": ann.primario_pil.loc[1960:2000].dropna(),
    "crescita del Pil pro capite": EU("pil_reale_procapite")["ITA"].pct_change().mul(100).loc[1961:2000].dropna(),
}

trovate = {}
print(f"{'serie':42} {'oss.':>5}  rotture")
print("-" * 100)
for nome, s in MENSILI.items():
    m, r = M.bai_perron(s.values, m_max=5)
    date = [s.index[i].strftime("%Y-%m") for i in r[m]["tagli"]]
    trovate[nome] = dict(date=date, medie=[round(v, 2) for v in M.medie_segmenti(s.values, r[m]["tagli"])])
    print(f"{nome:42} {len(s):>5}  " + ", ".join(date))
for nome, s in ANNUALI.items():
    m, r = M.bai_perron(s.values, m_max=3, frazione=0.18)
    date = [str(int(s.index[i])) for i in r[m]["tagli"]]
    trovate[nome] = dict(date=date, medie=[round(v, 2) for v in M.medie_segmenti(s.values, r[m]["tagli"])])
    print(f"{nome:42} {len(s):>5}  " + ", ".join(date))

print("\nI livelli medi dei segmenti, per le due serie chiave:")
for k in ["inflazione, Italia meno Germania", "tasso ufficiale, Italia meno Germania"]:
    print(f"  {k}: " + " | ".join(f"{v:+.2f}" for v in trovate[k]["medie"]))


# ------------------------------------------------------------------ 2
tit(2, "Quanto sono precise quelle date (bootstrap a blocchi)")


def intervalli(s, nome, B=N_BOOT, blocco=BLOCCO):
    y = s.values
    m, r = M.bai_perron(y, m_max=5)
    tagli = r[m]["tagli"]
    med = M.medie_segmenti(y, tagli)
    bordi = [0] + list(tagli) + [len(y)]
    fit = np.concatenate([np.full(b - a, mu) for (a, b), mu in zip(zip(bordi[:-1], bordi[1:]), med)])
    res = y - fit
    nb = int(np.ceil(len(y) / blocco))
    racc = [[] for _ in tagli]
    for _ in range(B):
        st = rng.integers(0, len(res) - blocco, size=nb)
        e = np.concatenate([res[k:k + blocco] for k in st])[:len(y)]
        _, rr = M.bai_perron(fit + e, m_max=m)
        tt = rr[m]["tagli"]
        if len(tt) == len(tagli):
            for i, v in enumerate(tt):
                racc[i].append(v)
    print(f"\n{nome}  ({len(y)} mesi, {B} ricampionamenti)")
    for i, k in enumerate(tagli):
        lo, hi = np.percentile(racc[i], [2.5, 97.5]).astype(int)
        esatti = sum(1 for v in racc[i] if v == k) / len(racc[i])
        print(f"  rottura {i+1}: {s.index[k]:%Y-%m}   intervallo 95%: "
              f"{s.index[lo]:%Y-%m} - {s.index[hi]:%Y-%m}   "
              f"simulazioni che cadono sullo stesso mese: {esatti*100:.1f}%")


intervalli(MENSILI["inflazione, Italia meno Germania"], "inflazione, Italia meno Germania")
intervalli(MENSILI["tasso ufficiale, Italia meno Germania"], "tasso ufficiale, Italia meno Germania")


# ------------------------------------------------------------------ 3
tit(3, "Le date reggono se cambio le impostazioni?")
s = MENSILI["tasso ufficiale, Italia meno Germania"]
print("lunghezza minima del segmento -> rotture trovate\n")
for fr in [0.08, 0.10, 0.12, 0.15, 0.18]:
    m, r = M.bai_perron(s.values, m_max=5, frazione=fr)
    print(f"  {int(len(s)*fr):>3} mesi   m={m}   " +
          ", ".join(s.index[i].strftime("%Y-%m") for i in r[m]["tagli"]))


# ------------------------------------------------------------------ 4
tit(4, "Chi guida il tasso italiano: Germania o Stati Uniti")
d = tassi[["IT", "DE", "US"]].dropna()
y = d.IT.values
X = np.column_stack([np.ones(len(d)), d.DE.values, d.US.values])
q, _ = M.scegli_q(y, X)
bs, Ps = M.kalman_tvp(y, X, q)
se = np.sqrt(np.array([np.diag(p) for p in Ps]))
k = pd.DataFrame({"beta_DE": bs[:, 1], "gamma_US": bs[:, 2],
                  "se_DE": se[:, 1], "se_US": se[:, 2]}, index=d.index)
print(f"campione {d.index[0]:%Y-%m} - {d.index[-1]:%Y-%m}, {len(d)} mesi")
print(f"rapporto segnale/rumore scelto per massima verosimiglianza: {q:.2e}\n")
a = k.resample("YE").mean()
a.index = a.index.year
print(f"{'anno':>6} {'Germania':>10} {'errore':>8} {'Stati Uniti':>13} {'errore':>8}")
for yy in [1966, 1970, 1974, 1977, 1981, 1984, 1987, 1990, 1993, 1996, 1998]:
    r = a.loc[yy]
    print(f"{yy:>6} {r.beta_DE:>+10.2f} {r.se_DE:>8.2f} {r.gamma_US:>+13.2f} {r.se_US:>8.2f}")
sig = (k.beta_DE - 2 * k.se_DE > 0).values
run, primo = 0, None
for i, v in enumerate(sig):
    run = run + 1 if v else 0
    if run == 24 and primo is None:
        primo = k.index[i - 23]
print(f"\nil peso della Germania sta sopra zero (oltre due errori standard) "
      f"stabilmente dal {primo:%Y-%m}")
print(f"massimo: {k.beta_DE.max():+.2f} in {k.beta_DE.idxmax():%Y-%m}")


# ------------------------------------------------------------------ 5
tit(5, "E il conto quanto e' stato")
pc = EU("pil_reale_procapite")
print("crescita media annua del Pil pro capite, per regime:")
for lab, aa, bb in [("1960-63 mercato comune", 1960, 1963), ("1963-73", 1963, 1973),
                    ("1973-79", 1973, 1979), ("1979-92 Sme", 1979, 1992),
                    ("1992-99 Maastricht", 1992, 1999), ("1999-2008 euro", 1999, 2008),
                    ("2008-19", 2008, 2019)]:
    print(f"  {lab:26} {((pc['ITA'][bb]/pc['ITA'][aa])**(1/(bb-aa))-1)*100:+5.2f}%")
q = pc["ITA"] / pc["FRA"] * 100
print("\nPil pro capite italiano in percentuale di quello francese:")
print("  " + "   ".join(f"{yy}: {q[yy]:.1f}" for yy in [1960, 1975, 1995, 2008, 2019, 2024]))
qs = EU("quota_salari")
print("\nquota dei salari sul Pil:")
for yy in [1960, 1975, 1990, 1999, 2024]:
    print(f"  {yy}  Italia {qs['ITA'][yy]:.1f}   Francia {qs['FRA'][yy]:.1f}")
print("\nsalario medio reale, variazione 1991 -> 2023:")
for c in sorted(sal.columns, key=lambda c: -(sal[c].loc[2023] / sal[c].loc[1991])):
    print(f"  {c}: {(sal[c].loc[2023]/sal[c].loc[1991]-1)*100:+5.1f}%")
pcorr = EU("partite_correnti_pil")
print("\npartite correnti (% del Pil):")
for yy in [1995, 2008, 2016, 2024]:
    print(f"  {yy}  Germania {pcorr['DEU'][yy]:+.1f}   Italia {pcorr['ITA'][yy]:+.1f}")
inv = EU("investimenti_pubblici_pil")
print("\ninvestimenti pubblici (% del Pil):")
for yy in [1995, 2010, 2019]:
    print(f"  {yy}  Italia {inv['ITA'][yy]:.1f}   Francia {inv['FRA'][yy]:.1f}")

print("\n" + "=" * 76)
print(f"Seme fisso {SEME}. Rilanciando escono gli stessi numeri.")
print("=" * 76)
