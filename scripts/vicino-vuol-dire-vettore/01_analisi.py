"""
Feed X — Analisi Vettoriale Completa
Legge da data/tweets.json (generato da 00_extract.py) e produce 10 grafici in output/.

Articolo: https://signal.pirate/articoli/vicino-vuol-dire-vettore.html
"""

import os, re, json, warnings, unicodedata
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.colors as mcolors
from matplotlib.patches import FancyArrowPatch
from scipy.spatial.distance import cdist
from scipy.stats import pearsonr
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score, davies_bouldin_score
from sklearn.neighbors import NearestNeighbors
from sentence_transformers import SentenceTransformer
import umap
import hdbscan

warnings.filterwarnings("ignore")
os.makedirs("output", exist_ok=True)

# ── CONFIG ────────────────────────────────────────────────────────────────────
DATA_FILE   = "data/tweets.json"
MAX_DOCS    = 1500
MODEL_NAME  = "paraphrase-multilingual-MiniLM-L12-v2"
PCA_DIMS    = 50
UMAP_HD     = 15
MIN_TEXT    = 15

LANG_NAMES  = {
    "it": "Italiano", "en": "English", "ja": "日本語",
    "ar": "العربية", "de": "Deutsch", "es": "Español",
    "fr": "Français", "ru": "Русский", "zh": "中文",
    "tr": "Türkçe",  "pt": "Português", "ko": "한국어",
}
LANG_COLORS = {
    "it": "#2ecc71", "en": "#3498db", "ja": "#e74c3c",
    "ar": "#f39c12", "de": "#9b59b6", "es": "#1abc9c",
    "fr": "#e67e22", "ru": "#e91e63", "zh": "#ff5722",
    "tr": "#607d8b", "pt": "#00bcd4", "ko": "#8bc34a",
}

# ── 1. CARICAMENTO ────────────────────────────────────────────────────────────
def load(path, limit):
    """Legge data/tweets.json generato da 00_extract.py."""
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)

    seen, records = set(), []
    for item in raw:
        text = item.get("text", "")
        if text.startswith("RT ") or not text.strip():
            continue
        norm = text.lower().strip()
        if norm in seen:
            continue
        seen.add(norm)
        records.append({
            "text":       text,
            "lang":       item.get("lang", "und"),
            "created_at": item.get("created_at", ""),
            "user_id":    "",
            "screen_name": "",
            "hashtags":   [],
        })
        if len(records) >= limit:
            break

    df = pd.DataFrame(records)
    print(f"[load] {len(df)} tweet — {df['lang'].nunique()} lingue")
    return df


def clean(text):
    text = unicodedata.normalize("NFC",
           text.encode("utf-8", "ignore").decode("utf-8", "ignore"))
    text = re.sub(r"http\S+", "", text)
    text = re.sub(r"@\w+", "", text)
    return re.sub(r"\s+", " ", text).strip()


def preprocess(df):
    df         = df.copy()
    df["clean"] = df["text"].apply(clean)
    df          = df[df["clean"].str.len() >= MIN_TEXT].reset_index(drop=True)
    try:
        df["dt"] = pd.to_datetime(df["created_at"],
                                  format="%a %b %d %H:%M:%S +0000 %Y",
                                  utc=True, errors="coerce")
    except Exception:
        df["dt"] = pd.NaT
    print(f"[prep] {len(df)} tweet dopo pulizia")
    print(f"[prep] Lingue: {df['lang'].value_counts().to_dict()}")
    return df


# ── 2. EMBEDDING ──────────────────────────────────────────────────────────────
def embed(texts, model_name):
    print(f"[embed] {model_name} su {len(texts)} testi…")
    model = SentenceTransformer(model_name)
    E     = model.encode(texts, batch_size=64,
                         show_progress_bar=True, normalize_embeddings=True)
    print(f"[embed] shape: {E.shape}")
    return E.astype(np.float32)


# ── 3. RIDUZIONE ──────────────────────────────────────────────────────────────
def reduce(E):
    n   = min(PCA_DIMS, E.shape[0]-1, E.shape[1])
    pca = PCA(n_components=n, random_state=42)
    Ep  = pca.fit_transform(E)
    print(f"[pca] varianza spiegata con {n} componenti: {pca.explained_variance_ratio_.sum():.2%}")

    Ehd = umap.UMAP(n_components=UMAP_HD, metric="cosine",
                    random_state=42, n_neighbors=15).fit_transform(Ep)
    E2d = umap.UMAP(n_components=2, metric="cosine",
                    random_state=42, n_neighbors=15, min_dist=0.1).fit_transform(Ep)
    return pca, Ep, Ehd, E2d


# ── 4. CLUSTERING ─────────────────────────────────────────────────────────────
def cluster(Ehd):
    clust  = hdbscan.HDBSCAN(min_cluster_size=12, min_samples=4,
                              metric="euclidean", cluster_selection_method="eom")
    labels = clust.fit_predict(Ehd)
    nc     = len(set(labels)) - (1 if -1 in labels else 0)
    print(f"[hdbscan] {nc} cluster — {(labels==-1).sum()} outlier")
    return labels


