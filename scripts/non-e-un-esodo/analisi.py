#!/usr/bin/env python3
# Replication di "Non e' un esodo (e non e' il lavoro)" - Signal Pirate
# Rifa tutti i conti dell'articolo: regressione multipla, PCA, clustering, bootstrap (Monte Carlo).
# I dati sono qui sotto, incorporati: lo script e' autosufficiente.
# Uso:  pip install pandas numpy statsmodels scikit-learn  &&  python3 analisi.py
import io, numpy as np, pandas as pd
import statsmodels.api as sm
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

# --- dataset (31 paesi europei; fonti nel README) ---
DATI = """paese,codice,eta_uscita,proprieta_casa,disoccupazione,neet,pil_pps_ue100,affitti_livprezzi,individualismo_hofstede
Romania,RO,27.7,95.6,21.8,19.3,75,49.2,30
Slovacchia,SK,31.0,93.6,19.8,11.2,74,80.2,52
Croazia,HR,31.9,91.2,18.9,11.8,78,43.7,33
Ungheria,HU,27.1,90.5,12.8,10.9,75,59.7,80
Serbia,RS,30.1,89.9,25.0,15.2,48,37.0,25
Lituania,LT,24.1,88.8,13.8,13.5,86,63.6,60
Polonia,PL,27.2,87.3,11.4,9.1,77,45.5,60
N.Macedonia,MK,30.8,87.1,29.4,24.2,41,37.7,
Bulgaria,BG,30.0,86.1,12.1,13.8,63,37.6,30
Lettonia,LV,26.2,82.8,12.3,10.0,70,55.8,70
Estonia,EE,22.8,80.7,17.3,9.6,80,101.1,60
Norvegia,NO,22.5,79.2,11.0,6.4,175,102.0,69
Cechia,CZ,25.4,76.0,8.3,10.1,91,104.1,58
Portogallo,PT,29.0,76.0,20.5,8.9,81,77.4,27
Spagna,ES,30.4,75.3,28.7,12.3,91,97.8,51
Italia,IT,30.0,75.2,22.7,16.1,98,93.9,76
Slovenia,SI,29.1,75.2,9.9,7.8,91,76.9,27
Malta,MT,28.5,74.7,9.2,7.6,109,77.6,59
Belgio,BE,26.4,71.9,16.1,9.6,118,133.6,75
Cipro,CY,27.4,70.1,16.5,13.7,97,93.5,
Grecia,EL,30.6,69.6,26.7,16.0,68,70.6,35
Irlanda,IE,28.0,69.4,10.7,8.5,218,185.6,70
Olanda,NL,23.2,69.3,8.2,4.7,131,133.8,80
Finlandia,FI,21.4,69.2,16.2,9.4,103,129.1,63
Lussemburgo,LU,26.7,67.6,18.8,8.5,248,181.9,60
Svezia,SE,21.8,64.9,22.1,5.7,111,109.4,71
Francia,FR,23.7,63.1,17.2,12.3,99,121.2,71
Danimarca,DK,21.8,60.0,11.5,8.6,126,189.2,74
Turchia,TR,28.1,56.2,17.5,25.8,67,18.8,37
Austria,AT,25.3,54.3,10.4,9.4,121,112.9,55
Germania,DE,24.0,47.6,5.9,8.8,118,113.9,67"""

df = pd.read_csv(io.StringIO(DATI))
df = df.dropna(subset=["individualismo_hofstede"]).reset_index(drop=True)  # Cipro e Macedonia esclusi
df["individualismo_hofstede"] = df["individualismo_hofstede"].astype(float)
n = len(df)
IT = int(df.index[df["paese"] == "Italia"][0])
print(f"n = {n} paesi (Cipro e Macedonia del Nord esclusi: manca l'indice Hofstede)\n")

Y  = "eta_uscita"
X5 = ["disoccupazione", "proprieta_casa", "pil_pps_ue100", "affitti_livprezzi", "individualismo_hofstede"]
X7 = ["eta_uscita", "proprieta_casa", "disoccupazione", "neet", "pil_pps_ue100", "affitti_livprezzi", "individualismo_hofstede"]
lab = {"disoccupazione":"disoccupazione", "proprieta_casa":"proprieta casa", "pil_pps_ue100":"ricchezza (PIL)",
       "affitti_livprezzi":"affitti", "individualismo_hofstede":"cultura"}

# ---------- 1) REGRESSIONE MULTIPLA (coefficienti standardizzati) ----------
print("=" * 62)
print("1) REGRESSIONE MULTIPLA  (eta di uscita ~ 5 fattori, coeff. standardizzati)")
print("=" * 62)
z  = lambda s: (s - s.mean()) / s.std(ddof=1)
dz = df.copy()
for c in [Y] + X5:
    dz[c] = z(df[c].astype(float))
