"""
QR Code Art via Stable Diffusion 1.5 + ControlNet QR Code Monster.

Tutto su CPU. Genera N candidati, verifica decodifica con pyzbar,
salva tutti, marca quelli che decodificano nel nome file.

Due modalita':
  - default: 30 step, qualita' piena, ~2-4 min/immagine su CPU multi-core
  - --fast:  8 step con LCM-LoRA, ~30-50 sec/immagine, qualita' leggermente inferiore

Dipendenze:
  pip install diffusers transformers accelerate torch \
              qrcode pillow pyzbar safetensors

Modelli scaricati al primo run (cache HF, ~6 GB totali):
  - runwayml/stable-diffusion-v1-5
  - monster-labs/control_v1p_sd15_qrcode_monster
  - latent-consistency/lcm-lora-sdv1-5  (solo --fast)
"""

import os
import sys
import time
import argparse

# usa tutti i core disponibili
N_THREADS = os.cpu_count() or 1
os.environ.setdefault("OMP_NUM_THREADS", str(N_THREADS))
os.environ.setdefault("MKL_NUM_THREADS", str(N_THREADS))

import torch
torch.set_num_threads(N_THREADS)
torch.set_num_interop_threads(max(1, N_THREADS // 2))

import qrcode
from qrcode.constants import ERROR_CORRECT_H
from PIL import Image
from pyzbar.pyzbar import decode

from diffusers import (
    StableDiffusionControlNetPipeline,
    ControlNetModel,
    DPMSolverMultistepScheduler,
    LCMScheduler,
)


def build_qr(url: str, size: int = 512) -> Image.Image:
    """Genera un QR livello H, lo rasterizza a size x size."""
    qr = qrcode.QRCode(
        version=None,
        error_correction=ERROR_CORRECT_H,
        box_size=10,
        border=2,
    )
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    img = img.resize((size, size), Image.LANCZOS)
    return img


def build_pipeline(fast: bool):
    """Stable Diffusion 1.5 + QR Monster ControlNet su CPU."""
    dtype = torch.float32  # CPU vuole FP32, FP16 e' piu' lento su x86

    print("[load] ControlNet QR Code Monster (~1.4 GB)...")
    controlnet = ControlNetModel.from_pretrained(
        "monster-labs/control_v1p_sd15_qrcode_monster",
        torch_dtype=dtype,
    )

    print("[load] Stable Diffusion 1.5 (~4 GB)...")
    pipe = StableDiffusionControlNetPipeline.from_pretrained(
        "runwayml/stable-diffusion-v1-5",
        controlnet=controlnet,
        torch_dtype=dtype,
        safety_checker=None,
        requires_safety_checker=False,
    )

    if fast:
        print("[load] LCM-LoRA (~140 MB)...")
        pipe.load_lora_weights("latent-consistency/lcm-lora-sdv1-5")
        pipe.fuse_lora()
        pipe.scheduler = LCMScheduler.from_config(pipe.scheduler.config)
    else:
        pipe.scheduler = DPMSolverMultistepScheduler.from_config(pipe.scheduler.config)

    pipe = pipe.to("cpu")
    pipe.enable_attention_slicing()
    pipe.enable_vae_slicing()
    return pipe


def generate_one(pipe, qr_img, prompt, neg_prompt, seed, fast, cn_scale,
                 ctrl_start=0.0, ctrl_end=0.95):
    """Una generazione. Ritorna PIL Image."""
    if fast:
        steps = 8
        guidance = 1.5  # LCM ignora CFG forte, valori bassi vanno bene
    else:
        steps = 30
        guidance = 7.5

    gen = torch.Generator("cpu").manual_seed(seed)
    out = pipe(
        prompt=prompt,
        negative_prompt=neg_prompt,
        image=qr_img,
        num_inference_steps=steps,
        guidance_scale=guidance,
        controlnet_conditioning_scale=cn_scale,
        control_guidance_start=ctrl_start,
        control_guidance_end=ctrl_end,
        generator=gen,
        width=qr_img.width,
        height=qr_img.height,
    ).images[0]
    return out


def verify(img, target_url):
    res = decode(img)
    if not res:
        return False, None
    payload = res[0].data.decode("utf-8", errors="replace")
    return payload == target_url, payload


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="https://pinperepette.github.io/signal.pirate/")
    ap.add_argument("--prompt", default=(
        "a fierce pirate captain wearing a red bandana, parrot on his shoulder, "
        "baroque oil painting, dramatic chiaroscuro lighting, hyperdetailed, "
        "masterpiece, intricate textures"
    ))
    ap.add_argument("--negative", default=(
        "blurry, low quality, text, watermark, ugly, deformed, "
        "extra fingers, low contrast"
    ))
    ap.add_argument("--n", type=int, default=6, help="numero candidati")
    ap.add_argument("--size", type=int, default=512)
    ap.add_argument("--cn-scale", type=float, default=1.30,
                    help="forza ControlNet (1.0-1.6). Alto = QR piu' leggibile.")
    ap.add_argument("--ctrl-end", type=float, default=0.95,
                    help="frazione di denoising durante cui ControlNet agisce (0.0-1.0)")
    ap.add_argument("--ctrl-start", type=float, default=0.0,
                    help="frazione di denoising da cui ControlNet inizia ad agire")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--fast", action="store_true",
                    help="LCM-LoRA 8 step invece di DPM 30 step")
    ap.add_argument("--outdir", default=".")
    args = ap.parse_args()

    print(f"[cpu] {N_THREADS} threads, {torch.get_num_threads()} torch threads")
    print(f"[mode] {'FAST (LCM 8 step)' if args.fast else 'FULL (DPM 30 step)'}")

    os.makedirs(args.outdir, exist_ok=True)

    qr_img = build_qr(args.url, args.size)
    qr_path = os.path.join(args.outdir, "qr-control.png")
    qr_img.save(qr_path)
    print(f"[qr] control image salvata: {qr_path}")

    pipe = build_pipeline(args.fast)

    print(f"[run] genero {args.n} candidati...")
    results = []
    t0_total = time.time()
    for i in range(args.n):
        seed = args.seed + i * 1000
        t0 = time.time()
        out = generate_one(
            pipe, qr_img,
            prompt=args.prompt,
            neg_prompt=args.negative,
            seed=seed,
            fast=args.fast,
            cn_scale=args.cn_scale,
            ctrl_start=args.ctrl_start,
            ctrl_end=args.ctrl_end,
        )
        dt = time.time() - t0
        ok, payload = verify(out, args.url)
        tag = "ok" if ok else "FAIL"
        fn = f"qr-art-{i:02d}-{tag}-seed{seed}.png"
        path = os.path.join(args.outdir, fn)
        out.save(path)
        results.append((i, seed, ok, dt, path))
        print(f"  [{i+1}/{args.n}] {dt:5.1f}s  seed={seed}  decode={tag}  -> {fn}")

    dt_total = time.time() - t0_total
    n_ok = sum(1 for r in results if r[2])
    print(f"\n[done] {n_ok}/{args.n} decodificano in {dt_total:.1f}s totali")
    if n_ok == 0:
        print("[hint] Aumenta --cn-scale (prova 1.40-1.55) e rilancia.")
    else:
        print("[hint] Aprire i file *-ok-* e scegliere visivamente il migliore.")


if __name__ == "__main__":
    main()
