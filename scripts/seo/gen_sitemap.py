#!/usr/bin/env python3
"""Genera sitemap.xml e robots.txt da index.html."""
import re
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[2]
INDEX_HTML = ROOT / "index.html"
SITE_URL = "https://pinperepette.github.io/signal.pirate"


def parse_articles() -> list[tuple[str, str]]:
    text = INDEX_HTML.read_text(encoding="utf-8")
    pattern = re.compile(
        r'<a href="(articoli/[^"]+)"[^>]*class="article-card"[^>]*>.*?'
        r'<div class="article-card-date">([^<]+)</div>',
        re.DOTALL,
    )
    return [(m.group(1), m.group(2).strip()) for m in pattern.finditer(text)]


def latest_date(articles: list[tuple[str, str]]) -> str:
    return max(d for _, d in articles)


def gen_sitemap(articles: list[tuple[str, str]]) -> str:
    urls = []
    urls.append(
        f"  <url>\n"
        f"    <loc>{SITE_URL}/</loc>\n"
        f"    <lastmod>{latest_date(articles)}</lastmod>\n"
        f"    <changefreq>weekly</changefreq>\n"
        f"    <priority>1.0</priority>\n"
        f"  </url>"
    )
    for href, date in articles:
        urls.append(
            f"  <url>\n"
            f"    <loc>{SITE_URL}/{escape(href)}</loc>\n"
            f"    <lastmod>{date}</lastmod>\n"
            f"    <changefreq>monthly</changefreq>\n"
            f"    <priority>0.8</priority>\n"
            f"  </url>"
        )
    body = "\n".join(urls)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{body}\n"
        "</urlset>\n"
    )


def gen_robots() -> str:
    return (
        "User-agent: *\n"
        "Allow: /\n"
        "\n"
        f"Sitemap: {SITE_URL}/sitemap.xml\n"
    )


def main() -> None:
    articles = parse_articles()
    (ROOT / "sitemap.xml").write_text(gen_sitemap(articles), encoding="utf-8")
    (ROOT / "robots.txt").write_text(gen_robots(), encoding="utf-8")
    print(f"sitemap.xml: {len(articles) + 1} URL")
    print("robots.txt: ok")


if __name__ == "__main__":
    main()
