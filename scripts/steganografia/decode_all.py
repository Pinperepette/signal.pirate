#!/usr/bin/env python3
"""
Decodifica le 4 immagini dopo il download da Twitter.
Uso: python decode_all.py <img_lsb> <img_dct> <img_spread> <img_qim>
  oppure: python decode_all.py <directory>  (cerca *lsb*, *dct*, *spread*, *qim*)
"""

import sys
import os
import glob
from PIL import Image

# Importa le funzioni di decodifica
from encode_all import decode_lsb, decode_dct, decode_spread, decode_qim, MESSAGE


def main():
    if len(sys.argv) == 2 and os.path.isdir(sys.argv[1]):
        d = sys.argv[1]
        files = {}
        for tag in ('lsb', 'dct', 'spread', 'qim'):
            matches = glob.glob(os.path.join(d, f'*{tag}*'))
            if matches:
                files[tag] = sorted(matches)[-1]  # prendi il piu' recente
    elif len(sys.argv) == 5:
        files = {
            'lsb': sys.argv[1],
            'dct': sys.argv[2],
            'spread': sys.argv[3],
            'qim': sys.argv[4],
        }
    else:
        print(f"Uso: python {sys.argv[0]} <directory>")
        print(f"  oppure: python {sys.argv[0]} <lsb> <dct> <spread> <qim>")
        sys.exit(1)

    decoders = {
        'lsb': ('LSB classico', decode_lsb),
        'dct': ('DCT mid-frequency', decode_dct),
        'spread': ('Spread Spectrum', decode_spread),
        'qim': ('QIM', decode_qim),
    }

    print(f"Messaggio originale: {MESSAGE}")
    print(f"{'='*60}")
    print()

    results = {}
    for tag in ('lsb', 'dct', 'spread', 'qim'):
        name, dec_fn = decoders[tag]
        path = files.get(tag)
        if not path or not os.path.exists(path):
            print(f"[{tag.upper()}] {name}: FILE NON TROVATO")
            results[tag] = False
            continue

        img = Image.open(path).convert('RGB')
        try:
            decoded = dec_fn(img)
            survived = decoded == MESSAGE
            results[tag] = survived

            status = 'SOPRAVVISSUTO' if survived else 'DISTRUTTO'
            color = '\033[92m' if survived else '\033[91m'
            reset = '\033[0m'

            print(f"[{tag.upper()}] {name}")
            print(f"  File: {path}")
            print(f"  Decodificato: '{decoded[:50]}'")
            print(f"  {color}{status}{reset}")
        except Exception as e:
            print(f"[{tag.upper()}] {name}: ERRORE ({e})")
            results[tag] = False
        print()

    print(f"{'='*60}")
    print("RISULTATO FINALE:")
    for tag in ('lsb', 'dct', 'spread', 'qim'):
        name = decoders[tag][0]
        s = results.get(tag, False)
        icon = '+' if s else 'X'
        print(f"  [{icon}] {name}: {'sopravvive' if s else 'distrutto'}")


if __name__ == '__main__':
    main()
