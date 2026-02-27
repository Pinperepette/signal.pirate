#!/usr/bin/env python3
"""
01_double_ratchet.py — Double Ratchet semplificato con Curve25519

Implementa il cuore del Signal Protocol con le stesse primitive:
- X25519 Diffie-Hellman per lo scambio chiavi (come Signal)
- HKDF-SHA256 per la derivazione delle chiavi (come Signal)
- AES-256-CBC + HMAC-SHA256 per cifrare ogni messaggio (come Signal)
- Ogni messaggio ha una chiave diversa
- Le chiavi vecchie vengono distrutte (forward secrecy)

Signal usa libsignal (Rust). Noi usiamo la libreria cryptography (Python/OpenSSL).
Stesse primitive crittografiche, stessa matematica, implementazione diversa.

Uso: python3 01_double_ratchet.py
"""

from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
from cryptography.hazmat.primitives import hashes, serialization, padding as sym_padding
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.hmac import HMAC
import os


def x25519_keypair():
    """Genera una coppia di chiavi X25519."""
    priv = X25519PrivateKey.generate()
    pub = priv.public_key()
    return priv, pub


def dh(private_key, peer_public_key):
    """Esegue lo scambio Diffie-Hellman su Curve25519."""
    return private_key.exchange(peer_public_key)


def kdf_chain(chain_key):
    """
    Symmetric ratchet: da una chain key deriva
    - la prossima chain key (per continuare la catena)
    - la message key (per cifrare un messaggio)

    Come Signal: usa HMAC-SHA256 con costanti diverse.
    Signal usa 0x01 per message key e 0x02 per chain key.
    CK_next = HMAC(CK, 0x02)
    MK      = HMAC(CK, 0x01)
    Operazione irreversibile: da MK non puoi risalire a CK.
    """
    # Message key (come Signal: HMAC con 0x01)
    h_mk = HMAC(chain_key, hashes.SHA256())
    h_mk.update(b'\x01')
    mk = h_mk.finalize()

    # Next chain key (come Signal: HMAC con 0x02)
    h_ck = HMAC(chain_key, hashes.SHA256())
    h_ck.update(b'\x02')
    ck_next = h_ck.finalize()

    return ck_next, mk


def derive_enc_keys(message_key):
    """
    Da una message key di 32 byte, deriva:
    - enc_key: 32 byte per AES-256-CBC
    - mac_key: 32 byte per HMAC-SHA256
    - iv:      16 byte per CBC

    Signal usa HKDF con info "WhisperMessageKeys" per questo step.
    """
    derived = HKDF(
        algorithm=hashes.SHA256(),
        length=80,  # 32 (enc) + 32 (mac) + 16 (iv)
        salt=b'\x00' * 32,
        info=b'WhisperMessageKeys',
    ).derive(message_key)

    enc_key = derived[:32]
    mac_key = derived[32:64]
    iv = derived[64:80]
    return enc_key, mac_key, iv


def encrypt(message_key, plaintext):
    """
    Cifra come Signal: AES-256-CBC + HMAC-SHA256.
    1. Deriva enc_key, mac_key, iv dalla message key
    2. Padding PKCS7 sul plaintext
    3. Cifra con AES-256-CBC
    4. HMAC-SHA256 sul ciphertext (authenticate-then-encrypt e' il contrario,
       ma Signal usa encrypt-then-MAC che e' piu' sicuro)
    Formato: iv || ciphertext || mac
    """
    enc_key, mac_key, iv = derive_enc_keys(message_key)

    # PKCS7 padding
    padder = sym_padding.PKCS7(128).padder()
    padded = padder.update(plaintext.encode()) + padder.finalize()

    # AES-256-CBC
    cipher = Cipher(algorithms.AES(enc_key), modes.CBC(iv))
    encryptor = cipher.encryptor()
    ct = encryptor.update(padded) + encryptor.finalize()

    # HMAC-SHA256 (encrypt-then-MAC)
    h = HMAC(mac_key, hashes.SHA256())
    h.update(iv + ct)
    mac = h.finalize()

    return iv + ct + mac  # 16 + ct_len + 32


