"""
Esperimento "rompiamolo davvero": comportamento empirico del QR Version 6 H
sotto stress reali (logo che cresce, posizione che varia, rumore sparso).

Tre setup:
  A. Logo (ape stilizzata) crescente al CENTRO. 20 trials per size, posizione
     dell'ape randomizzata di +-15 px per misurare stabilita'.
  B. Logo a size FISSA (45% lineare = ~20% area), posizione che varia
     dal centro verso i quattro angoli e verso i timing pattern.
  C. Rumore sparso (riuso esperimento precedente sull'occlusione bianca random).

Output: JSON con risultati + plot + 4 sample image stampabili.
"""

import os
import json
import argparse
import numpy as np
import qrcode
from qrcode.constants import ERROR_CORRECT_H
from PIL import Image, ImageDraw, ImageOps
import cv2
from pyzbar.pyzbar import decode
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


URL = "https://pinperepette.github.io/signal.pirate/"
N_TRIALS = 20
QR_PX = 1000
BORDER_PX = 80


def make_qr():
    qr = qrcode.QRCode(version=None, error_correction=ERROR_CORRECT_H, box_size=10, border=2)
    qr.add_data(URL); qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    return img.resize((QR_PX, QR_PX), Image.LANCZOS), qr.modules_count


def with_quiet_zone(img):
    return ImageOps.expand(img, border=BORDER_PX, fill=(255, 255, 255))


