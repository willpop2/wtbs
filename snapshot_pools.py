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
        "Proscenium":     {"source": "alchemy", "contract": "0x99a9b7c1116f9ceeb1652de04d5969cce509b069", "project": 486, "artist": "remnynt"},
        "Vibes":          {"source": "alchemy", "contract": "0x6c7c97caff156473f6c9836522ae6e1d6448abe7", "artist": "remnynt"},
        "Terraforms":     {"source": "alchemy", "contract": "0x4e1f41613c9084fdb9e34e11fae9412427480e56", "artist": "Mathcastles"},
    },
    "Zancan": {
        "A Bugged Forest":        {"source": "objkt", "creator": "zancan", "query": "A Bugged Forest", "artist": "Zancan"},
        "Garden Monoliths":       {"source": "objkt", "creator": "zancan", "query": "Garden, Monoliths", "artist": "Zancan"},
        "Kindergarten Monuments": {"source": "objkt", "creator": "zancan", "query": "(kinder)Garden, Monuments", "artist": "Zancan"},
        "Landscape with Carbon Capture": {"source": "alchemy", "contract": "0x850d754a640f640b8d9844518f584ee131a57c9d", "artist": "Zancan"},
    },
    "Nudoru": {
        "Cold Mountain":     {"source": "objkt", "creator": "nudoru", "query": "Cold Mountain", "artist": "Nudoru"},
        "Orchard":           {"source": "objkt", "creator": "nudoru", "query": "Orchard", "artist": "Nudoru"},
        "Deep Forest":       {"source": "objkt", "creator": "nudoru", "query": "Deep Forest", "artist": "Nudoru"},
        "Grove":             {"source": "objkt", "creator": "nudoru", "query": "Grove", "artist": "Nudoru"},
        "Crayon Attractors": {"source": "objkt", "creator": "nudoru", "query": "Crayon Attractors", "artist": "Nudoru"},
        "Turbulence":        {"source": "objkt", "creator": "nudoru", "query": "Turbulence", "artist": "Nudoru"},
        "Caustics":          {"source": "objkt", "creator": "nudoru", "query": "Caustics", "artist": "Nudoru"},
        "Crisis Worlds":     {"source": "objkt", "creator": "nudoru", "query": "Crisis Worlds", "artist": "Nudoru"},
    },
    "Jeres": {
        "Coronado":       {"source": "objkt", "creator": "jeres", "query": "Coronado", "artist": "Jeres"},
        "Glossolalia":    {"source": "objkt", "creator": "jeres", "query": "Glossolalia", "artist": "Jeres"},
        "Vapor Trails":   {"source": "objkt", "creator": "jeres", "query": "vapour trails", "artist": "Jeres"},
        "Sinuosity":      {"source": "objkt", "creator": "jeres", "query": "sinuosity", "artist": "Jeres"},
        "Nightfall Moon": {"source": "objkt", "creator": "jeres", "query": "night fall moon", "artist": "Jeres"},
        "Attachment":     {"source": "objkt", "creator": "jeres", "query": "Attachment", "artist": "Jeres"},
        "Here, After":    {"source": "objkt", "creator": "jeres", "query": "Here, After", "artist": "Jeres"},
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


def owner_of_token(base: str, contract: str, tid: str) -> str:
    try:
        ow = _get(f"{base}/getOwnersForNFT?contractAddress={contract}&tokenId={tid}").get("owners", [])
        return ow[0] if ow else ""
    except Exception:
        return ""


def snapshot_work(base: str, contract: str, project=None, name_like=None) -> list:
    """Pull a collection's pieces + owners. `project` scopes an Art Blocks-style
    shared contract to one project (token id = project*1e6 + edition). `name_like`
    keeps only tokens whose name contains it — guards against a shared/multi-work
    contract (e.g. a raster ETH work on a Manifold-style contract)."""
    lo = project * 1_000_000 if project is not None else None
    hi = (project + 1) * 1_000_000 if project is not None else None
    toks, page, scanned = [], None, 0          # [(tokenId, edition-or-id, img)]
    start = str(lo) if lo is not None else None
    while len(toks) < CAP and scanned < 4000:
        u = f"{base}/getNFTsForContract?contractAddress={contract}&withMetadata=true&limit=100"
        if start:
            u += f"&startToken={start}"
        if page:
            u += f"&pageKey={page}"
        try:
            d = _get(u)
        except Exception:
            break                                  # unreachable contract/chain -> return what we have
        done = False
        for n in d.get("nfts", []):
            scanned += 1
            tid = int(n.get("tokenId"))
            if hi is not None and tid >= hi:
                done = True
                break
            nm = n.get("name") or ""
            if name_like and name_like.lower() not in nm.lower():
                continue
            img = (n.get("image") or {}).get("cachedUrl") or (n.get("image") or {}).get("originalUrl")
            if not img:
                continue
            mm = re.search(r"#(\d+)", nm)                         # edition from the name
            edition = mm.group(1) if mm else (str(tid - lo) if lo is not None else str(tid))
            toks.append((str(tid), edition, img))
        page = d.get("pageKey")
        if done or not page:
            break
        time.sleep(0.2)
    if name_like and not toks:                 # filter matched nothing -> dedicated contract
        return snapshot_work(base, contract, project, name_like=None)
    # owners: per-token for a project slice, else the whole-contract map
    if project is not None:
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=8) as ex:
            addrs = list(ex.map(lambda t: owner_of_token(base, contract, t[0]), toks))
        o = {t[0]: a for t, a in zip(toks, addrs)}
    else:
        o = owners_map(base, contract)
    disp = resolve_owners(o.values())
    return [{"t": disp_id, "img": img, "o": disp.get(o.get(tid, ""), ""),
             "s": f"https://www.raster.art/token/ethereum/{contract}/{tid}"}
            for tid, disp_id, img in toks]


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


