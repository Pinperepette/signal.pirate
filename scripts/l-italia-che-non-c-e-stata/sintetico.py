#!/usr/bin/env python3
"""Controllo sintetico: costruisco un'Italia finta con paesi rimasti fuori
dall'euro, pesati per assomigliare alla nostra prima del 1999, e guardo di
quanto la vera si stacca dalla finta dopo.

Metodo standard (Abadie-Gardeazabal, Abadie-Diamond-Hainmueller):
  w = argmin || X1 - X0 w ||   con w >= 0 e somma dei pesi = 1
dove X sono i predittori misurati nel periodo pre-trattamento.
Poi il divario post-1999 fra l'Italia vera e quella sintetica e' la stima
dell'effetto. La significativita' si valuta con i placebo: rifaccio lo stesso
esercizio mettendo al posto dell'Italia ognuno dei paesi di controllo e vedo
quanti divari grandi come il nostro escono per caso.
"""
import os
import numpy as np
import pandas as pd
from scipy.optimize import minimize

B = os.path.dirname(os.path.abspath(__file__))

TRATTATO = "ITA"
DONATORI = ["GBR", "SWE", "DNK", "NOR", "CHE", "USA", "JPN", "CAN", "AUS", "ISL", "NZL", "KOR"]
PRE = list(range(1980, 1999))
POST = list(range(1999, 2020))


def carica():
    """Pannello gia' estratto da AMECO: Pil reale pro capite e Pil per occupato,
    Italia piu' i dodici paesi rimasti fuori dall'euro."""
    d = pd.read_csv(os.path.join(B, "dati", "panel_sintetico.csv"))
    return d.rename(columns={"paese": "p", "serie": "s", "valore": "v"})


def pesi(X1, X0):
    """Minimi quadrati vincolati: pesi non negativi che sommano a uno."""
    n = X0.shape[1]
    f = lambda w: float(np.sum((X1 - X0 @ w) ** 2))
    v = [{"type": "eq", "fun": lambda w: w.sum() - 1}]
    r = minimize(f, np.full(n, 1 / n), bounds=[(0, 1)] * n, constraints=v,
                 method="SLSQP", options={"maxiter": 2000, "ftol": 1e-12})
    return r.x


def sintetico(serie, trattato, donatori, pre, post):
    """serie: DataFrame anni x paesi, indicizzata a 100 nell'ultimo anno pre."""
    base = serie.loc[pre[-1]]
    idx = serie / base * 100
    X1 = idx.loc[pre, trattato].values
    X0 = idx.loc[pre, donatori].values
    w = pesi(X1, X0)
    tutto = pre + post
    fin = idx.loc[tutto, donatori].values @ w
    return pd.DataFrame({"vera": idx.loc[tutto, trattato].values, "sintetica": fin},
                        index=tutto), w


if __name__ == "__main__":
    d = carica()
    S = lambda n: d[d.s == n].pivot(index="anno", columns="p", values="v")

    for nome, chiave in [("Pil reale pro capite", "pil_pc"),
                         ("Pil reale per occupato", "prod_occupato")]:
        serie = S(chiave)
        disp = [c for c in DONATORI if serie[c].loc[PRE + POST].notna().all()] if True else []
        disp = [c for c in DONATORI if c in serie.columns and
                serie[c].reindex(PRE + POST).notna().all()]
        print("\n" + "=" * 74)
        print(f"{nome}  ({PRE[0]}-{PRE[-1]} per costruire, {POST[0]}-{POST[-1]} per misurare)")
        print("=" * 74)
        print("donatori con dati completi:", ", ".join(disp))
        res, w = sintetico(serie, TRATTATO, disp, PRE, POST)
        print("pesi:", ", ".join(f"{c} {v:.2f}" for c, v in zip(disp, w) if v > 0.01))
        print(f"errore medio pre-1999: {np.abs(res.loc[PRE,'vera']-res.loc[PRE,'sintetica']).mean():.2f}")
        print(res.loc[[1999, 2004, 2008, 2013, 2019]].round(1).to_string())
        gap = res["vera"] - res["sintetica"]
        print(f"\ndivario nel 2019: {gap[2019]:+.1f} punti percentuali di Pil pro capite")
        print(f"divario medio 1999-2019: {gap.loc[POST].mean():+.1f}")

        # placebo: rifaccio l'esercizio su ogni donatore
        pl = {}
        for c in disp:
            altri = [x for x in disp if x != c] + [TRATTATO]
            try:
                r2, _ = sintetico(serie, c, altri, PRE, POST)
                pl[c] = (r2["vera"] - r2["sintetica"])[2019]
            except Exception:
                pass
        peggio = sum(1 for v in pl.values() if v <= gap[2019])
        print(f"\nplacebo: divari al 2019 negli altri paesi -> " +
              ", ".join(f"{c} {v:+.0f}" for c, v in sorted(pl.items(), key=lambda x: x[1])))
        print(f"paesi con un divario negativo quanto il nostro o peggio: {peggio} su {len(pl)}")
        print(f"p-value per permutazione: {(peggio+1)/(len(pl)+1):.3f}")
