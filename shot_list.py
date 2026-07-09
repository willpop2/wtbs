"""
Generate an image "shot list" for the interviews.

For each episode, scans transcripts/final/<slug>.txt for italicized work titles
(the works actually discussed), and reports each one with how often it's
mentioned, roughly where it first comes up, a snippet of context, and a
ready-to-paste image marker. Use it to know which images to collect.

    python shot_list.py                 # all interviews -> shot_list.md
    python shot_list.py --only Remnynt,Zancan   # just these (also prints)
    python shot_list.py --top 6         # cap works listed per episode
"""

import argparse
import csv
import re
from pathlib import Path

import build_site as b  # reuse clean_guest / display_title

ROOT = Path(__file__).parent
FINAL = ROOT / "transcripts" / "final"
ITALIC = re.compile(r"\*([^*\n]+)\*")
# Skip obvious non-works that sometimes get italicized.
STOP = {"and", "the", "or", "but", "so", "a", "an", "i", "it", "yeah", "okay",
        "waiting to be signed", "wtbs"}


def slugify_work(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:40] or "image"


def sentence_with(block: str, work: str) -> str:
    body = re.sub(r"^[^:\n]{1,40}:\s*", "", block)          # drop speaker label
    for s in re.split(r"(?<=[.!?])\s+", body):
        if f"*{work}*" in s:
            return re.sub(r"\*([^*\n]+)\*", r"\1", s).strip()[:160]
    return re.sub(r"\*([^*\n]+)\*", r"\1", body).strip()[:160]


def episode_shots(slug: str, top: int) -> list:
    text = (FINAL / f"{slug}.txt").read_text(encoding="utf-8")
    blocks = [x for x in text.split("\n\n") if x.strip()]
    total = len(blocks)
    works = {}
    for i, block in enumerate(blocks):
        for w in ITALIC.findall(block):
            w = w.strip()
            if not w or len(w) < 2 or w.lower() in STOP:
                continue
            # merge simple singular/plural duplicates (Monogrid / Monogrids)
            if w + "s" in works:
                w = w + "s"
            elif w.endswith("s") and w[:-1] in works:
                w = w[:-1]
            if w not in works:
                works[w] = {"count": 0, "first": i, "ctx": sentence_with(block, w)}
            works[w]["count"] += 1
    ranked = sorted(works.items(), key=lambda kv: (-kv[1]["count"], kv[1]["first"]))
    return total, ranked[:top]


def main() -> None:
    ap = argparse.ArgumentParser(description="Generate an image shot list.")
    ap.add_argument("--only", default=None, help="Comma-separated slugs.")
    ap.add_argument("--top", type=int, default=8, help="Max works per episode.")
    args = ap.parse_args()

    rows = list(csv.DictReader((ROOT / "episodes.csv").open(encoding="utf-8")))
    if args.only:
        want = {s.strip() for s in args.only.split(",")}
        rows = [r for r in rows if r["slug"] in want]

    lines = ["# WTBS interview shot list\n",
             "Italicized works discussed in each interview, with mention count, "
             "roughly where it first comes up, context, and a paste-ready marker.\n"]
    for r in rows:
        if not (FINAL / f"{r['slug']}.txt").exists():
            continue
        guest = b.clean_guest(r["guests"])
        total, shots = episode_shots(r["slug"], args.top)
        lines.append(f"\n## {r['slug']} — {b.display_title(r['title'], guest)} · {guest}")
        if not shots:
            lines.append("_No italicized works found._")
            continue
        for w, info in shots:
            pct = round(100 * info["first"] / max(total, 1))
            marker = f"[img: {r['slug']}-{slugify_work(w)}.jpg | {w} — {guest} | ]"
            lines.append(
                f"- **{w}** — {info['count']}× · first ~turn {info['first']}/{total} ({pct}% in)\n"
                f"  - context: \"{info['ctx']}\"\n"
                f"  - marker: `{marker}`")

    out = ROOT / "shot_list.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {out} ({len([r for r in rows])} episodes)")
    if args.only:
        print("\n" + "\n".join(lines))


if __name__ == "__main__":
    main()
