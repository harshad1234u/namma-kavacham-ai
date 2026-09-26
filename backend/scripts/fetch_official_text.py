"""Fetch an official page and print/save its visible text, for quoting into the scheme KB.

Usage: python scripts/fetch_official_text.py <https-url> [out.txt]
TLS is always verified; a certificate error means the page is not used as a source.
"""
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.civic.retrieval.fetch import UA, html_to_text  # noqa: E402


def page_text(url: str) -> str:
    r = httpx.get(url, headers=UA, timeout=30, follow_redirects=True)
    r.raise_for_status()
    if "pdf" in r.headers.get("content-type", ""):
        raise SystemExit("PDF source: extract manually")
    return html_to_text(r.text)[1]


if __name__ == "__main__":
    text = page_text(sys.argv[1])
    if len(sys.argv) > 2:
        Path(sys.argv[2]).write_text(text, encoding="utf-8")
    print(len(text), "chars")
    print(text[:3000])
