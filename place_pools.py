"""
Auto-place [pool:] markers into an episode transcript.

For episodes wired to snapshot pools (pools/<slug>.json), this inserts one pool
slot per work into transcripts/final/<slug>.txt — evenly distributed for reading
rhythm, ordered by where each work is first discussed. Idempotent: strips any
existing img/pool markers first, so re-running re-places cleanly.

    python place_pools.py Nudoru Jeres
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent
FINAL = ROOT / "transcripts" / "final"
POOLS = ROOT / "pools"
MARKER = re.compile(r"^\s*\[(img|pool):.*\]\s*$")
norm = lambda s: re.sub(r"[^a-z0-9]", "", (s or "").lower())
PER_WORK = 2    # max images per work (from its different mentions)
MIN_GAP = 3     # min transcript turns between consecutive images
CAP = 16        # safety cap per episode


def place(slug, per_work=PER_WORK, min_gap=MIN_GAP):
    data = json.loads((POOLS / f"{slug}.json").read_text(encoding="utf-8"))
    artists = data.get("artists", {})
    works = [w for w, items in data["works"].items() if items]   # only works that have pieces
    text = (FINAL / f"{slug}.txt").read_text(encoding="utf-8")
    blocks = [b for b in text.split("\n\n") if b.strip() and not MARKER.match(b.strip())]
    T = len(blocks)
    nb = [norm(b) for b in blocks]

    # candidate placements: put an image just AFTER a block that mentions the work,
    # up to per_work spread-out mentions per work (so popular works get more images).
    cands = []
    for w in works:
        refs = [i for i, b in enumerate(nb) if norm(w) and norm(w) in b] or [T // 2]
        if len(refs) <= per_work:
            picks = refs
        else:
            picks = [refs[round(k * (len(refs) - 1) / (per_work - 1))] for k in range(per_work)]
        cands += [(r, w) for r in picks]

    # greedy left-to-right, keeping a minimum gap so images don't clump
    cands.sort()
    sched, last = {}, -10 ** 9
    for turn, w in cands:
        pos = min(T, turn + 1)               # right after the mention block
        if pos - last < min_gap or len(sched) >= CAP:
            continue
        art = artists.get(w, "")
        cap = f"{w} — {art}" if art else w
        cap = cap.replace("|", "/").replace("]", ")")   # | and ] are marker delimiters
        sched.setdefault(pos, []).append(f"[pool: {w} | {cap} | ]")
        last = pos

    out = []
    for i, b in enumerate(blocks):
        out.extend(sched.get(i, []))         # insert-before-block-i == after mention block i-1
        out.append(b)
    out.extend(sched.get(len(blocks), []))
    (FINAL / f"{slug}.txt").write_text("\n\n".join(out), encoding="utf-8")
    return sum(len(v) for v in sched.values())


def main():
    for slug in sys.argv[1:]:
        if (POOLS / f"{slug}.json").exists():
            print(f"{slug}: placed {place(slug)} pool slots")
        else:
            print(f"{slug}: no pools/{slug}.json — snapshot first")


if __name__ == "__main__":
    main()
