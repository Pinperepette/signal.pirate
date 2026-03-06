#!/usr/bin/env python3
"""
4 tecniche di steganografia a confronto.
Prende un'immagine, nasconde lo stesso messaggio con 4 metodi diversi,
produce 4 immagini PNG (per non perdere dati prima del test social).
"""

import sys
import os
import numpy as np
from PIL import Image
from scipy.fft import dctn, idctn

MESSAGE = "SIGNAL_PIRATE_2026"
SEED = 42

def msg_to_bits(msg):
    bits = []
    for c in msg:
        for i in range(7, -1, -1):
            bits.append((ord(c) >> i) & 1)
    # Aggiungi terminatore (8 bit zero)
    bits.extend([0] * 8)
    return bits

def bits_to_msg(bits):
    chars = []
    for i in range(0, len(bits) - 7, 8):
        byte = 0
        for j in range(8):
            byte = (byte << 1) | bits[i + j]
        if byte == 0:
            break
        chars.append(chr(byte))
    return ''.join(chars)


# ============================================================
# 1. LSB — Least Significant Bit (fragile)
# ============================================================
def encode_lsb(img, msg):
    pixels = np.array(img).copy()
    flat = pixels.flatten()
    bits = msg_to_bits(msg)

    if len(bits) > len(flat):
        raise ValueError(f"Messaggio troppo lungo: {len(bits)} bit, spazio: {len(flat)}")

    for i, bit in enumerate(bits):
        flat[i] = (flat[i] & 0xFE) | bit

    return Image.fromarray(flat.reshape(pixels.shape).astype(np.uint8))


def decode_lsb(img):
    flat = np.array(img).flatten()
    bits = [flat[i] & 1 for i in range(min(len(flat), 4096))]
    return bits_to_msg(bits)


# ============================================================
# 2. DCT mid-frequency embedding
# ============================================================
BLOCK = 8
DCT_POSITIONS = [(2, 3), (3, 2), (4, 1), (1, 4), (3, 3)]
DCT_STRENGTH = 50

def encode_dct(img, msg):
    arr = np.array(img.convert('YCbCr')).astype(np.float64)
    y_channel = arr[:, :, 0].copy()
    bits = msg_to_bits(msg)

    h, w = y_channel.shape
    bh, bw = h // BLOCK, w // BLOCK
    bit_idx = 0

    for by in range(bh):
        for bx in range(bw):
            if bit_idx >= len(bits):
                break
            block = y_channel[by*BLOCK:(by+1)*BLOCK, bx*BLOCK:(bx+1)*BLOCK]
            dct_block = dctn(block, type=2, norm='ortho')

            pos = DCT_POSITIONS[bit_idx % len(DCT_POSITIONS)]
            coeff = dct_block[pos[0], pos[1]]

            if bits[bit_idx] == 1:
                dct_block[pos[0], pos[1]] = abs(coeff) + DCT_STRENGTH if coeff >= 0 else -(abs(coeff) + DCT_STRENGTH)
                if abs(dct_block[pos[0], pos[1]]) < DCT_STRENGTH:
                    dct_block[pos[0], pos[1]] = DCT_STRENGTH
            else:
                dct_block[pos[0], pos[1]] = 0

            y_channel[by*BLOCK:(by+1)*BLOCK, bx*BLOCK:(bx+1)*BLOCK] = idctn(dct_block, type=2, norm='ortho')
            bit_idx += 1

    arr[:, :, 0] = np.clip(y_channel, 0, 255)

    # YCbCr -> RGB
    from PIL import ImageCms
    ycbcr_img = Image.fromarray(arr.astype(np.uint8), mode='YCbCr')
    return ycbcr_img.convert('RGB')


def decode_dct(img):
    arr = np.array(img.convert('YCbCr')).astype(np.float64)
    y_channel = arr[:, :, 0]
    h, w = y_channel.shape
    bh, bw = h // BLOCK, w // BLOCK

    bits = []
    bit_idx = 0
    for by in range(bh):
        for bx in range(bw):
            if bit_idx >= 4096:
                break
            block = y_channel[by*BLOCK:(by+1)*BLOCK, bx*BLOCK:(bx+1)*BLOCK]
            dct_block = dctn(block, type=2, norm='ortho')

            pos = DCT_POSITIONS[bit_idx % len(DCT_POSITIONS)]
            coeff = abs(dct_block[pos[0], pos[1]])

            bits.append(1 if coeff > DCT_STRENGTH / 2 else 0)
            bit_idx += 1

    return bits_to_msg(bits)


# ============================================================
# 3. Spread Spectrum (differenziale su coppie di blocchi)
# ============================================================
SS_STRENGTH = 20
SS_HALF = 128  # pixel per mezzo-blocco (coppia = 256)

def encode_spread(img, msg):
    arr = np.array(img.convert('YCbCr')).astype(np.float64)
    y = arr[:, :, 0].flatten().copy()
    bits = msg_to_bits(msg)

    rng = np.random.RandomState(SEED)

    for i, bit in enumerate(bits):
        start_a = i * SS_HALF * 2
        start_b = start_a + SS_HALF
        if start_b + SS_HALF > len(y):
            raise ValueError("Immagine troppo piccola")
        chip = rng.choice([-1.0, 1.0], size=SS_HALF)
        signal = 1.0 if bit == 1 else -1.0
        # Aggiungi a blocco A, sottrai da blocco B
        y[start_a:start_a + SS_HALF] += signal * chip * SS_STRENGTH
        y[start_b:start_b + SS_HALF] -= signal * chip * SS_STRENGTH

    arr[:, :, 0] = np.clip(y.reshape(arr.shape[:2]), 0, 255)
    return Image.fromarray(arr.astype(np.uint8), mode='YCbCr').convert('RGB')


