#!/usr/bin/env python3
# Prompts personalizzati per Signal Pirate blog
"""
Lab 06 - Feature Steering: il nostro Golden Gate Claude
Amplificare una feature del SAE e osservare come cambia l'output del modello.
Poi sopprimerla e confrontare.

Misurare il KL divergence tra le distribuzioni con e senza steering.

Requisiti:
    pip install transformer-lens sae-lens torch plotly kaleido

CPU only. ~4 GB RAM.
"""

import torch
import torch.nn.functional as F
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from transformer_lens import HookedTransformer

print('[*] Carico GPT-2 small...')
model = HookedTransformer.from_pretrained('gpt2-small', device='cpu', dtype=torch.float32)

# === 1. Caricare il SAE ===
print('[*] Carico SAE...')
try:
    from sae_lens import SAE
    sae = SAE.from_pretrained(
        release='gpt2-small-res-jb',
        sae_id='blocks.8.hook_resid_pre',
        device='cpu',
    )
    USE_SAE = True
    print(f'    SAE caricato: {sae.cfg.d_sae} features')
except Exception as e:
    print(f'[!] SAE non disponibile: {e}')
    print('[!] Uso direzione casuale nello spazio residual come fallback')
    USE_SAE = False

# === 2. Trovare feature interessanti ===
if USE_SAE:
    print('\n[*] Cerco feature ad alta attivazione su prompt specifici...')

    # Prompt per trovare feature tematiche
    discovery_prompts = {
        'exploit': 'def exploit(target): payload = shellcode + nop_sled + return_address',
        'crypto': 'The private key is stored inside the Secure Enclave chip on the iPhone',
        'network': 'After Pixel and Ghost hacked the server, Pixel sent the logs to',
        'stego': 'The steganography algorithm hides data in the least significant bits of pixels',
        'deepfake': 'The deepfake detection model analyzes facial micro-expressions frame by frame',
    }

    feature_candidates = {}  # theme -> (feature_id, activation, decoder_vector)

    for theme, prompt in discovery_prompts.items():
        tokens = model.to_tokens(prompt)
        _, cache = model.run_with_cache(tokens)
        resid = cache['blocks.8.hook_resid_pre']
        feature_acts = sae.encode(resid)

        # Feature con attivazione media piu' alta
        mean_acts = feature_acts[0].mean(dim=0)
        top_feat = mean_acts.argmax().item()
        top_val = mean_acts[top_feat].item()

        # Il decoder weight di questa feature e' la sua direzione nello spazio residual
        steering_dir = sae.W_dec[top_feat].detach().clone()
        steering_dir = steering_dir / steering_dir.norm()  # normalizzare

        feature_candidates[theme] = {
            'feature_id': top_feat,
            'activation': top_val,
            'direction': steering_dir,
        }
        print(f'    {theme:12s}: feature #{top_feat}, attivazione={top_val:.4f}')

    steering_features = feature_candidates
else:
    # Fallback: usare direzioni casuali
    print('\n[*] Creo direzioni di steering casuali...')
    d_model = model.cfg.d_model
    steering_features = {}
    for i, theme in enumerate(['direzione_A', 'direzione_B', 'direzione_C']):
        torch.manual_seed(42 + i)
        direction = torch.randn(d_model)
        direction = direction / direction.norm()
        steering_features[theme] = {
            'feature_id': -1,
            'activation': 0,
            'direction': direction,
        }

# === 3. Feature Steering ===
print('\n[*] Feature steering: generazione con amplificazione...')

test_prompt = 'When Alice and Bob went to the bar, Alice bought a beer for'
tokens = model.to_tokens(test_prompt)

# Generare senza steering (baseline)
model.reset_hooks()
with torch.no_grad():
    baseline_logits = model(tokens)
    baseline_probs = F.softmax(baseline_logits[0, -1], dim=-1)

# Generare testo baseline
baseline_tokens = model.generate(tokens, max_new_tokens=40, temperature=0.7)
baseline_text = model.to_string(baseline_tokens[0])
print(f'\n    Baseline: {baseline_text}')

# Per ogni feature, fare steering con diversi moltiplicatori
multipliers = [-10.0, -5.0, 0.0, 5.0, 10.0, 20.0, 40.0]
all_results = {}

