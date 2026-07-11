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

# episode slug -> pool key -> collection source.
#   Ethereum via Alchemy: {"source":"alchemy", "contract": "0x..", "artist": ..}
#   Tezos/fx(hash) via objkt (keyless): {"source":"objkt", "creator": alias,
#       "query": objkt-name-prefix, "artist": ..}
CONFIG = {
    "Remnynt": {
        "Architectonica": {"source": "alchemy", "contract": "0xe84b8d744a46098953293397a5c2ce2f5b393ebf", "artist": "remnynt"},
        "Proscenium":     {"source": "alchemy", "contract": "0x99a9b7c1116f9ceeb1652de04d5969cce509b069", "artist": "remnynt"},
        "Vibes":          {"source": "alchemy", "contract": "0x6c7c97caff156473f6c9836522ae6e1d6448abe7", "artist": "remnynt"},
        "Terraforms":     {"source": "alchemy", "contract": "0x4e1f41613c9084fdb9e34e11fae9412427480e56", "artist": "Mathcastles"},
    },
    "Zancan": {
        "A Bugged Forest":        {"source": "objkt", "creator": "zancan", "query": "A Bugged Forest", "artist": "Zancan"},
        "Garden Monoliths":       {"source": "objkt", "creator": "zancan", "query": "Garden, Monoliths", "artist": "Zancan"},
        "Kindergarten Monuments": {"source": "objkt", "creator": "zancan", "query": "(kinder)Garden, Monuments", "artist": "Zancan"},
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


ENS_CACHE = {}


def owner_display(addr: str) -> str:
    """ENS name if the address has one, else a truncated 0x…addr. Cached."""
    if not addr:
        return ""
    if addr in ENS_CACHE:
        return ENS_CACHE[addr]
    name = ""
    try:
        req = urllib.request.Request(f"https://api.ensideas.com/ens/resolve/{addr}",
                                     headers={"User-Agent": "Mozilla/5.0"})
        name = json.loads(urllib.request.urlopen(req, timeout=12).read()).get("name") or ""
    except Exception:
        name = ""
    disp = name or (addr[:6] + "…" + addr[-4:])
    ENS_CACHE[addr] = disp
    return disp


def resolve_owners(addresses) -> dict:
    """Resolve many owners' ENS names in parallel (falls back to short addr)."""
    from concurrent.futures import ThreadPoolExecutor
    addrs = [a for a in set(addresses) if a]
    with ThreadPoolExecutor(max_workers=8) as ex:
        names = list(ex.map(owner_display, addrs))
    return dict(zip(addrs, names))


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
    disp = resolve_owners(o.values())  # resolve ENS in parallel
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
            items.append({"t": tid, "img": img, "o": disp.get(o.get(tid, ""), ""),
                          "s": f"https://www.raster.art/token/ethereum/{contract}/{tid}"})
        page = d.get("pageKey")
        if not page:
            break
        time.sleep(0.25)
    return items


def objkt_gql(query: str) -> list:
    req = urllib.request.Request("https://data.objkt.com/v3/graphql",
                                 data=json.dumps({"query": query}).encode(),
                                 headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"})
    return json.loads(urllib.request.urlopen(req, timeout=30).read()).get("data", {}).get("token", [])


def snapshot_objkt(creator: str, query: str) -> list:
    """Tezos/fx(hash) collection via objkt: image (objkt CDN) + holder (tzdomain/alias)."""
    esc = query.replace('"', '\\"')
    q = ('{ token(where: {creators: {holder: {alias: {_eq: "%s"}}}, name: {_ilike: "%s #%%"}}, '
         'limit: %d, order_by: {token_id: asc}) { fa_contract token_id name '
         'holders(where: {quantity: {_gt: "0"}}, limit: 1) { holder_address holder { alias tzdomain } } } }'
         % (creator, esc, CAP))
    items = []
    for t in objkt_gql(q):
        c, tid, name = t["fa_contract"], t["token_id"], t.get("name") or ""
        h = (t.get("holders") or [{}])[0]
        hd = h.get("holder") or {}
        addr = h.get("holder_address", "")
        owner = hd.get("tzdomain") or hd.get("alias") or ((addr[:5] + "…" + addr[-4:]) if addr else "")
        m = re.search(r"#(\d+)", name)
        items.append({"t": m.group(1) if m else tid,
                      "img": f"https://assets.objkt.media/file/assets-003/{c}/{tid}/thumb400",
                      "o": owner, "s": f"https://objkt.com/tokens/{c}/{tid}"})
    return items


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="single episode slug")
    args = ap.parse_args()
    base = None
    POOLS.mkdir(exist_ok=True)

    slugs = [args.only] if args.only else list(CONFIG)
    for slug in slugs:
        works = CONFIG.get(slug, {})
        data, artists = {}, {}
        for work, cfg in works.items():
            if cfg["source"] == "alchemy":
                base = base or f"https://eth-mainnet.g.alchemy.com/nft/v3/{_key()}"
                items = snapshot_work(base, cfg["contract"])
            elif cfg["source"] == "objkt":
                items = snapshot_objkt(cfg["creator"], cfg["query"])
            else:
                raise SystemExit(f"unknown source {cfg['source']!r}")
            data[work] = items
            artists[work] = cfg["artist"]
            print(f"{slug}/{work}: {len(items)} pieces")
        out = {"artists": artists, "works": data}
        (POOLS / f"{slug}.json").write_text(json.dumps(out), encoding="utf-8")
        print(f"wrote pools/{slug}.json")


if __name__ == "__main__":
    main()
