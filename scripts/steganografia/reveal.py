#!/usr/bin/env python3
"""
Cosa si nasconde in questa foto?
Uso: python reveal.py <immagine>

Estrae un audio nascosto con steganografia spread spectrum,
lo salva come WAV e decodifica il messaggio morse contenuto.
"""

import sys
import os
import struct
import zlib
import numpy as np
from PIL import Image

SEED = 42
SS_HALF = 128


def bits_to_data(bits):
    if len(bits) < 32:
        return b''
    length = 0
    for i in range(32):
        length = (length << 1) | bits[i]
    if length <= 0 or length > 10_000_000:
        return b''
    data = bytearray()
    for i in range(32, 32 + length * 8, 8):
        if i + 8 > len(bits):
            break
        byte = 0
        for j in range(8):
            byte = (byte << 1) | bits[i + j]
        data.append(byte)
    return bytes(data)


def extract_audio(img):
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

    compressed = bits_to_data(bits)
    return zlib.decompress(compressed)


def decode_morse_from_wav(wav_bytes):
    # Leggi header WAV
    idx = wav_bytes.index(b'data') + 4
    size = struct.unpack('<I', wav_bytes[idx:idx + 4])[0]
    samples = np.frombuffer(wav_bytes[idx + 4:idx + 4 + size], dtype=np.uint8)
    # Converti da unsigned 8-bit a float centered
    signal = samples.astype(np.float64) - 128.0

    sample_rate = 8000
    # Calcola energia in finestre
    window = int(sample_rate * 0.02)  # 20ms
    energy = []
    for i in range(0, len(signal) - window, window):
        e = np.mean(signal[i:i + window] ** 2)
        energy.append(e)

    energy = np.array(energy)
    threshold = np.max(energy) * 0.15

    # Segmenta in on/off
    on = energy > threshold
    segments = []
    state = False
    count = 0

    for is_on in on:
        if is_on == state:
            count += 1
        else:
            if count > 0:
                segments.append(('on' if state else 'off', count))
            state = is_on
            count = 1
    if count > 0:
        segments.append(('on' if state else 'off', count))

    # Stima durata dot (il segmento on piu' corto)
    on_durations = [c for t, c in segments if t == 'on']
    if not on_durations:
        return '???'
    dot_dur = min(on_durations)

    # Decodifica morse
    MORSE_TO_CHAR = {
        '.-': 'A', '-...': 'B', '-.-.': 'C', '-..': 'D', '.': 'E',
        '..-.': 'F', '--.': 'G', '....': 'H', '..': 'I', '.---': 'J',
        '-.-': 'K', '.-..': 'L', '--': 'M', '-.': 'N', '---': 'O',
        '.--.': 'P', '--.-': 'Q', '.-.': 'R', '...': 'S', '-': 'T',
        '..-': 'U', '...-': 'V', '.--': 'W', '-..-': 'X', '-.--': 'Y',
        '--..': 'Z', '-----': '0', '.----': '1', '..---': '2',
        '...--': '3', '....-': '4', '.....': '5', '-....': '6',
        '--...': '7', '---..': '8', '----.': '9',
    }

    morse_symbols = []
    for seg_type, duration in segments:
        if seg_type == 'on':
            if duration <= dot_dur * 2:
                morse_symbols.append('.')
            else:
                morse_symbols.append('-')
        else:  # off
            if duration <= dot_dur * 2:
                pass  # pausa tra simboli
            elif duration <= dot_dur * 5:
                morse_symbols.append(' ')  # pausa tra lettere
            else:
                morse_symbols.append('/')  # pausa tra parole

    # Raggruppa in lettere
    morse_str = ''.join(morse_symbols)
    letters = []
    for word in morse_str.split('/'):
        for letter in word.strip().split(' '):
            letter = letter.strip()
            if letter:
                ch = MORSE_TO_CHAR.get(letter, '?')
                letters.append(ch)
        letters.append(' ')

    return ''.join(letters).strip()


def main():
    if len(sys.argv) < 2:
        print("Uso: python reveal.py <immagine>")
        print()
        print("Estrae un messaggio nascosto da una foto.")
        sys.exit(1)

    path = sys.argv[1]
    if not os.path.exists(path):
        print(f"File non trovato: {path}")
        sys.exit(1)

    img = Image.open(path).convert('RGB')
    print(f"Immagine: {path} ({img.size[0]}x{img.size[1]})")
    print()

    # Estrai audio
    print("Estrazione dati nascosti...")
    try:
        wav_data = extract_audio(img)
    except Exception as e:
        print(f"Nessun dato trovato ({e})")
        sys.exit(1)

    # Salva WAV
    outdir = os.path.dirname(path) or '.'
    out_wav = os.path.join(outdir, 'hidden_message.wav')
    with open(out_wav, 'wb') as f:
        f.write(wav_data)
    duration = (len(wav_data) - 44) / 8000
    print(f"Audio estratto: {out_wav} ({duration:.1f}s)")
    print()

    # Decodifica morse
    print("Decodifica morse...")
    message = decode_morse_from_wav(wav_data)
    print()
    print(f"  +-{'=' * (len(message) + 2)}-+")
    print(f"  |  {message}  |")
    print(f"  +-{'=' * (len(message) + 2)}-+")
    print()


if __name__ == '__main__':
    main()
