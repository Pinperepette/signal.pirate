"""
Esperimento empirico cliff Singleton + ruolo dei moduli strutturali.

Tre esperimenti separati per ogni livello L/M/Q/H:
  A. Occlusione centrale (cerchio bianco crescente al centro)
  B. Rumore sparso su MODULI DATI (rispetta la struttura, prova vera di Singleton)
  C. Rumore sparso su MODULI STRUTTURALI (mostra fragilita' della cornice)

Per A 1 prova per soglia (deterministica). Per B e C, 50 prove per soglia.
Decode con pyzbar e cv2.QRCodeDetector.
"""

import os
import json
import argparse
import numpy as np
import qrcode
from qrcode.constants import (
    ERROR_CORRECT_L, ERROR_CORRECT_M, ERROR_CORRECT_Q, ERROR_CORRECT_H,
)
from PIL import Image, ImageDraw, ImageOps
import cv2
from pyzbar.pyzbar import decode
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


URL = "https://pinperepette.github.io/signal.pirate/"
LEVELS = [
    ("L", ERROR_CORRECT_L, 0.07),
    ("M", ERROR_CORRECT_M, 0.15),
    ("Q", ERROR_CORRECT_Q, 0.25),
    ("H", ERROR_CORRECT_H, 0.30),
]
N_TRIALS = 50
QR_SIZE = 1000
BORDER_PX = 60


def structural_positions(n_mod, version):
    """Maschera moduli strutturali nella matrice n_mod x n_mod (senza border)."""
    s = np.zeros((n_mod, n_mod), dtype=bool)
    # Finder + separator
    for sy, sx in [(0, 0), (0, n_mod - 7), (n_mod - 7, 0)]:
        y0 = max(0, sy - 1); y1 = min(n_mod, sy + 8)
        x0 = max(0, sx - 1); x1 = min(n_mod, sx + 8)
        s[y0:y1, x0:x1] = True
    # Timing
    s[6, 6:n_mod - 6] = True
    s[6:n_mod - 6, 6] = True
    # Alignment (per QR version 1-6 c'e' un alignment centrale per V >= 2)
    # Position depends on version
    if version >= 2:
        align = {2: 18, 3: 22, 4: 26, 5: 30, 6: 34, 7: 38}
        pos = align.get(version, 34)
        s[pos - 2:pos + 3, pos - 2:pos + 3] = True
    # Dark module e format info
    s[4 * version + 9, 8] = True
    # Format info around top-left
    s[8, 0:9] = True
    s[0:9, 8] = True
    # Around top-right
    s[8, n_mod - 8:n_mod] = True
    # Around bottom-left
    s[n_mod - 7:n_mod, 8] = True
    return s


def make_qr(level_const):
    qr = qrcode.QRCode(
        version=None,
        error_correction=level_const,
        box_size=10,
        border=2,
    )
    qr.add_data(URL)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    return img.resize((QR_SIZE, QR_SIZE), Image.LANCZOS), qr.modules_count, qr.version


def with_quiet_zone(img):
    return ImageOps.expand(img, border=BORDER_PX, fill=(255, 255, 255))


def occlude_center(img, frac_area):
    out = img.copy()
    if frac_area <= 0:
        return out
    d = ImageDraw.Draw(out)
    w, h = img.size
    radius = int(np.sqrt(frac_area * w * h / np.pi))
    cx, cy = w // 2, h // 2
    d.ellipse([cx - radius, cy - radius, cx + radius, cy + radius],
              fill=(255, 255, 255))
    return out


