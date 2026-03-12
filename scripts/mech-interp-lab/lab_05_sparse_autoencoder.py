#!/usr/bin/env python3
"""
Lab 05 - Sparse Autoencoder: trovare feature interpretabili
Carica un SAE pre-trainato su GPT-2 small, passa diverse frasi,
e identifica le feature monosemantiche che si attivano.

Requisiti:
    pip install transformer-lens sae-lens torch plotly kaleido

CPU only. ~4 GB RAM (modello + SAE).
Il SAE viene scaricato automaticamente da HuggingFace (~200MB).
"""

import torch
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from transformer_lens import HookedTransformer

print('[*] Carico GPT-2 small...')
model = HookedTransformer.from_pretrained('gpt2-small', device='cpu', dtype=torch.float32)

# === 1. Caricare il SAE ===
print('[*] Carico SAE pre-trainato (residual stream, layer 8)...')
try:
    from sae_lens import SAE
    sae = SAE.from_pretrained(
        release='gpt2-small-res-jb',
        sae_id='blocks.8.hook_resid_pre',
        device='cpu',
    )
    print(f'    Features: {sae.cfg.d_sae}')
    print(f'    Input dim: {sae.cfg.d_in}')
    USE_SAE = True
except Exception as e:
    print(f'[!] SAE non disponibile: {e}')
    print('[!] Passo alla modalita\' manuale con SVD delle attivazioni')
    USE_SAE = False

# === 2. Frasi di test ===
test_prompts = [
    'When Alice and Bob went to the bar, Alice bought a beer for',
    'The private key is stored inside the Secure Enclave chip on the iPhone',
    'def exploit(target): payload = shellcode + nop_sled + return_address',
    'The neural network predicts the next token using self-attention heads',
    'After Pixel and Ghost hacked the server, Pixel sent the logs to',
    'Einstein discovered that E equals mc squared, proving mass energy equivalence',
    'The Mersenne Twister PRNG can be cracked after observing 624 outputs',
    'The steganography algorithm hides data in the least significant bits of pixels',
    'SELECT * FROM users WHERE password_hash = md5(input) ORDER BY created_at',
    'The deepfake detection model analyzes facial micro-expressions frame by frame',
]

