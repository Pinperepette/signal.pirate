#!/usr/bin/env python3
"""
03_ratchet_vs_static.py — Ratchet vs chiave statica: cosa succede quando ti bucano

Confronto pratico con le primitive di Signal:
- Sistema A: chiave statica (tipo Telegram chat normali, o key escrow)
- Sistema B: double ratchet (tipo Signal)

Cifratura: AES-256-CBC + HMAC-SHA256 (come Signal Protocol).
Ratchet: HMAC-SHA256 con 0x01/0x02 (come Signal Protocol).

Scenario: l'attaccante compromette la chiave al messaggio N.
Quanti messaggi puo' leggere?

Uso: python3 03_ratchet_vs_static.py
"""

from cryptography.hazmat.primitives import hashes, padding as sym_padding
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.hmac import HMAC
import os


def kdf_ratchet(chain_key):
    """
    Un passo del symmetric ratchet come Signal:
    MK = HMAC(CK, 0x01)
    CK_next = HMAC(CK, 0x02)
    """
    h_mk = HMAC(chain_key, hashes.SHA256())
    h_mk.update(b'\x01')
    mk = h_mk.finalize()

    h_ck = HMAC(chain_key, hashes.SHA256())
    h_ck.update(b'\x02')
    ck_next = h_ck.finalize()

    return ck_next, mk


def derive_enc_keys(message_key):
    """Deriva enc_key, mac_key, iv come Signal (HKDF 'WhisperMessageKeys')."""
    derived = HKDF(
        algorithm=hashes.SHA256(),
        length=80,
        salt=b'\x00' * 32,
        info=b'WhisperMessageKeys',
    ).derive(message_key)
    return derived[:32], derived[32:64], derived[64:80]


def encrypt(key, plaintext):
    """Cifra con AES-256-CBC + HMAC-SHA256 (come Signal)."""
    enc_key, mac_key, iv = derive_enc_keys(key)

    padder = sym_padding.PKCS7(128).padder()
    padded = padder.update(plaintext.encode()) + padder.finalize()

    encryptor = Cipher(algorithms.AES(enc_key), modes.CBC(iv)).encryptor()
    ct = encryptor.update(padded) + encryptor.finalize()

    h = HMAC(mac_key, hashes.SHA256())
    h.update(iv + ct)
    mac = h.finalize()

    return iv + ct + mac


def decrypt(key, blob):
    """Decifra verificando HMAC, poi AES-256-CBC."""
    enc_key, mac_key, _ = derive_enc_keys(key)

    iv = blob[:16]
    mac = blob[-32:]
    ct = blob[16:-32]

    h = HMAC(mac_key, hashes.SHA256())
    h.update(iv + ct)
    h.verify(mac)

    decryptor = Cipher(algorithms.AES(enc_key), modes.CBC(iv)).decryptor()
    padded = decryptor.update(ct) + decryptor.finalize()

    unpadder = sym_padding.PKCS7(128).unpadder()
    return (unpadder.update(padded) + unpadder.finalize()).decode()


def key_hex(k):
    return k[:6].hex()