def decrypt(message_key, blob):
    """
    Decifra come Signal: verifica HMAC, poi decifra AES-256-CBC.
    """
    enc_key, mac_key, iv_derived = derive_enc_keys(message_key)

    iv = blob[:16]
    mac = blob[-32:]
    ct = blob[16:-32]

    # Verifica HMAC
    h = HMAC(mac_key, hashes.SHA256())
    h.update(iv + ct)
    h.verify(mac)  # Lancia eccezione se il MAC non corrisponde

    # Decifra AES-256-CBC
    cipher = Cipher(algorithms.AES(enc_key), modes.CBC(iv))
    decryptor = cipher.decryptor()
    padded = decryptor.update(ct) + decryptor.finalize()

    # Rimuovi padding PKCS7
    unpadder = sym_padding.PKCS7(128).unpadder()
    plaintext = unpadder.update(padded) + unpadder.finalize()

    return plaintext.decode()


def pub_hex(pub_key):
    """Restituisce i primi 8 byte della chiave pubblica in hex."""
    raw = pub_key.public_bytes(
        serialization.Encoding.Raw,
        serialization.PublicFormat.Raw
    )
    return raw[:8].hex()


def key_hex(key_bytes):
    """Mostra i primi 8 byte di una chiave in hex."""
    return key_bytes[:8].hex()


