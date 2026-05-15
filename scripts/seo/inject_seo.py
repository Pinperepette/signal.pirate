#!/usr/bin/env python3
"""
Inietta tag SEO (OpenGraph, Twitter Card, JSON-LD Article) in tutti gli articoli.
Idempotente: rileva il marker <!-- seo:auto --> e sostituisce il blocco.

Uso:
    python3 inject_seo.py                # processa tutti
    python3 inject_seo.py --one FILE     # processa un singolo articolo
    python3 inject_seo.py --dry-run      # mostra solo cosa cambierebbe
"""
import argparse
import html
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARTICOLI_DIR = ROOT / "articoli"
INDEX_HTML = ROOT / "index.html"
SITE_URL = "https://pinperepette.github.io/signal.pirate"
OG_IMAGE = f"{SITE_URL}/assets/og-image.jpg"
OG_IMAGE_W = 1200
OG_IMAGE_H = 800
AUTHOR = "Andrea Amani"
SITE_NAME = "Signal Pirate"

SEO_BEGIN = "<!-- seo:auto -->"
SEO_END = "<!-- /seo:auto -->"


def parse_index_dates() -> dict[str, str]:
    """Estrae la mappa {filename: YYYY-MM-DD} dalle card di index.html."""
    text = INDEX_HTML.read_text(encoding="utf-8")
    pattern = re.compile(
        r'<a href="articoli/([^"]+)"[^>]*class="article-card"[^>]*>.*?'
        r'<div class="article-card-date">([^<]+)</div>',
        re.DOTALL,
    )
    return {m.group(1): m.group(2).strip() for m in pattern.finditer(text)}


def extract_meta(html_text: str) -> tuple[str, str]:
    """Estrae title e description dal <head> di un articolo."""
    title_match = re.search(r"<title>([^<]+)</title>", html_text)
    desc_match = re.search(
        r'<meta\s+name="description"\s+content="([^"]+)"', html_text
    )
    if not title_match or not desc_match:
        raise ValueError("Manca <title> o <meta description>")
    title = title_match.group(1).strip()
    if title.endswith(f"| {SITE_NAME}"):
        title = title[: -len(f"| {SITE_NAME}")].strip()
    return title, desc_match.group(1).strip()


def build_seo_block(
    *, title: str, description: str, url: str, date_iso: str, is_article: bool
) -> str:
    """Costruisce il blocco SEO da iniettare."""
    title_esc = html.escape(title, quote=True)
    desc_esc = html.escape(description, quote=True)

    if is_article:
        ld = (
            '{"@context":"https://schema.org",'
            '"@type":"BlogPosting",'
            f'"headline":{json_str(title)},'
            f'"description":{json_str(description)},'
            f'"image":"{OG_IMAGE}",'
            f'"datePublished":"{date_iso}",'
            f'"dateModified":"{date_iso}",'
            f'"author":{{"@type":"Person","name":"{AUTHOR}",'
            '"url":"https://github.com/pinperepette"},'
            f'"publisher":{{"@type":"Organization","name":"{SITE_NAME}",'
            f'"logo":{{"@type":"ImageObject","url":"{OG_IMAGE}"}}}},'
            f'"mainEntityOfPage":{{"@type":"WebPage","@id":"{url}"}},'
            f'"inLanguage":"it-IT"}}'
        )
        og_type = "article"
        og_article = (
            f'\n  <meta property="article:published_time" content="{date_iso}">\n'
            f'  <meta property="article:author" content="{AUTHOR}">'
        )
    else:
        ld = (
            '{"@context":"https://schema.org",'
            '"@type":"WebSite",'
            f'"name":"{SITE_NAME}",'
            f'"url":"{SITE_URL}/",'
            f'"description":{json_str(description)},'
            f'"author":{{"@type":"Person","name":"{AUTHOR}",'
            '"url":"https://github.com/pinperepette"},'
            '"inLanguage":"it-IT"}'
        )
        og_type = "website"
        og_article = ""

    return f"""{SEO_BEGIN}
  <link rel="canonical" href="{url}">
  <meta name="author" content="{AUTHOR}">
  <meta name="robots" content="index,follow,max-image-preview:large">

  <meta property="og:type" content="{og_type}">
  <meta property="og:site_name" content="{SITE_NAME}">
  <meta property="og:locale" content="it_IT">
  <meta property="og:title" content="{title_esc}">
  <meta property="og:description" content="{desc_esc}">
  <meta property="og:url" content="{url}">
  <meta property="og:image" content="{OG_IMAGE}">
  <meta property="og:image:type" content="image/jpeg">
  <meta property="og:image:width" content="{OG_IMAGE_W}">
  <meta property="og:image:height" content="{OG_IMAGE_H}">
  <meta property="og:image:alt" content="Signal Pirate - logo">{og_article}

  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{title_esc}">
  <meta name="twitter:description" content="{desc_esc}">
  <meta name="twitter:image" content="{OG_IMAGE}">

  <script type="application/ld+json">
  {ld}
  </script>
  {SEO_END}"""


def json_str(s: str) -> str:
    """Escape minimale per stringhe dentro JSON-LD."""
    import json
    return json.dumps(s, ensure_ascii=False)


def inject(html_text: str, block: str) -> str:
    """Sostituisce un blocco SEO esistente o lo inserisce prima di </head>."""
    if SEO_BEGIN in html_text and SEO_END in html_text:
        return re.sub(
            re.escape(SEO_BEGIN) + r".*?" + re.escape(SEO_END),
            block,
            html_text,
            count=1,
            flags=re.DOTALL,
        )
    return html_text.replace("</head>", f"  {block}\n</head>", 1)


def process_article(path: Path, dates: dict[str, str], dry: bool) -> str:
    text = path.read_text(encoding="utf-8")
    title, description = extract_meta(text)
    fname = path.name
    date = dates.get(fname)
    if not date:
        return f"skip {fname}: data non trovata in index.html"
    url = f"{SITE_URL}/articoli/{fname}"
    block = build_seo_block(
        title=title, description=description, url=url, date_iso=date, is_article=True
    )
    new_text = inject(text, block)
    if dry:
        return f"would update {fname}"
    if new_text != text:
        path.write_text(new_text, encoding="utf-8")
        return f"updated {fname}"
    return f"no change {fname}"


def process_index(dry: bool) -> str:
    text = INDEX_HTML.read_text(encoding="utf-8")
    title, description = extract_meta(text)
    block = build_seo_block(
        title=title,
        description=description,
        url=f"{SITE_URL}/",
        date_iso="",
        is_article=False,
    )
    new_text = inject(text, block)
    if dry:
        return "would update index.html"
    if new_text != text:
        INDEX_HTML.write_text(new_text, encoding="utf-8")
        return "updated index.html"
    return "no change index.html"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--one", help="Processa un solo articolo (nome file)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--index-only", action="store_true")
    args = ap.parse_args()

    dates = parse_index_dates()

    if args.index_only:
        print(process_index(args.dry_run))
        return 0

    if args.one:
        path = ARTICOLI_DIR / args.one
        if not path.exists():
            print(f"errore: {path} non esiste", file=sys.stderr)
            return 1
        print(process_article(path, dates, args.dry_run))
        return 0

    print(process_index(args.dry_run))
    for path in sorted(ARTICOLI_DIR.glob("*.html")):
        print(process_article(path, dates, args.dry_run))
    return 0


if __name__ == "__main__":
    sys.exit(main())
