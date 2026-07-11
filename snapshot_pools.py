"""
Snapshot NFT collections into committed pool files for the site.

For each configured collection, pulls every piece's image + current owner from
the Alchemy NFT API and writes pools/<slug>.json = {work: [{t, img, o, s}, ...]}.
The site's random-image-pool slots draw from these at page load (build_site.py
emits them; a client script picks a few at random per visit).

Run locally (key stays in .env, never in CI):
    python snapshot_pools.py                 # all configured collections
    python snapshot_pools.py --only Remnynt  # one episode

Refresh whenever you want updated ownership.
"""

import argparse
import json
import os
import re
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).parent
POOLS = ROOT / "pools"

# episode slug -> work name -> collection (ethereum contracts on Alchemy)
CONFIG = {
    "Remnynt": {
        "Architectonica": {"contract": "0xe84b8d744a46098953293397a5c2ce2f5b393ebf", "artist": "remnynt"},
        "Proscenium":     {"contract": "0x99a9b7c1116f9ceeb1652de04d5969cce509b069", "artist": "remnynt"},
        "Vibes":          {"contract": "0x6c7c97caff156473f6c9836522ae6e1d6448abe7", "artist": "remnynt"},
    },
}
CAP = 300  # max pieces per work to snapshot


def _key() -> str:
    for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        if line.startswith("ALCHEMY_API_KEY="):
            return line.split("=", 1)[1].strip()
    raise SystemExit("ALCHEMY_API_KEY not found in .env")


def _get(url: str) -> dict:
    return json.loads(urllib.request.urlopen(url, timeout=30).read())


def owners_map(base: str, contract: str) -> dict:
    """token id (decimal str) -> owner address, across pages."""
    out, page = {}, None
    while True:
        u = f"{base}/getOwnersForContract?contractAddress={contract}&withTokenBalances=true"
        if page:
            u += f"&pageKey={page}"
        d = _get(u)
        for o in d.get("owners", []):
            for tb in o.get("tokenBalances", []):
                tid = tb["tokenId"]
                tid = str(int(tid, 16)) if str(tid).startswith("0x") else str(tid)
                out[tid] = o["ownerAddress"]
        page = d.get("pageKey")
        if not page:
            return out


def snapshot_work(base: str, contract: str) -> list:
    o = owners_map(base, contract)
    items, page = [], None
    while len(items) < CAP:
        u = f"{base}/getNFTsForContract?contractAddress={contract}&withMetadata=true&limit=100"
        if page:
            u += f"&pageKey={page}"
        d = _get(u)
        for n in d.get("nfts", []):
            tid = str(n.get("tokenId"))
            img = (n.get("image") or {}).get("cachedUrl") or (n.get("image") or {}).get("originalUrl")
            if not img:
                continue
            addr = o.get(tid, "")
            short = (addr[:6] + "…" + addr[-4:]) if addr else ""
            items.append({"t": tid, "img": img, "o": short,
                          "s": f"https://www.raster.art/token/ethereum/{contract}/{tid}"})
        page = d.get("pageKey")
        if not page:
            break
        time.sleep(0.25)
    return items


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="single episode slug")
    args = ap.parse_args()
    base = f"https://eth-mainnet.g.alchemy.com/nft/v3/{_key()}"
    POOLS.mkdir(exist_ok=True)

    slugs = [args.only] if args.only else list(CONFIG)
    for slug in slugs:
        works = CONFIG.get(slug, {})
        data = {}
        artists = {}
        for work, cfg in works.items():
            items = snapshot_work(base, cfg["contract"])
            data[work] = items
            artists[work] = cfg["artist"]
            print(f"{slug}/{work}: {len(items)} pieces")
        out = {"artists": artists, "works": data}
        (POOLS / f"{slug}.json").write_text(json.dumps(out), encoding="utf-8")
        print(f"wrote pools/{slug}.json")


if __name__ == "__main__":
    main()
