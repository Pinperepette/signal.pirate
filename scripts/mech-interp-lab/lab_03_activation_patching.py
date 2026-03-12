#!/usr/bin/env python3
# Prompts personalizzati per Signal Pirate blog
"""
Lab 03 - Activation Patching
Identifica quali attention heads sono causalmente responsabili
della predizione corretta nel task IOI.

Tecnica: corrompere l'input, poi patchare un'attivazione alla volta
dal run pulito e misurare quanto recupera il logit corretto.

Requisiti:
    pip install transformer-lens torch plotly kaleido numpy

CPU only. ~3 GB RAM. Circa 2-3 minuti.
"""

import torch
import plotly.graph_objects as go
import numpy as np
from transformer_lens import HookedTransformer

print('[*] Carico GPT-2 small...')
model = HookedTransformer.from_pretrained('gpt2-small', device='cpu', dtype=torch.float32)

# === 1. Setup: frase clean e corrupted ===
clean_prompt = 'When Alice and Bob went to the bar, Alice bought a beer for'
# Corrupted: sostituire l'indirect object (Bob) con un soggetto diverso
corrupted_prompt = 'When Alice and Charlie went to the bar, Alice bought a beer for'

clean_tokens = model.to_tokens(clean_prompt)
corrupted_tokens = model.to_tokens(corrupted_prompt)
_clean_stoks = model.to_str_tokens(clean_prompt)
clean_str = _clean_stoks[0] if isinstance(_clean_stoks[0], list) else _clean_stoks

print(f'[*] Clean:     {clean_prompt}')
print(f'[*] Corrupted: {corrupted_prompt}')

# === 2. Forward pass su entrambi ===
clean_logits, clean_cache = model.run_with_cache(clean_tokens)
corrupted_logits, corrupted_cache = model.run_with_cache(corrupted_tokens)

# Token target: "Bob" e "Charlie"
bob_token = model.to_single_token(' Bob')
charlie_token = model.to_single_token(' Charlie')

clean_logit_diff = (clean_logits[0, -1, bob_token] - clean_logits[0, -1, charlie_token]).item()
corrupted_logit_diff = (corrupted_logits[0, -1, bob_token] - corrupted_logits[0, -1, charlie_token]).item()

print(f'\n[*] Logit difference (Bob - Charlie):')
print(f'    Clean:     {clean_logit_diff:+.4f}  (il modello preferisce Bob)')
print(f'    Corrupted: {corrupted_logit_diff:+.4f}  (il modello preferisce Charlie)')
print(f'    Delta:     {clean_logit_diff - corrupted_logit_diff:.4f}')

# === 3. Activation Patching: head output ===
# Per ogni (layer, head), patchare l'output dell'head dal clean al corrupted
# e misurare quanto il logit diff si avvicina al clean
print(f'\n[*] Activation patching su {model.cfg.n_layers * model.cfg.n_heads} head...')

patching_results = torch.zeros(model.cfg.n_layers, model.cfg.n_heads)

for layer in range(model.cfg.n_layers):
    for head in range(model.cfg.n_heads):
        # Hook che sostituisce l'output di un singolo head
        def patch_hook(activation, hook, layer=layer, head=head):
            # activation shape: [batch, seq_len, n_heads, d_head]
            activation[:, :, head, :] = clean_cache[hook.name][:, :, head, :]
            return activation

        # Run corrupted con il patch
        hook_name = f'blocks.{layer}.attn.hook_z'
        patched_logits = model.run_with_hooks(
            corrupted_tokens,
            fwd_hooks=[(hook_name, patch_hook)],
        )

        patched_logit_diff = (patched_logits[0, -1, bob_token] - patched_logits[0, -1, charlie_token]).item()

        # Normalizzare: 0 = corrupted (nessun effetto), 1 = clean (recovery completo)
        if abs(clean_logit_diff - corrupted_logit_diff) > 1e-6:
            recovery = (patched_logit_diff - corrupted_logit_diff) / (clean_logit_diff - corrupted_logit_diff)
        else:
            recovery = 0.0

        patching_results[layer, head] = recovery

    print(f'    Layer {layer:2d} completato')

# === 4. Visualizzazione: heatmap del patching ===
fig = go.Figure(data=go.Heatmap(
    z=patching_results.numpy(),
    x=[f'H{h}' for h in range(model.cfg.n_heads)],
    y=[f'L{l}' for l in range(model.cfg.n_layers)],
    colorscale='RdBu',
    zmid=0,
    text=np.round(patching_results.numpy(), 2),
    texttemplate='%{text}',
    textfont={'size': 8},
    hovertemplate='Layer %{y}, Head %{x}<br>Recovery: %{z:.3f}<extra></extra>',
))

