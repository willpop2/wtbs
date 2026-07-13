"""
Copy already-pooled works into episodes that reference them.

The ✅ rows in MANUAL_IMAGES.md are works by other artists that are already
snapshotted on some other episode's pool. Rather than re-fetch them, this copies
the items straight from the richest existing pools/<slug>.json into the
referencing episode's pool (keeping the real artist credit). Run AFTER
snapshot_pools and BEFORE place_pools.
"""
import re, json, glob
from pathlib import Path

ROOT = Path(__file__).parent
norm = lambda s: re.sub(r"[^a-z0-9]", "", (s or "").lower())

# index every pooled work (>=10 pieces) -> richest (items, artist)
idx = {}
for pf in glob.glob(str(ROOT / "pools" / "*.json")):
    d = json.loads(Path(pf).read_text(encoding="utf-8"))
    for w, items in d["works"].items():
        if len(items) >= 10 and (norm(w) not in idx or len(items) > len(idx[norm(w)][0])):
            idx[norm(w)] = (items, d.get("artists", {}).get(w, ""))

# ✅ works per episode from the doc
row = re.compile(r"^- \*\*(.+?)\*\* — contract/link: `[^`]*`(.*)$")
head = re.compile(r"^### .*`\[(.+?)\]`")
reuse, ep = {}, None
for ln in (ROOT / "MANUAL_IMAGES.md").read_text(encoding="utf-8").splitlines():
    h = head.match(ln)
    if h:
        ep = h.group(1)
    m = row.match(ln)
    if m and "wired via" in m.group(2) and ep:
        reuse.setdefault(ep, []).append(m.group(1).strip())

filled = 0
for ep, works in reuse.items():
    pf = ROOT / "pools" / f"{ep}.json"
    if not pf.exists():
        continue
    d = json.loads(pf.read_text(encoding="utf-8"))
    for w in works:
        if norm(w) in idx and w not in d["works"]:
            items, artist = idx[norm(w)]
            d["works"][w] = items
            d.setdefault("artists", {})[w] = artist
            filled += 1
    pf.write_text(json.dumps(d), encoding="utf-8")
print(f"apply_reuse: copied {filled} reused works across {len(reuse)} episodes")
