#!/usr/bin/env python3
"""
03_clustering.py — Clustering e visualizzazione dei campioni
Legge output/features.csv, scala le feature, applica PCA + t-SNE,
addestra un classificatore (Random Forest), produce grafici.

Output:
  output/01_scatter_tsne.png       — t-SNE con cluster per modello
  output/02_scatter_pca.png        — PCA 2D con cluster per modello
  output/03_confusion_matrix.png   — Matrice di confusione del classificatore
  output/04_feature_importance.png — Importanza feature (Random Forest)
  output/05_distribuzioni.png      — Distribuzione feature chiave per modello
  output/06_radar.png              — Radar chart delle feature medie
  output/risultati.json            — Metriche del classificatore

Requisiti:
  pip install pandas scikit-learn matplotlib numpy
"""

import csv
import json
import os
import numpy as np

INPUT_FILE = 'output/features.csv'
OUTPUT_DIR = 'output'

# feature numeriche da usare
FEATURE_COLS = [
    'media_len_frasi', 'std_len_frasi', 'ttr', 'hapax_ratio',
    'media_len_parole', 'ratio_parole_lunghe', 'entropia_char',
    'freq_punct_1k', 'virgole_1k', 'punti_1k', 'due_punti_1k',
    'punto_virgola_1k', 'trattini_1k', 'ratio_bg_ripetuti',
    'ratio_conj_start', 'n_paragrafi',
]

COLORI = {
    'claude': '#7c4dff',
    'chatgpt': '#00ff88',
    'ollama': '#ff6b6b',
}

NOMI_DISPLAY = {
    'claude': 'Claude',
    'chatgpt': 'ChatGPT',
    'ollama': 'Locale',
}


def carica_dati():
    """Carica CSV e ritorna X (feature), y (etichette), nomi."""
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        righe = list(reader)

    X = []
    y = []
    ids = []
    for r in righe:
        feat = []
        valido = True
        for col in FEATURE_COLS:
            try:
                feat.append(float(r[col]))
            except (ValueError, KeyError):
                valido = False
                break
        if valido:
            X.append(feat)
            y.append(r['modello'])
            ids.append(r['id'])

    return np.array(X), np.array(y), ids


def scala_features(X):
    """Standardizzazione z-score."""
    mu = X.mean(axis=0)
    sigma = X.std(axis=0)
    sigma[sigma == 0] = 1
    return (X - mu) / sigma, mu, sigma


def pca_2d(X_scaled):
    """PCA manuale a 2 componenti (senza sklearn per questa parte)."""
    cov = np.cov(X_scaled.T)
    eigenvalues, eigenvectors = np.linalg.eigh(cov)
    idx = np.argsort(eigenvalues)[::-1]
    eigenvalues = eigenvalues[idx]
    eigenvectors = eigenvectors[:, idx]
    variance_explained = eigenvalues[:2] / eigenvalues.sum()
    return X_scaled @ eigenvectors[:, :2], variance_explained


def tsne_2d(X_scaled, perplexity=30, n_iter=1000, lr=200):
    """t-SNE semplificato. Usa sklearn se disponibile, altrimenti PCA."""
    try:
        from sklearn.manifold import TSNE
        tsne = TSNE(n_components=2, perplexity=min(perplexity, len(X_scaled) - 1),
                     n_iter=n_iter, learning_rate=lr, random_state=42)
        return tsne.fit_transform(X_scaled)
    except ImportError:
        print('  sklearn non disponibile, uso PCA al posto di t-SNE')
        return pca_2d(X_scaled)[0]


