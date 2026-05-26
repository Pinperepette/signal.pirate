"""
QR code per https://pinperepette.github.io/signal.pirate/ con skull + crossbones
+ bandana al centro. Livello H. Versione "logo elaborato".
"""

import qrcode
from qrcode.constants import ERROR_CORRECT_H
from PIL import Image, ImageDraw
from pyzbar.pyzbar import decode

URL = "https://pinperepette.github.io/signal.pirate/"
OUT = "qr-pirata.png"

def build_qr(url):
    qr = qrcode.QRCode(
        version=None,
        error_correction=ERROR_CORRECT_H,
        box_size=20,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    return img

def draw_pirate(canvas_size):
    """Skull + crossbones + bandana rossa su canvas_size x canvas_size."""
    s = canvas_size
    img = Image.new("RGBA", (s, s), (255, 255, 255, 0))
    d = ImageDraw.Draw(img)

    cx, cy = s // 2, s // 2

    # cerchio bianco di fondo
    pad = int(s * 0.04)
    d.ellipse(
        [pad, pad, s - pad, s - pad],
        fill=(255, 255, 255, 255),
        outline=(0, 0, 0, 255),
        width=max(2, s // 60),
    )

    # crossbones (due rettangoli incrociati dietro al teschio)
    bone_len = int(s * 0.58)
    bone_w = max(6, int(s * 0.07))
    bone_color = (30, 30, 30, 255)
    # ossa diagonali: traccio come rettangoli ruotati via Image rotation
    bone_img = Image.new("RGBA", (s, s), (255, 255, 255, 0))
    bd = ImageDraw.Draw(bone_img)
    # osso orizzontale di base con palle agli estremi
    for angle in (45, -45):
        layer = Image.new("RGBA", (s, s), (255, 255, 255, 0))
        ld = ImageDraw.Draw(layer)
        # corpo
        ld.rectangle(
            [cx - bone_len // 2, cy - bone_w // 2, cx + bone_len // 2, cy + bone_w // 2],
            fill=bone_color, outline=(0, 0, 0, 255), width=max(1, s // 120),
        )
        # palle agli estremi
        ball_r = int(bone_w * 1.1)
        for k in (-1, 1):
            bx = cx + k * (bone_len // 2)
            ld.ellipse(
                [bx - ball_r, cy - ball_r, bx + ball_r, cy + ball_r],
                fill=bone_color, outline=(0, 0, 0, 255), width=max(1, s // 120),
            )
        rotated = layer.rotate(angle, resample=Image.BICUBIC, center=(cx, cy))
        bone_img.alpha_composite(rotated)
    img.alpha_composite(bone_img)

    # teschio (in primo piano sopra le ossa)
    skull_w = int(s * 0.52)
    skull_h = int(s * 0.46)
    skull_top = cy - int(skull_h * 0.55)
    skull_box = [cx - skull_w // 2, skull_top, cx + skull_w // 2, skull_top + skull_h]
    d.ellipse(
        skull_box,
        fill=(245, 245, 240, 255),
        outline=(0, 0, 0, 255),
        width=max(2, s // 80),
    )

    # mascella (rettangolo arrotondato sotto al cranio)
    jaw_w = int(skull_w * 0.55)
    jaw_h = int(skull_h * 0.28)
    jaw_top = skull_top + skull_h - jaw_h // 4
    jaw_box = [cx - jaw_w // 2, jaw_top, cx + jaw_w // 2, jaw_top + jaw_h]
    d.rounded_rectangle(
        jaw_box,
        radius=jaw_h // 3,
        fill=(245, 245, 240, 255),
        outline=(0, 0, 0, 255),
        width=max(2, s // 80),
    )

    # denti (linee verticali sulla mascella)
    tooth_n = 4
    tooth_step = jaw_w // (tooth_n + 1)
    for i in range(1, tooth_n + 1):
        tx = cx - jaw_w // 2 + i * tooth_step
        d.line(
            [(tx, jaw_top), (tx, jaw_top + jaw_h)],
            fill=(0, 0, 0, 255), width=max(1, s // 120),
        )

    # occhi (due cerchi neri)
    eye_r = int(skull_w * 0.12)
    eye_y = skull_top + int(skull_h * 0.42)
    for k in (-1, 1):
        ex = cx + k * int(skull_w * 0.20)
        d.ellipse(
            [ex - eye_r, eye_y - eye_r, ex + eye_r, eye_y + eye_r],
            fill=(0, 0, 0, 255),
        )

    # naso (triangolo nero invertito)
    nose_w = int(skull_w * 0.08)
    nose_top = skull_top + int(skull_h * 0.62)
    nose_bot = skull_top + int(skull_h * 0.78)
    d.polygon(
        [(cx - nose_w, nose_top), (cx + nose_w, nose_top), (cx, nose_bot)],
        fill=(0, 0, 0, 255),
    )

    # bandana rossa sopra il cranio
    band_top = skull_top + int(skull_h * 0.10)
    band_bot = skull_top + int(skull_h * 0.32)
    band_left = cx - int(skull_w * 0.55)
    band_right = cx + int(skull_w * 0.55)
    band_color = (180, 30, 30, 255)
    # corpo trapezoidale
    d.polygon(
        [
            (band_left, band_bot),
            (band_right, band_bot),
            (band_right - int(skull_w * 0.05), band_top),
            (band_left + int(skull_w * 0.05), band_top),
        ],
        fill=band_color,
        outline=(0, 0, 0, 255),
        width=max(1, s // 120),
    )
    # nodo a sinistra
    knot_size = int(skull_w * 0.16)
    knot_cx = band_left - int(knot_size * 0.3)
    knot_cy = band_bot - int((band_bot - band_top) * 0.45)
    d.polygon(
        [
            (knot_cx, knot_cy - knot_size // 2),
            (knot_cx - knot_size, knot_cy - knot_size // 3),
            (knot_cx - knot_size // 2, knot_cy),
            (knot_cx - knot_size, knot_cy + knot_size // 3),
            (knot_cx, knot_cy + knot_size // 2),
        ],
        fill=band_color,
        outline=(0, 0, 0, 255),
        width=max(1, s // 120),
    )
    # puntini bianchi sulla bandana
    dot_r = max(2, int(s * 0.012))
    for k in (-1, 0, 1):
        dx = cx + k * int(skull_w * 0.20)
        dy = (band_top + band_bot) // 2
        d.ellipse([dx - dot_r, dy - dot_r, dx + dot_r, dy + dot_r], fill=(255, 255, 255, 255))

    return img

def overlay(qr_img, fraction):
    W, H = qr_img.size
    side = int(min(W, H) * fraction)
    deco = draw_pirate(side)
    x = (W - side) // 2
    y = (H - side) // 2
    out = qr_img.copy().convert("RGBA")
    out.alpha_composite(deco, (x, y))
    return out.convert("RGB")

def verify(img, label):
    res = decode(img)
    ok = bool(res) and res[0].data.decode("utf-8", errors="replace") == URL
    print(f"[{label}] decode ok = {ok}")
    return ok

def main():
    base = build_qr(URL)
    best = None
    for frac in (0.30, 0.35, 0.40, 0.42, 0.45, 0.48, 0.50):
        composed = overlay(base, frac)
        if verify(composed, f"pirate {int(frac*100)}%"):
            best = (frac, composed)

    if best is None:
        composed = overlay(base, 0.30)
        composed.save(OUT)
        print("salvato con 30% come fallback")
    else:
        frac, composed = best
        composed.save(OUT)
        print(f"salvato {OUT} con pirata al {int(frac*100)}% lineare")

if __name__ == "__main__":
    main()
