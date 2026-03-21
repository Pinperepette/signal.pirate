"""Un pacchetto legittimo pulito — nessun pattern sospetto."""
from setuptools import setup, find_packages

setup(
    name="my-clean-utils",
    version="1.0.0",
    description="A perfectly clean utility library",
    author="Honest Developer",
    author_email="dev@example.com",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=[
        "typing-extensions>=4.0",
    ],
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
    ],
)
