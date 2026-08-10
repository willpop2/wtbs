"""
Cross-corpus mention index for the WTBS site.

Builds a searchable index of ARTISTS + WORK TITLES -> the episodes that mention
them (both the 82 published interviews and the 136 numbered/weekly episodes),
with per-episode mention counts and one short context snippet each.

The numbered-episode transcripts are NOT published as readable pages; only this
entity index (name -> episodes + counts + a one-line snippet) is emitted, so an
artist like "Zancan" can be found across the whole archive without exposing the
full numbered transcripts.

    build_search() -> (entities, numbered)   # consumed by build_site.py
    python search_index.py                    # writes site/search.json for a quick look
"""

import csv
import glob
import json
import os
import re
import collections
import html as htmllib
from pathlib import Path

ROOT = Path(__file__).parent
FINAL = ROOT / "transcripts" / "final"
NUM = ROOT / "transcripts" / "clean_numbered"

MAX_EPS = 120          # cap episodes listed per entity (sorted by count)
SNIP_MAX = 160         # snippet length cap
ARTIST_STOP = {"various", "operator", "will", "trinity"}
WORK_STOP = {"waiting to be signed", "wtbs", "will", "trinity", "the", "a", "an",
             "here", "now", "yes", "no", "ok"}
_span = re.compile(r"\*([A-Za-z0-9][^*\n]{0,48}?)\*")


def _read(p): return Path(p).read_text(encoding="utf-8", errors="ignore")


def _num_sort(slug):
    m = re.match(r"E(\d+)$", slug)
    return (0, int(m.group(1))) if m else (1, slug.lower())


def numbered_meta():
    """[{slug, title, words}] for the numbered episodes, from numbered_index.md,
    intersected with the transcripts we actually have."""
    have = {os.path.splitext(os.path.basename(f))[0] for f in glob.glob(str(NUM / "*.txt"))}
    out = []
    for line in _read(ROOT / "numbered_index.md").splitlines():
        m = re.match(r"\|\s*`([^`]+)`\s*\|\s*([^|]+?)\s*\|\s*([\d,]+)\s*\|", line)
        if m and m.group(1) in have:
            out.append({"slug": m.group(1), "title": m.group(2).strip(), "words": m.group(3)})
    listed = {o["slug"] for o in out}
    for s in sorted(have - listed, key=_num_sort):     # any transcript missing from the index
        out.append({"slug": s, "title": s.replace("_", " "), "words": ""})
    out.sort(key=lambda o: _num_sort(o["slug"]))
    return out


def _artists():
    arts = {}
    for r in csv.DictReader((ROOT / "episodes_metadata.csv").open(encoding="utf-8")):
        g = (r.get("guest") or "").strip()
        if len(g) >= 3:
            arts[g.lower()] = g
    for f in glob.glob(str(ROOT / "pools" / "*.json")):
        try:
            d = json.load(open(f, encoding="utf-8"))
        except Exception:
            continue
        for a in (d.get("artists") or {}).values():
            for part in re.split(r"\s*&\s*|,|\band\b", a):
                part = part.strip()
                if len(part) >= 3:
                    arts.setdefault(part.lower(), part)
    return {k: v for k, v in arts.items() if k not in ARTIST_STOP}


def _works():
    """Italicized work titles appearing in >=2 files, or present in any pool."""
    files = collections.defaultdict(set)
    disp = {}
    for fp in list(glob.glob(str(FINAL / "*.txt"))) + list(glob.glob(str(NUM / "*.txt"))):
        for m in _span.finditer(_read(fp)):
            if ":" in m.group(1):
                continue
            raw = re.sub(r"[’']s$", "", m.group(1).strip().strip(' "\'.,;:!?()[]'))
            if not raw:
                continue
            k = raw.lower()
            if k in WORK_STOP:
                continue
            files[k].add(fp)
            disp[k] = raw
    poolworks = set()
    for f in glob.glob(str(ROOT / "pools" / "*.json")):
        try:
            d = json.load(open(f, encoding="utf-8"))
        except Exception:
            continue
        poolworks |= {w.lower() for w in (d.get("works") or {})}
    # a real title: in a pool, OR appears in >=2 files AND is capitalized (drops
    # lowercase emphasis italics like *really* / *actually*).
    return {k: disp[k] for k in disp
            if k in poolworks or (len(files[k]) >= 2 and disp[k][:1].isupper())}


