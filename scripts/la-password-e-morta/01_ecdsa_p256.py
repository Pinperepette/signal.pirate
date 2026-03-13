#!/usr/bin/env python3
"""
01_ecdsa_p256.py — ECDSA P-256: keypair, firma, verifica, replay, phishing, nonce riusato (PS3)

Stessa primitiva crittografica che usa il tuo telefono
quando fai login con una passkey (WebAuthn/FIDO2).

Prerequisiti:
    pip install cryptography

Uso:
    python 01_ecdsa_p256.py
"""

import hashlib
import os
import secrets
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature
from cryptography.exceptions import InvalidSignature


def separator(title):
    print(f'\n{"=" * 60}')
    print(f'  {title}')
    print(f'{"=" * 60}\n')


# ============================================================
#  1. Generazione keypair ECDSA P-256
# ============================================================
separator('1. Generazione keypair ECDSA P-256')

private_key = ec.generate_private_key(ec.SECP256R1())
public_key = private_key.public_key()

# Mostra i numeri
private_numbers = private_key.private_numbers()
public_numbers = private_numbers.public_numbers

print(f'Curva: {public_numbers.curve.name}')
print(f'Chiave privata d: {private_numbers.private_value:064x}')
print(f'Chiave pubblica Q.x: {public_numbers.x:064x}')
print(f'Chiave pubblica Q.y: {public_numbers.y:064x}')
print(f'\nd e\' un numero casuale di 256 bit.')
print(f'Q = d * G (moltiplicazione scalare sul gruppo della curva)')
print(f'Dato Q e G, trovare d e\' computazionalmente impossibile (ECDLP).')


# ============================================================
#  2. Firma di un challenge (come fa WebAuthn)
# ============================================================
separator('2. Firma di un challenge')

# Simula il challenge del server (32 byte random, come WebAuthn)
challenge = os.urandom(32)
print(f'Challenge (hex): {challenge.hex()}')
print(f'Challenge (base64 sarebbe nel clientDataJSON)')

# Firma con la chiave privata
signature = private_key.sign(challenge, ec.ECDSA(hashes.SHA256()))

# Decodifica la firma DER per mostrare (r, s)
r, s = decode_dss_signature(signature)
print(f'\nFirma ECDSA:')
print(f'  r = {r:064x}')
print(f'  s = {s:064x}')
print(f'\nLa firma e\' calcolata come:')
print(f'  h = SHA-256(challenge)')
print(f'  k = nonce casuale')
print(f'  R = k * G, r = R.x mod n')
print(f'  s = k^(-1) * (h + r*d) mod n')


# ============================================================
#  3. Verifica della firma (come fa il server)
# ============================================================
separator('3. Verifica della firma')

try:
    public_key.verify(signature, challenge, ec.ECDSA(hashes.SHA256()))
    print('Firma VALIDA.')
    print('Il server ha verificato usando solo la chiave pubblica Q.')
    print('Non ha mai toccato la chiave privata d.')
except InvalidSignature:
    print('Firma INVALIDA.')


# ============================================================
#  4. Replay attack: firma vecchia su challenge nuovo
# ============================================================
separator('4. Replay attack (fallito)')

new_challenge = os.urandom(32)
print(f'Challenge originale: {challenge.hex()[:32]}...')
print(f'Nuovo challenge:     {new_challenge.hex()[:32]}...')
print(f'\nL\'attaccante intercetta la firma e prova a riusarla')
print(f'sul nuovo challenge...')

try:
    public_key.verify(signature, new_challenge, ec.ECDSA(hashes.SHA256()))
    print('Firma VALIDA. (non dovrebbe succedere)')
except InvalidSignature:
    print('Firma INVALIDA. Replay attack neutralizzato.')
    print('La firma e\' specifica per quel challenge.')
    print('Un challenge diverso = firma diversa. Sempre.')


# ============================================================
#  5. Phishing: dominio sbagliato (origin binding)
# ============================================================
separator('5. Phishing: origin binding')

# Simula clientDataJSON con origin corretto
import json

client_data_real = json.dumps({
    'type': 'webauthn.get',
    'challenge': challenge.hex(),
    'origin': 'https://bank.example.com',
    'crossOrigin': False
}).encode()

client_data_fake = json.dumps({
    'type': 'webauthn.get',
    'challenge': challenge.hex(),
    'origin': 'https://banlk.example.com',  # nota: L al posto di K
    'crossOrigin': False
}).encode()

# Firma il clientDataJSON reale
sig_real = private_key.sign(client_data_real, ec.ECDSA(hashes.SHA256()))
print(f'Origin reale: https://bank.example.com')
print(f'Origin falso: https://banlk.example.com')

# Verifica con il dato reale
try:
    public_key.verify(sig_real, client_data_real, ec.ECDSA(hashes.SHA256()))
    print(f'\nVerifica origin reale: VALIDA')
except InvalidSignature:
    print(f'\nVerifica origin reale: INVALIDA')

