#!/usr/bin/env python3
"""
Genera una cartella Download finta ma realistica, per provare organize.py
senza toccare la cartella vera. Include i casi che contano:
  - file dal nome ovvio e dal nome inutile
  - documenti veri (testo) e "binari" (foto/installer/zip simulati)
  - duplicati ESATTI (stesso contenuto, nome diverso) per la dedup via hash
  - un paio di file ambigui che dovrebbero finire in quarantena
"""

import os
import shutil
import sys

DEST = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "sandbox-downloads")

# (nome, contenuto). Per i "binari" mettiamo un header plausibile: nel demo
# basta a non farli sembrare testo; nella realta' i veri PDF/JPG sono binari.
TEXT_FILES = [
    ("fattura_amazon_marzo.pdf", "FATTURA Amazon EU - n. 2024-0312 - Totale 89,90 EUR - IVA 22%"),
    ("Fattura_Enel_2024_01.pdf", "Enel Energia - Bolletta luce gennaio 2024 - importo 142,33 EUR"),
    ("fattura (2).pdf", "Fattura Vodafone - linea mobile - 19,99 EUR - periodo feb 2024"),
    ("contratto_affitto.pdf", "CONTRATTO DI LOCAZIONE ad uso abitativo tra le parti, durata 4+4 anni"),
    ("referto_medico.pdf", "REFERTO - Esami ematochimici - emocromo, glicemia, colesterolo. Paziente:"),
    ("busta_paga_marzo.pdf", "CEDOLINO PAGA marzo 2024 - retribuzione lorda, netto in busta, IRPEF"),
    ("curriculum.pdf", "Curriculum Vitae - esperienze professionali, competenze, istruzione"),
    ("note_riunione.txt", "Riunione 12/03: decidere roadmap Q2, assegnare owner, prossimi step."),
    ("data.csv", "id,nome,valore\n1,alfa,10\n2,beta,20\n3,gamma,30\n"),
    ("script.py", "import sys\n\ndef main():\n    print('hello')\n\nif __name__=='__main__':\n    main()\n"),
    ("index.html", "<!doctype html><html><head><title>Pagina</title></head><body>ciao</body></html>"),
    ("README.md", "# Progetto X\n\nIstruzioni di installazione e uso del progetto.\n"),
    # file dal nome inutile ma contenuto chiaro -> il content peek aiuta
    ("scan0007.pdf", "Spett.le condominio, si comunica la quota straordinaria deliberata in assemblea"),
    # file davvero ambigui -> dovrebbero andare in quarantena
    ("untitled.txt", "asdf\nqwerty\n...\n"),
    ("appunti.txt", "ricordati"),
]

# "Binari" simulati: header non-testo + nome che porta tutto il segnale.
BIN_FILES = {
    "Schermata 2024-03-11 alle 18.42.png": b"\x89PNG\r\n\x1a\n",
    "Screenshot 2023-12-01.png": b"\x89PNG\r\n\x1a\n",
    "IMG_4471.jpg": b"\xff\xd8\xff\xe0",
    "IMG_4472.jpg": b"\xff\xd8\xff\xe0",
    "foto_vacanza.jpeg": b"\xff\xd8\xff\xe0",
    "GoogleChrome.dmg": b"\x00\x00\x00\x00koly",
    "Zoom.pkg": b"\x00\x00xar!",
    "setup.exe": b"MZ\x90\x00",
    "progetto.zip": b"PK\x03\x04",
    "backup_2023.zip": b"PK\x03\x04",
    "song.mp3": b"ID3\x04\x00",
    "clip_compleanno.mp4": b"\x00\x00\x00\x18ftyp",
    "libro_sql.epub": b"PK\x03\x04epub",
    # niente nome utile, niente estensione, contenuto opaco: deve finire
    # in quarantena dopo il retry, non essere indovinato a caso.
    "qzx7": b"\x01\x02\x03\x04\x05",
}


def main():
    if os.path.exists(DEST):
        shutil.rmtree(DEST)
    os.makedirs(DEST)

    for name, content in TEXT_FILES:
        with open(os.path.join(DEST, name), "w") as f:
            f.write(content + "\n")

    for name, header in BIN_FILES.items():
        with open(os.path.join(DEST, name), "wb") as f:
            f.write(header + os.urandom(64))

    # Duplicati ESATTI (byte identici, nome diverso): li deve prendere l'hash.
    shutil.copyfile(os.path.join(DEST, "fattura_amazon_marzo.pdf"),
                    os.path.join(DEST, "fattura_amazon_COPIA.pdf"))
    shutil.copyfile(os.path.join(DEST, "progetto.zip"),
                    os.path.join(DEST, "progetto (1).zip"))

    n = len(os.listdir(DEST))
    print("Sandbox creata in: %s" % DEST)
    print("File generati: %d (di cui 2 duplicati esatti da deduplicare)" % n)


if __name__ == "__main__":
    main()