# ── 5. LIVELLO COGNITIVO (densità KNN) ───────────────────────────────────────
def cognitive_level(Ehd, k=10):
    """
    Densità locale = inverso distanza media ai k vicini.
    Alta densità → mainstream (tanti tweet simili).
    Bassa densità → niché/tecnico (pochi tweet simili).
    """
    nn     = NearestNeighbors(n_neighbors=k+1, metric="euclidean").fit(Ehd)
    dists, _ = nn.kneighbors(Ehd)
    density  = 1.0 / (dists[:, 1:].mean(axis=1) + 1e-9)
    # normalizza 0-1
    d_norm   = (density - density.min()) / (density.max() - density.min() + 1e-9)
    level    = np.where(d_norm > 0.66, "mainstream",
               np.where(d_norm > 0.33, "intermedio", "niché/tecnico"))
    return d_norm, level


# ─────────────────────────────────────────────────────────────────────────────
# GRAFICI
# ─────────────────────────────────────────────────────────────────────────────

# ── G1: UN TWEET COME VETTORE ─────────────────────────────────────────────────
def plot_tweet_as_vector(E, df):
    idx   = 0
    tweet = df["text"].iloc[idx]
    vec   = E[idx]

    # trova simile e diverso escludendo idx
    sims        = E @ vec
    others      = np.arange(len(E)) != idx
    most_sim    = int(np.where(others, sims, -np.inf).argmax())
    most_diff   = int(np.where(others, sims,  np.inf).argmin())

    sim_val  = float(sims[most_sim])
    diff_val = float(sims[most_diff])

    fig, axes = plt.subplots(1, 2, figsize=(16, 4.5))

    # barre embedding completo
    colors = ["#e74c3c" if v < 0 else "#2ecc71" for v in vec]
    axes[0].bar(range(len(vec)), vec, color=colors, linewidth=0)
    axes[0].axhline(0, color="black", linewidth=0.5)
    axes[0].set_title(f'Tweet → vettore ({len(vec)} dimensioni)\n"{tweet[:75]}…"',
                      fontsize=9, fontweight="bold")
    axes[0].set_xlabel("Dimensione (0–383)")
    axes[0].set_ylabel("Valore")
    axes[0].text(0.98, 0.97, f'[{df["lang"].iloc[idx]}]',
                 transform=axes[0].transAxes, ha="right", va="top",
                 fontsize=9, color="gray")

    # confronto prime 50 dimensioni: 3 tweet
    idxs3  = [idx, most_sim, most_diff]
    labels3 = ["Questo tweet", f"Più simile (score {sim_val:.2f})", f"Più diverso (score {diff_val:.2f})"]
    cols3   = ["#3498db", "#2ecc71", "#e74c3c"]
    for i, (ii, lbl, c) in enumerate(zip(idxs3, labels3, cols3)):
        snippet = df["text"].iloc[ii][:45].replace("\n", " ")
        axes[1].plot(E[ii, :50], color=c, alpha=0.85, linewidth=1.5,
                     label=f"{lbl}\n  [{df['lang'].iloc[ii]}] \"{snippet}...\"")
    axes[1].legend(fontsize=7.5, loc="upper right",
                   framealpha=0.9, edgecolor="lightgray")
    axes[1].set_title("Confronto vettori (prime 50 dim)\nLa forma della curva = il significato",
                      fontweight="bold")
    axes[1].set_xlabel("Dimensione")
    axes[1].set_ylabel("Valore")
    axes[1].axhline(0, color="gray", linewidth=0.4, linestyle="--")

    fig.suptitle("Un testo diventa un punto nello spazio: 384 numeri che ne catturano il significato",
                 fontsize=10, fontweight="bold", color="#2c3e50")
    plt.tight_layout()
    plt.savefig("output/01_tweet_come_vettore.png", dpi=140, bbox_inches="tight")
    plt.close()
    print("[G1] 01_tweet_come_vettore.png")


