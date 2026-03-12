#!/usr/bin/env python3
# Prompts personalizzati per Signal Pirate blog
"""
Lab 02 - Attention Pattern Visualization
Visualizza i pattern di attenzione dei Name Mover Heads e dei Duplicate Token Heads
nel circuito IOI di GPT-2 small.

Requisiti:
    pip install transformer-lens torch plotly kaleido

CPU only. ~2 GB RAM.
"""

import torch
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from transformer_lens import HookedTransformer

print('[*] Carico GPT-2 small...')
model = HookedTransformer.from_pretrained('gpt2-small', device='cpu', dtype=torch.float32)

# === 1. Due frasi IOI per confronto ===
prompts = {
    'clean': 'When Alice and Bob went to the bar, Alice bought a beer for',
    'hacker': 'After Pixel and Ghost hacked the server, Pixel sent the logs to',
}

for name, prompt in prompts.items():
    print(f'\n{"="*60}')
    print(f'[*] Analisi: {name}')
    print(f'    Prompt: {prompt}')

    tokens = model.to_tokens(prompt)
    str_tokens = model.to_str_tokens(prompt)
    logits, cache = model.run_with_cache(tokens)
    seq_len = tokens.shape[1]

    # Top predizione
    probs = torch.softmax(logits[0, -1], dim=-1)
    top_token = probs.argmax().item()
    top_str = model.to_single_str_token(top_token)
    print(f'    Predizione: "{top_str}" ({probs[top_token].item()*100:.1f}%)')

    # === 2. Head chiave del circuito IOI ===
    ioi_heads = {
        'Duplicate Token': [(0, 1), (0, 10)],
        'Previous Token': [(2, 2), (4, 11)],
        'S-Inhibition': [(7, 3), (7, 9), (8, 6), (8, 10)],
        'Name Mover': [(9, 6), (9, 9), (10, 0)],
        'Backup Name Mover': [(10, 7), (10, 10), (11, 2)],
    }

    # === 3. Estrarre e visualizzare i pattern di attenzione ===
    # Focus sui Name Mover Heads e Duplicate Token Heads
    focus_heads = [
        ('Name Mover L9H9', 9, 9),
        ('Name Mover L9H6', 9, 6),
        ('Dup Token L0H1', 0, 1),
        ('S-Inhibition L7H3', 7, 3),
    ]

    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=[h[0] for h in focus_heads],
        horizontal_spacing=0.12,
        vertical_spacing=0.15,
    )

    # to_str_tokens puo' restituire List[str] o List[List[str]] a seconda della versione
    _stoks = model.to_str_tokens(prompt)
    if isinstance(_stoks[0], list):
        labels = [s.strip() for s in _stoks[0]]
    else:
        labels = [s.strip() for s in _stoks]

    for idx, (title, layer, head) in enumerate(focus_heads):
        row = idx // 2 + 1
        col = idx % 2 + 1

        # Pattern di attenzione: [seq_len, seq_len]
        attn_pattern = cache[f'blocks.{layer}.attn.hook_pattern'][0, head].numpy()

        fig.add_trace(go.Heatmap(
            z=attn_pattern,
            x=labels,
            y=labels,
            colorscale='Viridis',
            showscale=(idx == 0),
            hovertemplate='Da: %{y}<br>A: %{x}<br>Attenzione: %{z:.3f}<extra></extra>',
        ), row=row, col=col)

        fig.update_xaxes(tickangle=45, tickfont=dict(size=7), row=row, col=col)
        fig.update_yaxes(tickfont=dict(size=7), autorange='reversed', row=row, col=col)

    fig.update_layout(
        title=f'Attention Patterns - Circuito IOI ({name})',
        width=1100,
        height=900,
        font=dict(family='JetBrains Mono, monospace', size=10),
    )
    fig.write_html(f'output_02_attention_{name}.html')
    fig.write_image(f'output_02_attention_{name}.png', scale=2)
    print(f'[+] Salvato: output_02_attention_{name}.html / .png')

    # === 4. Analisi quantitativa: dove attendono i Name Mover Heads ===
    print(f'\n[*] Analisi Name Mover Heads:')
    for layer, head in ioi_heads['Name Mover']:
        attn = cache[f'blocks.{layer}.attn.hook_pattern'][0, head, -1]  # ultima posizione
        print(f'    L{layer}H{head} (ultima pos attende a):')
        top_attn = attn.topk(5)
        for i in range(5):
            pos = top_attn.indices[i].item()
            val = top_attn.values[i].item()
            tok = labels[pos] if pos < len(labels) else '?'
            marker = ' <-- IO' if tok.strip().lower() in ['bob', 'ghost'] else ''
            print(f'        pos {pos} "{tok}": {val:.4f}{marker}')

    # === 5. Attenzione aggregata per tipo di head ===
    print(f'\n[*] Attenzione media dell\'ultima posizione per tipo:')
    for head_type, heads in ioi_heads.items():
        attn_sum = torch.zeros(seq_len)
        for layer, head in heads:
            attn_sum += cache[f'blocks.{layer}.attn.hook_pattern'][0, head, -1]
        attn_sum /= len(heads)
        top3 = attn_sum.topk(3)
        targets = ', '.join([
            f'"{labels[t.item()] if t.item() < len(labels) else "?"}"({attn_sum[t.item()]:.3f})'
            for t in top3.indices
        ])
        print(f'    {head_type}: {targets}')

print('\n[+] Lab 02 completato.')