# === 3. Analisi delle feature ===
if USE_SAE:
    print('\n[*] Analisi feature SAE su frasi di test...')

    all_features = {}  # feature_id -> lista di (prompt, token, activation)

    for prompt in test_prompts:
        tokens = model.to_tokens(prompt)
        _stoks = model.to_str_tokens(prompt)
        str_tokens_list = _stoks[0] if isinstance(_stoks[0], list) else _stoks
        _, cache = model.run_with_cache(tokens)

        # Attivazioni del residual stream al layer 8
        resid = cache['blocks.8.hook_resid_pre']  # [1, seq_len, d_model]

        # Passare attraverso il SAE
        feature_acts = sae.encode(resid)  # [1, seq_len, n_features]

        # Per ogni token, trovare le top features attive
        for pos in range(tokens.shape[1]):
            acts = feature_acts[0, pos]  # [n_features]
            nonzero = (acts > 0).sum().item()
            top5 = acts.topk(min(5, nonzero if nonzero > 0 else 1))

            for feat_idx, feat_val in zip(top5.indices.tolist(), top5.values.tolist()):
                if feat_val > 0:
                    if feat_idx not in all_features:
                        all_features[feat_idx] = []
                    all_features[feat_idx].append({
                        'prompt': prompt[:50],
                        'token': str_tokens_list[pos] if pos < len(str_tokens_list) else '?',
                        'activation': feat_val,
                        'position': pos,
                    })

    # === 4. Feature piu' frequenti ===
    print(f'\n[*] Feature trovate: {len(all_features)}')
    print(f'\n[*] Top 20 feature piu\' frequenti:')
    sorted_features = sorted(all_features.items(), key=lambda x: len(x[1]), reverse=True)

    for feat_id, activations in sorted_features[:20]:
        n = len(activations)
        avg_act = np.mean([a['activation'] for a in activations])
        tokens = list(set([a['token'].strip() for a in activations]))[:5]
        print(f'    Feature #{feat_id:5d}: attivazioni={n:3d}, media={avg_act:.3f}, tokens: {tokens}')

    # === 5. Feature specifiche per dominio ===
    print('\n[*] Cerco pattern nei cluster di feature...')

    # Raggruppare per prompt per capire le feature specifiche per dominio
    prompt_features = {}
    for prompt in test_prompts:
        tokens = model.to_tokens(prompt)
        _, cache = model.run_with_cache(tokens)
        resid = cache['blocks.8.hook_resid_pre']
        feature_acts = sae.encode(resid)

        # Feature con attivazione media piu' alta su questa frase
        mean_acts = feature_acts[0].mean(dim=0)  # media su tutte le posizioni
        top_feats = mean_acts.topk(10)
        prompt_features[prompt[:40]] = list(zip(
            top_feats.indices.tolist(),
            top_feats.values.tolist()
        ))

    for prompt, feats in prompt_features.items():
        print(f'\n    "{prompt}..."')
        for feat_id, val in feats[:5]:
            if val > 0:
                print(f'        Feature #{feat_id}: {val:.4f}')

    # === 6. Visualizzazione: heatmap feature x prompt ===
    # Top 30 feature piu' informative
    top_feat_ids = [f[0] for f in sorted_features[:30]]

    heatmap_data = np.zeros((len(test_prompts), len(top_feat_ids)))
    for i, prompt in enumerate(test_prompts):
        tokens = model.to_tokens(prompt)
        _, cache = model.run_with_cache(tokens)
        resid = cache['blocks.8.hook_resid_pre']
        feature_acts = sae.encode(resid)
        mean_acts = feature_acts[0].mean(dim=0)

        for j, feat_id in enumerate(top_feat_ids):
            heatmap_data[i, j] = mean_acts[feat_id].item()

    prompt_labels = [p[:35] + '...' for p in test_prompts]
    feat_labels = [f'#{fid}' for fid in top_feat_ids]

    fig = go.Figure(data=go.Heatmap(
        z=heatmap_data,
        x=feat_labels,
        y=prompt_labels,
        colorscale='Viridis',
        hovertemplate='Prompt: %{y}<br>Feature: %{x}<br>Attivazione: %{z:.4f}<extra></extra>',
    ))
    fig.update_layout(
        title='SAE Feature Activations: top 30 feature su 10 frasi di test',
        xaxis_title='Feature ID',
        yaxis_title='Prompt',
        width=1100,
        height=600,
        font=dict(family='JetBrains Mono, monospace', size=9),
    )
    fig.write_html('output_05_sae_features.html')
    fig.write_image('output_05_sae_features.png', scale=2)
    print('\n[+] Salvato: output_05_sae_features.html / .png')

else:
    # === Fallback: analisi con SVD ===
    print('\n[*] Fallback: SVD delle attivazioni al layer 8...')

    all_resids = []
    all_labels = []
    for prompt in test_prompts:
        tokens = model.to_tokens(prompt)
        _stoks = model.to_str_tokens(prompt)
        _stoks_list = _stoks[0] if isinstance(_stoks[0], list) else _stoks
        _, cache = model.run_with_cache(tokens)
        resid = cache['blocks.8.hook_resid_pre'][0]  # [seq_len, d_model]
        all_resids.append(resid)
        all_labels.extend([f'{prompt[:20]}|{s.strip()}' for s in _stoks_list])

    # Concatenare e SVD
    X = torch.cat(all_resids, dim=0)  # [total_tokens, d_model]
    U, S, Vh = torch.linalg.svd(X, full_matrices=False)

    print(f'    Shape: {X.shape}')
    print(f'    Top 10 valori singolari: {S[:10].tolist()}')
    print(f'    Varianza spiegata dai primi 10 componenti: {(S[:10]**2).sum() / (S**2).sum() * 100:.1f}%')

    # Plot 2D delle prime 2 componenti
    proj = (X @ Vh[:2].T).numpy()  # proiezione sui primi 2 componenti
    fig = go.Figure(data=go.Scatter(
        x=proj[:, 0], y=proj[:, 1],
        mode='markers+text',
        text=[l.split('|')[1] for l in all_labels],
        textposition='top center',
        textfont=dict(size=6),
        marker=dict(size=5, color=[hash(l.split('|')[0]) % 10 for l in all_labels], colorscale='viridis'),
        hovertext=all_labels,
    ))
    fig.update_layout(
        title='SVD delle attivazioni al layer 8 (primi 2 componenti)',
        width=1000, height=700,
        font=dict(family='JetBrains Mono, monospace'),
    )
    fig.write_html('output_05_svd_activations.html')
    fig.write_image('output_05_svd_activations.png', scale=2)
    print('[+] Salvato: output_05_svd_activations.html / .png')

print('\n[+] Lab 05 completato.')
