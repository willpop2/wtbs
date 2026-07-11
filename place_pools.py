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
CAP = 8   # max slots per episode


def place(slug):
    data = json.loads((POOLS / f"{slug}.json").read_text(encoding="utf-8"))
    artists = data.get("artists", {})
    works = [w for w, items in data["works"].items() if items]   # only works that have pieces
    text = (FINAL / f"{slug}.txt").read_text(encoding="utf-8")
    blocks = [b for b in text.split("\n\n") if b.strip() and not MARKER.match(b.strip())]
    T = len(blocks)
    nb = [norm(b) for b in blocks]

    # anchor each work at its first mention (else spread to the middle)
    anchored = []
    for w in works:
        refs = [i for i, b in enumerate(nb) if norm(w) and norm(w) in b]
        anchored.append((refs[0] if refs else T // 2, w))
    anchored.sort(key=lambda x: x[0])
    anchored = anchored[:CAP]

    # even slots across the transcript, assigned in reference order
    n = len(anchored)
    slots = [min(T - 1, max(2, round((k + 1) * T / (n + 1)))) for k in range(n)]
    sched = {}
    for (_, w), pos in zip(anchored, slots):
        art = artists.get(w, "")
        cap = f"{w} — {art}" if art else w
        sched.setdefault(pos, []).append(f"[pool: {w} | {cap} | ]")

    out = []
    for i, b in enumerate(blocks):
        out.extend(sched.get(i, []))
        out.append(b)
    (FINAL / f"{slug}.txt").write_text("\n\n".join(out), encoding="utf-8")
    return n


def main():
    for slug in sys.argv[1:]:
        if (POOLS / f"{slug}.json").exists():
            print(f"{slug}: placed {place(slug)} pool slots")
        else:
            print(f"{slug}: no pools/{slug}.json — snapshot first")


if __name__ == "__main__":
    main()
