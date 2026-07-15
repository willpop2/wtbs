"""
Generate self-hosted 1200x630 social share-card images.

Twitter/Facebook reject og:images over ~5 MB, and the full-res Alchemy art CDN
serves multi-MB (sometimes 25 MB+) PNGs — so shared links showed no image. This
downsamples each episode's representative artwork to a small JPEG via the
images.weserv.nl resizer and saves it under static/og/<slug>.jpg (copied into
site/og/ at build; og:image points there). weserv is used only here, at
generation time — the deployed cards are fully self-hosted on wtbs.show.

Run after the snapshot pools change, then commit static/og/ :

    python make_og.py
"""

import csv
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).parent
POOLS = ROOT / "pools"
OUT = ROOT / "static" / "og"


def og_source(slug: str) -> str:
    """First piece of the first populated work — same deterministic pick as build_site."""
    p = POOLS / f"{slug}.json"
    if not p.exists():
        return ""
    data = json.loads(p.read_text(encoding="utf-8"))
    for items in data.get("works", {}).values():
        if items and items[0].get("img"):
            return items[0]["img"]
    return ""


def weserv_url(src: str) -> str:
    host_path = src.split("://", 1)[-1]                       # weserv wants scheme-less; ssl: = https source
    q = urllib.parse.urlencode({"url": "ssl:" + host_path, "w": 1200, "h": 630,
                                "fit": "cover", "output": "jpg", "q": 80})
    return "https://images.weserv.nl/?" + q


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "wtbs-og/1.0"})
    with urllib.request.urlopen(req, timeout=90) as r:
        return r.read()


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    slugs = [r["slug"] for r in csv.DictReader((ROOT / "episodes.csv").open(encoding="utf-8"))]
    ok, fail, first = 0, [], None
    for s in slugs:
        src = og_source(s)
        if not src:
            continue
        try:
            data = fetch(weserv_url(src))
            if not (1000 < len(data) < 4_500_000):
                raise ValueError(f"unexpected size {len(data)}")
            (OUT / f"{s}.jpg").write_bytes(data)
            ok += 1
            if first is None:
                first = OUT / f"{s}.jpg"
            print(f"  ok  {s}  ({len(data)//1024} KB)")
        except Exception as e:
            fail.append((s, str(e)))
            print(f"  FAIL {s}: {e}", file=sys.stderr)
        time.sleep(0.15)
    if first:                                                 # fallback card for episodes with no art
        (OUT / "_default.jpg").write_bytes(first.read_bytes())
    print(f"\ngenerated {ok} og images; default = {first.name if first else 'NONE'}")
    if fail:
        print(f"{len(fail)} failures: {[s for s, _ in fail]}")


if __name__ == "__main__":
    main()
