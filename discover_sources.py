"""
Discovery helper: propose on-chain sources for an episode's artworks.

For each work discussed in an episode, this tries to find where it lives so it
can be wired into snapshot_pools.py:
  - Tezos/fx(hash): objkt.com GraphQL (keyless) by creator + name.
  - Ethereum: the guest's raster.art artist page -> collection -> contract,
    verified against Alchemy (needs ALCHEMY_API_KEY in .env).

It flags shared/Art Blocks-style contracts, works that look like references to
other artists, and anything it can't resolve. Output is a review-ready report
(discovery/<slug>.md) plus a draft CONFIG block — NOT applied automatically.

    python discover_sources.py Ciphrd_Cosimo
    python discover_sources.py --all
"""

import argparse
import csv
import json
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).parent
IMAGES = ROOT / "images"
FINAL = ROOT / "transcripts" / "final"
OUT = ROOT / "discovery"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120 Safari/537.36"}
COMMON = {"0x0000000000000000000000000000000000000000",
          "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",   # WETH
          "0x7f0e75fe32f71195ddd754d12533888d014e0b5e",
          "0xfdfa6863d7cb89186b76c6b051711d25a76a3eed"}

norm = lambda s: re.sub(r"[^a-z0-9]", "", (s or "").lower())
STOP = {"the", "and", "a", "of", "with", "on", "in", "by", "an"}


def decamel(s):
    s = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", s)
    return re.sub(r"(?<=[A-Z])(?=[A-Z][a-z])", " ", s)


def distinctive_words(work):
    """Meaningful words of a (de-camelCased) work name, longest first."""
    words = [w.replace('"', "") for w in re.split(r"[\s,]+", decamel(work))
             if len(w) >= 4 and w.lower() not in STOP]
    return sorted(set(words), key=len, reverse=True) or [decamel(work).strip().replace('"', "")]


def guest_aliases(guest):
    """Alias candidates from a guest string: split multi-artist, keep parentheticals."""
    out = []
    for p in re.split(r"\band\b|&|,|/", re.sub(r"\(.*?\)", " ", guest), flags=re.I):
        if p.strip():
            out.append(p.strip())
    out += [m.strip() for m in re.findall(r"\((.*?)\)", guest)]
    return out or [guest]


def alchemy_key():
    for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        if line.startswith("ALCHEMY_API_KEY="):
            return line.split("=", 1)[1].strip()
    return None


def get(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=25).read().decode("utf-8", "ignore")


def get_json(url):
    return json.loads(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=25).read())


def objkt_gql(q):
    req = urllib.request.Request("https://data.objkt.com/v3/graphql",
                                 data=json.dumps({"query": q}).encode(),
                                 headers={"Content-Type": "application/json", **UA})
    return json.loads(urllib.request.urlopen(req, timeout=25).read()).get("data", {}).get("token", [])


# ---- work list for an episode ----
def works_for(slug):
    """Image-folder prefixes if the folder exists, else italicized transcript works."""
    d = IMAGES / slug
    if d.exists():
        pre = sorted({re.sub(r"_[^_]+\.[^.]+$", "", f.name) for f in d.iterdir() if f.is_file()})
        if pre:
            return pre
    txt = (FINAL / f"{slug}.txt").read_text(encoding="utf-8") if (FINAL / f"{slug}.txt").exists() else ""
    stop = {"and", "the", "wtbs", "waiting to be signed"}
    seen = {}
    for w in re.findall(r"\*([^*\n]{2,40})\*", txt):
        w = w.strip()
        if w.lower() not in stop:
            seen[w] = seen.get(w, 0) + 1
    return [w for w, _ in sorted(seen.items(), key=lambda kv: -kv[1])][:10]


# ---- Tezos (objkt) ----
def _objkt_rows(hits):
    return [{"fa": t["fa_contract"], "name": t.get("name"),
             "creators": [c["holder"]["alias"] for c in (t.get("creators") or []) if c.get("holder")]}
            for t in hits]


AB_URL = "https://data.artblocks.io/v1/graphql"


def artist_matches(artist_name, aliases):
    a = norm(artist_name)
    aw = {w for w in re.split(r"[^a-z0-9]+", artist_name.lower()) if len(w) >= 4}
    for al in aliases:
        if norm(al) and norm(al) == a:                 # exact (handles short names)
            return True
        alw = {w for w in re.split(r"[^a-z0-9]+", al.lower()) if len(w) >= 4}
        if aw & alw:                                   # shared significant word
            return True
    return False


