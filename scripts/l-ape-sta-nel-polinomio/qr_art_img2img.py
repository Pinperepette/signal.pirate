"""
QR Code Art con immagine di partenza (img2img + ControlNet QR Monster).

Differenza dal text2img: invece di generare il pirata da prompt, parte da una
immagine fornita (--init) e la "modifica" con ControlNet che impone la struttura QR.

Risultato: l'immagine fornita resta riconoscibile come layout/colore generale,
sopra ci viene inciso il pattern QR.

Strength controlla quanto SD modifica l'init:
  0.50 = preserva molto l'immagine, QR debole
  0.75 = bilanciamento, soggetto riconoscibile + QR visibile
  0.90 = init e' solo "ispirazione", il modello reinventa molto
"""

import os
import time
import argparse

N_THREADS = os.cpu_count() or 1
os.environ.setdefault("OMP_NUM_THREADS", str(N_THREADS))
os.environ.setdefault("MKL_NUM_THREADS", str(N_THREADS))

import torch
torch.set_num_threads(N_THREADS)

import qrcode
from qrcode.constants import ERROR_CORRECT_H
from PIL import Image
from pyzbar.pyzbar import decode

from diffusers import (
    StableDiffusionControlNetImg2ImgPipeline,
    ControlNetModel,
    DPMSolverMultistepScheduler,
)


def build_qr(url: str, size: int) -> Image.Image:
    qr = qrcode.QRCode(version=None, error_correction=ERROR_CORRECT_H, box_size=10, border=2)
    qr.add_data(url); qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    return img.resize((size, size), Image.LANCZOS)


def prepare_init(init_path: str, size: int) -> Image.Image:
    """Carica e ridimensiona l'init image a size x size."""
    img = Image.open(init_path).convert("RGB")
    # Crop centrale al quadrato se non lo e'
    w, h = img.size
    if w != h:
        s = min(w, h)
        img = img.crop(((w-s)//2, (h-s)//2, (w+s)//2, (h+s)//2))
    return img.resize((size, size), Image.LANCZOS)


def build_pipeline():
    dtype = torch.float32
    print("[load] ControlNet QR Code Monster...")
    cn = ControlNetModel.from_pretrained(
        "monster-labs/control_v1p_sd15_qrcode_monster",
        torch_dtype=dtype,
    )
    print("[load] Stable Diffusion 1.5 img2img...")
    pipe = StableDiffusionControlNetImg2ImgPipeline.from_pretrained(
        "runwayml/stable-diffusion-v1-5",
        controlnet=cn,
        torch_dtype=dtype,
        safety_checker=None,
        requires_safety_checker=False,
    )
    pipe.scheduler = DPMSolverMultistepScheduler.from_config(pipe.scheduler.config)
    pipe = pipe.to("cpu")
    pipe.enable_attention_slicing()
    pipe.enable_vae_slicing()
    return pipe


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="https://pinperepette.github.io/signal.pirate/")
    ap.add_argument("--init", required=True, help="immagine di partenza (pirata, etc.)")
    ap.add_argument("--prompt", default=(
        "cartoon pirate with eye patch and skull symbol, exaggerated features, "
        "wide eyes, comic illustration, vibrant colors, intricate detail"
    ))
    ap.add_argument("--negative", default=(
        "blurry, low quality, text, watermark, ugly, deformed, photograph, realistic"
    ))
    ap.add_argument("--n", type=int, default=3)
    ap.add_argument("--size", type=int, default=768)
    ap.add_argument("--cn-scale", type=float, default=1.30)
    ap.add_argument("--strength", type=float, default=0.85,
                    help="0.5 conserva molto init, 0.95 lo modifica quasi tutto")
    ap.add_argument("--steps", type=int, default=30)
    ap.add_argument("--guidance", type=float, default=7.5)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--ctrl-end", type=float, default=0.95)
    ap.add_argument("--outdir", default=".")
    args = ap.parse_args()

    print(f"[cpu] {N_THREADS} threads")
    print(f"[init] {args.init}")
    print(f"[mode] img2img, strength={args.strength}, steps={args.steps}, cn_scale={args.cn_scale}")

    os.makedirs(args.outdir, exist_ok=True)

    init = prepare_init(args.init, args.size)
    init.save(os.path.join(args.outdir, "init-resized.png"))

    qr = build_qr(args.url, args.size)
    qr.save(os.path.join(args.outdir, "qr-control.png"))

    pipe = build_pipeline()

    t_total = time.time()
    for i in range(args.n):
        seed = args.seed + i * 1000
        gen = torch.Generator("cpu").manual_seed(seed)
        t0 = time.time()
        out = pipe(
            prompt=args.prompt,
            negative_prompt=args.negative,
            image=init,            # init image (per img2img)
            control_image=qr,      # control (per ControlNet)
            num_inference_steps=args.steps,
            guidance_scale=args.guidance,
            controlnet_conditioning_scale=args.cn_scale,
            control_guidance_start=0.0,
            control_guidance_end=args.ctrl_end,
            strength=args.strength,
            generator=gen,
            width=args.size,
            height=args.size,
        ).images[0]
        dt = time.time() - t0
        # verify
        r = decode(out)
        ok = bool(r) and r[0].data.decode() == args.url
        tag = "ok" if ok else "FAIL"
        fn = f"qrart-img2img-{i:02d}-{tag}-seed{seed}.png"
        out.save(os.path.join(args.outdir, fn))
        print(f"  [{i+1}/{args.n}] {dt:5.1f}s seed={seed} pyzbar={tag} -> {fn}")

    print(f"\n[done] {time.time()-t_total:.1f}s totali")


if __name__ == "__main__":
    main()
