"""
Refinement chirurgico di un sample QR art generato da Stable Diffusion + ControlNet.

Strategia:
- Identifica i moduli strutturali del QR (finder, separator, timing, alignment,
  dark module, format info). Per Version 6 sono 297 moduli su 2025.
- Forza i moduli strutturali al 90% verso il valore canonico (10% texture originale).
- Per i moduli dati, sampla la luminanza media e identifica quelli "sbagliati"
  (interpretati come dark se >127 o viceversa). Solo quelli vengono ritoccati al 70%.
- Aggiunge una quiet zone bianca di 80 px ai bordi.

Risultato: l'85% del mosaico AI resta intatto, ma il QR e' decodificabile.

Uso:
  python3 qr_refine.py --src input.png --url "https://..." --out refined.png
"""

import argparse
import numpy as np
import qrcode
from qrcode.constants import ERROR_CORRECT_H
from PIL import Image, ImageOps
import cv2


def canonical_matrix(url: str):
    """Genera la matrice QR canonica per `url`, con border 2 modules."""
    qr = qrcode.QRCode(
        version=None,
        error_correction=ERROR_CORRECT_H,
        box_size=1,
        border=0,
    )
    qr.add_data(url)
    qr.make(fit=True)
    md = np.array(qr.get_matrix(), dtype=bool)
    n = md.shape[0]
    N = n + 4
    mat = np.zeros((N, N), dtype=bool)
    mat[2:2+n, 2:2+n] = md
    return mat, n, N, qr.version


def structural_mask(N: int, n: int, version: int):
    """Maschera dei moduli strutturali (finder, timing, alignment, format, dark)."""
    s = np.zeros((N, N), dtype=bool)

    # Finder patterns (7x7) ai tre angoli (in full-coord, considerando border 2)
    for sy, sx in [(2, 2), (2, N-9), (N-9, 2)]:
        s[sy:sy+7, sx:sx+7] = True

    # Separator (1 modulo bianco intorno ai finder)
    s[9, 2:10] = True; s[2:10, 9] = True              # top-left
    s[9, N-10:N-2] = True; s[2:10, N-10] = True       # top-right
    s[N-10, 2:10] = True; s[N-10:N-2, 9] = True       # bottom-left

    # Timing pattern (riga 8 e col 8 in full-coord)
    s[8, 8:N-8] = True
    s[8:N-8, 8] = True

    # Alignment patterns: per Version 6, centro a (22, 22) QR-coord = (24, 24) full
    if version >= 2:
        # Posizioni alignment per Version V (vedi specifica ISO 18004)
        alignment_positions = {
            2: [6, 18], 3: [6, 22], 4: [6, 26], 5: [6, 30],
            6: [6, 34], 7: [6, 22, 38], 8: [6, 24, 42],
        }
        positions = alignment_positions.get(version, [6, 34])
        for ay in positions:
            for ax in positions:
                # skip se sovrapposto a finder
                if (ay == 6 and ax == 6) or (ay == 6 and ax == n-7) or (ay == n-7 and ax == 6):
                    continue
                fy, fx = ay + 2, ax + 2  # offset border
                if 0 <= fy-2 < N and 0 <= fx-2 < N:
                    s[fy-2:fy+3, fx-2:fx+3] = True

    # Dark module: (4V + 9, 8) in QR-coord = (4*6+9, 8) = (33, 8) per V6
    dy, dx = 4 * version + 9 + 2, 8 + 2
    if 0 <= dy < N and 0 <= dx < N:
        s[dy, dx] = True

    # Format info: 15 bit intorno ai finder
    # Around top-left: row 10 cols 2..9 + col 10 rows 2..9
    for c in range(2, 11):
        s[10, c] = True
    for r in range(2, 11):
        s[r, 10] = True
    # Around top-right: row 10 cols N-9..N-2
    for c in range(N-9, N-2):
        s[10, c] = True
    # Around bottom-left: col 10 rows N-9..N-2
    for r in range(N-9, N-2):
        s[r, 10] = True

    return s