def plot_scatter(coords, y, titolo, path, xlabel='', ylabel=''):
    """Scatter plot colorato per modello."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(10, 8))
    fig.patch.set_facecolor('#0d1117')
    ax.set_facecolor('#0d1117')

    for modello in sorted(set(y)):
        mask = y == modello
        ax.scatter(
            coords[mask, 0], coords[mask, 1],
            c=COLORI.get(modello, '#ffffff'),
            label=NOMI_DISPLAY.get(modello, modello),
            alpha=0.7, s=60, edgecolors='white', linewidths=0.3,
        )

    ax.set_title(titolo, color='white', fontsize=14, fontweight='bold', pad=15)
    ax.set_xlabel(xlabel, color='#8b949e')
    ax.set_ylabel(ylabel, color='#8b949e')
    ax.tick_params(colors='#8b949e')
    for spine in ax.spines.values():
        spine.set_color('#30363d')
    ax.legend(facecolor='#161b22', edgecolor='#30363d', labelcolor='white',
              fontsize=11, loc='best')
    ax.grid(True, alpha=0.1)

    plt.tight_layout()
    plt.savefig(path, dpi=150, facecolor='#0d1117')
    plt.close()
    print(f'  Salvato: {path}')


def plot_confusion_matrix(y_true, y_pred, labels, path):
    """Matrice di confusione."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    n = len(labels)
    cm = np.zeros((n, n), dtype=int)
    label_idx = {l: i for i, l in enumerate(labels)}
    for t, p in zip(y_true, y_pred):
        cm[label_idx[t], label_idx[p]] += 1

    fig, ax = plt.subplots(figsize=(8, 7))
    fig.patch.set_facecolor('#0d1117')
    ax.set_facecolor('#0d1117')

    im = ax.imshow(cm, cmap='Purples', aspect='auto')

    display_labels = [NOMI_DISPLAY.get(l, l) for l in labels]
    ax.set_xticks(range(n))
    ax.set_yticks(range(n))
    ax.set_xticklabels(display_labels, color='white', fontsize=11)
    ax.set_yticklabels(display_labels, color='white', fontsize=11)
    ax.set_xlabel('Predetto', color='#8b949e', fontsize=12)
    ax.set_ylabel('Reale', color='#8b949e', fontsize=12)
    ax.set_title('Matrice di Confusione — Model Attribution', color='white',
                 fontsize=14, fontweight='bold', pad=15)

    for i in range(n):
        for j in range(n):
            val = cm[i, j]
            color = 'white' if val > cm.max() * 0.5 else '#c8c8d8'
            ax.text(j, i, str(val), ha='center', va='center',
                    color=color, fontsize=16, fontweight='bold')

    for spine in ax.spines.values():
        spine.set_color('#30363d')

    plt.tight_layout()
    plt.savefig(path, dpi=150, facecolor='#0d1117')
    plt.close()
    print(f'  Salvato: {path}')


