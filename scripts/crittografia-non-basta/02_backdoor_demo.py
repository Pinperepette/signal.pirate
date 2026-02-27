#!/usr/bin/env python3
"""
02_backdoor_demo.py — Perche' una backdoor "solo per i buoni" non puo' esistere

Dimostrazione pratica:
1. Implementa un canale cifrato AES-256-CBC + HMAC-SHA256 (come Signal)
2. Aggiunge una "master key" governativa (key escrow)
3. Mostra che CHIUNQUE trovi la master key decifra tutto
4. Simula il leak della master key
5. Confronta: con backdoor vs senza

La matematica non distingue tra "polizia" e "attaccante".
Signal usa libsignal (Rust). Noi usiamo cryptography (Python/OpenSSL).
Stesse primitive, stessa dimostrazione.

Uso: python3 02_backdoor_demo.py
"""

from cryptography.hazmat.primitives import hashes, padding as sym_padding
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.hmac import HMAC
import os


def derive_enc_keys(message_key):
    """Deriva enc_key (32B), mac_key (32B), iv (16B) come Signal."""
    derived = HKDF(
        algorithm=hashes.SHA256(),
        length=80,
        salt=b'\x00' * 32,
        info=b'WhisperMessageKeys',
    ).derive(message_key)
    return derived[:32], derived[32:64], derived[64:80]


def encrypt_cbc_hmac(key, plaintext):
    """Cifra con AES-256-CBC + HMAC-SHA256 (come Signal)."""
    enc_key, mac_key, iv = derive_enc_keys(key)

    padder = sym_padding.PKCS7(128).padder()
    padded = padder.update(plaintext.encode()) + padder.finalize()

    cipher = Cipher(algorithms.AES(enc_key), modes.CBC(iv))
    ct = cipher.encryptor().update(padded) + cipher.encryptor().finalize()

    # Serve ricreare l'encryptor perche' e' gia' finalizzato
    encryptor = Cipher(algorithms.AES(enc_key), modes.CBC(iv)).encryptor()
    ct = encryptor.update(padded) + encryptor.finalize()

    h = HMAC(mac_key, hashes.SHA256())
    h.update(iv + ct)
    mac = h.finalize()

    return iv + ct + mac


def decrypt_cbc_hmac(key, blob):
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


def encrypt_with_backdoor(user_key, master_key, plaintext):
    """
    Cifratura con backdoor: il messaggio viene cifrato DUE volte.
    - Con la chiave dell'utente (come al solito)
    - Con la master key governativa
    Chiunque abbia UNA delle due chiavi puo' leggere.
    """
    ct_user = encrypt_cbc_hmac(user_key, plaintext)
    ct_master = encrypt_cbc_hmac(master_key, plaintext)

    len_user = len(ct_user)
    return len_user.to_bytes(4, 'big') + ct_user + ct_master


def decrypt_with_user_key(user_key, blob):
    """Decifra con la chiave utente (percorso normale)."""
    len_user = int.from_bytes(blob[:4], 'big')
    return decrypt_cbc_hmac(user_key, blob[4:4 + len_user])


def decrypt_with_master_key(master_key, blob):
    """Decifra con la master key (percorso backdoor)."""
    len_user = int.from_bytes(blob[:4], 'big')
    return decrypt_cbc_hmac(master_key, blob[4 + len_user:])


def key_hex(k):
    return k[:8].hex()


