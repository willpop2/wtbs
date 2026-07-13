"""
Turn the hand-filled MANUAL_IMAGES.md into pool configs.

Reads each episode's works + the contract/link the user pasted and resolves the
ones we can fetch today into discovery/<slug>.config.json (merged, never
clobbering existing entries):
  - objkt.com/collections/fxhash/projects/<id>  -> source=fxhash
  - raster.art/artwork/<name>-by-...  -> only if the work resolves on Art Blocks
  - ✅ "wired via X" rows -> reuse a source already pooled elsewhere (>=10 pieces)
Everything else (non-AB raster, verse.works, tezos token urls) is reported as
unresolved for a later pass. Prints a per-episode summary; writes nothing on --dry.
"""
import re, json, glob, csv, sys, io, time, urllib.request
from pathlib import Path
import snapshot_pools as sp

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
norm = lambda s: re.sub(r"[^a-z0-9]", "", (s or "").lower())
ROOT = Path(__file__).parent
guests = {r["slug"]: r["guests"] for r in csv.DictReader(open(ROOT / "episodes.csv", encoding="utf-8"))}
clean_guest = lambda g: re.sub(r"^\s*artist\s+", "", re.sub(r"\(.*?\)", "", g or ""), flags=re.I).strip()

# reusable sources for ✅ rows: works already pooled somewhere with >=10 pieces
valid = set()
for pf in glob.glob(str(ROOT / "pools" / "*.json")):
    for w, items in json.load(open(pf, encoding="utf-8"))["works"].items():
        if len(items) >= 10:
            valid.add(norm(w))
srcidx = {}
for slug, works in sp.merged_config().items():
    for w, cfg in works.items():
        if norm(w) in valid:
            srcidx.setdefault(norm(w), cfg)

_fx_author = {}
def fx_author(pid):
    if pid in _fx_author:
        return _fx_author[pid]
    name = ""
    try:
        r = urllib.request.Request("https://api.fxhash.xyz/graphql",
                                   data=json.dumps({"query": '{ generativeToken(id:%d){ author{ name } } }' % pid}).encode(),
                                   headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"})
        g = (json.loads(urllib.request.urlopen(r, timeout=20).read()).get("data") or {}).get("generativeToken") or {}
        name = (g.get("author") or {}).get("name") or ""
    except Exception:
        pass
    _fx_author[pid] = name
    return name


_ab_cache = {}
def ab_resolve(name):
    if name in _ab_cache:
        return _ab_cache[name]
    q = ('{ projects_metadata(where:{name:{_ilike:"%s"}},limit:3){project_id name artist_name '
         'contract_address invocations}}' % name.replace('"', ""))
    out = None
    for attempt in range(3):                       # AB API is flaky — retry so real AB works never fall through
        try:
            r = urllib.request.Request("https://data.artblocks.io/v1/graphql", data=json.dumps({"query": q}).encode(),
                                       headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"})
            data = json.loads(urllib.request.urlopen(r, timeout=20).read())["data"]["projects_metadata"]
        except Exception:
            time.sleep(1)
            continue
        for p in data:
            if norm(p["name"]) == norm(name) and int(p["invocations"]) >= 10:
                out = {"source": "alchemy", "contract": p["contract_address"],
                       "project": int(p["project_id"]), "artist": p["artist_name"]}
                break
        _ab_cache[name] = out                      # got a response — cache it (even a no-match)
        return out
    return out                                     # all retries failed — don't cache (retry next work)

def deslug(s):
    s = re.sub(r"-\d{4}$", "", s.split("?")[0])          # drop trailing year
    return s.replace("-and-", " & ").replace("-", " ").title().strip()

_raster_cache = {}
def raster_page(url):
    u = url.split("?")[0]
    if u not in _raster_cache:
        try:
            html = urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}),
                                          timeout=25).read().decode("utf-8", "ignore")
        except Exception:
            html = ""
        _raster_cache[u] = html.replace('\\"', '"')
    return _raster_cache[u]

