#!/usr/bin/env python3
"""
Genera pr-github.png: la vista "Files changed" di una pull request come la vede
il revisore. E' esattamente il punto cieco: cli.py con una riga in piu' (sembra
innocuo) e build-spec.png collassato come binario, "Binary file not shown".

Ricostruzione fedele dello stile GitHub (tema chiaro), non uno screenshot reale.
Uso: python3 make_pr_screenshot.py [output.png]
"""
import sys
from PIL import Image, ImageDraw, ImageFont

OUT = sys.argv[1] if len(sys.argv) > 1 else "../../immagini/il-pixel-che-da-ordini/pr-github.png"
S = 2  # supersampling per bordi nitidi

# palette GitHub (light)
WHITE = "#ffffff"; BORDER = "#d0d7de"; HEADER = "#f6f8fa"
TEXT = "#1f2328"; MUTED = "#656d76"; LNUM = "#6e7781"
ADD_BG = "#e6ffec"; ADD_GUT = "#ccffd8"; GREEN = "#1a7f37"

ui_fonts = ["/System/Library/Fonts/Helvetica.ttc",
            "/System/Library/Fonts/Supplemental/Arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]
ui_bold  = ["/System/Library/Fonts/Supplemental/Arial Bold.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]
mono_fonts = ["/System/Library/Fonts/Supplemental/Menlo.ttc",
              "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"]


def load(paths, size):
    for p in paths:
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            continue
    return ImageFont.load_default()


f_ui   = load(ui_fonts, 15 * S)
f_uib  = load(ui_bold, 15 * S)
f_small = load(ui_fonts, 12 * S)
f_mono = load(mono_fonts, 13 * S)

W = 900 * S
PAD = 24 * S
CARD_W = W - PAD * 2
ROW = 24 * S           # diff line height
HEAD_H = 42 * S

# altezza totale: titolo + card1(header+3 righe) + gap + card2(header+box)
y_title = 22 * S
card1_y = 58 * S
card1_h = HEAD_H + ROW * 3 + 12 * S
gap = 16 * S
card2_y = card1_y + card1_h + gap
card2_body = 84 * S
card2_h = HEAD_H + card2_body
H = card2_y + card2_h + PAD

img = Image.new("RGB", (W, H), WHITE)
d = ImageDraw.Draw(img)


def rrect(xy, r, fill=None, outline=None, width=1):
    d.rounded_rectangle(xy, radius=r, fill=fill, outline=outline, width=width)


def file_icon(x, y):
    # piccolo glifo "file" stile octicon
    w, h = 11 * S, 14 * S
    d.rounded_rectangle([x, y, x + w, y + h], radius=2 * S, outline=MUTED, width=1 * S)


def chevron(x, y):
    # freccia collapse verso il basso, disegnata (niente dipendenza da font)
    w = 9 * S
    d.polygon([(x, y), (x + w, y), (x + w / 2, y + w * 0.6)], fill=MUTED)


# --- titolo ---
d.text((PAD, y_title), "2 files changed", font=f_uib, fill=TEXT)
tw = d.textlength("2 files changed", font=f_uib)
d.text((PAD + tw + 14 * S, y_title + 2 * S), "+1  −0", font=f_small, fill=MUTED)

# ============ CARD 1: cli.py ============
rrect([PAD, card1_y, PAD + CARD_W, card1_y + card1_h], 8 * S, fill=WHITE, outline=BORDER, width=1 * S)
# header
d.rounded_rectangle([PAD, card1_y, PAD + CARD_W, card1_y + HEAD_H], radius=8 * S, fill=HEADER)
d.rectangle([PAD, card1_y + HEAD_H - 8 * S, PAD + CARD_W, card1_y + HEAD_H], fill=HEADER)
d.line([PAD, card1_y + HEAD_H, PAD + CARD_W, card1_y + HEAD_H], fill=BORDER, width=1 * S)
hy = card1_y + (HEAD_H - 15 * S) // 2
chevron(PAD + 16 * S, hy + 5 * S)
file_icon(PAD + 40 * S, card1_y + (HEAD_H - 14 * S) // 2)
d.text((PAD + 60 * S, hy), "src/cli.py", font=f_ui, fill=TEXT)
# stat a destra
st = "+1 −0"
stw = d.textlength(st, font=f_small)
d.text((PAD + CARD_W - 22 * S - stw, hy + 1 * S), st, font=f_small, fill=MUTED)
d.rectangle([PAD + CARD_W - 16 * S, hy + 3 * S, PAD + CARD_W - 12 * S, hy + 10 * S], fill=GREEN)

# diff body
gx_old = PAD + 8 * S      # colonna numero riga vecchia
gx_new = PAD + 40 * S     # colonna numero riga nuova
gx_sign = PAD + 74 * S
gx_code = PAD + 90 * S
by = card1_y + HEAD_H + 6 * S

rows = [
    ("ctx", "11", "11", "",  '    p = argparse.ArgumentParser(prog="acme-cli")'),
    ("add", "",   "12", "+", '    p.add_argument("--version", action="version", version=__version__)'),
    ("ctx", "12", "13", "",  '    p.add_argument("name", nargs="?", default="world")'),
]
for kind, lo, ln, sign, code in rows:
    ry = by
    if kind == "add":
        d.rectangle([PAD + 1 * S, ry, gx_sign - 2 * S, ry + ROW], fill=ADD_GUT)
        d.rectangle([gx_sign - 2 * S, ry, PAD + CARD_W - 1 * S, ry + ROW], fill=ADD_BG)
    ty = ry + (ROW - 13 * S) // 2 - 1 * S
    if lo:
        d.text((gx_old, ty), lo, font=f_mono, fill=LNUM)
    if ln:
        d.text((gx_new, ty), ln, font=f_mono, fill=LNUM)
    if sign:
        d.text((gx_sign, ty), sign, font=f_mono, fill=GREEN)
    d.text((gx_code, ty), code, font=f_mono, fill=TEXT)
    by += ROW

# ============ CARD 2: build-spec.png ============
rrect([PAD, card2_y, PAD + CARD_W, card2_y + card2_h], 8 * S, fill=WHITE, outline=BORDER, width=1 * S)
d.rounded_rectangle([PAD, card2_y, PAD + CARD_W, card2_y + HEAD_H], radius=8 * S, fill=HEADER)
d.rectangle([PAD, card2_y + HEAD_H - 8 * S, PAD + CARD_W, card2_y + HEAD_H], fill=HEADER)
d.line([PAD, card2_y + HEAD_H, PAD + CARD_W, card2_y + HEAD_H], fill=BORDER, width=1 * S)
hy2 = card2_y + (HEAD_H - 15 * S) // 2
chevron(PAD + 16 * S, hy2 + 5 * S)
file_icon(PAD + 40 * S, card2_y + (HEAD_H - 14 * S) // 2)
d.text((PAD + 60 * S, hy2), "src/build-spec.png", font=f_ui, fill=TEXT)
# pill "BIN"
pill = "BIN"
pw = d.textlength(pill, font=f_small)
px1 = PAD + CARD_W - 22 * S - pw - 12 * S
rrect([px1, hy2 - 1 * S, px1 + pw + 12 * S, hy2 + 17 * S], 9 * S, outline=BORDER, width=1 * S)
d.text((px1 + 6 * S, hy2 + 1 * S), pill, font=f_small, fill=MUTED)

# body: "Binary file not shown"
msg = "Binary file not shown."
mw = d.textlength(msg, font=f_ui)
d.text((PAD + (CARD_W - mw) // 2, card2_y + HEAD_H + card2_body // 2 - 16 * S), msg, font=f_ui, fill=MUTED)
sub = "92 KB · 900×776"
sw = d.textlength(sub, font=f_small)
d.text((PAD + (CARD_W - sw) // 2, card2_y + HEAD_H + card2_body // 2 + 4 * S), sub, font=f_small, fill=LNUM)

img = img.resize((W // S, H // S), Image.LANCZOS)
img.save(OUT)
print(f"[+] scritto {OUT}  ({img.width}x{img.height})")