def main():
    print()
    print("=" * 65)
    print("  SIGNAL PIRATE — PERCHE' UNA BACKDOOR NON PUO' FUNZIONARE")
    print("  AES-256-CBC + HMAC-SHA256 (stesse primitive di Signal)")
    print("=" * 65)

    # === FASE 1: Canale normale (come Signal) ===
    print("\n  [FASE 1] CANALE NORMALE — SENZA BACKDOOR")
    print("  " + "-" * 50)

    alice_key = os.urandom(32)
    print(f"  Chiave Alice:  {key_hex(alice_key)}...")

    messaggi = [
        "La legge svedese entra in vigore il 1 marzo",
        "Signal preferisce andarsene che mettere una backdoor",
        "L'esercito svedese si oppone alla legge del proprio governo",
    ]

    encrypted_normal = []
    for i, msg in enumerate(messaggi):
        ct = encrypt_cbc_hmac(alice_key, msg)
        encrypted_normal.append(ct)
        decrypted = decrypt_cbc_hmac(alice_key, ct)
        print(f"\n  MSG {i + 1}:")
        print(f"    Plaintext: \"{msg}\"")
        print(f"    IV:        {ct[:16].hex()[:16]}...")
        print(f"    AES-CBC:   {ct[16:-32][:8].hex()}... ({len(ct[16:-32])} byte)")
        print(f"    HMAC:      {ct[-32:][:8].hex()}...")
        print(f"    Totale:    {len(ct)} byte")
        print(f"    Decifrato: OK")

    print(f"\n  Solo chi ha la chiave di Alice puo' leggere.")
    print(f"  Nessun altro percorso. Nessuna scorciatoia.")

    # === FASE 2: Aggiungiamo la "master key governativa" ===
    print("\n\n  [FASE 2] AGGIUNGIAMO LA BACKDOOR (KEY ESCROW)")
    print("  " + "-" * 50)
    print("  Il governo chiede: 'Dateci una master key. Solo noi la useremo.'")

    master_key = os.urandom(32)
    print(f"\n  Master key:    {key_hex(master_key)}...")
    print(f"  Chiave Alice:  {key_hex(alice_key)}...")
    print(f"  (due chiavi diverse, stesso messaggio)")

    encrypted_backdoor = []
    for i, msg in enumerate(messaggi):
        ct = encrypt_with_backdoor(alice_key, master_key, msg)
        encrypted_backdoor.append(ct)

        dec_user = decrypt_with_user_key(alice_key, ct)
        dec_master = decrypt_with_master_key(master_key, ct)

        print(f"\n  MSG {i + 1}: \"{msg[:50]}\"")
        print(f"    Blob:            {len(ct)} byte (vs {len(encrypted_normal[i])} senza backdoor)")
        print(f"    Con chiave user: \"{dec_user[:50]}\"")
        print(f"    Con master key:  \"{dec_master[:50]}\"")

    overhead = len(encrypted_backdoor[0]) - len(encrypted_normal[0])
    print(f"\n  Overhead per backdoor: +{overhead} byte per messaggio")
    print(f"  ({overhead} byte = iv + ciphertext + HMAC duplicati + 4 byte header)")

    # === FASE 3: Il leak inevitabile ===
    print("\n\n  [FASE 3] IL LEAK INEVITABILE")
    print("  " + "-" * 50)
    print("  La master key viene compromessa.")
    print("  Non e' se. E' quando.")
    print()

    scenari = [
        ("Insider threat",     "Un dipendente del governo la copia su una USB"),
        ("Server breach",      "Il key escrow server viene bucato"),
        ("Supply chain",       "Il firmware del HSM ha una vulnerabilita'"),
        ("Crypto AG 2.0",      "Un altro governo la ottiene tramite spionaggio"),
        ("Brute force futuro", "Computer quantistici o avanzamenti matematici"),
    ]

    for scenario, desc in scenari:
        print(f"  [{scenario}]")
        print(f"    {desc}")
        print(f"    Risultato: TUTTI i messaggi di TUTTI gli utenti esposti")
        print()

    print("  Simulazione: un attaccante trova la master key")
    print(f"  Master key rubata: {key_hex(master_key)}...")
    print()

    for i, ct in enumerate(encrypted_backdoor):
        stolen = decrypt_with_master_key(master_key, ct)
        print(f"  MSG {i + 1} decifrato dall'attaccante: \"{stolen}\"")

    print(f"\n  L'attaccante legge TUTTO. La matematica non distingue")
    print(f"  tra 'polizia svedese' e 'hacker russo'.")

    # === FASE 4: Confronto finale ===
    print("\n\n  [FASE 4] CONFRONTO FINALE")
    print("  " + "-" * 50)

    print(f"""
  ┌─────────────────────────┬──────────────┬──────────────────┐
  │                         │ Senza        │ Con backdoor     │
  │                         │ backdoor     │ (key escrow)     │
  ├─────────────────────────┼──────────────┼──────────────────┤
  │ Chi puo' leggere        │ Solo Alice   │ Alice + governo  │
  │                         │ e Bob        │ + chi ruba la MK │
  ├─────────────────────────┼──────────────┼──────────────────┤
  │ Forward secrecy         │ SI           │ NO (MK statica)  │
  ├─────────────────────────┼──────────────┼──────────────────┤
  │ Overhead per messaggio  │ 0            │ +{overhead} byte        │
  ├─────────────────────────┼──────────────┼──────────────────┤
  │ Superficie d'attacco    │ 1 chiave     │ 2 chiavi         │
  ├─────────────────────────┼──────────────┼──────────────────┤
  │ Impatto di un breach    │ 1 sessione   │ TUTTI gli utenti │
  ├─────────────────────────┼──────────────┼──────────────────┤
  │ Precedenti storici      │ -            │ Clipper, DECDRBG │
  │                         │              │ Juniper, CryptoAG│
  └─────────────────────────┴──────────────┴──────────────────┘""")

    print("\n" + "=" * 65)
    print("  RISULTATO")
    print("=" * 65)
    print("  Una backdoor 'solo per i buoni' e' un ossimoro crittografico.")
    print("  Se esiste un secondo percorso per decifrare, quel percorso")
    print("  esiste per chiunque lo trovi. La matematica non fa sconti.")
    print("  P(leak in t anni) = 1 - (1-p)^t  -->  tende a 1.")
    print("=" * 65)
    print()


if __name__ == '__main__':
    main()
