"""
Add the live/animation URL (`a`) to pool pieces that lack it — in place.

For pools restored from git (which predate the play feature) each piece has an
`s` (token page) but no `a`. This derives the live URL per piece from `s`
WITHOUT re-resolving owners/images (so no data-loss risk):
  objkt.com/tokens/<c>/<id>          -> objkt artifact_uri (ipfs gateway)
  raster.art/token/ethereum/<c>/<id> -> Alchemy generator_url / animation_url
Only touches works where pieces are missing `a`. Run: python enrich_live.py [slug]
"""
import json, glob, os, sys, io, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import snapshot_pools as sp

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")


def objkt_artifacts(contract, ids):
    out = {}
    for i in range(0, len(ids), 100):
        idlist = ",".join('"%s"' % t for t in ids[i:i + 100])
        q = ('{ token(where:{fa_contract:{_eq:"%s"}, token_id:{_in:[%s]}}, limit:100)'
             '{ token_id artifact_uri } }' % (contract, idlist))
        for t in sp.objkt_gql(q):
            out[str(t["token_id"])] = sp._ipfs(t.get("artifact_uri"))
    return out


def alchemy_live(base, contract, ids):
    out = {}
    for i in range(0, len(ids), 100):
        body = json.dumps({"tokens": [{"contractAddress": contract, "tokenId": str(t)}
                                      for t in ids[i:i + 100]]}).encode()
        try:
            req = urllib.request.Request(base + "/getNFTMetadataBatch", data=body,
                                         headers={"Content-Type": "application/json"})
            d = json.loads(urllib.request.urlopen(req, timeout=90).read())
        except Exception as e:
            print("   alchemy batch err:", str(e)[:50]); continue
        for n in d.get("nfts", []):
            tid = n.get("tokenId")
            if tid is None:
                continue
            md = n.get("raw", {}).get("metadata", {}) or {}
            out[str(int(tid))] = md.get("generator_url") or sp._ipfs(md.get("animation_url", ""))
    return out


def enrich(pf, base_holder):
    d = json.loads(open(pf, encoding="utf-8").read())
    changed = 0
    for work, items in d.get("works", {}).items():
        if not items or all("a" in it for it in items):
            continue
        s0 = items[0].get("s", "")
        if "objkt.com/tokens/" in s0:
            contract = s0.split("/tokens/")[1].split("/")[0]
            ids = [it["s"].split("/tokens/")[1].split("/")[1] for it in items]
            amap = objkt_artifacts(contract, ids)
            for it in items:
                it["a"] = amap.get(it["s"].split("/tokens/")[1].split("/")[1], "")
            changed += len(items)
        elif "raster.art/token/ethereum/" in s0:
            contract = s0.split("/ethereum/")[1].split("/")[0]
            base_holder[0] = base_holder[0] or f"https://eth-mainnet.g.alchemy.com/nft/v3/{sp._key()}"
            ids = [it["s"].rsplit("/", 1)[1] for it in items]
            amap = alchemy_live(base_holder[0], contract, ids)
            for it in items:
                it["a"] = amap.get(str(int(it["s"].rsplit("/", 1)[1])), "")
            changed += len(items)
        else:
            for it in items:
                it.setdefault("a", "")
    if changed:
        open(pf, "w", encoding="utf-8").write(json.dumps(d))
    return changed


def main():
    only = sys.argv[1] if len(sys.argv) > 1 else None
    files = [f"pools/{only}.json"] if only else sorted(glob.glob("pools/*.json"))
    base_holder = [None]
    total = 0
    for pf in files:
        n = enrich(pf, base_holder)
        if n:
            print(f"{os.path.basename(pf)[:-5]}: +a on {n} pieces")
            total += n
    print("DONE, enriched", total, "pieces")


if __name__ == "__main__":
    main()