# fx(hash) shared gentk contracts — a name scope is mandatory (whole-contract = every project)
FX_SHARED = {"KT1KEa8z6vWXDJrVqtMrAeDVzsvxat3kHaCE",   # v1
             "KT1U6EHmNxJTkvaWJ4ThczG4FSDaHC21ssvi",   # v2 gentk
             "KT1EfsNuqwLAWDd3o4pvfUx1CAh5GMdTrRvr"}    # v3 / fx(params)


def snapshot_objkt_fa(contract: str, query: str) -> list:
    """Tezos collection by fa_contract (from a raster tezos:.../KT1 contractRef),
    scoped by work name for shared contracts like the fx(hash) gentks. Falls back to
    the whole contract only for dedicated (non-shared) contracts."""
    def q(name_clause):
        return ('{ token(where: {fa_contract: {_eq: "%s"}%s}, limit: %d, order_by: {token_id: asc}) '
                '{ fa_contract token_id name holders(where: {quantity: {_gt: "0"}}, limit: 1) '
                '{ holder_address holder { alias tzdomain } } } }' % (contract, name_clause, CAP))
    esc = query.replace('"', '\\"')
    # name-scope only: a whole-contract fallback pulls garbage from any shared contract
    # (fx(hash) gentks, objkt editions like KT1RJ6Pbj…) so we skip rather than mis-attribute.
    rows = objkt_gql(q(', name: {_ilike: "%s #%%"}' % esc))
    items = []
    for t in rows:
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


def _fx_gql(query: str) -> dict:
    req = urllib.request.Request("https://api.fxhash.xyz/graphql",
                                 data=json.dumps({"query": query}).encode(),
                                 headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"})
    return json.loads(urllib.request.urlopen(req, timeout=30).read()).get("data", {})


def snapshot_fxhash(project: int) -> list:
    """fx(hash) generative token by project id (from objkt.com/collections/fxhash/projects/<id>).
    Resolves the gentk contract + every iteration's owner via the fxhash API; images come from
    the objkt CDN (same path as snapshot_objkt), so rendering/credits stay consistent."""
    q = ('{ generativeToken(id:%d){ gentkContractAddress entireCollection{ iteration id '
         'owner{ name id } } } }' % project)
    g = (_fx_gql(q) or {}).get("generativeToken") or {}
    c = g.get("gentkContractAddress")
    items = []
    for o in (g.get("entireCollection") or [])[:CAP]:
        tid = str(o["id"]).split("-")[-1]
        ow = o.get("owner") or {}
        addr = ow.get("id", "")
        owner = ow.get("name") or ((addr[:5] + "…" + addr[-4:]) if addr else "")
        items.append({"t": o["iteration"],
                      "img": f"https://assets.objkt.media/file/assets-003/{c}/{tid}/thumb400",
                      "o": owner, "s": f"https://objkt.com/tokens/{c}/{tid}"})
    return items


def merged_config() -> dict:
    """discovery/*.config.json (from discover_sources.py) merged under the
    hand-tuned CONFIG, which wins per slug."""
    cfg = {}
    disc = ROOT / "discovery"
    if disc.exists():
        for f in disc.glob("*.config.json"):
            try:
                d = json.loads(f.read_text(encoding="utf-8"))
                if d:
                    cfg[f.name[:-len(".config.json")]] = d
            except Exception:
                pass
    cfg.update(CONFIG)
    return cfg


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="single episode slug")
    args = ap.parse_args()
    key = None
    POOLS.mkdir(exist_ok=True)

    ALL = merged_config()
    slugs = [args.only] if args.only else list(ALL)
    for slug in slugs:
        works = ALL.get(slug, {})
        data, artists, seen = {}, {}, set()
        for work, cfg in works.items():
            sig = (cfg["source"], cfg.get("contract"), cfg.get("project"), cfg.get("creator"),
                   cfg.get("query"), cfg.get("name_like"))
            if sig in seen:          # same collection under a different label -> skip dup
                continue
            seen.add(sig)
            if cfg["source"] == "alchemy":
                sub = {"eth": "eth-mainnet", "base": "base-mainnet", "arb": "arb-mainnet",
                       "opt": "opt-mainnet", "matic": "polygon-mainnet"}.get(cfg.get("chain", "eth"), "eth-mainnet")
                key = key or _key()
                items = snapshot_work(f"https://{sub}.g.alchemy.com/nft/v3/{key}",
                                      cfg["contract"], cfg.get("project"), cfg.get("name_like"))
            elif cfg["source"] == "objkt":
                items = snapshot_objkt(cfg["creator"], cfg["query"])
            elif cfg["source"] == "objkt_fa":
                items = snapshot_objkt_fa(cfg["contract"], cfg["query"])
            elif cfg["source"] == "fxhash":
                items = snapshot_fxhash(cfg["project"])
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
