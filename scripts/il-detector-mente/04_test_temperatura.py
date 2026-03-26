#!/usr/bin/env python3
"""
04_test_temperatura.py — Test di robustezza: temperatura
Stesso prompt, stessi modelli (Claude + ChatGPT), tre temperature diverse.
Verifica se i cluster tengono quando cambi la temperature.

Output:
  output/campioni_temperatura.json
  output/features_temperatura.csv
  output/07_temperatura_pca.png
  output/08_temperatura_accuracy.png
  output/risultati_temperatura.json

Requisiti:
  pip install anthropic openai pandas scikit-learn matplotlib numpy
"""

import json
import os
import time
import csv
import numpy as np

OUTPUT_DIR = 'output'
os.makedirs(OUTPUT_DIR, exist_ok=True)

TEMPERATURE = [0.3, 0.7, 1.0]
N_CAMPIONI_PER_COND = 30  # per modello per temperatura = 30*2*3 = 180

PROMPTS = [
    'Spiega come funziona il protocollo TCP in modo tecnico.',
    'Descrivi il funzionamento di una hash table e le strategie di collision resolution.',
    'Spiega la differenza tra processi e thread in un sistema operativo moderno.',
    'Come funziona il garbage collector in Java? Descrivi le generazioni e gli algoritmi.',
    'Spiega il teorema CAP nei sistemi distribuiti con esempi concreti.',
    'Descrivi come funziona TLS 1.3 e cosa cambia rispetto a TLS 1.2.',
    'Spiega il funzionamento di un B-tree e perche\' i database lo usano per gli indici.',
    'Come funziona il meccanismo di attention nei transformer?',
    'Descrivi il protocollo Raft per il consenso distribuito.',
    'Spiega come funziona la memoria virtuale e il page fault handling.',
    'Descrivi l\'architettura di un compilatore moderno, dal lexer al codegen.',
    'Come funziona il protocollo BGP e perche\' e\' critico per Internet?',
    'Spiega il funzionamento di ECDSA e perche\' si usa nelle blockchain.',
    'Descrivi come funziona un container Linux a livello di kernel (namespaces, cgroups).',
    'Spiega il funzionamento di MapReduce e i suoi limiti.',
]

CAMPIONI_FILE = os.path.join(OUTPUT_DIR, 'campioni_temperatura.json')


def genera_claude(prompt, temperature):
    import anthropic
    client = anthropic.Anthropic()
    resp = client.messages.create(
        model='claude-sonnet-4-20250514',
        max_tokens=1024,
        temperature=temperature,
        messages=[{'role': 'user', 'content': prompt}],
    )
    return resp.content[0].text


def genera_chatgpt(prompt, temperature):
    import openai
    resp = openai.ChatCompletion.create(
        model='gpt-4o',
        max_tokens=1024,
        temperature=temperature,
        messages=[{'role': 'user', 'content': prompt}],
    )
    return resp.choices[0].message.content


def salva(campioni):
    with open(CAMPIONI_FILE, 'w', encoding='utf-8') as f:
        json.dump(campioni, f, ensure_ascii=False, indent=2)


