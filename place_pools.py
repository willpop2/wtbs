"""
Auto-place [pool:] markers into an episode transcript.

For episodes wired to snapshot pools (pools/<slug>.json), this inserts one pool
slot per work into transcripts/final/<slug>.txt — evenly distributed for reading
rhythm, ordered by where each work is first discussed. Idempotent: strips any
existing img/pool markers first, so re-running re-places cleanly.

    python place_pools.py Nudoru Jeres
"""

import csv
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent
FINAL = ROOT / "transcripts" / "final"
POOLS = ROOT / "pools"
MARKER = re.compile(r"^\s*\[(img|pool):.*\]\s*$")
norm = lambda s: re.sub(r"[^a-z0-9]", "", (s or "").lower())
MIN_GAP = 3       # min transcript turns between image slots (avoid clumping)
MAX_GAP = 6       # after this many imageless turns, drop one from the most-recent work
FIRST_COUNT = 3   # first placed image of a STATIC work -> triptych (show the generative range)
GAP_COUNT = 1     # gap-fillers -> a single image


def _load_animated():
    """(work, artist) pairs tagged animated — these always get a single, full-size slot
    (never paired/trio) since they run live and need the space."""
    s = set()
    p = ROOT / "animated_works.csv"
    if p.exists():
        for r in csv.DictReader(p.open(encoding="utf-8")):
            s.add((norm(r["work"]), norm(r.get("artist", ""))))
    return s


ANIMATED = _load_animated()


def place(slug, min_gap=MIN_GAP, max_gap=MAX_GAP):
    data = json.loads((POOLS / f"{slug}.json").read_text(encoding="utf-8"))
    artists = data.get("artists", {})
    works = [w for w, items in data["works"].items() if items]   # only works that have pieces
    counts = {w: len(data["works"][w]) for w in works}
    text = (FINAL / f"{slug}.txt").read_text(encoding="utf-8")
    blocks = [b for b in text.split("\n\n") if b.strip() and not MARKER.match(b.strip())]
    T = len(blocks)
    nb = [norm(b) for b in blocks]
    nw = {w: norm(w) for w in works}

    def marker(w, cnt):
        art = artists.get(w, "")
        if (norm(w), norm(art)) in ANIMATED:   # animated works always solo (need the space)
            cnt = 1
        cap = (f"{w} — {art}" if art else w).replace("|", "/").replace("]", ")")
        return f"[pool: {w} | {cap} | | {min(cnt, counts.get(w, 1))}]"

    # Walk the transcript once. Anchor an image right after a block that mentions a
    # work; the FIRST time a work appears show a triptych; long mention-free stretches
    # get a filler from the most-recent work. A per-work cap keeps any one work from
    # dominating (generic names like "Web" match all over), and gap-fillers top up the
    # least-used work once the recent one is capped — so works spread evenly.
    placed = {w: 0 for w in works}
    cap = max(4, round(1.5 * max(1, T // max_gap) / max(1, len(works))))
    sched, last, last_ref, seen = {}, -10 ** 9, None, set()
    for i in range(T):
        ms = [w for w in works if nw[w] and nw[w] in nb[i]]
        if ms:
            last_ref = ms[0]
            avail = [w for w in ms if placed[w] < cap]
            if avail and i + 1 - last >= min_gap:               # anchor right after the mention
                w = min(avail, key=lambda x: (x in seen, placed[x]))   # unshown, then least-used
                sched.setdefault(i + 1, []).append(marker(w, FIRST_COUNT if w not in seen else 1))
                seen.add(w); placed[w] += 1; last = i + 1
        elif last_ref and (i + 1 - last) >= max_gap:            # long gap -> top up
            avail = [w for w in works if placed[w] < cap]
            if avail:
                w = last_ref if placed.get(last_ref, cap) < cap else min(avail, key=lambda x: placed[x])
                sched.setdefault(i + 1, []).append(marker(w, FIRST_COUNT if w not in seen else GAP_COUNT))
                seen.add(w); placed[w] += 1; last = i + 1

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
