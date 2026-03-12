#!/usr/bin/env python3

"""
Lab 01 - Anatomia del Forward Pass
Carica GPT-2 small, tokenizza una frase, estrae le attivazioni di ogni layer
e calcola il Direct Logit Attribution per ogni attention head.

Requisiti:
    pip install transformer-lens torch plotly kaleido

Tutto su CPU. ~2 GB di RAM. Nessuna GPU, nessuna API key.
"""

import torch
import plotly.graph_objects as go
import numpy as np
from transformer_lens import HookedTransformer

# === 1. Caricare il modello ===
print('[*] Carico GPT-2 small (124M parametri)...')
model = HookedTransformer.from_pretrained('gpt2-small', device='cpu', dtype=torch.float32)
print(f'    Layers: {model.cfg.n_layers}')
print(f'    Heads per layer: {model.cfg.n_heads}')
print(f'    d_model: {model.cfg.d_model}')
print(f'    d_head: {model.cfg.d_head}')
print(f'    Vocabolario: {model.cfg.d_vocab}')

# === 2. Tokenizzare la frase IOI ===
# Alice e Bob: quelli della crittografia. Stavolta vanno al bar.
# GPT-2 e' trainato su inglese, il circuito IOI funziona meglio cosi'.
prompt = 'When Alice and Bob went to the bar, Alice bought a beer for'
tokens = model.to_tokens(prompt)
_stoks = model.to_str_tokens(prompt)
str_tokens = _stoks[0] if isinstance(_stoks[0], list) else _stoks
print(f'\n[*] Prompt: {prompt}')
print(f'    Tokens ({len(str_tokens)}): {str_tokens}')

# === 3. Forward pass con cache completa ===
print('\n[*] Forward pass con cache di tutte le attivazioni...')
logits, cache = model.run_with_cache(tokens)

# Dimensioni della cache
cache_keys = list(cache.keys())
print(f'    Attivazioni cached: {len(cache_keys)}')
print(f'    Logits shape: {logits.shape}')  # [batch, seq_len, vocab]

# === 4. Predizione top-k ===
last_logits = logits[0, -1, :]  # logits dell'ultima posizione
probs = torch.softmax(last_logits, dim=-1)
top_k = 10
top_probs, top_indices = probs.topk(top_k)

print(f'\n[*] Top {top_k} predizioni per il prossimo token:')
for i in range(top_k):
    token_str = model.to_single_str_token(top_indices[i].item())
    print(f'    {i+1}. "{token_str}" -> {top_probs[i].item():.4f} ({top_probs[i].item()*100:.1f}%)')

# === 5. Direct Logit Attribution ===
# Quale head contribuisce di piu' al logit del token target?
target_token = top_indices[0].item()  # il token piu' probabile
target_str = model.to_single_str_token(target_token)
print(f'\n[*] Direct Logit Attribution per "{target_str}" (token {target_token})')

# Il logit finale e' il prodotto del residual stream con la colonna di W_U
# Possiamo scomporlo nella somma dei contributi di ogni head e MLP
W_U = model.W_U[:, target_token]  # [d_model]

# Contributo di ogni attention head
# hook_z e' il pre-W_O: [batch, pos, n_heads, d_head]
# Per ottenere il contributo al residual stream: z @ W_O
head_contributions = torch.zeros(model.cfg.n_layers, model.cfg.n_heads)
for layer in range(model.cfg.n_layers):
    z = cache[f'blocks.{layer}.attn.hook_z'][0, -1, :, :]  # [n_heads, d_head]
    W_O = model.blocks[layer].attn.W_O  # [n_heads, d_head, d_model]
    for head in range(model.cfg.n_heads):
        head_out = z[head] @ W_O[head]  # [d_model]
        head_contributions[layer, head] = (head_out @ W_U).item()

# Contributo di ogni MLP
mlp_contributions = torch.zeros(model.cfg.n_layers)
for layer in range(model.cfg.n_layers):
    mlp_out = cache[f'blocks.{layer}.hook_mlp_out'][0, -1, :]
    mlp_contributions[layer] = (mlp_out @ W_U).item()

# === 6. Visualizzazione: Heatmap dei contributi ===
fig = go.Figure(data=go.Heatmap(
    z=head_contributions.numpy(),
    x=[f'H{h}' for h in range(model.cfg.n_heads)],
    y=[f'L{l}' for l in range(model.cfg.n_layers)],
    colorscale='RdBu',
    zmid=0,
    text=np.round(head_contributions.numpy(), 2),
    texttemplate='%{text}',
    textfont={'size': 8},
    hovertemplate='Layer %{y}, Head %{x}<br>Contributo: %{z:.3f}<extra></extra>',
))
fig.update_layout(
    title=f'Direct Logit Attribution: contributo di ogni head al logit di "{target_str}"',
    xaxis_title='Head',
    yaxis_title='Layer',
    yaxis=dict(autorange='reversed'),
    width=900,
    height=600,
    font=dict(family='JetBrains Mono, monospace'),
)
fig.write_html('output_01_logit_attribution.html')
fig.write_image('output_01_logit_attribution.png', scale=2)
print('\n[+] Heatmap salvata: output_01_logit_attribution.html / .png')

# === 7. Ranking dei contributi ===
print(f'\n[*] Top 10 head per contributo POSITIVO a "{target_str}":')
flat = head_contributions.flatten()
top_pos = flat.topk(10)
for i in range(10):
    idx = top_pos.indices[i].item()
    layer = idx // model.cfg.n_heads
    head = idx % model.cfg.n_heads
    val = top_pos.values[i].item()
    print(f'    L{layer}H{head}: {val:+.4f}')

print(f'\n[*] Top 10 head per contributo NEGATIVO (inibiscono "{target_str}"):')
top_neg = (-flat).topk(10)
for i in range(10):
    idx = top_neg.indices[i].item()
    layer = idx // model.cfg.n_heads
    head = idx % model.cfg.n_heads
    val = -top_neg.values[i].item()
    print(f'    L{layer}H{head}: {val:+.4f}')

# === 8. Contributi MLP vs Attention ===
total_attn = head_contributions.sum().item()
total_mlp = mlp_contributions.sum().item()
embed_contribution = (cache['hook_embed'][0, -1] @ W_U).item()
pos_contribution = (cache['hook_pos_embed'][0, -1] @ W_U).item()

print(f'\n[*] Scomposizione del logit di "{target_str}":')
print(f'    Embedding:         {embed_contribution:+.4f}')
print(f'    Pos embedding:     {pos_contribution:+.4f}')
print(f'    Attention (totale):{total_attn:+.4f}')
print(f'    MLP (totale):      {total_mlp:+.4f}')
print(f'    Layer Norm finale: (residuo)')
print(f'    Logit finale:      {last_logits[target_token].item():.4f}')

print('\n[+] Lab 01 completato.')