def draw_bee(side):
    """Disegna un'ape stilizzata su un'immagine RGBA quadrata side x side."""
    img = Image.new("RGBA", (side, side), (255, 255, 255, 0))
    d = ImageDraw.Draw(img)
    cx, cy = side // 2, side // 2
    pad = int(side * 0.04)
    d.ellipse([pad, pad, side - pad, side - pad], fill=(255, 255, 255, 255),
              outline=(0, 0, 0, 255), width=max(2, side // 60))
    bw = int(side * 0.62); bh = int(side * 0.44)
    d.ellipse([cx - bw // 2, cy - bh // 2, cx + bw // 2, cy + bh // 2],
              fill=(255, 200, 0, 255), outline=(0, 0, 0, 255), width=max(2, side // 80))
    sw = bw // 7
    for k in (-1, 1):
        x0 = cx + k * sw - sw // 2; x1 = x0 + sw
        d.rectangle([x0, cy - bh // 2 + 4, x1, cy + bh // 2 - 4], fill=(0, 0, 0, 255))
    ww = int(bw * 0.55); wh = int(bh * 0.70); woff = -int(bh * 0.40)
    for k in (-1, 1):
        wx = cx + k * int(bw * 0.20)
        d.ellipse([wx - ww // 2, cy + woff - wh // 2, wx + ww // 2, cy + woff + wh // 2],
                  fill=(245, 245, 250, 255), outline=(0, 0, 0, 255), width=max(2, side // 90))
    return img


def overlay_bee(qr_img, frac_linear, pos_offset_xy=(0, 0)):
    W, H = qr_img.size
    side = int(min(W, H) * frac_linear)
    bee = draw_bee(side)
    cx = (W - side) // 2 + pos_offset_xy[0]
    cy = (H - side) // 2 + pos_offset_xy[1]
    out = qr_img.copy().convert("RGBA")
    out.alpha_composite(bee, (cx, cy))
    return out.convert("RGB")


def try_decode(img):
    img_l = np.array(img.convert("L"))
    pyz = decode(img)
    py_ok = bool(pyz) and pyz[0].data.decode("utf-8", errors="replace") == URL
    det = cv2.QRCodeDetector()
    d, _, _ = det.detectAndDecode(img_l)
    if d != URL:
        _, otsu = cv2.threshold(img_l, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        d, _, _ = det.detectAndDecode(otsu)
    cv_ok = (d == URL)
    return py_ok, cv_ok


def expA_size_sweep(qr_b, fracs, save_samples_at=None, samples_dir=None):
    """Per ogni size lineare, 20 prove con bee position randomizzata."""
    rng = np.random.default_rng(42)
    results = []
    for frac in fracs:
        ok_py, ok_cv = 0, 0
        for trial in range(N_TRIALS):
            dx = int(rng.uniform(-15, 15))
            dy = int(rng.uniform(-15, 15))
            img = overlay_bee(qr_b, frac, (dx, dy))
            py, cv = try_decode(img)
            if py: ok_py += 1
            if cv: ok_cv += 1
        p_py = ok_py / N_TRIALS
        p_cv = ok_cv / N_TRIALS
        results.append({"frac": float(frac), "area": float(frac**2),
                        "p_pyzbar": p_py, "p_cv2": p_cv})
        print(f"  size={int(frac*100)}% area={frac*frac*100:.1f}%  pyzbar={p_py:.2f}  cv2={p_cv:.2f}")
        # Salva campione visivo
        if save_samples_at and int(frac * 100) in save_samples_at and samples_dir:
            sample = overlay_bee(qr_b, frac, (0, 0))
            sample.save(os.path.join(samples_dir, f"sample-bee-{int(frac*100):02d}.png"))
    return results


def expB_position(qr_b, frac_linear, offsets):
    """Posizione fissa a frac_linear, varia offset (lista di tuple)."""
    results = []
    for label, (dx, dy) in offsets.items():
        ok_py, ok_cv = 0, 0
        rng = np.random.default_rng(hash(label) & 0xFFFFFFFF)
        for trial in range(N_TRIALS):
            jx = int(rng.uniform(-10, 10))
            jy = int(rng.uniform(-10, 10))
            img = overlay_bee(qr_b, frac_linear, (dx + jx, dy + jy))
            py, cv = try_decode(img)
            if py: ok_py += 1
            if cv: ok_cv += 1
        p_py = ok_py / N_TRIALS
        p_cv = ok_cv / N_TRIALS
        results.append({"position": label, "offset_xy": [dx, dy],
                        "p_pyzbar": p_py, "p_cv2": p_cv})
        print(f"  pos={label:<20} pyzbar={p_py:.2f}  cv2={p_cv:.2f}")
    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", default="/Users/pinperepette/Github/blog/output/break-exp")
    args = ap.parse_args()
    os.makedirs(args.outdir, exist_ok=True)
    samples_dir = os.path.join(args.outdir, "samples")
    os.makedirs(samples_dir, exist_ok=True)

    qr_clean, n_mod = make_qr()
    qr_b = with_quiet_zone(qr_clean)
    print(f"QR Version 6 H, {n_mod}x{n_mod} moduli")

    print("\n[A] sweep size con jitter posizione (20 trials/size):")
    fracs = [0.30, 0.35, 0.40, 0.42, 0.44, 0.45, 0.46, 0.48, 0.50,
             0.52, 0.55, 0.58, 0.60, 0.65, 0.70]
    expA = expA_size_sweep(qr_b, fracs,
                           save_samples_at={35, 45, 50, 55, 60},
                           samples_dir=samples_dir)

    print("\n[B] posizione a size fissa 44% lineare (19% area, zona instabile):")
    # Offset: il QR e' 1000+160=1160 px. Offsets in px.
    offsets = {
        "centro":                  (   0,    0),
        "offset 100 px alto-sx":   (-100, -100),
        "offset 100 px alto-dx":   ( 100, -100),
        "offset 200 px sopra":     (   0, -200),
        "offset 200 px sinistra":  (-200,    0),
        "offset 100 px sotto":     (   0,  100),
    }
    expB = expB_position(qr_b, frac_linear=0.44, offsets=offsets)

    # Save JSON
    out = {
        "qr": {"version": 6, "level": "H", "modules": n_mod},
        "expA_size_sweep": expA,
        "expB_position_at_50pct": expB,
    }
    with open(os.path.join(args.outdir, "break_data.json"), "w") as f:
        json.dump(out, f, indent=2)

    # Plot A: probability vs size
    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=140)
    xs = [r["frac"] * 100 for r in expA]
    py = [r["p_pyzbar"] for r in expA]
    cv = [r["p_cv2"] for r in expA]
    ax.plot(xs, py, color="#7c4dff", marker="o", linewidth=2, label="pyzbar")
    ax.plot(xs, cv, color="#00ff88", marker="s", linewidth=2, linestyle="--", label="cv2.QRCodeDetector")
    # Linee di riferimento Singleton
    ax.axvline(np.sqrt(0.325) * 100, color="#ff6b6b", linestyle=":", alpha=0.6,
               label=f"Singleton teorico ({np.sqrt(0.325)*100:.1f}% lineare = 32.5% area)")
    ax.set_xlabel("dimensione lineare ape (% del lato QR)")
    ax.set_ylabel(f"prob. decodifica ({N_TRIALS} prove/punto)")
    ax.set_title("Cliff empirico per QR Version 6 H, jitter posizione +-15 px")
    ax.set_ylim(-0.05, 1.05)
    ax.legend(fontsize=9, loc="lower left")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(args.outdir, "break_size.png"))
    plt.close(fig)

    # Plot B: position bar chart
    fig, ax = plt.subplots(figsize=(9, 4), dpi=140)
    labels = [r["position"] for r in expB]
    py = [r["p_pyzbar"] for r in expB]
    cv = [r["p_cv2"] for r in expB]
    x = np.arange(len(labels))
    w = 0.4
    ax.bar(x - w/2, py, w, color="#7c4dff", label="pyzbar")
    ax.bar(x + w/2, cv, w, color="#00ff88", label="cv2")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=20, ha="right", fontsize=9)
    ax.set_ylabel(f"prob. decodifica ({N_TRIALS} prove)")
    ax.set_title("Stessa size, posizioni diverse: dipendenza dalla cornice")
    ax.set_ylim(0, 1.05)
    ax.legend(fontsize=9)
    ax.grid(alpha=0.3, axis="y")
    fig.tight_layout()
    fig.savefig(os.path.join(args.outdir, "break_position.png"))
    plt.close(fig)

    print("\n=== SOMMARIO ===")
    print("Soglie pyzbar nel sweep A:")
    last_full = max((r["frac"] for r in expA if r["p_pyzbar"] >= 0.95), default=0)
    first_partial = next((r["frac"] for r in expA if r["p_pyzbar"] < 0.95), 1)
    half = next((r["frac"] for r in expA if r["p_pyzbar"] < 0.5), 1)
    first_dead = next((r["frac"] for r in expA if r["p_pyzbar"] <= 0.05), 1)
    print(f"  ultimo punto OK robusto (p>=0.95):  {last_full*100:.0f}% lineare ({last_full**2*100:.1f}% area)")
    print(f"  inizio zona instabile (p<0.95):      {first_partial*100:.0f}% lineare ({first_partial**2*100:.1f}% area)")
    print(f"  cliff a meta' altezza (p<0.5):        {half*100:.0f}% lineare ({half**2*100:.1f}% area)")
    print(f"  morto (p<=0.05):                      {first_dead*100:.0f}% lineare ({first_dead**2*100:.1f}% area)")


if __name__ == "__main__":
    main()
