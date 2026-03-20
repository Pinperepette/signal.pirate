#!/usr/bin/env python3
"""
02_ispeziona_onnx.py — Apre il modello ONNX e mappa l'architettura.
Conta nodi per tipo, dimensioni dei tensori, parametri totali.
pip install onnx onnxruntime huggingface_hub numpy
"""

import os
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
import numpy as np
import onnx
from collections import Counter
from huggingface_hub import hf_hub_download

MODELLI = [
    ("nano-int8", "KittenML/kitten-tts-nano-0.8-int8"),
    ("nano-fp32", "KittenML/kitten-tts-nano-0.8-fp32"),
    ("micro", "KittenML/kitten-tts-micro-0.8"),
    ("mini", "KittenML/kitten-tts-mini-0.8"),
]

OUT_DIR = "output/onnx"
os.makedirs(OUT_DIR, exist_ok=True)


def analizza_modello(nome, repo_id):
    print(f"\n{'=' * 70}")
    print(f"MODELLO: {nome} ({repo_id})")
    print(f"{'=' * 70}")

    # Scarica config e modello
    import json
    config_path = hf_hub_download(repo_id=repo_id, filename="config.json")
    with open(config_path) as f:
        config = json.load(f)
    print(f"\n[config.json] {json.dumps(config, indent=2)}")

    model_path = hf_hub_download(repo_id=repo_id, filename=config["model_file"])
    voices_path = hf_hub_download(repo_id=repo_id, filename=config["voices"])

    # Dimensione file
    model_size = os.path.getsize(model_path)
    voices_size = os.path.getsize(voices_path)
    print(f"\n[dimensioni]")
    print(f"  Modello: {model_size / 1024 / 1024:.1f} MB")
    print(f"  Voci:    {voices_size / 1024 / 1024:.1f} MB")
    print(f"  Totale:  {(model_size + voices_size) / 1024 / 1024:.1f} MB")

    # Carica ONNX
    model = onnx.load(model_path)
    graph = model.graph

    # Conta nodi per tipo
    op_counts = Counter(node.op_type for node in graph.node)
    print(f"\n[nodi] Totale: {len(graph.node)}")
    print(f"{'Operazione':<25} {'Conteggio':<10}")
    print("-" * 35)
    for op, count in op_counts.most_common():
        print(f"  {op:<25} {count}")

    # Input/Output
    print(f"\n[input]")
    for inp in graph.input:
        shape = [d.dim_value if d.dim_value else d.dim_param for d in inp.type.tensor_type.shape.dim]
        print(f"  {inp.name}: {shape}")

    print(f"\n[output]")
    for out in graph.output:
        shape = [d.dim_value if d.dim_value else d.dim_param for d in out.type.tensor_type.shape.dim]
        print(f"  {out.name}: {shape}")

    # Conta parametri dagli initializer
    total_params = 0
    total_bytes = 0
    layer_sizes = {}

    for init in graph.initializer:
        arr = np.frombuffer(init.raw_data, dtype=np.float32) if init.data_type == 1 else None
        dims = list(init.dims)
        n_params = 1
        for d in dims:
            n_params *= d
        total_params += n_params

        # Raggruppa per prefisso
        prefix = init.name.split('.')[0] if '.' in init.name else init.name
        layer_sizes[prefix] = layer_sizes.get(prefix, 0) + n_params

    print(f"\n[parametri] Totale: {total_params:,}")
    print(f"\n[parametri per blocco]")
    print(f"{'Blocco':<40} {'Parametri':<15} {'%':<8}")
    print("-" * 63)
    for prefix, count in sorted(layer_sizes.items(), key=lambda x: -x[1])[:20]:
        pct = count / total_params * 100
        print(f"  {prefix:<40} {count:>12,} {pct:>6.1f}%")

    # Analizza voci
    voices = np.load(voices_path)
    print(f"\n[voci]")
    for key in voices.files:
        v = voices[key]
        print(f"  {key}: shape={v.shape}, dtype={v.dtype}, min={v.min():.4f}, max={v.max():.4f}")

    return {
        "nome": nome,
        "nodi": len(graph.node),
        "parametri": total_params,
        "size_mb": model_size / 1024 / 1024,
    }


# Analizza tutti
risultati = []
for nome, repo_id in MODELLI:
    try:
        r = analizza_modello(nome, repo_id)
        risultati.append(r)
    except Exception as e:
        print(f"[!] Errore con {nome}: {e}")

print(f"\n\n{'=' * 70}")
print("RIEPILOGO")
print(f"{'=' * 70}")
print(f"{'Modello':<15} {'Nodi':<10} {'Parametri':<18} {'Size (MB)':<12}")
print("-" * 55)
for r in risultati:
    print(f"  {r['nome']:<15} {r['nodi']:<10} {r['parametri']:>15,} {r['size_mb']:>8.1f}")