# ── G2: CROSS-LINGUAL SIMILARITY HEATMAP ─────────────────────────────────────
def plot_crosslingual_heatmap(E, df):
    ai_kw = ["ai", "agent", "claude", "gpt", "llm", "model", "intelligenza",
              "artificiale", "agente", "modello", "robot", "automation"]

    candidates = df[df["text"].str.lower().str.contains("|".join(ai_kw), na=False)]

    # 1 tweet per lingua, max 12 lingue
    samples = []
    for lang, grp in candidates.groupby("lang"):
        samples.append(grp.index[0])
        if len(samples) >= 12:
            break
    if len(samples) < 5:
        for lang, grp in df.groupby("lang"):
            samples.append(grp.index[0])
    samples = samples[:12]

    Em    = E[samples]
    sim   = Em @ Em.T
    langs = [df["lang"].iloc[i] for i in samples]

    # etichetta corta: [LANG] prime 30 lettere
    def short_label(i, l):
        txt = re.sub(r"http\S+|@\w+|[^\w\s]", " ", df["text"].iloc[i])
        txt = " ".join(txt.split()[:6])
        return f"[{l.upper()}]  {txt[:32]}…"

    row_labels = [short_label(i, l) for i, l in zip(samples, langs)]

    fig, ax = plt.subplots(figsize=(13, 10))
    im = ax.imshow(sim, cmap="RdYlGn", vmin=0.0, vmax=1.0)

    ax.set_xticks(range(len(samples)))
    ax.set_yticks(range(len(samples)))
    ax.set_xticklabels(row_labels, rotation=40, ha="right", fontsize=8.5)
    ax.set_yticklabels(row_labels, fontsize=8.5)

    # colora etichette per lingua
    for tick, lang in zip(ax.get_xticklabels(), langs):
        tick.set_color(LANG_COLORS.get(lang, "#333333"))
    for tick, lang in zip(ax.get_yticklabels(), langs):
        tick.set_color(LANG_COLORS.get(lang, "#333333"))

    # valori nelle celle
    for i in range(len(samples)):
        for j in range(len(samples)):
            v = sim[i, j]
            clr = "white" if v > 0.75 or v < 0.15 else "black"
            ax.text(j, i, f"{v:.2f}", ha="center", va="center", fontsize=8, color=clr)

    plt.colorbar(im, ax=ax, label="Cosine Similarity", shrink=0.8)
    ax.set_title("Similarità coseno cross-lingua\n"
                 "Testi sullo stesso topic (AI/tech) in lingue diverse → celle verdi\n"
                 "Stesso significato = stesso punto nello spazio vettoriale",
                 fontsize=11, fontweight="bold", pad=15)
    plt.tight_layout()
    plt.savefig("output/02_crosslingual_heatmap.png", dpi=140, bbox_inches="tight")
    plt.close()
    print("[G2] 02_crosslingual_heatmap.png")
    return samples, sim, langs


# ── G3: CURVA VARIANZA PCA ────────────────────────────────────────────────────
def plot_pca_variance(pca):
    ev    = pca.explained_variance_ratio_
    cumev = np.cumsum(ev)
    n     = len(ev)
    final_pct = cumev[-1] * 100

    fig, axes = plt.subplots(1, 2, figsize=(13, 4))

    # barre varianza per componente
    axes[0].bar(range(1, n+1), ev*100, color="#3498db", alpha=0.75)
    axes[0].set_xlabel("Componente principale")
    axes[0].set_ylabel("Varianza spiegata (%)")
    axes[0].set_title("Varianza per componente\n"
                      "Ogni barra = una direzione nel dato", fontweight="bold")

    # curva cumulativa
    xs = range(1, n+1)
    axes[1].plot(xs, cumev*100, color="#e74c3c", linewidth=2.5)
    axes[1].fill_between(xs, cumev*100, alpha=0.12, color="#e74c3c")

    # soglie raggiungibili
    for threshold, color, lbl in [(80, "#7f8c8d", "80%"), (90, "#e67e22", "90%")]:
        k = int(np.searchsorted(cumev, threshold/100))
        if k < n:
            axes[1].axhline(threshold, color=color, linestyle="--", linewidth=1, label=f"{lbl}")
            axes[1].axvline(k+1, color=color, linestyle=":", linewidth=1)
            axes[1].annotate(f"{k+1} dim → {threshold}%",
                             xy=(k+1, threshold), xytext=(k+4, threshold-8),
                             fontsize=8, color=color,
                             arrowprops=dict(arrowstyle="->", color=color, lw=1))
        else:
            axes[1].axhline(threshold, color=color, linestyle="--", linewidth=1,
                            label=f"{lbl} (richiede >{n} dim)")

    # annotazione: dove siamo ora
    axes[1].axvline(n, color="#2ecc71", linestyle="-", linewidth=1.5, alpha=0.7)
    axes[1].annotate(f"Noi: {n} dim\n→ {final_pct:.1f}%",
                     xy=(n, final_pct), xytext=(n-18, final_pct-15),
                     fontsize=8.5, color="#27ae60", fontweight="bold",
                     arrowprops=dict(arrowstyle="->", color="#27ae60", lw=1.2))

    axes[1].set_xlim(0, n+2)
    axes[1].set_ylim(0, 102)
    axes[1].set_xlabel("N componenti")
    axes[1].set_ylabel("Varianza cumulativa (%)")
    axes[1].set_title("Varianza cumulativa\nQuante dimensioni bastano?", fontweight="bold")
    axes[1].legend(fontsize=8)

    fig.suptitle(f"PCA: da {pca.n_features_in_} → {n} dimensioni  "
                 f"(il significato è distribuito su molte direzioni)",
                 fontsize=10, color="#555555")
    plt.tight_layout()
    plt.savefig("output/03_pca_varianza.png", dpi=140, bbox_inches="tight")
    plt.close()
    print("[G3] 03_pca_varianza.png")


