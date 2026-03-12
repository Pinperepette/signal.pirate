#!/usr/bin/env python3
"""
Lab 04 - Path Patching
Non basta sapere QUALI head contano. Serve sapere COME comunicano.
Path patching identifica le connessioni causali tra head specifici.

Tecnica: patchare lungo un singolo edge del grafo computazionale
(head A -> head B) invece che sull'intero output di un head.

Requisiti:
    pip install transformer-lens torch plotly kaleido numpy

CPU only. ~4 GB RAM. Circa 5-10 minuti.
"""

import torch
import plotly.graph_objects as go
import numpy as np
from transformer_lens import HookedTransformer

print('[*] Carico GPT-2 small...')
model = HookedTransformer.from_pretrained('gpt2-small', device='cpu', dtype=torch.float32)

# === 1. Setup IOI ===
clean_prompt = 'When Alice and Bob went to the bar, Alice bought a beer for'
corrupted_prompt = 'When Alice and Charlie went to the bar, Alice bought a beer for'

clean_tokens = model.to_tokens(clean_prompt)
corrupted_tokens = model.to_tokens(corrupted_prompt)

clean_logits, clean_cache = model.run_with_cache(clean_tokens)
corrupted_logits, corrupted_cache = model.run_with_cache(corrupted_tokens)

bob_token = model.to_single_token(' Bob')
charlie_token = model.to_single_token(' Charlie')

clean_diff = (clean_logits[0, -1, bob_token] - clean_logits[0, -1, charlie_token]).item()
corrupted_diff = (corrupted_logits[0, -1, bob_token] - corrupted_logits[0, -1, charlie_token]).item()
total_effect = clean_diff - corrupted_diff

print(f'[*] Clean logit diff:     {clean_diff:+.4f}')
print(f'[*] Corrupted logit diff: {corrupted_diff:+.4f}')
print(f'[*] Total effect:         {total_effect:.4f}')

# === 2. Head chiave nel circuito IOI ===
# Testeremo le connessioni tra questi gruppi
source_heads = {
    'DT': [(0, 1), (0, 10)],           # Duplicate Token
    'PT': [(2, 2), (4, 11)],           # Previous Token
}
target_heads = {
    'SI': [(7, 3), (7, 9), (8, 6), (8, 10)],   # S-Inhibition
    'NM': [(9, 6), (9, 9), (10, 0)],            # Name Mover
}

# === 3. Path Patching: source -> target ===
# Per ogni coppia (source, target):
# 1. Run corrupted come base
# 2. Patchare l'output del source head dal clean
# 3. Ma SOLO il contributo che passa attraverso le query/key del target head
# Approccio semplificato: patchare il residual stream *prima* del target layer
# solo con il contributo del source head

print('\n[*] Path patching tra source e target heads...')

results = {}

for src_type, src_heads in source_heads.items():
    for tgt_type, tgt_heads in target_heads.items():
        for src_layer, src_head in src_heads:
            for tgt_layer, tgt_head in tgt_heads:
                if src_layer >= tgt_layer:
                    continue  # il source deve precedere il target

                # Calcolare il contributo del source head usando hook_z e W_O
                clean_z = clean_cache[f'blocks.{src_layer}.attn.hook_z'][0, :, src_head, :]  # [seq_len, d_head]
                corrupted_z = corrupted_cache[f'blocks.{src_layer}.attn.hook_z'][0, :, src_head, :]  # [seq_len, d_head]

                # Proiettare nel residual stream tramite W_O
                W_O = model.blocks[src_layer].attn.W_O[src_head]  # [d_head, d_model]
                clean_head_out = clean_z @ W_O  # [seq_len, d_model]
                corrupted_head_out = corrupted_z @ W_O  # [seq_len, d_model]
                residual_diff = clean_head_out - corrupted_head_out  # [seq_len, d_model]

                # Hook: aggiungere questo contributo al residual stream
                # prima del target head
                def path_hook(activation, hook, diff=residual_diff):
                    activation[0] += diff
                    return activation

                hook_point = f'blocks.{tgt_layer}.hook_resid_pre'

                patched_logits = model.run_with_hooks(
                    corrupted_tokens,
                    fwd_hooks=[(hook_point, path_hook)],
                )

                patched_diff = (patched_logits[0, -1, bob_token] - patched_logits[0, -1, charlie_token]).item()
                recovery = (patched_diff - corrupted_diff) / total_effect if abs(total_effect) > 1e-6 else 0

                key = f'{src_type} L{src_layer}H{src_head} -> {tgt_type} L{tgt_layer}H{tgt_head}'
                results[key] = recovery

# === 4. Risultati ===
print(f'\n[*] Path patching results ({len(results)} edges):')
sorted_results = sorted(results.items(), key=lambda x: abs(x[1]), reverse=True)
for path, recovery in sorted_results:
    bar = '#' * int(abs(recovery) * 50)
    print(f'    {path:45s} {recovery:+.4f} |{bar}')

# === 5. Visualizzazione: grafo del circuito ===
# Creare una heatmap source x target
all_sources = []
all_targets = []
for src_type, src_heads in source_heads.items():
    for sl, sh in src_heads:
        all_sources.append(f'{src_type} L{sl}H{sh}')
for tgt_type, tgt_heads in target_heads.items():
    for tl, th in tgt_heads:
        all_targets.append(f'{tgt_type} L{tl}H{th}')

matrix = np.zeros((len(all_sources), len(all_targets)))
for i, src_label in enumerate(all_sources):
    for j, tgt_label in enumerate(all_targets):
        for path, val in results.items():
            src_part = path.split(' -> ')[0]
            tgt_part = path.split(' -> ')[1]
            if src_part == src_label and tgt_part == tgt_label:
                matrix[i, j] = val

fig = go.Figure(data=go.Heatmap(
    z=matrix,
    x=all_targets,
    y=all_sources,
    colorscale='RdBu',
    zmid=0,
    text=np.round(matrix, 3),
    texttemplate='%{text}',
    textfont={'size': 10},
    hovertemplate='%{y} -> %{x}<br>Recovery: %{z:.4f}<extra></extra>',
))
fig.update_layout(
    title='Path Patching: forza delle connessioni nel circuito IOI<br>'
          '<sub>DT=Duplicate Token, PT=Previous Token, SI=S-Inhibition, NM=Name Mover</sub>',
    xaxis_title='Target Head',
    yaxis_title='Source Head',
    width=900,
    height=500,
    font=dict(family='JetBrains Mono, monospace'),
)
fig.write_html('output_04_path_patching.html')
fig.write_image('output_04_path_patching.png', scale=2)
print('\n[+] Salvato: output_04_path_patching.html / .png')

# === 6. Knockout: azzerare un head e misurare il degrado ===
print('\n[*] Head knockout (azzerare e misurare degrado):')

knockout_results = {}
for head_type, heads in {**source_heads, **target_heads}.items():
    for layer, head in heads:
        def knockout_hook(activation, hook, head=head):
            activation[:, :, head, :] = 0
            return activation

        ko_logits = model.run_with_hooks(
            clean_tokens,
            fwd_hooks=[(f'blocks.{layer}.attn.hook_z', knockout_hook)],
        )
        ko_diff = (ko_logits[0, -1, bob_token] - ko_logits[0, -1, charlie_token]).item()
        degradation = clean_diff - ko_diff
        knockout_results[f'{head_type} L{layer}H{head}'] = degradation
        print(f'    KO {head_type} L{layer}H{head}: logit diff {ko_diff:+.4f} (degrado: {degradation:+.4f})')

print('\n[+] Lab 04 completato.')
