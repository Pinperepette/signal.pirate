#!/usr/bin/env python3
"""Riproduce tutti i numeri dell'articolo "I numeri sono giusti (la conclusione no)".

Legge i CSV in data/ (generati da fetch.py) e stampa, sezione per sezione,
ogni cifra citata nel pezzo. Richiede numpy e scipy.

Uso: python3 analisi.py
"""
import csv, os
import numpy as np
from scipy import stats

HERE = os.path.dirname(os.path.abspath(__file__))
YEARS = list(range(2006, 2025))
rng = np.random.default_rng(20260725)   # seme fisso: stessi numeri a ogni run

def load(name, keycols):
    out = {}
    with open(os.path.join(HERE, "data", name)) as f:
        for r in csv.DictReader(f):
            k = tuple(r[c] for c in keycols)
            out.setdefault(k, {})[int(r["TIME_PERIOD"])] = float(r["OBS_VALUE"])
    return out

D = {k[0]: v for k, v in load("delitti.csv", ["TYPE_CRIME"]).items()}

# le 35 categorie di primo livello: non si sovrappongono e sommano al totale
TOP = ['MASSMURD','INTENHOM','INFANTHOM','ATTEMPHOM','MANSHOM','UNINTHOM','CULPINJU',
       'BLOWS','MENACE','KIDNAPP','RAPE','RAPEUN18','CORRUPUN18','PORNO','PROSTI',
       'THEFT','RECEIV','ROBBER','EXTORT','USURY','SWINCYB','CYBERCRIM','COUNTER',
       'INTPROP','MONEYLAU','CRIMASS','MAFIASS','ARSON','DAMAGE','DAMARS','DRUG',
       'SMUGGL','ATTACK','OTHCRIM','OFFENCE']
VEICOLI = ['MOPETHEF','MOTORTHEF','CARTHEF','VEHITHEF','TRUCKTHEF']

def sez(t): print(f"\n=== {t} ===")

# ---------------------------------------------------------------- partizione
sez("PARTIZIONE: 35 categorie che sommano al totale")
for y in YEARS:
    s = sum(D[c].get(y, 0.0) for c in TOP)
    assert abs(s - D['TOT'][y]) < 1, (y, s, D['TOT'][y])
print(f"verificata su tutti i {len(YEARS)} anni: scarto zero")

# ------------------------------------------------------- il calo dal picco
sez("IL CALO DAL PICCO DEL 2007")
tot_d  = D['TOT'][2007]   - D['TOT'][2024]
theft_d= D['THEFT'][2007] - D['THEFT'][2024]
ing    = D['OFFENCE'][2007]
veic_d = sum(D[c][2007] - D[c][2024] for c in VEICOLI)
netto07= (D['TOT'][2024]-D['THEFT'][2024]) / (D['TOT'][2007]-D['THEFT'][2007]) - 1
netto19= (D['TOT'][2024]-D['THEFT'][2024]) / (D['TOT'][2019]-D['THEFT'][2019]) - 1
print(f"calo totale 2007-2024 : {tot_d:>10,.0f}")
print(f"calo dei soli furti   : {theft_d:>10,.0f}  ({theft_d/tot_d*100:.1f}% del calo)")
print(f"furti di veicoli      : {veic_d:>10,.0f}  ({veic_d/tot_d*100:.0f}% del calo)")
print(f"ingiurie (depenalizz.): {ing:>10,.0f}  ({ing/tot_d*100:.1f}% del calo)")
print(f"veicoli + ingiurie    : {(veic_d+ing)/tot_d*100:.0f}% | furti + ingiurie: {(theft_d+ing)/tot_d*100:.1f}%")
print(f"al netto dei furti    : {netto07*100:+.1f}% sul 2007, {netto19*100:+.1f}% sul 2019")
d16 = D['TOT'][2016]/D['TOT'][2015] - 1
print(f"2016 sul 2015         : {d16*100:+.1f}%  (ingiurie: {(D['OFFENCE'][2015]-D['OFFENCE'][2016])/(D['TOT'][2015]-D['TOT'][2016])*100:.0f}% di quel calo)")
for base in (2007, 2019, 2020):
    print(f"totale 2024 sul {base} : {(D['TOT'][2024]/D['TOT'][base]-1)*100:+.1f}%")
sd07 = D['TOT'][2007]-D['SWINCYB'][2007]-D['CYBERCRIM'][2007]
sd24 = D['TOT'][2024]-D['SWINCYB'][2024]-D['CYBERCRIM'][2024]
print(f"'senza i reati digitali' (verifica della mossa dell'articolo): {(sd24/sd07-1)*100:+.1f}%")

