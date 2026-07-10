"""
Pull artwork images + crediting metadata from raster.art.

Each raster token page (server-rendered) carries schema.org VisualArtwork
JSON-LD (title, artist, year, full-res image URL) plus the current owner in
the HTML. Given a collection's chain + contract and a set of token IDs, this
fetches that metadata and (optionally) downloads the images.

    # inspect a few tokens (prints credit lines, no download)
    python raster_pull.py --contract 0xe84b...ebf --tokens 38,192,203

    # download images + write a credits sidecar into images/<slug>/
    python raster_pull.py --contract 0xe84b...ebf --tokens 38,192 \
        --slug Remnynt --work Architectonica --download

A token URL like
  https://www.raster.art/token/ethereum/<contract>/<id>
gives you the chain (ethereum), contract, and id to feed in.
"""

import argparse
import json
import re
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).parent
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120 Safari/537.36"}
TOKEN_URL = "https://www.raster.art/token/{chain}/{contract}/{tid}"


def _get(url: str) -> str:
    req = urllib.request.Request(url, headers=UA)
    return urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "ignore")


def _strip_tags(html: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", html)).strip()


def fetch_token(contract: str, tid, chain: str = "ethereum") -> dict:
    """Return crediting metadata for one raster token."""
    url = TOKEN_URL.format(chain=chain, contract=contract, tid=tid)
    html = _get(url)

    art = {}
    for b in re.findall(r'<script type="application/ld\+json"[^>]*>(.*?)</script>', html, re.S):
        try:
            d = json.loads(b)
        except Exception:
            continue
        if d.get("@type") == "VisualArtwork":
            art = d
            break

    title = art.get("name", "")
    creators = art.get("creator") or []
    artist = creators[0].get("name", "") if creators else ""
    artist_url = creators[0].get("url", "") if creators else ""
    year = (art.get("dateCreated", "") or "")[:4]
    image_url = (art.get("image") or {}).get("contentUrl", "")

    # owner: `Owned by <a href="/collector/0x..">NAME or truncated-addr</a>`
    owner_addr = owner_name = ""
    m = re.search(r'headerOwnerName__\w+">\s*<a href="/collector/(0x[a-fA-F0-9]{40})"'
                  r'[^>]*>(.*?)</a>', html, re.S)
    if not m:
        m = re.search(r'href="/collector/(0x[a-fA-F0-9]{40})"[^>]*>(.*?)</a>', html, re.S)
    if m:
        owner_addr = m.group(1)
        owner_name = _strip_tags(m.group(2))
    if not owner_name and owner_addr:
        owner_name = owner_addr[:6] + "…" + owner_addr[-4:]

    return {
        "token": str(tid), "title": title, "artist": artist, "artist_url": artist_url,
        "year": year, "image_url": image_url, "owner": owner_name,
        "owner_addr": owner_addr, "source": url,
        "credit": f"{title} — {artist}, {year} · collected by {owner_name}",
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--contract", required=True)
    ap.add_argument("--chain", default="ethereum")
    ap.add_argument("--tokens", required=True, help="comma-separated token ids")
    ap.add_argument("--slug", help="episode slug (dest images/<slug>/)")
    ap.add_argument("--work", help="work name, used for image filenames")
    ap.add_argument("--download", action="store_true")
    args = ap.parse_args()

    ids = [t.strip() for t in args.tokens.split(",") if t.strip()]
    records = []
    for tid in ids:
        rec = fetch_token(args.contract, tid, args.chain)
        records.append(rec)
        print(f"#{tid}: {rec['credit']}")
        print(f"      img: {rec['image_url']}")
        if args.download and args.slug and args.work and rec["image_url"]:
            ext = rec["image_url"].rsplit(".", 1)[-1]
            dest = ROOT / "images" / args.slug / f"{args.work}_{tid}.{ext}"
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(urllib.request.urlopen(
                urllib.request.Request(rec["image_url"], headers=UA), timeout=60).read())
            print(f"      saved -> {dest.relative_to(ROOT)}")
        time.sleep(0.6)  # be polite

    if args.slug:
        side = ROOT / "images" / args.slug / "credits.json"
        side.parent.mkdir(parents=True, exist_ok=True)
        existing = json.loads(side.read_text(encoding="utf-8")) if side.exists() else {}
        for rec in records:
            existing[rec["token"]] = rec
        side.write_text(json.dumps(existing, indent=1), encoding="utf-8")
        print(f"\nwrote {side.relative_to(ROOT)} ({len(records)} records)")


if __name__ == "__main__":
    main()