CHAINS = {1: "eth", 8453: "base"}   # CAIP eip155 id -> Alchemy net (key only has eth+base enabled)
# Art Blocks shared contracts: token id = project*1e6+edition, so a name scan from 0 never reaches
# the project — these MUST be project-scoped via ab_resolve, never the raster name_like path.
AB_SHARED = {"0xa7d8d9ef8d8ce8992df33d8b8cf4aebabd5bd270", "0x059edd72cd353df5106d2b9cc5ab83a52287ac3a"}
CAIP = re.compile(r'"contractRefs":\["([^"]+)"\]')
def _caip_cfg(caip, name, artist):
    if caip.startswith("eip155:"):
        contract = caip.split("/")[-1]
        if contract.lower() in AB_SHARED:
            return ab_resolve(name)                       # project-scoped, or None (better than wrong)
        chain = CHAINS.get(int(caip.split(":")[1].split("/")[0]))
        if not chain:
            return None                                   # unsupported L2 -> leave unresolved
        return {"source": "alchemy", "chain": chain, "contract": contract,
                "name_like": name, "artist": artist}
    if caip.startswith("tezos:"):
        return {"source": "objkt_fa", "contract": caip.split("/")[-1], "query": name, "artist": artist}
    return None

def resolve_raster(url):
    """raster.art artwork -> config via the page's CAIP contractRef. Artist + name from the slug."""
    m = CAIP.search(raster_page(url))
    if not m:
        return None
    slug = url.split("/artwork/")[-1].split("?")[0]
    workslug, _, artistslug = slug.rpartition("-by-")
    return _caip_cfg(m.group(1), deslug(workslug) if workslug else "", deslug(artistslug) if artistslug else "")

def resolve_raster_token(url, work):
    """raster.art/token/<chain>/<contract>/<id> -> config (contract is right in the URL)."""
    p = url.split("/token/")[-1].split("?")[0].split("/")
    if len(p) < 2:
        return None
    chain, contract = p[0], p[1]
    if chain == "tezos":
        return {"source": "objkt_fa", "contract": contract, "query": work, "artist": ""}
    if chain == "ethereum":
        return {"source": "alchemy", "contract": contract, "name_like": work, "artist": ""}
    return None

FX = re.compile(r"objkt\.com/collections/fxhash/projects/(\d+)")
row = re.compile(r"^- \*\*(.+?)\*\* — contract/link: `([^`]*)`(.*)$")
head = re.compile(r"^### .*`\[(.+?)\]`")
lines = (ROOT / "MANUAL_IMAGES.md").read_text(encoding="utf-8").splitlines()

configs, unresolved = {}, {}
ep, section = None, "A"
for ln in lines:
    if ln.startswith("## B."):
        section = "B"
    h = head.match(ln)
    if h:
        ep = h.group(1)
    m = row.match(ln)
    if not m or not ep:
        continue
    work, url, rest = m.group(1).strip(), m.group(2).strip(), m.group(3)
    if "wired via" in rest:
        continue                        # ✅ reuse handled by apply_reuse.py (copies from committed pools)
    cfg = None
    if FX.search(url):
        pid = int(FX.search(url).group(1))
        artist = fx_author(pid) or (clean_guest(guests.get(ep, ep)) if section == "A" else "")
        cfg = {"source": "fxhash", "project": pid, "artist": artist}
    elif "raster.art/artwork/" in url:
        cfg = ab_resolve(work) or resolve_raster(url)
    elif "raster.art/token/" in url:
        cfg = resolve_raster_token(url, work)
    if cfg:
        configs.setdefault(ep, {})[work] = cfg
    elif url and url != "________":
        unresolved.setdefault(ep, []).append((work, url))

if "--dry" not in sys.argv:
    (ROOT / "discovery").mkdir(exist_ok=True)
    for ep, works in configs.items():
        p = ROOT / "discovery" / f"{ep}.config.json"
        existing = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
        existing.update(works)   # the doc is authoritative for works it resolves; keep any extras
        p.write_text(json.dumps(existing, indent=1), encoding="utf-8")

nfx = sum(1 for e in configs.values() for c in e.values() if c["source"] == "fxhash")
nab = sum(1 for e in configs.values() for c in e.values() if c["source"] == "alchemy")
nre = sum(len(v) for v in configs.values()) - nfx - nab
print(f"RESOLVED {sum(len(v) for v in configs.values())} works  "
      f"(fxhash={nfx}, artblocks={nab}, reuse✅={nre}) across {len(configs)} episodes")
print(f"UNRESOLVED {sum(len(v) for v in unresolved.values())} works (Phase 2: non-AB raster / verse / tezos-url)\n")
for ep in sorted(configs, key=lambda e: -len(configs[e])):
    u = len(unresolved.get(ep, []))
    print(f"  {len(configs[ep]):2} wired  {u:2} left   {ep}")
if "--dry" in sys.argv:
    print("\nUNRESOLVED detail:")
    for ep in sorted(unresolved):
        for w, u in unresolved[ep]:
            print(f"  {ep:26} {w:26} {u}")
print("\nSLUGS:", " ".join(sorted(configs)))
