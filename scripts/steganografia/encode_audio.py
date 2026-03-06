#!/usr/bin/env python3
"""
Nasconde un file audio dentro un'immagine con 4 tecniche.
Per DCT e Spread comprimo i dati raw con zlib.
"""

import sys
import os
import struct
import zlib
import numpy as np
from PIL import Image
from scipy.fft import dctn, idctn

SEED = 42


def load_audio_raw(path):
    """Legge un WAV e restituisce i byte raw PCM."""
    with open(path, 'rb') as f:
        data = f.read()
    # Trova il chunk 'data'
    idx = data.index(b'data') + 4
    size = struct.unpack('<I', data[idx:idx+4])[0]
    raw = data[idx+4:idx+4+size]
    # Prendi anche l'header WAV per ricostruire dopo
    header = data[:idx+4+size]
    return header, raw


def data_to_bits(data):
    """Converte bytes in lista di bit, con prefisso lunghezza (32 bit)."""
    length = len(data)
    bits = []
    # 32 bit per la lunghezza
    for i in range(31, -1, -1):
        bits.append((length >> i) & 1)
    for byte in data:
        for i in range(7, -1, -1):
            bits.append((byte >> i) & 1)
    return bits


def bits_to_data(bits):
    """Ricostruisce bytes dalla lista di bit (con prefisso lunghezza)."""
    if len(bits) < 32:
        return b''
    length = 0
    for i in range(32):
        length = (length << 1) | bits[i]
    data = bytearray()
    for i in range(32, 32 + length * 8, 8):
        if i + 8 > len(bits):
            break
        byte = 0
        for j in range(8):
            byte = (byte << 1) | bits[i + j]
        data.append(byte)
    return bytes(data)


# ============================================================
# 1. LSB
# ============================================================
def encode_lsb(img, data):
    pixels = np.array(img).copy()
    flat = pixels.flatten()
    bits = data_to_bits(data)
    if len(bits) > len(flat):
        raise ValueError(f"Troppi dati: {len(bits)} bit, spazio: {len(flat)}")
    for i, bit in enumerate(bits):
        flat[i] = (flat[i] & 0xFE) | bit
    return Image.fromarray(flat.reshape(pixels.shape).astype(np.uint8))


def decode_lsb(img, max_bits=None):
    flat = np.array(img).flatten()
    # Leggi prima i 32 bit di lunghezza
    if len(flat) < 32:
        return b''
    length = 0
    for i in range(32):
        length = (length << 1) | (flat[i] & 1)
    total_bits = 32 + length * 8
    if max_bits:
        total_bits = min(total_bits, max_bits)
    bits = [flat[i] & 1 for i in range(min(total_bits, len(flat)))]
    return bits_to_data(bits)


# ============================================================
# 2. DCT
# ============================================================
BLOCK = 8
DCT_POS = [(2, 3), (3, 2), (4, 1), (1, 4), (3, 3)]
DCT_STR = 50

def encode_dct(img, data):
    arr = np.array(img.convert('YCbCr')).astype(np.float64)
    y = arr[:, :, 0].copy()
    bits = data_to_bits(data)
    h, w = y.shape
    bh, bw = h // BLOCK, w // BLOCK
    capacity = bh * bw
    if len(bits) > capacity:
        raise ValueError(f"Troppi dati per DCT: {len(bits)} bit, capacita: {capacity}")
    bit_idx = 0
    for by in range(bh):
        for bx in range(bw):
            if bit_idx >= len(bits):
                break
            block = y[by*BLOCK:(by+1)*BLOCK, bx*BLOCK:(bx+1)*BLOCK]
            dct_block = dctn(block, type=2, norm='ortho')
            pos = DCT_POS[bit_idx % len(DCT_POS)]
            if bits[bit_idx] == 1:
                dct_block[pos[0], pos[1]] = DCT_STR
            else:
                dct_block[pos[0], pos[1]] = 0
            y[by*BLOCK:(by+1)*BLOCK, bx*BLOCK:(bx+1)*BLOCK] = idctn(dct_block, type=2, norm='ortho')
            bit_idx += 1
    arr[:, :, 0] = np.clip(y, 0, 255)
    return Image.fromarray(arr.astype(np.uint8), mode='YCbCr').convert('RGB')