def sparse_noise_subset(img, mask_flippable, frac_modules, n_mod, seed):
    """Flippa una frazione di moduli dentro mask_flippable."""
    rng = np.random.default_rng(seed)
    arr = np.array(img).copy()
    px = QR_SIZE / n_mod
    n_subset = int(mask_flippable.sum())
    n_flips = int(frac_modules * n_subset)
    if n_flips == 0 or n_subset == 0:
        return Image.fromarray(arr)
    # indici lineari dei moduli flippabili
    flat_pos = np.flatnonzero(mask_flippable.flatten())
    chosen = rng.choice(flat_pos, size=min(n_flips, n_subset), replace=False)
    # offset border 2 modules nella mat (no: noi lavoriamo solo sulla matrice senza quiet zone)
    # ma l'immagine ha quiet zone => devo sommare BORDER_PX
    for p in chosen:
        i, j = p // n_mod, p % n_mod
        y0 = BORDER_PX + int(i * px); y1 = BORDER_PX + int((i + 1) * px)
        x0 = BORDER_PX + int(j * px); x1 = BORDER_PX + int((j + 1) * px)
        patch = arr[y0:y1, x0:x1]
        is_dark = patch.mean() < 127
        arr[y0:y1, x0:x1] = 0 if not is_dark else 255
    return Image.fromarray(arr)