def carica_esistenti():
    if os.path.exists(CAMPIONI_FILE):
        with open(CAMPIONI_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []


def genera_campioni():
    """Genera campioni a temperature diverse."""
    campioni = carica_esistenti()
    ids_fatti = {c['id'] for c in campioni if c.get('testo')}

    generatori = {
        'claude': genera_claude,
        'chatgpt': genera_chatgpt,
    }

    totale = N_CAMPIONI_PER_COND * len(generatori) * len(TEMPERATURE)
    print(f'Target: {totale} campioni ({N_CAMPIONI_PER_COND} x {len(generatori)} modelli x {len(TEMPERATURE)} temperature)')

    for temp in TEMPERATURE:
        for i in range(N_CAMPIONI_PER_COND):
            prompt = PROMPTS[i % len(PROMPTS)]

            for nome, fn in generatori.items():
                cid = f'{nome}_t{temp}_{i:03d}'
                if cid in ids_fatti:
                    continue

                try:
                    print(f'  {cid}...', end=' ', flush=True)
                    t0 = time.time()
                    testo = fn(prompt, temp)
                    dt = time.time() - t0
                    campioni.append({
                        'id': cid,
                        'modello': nome,
                        'temperatura': temp,
                        'prompt': prompt,
                        'testo': testo,
                        'lunghezza': len(testo),
                        'tempo_s': round(dt, 2),
                    })
                    print(f'{len(testo)} char, {dt:.1f}s')
                except Exception as e:
                    print(f'ERRORE: {e}')
                    campioni.append({
                        'id': cid,
                        'modello': nome,
                        'temperatura': temp,
                        'prompt': prompt,
                        'testo': None,
                        'errore': str(e),
                    })

                salva(campioni)

            time.sleep(0.5)

    ok = [c for c in campioni if c.get('testo')]
    print(f'\nCampioni OK: {len(ok)}/{len(campioni)}')
    return campioni


def estrai_features_testo(testo):
    """Riusa la logica di 02_estrai_features.py."""
    # importa dallo script 02
    import importlib.util
    spec = importlib.util.spec_from_file_location('feat', os.path.join(os.path.dirname(__file__), '02_estrai_features.py'))
    feat_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(feat_mod)
    return feat_mod.estrai_features(testo)


def analizza(campioni):
    """Estrai feature e classifica."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    # importa feature extractor
    import importlib.util
    spec = importlib.util.spec_from_file_location('feat', os.path.join(os.path.dirname(__file__), '02_estrai_features.py'))
    feat_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(feat_mod)

    FEATURE_COLS = [
        'media_len_frasi', 'std_len_frasi', 'ttr', 'hapax_ratio',
        'media_len_parole', 'ratio_parole_lunghe', 'entropia_char',
        'freq_punct_1k', 'virgole_1k', 'punti_1k', 'due_punti_1k',
        'punto_virgola_1k', 'trattini_1k', 'ratio_bg_ripetuti',
        'ratio_conj_start', 'n_paragrafi',
    ]

    validi = [c for c in campioni if c.get('testo')]

    # estrai feature
    righe = []
    for c in validi:
        f = feat_mod.estrai_features(c['testo'])
        if f is None:
            continue
        r = {'id': c['id'], 'modello': c['modello'], 'temperatura': c['temperatura']}
        r.update(f)
        righe.append(r)

    print(f'Campioni con feature valide: {len(righe)}')

    # salva CSV
    csv_path = os.path.join(OUTPUT_DIR, 'features_temperatura.csv')
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(righe[0].keys()))
        w.writeheader()
        w.writerows(righe)

    # prepara X, y
    X = np.array([[float(r[col]) for col in FEATURE_COLS] for r in righe])
    y_modello = np.array([r['modello'] for r in righe])
    y_temp = np.array([r['temperatura'] for r in righe])

    # standardizza
    mu = X.mean(axis=0)
    sigma = X.std(axis=0)
    sigma[sigma == 0] = 1
    X_scaled = (X - mu) / sigma

    # PCA
    cov = np.cov(X_scaled.T)
    eigenvalues, eigenvectors = np.linalg.eigh(cov)
    idx = np.argsort(eigenvalues)[::-1]
    eigenvectors = eigenvectors[:, idx]
    eigenvalues = eigenvalues[idx]
    var_expl = eigenvalues[:2] / eigenvalues.sum()
    X_pca = X_scaled @ eigenvectors[:, :2]

    # --- Grafico PCA colorato per modello, marker per temperatura ---
    COLORI = {'claude': '#7c4dff', 'chatgpt': '#00ff88'}
    MARKERS = {0.3: 'o', 0.7: 's', 1.0: '^'}
    NOMI = {'claude': 'Claude', 'chatgpt': 'ChatGPT'}

    fig, ax = plt.subplots(figsize=(10, 8))
    fig.patch.set_facecolor('#0d1117')
    ax.set_facecolor('#0d1117')

    for modello in sorted(set(y_modello)):
        for temp in TEMPERATURE:
            mask = (y_modello == modello) & (y_temp == temp)
            if not mask.any():
                continue
            ax.scatter(
                X_pca[mask, 0], X_pca[mask, 1],
                c=COLORI[modello], marker=MARKERS[temp],
                alpha=0.7, s=60, edgecolors='white', linewidths=0.3,
                label=f'{NOMI[modello]} t={temp}',
            )

    ax.set_title(f'PCA — Modello x Temperatura\n(var. spiegata: {var_expl[0]+var_expl[1]:.1%})',
                 color='white', fontsize=14, fontweight='bold', pad=15)
    ax.set_xlabel(f'PC1 ({var_expl[0]:.1%})', color='#8b949e')
    ax.set_ylabel(f'PC2 ({var_expl[1]:.1%})', color='#8b949e')
    ax.tick_params(colors='#8b949e')
    for spine in ax.spines.values():
        spine.set_color('#30363d')
    ax.legend(facecolor='#161b22', edgecolor='#30363d', labelcolor='white',
              fontsize=9, loc='best', ncol=2)
    ax.grid(True, alpha=0.1)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '07_temperatura_pca.png'), dpi=150, facecolor='#0d1117')
    plt.close()
    print(f'Salvato: output/07_temperatura_pca.png')

    # --- Accuracy per temperatura ---
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.model_selection import cross_val_score, StratifiedKFold

    risultati = {}

    # accuracy globale (tutte le temperature insieme)
    clf = RandomForestClassifier(n_estimators=200, random_state=42, max_depth=10)
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    scores = cross_val_score(clf, X_scaled, y_modello, cv=cv, scoring='accuracy')
    risultati['globale'] = {'accuracy': round(scores.mean(), 4), 'std': round(scores.std(), 4)}
    print(f'Accuracy globale (tutte le temp): {scores.mean():.1%} +/- {scores.std():.1%}')

    # accuracy per singola temperatura
    for temp in TEMPERATURE:
        mask = y_temp == temp
        X_t = X_scaled[mask]
        y_t = y_modello[mask]
        if len(set(y_t)) < 2 or len(y_t) < 10:
            continue
        n_splits = min(5, min(np.bincount(np.unique(y_t, return_inverse=True)[1])))
        if n_splits < 2:
            continue
        cv_t = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)
        scores_t = cross_val_score(clf, X_t, y_t, cv=cv_t, scoring='accuracy')
        risultati[f't={temp}'] = {'accuracy': round(scores_t.mean(), 4), 'std': round(scores_t.std(), 4)}
        print(f'  t={temp}: {scores_t.mean():.1%} +/- {scores_t.std():.1%}')

    # bar chart accuracy per temperatura
    labels = list(risultati.keys())
    accs = [risultati[l]['accuracy'] for l in labels]
    stds = [risultati[l]['std'] for l in labels]

    fig, ax = plt.subplots(figsize=(8, 5))
    fig.patch.set_facecolor('#0d1117')
    ax.set_facecolor('#0d1117')

    bars = ax.bar(range(len(labels)), accs, yerr=stds, capsize=5,
                  color=['#7c4dff'] + ['#00ff88'] * (len(labels) - 1),
                  edgecolor='#0d1117', error_kw={'color': '#8b949e'})
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, color='#c8c8d8', fontsize=11)
    ax.set_ylabel('Accuracy', color='#8b949e')
    ax.set_title('Accuracy per Temperatura', color='white', fontsize=14, fontweight='bold', pad=15)
    ax.set_ylim(0, 1.05)
    ax.tick_params(colors='#8b949e')
    for spine in ax.spines.values():
        spine.set_color('#30363d')
    ax.grid(True, axis='y', alpha=0.1)

    for i, (acc, std) in enumerate(zip(accs, stds)):
        ax.text(i, acc + std + 0.02, f'{acc:.1%}', ha='center', color='white',
                fontweight='bold', fontsize=11)

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '08_temperatura_accuracy.png'), dpi=150, facecolor='#0d1117')
    plt.close()
    print(f'Salvato: output/08_temperatura_accuracy.png')

    # salva risultati
    with open(os.path.join(OUTPUT_DIR, 'risultati_temperatura.json'), 'w') as f:
        json.dump(risultati, f, indent=2)

    return risultati


def main():
    print('=== Test Robustezza: Temperatura ===\n')
    campioni = genera_campioni()

    # rimuovi falliti
    campioni = [c for c in campioni if c.get('testo')]

    print(f'\n=== Analisi ===\n')
    analizza(campioni)
    print('\nFatto.')


if __name__ == '__main__':
    main()