for theme, feat_data in steering_features.items():
    print(f'\n{"="*60}')
    print(f'[*] Steering: {theme} (feature #{feat_data["feature_id"]})')
    direction = feat_data['direction']

    theme_results = []

    for mult in multipliers:
        # Hook di steering
        def steering_hook(activation, hook, direction=direction, mult=mult):
            activation[:, :, :] += mult * direction
            return activation

        model.reset_hooks()
        if mult != 0:
            model.add_hook('blocks.8.hook_resid_post', steering_hook)

        with torch.no_grad():
            steered_logits = model(tokens)
            steered_probs = F.softmax(steered_logits[0, -1], dim=-1)

        # KL divergence: D_KL(baseline || steered)
        kl_div = F.kl_div(
            steered_probs.log(),
            baseline_probs,
            reduction='sum',
            log_target=False,
        ).item()

        # Top-5 token predetti
        top5 = steered_probs.topk(5)
        top5_str = ', '.join([
            f'"{model.to_single_str_token(t.item())}"({v.item():.3f})'
            for t, v in zip(top5.indices, top5.values)
        ])

        # Generare testo
        steered_tokens = model.generate(tokens, max_new_tokens=40, temperature=0.7)
        steered_text = model.to_string(steered_tokens[0])

        theme_results.append({
            'multiplier': mult,
            'kl_divergence': kl_div,
            'top5': top5_str,
            'text': steered_text,
        })

        print(f'    mult={mult:+6.1f}  KL={kl_div:8.4f}  top5: {top5_str}')
        if mult in [-10, 10, 40]:
            print(f'              testo: {steered_text[:100]}...')

    all_results[theme] = theme_results
    model.reset_hooks()

# === 4. Visualizzazione: KL divergence per moltiplicatore ===
fig = go.Figure()
for theme, results in all_results.items():
    mults = [r['multiplier'] for r in results]
    kls = [r['kl_divergence'] for r in results]
    fig.add_trace(go.Scatter(
        x=mults, y=kls,
        mode='lines+markers',
        name=theme,
        hovertemplate='mult=%{x}<br>KL=%{y:.4f}<extra></extra>',
    ))

fig.update_layout(
    title='KL Divergence vs Steering Multiplier per feature',
    xaxis_title='Moltiplicatore di steering',
    yaxis_title='KL Divergence (bits)',
    yaxis_type='log',
    width=900,
    height=500,
    font=dict(family='JetBrains Mono, monospace'),
    legend=dict(x=0.02, y=0.98),
)
fig.write_html('output_06_kl_divergence.html')
fig.write_image('output_06_kl_divergence.png', scale=2)
print('\n[+] Salvato: output_06_kl_divergence.html / .png')

# === 5. Before/After comparison ===
print('\n[*] Before/After per ogni feature (mult=20):')
print('=' * 80)
for theme, results in all_results.items():
    baseline_r = [r for r in results if r['multiplier'] == 0][0]
    steered_r = [r for r in results if r['multiplier'] == 20.0]
    if steered_r:
        steered_r = steered_r[0]
        print(f'\n  [{theme}] Feature #{steering_features[theme]["feature_id"]}')
        print(f'  BEFORE: {baseline_r["text"][:120]}')
        print(f'  AFTER:  {steered_r["text"][:120]}')
        print(f'  KL divergence: {steered_r["kl_divergence"]:.4f}')

# === 6. Logit lens: come cambia la predizione layer per layer ===
print('\n[*] Logit lens con steering (mult=20, prima feature)...')
first_theme = list(steering_features.keys())[0]
direction = steering_features[first_theme]['direction']

def steering_hook_20(activation, hook):
    activation[:, :, :] += 20.0 * direction
    return activation

# Senza steering
model.reset_hooks()
_, clean_cache = model.run_with_cache(tokens)

# Con steering
model.add_hook('blocks.8.hook_resid_post', steering_hook_20)
_, steered_cache = model.run_with_cache(tokens)
model.reset_hooks()

# Per ogni layer, proiettare il residual stream sui logit
print(f'\n    Layer-by-layer prediction (ultima posizione):')
W_U = model.W_U  # [d_model, vocab]
ln_final = model.ln_final

for layer in range(model.cfg.n_layers):
    clean_resid = clean_cache[f'blocks.{layer}.hook_resid_post'][0, -1]
    steered_resid = steered_cache[f'blocks.{layer}.hook_resid_post'][0, -1]

    # Applicare layer norm e unembedding
    clean_logits = ln_final(clean_resid) @ W_U
    steered_logits = ln_final(steered_resid) @ W_U

    clean_top = model.to_single_str_token(clean_logits.argmax().item())
    steered_top = model.to_single_str_token(steered_logits.argmax().item())

    marker = ' <-- STEERING APPLIED' if layer == 8 else ''
    changed = ' ***' if clean_top != steered_top else ''
    print(f'    L{layer:2d}: clean="{clean_top:>12s}"  steered="{steered_top:>12s}"{changed}{marker}')

print('\n[+] Lab 06 completato.')
print('\n=== TUTTI I LAB COMPLETATI ===')
print('Output files:')
print('  output_01_logit_attribution.html/.png')
print('  output_02_attention_*.html/.png')
print('  output_03_activation_patching.html/.png')
print('  output_03_position_patching.html/.png')
print('  output_04_path_patching.html/.png')
print('  output_05_sae_features.html/.png')
print('  output_06_kl_divergence.html/.png')
