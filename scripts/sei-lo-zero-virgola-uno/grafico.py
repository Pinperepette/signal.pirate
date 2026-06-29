#!/usr/bin/env python3
"""Genera il grafico dell'articolo: due barre impilate (scenario A e B),
con 'TU' evidenziato. Stile dark coerente col blog."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from scenari import SCENARI

# palette del blog
C_HARNESS = "#7c4dff"   # viola
C_TOOL    = "#4ecdc4"   # teal
C_AGENT   = "#00ff88"   # verde
C_TU      = "#ff6b6b"   # rosso (TU)
BG        = "#0d1117"

ORDINE = [
    ("HARNESS (system+tool+hook+skill)", C_HARNESS, "harness (system+tool+hook)"),
    ("RISULTATI TOOL (file letti + output)", C_TOOL, "risultati tool"),
    ("AGENTE (ragionamenti + chiamate)", C_AGENT, "agente"),
    ("TU (quello che hai digitato)", C_TU, "TU"),
]

fig, ax = plt.subplots(figsize=(9, 6))
fig.patch.set_facecolor(BG); ax.set_facecolor(BG)

labels = list(SCENARI.keys())
labels_short = ["A\ntask corto", "B\nsessione lunga"]
x = range(len(labels))

for xi, (nome, d) in enumerate(SCENARI.items()):
    TOT = sum(d.values())
    bottom = 0
    for key, col, _ in ORDINE:
        v = d[key]
        pct = 100*v/TOT
        ax.bar(xi, v, bottom=bottom, color=col, width=0.55,
               edgecolor=BG, linewidth=1.5)
        # etichetta TU sempre, le altre se >5%
        if key.startswith("TU"):
            sx = -1 if xi == 0 else 1   # A punta a sinistra, B a destra
            ax.annotate(f"TU = {pct:.2f}%",
                        xy=(xi+0.28*sx, bottom+v/2),
                        xytext=(xi+0.62*sx, bottom+v/2+1500),
                        color=C_TU, fontsize=12, fontweight="bold", va="center",
                        ha="right" if sx < 0 else "left",
                        arrowprops=dict(arrowstyle="->", color=C_TU, lw=1.5))
        elif pct > 5:
            ax.text(xi, bottom+v/2, f"{pct:.0f}%", ha="center", va="center",
                    color="white", fontsize=11, fontweight="bold")
        bottom += v

ax.set_xticks(list(x)); ax.set_xticklabels(labels_short, color="white", fontsize=11)
ax.set_ylabel("token nel contesto del modello", color="white", fontsize=11)
ax.tick_params(colors="white")
for s in ax.spines.values(): s.set_color("#30363d")
ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)

ax.set_title("Quanto del contesto sei davvero TU?",
             color="white", fontsize=15, fontweight="bold", pad=14)
legend = [Patch(facecolor=c, label=l) for _, c, l in ORDINE]
leg = ax.legend(handles=legend, loc="upper left", frameon=False,
                labelcolor="white", fontsize=10)

fig.text(0.5, 0.01,
         "In un task corto la harness e' il 98%. In uno lungo i file letti "
         "la superano. In entrambi TU resti ~0,1%.",
         ha="center", color="#8b949e", fontsize=9)

plt.tight_layout(rect=[0, 0.03, 1, 1])
OUT = "tu_sei_lo_zero_virgola_uno.png"
plt.savefig(OUT, dpi=150, facecolor=BG, bbox_inches="tight")
print("salvato:", OUT)