def resolve_artblocks(name):
    """Art Blocks / Engine projects matching a name -> contract + project_id + artist."""
    q = ('{ projects_metadata(where: {name: {_ilike: "%%%s%%"}}, limit: 5) '
         '{ project_id name artist_name contract_address invocations } }' % name.replace('"', ""))
    try:
        req = urllib.request.Request(AB_URL, data=json.dumps({"query": q}).encode(),
                                     headers={"Content-Type": "application/json", **UA})
        return json.loads(urllib.request.urlopen(req, timeout=20).read()).get("data", {}).get("projects_metadata", [])
    except Exception:
        return []


def best_artblocks(work, aliases):
    hits = [p for p in resolve_artblocks(work) if p.get("contract_address")]
    if not hits:
        return None
    return max(hits, key=lambda p: (artist_matches(p["artist_name"], aliases),
                                    norm(work) in norm(p["name"]) or norm(p["name"]) in norm(work),
                                    int(p.get("invocations") or 0)))


def _q_objkt(hits_where):
    return objkt_gql("{ token(where: %s, limit: 4) "
                     "{ fa_contract name creators { holder { alias } } } }" % hits_where)


def find_objkt(aliases, work):
    """Find a Tezos collection. Tries every distinctive word creator-filtered by
    each guest alias (authoritative); if none, falls back to a name-only search
    whose hits are marked creator_matched=False for manual review."""
    words = distinctive_words(work)
    rows, matched = [], True
    for alias in aliases:
        for w in words:
            try:
                rows += _objkt_rows(_q_objkt(
                    '{creators: {holder: {alias: {_ilike: "%%%s%%"}}}, name: {_ilike: "%%%s%%"}}'
                    % (alias.replace('"', ""), w)))
            except Exception:
                pass
        if rows:
            break
    if not rows:                              # last resort: any creator by work name
        matched = False
        for w in words[:2]:
            try:
                rows += _objkt_rows(_q_objkt('{name: {_ilike: "%%%s%%"}}' % w))
            except Exception:
                pass
    seen, out = set(), []
    for r in rows:
        k = (r["fa"], re.sub(r"\s*#.*$", "", r["name"] or ""))
        if k not in seen:
            seen.add(k)
            out.append(r)
    return out[:3], matched


# ---- Ethereum (raster -> Alchemy) ----
def raster_artist_slugs(aliases):
    """Aggregate collection slugs across each guest alias's raster artist page."""
    found, slugs = [], set()
    for alias in aliases:
        for cand in {norm(alias), alias.lower().replace(" ", "-"), alias.lower().replace(" ", "")}:
            try:
                h = get(f"https://www.raster.art/artist/{cand}")
            except Exception:
                continue
            got = set(re.findall(r"/artwork/([a-z0-9-]+)", h))
            if got:
                found.append(cand)
                slugs |= got
                break
    return found, sorted(slugs)


def contract_from_raster_collection(slug):
    try:
        h = get(f"https://www.raster.art/artwork/{slug}")
    except Exception:
        return []
    return [a for a in sorted(set(a.lower() for a in re.findall(r"0x[a-fA-F0-9]{40}", h))) if a not in COMMON]


def alchemy_check(base, contract, work):
    """Return (matches, supply, sample_names, shared, sample_tid) for a contract."""
    try:
        d = get_json(f"{base}/getNFTsForContract?contractAddress={contract}&withMetadata=true&limit=6")
    except Exception:
        return None
    nfts = d.get("nfts", [])
    if not nfts:
        return None
    names = [n.get("name") or "" for n in nfts]
    tids = [int(n.get("tokenId")) for n in nfts]
    prefixes = {re.sub(r"\s*#.*$", "", nm).strip() for nm in names}
    shared = len(prefixes) > 1 or max(tids) > 10 ** 8
    matches = any(norm(work) in norm(nm) for nm in names)
    supply = nfts[0].get("contract", {}).get("totalSupply")
    return {"matches": matches, "supply": supply, "names": names[:3], "shared": shared, "sample_tid": tids[0]}


def find_eth(base, guest, work, artist_slugs):
    if not base:
        return None
    matched = [s for s in artist_slugs if norm(work) and norm(work) in norm(s)]
    for slug in matched:
        for c in contract_from_raster_collection(slug):
            chk = alchemy_check(base, c, work)
            if chk and (chk["matches"] or not chk["shared"]):
                return {"contract": c, "raster_slug": slug, **chk}
    return None