# Annotare i head conosciuti del circuito IOI
ioi_annotations = {
    (9, 9): 'NM', (9, 6): 'NM', (10, 0): 'NM',
    (10, 7): 'BNM', (10, 10): 'BNM', (11, 2): 'BNM',
    (7, 3): 'SI', (7, 9): 'SI', (8, 6): 'SI', (8, 10): 'SI',
    (0, 1): 'DT', (0, 10): 'DT',
    (2, 2): 'PT', (4, 11): 'PT',
}
for (layer, head), label in ioi_annotations.items():
    fig.add_annotation(
        x=f'H{head}', y=f'L{layer}',
        text=label, showarrow=False,
        font=dict(size=7, color='white'),
        bgcolor='rgba(0,0,0,0.6)',
        borderpad=1,
    )

fig.update_layout(
    title='Activation Patching: recovery del logit corretto per head<br>'
          '<sub>NM=Name Mover, BNM=Backup, SI=S-Inhibition, DT=Dup Token, PT=Prev Token</sub>',
    xaxis_title='Head',
    yaxis_title='Layer',
    yaxis=dict(autorange='reversed'),
    width=1000,
    height=650,
    font=dict(family='JetBrains Mono, monospace'),
)
fig.write_html('output_03_activation_patching.html')
fig.write_image('output_03_activation_patching.png', scale=2)
print('\n[+] Heatmap salvata: output_03_activation_patching.html / .png')

# === 5. Ranking dei risultati ===
print(f'\n[*] Top 10 head con maggior effetto causale (recovery):')
flat = patching_results.flatten()
top_pos = flat.topk(10)
for i in range(10):
    idx = top_pos.indices[i].item()
    layer = idx // model.cfg.n_heads
    head = idx % model.cfg.n_heads
    val = top_pos.values[i].item()
    label = ioi_annotations.get((layer, head), '')
    print(f'    L{layer}H{head}: {val:+.4f}  {label}')

print(f'\n[*] Top 10 head con effetto negativo (inibizione):')
top_neg = (-flat).topk(10)
for i in range(10):
    idx = top_neg.indices[i].item()
    layer = idx // model.cfg.n_heads
    head = idx % model.cfg.n_heads
    val = -top_neg.values[i].item()
    label = ioi_annotations.get((layer, head), '')
    print(f'    L{layer}H{head}: {val:+.4f}  {label}')

# === 6. Patching per posizione (solo Name Mover L9H9) ===
print(f'\n[*] Patching per posizione di L9H9:')
pos_results = torch.zeros(clean_tokens.shape[1])

for pos in range(clean_tokens.shape[1]):
    def pos_patch_hook(activation, hook, pos=pos):
        activation[:, pos, 9, :] = clean_cache[hook.name][:, pos, 9, :]
        return activation

    patched_logits = model.run_with_hooks(
        corrupted_tokens,
        fwd_hooks=[('blocks.9.attn.hook_z', pos_patch_hook)],
    )
    patched_diff = (patched_logits[0, -1, bob_token] - patched_logits[0, -1, charlie_token]).item()
    if abs(clean_logit_diff - corrupted_logit_diff) > 1e-6:
        pos_results[pos] = (patched_diff - corrupted_logit_diff) / (clean_logit_diff - corrupted_logit_diff)

labels = [s.strip() for s in clean_str]
fig2 = go.Figure(data=go.Bar(
    x=labels,
    y=pos_results.numpy(),
    marker_color=['#ff6b6b' if v > 0.05 else '#3a3a5a' for v in pos_results.numpy()],
    hovertemplate='Pos %{x}<br>Recovery: %{y:.3f}<extra></extra>',
))
fig2.update_layout(
    title='L9H9: recovery per posizione del token patchato',
    xaxis_title='Token',
    yaxis_title='Recovery',
    width=1000,
    height=400,
    font=dict(family='JetBrains Mono, monospace'),
    xaxis=dict(tickangle=45),
)
fig2.write_html('output_03_position_patching.html')
fig2.write_image('output_03_position_patching.png', scale=2)
print('[+] Salvato: output_03_position_patching.html / .png')

print('\n[+] Lab 03 completato.')