def main():
    print()
    print("=" * 65)
    print("  SIGNAL PIRATE — RATCHET vs CHIAVE STATICA")
    print("  AES-256-CBC + HMAC-SHA256 (primitive di Signal)")
    print("=" * 65)

    N_MESSAGGI = 10
    COMPROMESSO_A = 4  # L'attaccante buca al messaggio 5 (indice 4)

    conversazione = [
        "Ciao, hai visto la notizia sulla Svezia?",
        "Si, vogliono la backdoor in Signal",
        "La deadline e' il 1 marzo",
        "Signal dice che se ne va",
        "L'esercito svedese si oppone",            # <-- compromesso qui
        "200 esperti hanno firmato contro",
        "Anche il UK ci ha provato con Apple",
        "Apple ha tolto la crittografia dal UK",
        "Gli AI agent sono il vero problema",
        "Il protocollo e' solido, gli endpoint no",
    ]

    # === SISTEMA A: Chiave statica ===
    print("\n  [SISTEMA A] CHIAVE STATICA")
    print("  " + "-" * 50)
    print("  Una chiave per tutta la sessione (tipo Telegram, key escrow)")
    print()

    static_key = os.urandom(32)
    print(f"  Chiave sessione: {key_hex(static_key)}...")
    print()

    ct_static = []
    for i, msg in enumerate(conversazione):
        ct = encrypt(static_key, msg)
        ct_static.append(ct)
        marker = "  <<<< COMPROMESSO" if i == COMPROMESSO_A else ""
        print(f"  MSG {i + 1:2d}: cifrato con {key_hex(static_key)}...{marker}")

    # Attaccante ruba la chiave al messaggio 5
    stolen_static = static_key  # E' la stessa per tutti!

    print(f"\n  Attaccante ruba la chiave al MSG {COMPROMESSO_A + 1}")
    print(f"  Chiave rubata: {key_hex(stolen_static)}...")
    print(f"  Provo a decifrare tutti i messaggi:\n")

    count_a = 0
    for i, ct in enumerate(ct_static):
        try:
            dec = decrypt(stolen_static, ct)
            print(f"    MSG {i + 1:2d}: \"{dec[:45]}\"")
            count_a += 1
        except Exception:
            print(f"    MSG {i + 1:2d}: FALLITO")

    print(f"\n  Risultato: {count_a}/{N_MESSAGGI} messaggi decifrati")
    print(f"  Passati, presenti E futuri. TUTTO esposto.")

    # === SISTEMA B: Double Ratchet ===
    print("\n\n  [SISTEMA B] DOUBLE RATCHET")
    print("  " + "-" * 50)
    print("  Una chiave diversa per ogni messaggio (tipo Signal)")
    print("  Ratchet: HMAC(CK, 0x01) / HMAC(CK, 0x02)")
    print()

    root_key = os.urandom(32)
    chain_key = root_key
    msg_keys = []
    ct_ratchet = []

    for i, msg in enumerate(conversazione):
        chain_key, mk = kdf_ratchet(chain_key)
        ct = encrypt(mk, msg)
        msg_keys.append(mk)
        ct_ratchet.append(ct)
        marker = "  <<<< COMPROMESSO" if i == COMPROMESSO_A else ""
        print(f"  MSG {i + 1:2d}: cifrato con {key_hex(mk)}...{marker}")

    # Attaccante ruba la message key del messaggio 5
    stolen_ratchet = msg_keys[COMPROMESSO_A]

    print(f"\n  Attaccante ruba la chiave al MSG {COMPROMESSO_A + 1}")
    print(f"  Chiave rubata: {key_hex(stolen_ratchet)}...")
    print(f"  Provo a decifrare tutti i messaggi:\n")

    count_b = 0
    for i, ct in enumerate(ct_ratchet):
        try:
            dec = decrypt(stolen_ratchet, ct)
            print(f"    MSG {i + 1:2d}: \"{dec[:45]}\"")
            count_b += 1
        except Exception:
            print(f"    MSG {i + 1:2d}: FALLITO")

    print(f"\n  Risultato: {count_b}/{N_MESSAGGI} messaggi decifrati")
    print(f"  Solo il messaggio compromesso. Il resto e' al sicuro.")

    # === CONFRONTO ===
    print("\n\n  [CONFRONTO] IMPATTO DELLA COMPROMISSIONE")
    print("  " + "-" * 50)

    bar_a = "#" * count_a + "." * (N_MESSAGGI - count_a)
    bar_b = "#" * count_b + "." * (N_MESSAGGI - count_b)

    print(f"""
  Messaggi esposti dopo compromissione della chiave al MSG {COMPROMESSO_A + 1}:

  Chiave statica:   [{bar_a}]  {count_a}/{N_MESSAGGI}  TUTTI
  Double ratchet:   [{bar_b}]  {count_b}/{N_MESSAGGI}  SOLO 1

  Legenda: # = esposto, . = protetto

  ┌────────────────────┬──────────────┬──────────────────┐
  │                    │ Statica      │ Double Ratchet   │
  ├────────────────────┼──────────────┼──────────────────┤
  │ Chiavi per 10 msg  │ 1            │ 10               │
  │ Msg esposti        │ {count_a:2d}           │ {count_b:2d}               │
  │ Forward secrecy    │ NO           │ SI               │
  │ Break-in recovery  │ NO           │ SI               │
  │ Costo per utente   │ Basso        │ Medio (piu' KDF) │
  │ Costo per attacco  │ 1 chiave     │ N chiavi         │
  └────────────────────┴──────────────┴──────────────────┘""")

    print("\n" + "=" * 65)
    print("  CONCLUSIONE")
    print("=" * 65)
    print("  Il Double Ratchet trasforma un singolo breach in un")
    print("  problema contenuto. La chiave statica lo trasforma in")
    print("  un disastro totale. Ecco perche' Signal funziona cosi'.")
    print("  E perche' qualsiasi backdoor (che richiede una chiave")
    print("  statica master) rompe questo modello.")
    print("=" * 65)
    print()


if __name__ == '__main__':
    main()
