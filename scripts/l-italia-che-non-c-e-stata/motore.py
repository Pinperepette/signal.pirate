#!/usr/bin/env python3
"""Motore: chi guida la politica monetaria italiana, e da quando.

Tre stime, nessuna data imposta a mano.

A) Regressione a coefficienti variabili nel tempo, stimata con filtro di Kalman
   e smoother RTS:  i_IT(t) = a(t) + b(t)*i_DE(t) + c(t)*i_US(t) + e(t)
   con gli stati che seguono un random walk. Il rapporto segnale/rumore lo
   scelgo per massima verosimiglianza. Output: b(t) e c(t) mese per mese.

B) Bai-Perron: rotture multiple, numero e posizione scelti dai dati con
   programmazione dinamica sulla matrice degli SSR e selezione via BIC.

C) PCA mobile sul pannello dei tassi europei: quanta parte della varianza
   sta su una sola componente, finestra mobile di 60 mesi.
"""
import numpy as np
import pandas as pd


# --------------------------------------------------------------- A
def kalman_tvp(y, X, q_su_r, ritorna_ll=False):
    """Filtro di Kalman + smoother RTS per y(t) = X(t)' beta(t) + e(t),
    beta(t) = beta(t-1) + u(t).  q_su_r e' il rapporto segnale/rumore."""
    n, k = X.shape
    R = 1.0
    Q = np.eye(k) * q_su_r
    b = np.zeros(k)
    P = np.eye(k) * 1e4
    bf, Pf, bp, Pp = np.empty((n, k)), np.empty((n, k, k)), np.empty((n, k)), np.empty((n, k, k))
    ll = 0.0
    for t in range(n):
        b_prior = b
        P_prior = P + Q
        bp[t], Pp[t] = b_prior, P_prior
        x = X[t]
        f = x @ P_prior @ x + R
        v = y[t] - x @ b_prior
        K = P_prior @ x / f
        b = b_prior + K * v
        P = P_prior - np.outer(K, x) @ P_prior
        bf[t], Pf[t] = b, P
        if t > k:
            ll += -0.5 * (np.log(2 * np.pi * f) + v * v / f)
    if ritorna_ll:
        return ll
    # smoother RTS
    bs, Ps = bf.copy(), Pf.copy()
    for t in range(n - 2, -1, -1):
        J = Pf[t] @ np.linalg.pinv(Pp[t + 1])
        bs[t] = bf[t] + J @ (bs[t + 1] - bp[t + 1])
        Ps[t] = Pf[t] + J @ (Ps[t + 1] - Pp[t + 1]) @ J.T
    return bs, Ps


def scegli_q(y, X, griglia=None):
    """Sceglie il rapporto segnale/rumore per massima verosimiglianza."""
    if griglia is None:
        griglia = np.logspace(-6, -1, 40)
    lls = [kalman_tvp(y, X, q, ritorna_ll=True) for q in griglia]
    return griglia[int(np.argmax(lls))], np.array(lls)


# --------------------------------------------------------------- B
def bai_perron(y, m_max=5, frazione=0.12):
    """Rotture multiple in media. Numero e posizione scelti dai dati.
    Programmazione dinamica sulla matrice degli SSR, selezione con BIC."""
    y = np.asarray(y, float)
    n = len(y)
    h = max(int(n * frazione), 8)          # ampiezza minima di un segmento
    cs = np.concatenate([[0.0], np.cumsum(y)])
    cs2 = np.concatenate([[0.0], np.cumsum(y * y)])

    def ssr(i, j):                          # segmento [i, j)
        L = j - i
        if L <= 0:
            return np.inf
        s = cs[j] - cs[i]
        return (cs2[j] - cs2[i]) - s * s / L

    S = np.full((n + 1, n + 1), np.inf)
    for i in range(n):
        for j in range(i + h, n + 1):
            S[i, j] = ssr(i, j)

    risultati = {}
    C = np.full((m_max + 1, n + 1), np.inf)
    P = np.zeros((m_max + 1, n + 1), dtype=int)
    C[0, :] = S[0, :]
    for m in range(1, m_max + 1):
        for j in range(h * (m + 1), n + 1):
            best, arg = np.inf, -1
            for t in range(h * m, j - h + 1):
                v = C[m - 1, t] + S[t, j]
                if v < best:
                    best, arg = v, t
            C[m, j], P[m, j] = best, arg
    for m in range(0, m_max + 1):
        if not np.isfinite(C[m, n]):
            continue
        tagli, j, mm = [], n, m
        while mm > 0:
            t = P[mm, j]
            tagli.append(t)
            j, mm = t, mm - 1
        tagli = sorted(tagli)
        k = 2 * (m + 1)                     # medie + varianza per segmento
        bic = n * np.log(C[m, n] / n) + k * np.log(n)
        risultati[m] = dict(ssr=C[m, n], bic=bic, tagli=tagli)
    m_best = min(risultati, key=lambda m: risultati[m]["bic"])
    return m_best, risultati


def medie_segmenti(y, tagli):
    y = np.asarray(y, float)
    bordi = [0] + list(tagli) + [len(y)]
    return [float(y[a:b].mean()) for a, b in zip(bordi[:-1], bordi[1:])]


# --------------------------------------------------------------- C
def pca_mobile(P, finestra=60):
    """Quota di varianza sulla prima componente, finestra mobile.
    P: DataFrame di variazioni mensili, colonne = paesi."""
    out = {}
    for i in range(finestra, len(P) + 1):
        W = P.iloc[i - finestra:i].dropna(axis=1, how="any")
        if W.shape[1] < 3:
            continue
        Z = (W - W.mean()) / W.std(ddof=0)
        ev = np.linalg.eigvalsh(np.cov(Z.values, rowvar=False))[::-1]
        out[P.index[i - 1]] = dict(quota=float(ev[0] / ev.sum()), paesi=int(W.shape[1]))
    return pd.DataFrame(out).T


# --------------------------------------------------------------- test rapido
if __name__ == "__main__":
    rs = np.random.default_rng(0)
    n = 300
    b = np.concatenate([np.zeros(150), np.ones(150)])
    x = rs.normal(size=n)
    y = b * x + rs.normal(scale=.3, size=n)
    X = np.column_stack([np.ones(n), x])
    q, _ = scegli_q(y, X)
    bs, _ = kalman_tvp(y, X, q)
    print(f"test Kalman: q={q:.2e}  beta a t=50 -> {bs[50,1]:+.2f}  a t=250 -> {bs[250,1]:+.2f}"
          f"   (veri: 0.00 e 1.00)")
    z = np.concatenate([rs.normal(0, 1, 100), rs.normal(3, 1, 100), rs.normal(-1, 1, 100)])
    m, r = bai_perron(z, m_max=4)
    print(f"test Bai-Perron: rotture trovate = {m}, in {r[m]['tagli']} (vere: 100 e 200)")