# ── G4: UMAP per LINGUA ───────────────────────────────────────────────────────
def plot_umap_by_language(E2d, df):
    langs_present = df["lang"].value_counts()
    langs_present = langs_present[langs_present >= 3].index.tolist()

    fig, ax = plt.subplots(figsize=(13, 9))

    # plotta lingue con < 3 tweet come grigio
    mask_other = ~df["lang"].isin(langs_present)
    if mask_other.sum():
        ax.scatter(E2d[mask_other, 0], E2d[mask_other, 1],
                   c="lightgray", s=8, alpha=0.3, label="altre", zorder=1)

    for lang in langs_present:
        mask  = df["lang"] == lang
        color = LANG_COLORS.get(lang, "#999999")
        name  = LANG_NAMES.get(lang, lang)
        ax.scatter(E2d[mask, 0], E2d[mask, 1],
                   c=color, s=25, alpha=0.75, label=f"{name} ({mask.sum()})",
                   linewidths=0, zorder=2)

    ax.set_title("UMAP 2D — colorato per lingua\n"
                 "Nota: tweet in lingue diverse si sovrappongono se parlano dello stesso topic",
                 fontsize=11, fontweight="bold")
    ax.set_xlabel("UMAP-1"); ax.set_ylabel("UMAP-2")
    ax.legend(loc="best", fontsize=8, markerscale=1.8, ncol=2, framealpha=0.9)
    plt.tight_layout()
    plt.savefig("output/04_umap_per_lingua.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("[G4] 04_umap_per_lingua.png")


# ── G5: UMAP per CLUSTER ──────────────────────────────────────────────────────
def plot_umap_by_cluster(E2d, df, labels, cluster_names):
    cids      = sorted(set(labels))
    real_cids = [c for c in cids if c != -1]
    n_real    = len(real_cids)
    cmap20    = plt.cm.get_cmap("tab20", n_real)
    cidx      = {cid: i for i, cid in enumerate(real_cids)}

    # top 8 cluster per dimensione (per annotare solo quelli)
    sizes     = {c: (labels == c).sum() for c in real_cids}
    top8      = sorted(real_cids, key=lambda c: -sizes[c])[:8]

    fig, ax = plt.subplots(figsize=(14, 10))

    # outlier prima (sotto)
    if -1 in cids:
        m = labels == -1
        ax.scatter(E2d[m, 0], E2d[m, 1], c=[(0.82, 0.82, 0.82, 0.18)],
                   s=6, linewidths=0, zorder=1, label="Outlier")

    # cluster
    for cid in real_cids:
        m     = labels == cid
        color = cmap20(cidx[cid])
        pct   = sizes[cid] / len(labels) * 100
        # nome breve nel legend: prime 2 keyword
        short = " / ".join(cluster_names.get(cid, f"C{cid}").split(" / ")[:2])
        lbl   = f"C{cid} {short} ({pct:.0f}%)" if cid in top8 else f"C{cid} ({pct:.0f}%)"
        ax.scatter(E2d[m, 0], E2d[m, 1], c=[color], s=20,
                   alpha=0.75, linewidths=0, zorder=2, label=lbl)

    # annotazioni solo sui top 8 (al centroide)
    for cid in top8:
        m      = labels == cid
        cx, cy = E2d[m, 0].mean(), E2d[m, 1].mean()
        short  = " / ".join(cluster_names.get(cid, f"C{cid}").split(" / ")[:2])
        ax.annotate(f"C{cid}\n{short}", (cx, cy),
                    fontsize=7.5, fontweight="bold", ha="center", va="center",
                    bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="gray",
                              alpha=0.88, linewidth=0.7))

    ax.set_title("UMAP 2D — topic cluster\n"
                 "Ogni colore = un argomento  |  Aree vicine = significati simili",
                 fontsize=11, fontweight="bold")
    ax.set_xlabel("UMAP-1"); ax.set_ylabel("UMAP-2")
    ax.legend(loc="upper left", fontsize=7, markerscale=1.8,
              ncol=2, framealpha=0.9, bbox_to_anchor=(1.01, 1))
    plt.tight_layout()
    plt.savefig("output/05_umap_per_cluster.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("[G5] 05_umap_per_cluster.png")


# ── G6: METRICHE CLUSTER ─────────────────────────────────────────────────────
def plot_cluster_metrics(Ehd, E2d, labels):
    valid = labels != -1
    if valid.sum() < 10 or len(set(labels[valid])) < 2:
        print("[G6] Dati insufficienti per metriche cluster")
        return {}

    sil = silhouette_score(Ehd[valid], labels[valid])
    dbi = davies_bouldin_score(Ehd[valid], labels[valid])

    all_cids = sorted(set(labels[labels != -1]))
    rows = []
    for cid in all_cids:
        mask   = labels == cid
        sub    = Ehd[mask]
        center = sub.mean(axis=0)
        intra  = np.linalg.norm(sub - center, axis=1).mean()
        rows.append({"cluster": cid, "size": int(mask.sum()), "intra_dist": round(intra, 4)})

    # usa solo top 10 per leggibilità
    rows_top = sorted(rows, key=lambda r: -r["size"])[:10]
    cids_top = [r["cluster"] for r in rows_top]
    xlabels  = [f"C{r['cluster']}" for r in rows_top]

    centroids_all = np.array([Ehd[labels == c].mean(axis=0) for c in all_cids])
    centroids_top = np.array([Ehd[labels == c].mean(axis=0) for c in cids_top])
    inter_top     = cdist(centroids_top, centroids_top, metric="euclidean")

    fig = plt.figure(figsize=(17, 5))
    gs  = gridspec.GridSpec(1, 3, figure=fig, wspace=0.45)

    # ── dimensione cluster (top 10) ──
    ax1 = fig.add_subplot(gs[0])
    colors_bar = plt.cm.tab20(np.linspace(0, 1, len(rows_top)))
    ax1.barh([r["cluster"] for r in rows_top],
             [r["size"] for r in rows_top],
             color=colors_bar, alpha=0.85)
    ax1.set_yticks([r["cluster"] for r in rows_top])
    ax1.set_yticklabels(xlabels, fontsize=9)
    ax1.invert_yaxis()
    ax1.set_xlabel("N tweet")
    ax1.set_title(f"Dimensione cluster (top 10)\nSilhouette = {sil:.3f}  |  DBI = {dbi:.3f}",
                  fontweight="bold")
    for i, r in enumerate(rows_top):
        ax1.text(r["size"] + 1, i, str(r["size"]), va="center", fontsize=8)

    # ── raggio medio intra-cluster ──
    ax2 = fig.add_subplot(gs[1])
    bars = ax2.barh([r["cluster"] for r in rows_top],
                    [r["intra_dist"] for r in rows_top],
                    color=colors_bar, alpha=0.85)
    ax2.set_yticks([r["cluster"] for r in rows_top])
    ax2.set_yticklabels(xlabels, fontsize=9)
    ax2.invert_yaxis()
    ax2.set_xlabel("Raggio medio (distanza dal centroide)")
    ax2.set_title("Compattezza cluster\nBasso = cluster coerente e denso",
                  fontweight="bold")

    # ── heatmap distanze inter-cluster (top 10, senza numeri) ──
    ax3 = fig.add_subplot(gs[2])
    im  = ax3.imshow(inter_top, cmap="YlOrRd", aspect="auto")
    ax3.set_xticks(range(len(cids_top)))
    ax3.set_yticks(range(len(cids_top)))
    ax3.set_xticklabels(xlabels, fontsize=8, rotation=45, ha="right")
    ax3.set_yticklabels(xlabels, fontsize=8)
    plt.colorbar(im, ax=ax3, shrink=0.85, label="Distanza euclidea")
    ax3.set_title("Distanze inter-cluster (top 10)\nScuro = vicini  |  Chiaro = ben separati",
                  fontweight="bold")

    fig.suptitle("Qualità del clustering — separazione e coesione",
                 fontsize=12, fontweight="bold")
    plt.tight_layout()
    plt.savefig("output/06_metriche_cluster.png", dpi=140, bbox_inches="tight")
    plt.close()
    print(f"[G6] 06_metriche_cluster.png  |  silhouette={sil:.3f}  DBI={dbi:.3f}")
    return {"silhouette": round(sil, 4), "davies_bouldin": round(dbi, 4), "clusters": rows}


# ── G7: LIVELLI COGNITIVI ─────────────────────────────────────────────────────
def plot_cognitive_levels(E2d, df, density, level):
    fig, axes = plt.subplots(1, 2, figsize=(16, 7))

    # scatter dimensionato per densità
    scatter = axes[0].scatter(
        E2d[:, 0], E2d[:, 1],
        c=density, cmap="plasma",
        s=(density * 60 + 5),
        alpha=0.7, linewidths=0
    )
    plt.colorbar(scatter, ax=axes[0], label="Densità locale (KNN)")
    axes[0].set_title("Densità locale nel feed\nGrande/Chiaro = mainstream | Piccolo/Scuro = niché",
                      fontweight="bold")
    axes[0].set_xlabel("UMAP-1"); axes[0].set_ylabel("UMAP-2")

    # distribuzione per livello
    level_counts = pd.Series(level).value_counts()
    colors_lv    = {"mainstream": "#2ecc71", "intermedio": "#f39c12", "niché/tecnico": "#e74c3c"}
    bars = axes[1].barh(
        level_counts.index,
        level_counts.values,
        color=[colors_lv.get(l, "gray") for l in level_counts.index]
    )
    for bar, val in zip(bars, level_counts.values):
        pct = val / len(level) * 100
        axes[1].text(bar.get_width() + 5, bar.get_y() + bar.get_height()/2,
                     f"{pct:.1f}%", va="center", fontsize=10)
    axes[1].set_title("Distribuzione livelli cognitivi nel feed\n"
                      "(basata su densità KNN dello spazio vettoriale)", fontweight="bold")
    axes[1].set_xlabel("N tweet")

    # esempi per livello
    for lv, color in colors_lv.items():
        mask_lv = np.array(level) == lv
        if mask_lv.sum() == 0:
            continue
        # i 3 più "centrali" per quel livello (distanza media dai vicini)
        idxs = np.where(mask_lv)[0]
        dens_lv = density[idxs]
        if lv == "mainstream":
            top3 = idxs[np.argsort(dens_lv)[-3:]]
        elif lv == "niché/tecnico":
            top3 = idxs[np.argsort(dens_lv)[:3]]
        else:
            mid = np.argsort(np.abs(dens_lv - 0.5))[:3]
            top3 = idxs[mid]
        axes[0].scatter(E2d[top3, 0], E2d[top3, 1],
                        s=120, c=color, edgecolors="black",
                        linewidths=1.5, zorder=5, label=lv)

    axes[0].legend(fontsize=8)
    plt.tight_layout()
    plt.savefig("output/07_livelli_cognitivi.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("[G7] 07_livelli_cognitivi.png")


# ── G8: RICERCA CROSS-LINGUAL ─────────────────────────────────────────────────
def crosslingual_search(E, df, model):
    queries = [
        "intelligenza artificiale e automazione del lavoro",
        "crisi politica e governo",
        "criptovalute e investimenti",
    ]
    results = {}

    def strip_ctrl(s):
        return re.sub(r"[\x00-\x1f\x7f-\x9f]", "", s)

    fig, axes = plt.subplots(len(queries), 1, figsize=(16, 5 * len(queries)))

    for ax, query in zip(axes, queries):
        qvec = model.encode([query], normalize_embeddings=True)[0]
        sims = E @ qvec
        top  = np.argsort(sims)[::-1][:7]

        results[query] = [
            {"rank": i+1, "lang": df["lang"].iloc[idx],
             "score": round(float(sims[idx]), 4),
             "text": df["text"].iloc[idx][:130]}
            for i, idx in enumerate(top)
        ]

        ax.axis("off")
        table_data = [
            [f"#{r['rank']}", r["lang"].upper(), f"{r['score']:.3f}",
             strip_ctrl(r["text"])[:110]]
            for r in results[query]
        ]
        tbl = ax.table(cellText=table_data,
                       colLabels=["#", "Lingua", "Score", "Tweet"],
                       loc="center", cellLoc="left")
        tbl.auto_set_font_size(False)
        tbl.set_fontsize(9.5)
        tbl.scale(1, 1.7)
        tbl.auto_set_column_width([0, 1, 2, 3])

        # header scuro
        for col in range(4):
            tbl[0, col].set_facecolor("#2c3e50")
            tbl[0, col].set_text_props(color="white", fontweight="bold")

        # colora lingua per riga
        for row_i, r in enumerate(results[query], start=1):
            lc = LANG_COLORS.get(r["lang"], "#ecf0f1")
            tbl[row_i, 1].set_facecolor(lc)
            tbl[row_i, 1].set_text_props(color="white", fontweight="bold")
            # score → sfondo da verde a giallo
            score_norm = (r["score"] - 0.3) / 0.5
            bg = plt.cm.RdYlGn(min(max(score_norm, 0), 1))
            tbl[row_i, 2].set_facecolor(bg)

        ax.set_title(f'🔍 Query: "{query}"', fontsize=11, fontweight="bold", pad=20)

    fig.suptitle("Ricerca Semantica Cross-Lingual\n"
                 "Query scritta in italiano → trova tweet simili in qualsiasi lingua",
                 fontsize=12, fontweight="bold")
    plt.tight_layout(pad=2)
    plt.savefig("output/08_ricerca_crosslingual.png", dpi=140, bbox_inches="tight")
    plt.close()
    print("[G8] 08_ricerca_crosslingual.png")
    return results


# ── G9: CORRELAZIONI TEMPORALI ────────────────────────────────────────────────
def plot_temporal_correlation(df, labels, cluster_names):
    df2 = df.copy()
    df2["cluster"] = labels
    df2 = df2[df2["dt"].notna() & (df2["cluster"] != -1)]
    if df2.empty:
        print("[G9] Skip — nessun dato temporale")
        return

    df2["hour"] = df2["dt"].dt.floor("1h")
    pivot_all = df2.groupby(["hour", "cluster"]).size().unstack(fill_value=0)

    # tieni solo i top 8 cluster per volume totale
    top8 = pivot_all.sum().nlargest(8).index.tolist()
    pivot = pivot_all[top8]

    if len(top8) < 2:
        print("[G9] Skip — meno di 2 cluster con dati temporali")
        return

    # nomi brevi
    def short(cid):
        n = cluster_names.get(cid, f"C{cid}")
        return f"C{cid}: {' / '.join(n.split(' / ')[:2])}"

    short_names = {c: short(c) for c in top8}

    # matrice correlazione
    corr = np.zeros((len(top8), len(top8)))
    for i, ca in enumerate(top8):
        for j, cb in enumerate(top8):
            r, _ = pearsonr(pivot[ca], pivot[cb])
            corr[i, j] = r

    cmap8 = plt.cm.tab10

    fig, axes = plt.subplots(1, 2, figsize=(16, 6))

    # heatmap correlazioni (8×8, leggibile)
    im = axes[0].imshow(corr, cmap="coolwarm", vmin=-1, vmax=1)
    tick_labels = [short_names[c] for c in top8]
    axes[0].set_xticks(range(len(top8)))
    axes[0].set_yticks(range(len(top8)))
    axes[0].set_xticklabels(tick_labels, rotation=35, ha="right", fontsize=8)
    axes[0].set_yticklabels(tick_labels, fontsize=8)
    for i in range(len(top8)):
        for j in range(len(top8)):
            v = corr[i, j]
            clr = "white" if abs(v) > 0.6 else "black"
            axes[0].text(j, i, f"{v:.2f}", ha="center", va="center",
                         fontsize=8, fontweight="bold", color=clr)
    plt.colorbar(im, ax=axes[0], shrink=0.85,
                 label="Pearson r  (+1 = si muovono insieme)")
    axes[0].set_title("Correlazione temporale tra cluster (top 8)\n"
                      "Rosso = si muovono insieme  |  Blu = si muovono in opposizione",
                      fontweight="bold")

    # serie temporali
    for i, c in enumerate(top8):
        axes[1].plot(pivot.index, pivot[c], label=short_names[c],
                     color=cmap8(i), linewidth=1.6, marker=".", markersize=4)
    axes[1].set_title("Volume tweet orario — top 8 cluster", fontweight="bold")
    axes[1].set_ylabel("Tweet / ora")
    axes[1].legend(fontsize=7.5, loc="upper left", framealpha=0.9)
    axes[1].tick_params(axis="x", rotation=30)

    plt.tight_layout()
    plt.savefig("output/09_correlazioni_temporali.png", dpi=140, bbox_inches="tight")
    plt.close()
    print("[G9] 09_correlazioni_temporali.png")


# ── G10: PROFILO ALGORITMICO ──────────────────────────────────────────────────
def plot_profilo_algoritmico(labels, cluster_names, df=None):
    """
    "Questo è il mio profilo secondo l'algoritmo"
    Top 8 cluster per percentuale, con barre orizzontali chiare.
    """
    total = len(labels)
    rows = []
    for cid in sorted(set(labels)):
        if cid == -1:
            continue
        mask = labels == cid
        pct  = mask.sum() / total * 100
        # lingua dominante del cluster
        lang = df[mask]["lang"].value_counts().index[0] if df is not None else "?"
        # tweet rappresentativo: primo del cluster (già ordinato per distanza in make_cluster_names)
        snippet = cluster_names.get(cid, f"C{cid}")
        rows.append({"snippet": snippet, "pct": pct, "cid": cid, "lang": lang})

    rows = sorted(rows, key=lambda r: -r["pct"])[:10]

    fig, ax = plt.subplots(figsize=(14, 7))
    cmap = plt.cm.tab10
    max_pct = max(r["pct"] for r in rows)

    for i, r in enumerate(rows):
        color = cmap(i % 10)
        ax.barh(i, r["pct"], color=color, alpha=0.85, height=0.6)

        # percentuale a destra della barra
        ax.text(r["pct"] + 0.3, i, f"{r['pct']:.1f}%",
                va="center", fontsize=11, fontweight="bold", color=color)

        # badge lingua
        lang_color = LANG_COLORS.get(r["lang"], "#999")
        ax.text(-0.8, i, f"[{r['lang'].upper()}]",
                va="center", ha="right", fontsize=8,
                color="white", fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.2", fc=lang_color, ec="none"))

        # testo tweet rappresentativo
        ax.text(-2.2, i, f'"{r["snippet"]}"',
                va="center", ha="right", fontsize=8.5,
                color="#2c3e50", style="italic")

    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([""] * len(rows))
    ax.invert_yaxis()
    ax.set_xlim(-max_pct * 2.2, max_pct + 6)
    ax.axvline(0, color="#bdc3c7", linewidth=0.8)
    ax.set_xlabel("% dei tweet nel feed", fontsize=11)
    ax.set_title("Il tuo profilo algoritmico\n"
                 "Cosa pensa di te l'algoritmo di X  —  ogni riga = tweet più rappresentativo del cluster",
                 fontsize=12, fontweight="bold", pad=15)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_visible(False)
    ax.tick_params(axis="y", length=0)

    plt.tight_layout()
    plt.savefig("output/10_profilo_algoritmico.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("[G10] 10_profilo_algoritmico.png")


# ── CLUSTER LABELS — usa il tweet più rappresentativo come etichetta ──────────
def make_cluster_names(df, labels, E, Ehd):
    names     = {}
    rep_texts = {}

    # carica etichette manuali/generate se disponibili
    manual = {}
    label_path = "output/cluster_labels.json"
    if os.path.exists(label_path):
        with open(label_path, encoding="utf-8") as f:
            raw = json.load(f)
        manual = {int(k): v for k, v in raw.items()}

    for cid in sorted(set(labels)):
        if cid == -1:
            names[-1]     = "Outlier"
            rep_texts[-1] = ""
            continue

        mask      = labels == cid
        positions = np.where(mask)[0]
        center    = Ehd[mask].mean(axis=0)
        dists     = np.linalg.norm(Ehd[mask] - center, axis=1)
        best_i    = positions[np.argmin(dists)]
        tweet     = df["text"].iloc[best_i]
        rep_texts[cid] = tweet

        if cid in manual:
            names[cid] = manual[cid]
        else:
            snippet = re.sub(r"http\S+|@\w+|#", "", tweet).strip()
            snippet = re.sub(r"\s+", " ", snippet)[:60].strip()
            names[cid] = snippet or f"Cluster {cid}"

    print("[names]")
    for cid, name in names.items():
        if cid != -1:
            print(f"  C{cid}: {name}")

    return names, rep_texts

from collections import Counter


# ── REPORT JSON ───────────────────────────────────────────────────────────────
def save_report(df, labels, cluster_names, density, level, metrics, search_results):
    lang_dist   = df["lang"].value_counts().to_dict()
    level_dist  = pd.Series(level).value_counts().to_dict()

    cluster_summary = []
    for cid in sorted(set(labels)):
        mask = labels == cid
        sub  = df[mask]
        cluster_summary.append({
            "id":       int(cid),
            "name":     cluster_names.get(cid, f"C{cid}"),
            "size":     int(mask.sum()),
            "pct":      round(float(mask.sum()) / len(labels) * 100, 2),
            "langs":    sub["lang"].value_counts().to_dict(),
        })

    report = {
        "totale_tweet":      len(df),
        "lingue":            lang_dist,
        "livelli_cognitivi": level_dist,
        "cluster":           cluster_summary,
        "metriche_cluster":  metrics,
        "crosslingual_demo": {
            q: [{"lang": r["lang"], "score": r["score"], "text": r["text"]}
                for r in res[:3]]
            for q, res in search_results.items()
        },
    }

    def _serialize(o):
        if isinstance(o, (np.integer,)): return int(o)
        if isinstance(o, (np.floating,)): return float(o)
        raise TypeError(f"Not serializable: {type(o)}")

    with open("output/report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2, default=_serialize)
    print("[save] output/report.json")


# ── PRINT FINALE ──────────────────────────────────────────────────────────────
def print_summary(df, labels, cluster_names, density, level):
    print("\n" + "═"*65)
    print("  FEED X — ANALISI VETTORIALE — SOMMARIO")
    print("═"*65)
    print(f"\n  Tweet totali   : {len(df)}")
    print(f"  Lingue         : {df['lang'].value_counts().to_dict()}")
    print(f"  Dimensioni emb : {384} → PCA {PCA_DIMS} → UMAP 2D")

    print("\n  CLUSTER:")
    for cid, name in sorted(cluster_names.items()):
        mask = labels == cid
        n    = mask.sum()
        pct  = n / len(labels) * 100
        bar  = "█" * max(1, int(pct/2))
        print(f"    C{cid:>2} {name:<30} {pct:5.1f}% {bar}")

    lv_ct = pd.Series(level).value_counts()
    print("\n  LIVELLI COGNITIVI:")
    for lv, n in lv_ct.items():
        print(f"    {lv:<20} {n:>5} tweet  ({n/len(level)*100:.1f}%)")

    print("\n  OUTPUT:")
    for f in sorted(os.listdir("output")):
        print(f"    output/{f}")
    print("═"*65)


# ── MAIN ──────────────────────────────────────────────────────────────────────
def main():
    # 1. Dati
    df  = preprocess(load(DATA_FILE, MAX_DOCS))

    # 2. Embedding
    print(f"\n[embed] Carico modello {MODEL_NAME}…")
    model = SentenceTransformer(MODEL_NAME)
    E     = model.encode(df["clean"].tolist(), batch_size=64,
                         show_progress_bar=True, normalize_embeddings=True
                         ).astype(np.float32)
    print(f"[embed] shape: {E.shape}")

    # 3. Riduzione
    pca, Ep, Ehd, E2d = reduce(E)

    # 4. Clustering
    labels = cluster(Ehd)
    df["cluster"] = labels

    # 5. Livelli cognitivi
    density, level = cognitive_level(Ehd)
    df["density"]  = density
    df["level"]    = level

    # 6. Nomi cluster
    cluster_names, rep_texts = make_cluster_names(df, labels, E, Ehd)
    print("[names]")
    for cid, name in sorted(cluster_names.items()):
        if cid != -1:
            print(f"  C{cid}: {name}")

    # ── Grafici ──
    plot_tweet_as_vector(E, df)
    plot_crosslingual_heatmap(E, df)
    plot_pca_variance(pca)
    plot_umap_by_language(E2d, df)
    plot_umap_by_cluster(E2d, df, labels, cluster_names)
    metrics = plot_cluster_metrics(Ehd, E2d, labels)
    plot_cognitive_levels(E2d, df, density, level)
    search_results = crosslingual_search(E, df, model)
    plot_temporal_correlation(df, labels, cluster_names)
    plot_profilo_algoritmico(labels, cluster_names, df)

    # ── Report ──
    save_report(df, labels, cluster_names, density, level, metrics, search_results)
    df.drop(columns=["density","level","cluster"], errors="ignore"
            ).assign(cluster=labels, density=density, level=level
            ).to_csv("output/tweets_full.csv", index=False, encoding="utf-8")

    print_summary(df, labels, cluster_names, density, level)


if __name__ == "__main__":
    main()