def decode_dct(img):
    arr = np.array(img.convert('YCbCr')).astype(np.float64)
    y = arr[:, :, 0]
    h, w = y.shape
    bh, bw = h // BLOCK, w // BLOCK
    # Leggi primi 32 bit per la lunghezza
    bits = []
    bit_idx = 0
    total_needed = 32  # inizia con i bit di lunghezza
    for by in range(bh):
        for bx in range(bw):
            if bit_idx >= total_needed:
                break
            block = y[by*BLOCK:(by+1)*BLOCK, bx*BLOCK:(bx+1)*BLOCK]
            dct_block = dctn(block, type=2, norm='ortho')
            pos = DCT_POS[bit_idx % len(DCT_POS)]
            coeff = abs(dct_block[pos[0], pos[1]])
            bits.append(1 if coeff > DCT_STR / 2 else 0)
            bit_idx += 1
            # Dopo 32 bit, calcola quanti ne servono in totale
            if bit_idx == 32:
                length = 0
                for b in bits:
                    length = (length << 1) | b
                total_needed = 32 + length * 8
    return bits_to_data(bits)


# ============================================================
# 3. Spread Spectrum (differenziale)
# ============================================================
SS_STR = 20
SS_HALF = 128

def encode_spread(img, data):
    arr = np.array(img.convert('YCbCr')).astype(np.float64)
    y = arr[:, :, 0].flatten().copy()
    bits = data_to_bits(data)
    if len(bits) * SS_HALF * 2 > len(y):
        raise ValueError(f"Troppi dati per spread: {len(bits)} bit")
    rng = np.random.RandomState(SEED)
    for i, bit in enumerate(bits):
        start_a = i * SS_HALF * 2
        start_b = start_a + SS_HALF
        chip = rng.choice([-1.0, 1.0], size=SS_HALF)
        signal = 1.0 if bit == 1 else -1.0
        y[start_a:start_a + SS_HALF] += signal * chip * SS_STR
        y[start_b:start_b + SS_HALF] -= signal * chip * SS_STR
    arr[:, :, 0] = np.clip(y.reshape(arr.shape[:2]), 0, 255)
    return Image.fromarray(arr.astype(np.uint8), mode='YCbCr').convert('RGB')


def decode_spread(img):
    arr = np.array(img.convert('YCbCr')).astype(np.float64)
    y = arr[:, :, 0].flatten()
    max_bits = len(y) // (SS_HALF * 2)
    rng = np.random.RandomState(SEED)
    bits = []
    total_needed = 32
    for i in range(min(max_bits, 500000)):
        start_a = i * SS_HALF * 2
        start_b = start_a + SS_HALF
        chip = rng.choice([-1.0, 1.0], size=SS_HALF)
        diff = y[start_a:start_a + SS_HALF] - y[start_b:start_b + SS_HALF]
        correlation = np.dot(diff, chip)
        bits.append(1 if correlation > 0 else 0)
        if len(bits) == 32:
            length = 0
            for b in bits:
                length = (length << 1) | b
            total_needed = 32 + length * 8
        if len(bits) >= total_needed:
            break
    return bits_to_data(bits)


# ============================================================
# 4. QIM
# ============================================================
QIM_DELTA = 40