def discover(slug, base, guest):
    works = works_for(slug)
    aliases = guest_aliases(guest)
    lines = [f"## {slug} — guest: **{guest}**  (aliases tried: {aliases})", ""]
    cfg = []
    artist_found, artist_slugs = raster_artist_slugs(aliases)
    lines.append(f"raster artist page(s): {artist_found or '_not found_'} ({len(artist_slugs)} collections)\n")
    for w in works:
        lines.append(f"### {w}")
        ab = best_artblocks(w, aliases)
        eth = None if ab else find_eth(base, guest, w, artist_slugs)
        tez, tez_matched = find_objkt(aliases, w)
        resolved = False
        if ab:
            am = artist_matches(ab["artist_name"], aliases)
            mark = "" if am else "  ⚠️ artist is NOT the guest — reference; verify"
            lines.append(f"- **Art Blocks**: proj {ab['project_id']} on `{ab['contract_address']}` — "
                         f"'{ab['name']}' by {ab['artist_name']} ({ab['invocations']} mints){mark}")
            if am:
                cfg.append(f'"{w}": {{"source": "alchemy", "contract": "{ab["contract_address"]}", '
                           f'"project": {ab["project_id"]}, "artist": "{ab["artist_name"]}"}},')
                resolved = True
        if eth:
            flag = "  ⚠️ SHARED contract — needs project #" if eth["shared"] else ""
            proj = '"project": ?, ' if eth["shared"] else ""
            lines.append(f"- **ETH**: `{eth['contract']}` — names {eth['names']} · supply {eth['supply']}{flag}")
            if not eth["shared"]:
                cfg.append(f'"{w}": {{"source": "alchemy", "contract": "{eth["contract"]}", {proj}"artist": "{guest}"}},')
                resolved = True
        if tez:
            best = tez[0]
            mark = "" if tez_matched else "  ⚠️ creator is NOT the guest — likely a reference; verify"
            lines.append(f"- **Tezos(objkt)**: `{best['fa']}` — \"{best['name']}\" by {best['creators']}{mark}")
            if not resolved and tez_matched:
                q = re.sub(r"\s*#.*$", "", best["name"] or w).replace('"', "")
                cfg.append(f'"{w}": {{"source": "objkt", "creator": "{(best["creators"] or [""])[0]}", '
                           f'"query": "{q}", "artist": "{guest}"}},')
                resolved = True
        if not ab and not eth and not tez:
            lines.append("- _no source found — reference to another artist, off-chain, or local-only_")
        lines.append("")
    lines.append("### draft CONFIG\n```python\n\"%s\": {\n    %s\n},\n```" % (slug, "\n    ".join(cfg) or "# none resolved"))
    return "\n".join(lines), len(cfg)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("slugs", nargs="*")
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    key = alchemy_key()
    base = f"https://eth-mainnet.g.alchemy.com/nft/v3/{key}" if key else None
    guests = {r["slug"]: r["guests"] for r in csv.DictReader((ROOT / "episodes.csv").open(encoding="utf-8"))}
    slugs = list(guests) if args.all else args.slugs
    OUT.mkdir(exist_ok=True)
    summary = []
    for slug in slugs:
        if not (FINAL / f"{slug}.txt").exists():
            print(f"skip {slug} (no transcript)"); continue
        try:
            report, n = discover(slug, base, guests.get(slug, slug))
        except Exception as e:
            print(f"ERR {slug}: {e}"); continue
        (OUT / f"{slug}.md").write_text(report, encoding="utf-8")
        summary.append((n, slug, guests.get(slug, slug)))
        print(f"{slug}: {n} works resolved")
        if not args.all:
            print(report[:1500])
    if args.all:
        summary.sort(reverse=True)
        rows = "\n".join(f"| {s} | {g} | {n} | {'POOL (artist)' if n else 'local/none'} |"
                         for n, s, g in summary)
        (OUT / "_summary.md").write_text(
            "# Discovery summary\n\n| episode | guest | works resolved | verdict |\n"
            "|---|---|---|---|\n" + rows + "\n", encoding="utf-8")
        print(f"\nwrote discovery/_summary.md — {sum(1 for n,_,_ in summary if n)} poolable / {len(summary)} episodes")


if __name__ == "__main__":
    main()