m  = sm.OLS(dz[Y], sm.add_constant(dz[X5])).fit()
ci = m.conf_int(0.05)
print(f"R2 = {m.rsquared:.3f}    R2 aggiustato = {m.rsquared_adj:.3f}    F p-value = {m.f_pvalue:.4f}\n")
print(f"{'variabile':<16}{'beta':>8}{'p-value':>10}     IC 95%")
for c in sorted(X5, key=lambda c: -abs(m.params[c])):
    print(f"{lab[c]:<16}{m.params[c]:>+8.2f}{m.pvalues[c]:>10.3f}     [{ci.loc[c,0]:+.2f}, {ci.loc[c,1]:+.2f}]")
print("\n-> l'unica variabile con p < 0,05 e' la cultura; la disoccupazione (p=0,17) non e' significativa.")

# ---------- 2) PCA (7 indicatori) ----------
print("\n" + "=" * 62)
print("2) PCA  (7 indicatori standardizzati)")
print("=" * 62)
Z  = StandardScaler().fit_transform(df[X7].astype(float))
pc = PCA().fit(Z)
sc = pc.transform(Z)
if pc.components_[0, X7.index("pil_pps_ue100")] < 0:   # orienta PC1: ricchezza positiva
    pc.components_[0] *= -1; sc[:, 0] *= -1
print(f"varianza spiegata:  PC1 {pc.explained_variance_ratio_[0]*100:.1f}%   PC2 {pc.explained_variance_ratio_[1]*100:.1f}%")
print(f"PC1 dell'Italia = {sc[IT,0]:+.2f}   (negativo = lato povero/debole della mappa)")
print("-> un solo grande asse ricchi-poveri; l'Italia cade a sinistra, col gruppo mediterraneo.")

# ---------- 3) CLUSTERING (KMeans) ----------
print("\n" + "=" * 62)
print("3) CLUSTERING KMeans  (stessi 7 indicatori)")
print("=" * 62)
best = None
for k in range(2, 7):
    lb = KMeans(k, n_init=10, random_state=0).fit_predict(Z)
    s  = silhouette_score(Z, lb)
    print(f"k={k}:  silhouette {s:.3f}")
    if best is None or s > best[1]:
        best = (k, s, lb)
k, s, lb = best
comp = [df["paese"][i] for i in range(n) if lb[i] == lb[IT] and i != IT]
print(f"\nk scelto = {k}  (silhouette {s:.2f}: gruppi deboli, e' un gradiente continuo non scatole nette)")
print("L'Italia finisce con:", ", ".join(comp))

# ---------- 4) BOOTSTRAP / MONTE CARLO (100.000 ricampionamenti) ----------
print("\n" + "=" * 62)
print("4) BOOTSTRAP / MONTE CARLO  (100.000 ricampionamenti con reinserimento)")
print("=" * 62)
B   = 100_000
rng = np.random.default_rng(20260721)
Xc  = np.column_stack([np.ones(n), dz[X5].values]); yc = dz[Y].values
i_un, i_id = 1 + X5.index("disoccupazione"), 1 + X5.index("individualismo_hofstede")
bu = np.empty(B); bc = np.empty(B)
for b in range(B):
    s_ = rng.integers(0, n, n)
    beta, *_ = np.linalg.lstsq(Xc[s_], yc[s_], rcond=None)
    bu[b], bc[b] = beta[i_un], beta[i_id]
print(f"cultura:        mediana {np.median(bc):+.2f},  a sinistra dello zero nel {100*np.mean(bc<0):.1f}% dei casi")
print(f"disoccupazione: mediana {np.median(bu):+.2f},  IC 95% [{np.percentile(bu,2.5):+.2f}, {np.percentile(bu,97.5):+.2f}] (attraversa lo zero)")

# stabilita' della posizione dell'Italia: sottocampionamento della PCA
T, keep = 10_000, int(round(n * 0.7))
rng2 = np.random.default_rng(1); weak = 0
for _ in range(T):
    sub = rng2.choice(n, keep, replace=False)
    if IT not in sub:
        sub = np.append(sub, IT)
    Zs  = StandardScaler().fit_transform(df[X7].astype(float).values[sub])
    ps  = PCA(2).fit(Zs); scs = ps.transform(Zs)
    sign = 1 if ps.components_[0, X7.index("pil_pps_ue100")] >= 0 else -1
    if sign * scs[list(sub).index(IT), 0] < 0:
        weak += 1
print(f"Italia nel gruppo debole (PC1<0) nel {100*weak/T:.1f}% dei sottocampioni")
print("\n-> non e' il lavoro (la disoccupazione attraversa lo zero), e l'Italia resta quasi sempre nel gruppo debole.")
