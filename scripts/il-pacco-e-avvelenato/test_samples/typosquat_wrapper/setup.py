"""Campione malevolo: wrapper typosquatting che importa il pacchetto legittimo
e aggiunge un payload silenzioso. L'utente non nota nulla perché tutto funziona."""
from setuptools import setup

setup(
    name="requestes",  # typosquatting: requests
    version="2.31.0",
    description="HTTP library for Python",
    install_requires=["requests==2.31.0"],  # installa il legittimo come dipendenza
)