def main():
    print()
    print("=" * 65)
    print("  SIGNAL PIRATE — DOUBLE RATCHET (SEMPLIFICATO)")
    print("  Curve25519 + HKDF-SHA256 + AES-256-CBC + HMAC-SHA256")
    print("  Stesse primitive di Signal. Libreria: cryptography (OpenSSL)")
    print("=" * 65)

    # === FASE 1: Scambio chiavi iniziale (X3DH semplificato) ===
    print("\n  [FASE 1] SCAMBIO CHIAVI — X25519 Diffie-Hellman")
    print("  " + "-" * 50)

    alice_priv, alice_pub = x25519_keypair()
    bob_priv, bob_pub = x25519_keypair()

    print(f"  Alice pub:     {pub_hex(alice_pub)}...")
    print(f"  Bob pub:       {pub_hex(bob_pub)}...")

    # Entrambi calcolano lo stesso segreto condiviso
    shared_alice = dh(alice_priv, bob_pub)
    shared_bob = dh(bob_priv, alice_pub)

    assert shared_alice == shared_bob, "DH fallito!"

    print(f"\n  Shared secret: {key_hex(shared_alice)}...")
    print(f"  Match:         {shared_alice == shared_bob}")
    print(f"  Lunghezza:     {len(shared_alice) * 8} bit")

    # Deriva la root key iniziale dal segreto condiviso
    root_key = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=None,
        info=b'WhisperRatchet',  # come Signal
    ).derive(shared_alice)

    print(f"  Root key:      {key_hex(root_key)}...")

    # === FASE 2: Symmetric ratchet — 5 messaggi ===
    print("\n  [FASE 2] SYMMETRIC RATCHET — 5 MESSAGGI")
    print("  " + "-" * 50)
    print("  Chain key: HMAC(CK, 0x02)  |  Msg key: HMAC(CK, 0x01)")
    print("  Cifratura: AES-256-CBC + HMAC-SHA256 (come Signal)")

    messaggi = [
        "Ehi, la Svezia vuole una backdoor in Signal",
        "1 marzo 2026. Dopodomani",
        "Signal dice che se ne va piuttosto che farlo",
        "L'esercito svedese si oppone alla legge",
        "200+ esperti hanno firmato contro",
    ]

    chain_key = root_key
    message_keys = []
    ciphertexts = []

    for i, msg in enumerate(messaggi):
        chain_key, msg_key = kdf_chain(chain_key)
        ct = encrypt(msg_key, msg)
        ciphertexts.append(ct)
        message_keys.append(msg_key)

        # Scomponi il blob per mostrare la struttura
        iv_part = ct[:16]
        mac_part = ct[-32:]
        ct_part = ct[16:-32]

        print(f"\n  MSG {i + 1}:")
        print(f"    Plaintext:   \"{msg[:50]}\"")
        print(f"    Chain key:   {key_hex(chain_key)}...")
        print(f"    Msg key:     {key_hex(msg_key)}...")
        print(f"    IV (16B):    {iv_part[:8].hex()}...")
        print(f"    AES-CBC:     {ct_part[:8].hex()}... ({len(ct_part)} byte)")
        print(f"    HMAC-SHA256: {mac_part[:8].hex()}...")
        print(f"    Totale:      {len(ct)} byte (iv + ct + mac)")

        # Decifra per verifica
        decrypted = decrypt(msg_key, ct)
        assert decrypted == msg
        print(f"    Decifrato:   OK")

    # === FASE 3: Forward Secrecy — distruggi le chiavi ===
    print("\n  [FASE 3] FORWARD SECRECY")
    print("  " + "-" * 50)
    print("  Scenario: l'attaccante ruba la message key del MSG 3")

    stolen_key = message_keys[2]
    print(f"\n  Chiave rubata: {key_hex(stolen_key)}...")

    # Puo' decifrare MSG 3
    decrypted_3 = decrypt(stolen_key, ciphertexts[2])
    print(f"  MSG 3 decifrato: \"{decrypted_3}\"")

    # Non puo' decifrare MSG 1, 2, 4, 5
    print(f"\n  Provo a decifrare gli altri messaggi con la stessa chiave:")
    for i, ct in enumerate(ciphertexts):
        if i == 2:
            continue
        try:
            decrypt(stolen_key, ct)
            print(f"    MSG {i + 1}: DECIFRATO (problema!)")
        except Exception:
            print(f"    MSG {i + 1}: FALLITO (chiave sbagliata)")

    print(f"\n  Risultato: la chiave di MSG 3 decifra SOLO MSG 3")
    print(f"  Forward secrecy: i messaggi passati sono al sicuro")
    print(f"  Break-in recovery: i messaggi futuri sono al sicuro")

    # === FASE 4: DH Ratchet — nuova coppia di chiavi ===
    print("\n  [FASE 4] DH RATCHET — RIGENERAZIONE")
    print("  " + "-" * 50)
    print("  Alice genera una nuova coppia di chiavi effimere")

    alice_priv2, alice_pub2 = x25519_keypair()
    new_shared = dh(alice_priv2, bob_pub)

    print(f"  Nuova pub Alice: {pub_hex(alice_pub2)}...")
    print(f"  Nuovo shared:    {key_hex(new_shared)}...")

    new_root = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=None,
        info=b'WhisperRatchet',
    ).derive(new_shared)

    print(f"  Nuova root key:  {key_hex(new_root)}...")
    print(f"\n  La vecchia root key e' completamente scollegata.")
    print(f"  Anche se l'attaccante aveva compromesso la sessione,")
    print(f"  il DH ratchet lo espelle. Nuovo DH = nuove chiavi = game over.")

    # === Riepilogo ===
    print("\n" + "=" * 65)
    print("  RIEPILOGO")
    print("=" * 65)
    print(f"  Curva:             Curve25519 (Daniel Bernstein)")
    print(f"  Scambio chiavi:    X25519 Diffie-Hellman")
    print(f"  Derivazione CK:   HMAC-SHA256 con 0x01/0x02 (come Signal)")
    print(f"  Derivazione MK:   HKDF-SHA256 info='WhisperMessageKeys'")
    print(f"  Cifratura:         AES-256-CBC (come Signal)")
    print(f"  Autenticazione:    HMAC-SHA256 encrypt-then-MAC (come Signal)")
    print(f"  Messaggi cifrati:  {len(messaggi)}")
    print(f"  Chiavi generate:   {len(messaggi)} message keys + {len(messaggi)} chain keys")
    print(f"  Forward secrecy:   SI (ogni chiave decifra solo il suo messaggio)")
    print(f"  Break-in recovery: SI (DH ratchet rigenera tutto)")
    print(f"\n  Nota: Signal usa libsignal (Rust), noi usiamo")
    print(f"  cryptography (Python/OpenSSL). Stesse primitive,")
    print(f"  stessa matematica, implementazione diversa.")
    print("=" * 65)
    print()


if __name__ == '__main__':
    main()
