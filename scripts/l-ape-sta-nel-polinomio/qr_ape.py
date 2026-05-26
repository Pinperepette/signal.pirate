"""
QR code per https://pinperepette.github.io/signal.pirate/ con ape al centro.
Livello H (30% recovery via Reed-Solomon su GF(2^8)).
"""

import qrcode
from qrcode.constants import ERROR_CORRECT_H
from PIL import Image, ImageDraw
from pyzbar.pyzbar import decode

URL = "https://pinperepette.github.io/signal.pirate/"
OUT_PNG = "qr_ape.png"
OUT_PNG_PLAIN = "qr_plain.png"

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
    return img, qr

def draw_bee(canvas_size):
    """Disegna un'ape stilizzata su un quadrato canvas_size x canvas_size."""
    s = canvas_size
    img = Image.new("RGBA", (s, s), (255, 255, 255, 0))
    d = ImageDraw.Draw(img)

    cx, cy = s // 2, s // 2
    body_w = int(s * 0.62)
    body_h = int(s * 0.44)

    # cerchio bianco di fondo per garantire che la zona logo sia "tutta bianca"
    # (l'occlusione vera per il decoder e' questa, non i pixel colorati)
    pad = int(s * 0.04)
    d.ellipse(
        [pad, pad, s - pad, s - pad],
        fill=(255, 255, 255, 255),
        outline=(0, 0, 0, 255),
        width=max(2, s // 60),
    )

    # corpo dell'ape (ellisse gialla)
    body_box = [cx - body_w // 2, cy - body_h // 2, cx + body_w // 2, cy + body_h // 2]
    d.ellipse(body_box, fill=(255, 200, 0, 255), outline=(0, 0, 0, 255), width=max(2, s // 80))

    # strisce nere
    stripe_w = body_w // 7
    for k in (-1, 1):
        x0 = cx + k * stripe_w - stripe_w // 2
        x1 = x0 + stripe_w
        d.rectangle(
            [x0, cy - body_h // 2 + 4, x1, cy + body_h // 2 - 4],
            fill=(0, 0, 0, 255),
        )

    # ali (due ellissi bianche piene sopra il corpo)
    wing_w = int(body_w * 0.55)
    wing_h = int(body_h * 0.70)
    wing_y_off = -int(body_h * 0.40)
    for k in (-1, 1):
        wx = cx + k * int(body_w * 0.20)
        wbox = [wx - wing_w // 2, cy + wing_y_off - wing_h // 2,
                wx + wing_w // 2, cy + wing_y_off + wing_h // 2]
        d.ellipse(wbox, fill=(245, 245, 250, 255), outline=(0, 0, 0, 255), width=max(2, s // 90))

    # occhio
    eye_r = max(3, int(s * 0.025))
    eye_x = cx - int(body_w * 0.18)
    eye_y = cy - int(body_h * 0.05)
    d.ellipse([eye_x - eye_r, eye_y - eye_r, eye_x + eye_r, eye_y + eye_r], fill=(0, 0, 0, 255))

    # antenne
    head_x = cx - body_w // 2 + int(body_w * 0.08)
    head_y = cy - int(body_h * 0.15)
    for k in (-1, 1):
        d.line(
            [(head_x, head_y), (head_x - int(s * 0.10), head_y + k * int(s * 0.10))],
            fill=(0, 0, 0, 255), width=max(2, s // 100),
        )

    return img

def overlay_bee(qr_img, fraction=0.20):
    """Sovrappone l'ape al centro. fraction = frazione lineare del lato."""
    W, H = qr_img.size
    side = int(min(W, H) * fraction)
    bee = draw_bee(side)
    x = (W - side) // 2
    y = (H - side) // 2
    out = qr_img.copy().convert("RGBA")
    out.alpha_composite(bee, (x, y))
    return out.convert("RGB")

def verify(img, label):
    res = decode(img)
    if not res:
        print(f"[{label}] DECODE FALLITO")
        return False
    payload = res[0].data.decode("utf-8", errors="replace")
    ok = payload == URL
    print(f"[{label}] decode ok = {ok} | payload = {payload}")
    return ok

def main():
    qr_img, qr = build_qr(URL)
    print(f"version={qr.version}  modules={qr.modules_count}x{qr.modules_count}  ec=H")
    qr_img.save(OUT_PNG_PLAIN)
    verify(qr_img, "plain")

    # sweep ampio per trovare il cliff
    best = None
    for frac in (0.25, 0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70):
        composed = overlay_bee(qr_img, fraction=frac)
        ok = verify(composed, f"bee {int(frac*100)}%")
        if ok:
            best = (frac, composed)

    if best is None:
        print("nessuna frazione ha decodificato, fallback a 0.15")
        composed = overlay_bee(qr_img, fraction=0.15)
        verify(composed, "bee 15%")
        composed.save(OUT_PNG)
    else:
        # salvo la frazione piu' grande che ha funzionato
        frac, composed = best
        composed.save(OUT_PNG)
        print(f"salvato {OUT_PNG} con ape al {int(frac*100)}% lineare")

if __name__ == "__main__":
    main()
