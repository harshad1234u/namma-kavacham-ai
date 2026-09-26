"""Fetch an official page and print/save its visible text, for quoting into the scheme KB.

Usage: python scripts/fetch_official_text.py <https-url> [out.txt]
TLS is always verified; a certificate error means the page is not used as a source.
"""
import html
import re
import sys

import httpx

UA = {"User-Agent": "Mozilla/5.0 (CivicInsight KB curation; +https://github.com/harshad1234u/namma-kavacham-ai)"}


def page_text(url: str) -> str:
    r = httpx.get(url, headers=UA, timeout=30, follow_redirects=True)
    r.raise_for_status()
    ctype = r.headers.get("content-type", "")
    if "pdf" in ctype:
        raise SystemExit("PDF source: extract manually")
    body = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", r.text)
    body = re.sub(r"(?s)<[^>]+>", " ", body)
    return re.sub(r"\s+", " ", html.unescape(body)).strip()


if __name__ == "__main__":
    text = page_text(sys.argv[1])
    if len(sys.argv) > 2:
        open(sys.argv[2], "w", encoding="utf-8").write(text)
    print(len(text), "chars")
    print(text[:3000])