def try_decode(img):
    img_l = np.array(img.convert("L"))
    pyz = decode(img)
    pyzbar_ok = bool(pyz) and pyz[0].data.decode("utf-8", errors="replace") == URL
    det = cv2.QRCodeDetector()
    d, _, _ = det.detectAndDecode(img_l)
    if d != URL:
        _, otsu = cv2.threshold(img_l, 0, 255,
                                cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        d, _, _ = det.detectAndDecode(otsu)
    cv2_ok = (d == URL)
    return pyzbar_ok, cv2_ok


def experiment_central(level_const):
    qr, n_mod, _ = make_qr(level_const)
    qr_b = with_quiet_zone(qr)
    results = []
    fracs = np.linspace(0.0, 0.60, 31)
    for frac in fracs:
        out = occlude_center(qr_b, frac)
        py, cv = try_decode(out)
        results.append({"frac": float(frac), "pyzbar": py, "cv2": cv})
    return results, n_mod


def experiment_sparse(level_const, mask_flippable, label):
    qr, n_mod, _ = make_qr(level_const)
    qr_b = with_quiet_zone(qr)
    n_subset = int(mask_flippable.sum())
    results = []
    fracs = np.linspace(0.0, 0.60, 25)
    for frac in fracs:
        ok_py, ok_cv = 0, 0
        for trial in range(N_TRIALS):
            out = sparse_noise_subset(qr_b, mask_flippable, frac, n_mod,
                                      seed=trial * 7919 + int(frac * 1000))
            py, cv = try_decode(out)
            if py: ok_py += 1
            if cv: ok_cv += 1
        results.append({
            "frac": float(frac),
            "p_pyzbar": ok_py / N_TRIALS,
            "p_cv2": ok_cv / N_TRIALS,
            "n_subset": n_subset,
        })
    return results, n_mod


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", default="/Users/pinperepette/Github/blog/output/cliff-exp")
    args = ap.parse_args()
    os.makedirs(args.outdir, exist_ok=True)

    all_data = {}
    colors = {"L": "#4ecdc4", "M": "#7c4dff", "Q": "#ff8800", "H": "#00ff88"}

    for name, const, pct in LEVELS:
        qq = qrcode.QRCode(error_correction=const, box_size=10, border=2)
        qq.add_data(URL); qq.make(fit=True)
        n_mod = qq.modules_count
        version = qq.version
        struct_mask = structural_positions(n_mod, version)
        data_mask = ~struct_mask

        print(f"[{name}] V{version}, {n_mod}x{n_mod}, struct={struct_mask.sum()}, data={data_mask.sum()}")
        print(f"  A. occlusione centrale...")
        ctr, _ = experiment_central(const)
        print(f"  B. rumore su DATI (rispetta struttura)...")
        sp_data, _ = experiment_sparse(const, data_mask, "data")
        print(f"  C. rumore su STRUTTURA (rompe cornice)...")
        sp_struct, _ = experiment_sparse(const, struct_mask, "struct")

        all_data[name] = {
            "level_pct_nominal": pct,
            "version": version,
            "modules": n_mod,
            "n_struct": int(struct_mask.sum()),
            "n_data": int(data_mask.sum()),
            "central": ctr,
            "sparse_data": sp_data,
            "sparse_struct": sp_struct,
        }

    with open(os.path.join(args.outdir, "cliff_data.json"), "w") as f:
        json.dump(all_data, f, indent=2)

    # Plot A: occlusione centrale
    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=140)
    for name, _, _ in LEVELS:
        d = all_data[name]["central"]
        x = [r["frac"] * 100 for r in d]
        y_py = [int(r["pyzbar"]) for r in d]
        ax.plot(x, y_py, color=colors[name], linewidth=2,
                label=f"livello {name} ({all_data[name]['level_pct_nominal']*100:.0f}% nominale)")
    ax.set_xlabel("% area dell'immagine occlusa (cerchio bianco al centro)")
    ax.set_ylabel("pyzbar decode (0/1)")
    ax.set_title("Occlusione centrale: il cliff cade sotto Singleton")
    ax.set_ylim(-0.05, 1.05)
    ax.legend(fontsize=9, loc="upper right")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(args.outdir, "cliff_central.png"))
    plt.close(fig)

    # Plot B: rumore su dati (Singleton vero)
    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=140)
    for name, _, pct in LEVELS:
        d = all_data[name]["sparse_data"]
        x = [r["frac"] * 100 for r in d]
        y_py = [r["p_pyzbar"] for r in d]
        ax.plot(x, y_py, color=colors[name], linewidth=2,
                label=f"livello {name} (Singleton {pct*100:.0f}%)")
        ax.axvline(pct * 100, color=colors[name], linestyle=":", alpha=0.5)
    ax.set_xlabel("% moduli dati flippati (struttura intatta)")
    ax.set_ylabel(f"prob. decodifica pyzbar ({N_TRIALS} prove)")
    ax.set_title("Rumore sparso su dati: il cliff coincide con Singleton")
    ax.set_ylim(-0.05, 1.05)
    ax.legend(fontsize=9, loc="upper right")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(args.outdir, "cliff_sparse_data.png"))
    plt.close(fig)

    # Plot C: rumore su struttura (cornice fragile)
    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=140)
    for name, _, _ in LEVELS:
        d = all_data[name]["sparse_struct"]
        x = [r["frac"] * 100 for r in d]
        y_py = [r["p_pyzbar"] for r in d]
        ax.plot(x, y_py, color=colors[name], linewidth=2, label=f"livello {name}")
    ax.set_xlabel("% moduli strutturali flippati (dati intatti)")
    ax.set_ylabel(f"prob. decodifica pyzbar ({N_TRIALS} prove)")
    ax.set_title("Rumore sparso su struttura: la cornice cade subito")
    ax.set_ylim(-0.05, 1.05)
    ax.legend(fontsize=9, loc="upper right")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(args.outdir, "cliff_sparse_struct.png"))
    plt.close(fig)

    # Summary
    print("\n=== SOMMARIO ===")
    for name, _, pct in LEVELS:
        d = all_data[name]
        # Cliff occlusione centrale: prima frac dove pyzbar fail
        py_centr = next((r["frac"] for r in d["central"] if not r["pyzbar"]), 1.0)
        # Cliff sparse data: prob = 0.5
        py_sp_data = next((r["frac"] for r in d["sparse_data"] if r["p_pyzbar"] < 0.5), 1.0)
        # Cliff sparse struct: prob = 0.5
        py_sp_str = next((r["frac"] for r in d["sparse_struct"] if r["p_pyzbar"] < 0.5), 1.0)
        print(f"{name} (Singleton {pct*100:.0f}%):  occlusione {py_centr*100:5.1f}%  "
              f"|  dati {py_sp_data*100:5.1f}%  |  struttura {py_sp_str*100:5.1f}%")


if __name__ == "__main__":
    main()