def _snippet(text, start, end):
    a = text.rfind(".", 0, start)
    a = a + 1 if a >= 0 and start - a < 220 else max(0, start - 90)
    b = text.find(".", end)
    b = b + 1 if b >= 0 and b - end < 220 else min(len(text), end + 90)
    s = re.sub(r"\s+", " ", text[a:b]).strip()
    if len(s) > SNIP_MAX:
        s = s[:SNIP_MAX].rsplit(" ", 1)[0] + "…"
    return s


def build_search():
    """Returns (entities, numbered). One pass per transcript: a single italic-span
    scan (works) + one combined artist regex (artists), so it's O(transcripts).
    entities: [{"n": name, "t": "artist"|"work", "total": int,
                "iv": [[slug,count,snip],...], "nm": [[slug,count,snip],...],
                "iv_more": int, "nm_more": int}]   (iv = interviews, nm = numbered)
    numbered: [{slug, title, words, artists:[...], works:[...]}] for the minimal pages."""
    interviews = sorted(os.path.splitext(os.path.basename(f))[0] for f in glob.glob(str(FINAL / "*.txt")))
    numbered = numbered_meta()
    texts = {("iv", s): _read(FINAL / f"{s}.txt") for s in interviews}
    texts.update({("nm", o["slug"]): _read(NUM / f"{o['slug']}.txt") for o in numbered})

    artists, works = _artists(), _works()
    artist_names = set(artists.values())
    names_sorted = sorted(artists.values(), key=len, reverse=True)      # longest-first
    art_rx = re.compile(r"(?<![A-Za-z0-9])(" + "|".join(re.escape(n) for n in names_sorted)
                        + r")(?![A-Za-z0-9])", re.I) if names_sorted else None

    acc = collections.defaultdict(dict)                     # (typ,name) -> {(kind,slug): [count, first_pos]}
    per_ep = collections.defaultdict(lambda: collections.defaultdict(int))  # (kind,slug) -> name -> count

    def bump(typ, name, kind, slug, pos):
        d = acc[(typ, name)].get((kind, slug))
        if d:
            d[0] += 1
        else:
            acc[(typ, name)][(kind, slug)] = [1, pos]
        per_ep[(kind, slug)][name] += 1

    for (kind, slug), text in texts.items():
        for m in _span.finditer(text):                      # works, via italic titles
            if ":" in m.group(1):
                continue
            raw = re.sub(r"[’']s$", "", m.group(1).strip().strip(' "\'.,;:!?()[]'))
            w = works.get(raw.lower())
            if w:
                bump("work", w, kind, slug, m.start())
        if art_rx:
            for m in art_rx.finditer(text):                 # artists, one combined pass
                canon = artists.get(m.group(1).lower())
                if canon:
                    bump("artist", canon, kind, slug, m.start())

    entities = []
    for (typ, name), eps in acc.items():
        iv, nm, total = [], [], 0
        for (kind, slug), (cnt, pos) in eps.items():
            total += cnt
            snip = _snippet(texts[(kind, slug)], pos, pos + len(name))
            (iv if kind == "iv" else nm).append([slug, cnt, snip])
        iv.sort(key=lambda x: -x[1]); nm.sort(key=lambda x: -x[1])
        entities.append({"n": name, "t": typ, "total": total,
                         "iv": iv[:MAX_EPS], "nm": nm[:MAX_EPS],
                         "iv_more": max(0, len(iv) - MAX_EPS), "nm_more": max(0, len(nm) - MAX_EPS)})
    entities.sort(key=lambda e: -e["total"])

    for o in numbered:                                      # what each numbered ep mentions
        ranked = sorted(per_ep.get(("nm", o["slug"]), {}).items(), key=lambda kv: -kv[1])
        o["artists"] = [n for n, _ in ranked if n in artist_names][:12]
        o["works"] = [n for n, _ in ranked if n not in artist_names][:16]
    return entities, numbered


if __name__ == "__main__":
    ents, num = build_search()
    (ROOT / "site").mkdir(exist_ok=True)
    payload = {"entities": ents}
    (ROOT / "site" / "search.json").write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    z = next((e for e in ents if e["n"] == "Zancan"), None)
    print(f"entities: {len(ents)}  |  numbered: {len(num)}")
    print(f"search.json bytes: {(ROOT/'site'/'search.json').stat().st_size:,}")
    if z:
        print(f"Zancan: {len(z['iv'])} interviews (+{z['iv_more']}), {len(z['nm'])} numbered (+{z['nm_more']}), total {z['total']}")
        print("  sample numbered:", z["nm"][0])