# ------------------------------------------------------------------ omicidi
sez("OMICIDI: pianoro, rottura, controfattuale")
h = D['INTENHOM']; ys = np.array(YEARS, float); v = np.array([h[y] for y in YEARS])
for a, b, lab in [(2006, 2017, "2006-2017"), (2018, 2024, "2018-2024")]:
    m = (ys >= a) & (ys <= b)
    tau, p = stats.kendalltau(ys[m], v[m]); sen = stats.theilslopes(v[m], ys[m], 0.95)
    print(f"{lab}: tau={tau:+.3f} p={p:.4f}  Theil-Sen {sen[0]:+.1f}/anno  IC95 [{sen[2]:+.1f},{sen[3]:+.1f}]")

def supF(x, y, lo=4):
    n = len(y); X0 = np.column_stack([np.ones(n), x])
    b0, *_ = np.linalg.lstsq(X0, y, rcond=None); s0 = ((y - X0@b0)**2).sum()
    best = (-1, None)
    for k in range(lo, n - lo):
        Dk = (x >= x[k]).astype(float)
        X1 = np.column_stack([np.ones(n), x, Dk, Dk*(x - x[k])])
        b1, *_ = np.linalg.lstsq(X1, y, rcond=None); s1 = ((y - X1@b1)**2).sum()
        F = ((s0 - s1)/2) / (s1/(n - 4))
        if F > best[0]: best = (F, x[k])
    return best

F_obs, brk = supF(ys, v)
X0 = np.column_stack([np.ones(len(ys)), ys]); b0, *_ = np.linalg.lstsq(X0, v, rcond=None)
sd = (v - X0@b0).std(ddof=2)
sim = np.array([supF(ys, X0@b0 + rng.normal(0, sd, len(ys)))[0] for _ in range(4000)])
print(f"sup-F: rottura nel {int(brk)}, F={F_obs:.1f}, p simulato={max((sim>=F_obs).mean(),1/4000):.4f}")
Dk = (ys >= brk).astype(float)
X1 = np.column_stack([np.ones(len(ys)), ys, Dk, Dk*(ys - brk)])
b1, *_ = np.linalg.lstsq(X1, v, rcond=None); fit = X1@b1; res = v - fit
dates = [supF(ys, fit + rng.choice(res, len(ys), replace=True))[1] for _ in range(2000)]
print(f"bootstrap sulla data: IC95 [{int(np.percentile(dates,2.5))}, {int(np.percentile(dates,97.5))}]")
m = ys <= 2017; sen = stats.theilslopes(v[m], ys[m], 0.95)
proj = sen[1] + sen[0]*2024
print(f"controfattuale: attesi {proj:.0f} nel 2024, osservati {v[-1]:.0f} ({(v[-1]/proj-1)*100:+.0f}%)")

t = D['ATTEMPHOM']
print(f"consumati 2006-2024: {(h[2024]/h[2006]-1)*100:+.1f}% | tentati: {(t[2024]/t[2006]-1)*100:+.1f}%"
      f" | somma: {((h[2024]+t[2024])/(h[2006]+t[2006])-1)*100:+.1f}%")
print(f"quota che finisce in morte: {h[2006]/(h[2006]+t[2006])*100:.1f}% -> {h[2024]/(h[2024]+t[2024])*100:.1f}%")
print(f"tentati 2020->2024: {(t[2024]/t[2020]-1)*100:+.1f}%")
print(f"omicidi mafiosi: {D['MAFIAHOM'][2007]:.0f} -> {D['MAFIAHOM'][2024]:.0f} ({D['MAFIAHOM'][2024]/h[2024]*100:.1f}% del totale 2024)")

sez("VITTIME PER SESSO (flusso 73_230, VICTIM)")
V = load("vittime_sesso.csv", ["SEX", "AGE"])
vm = {y: sum(s.get(y, 0) for k, s in V.items() if k[0] == '1') for y in range(2007, 2025)}
vf = {y: sum(s.get(y, 0) for k, s in V.items() if k[0] == '2') for y in range(2007, 2025)}
print(f"uomini: {vm[2007]:.0f} -> {vm[2024]:.0f} ({(vm[2024]/vm[2007]-1)*100:+.1f}%)")
print(f"donne : {vf[2007]:.0f} -> {vf[2024]:.0f} ({(vf[2024]/vf[2007]-1)*100:+.1f}%)")
print(f"quota donne: {vf[2007]/(vm[2007]+vf[2007])*100:.1f}% -> {vf[2024]/(vm[2024]+vf[2024])*100:.1f}%")