def refine(src_path: str, url: str, out_path: str, size: int = 1024,
           border_px: int = 80, struct_force: float = 0.90,
           data_force: float = 0.70, threshold: int = 127,
           color: bool = True) -> bool:
    """Applica refinement chirurgico. Se color=True lavora in RGB preservando la tinta."""
    mat, n, N, version = canonical_matrix(url)
    print(f"QR Version {version}, {n}x{n} dati, {N}x{N} con border")

    if color:
        art_rgb = np.array(
            Image.open(src_path).convert("RGB").resize((size, size), Image.LANCZOS),
            dtype=np.float32,
        )
        art_lum = np.array(
            Image.open(src_path).convert("L").resize((size, size), Image.LANCZOS),
            dtype=np.float32,
        )
        out = art_rgb.copy()
    else:
        art_lum = np.array(
            Image.open(src_path).convert("L").resize((size, size), Image.LANCZOS),
            dtype=np.float32,
        )
        out = art_lum.copy()

    px = size / N
    struct = structural_mask(N, n, version)
    n_struct = int(struct.sum())
    print(f"moduli strutturali: {n_struct}/{N*N}")

    n_struct_applied = 0
    n_data_fixed = 0

    for i in range(N):
        for j in range(N):
            y0, y1 = int(i * px), int((i + 1) * px)
            x0, x1 = int(j * px), int((j + 1) * px)
            target_dark = bool(mat[i, j])

            if struct[i, j]:
                # strutturale: forza canonico
                if color:
                    target = np.array([0., 0., 0.]) if target_dark else np.array([255., 255., 255.])
                else:
                    target = 0.0 if target_dark else 255.0
                out[y0:y1, x0:x1] = (1 - struct_force) * out[y0:y1, x0:x1] + struct_force * target
                n_struct_applied += 1
                continue

            # dato: ritocca solo se sbagliato
            lum = art_lum[y0:y1, x0:x1].mean()
            ai_dark = lum < threshold
            if ai_dark == target_dark:
                continue

            patch = out[y0:y1, x0:x1].copy()
            if target_dark:
                # scurire mantenendo tinta: moltiplica
                patch = patch * (1 - data_force)
            else:
                # schiarire mantenendo tinta: avvicina a bianco preservando rapporti
                patch = patch + (255.0 - patch) * data_force
            out[y0:y1, x0:x1] = patch
            n_data_fixed += 1

    print(f"applicati: {n_struct_applied} strutturali + {n_data_fixed} dati = {n_struct_applied + n_data_fixed}")

    out_u8 = np.clip(out, 0, 255).astype(np.uint8)
    if color:
        bordered = ImageOps.expand(Image.fromarray(out_u8), border=border_px, fill=(255, 255, 255))
    else:
        bordered = ImageOps.expand(Image.fromarray(out_u8), border=border_px, fill=255)
    bordered.save(out_path)

    # verifica
    img = cv2.imread(out_path, cv2.IMREAD_GRAYSCALE)
    det = cv2.QRCodeDetector()
    d, _, _ = det.detectAndDecode(img)
    if d != url:
        _, otsu = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        d, _, _ = det.detectAndDecode(otsu)
    ok = d == url
    print(f"cv2 verifica: {'OK' if ok else 'FAIL'} -> {repr(d)[:60]}")
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True, help="input AI image")
    ap.add_argument("--url", required=True, help="URL canonico encoded nel QR")
    ap.add_argument("--out", required=True, help="output refined image")
    ap.add_argument("--size", type=int, default=1024)
    ap.add_argument("--border", type=int, default=80, help="quiet zone bianca (px)")
    ap.add_argument("--struct-force", type=float, default=0.90)
    ap.add_argument("--data-force", type=float, default=0.70)
    ap.add_argument("--threshold", type=int, default=127,
                    help="soglia per identificare moduli dark nel sample AI")
    ap.add_argument("--grayscale", action="store_true",
                    help="output in grayscale (default: RGB, preserva colori)")
    args = ap.parse_args()

    ok = refine(
        src_path=args.src,
        url=args.url,
        out_path=args.out,
        size=args.size,
        border_px=args.border,
        struct_force=args.struct_force,
        data_force=args.data_force,
        threshold=args.threshold,
        color=not args.grayscale,
    )
    if not ok:
        print("[hint] sample troppo lontano dal QR, riprova con cn-scale piu' alta in generazione")


if __name__ == "__main__":
    main()
