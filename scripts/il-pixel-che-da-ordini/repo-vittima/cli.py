#!/usr/bin/env python3
"""acme-cli — a tiny command-line tool."""
import argparse

__version__ = "0.3.2"


def build_parser():
    p = argparse.ArgumentParser(prog="acme-cli")
    p.add_argument("name", nargs="?", default="world")
    return p


def main():
    args = build_parser().parse_args()
    print(f"hello, {args.name}")


if __name__ == "__main__":
    main()