def decode_spread(img):
    arr = np.array(img.convert('YCbCr')).astype(np.float64)
    y = arr[:, :, 0].flatten()
    max_bits = min(4096, len(y) // (SS_HALF * 2))

    rng = np.random.RandomState(SEED)
    bits = []

    for i in range(max_bits):
        start_a = i * SS_HALF * 2
        start_b = start_a + SS_HALF
        chip = rng.choice([-1.0, 1.0], size=SS_HALF)
        # Differenza tra i due blocchi elimina il contenuto originale
        diff = y[start_a:start_a + SS_HALF] - y[start_b:start_b + SS_HALF]
        correlation = np.dot(diff, chip)
        bits.append(1 if correlation > 0 else 0)

        if len(bits) >= 8 and len(bits) % 8 == 0:
            last_byte = 0
            for b in bits[-8:]:
                last_byte = (last_byte << 1) | b
            if last_byte == 0:
                bits = bits[:-8]
                break

    return bits_to_msg(bits)


# ============================================================
# 4. QIM — Quantization Index Modulation
# ============================================================
QIM_DELTA = 40

def encode_qim(img, msg):
    arr = np.array(img).astype(np.float64)
    bits = msg_to_bits(msg)
    flat = arr.flatten()

    rng = np.random.RandomState(SEED + 1)
    indices = rng.permutation(len(flat))

    for i, bit in enumerate(bits):
        idx = indices[i]
        val = flat[idx]
        # Quantizza su due griglie diverse
        q0 = np.round(val / QIM_DELTA) * QIM_DELTA
        q1 = np.round((val - QIM_DELTA / 2) / QIM_DELTA) * QIM_DELTA + QIM_DELTA / 2

        flat[idx] = q1 if bit == 1 else q0

    return Image.fromarray(np.clip(flat.reshape(arr.shape), 0, 255).astype(np.uint8))


def decode_qim(img):
    arr = np.array(img).astype(np.float64)
    flat = arr.flatten()

    rng = np.random.RandomState(SEED + 1)
    indices = rng.permutation(len(flat))

    bits = []
    for i in range(min(4096, len(indices))):
        idx = indices[i]
        val = flat[idx]

        q0 = np.round(val / QIM_DELTA) * QIM_DELTA
        q1 = np.round((val - QIM_DELTA / 2) / QIM_DELTA) * QIM_DELTA + QIM_DELTA / 2

        d0 = abs(val - q0)
        d1 = abs(val - q1)

        bits.append(1 if d1 < d0 else 0)

        # Check terminatore
        if len(bits) >= 8 and len(bits) % 8 == 0:
            last_byte = 0
            for b in bits[-8:]:
                last_byte = (last_byte << 1) | b
            if last_byte == 0:
                bits = bits[:-8]
                break

    return bits_to_msg(bits)


# ============================================================
# Main
# ============================================================
def main():
    if len(sys.argv) < 2:
        print(f"Uso: python {sys.argv[0]} <immagine>")
        sys.exit(1)

    src = sys.argv[1]
    img = Image.open(src).convert('RGB')
    base = os.path.splitext(os.path.basename(src))[0]
    outdir = os.path.dirname(src) or '.'

    print(f"Immagine: {src} ({img.size[0]}x{img.size[1]})")
    print(f"Messaggio: {MESSAGE}")
    print(f"Bit da nascondere: {len(msg_to_bits(MESSAGE))}")
    print()

    techniques = [
        ('lsb', 'LSB classico', encode_lsb, decode_lsb),
        ('dct', 'DCT mid-frequency', encode_dct, decode_dct),
        ('spread', 'Spread Spectrum', encode_spread, decode_spread),
        ('qim', 'QIM', encode_qim, decode_qim),
    ]

    for tag, name, enc_fn, dec_fn in techniques:
        print(f"[{tag.upper()}] {name}...")
        try:
            encoded = enc_fn(img, MESSAGE)
            out_png = os.path.join(outdir, f"{base}_{tag}.png")
            encoded.save(out_png)

            # Verifica immediata
            verify = dec_fn(Image.open(out_png))
            ok = verify == MESSAGE
            print(f"  -> {out_png}")
            print(f"  Verifica: {'OK' if ok else 'FAIL'} (letto: '{verify}')")

            # Test: salva come JPEG quality 85 e ri-decodifica
            out_jpg = os.path.join(outdir, f"{base}_{tag}_q85.jpg")
            encoded.save(out_jpg, 'JPEG', quality=85)
            verify_jpg = dec_fn(Image.open(out_jpg))
            ok_jpg = verify_jpg == MESSAGE
            print(f"  JPEG q85: {'SOPRAVVIVE' if ok_jpg else 'DISTRUTTO'} (letto: '{verify_jpg[:30]}')")
        except Exception as e:
            print(f"  ERRORE: {e}")
        print()

    print("Fatto. Posta le 4 PNG su Twitter, riscaricale, e lancia decode_all.py")


if __name__ == '__main__':
    main()
