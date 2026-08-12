# -*- coding: utf-8 -*-
"""Stile condiviso dei quattro grafici — coerente con il post sulle serie TV."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BG = "#08080c"
FG = "#f2f3f5"
DIM = "#8b9098"
DIMMER = "#5a6068"
GRID = "#22242c"

TITLE_FONT = "Impact"
MONO = "Menlo"
BODY = "Helvetica Neue"

plt.rcParams.update({
    "figure.facecolor": BG,
    "savefig.facecolor": BG,
    "axes.facecolor": BG,
    "text.color": FG,
    "font.family": BODY,
})


def testata(fig, titolo, sottotitolo, corpo=None, x=0.028, y=0.965, fs=52, wrap_y=None):
    """Titolo Impact + sottotitolo mono letterspaziato + paragrafo esplicativo."""
    fig.text(x, y, titolo, fontfamily=TITLE_FONT, fontsize=fs, color=FG,
             va="top", ha="left")
    fig.text(x + 0.004, y - fs / 1450 - 0.012, " ".join(sottotitolo.upper()),
             fontfamily=MONO, fontsize=9.5, color=DIM, va="top", ha="left")
    if corpo:
        fig.text(x + 0.004, wrap_y if wrap_y else y - fs / 1450 - 0.045, corpo,
                 fontfamily=BODY, fontsize=11.5, color="#c3c7cd", va="top",
                 ha="left", linespacing=1.55)


def pieResta(fig, sinistra, destra=None, y=0.018):
    fig.text(0.028, y, sinistra, fontfamily=MONO, fontsize=8.5, color=DIMMER, ha="left")
    if destra:
        fig.text(0.972, y, destra, fontfamily=MONO, fontsize=8.5, color=DIMMER, ha="right")


def sovrapposto(fig):
    """Assi trasparenti in coordinate figura, per disegnare fuori dal grafico."""
    if not hasattr(fig, "_ov"):
        ov = fig.add_axes([0, 0, 1, 1], zorder=20)
        ov.set_axis_off()
        ov.set_facecolor("none")
        ov.set_xlim(0, 1)
        ov.set_ylim(0, 1)
        fig._ov = ov
    return fig._ov


def legenda(fig, voci, x=0.50, y=0.962, colonne=3, dx=0.155, dy=0.0175, fs=9.5,
            contatori=None, s=42):
    """voci: lista (etichetta, colore). Griglia in alto a destra."""
    ov = sovrapposto(fig)
    for i, (lab, col) in enumerate(voci):
        c, r = divmod(i, (len(voci) + colonne - 1) // colonne)
        px, py = x + c * dx, y - r * dy
        ov.scatter([px], [py], s=s, color=col, clip_on=False, zorder=21,
                   edgecolors="none")
        fig.text(px + 0.011, py, lab, fontfamily=BODY, fontsize=fs, color="#d7dae0",
                 va="center", ha="left")
        if contatori:
            fig.text(px + dx - 0.018, py, str(contatori[i]), fontfamily=MONO,
                     fontsize=fs - 0.5, color=DIMMER, va="center", ha="right")