def plot_feature_importance(importances, feature_names, path):
    """Bar chart importanza feature."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    idx = np.argsort(importances)[::-1][:12]
    names = [feature_names[i] for i in idx]
    vals = importances[idx]

    fig, ax = plt.subplots(figsize=(10, 6))
    fig.patch.set_facecolor('#0d1117')
    ax.set_facecolor('#0d1117')

    bars = ax.barh(range(len(names)), vals, color='#7c4dff', edgecolor='#0d1117')
    ax.set_yticks(range(len(names)))
    ax.set_yticklabels(names, color='#c8c8d8', fontsize=10, fontfamily='monospace')
    ax.invert_yaxis()
    ax.set_xlabel('Importanza (Gini)', color='#8b949e')
    ax.set_title('Feature Importance — Random Forest', color='white',
                 fontsize=14, fontweight='bold', pad=15)
    ax.tick_params(colors='#8b949e')
    for spine in ax.spines.values():
        spine.set_color('#30363d')
    ax.grid(True, axis='x', alpha=0.1)

    plt.tight_layout()
    plt.savefig(path, dpi=150, facecolor='#0d1117')
    plt.close()
    print(f'  Salvato: {path}')


def plot_distribuzioni(X, y, feature_names, path):
    """Distribuzione delle feature chiave per modello (violin/box)."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    chiave = ['media_len_frasi', 'ttr', 'virgole_1k', 'entropia_char',
              'ratio_parole_lunghe', 'ratio_bg_ripetuti']
    indici = [feature_names.index(f) for f in chiave if f in feature_names]
    nomi = [chiave[i] for i, _ in enumerate(indici)]

    fig, axes = plt.subplots(2, 3, figsize=(14, 9))
    fig.patch.set_facecolor('#0d1117')
    fig.suptitle('Distribuzione Feature per Modello', color='white',
                 fontsize=14, fontweight='bold', y=0.98)

    modelli = sorted(set(y))

    for ax_idx, (feat_idx, feat_name) in enumerate(zip(indici, nomi)):
        ax = axes[ax_idx // 3][ax_idx % 3]
        ax.set_facecolor('#0d1117')

        data = []
        colors = []
        positions = []
        for i, m in enumerate(modelli):
            mask = y == m
            vals = X[mask, feat_idx]
            data.append(vals)
            colors.append(COLORI.get(m, '#ffffff'))
            positions.append(i)

        bp = ax.boxplot(data, positions=positions, widths=0.6, patch_artist=True,
                        showfliers=True, flierprops={'marker': '.', 'markersize': 3,
                                                      'markerfacecolor': '#8b949e'})

        for patch, color in zip(bp['boxes'], colors):
            patch.set_facecolor(color + '40')
            patch.set_edgecolor(color)
        for element in ['whiskers', 'caps']:
            for line in bp[element]:
                line.set_color('#8b949e')
        for median in bp['medians']:
            median.set_color('white')
            median.set_linewidth(2)

        ax.set_xticks(positions)
        ax.set_xticklabels([NOMI_DISPLAY.get(m, m) for m in modelli],
                           color='#c8c8d8', fontsize=9)
        ax.set_title(feat_name, color='#c8c8d8', fontsize=10, fontfamily='monospace')
        ax.tick_params(colors='#8b949e')
        for spine in ax.spines.values():
            spine.set_color('#30363d')
        ax.grid(True, axis='y', alpha=0.1)

    plt.tight_layout()
    plt.savefig(path, dpi=150, facecolor='#0d1117')
    plt.close()
    print(f'  Salvato: {path}')


def plot_radar(X, y, feature_names, path):
    """Radar chart delle feature medie per modello."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    chiave = ['media_len_frasi', 'ttr', 'virgole_1k', 'entropia_char',
              'ratio_parole_lunghe', 'media_len_parole', 'std_len_frasi',
              'ratio_bg_ripetuti']
    indici = [feature_names.index(f) for f in chiave if f in feature_names]
    nomi_radar = [chiave[i] for i, _ in enumerate(indici)]

    modelli = sorted(set(y))
    medie = {}
    for m in modelli:
        mask = y == m
        medie[m] = X[mask][:, indici].mean(axis=0)

    # normalizza 0-1 per il radar
    all_vals = np.array(list(medie.values()))
    mins = all_vals.min(axis=0)
    maxs = all_vals.max(axis=0)
    rng = maxs - mins
    rng[rng == 0] = 1

    N = len(nomi_radar)
    angles = np.linspace(0, 2 * np.pi, N, endpoint=False).tolist()
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(polar=True))
    fig.patch.set_facecolor('#0d1117')
    ax.set_facecolor('#0d1117')

    for m in modelli:
        vals = (medie[m] - mins) / rng
        vals = vals.tolist() + vals[:1].tolist()
        color = COLORI.get(m, '#ffffff')
        ax.plot(angles, vals, 'o-', linewidth=2, color=color,
                label=NOMI_DISPLAY.get(m, m))
        ax.fill(angles, vals, alpha=0.1, color=color)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(nomi_radar, color='#c8c8d8', fontsize=8, fontfamily='monospace')
    ax.set_yticklabels([])
    ax.set_title('Profilo Stilometrico per Modello', color='white',
                 fontsize=14, fontweight='bold', pad=20)
    ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1),
              facecolor='#161b22', edgecolor='#30363d', labelcolor='white')
    ax.grid(color='#30363d')
    ax.spines['polar'].set_color('#30363d')

    plt.tight_layout()
    plt.savefig(path, dpi=150, facecolor='#0d1117', bbox_inches='tight')
    plt.close()
    print(f'  Salvato: {path}')


def main():
    print('=== Clustering e Classificazione ===\n')

    X, y, ids = carica_dati()
    print(f'Campioni caricati: {len(X)}')
    print(f'Modelli: {dict(zip(*np.unique(y, return_counts=True)))}')

    X_scaled, mu, sigma = scala_features(X)

    # --- PCA ---
    print('\nPCA...')
    X_pca, var_expl = pca_2d(X_scaled)
    print(f'  Varianza spiegata: PC1={var_expl[0]:.1%}, PC2={var_expl[1]:.1%}')
    plot_scatter(X_pca, y, f'PCA — Campioni per Modello\n(var. spiegata: {var_expl[0]+var_expl[1]:.1%})',
                 os.path.join(OUTPUT_DIR, '02_scatter_pca.png'),
                 f'PC1 ({var_expl[0]:.1%})', f'PC2 ({var_expl[1]:.1%})')

    # --- t-SNE ---
    print('t-SNE...')
    X_tsne = tsne_2d(X_scaled)
    plot_scatter(X_tsne, y, 't-SNE — Campioni per Modello',
                 os.path.join(OUTPUT_DIR, '01_scatter_tsne.png'),
                 't-SNE 1', 't-SNE 2')

    # --- Classificatore ---
    print('\nRandom Forest...')
    try:
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.model_selection import cross_val_predict, StratifiedKFold
        from sklearn.metrics import classification_report, accuracy_score

        clf = RandomForestClassifier(n_estimators=200, random_state=42, max_depth=10)
        cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
        y_pred = cross_val_predict(clf, X_scaled, y, cv=cv)

        acc = accuracy_score(y, y_pred)
        print(f'  Accuracy (5-fold CV): {acc:.1%}')
        print()
        print(classification_report(y, y_pred,
              target_names=[NOMI_DISPLAY.get(m, m) for m in sorted(set(y))]))

        labels = sorted(set(y))
        plot_confusion_matrix(y, y_pred, labels,
                              os.path.join(OUTPUT_DIR, '03_confusion_matrix.png'))

        # feature importance (fit su tutto il dataset)
        clf.fit(X_scaled, y)
        plot_feature_importance(clf.feature_importances_, FEATURE_COLS,
                                os.path.join(OUTPUT_DIR, '04_feature_importance.png'))

        # salva risultati
        risultati = {
            'accuracy': round(acc, 4),
            'n_campioni': len(X),
            'n_features': len(FEATURE_COLS),
            'modelli': dict(zip(*[a.tolist() for a in np.unique(y, return_counts=True)])),
            'varianza_pca': [round(v, 4) for v in var_expl.tolist()],
            'top_features': [
                {'nome': FEATURE_COLS[i], 'importanza': round(clf.feature_importances_[i], 4)}
                for i in np.argsort(clf.feature_importances_)[::-1][:8]
            ],
        }

        with open(os.path.join(OUTPUT_DIR, 'risultati.json'), 'w') as f:
            json.dump(risultati, f, indent=2)
        print(f'  Salvato: {os.path.join(OUTPUT_DIR, "risultati.json")}')

    except ImportError:
        print('  sklearn non disponibile, salto classificazione.')

    # --- Distribuzioni ---
    print('\nDistribuzioni...')
    plot_distribuzioni(X, y, FEATURE_COLS, os.path.join(OUTPUT_DIR, '05_distribuzioni.png'))

    # --- Radar ---
    print('Radar...')
    plot_radar(X, y, FEATURE_COLS, os.path.join(OUTPUT_DIR, '06_radar.png'))

    print('\nFatto.')


if __name__ == '__main__':
    main()