# ------------------------------------------------- quantita' vs composizione
sez("QUANTITA' vs COMPOSIZIONE (distanza in variazione totale dal 2007)")
M = np.array([[D[c].get(y, 0.0) for c in TOP] for y in YEARS])
P = M / M.sum(1)[:, None]; b = YEARS.index(2007)
tv = lambda p, q: 0.5*np.abs(p - q).sum()
print(f"2024: quantita' {abs(D['TOT'][2024]/D['TOT'][2007]-1)*100:.1f}%  composizione {tv(P[-1],P[b])*100:.1f}%")
k = [i for i, c in enumerate(TOP) if c != 'OFFENCE']
M2 = M[:, k]; t2 = M2.sum(1); P2 = M2 / t2[:, None]
print(f"senza ingiurie: quantita' {abs(t2[-1]/t2[b]-1)*100:.1f}%  composizione {tv(P2[-1],P2[b])*100:.1f}%")
noise = [tv(a/a.sum(), c/c.sum()) for a, c in
         ((rng.poisson(M[b]), rng.poisson(M[b])) for _ in range(500))]
print(f"rumore di Poisson fra due anni identici: {np.mean(noise)*100:.2f} punti "
      f"(osservato = {tv(P[-1],P[b])/np.mean(noise):.0f} volte tanto)")
contrib = np.abs(P[-1] - P[b])/2*100
top8 = np.sort(contrib)[-8:].sum()
print(f"le prime 8 voci spiegano il {top8/contrib.sum()*100:.0f}% dello spostamento")
print(f"quota furti: {P[b][TOP.index('THEFT')]*100:.1f}% -> {P[-1][TOP.index('THEFT')]*100:.1f}%"
      f" | truffe: {P[b][TOP.index('SWINCYB')]*100:.1f}% -> {P[-1][TOP.index('SWINCYB')]*100:.1f}%")

# --------------------------------------------------------- delitti vs persone
sez("DELITTI vs PERSONE DENUNCIATE (segni che divergono)")
O = load("denunciati_cittadinanza.csv", ["CITIZENSHIP", "SEX", "AGE"])
den_tot = {y: sum(s.get(y, 0) for k, s in O.items() if k[0] in ('ITL', 'FRG')) for y in range(2007, 2025)}
# nota: il confronto per singolo reato richiede il flusso OFFEND per reato; qui il totale
print(f"denunciati totali 2022 (controllo): {den_tot[2022]:,.0f}")
itl22 = sum(s.get(2022, 0) for k, s in O.items() if k[0] == 'ITL')
frg22 = sum(s.get(2022, 0) for k, s in O.items() if k[0] == 'FRG')
print(f"  italiani {itl22:,.0f} ({itl22/den_tot[2022]*100:.1f}%) | stranieri {frg22:,.0f} ({frg22/den_tot[2022]*100:.1f}%)")
# denominatori: popolazione residente 2022 (fonte ISTAT, usata per i tassi della dashboard)
POP_ITL, POP_FRG = 54_000_295, 5_030_716
POP_ITL_M_ADU, POP_FRG_M_ADU = 22_149_339, 1_924_838
r_i, r_f = itl22/POP_ITL*1e5, frg22/POP_FRG*1e5
print(f"tassi/100k: italiani {r_i:.0f} | stranieri {r_f:.0f} | rapporto {r_f/r_i:.1f}x")
im = sum(s.get(2022,0) for k,s in O.items() if k[0]=='ITL' and k[1]=='1' and k[2] not in ('Y_UN13','Y14-17'))
fm = sum(s.get(2022,0) for k,s in O.items() if k[0]=='FRG' and k[1]=='1' and k[2] not in ('Y_UN13','Y14-17'))
print(f"maschi adulti: {im/POP_ITL_M_ADU*1e5:.0f} vs {fm/POP_FRG_M_ADU*1e5:.0f} | rapporto {(fm/POP_FRG_M_ADU)/(im/POP_ITL_M_ADU):.1f}x")

# --------------------------------------------------------------- gli scippi
sez("GLI SCIPPI: il calo atteso dal solo effetto denuncia")
# tassi di denuncia misurati dall'indagine ISTAT 'Sicurezza dei cittadini'
# (report 9 giugno 2025): scippi consumati 88,9% -> 68,2%
atteso = 68.2/88.9 - 1
s = D['BAGTHEF']
oss = s[2022]/s[2015] - 1
print(f"atteso {atteso*100:+.1f}% | osservato nelle denunce 2015->2022 {oss*100:+.1f}%")

sez("VARIAZIONI 2019->2024 e ANNO DI LOCKDOWN")
for c, lab in [('CYBERCRIM','accessi abusivi'),('RAPE','violenze sessuali'),('SWINCYB','truffe'),
               ('EXTORT','estorsioni'),('STREETROB','rapine in pubblica via'),('ROBBER','rapine'),
               ('BAGTHEF','scippi'),('TOT','TOTALE'),('THEFT','furti'),('BURGTHEF','furti in abitazione')]:
    print(f"  {lab:24s} 2019->2024 {(D[c][2024]/D[c][2019]-1)*100:+6.1f}%   2019->2020 {(D[c][2020]/D[c][2019]-1)*100:+6.1f}%")
print("\nTutti i numeri dell'articolo sono riprodotti sopra.")