def encode_qim(img, data):
    arr = np.array(img).astype(np.float64)
    flat = arr.flatten()
    bits = data_to_bits(data)
    rng = np.random.RandomState(SEED + 1)
    indices = rng.permutation(len(flat))
    if len(bits) > len(indices):
        raise ValueError("Troppi dati per QIM")
    for i, bit in enumerate(bits):
        idx = indices[i]
        val = flat[idx]
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
    total_needed = 32
    for i in range(min(len(indices), 500000)):
        idx = indices[i]
        val = flat[idx]
        q0 = np.round(val / QIM_DELTA) * QIM_DELTA
        q1 = np.round((val - QIM_DELTA / 2) / QIM_DELTA) * QIM_DELTA + QIM_DELTA / 2
        d0 = abs(val - q0)
        d1 = abs(val - q1)
        bits.append(1 if d1 < d0 else 0)
        if len(bits) == 32:
            length = 0
            for b in bits:
                length = (length << 1) | b
            total_needed = 32 + length * 8
        if len(bits) >= total_needed:
            break
    return bits_to_data(bits)


# ============================================================
# Main
# ============================================================
def main():
    if len(sys.argv) < 3:
        print(f"Uso: python {sys.argv[0]} <immagine> <audio.wav>")
        sys.exit(1)

    img_path = sys.argv[1]
    wav_path = sys.argv[2]
    img = Image.open(img_path).convert('RGB')
    wav_header, wav_raw = load_audio_raw(wav_path)

    # Comprimi per le tecniche a bassa capacita
    wav_compressed = zlib.compress(wav_header, level=9)
    wav_full = wav_header  # intero WAV per LSB/QIM

    outdir = os.path.dirname(img_path) or '.'

    print(f"Immagine: {img_path} ({img.size[0]}x{img.size[1]})")
    print(f"Audio: {wav_path} ({len(wav_raw):,} byte raw, {len(wav_raw)/8000:.2f}s)")
    print(f"WAV completo: {len(wav_full):,} byte")
    print(f"WAV compresso: {len(wav_compressed):,} byte")
    print()

    techniques = [
        ('lsb', 'LSB', encode_lsb, decode_lsb, wav_full, False),
        ('dct', 'DCT', encode_dct, decode_dct, wav_compressed, True),
        ('spread', 'Spread', encode_spread, decode_spread, wav_compressed, True),
        ('qim', 'QIM', encode_qim, decode_qim, wav_full, False),
    ]

    for tag, name, enc_fn, dec_fn, payload, compressed in techniques:
        bits_needed = (len(payload) + 4) * 8  # +4 per header lunghezza
        print(f"[{tag.upper()}] {name} — {len(payload):,} byte ({bits_needed:,} bit)...")

        try:
            encoded = enc_fn(img, payload)
            out_png = os.path.join(outdir, f"audio_{tag}.png")
            encoded.save(out_png)

            # Verifica
            recovered = dec_fn(Image.open(out_png))
            if compressed:
                try:
                    recovered_wav = zlib.decompress(recovered)
                except:
                    recovered_wav = b''
            else:
                recovered_wav = recovered

            ok = recovered_wav == wav_full if not compressed else recovered == payload
            print(f"  -> {out_png}")
            print(f"  Verifica PNG: {'OK' if ok else 'FAIL'}")

            # Test JPEG q85
            out_jpg = os.path.join(outdir, f"audio_{tag}_q85.jpg")
            encoded.save(out_jpg, 'JPEG', quality=85)
            recovered_jpg = dec_fn(Image.open(out_jpg))
            if compressed:
                try:
                    recovered_wav_jpg = zlib.decompress(recovered_jpg)
                    ok_jpg = recovered_wav_jpg == wav_full
                except:
                    ok_jpg = False
            else:
                ok_jpg = recovered_jpg == wav_full

            print(f"  JPEG q85: {'SOPRAVVIVE' if ok_jpg else 'DISTRUTTO'}")

            # Salva audio recuperato per verifica
            if ok:
                out_wav = os.path.join(outdir, f"recovered_{tag}.wav")
                with open(out_wav, 'wb') as f:
                    if compressed:
                        f.write(zlib.decompress(recovered))
                    else:
                        f.write(recovered)
                print(f"  Audio recuperato: {out_wav}")

        except Exception as e:
            print(f"  ERRORE: {e}")
        print()

    print("Fatto. Posta le 4 PNG, riscaricale, e lancia decode_audio.py")


if __name__ == '__main__':
    main()
