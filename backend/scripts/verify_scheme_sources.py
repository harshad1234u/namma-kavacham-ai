"""Re-fetch every scheme source and check that each recorded quote still appears on the live page.

Run before committing KB changes:  python scripts/verify_scheme_sources.py [scheme_id ...]
Exit code 1 if any quote is missing or any source cannot be fetched with a validated TLS connection.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.civic.schemes.kb import SCHEMES_DIR  # noqa: E402
from app.civic.schemes.schema import norm  # noqa: E402
from scripts.fetch_official_text import page_text  # noqa: E402


def main(only: set[str]) -> int:
    failures = 0
    for path in sorted(SCHEMES_DIR.glob("*.json")):
        scheme = json.loads(path.read_text(encoding="utf-8"))
        if only and scheme["id"] not in only:
            continue
        for src in scheme["sources"]:
            try:
                text = norm(page_text(src["url"]))
            except Exception as exc:  # noqa: BLE001 - report and continue
                print(f"FAIL {scheme['id']}/{src['id']}: cannot fetch ({type(exc).__name__}: {exc})")
                failures += 1
                continue
            missing = [q for q in src["quotes"] if norm(q) not in text]
            for q in missing:
                print(f"FAIL {scheme['id']}/{src['id']}: quote not on page: {q[:90]!r}")
            failures += len(missing)
            print(f"{'ok  ' if not missing else 'FAIL'} {scheme['id']}/{src['id']}: {len(src['quotes']) - len(missing)}/{len(src['quotes'])} quotes")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(set(sys.argv[1:])))