# Verifica con il dato falso (origin diverso = hash diverso = firma invalida)
try:
    public_key.verify(sig_real, client_data_fake, ec.ECDSA(hashes.SHA256()))
    print(f'Verifica origin falso: VALIDA (non dovrebbe succedere)')
except InvalidSignature:
    print(f'Verifica origin falso: INVALIDA. Phishing neutralizzato.')
    print(f'La firma include l\'origin. Dominio sbagliato = firma sbagliata.')


# ============================================================
#  6. Nonce riusato: il caso Sony PS3 (2010)
# ============================================================
separator('6. Nonce riusato: il caso Sony PS3')

print('Nel 2010 fail0verflow ha estratto la chiave privata della PS3')
print('perche\' Sony usava un nonce k fisso per ogni firma ECDSA.')
print('')
print('Dimostrazione: se k e\' lo stesso per due firme diverse,')
print('la chiave privata si calcola con semplice algebra.\n')

# Parametri della curva P-256
curve_order = 0xFFFFFFFF00000000FFFFFFFFFFFFFFFFBCE6FAADA7179E84F3B9CAC2FC632551

# Genera una chiave privata per la demo
d_demo = secrets.randbelow(curve_order - 1) + 1
k_fixed = secrets.randbelow(curve_order - 1) + 1  # nonce fisso (l'errore di Sony)

# Calcola R = k * G (usiamo la libreria per la moltiplicazione scalare)
demo_privkey = ec.derive_private_key(d_demo, ec.SECP256R1())

# Due messaggi diversi
m1 = b'messaggio 1: aggiornamento firmware PS3'
m2 = b'messaggio 2: nuovo gioco certificato'

h1 = int.from_bytes(hashlib.sha256(m1).digest(), 'big')
h2 = int.from_bytes(hashlib.sha256(m2).digest(), 'big')

# Calcola R = k * G per ottenere r
k_as_key = ec.derive_private_key(k_fixed, ec.SECP256R1())
r = k_as_key.public_key().public_numbers().x % curve_order

# Calcola le due firme con lo stesso k
def mod_inv(a, m):
    """Inverso modulare con algoritmo esteso di Euclide."""
    if a < 0:
        a = a % m
    g, x, _ = extended_gcd(a, m)
    if g != 1:
        raise ValueError('Inverso modulare non esiste')
    return x % m

def extended_gcd(a, b):
    if a == 0:
        return b, 0, 1
    g, x, y = extended_gcd(b % a, a)
    return g, y - (b // a) * x, x

k_inv = mod_inv(k_fixed, curve_order)

s1 = (k_inv * (h1 + r * d_demo)) % curve_order
s2 = (k_inv * (h2 + r * d_demo)) % curve_order

print(f'Firma 1: r = {r:064x}')
print(f'         s1 = {s1:064x}')
print(f'Firma 2: r = {r:064x}')
print(f'         s2 = {s2:064x}')
print(f'\nNota: r e\' uguale in entrambe le firme (stesso k).')
print(f'Questo e\' il segnale che il nonce e\' stato riusato.\n')

# L'attaccante calcola k dalla differenza delle firme:
# s1 - s2 = k^(-1) * (h1 - h2) mod n
# k = (h1 - h2) * (s1 - s2)^(-1) mod n
s_diff = (s1 - s2) % curve_order
h_diff = (h1 - h2) % curve_order
k_recovered = (h_diff * mod_inv(s_diff, curve_order)) % curve_order

print(f'k originale:  {k_fixed:064x}')
print(f'k recuperato: {k_recovered:064x}')
print(f'Match: {k_fixed == k_recovered}')

# Con k noto, calcola la chiave privata:
# d = (s * k - h) * r^(-1) mod n
r_inv = mod_inv(r, curve_order)
d_recovered = ((s1 * k_recovered - h1) * r_inv) % curve_order

print(f'\nChiave privata originale:  {d_demo:064x}')
print(f'Chiave privata recuperata: {d_recovered:064x}')
print(f'Match: {d_demo == d_recovered}')

if d_demo == d_recovered:
    print(f'\nChiave privata estratta con successo.')
    print(f'Un singolo nonce riusato = game over.')
    print(f'Per questo ogni firma WebAuthn usa un k casuale diverso,')
    print(f'generato dal Secure Enclave con un CSPRNG hardware.')
else:
    print(f'\nErrore nel calcolo (non dovrebbe succedere).')


# ============================================================
#  Riepilogo
# ============================================================
separator('Riepilogo')

print('ECDSA P-256: la stessa crittografia delle passkey WebAuthn.')
print('')
print('1. Keypair: d (privata, nel Secure Enclave) e Q = d*G (pubblica, sul server)')
print('2. Firma: il Secure Enclave firma il challenge con d, produce (r, s)')
print('3. Verifica: il server verifica con Q. Non tocca mai d')
print('4. Replay: firma legata al challenge. Challenge diverso = firma inutile')
print('5. Phishing: firma include l\'origin. Dominio sbagliato = verifica fallita')
print('6. Nonce: mai riusare k. Sony l\'ha fatto e ha perso la PS3')
