"""
Generate the static WTBS website ("ledger" design) from the transcripts.

Reads episodes.csv + the RSS feed + the transcripts and renders a searchable
"Ledger" index plus one page per episode into site/. Audio is referenced from
../audio/ with a download link. Reader edit-suggestions post to a Cloudflare
Worker (WTBS_SUGGEST_ENDPOINT).
"""

import csv
import html as htmllib
import json
import os
import re
import shutil
import xml.etree.ElementTree as ET
from collections import Counter
from email.utils import parsedate_to_datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

ROOT = Path(__file__).parent
SITE = ROOT / "site"
CLEAN = ROOT / "transcripts" / "clean"
FINAL = ROOT / "transcripts" / "final"
RAW_ASR = ROOT / "transcripts" / "raw"
IMAGES = ROOT / "images"
FEED = ROOT / "scratch_feed.xml"
# Deployed suggestion Worker (public URL, not a secret). Override with the env var.
SUGGEST_ENDPOINT = os.environ.get(
    "WTBS_SUGGEST_ENDPOINT", "https://wtbs-suggest.willpop2.workers.dev")

# Show-wide handles (real, from the brief).
SHOW = {
    "twitter": "https://twitter.com/waitingtosign",
    "spotify": "https://open.spotify.com/show/1mCgOIE98vpVpE9nRzWfrM",
    "patreon": "https://patreon.com/WaitingToBeSigned",
}
BIG3 = {"fx(hash)", "Art Blocks", "Verse"}
PLATFORM_KEY = {"fx(hash)": "fxhash", "Art Blocks": "art-blocks", "Verse": "verse"}

# platform display name -> detection regex
PLATFORMS = [
    ("fx(hash)", r"fx\(?hash\)?|fxhash"), ("Art Blocks", r"art\s*blocks"),
    ("Verse", r"\bverse\b"), ("Tezos", r"\btezos\b"),
    ("Bright Moments", r"bright\s*moments"), ("Feral File", r"feral\s*file"),
    ("Highlight", r"highlight"), ("Tonic", r"tonic"), ("TriliTech", r"trili?tech"),
    ("OpenSea", r"opensea"), ("Ethereum", r"ethereum"),
]
# well-known platform founders whose role isn't in the title
FOUNDERS = {"erick calderon": "Art Blocks", "snowfro": "Art Blocks",
            "ciphrd": "fx(hash)", "bre pettis": "Bright Moments"}


def feed_metadata() -> dict:
    root = ET.parse(FEED).getroot()
    ns = {"i": "http://www.itunes.com/dtds/podcast-1.0.dtd"}
    meta = {}
    for it in root.findall(".//item"):
        title = (it.findtext("title") or "").strip()
        d = parsedate_to_datetime(it.findtext("pubDate")) if it.findtext("pubDate") else None
        dur = it.findtext("i:duration", namespaces=ns) or ""
        secs = 0
        if ":" in dur:
            p = [int(x) for x in dur.split(":")]
            secs = p[0] * 3600 + p[1] * 60 + p[2] if len(p) == 3 else p[0] * 60 + p[1]
        desc = re.sub(r"<[^>]+>", " ", it.findtext("description") or "")
        desc = re.sub(r"\s+", " ", htmllib.unescape(desc)).strip()
        enc = it.find("enclosure")
        audio_url = enc.get("url") if enc is not None else ""
        meta[title] = {"dt": d, "secs": secs, "description": desc,
                       "audio_url": audio_url}
    return meta, len(root.findall(".//item"))


def hm(secs: int) -> str:
    return f"{secs // 3600}:{(secs % 3600) // 60:02d}" if secs else ""


def clean_guest(raw: str) -> str:
    return re.sub(r"^\s*artist\s+", "", raw, flags=re.I).strip()


def display_title(title: str, guest: str = "") -> str:
    t = re.sub(r"\s*[-:–—]\s*interview\s+(?:with|w/).*$", "", title, flags=re.I)
    t = re.sub(r"^\s*interview\s+(?:with|w/)\s+.*$", "", t, flags=re.I)
    t = re.sub(r"\s+interview\s*$", "", t, flags=re.I)
    t = t.strip().rstrip("!:–—- ").strip()
    return t or (f"Interview with {guest}" if guest else title)


def summary_from(desc: str) -> str:
    if not desc:
        return ""
    cut = re.split(r"\bin this episode\b|\bwe discuss\b|Follow ", desc, flags=re.I)[0].strip()
    return " ".join(re.split(r"(?<=[.!?])\s+", cut)[:2]).strip()[:320]


def detect_platform(text: str) -> str:
    low = text.lower()
    counts = [(name, len(re.findall(rx, low))) for name, rx in PLATFORMS]
    counts.sort(key=lambda c: -c[1])
    return counts[0][0] if counts and counts[0][1] else ""


def role_and_platform(title: str, guests: str, text: str) -> tuple:
    src = f"{title} {guests}"
    m = re.search(r"\b(co-?founder|founder|director|head)\b[^,]*?\b(?:of|at)\s+"
                  r"([A-Za-z0-9.()/ ]{2,22})", src, re.I)
    if m:
        role_word = m.group(1).lower().replace("co-founder", "Co-founder").replace(
            "cofounder", "Co-founder")
        role_word = role_word if role_word.startswith("Co") else role_word.capitalize()
        plat = detect_platform(m.group(2)) or m.group(2).strip().title()
        return f"{role_word}, {plat}", plat
    key = re.sub(r"\(.*?\)", "", clean_guest(guests)).strip().lower()
    if key in FOUNDERS:
        return f"Founder, {FOUNDERS[key]}", FOUNDERS[key]
    return "Generative artist", detect_platform(text)


GREETING = re.compile(r"\b(thank you|thanks for having|nice to be here|happy to be here|"
                      r"great to be here|good to be here|um|uh)\b", re.I)


def pull_quote(text: str) -> str:
    """A short, punchy, self-contained line from the guest, for the quote strip."""
    for block in text.split("\n\n"):
        if block.lstrip().startswith("[img:"):   # never quote an image marker
            continue
        m = re.match(r"^([^:\n]{1,40}):\s*(.*)$", block.strip(), re.DOTALL)
        who, body = (m.group(1), m.group(2)) if m else ("", block.strip())
        if who in ("Will", "Trinity"):
            continue
        for s in re.split(r"(?<=[.!?])\s+", body):
            s = s.strip()
            words = s.split()
            if 9 <= len(words) <= 26 and len(s) <= 170 and s[0].isupper() \
                    and "*" not in s and not GREETING.search(s):
                return s
    return ""


BASELINE_ENTRY = {"date": "", "summary": "Initial transcript — auto-transcribed "
                  "(AssemblyAI) and readability-edited.", "credit": ""}


def load_changelog() -> dict:
    """Read changelog.csv (slug,date,summary,credit) -> {slug: [entries newest-first]}."""
    log = {}
    p = ROOT / "changelog.csv"
    if p.exists():
        for r in csv.DictReader(p.open(encoding="utf-8")):
            slug = (r.get("slug") or "").strip()
            if not slug:
                continue
            log.setdefault(slug, []).append({
                "date": (r.get("date") or "").strip(),
                "summary": (r.get("summary") or "").strip(),
                "credit": (r.get("credit") or "").strip(),
            })
    for slug in log:
        log[slug].sort(key=lambda e: e["date"], reverse=True)
    return log


def guest_type(role: str, bio: str) -> str:
    if role != "Generative artist":
        return "builder"
    low = bio.lower()[:400]
    if "collector" in low and "artist" not in low[:120]:
        return "collector"
    if "curator" in low:
        return "curator"
    return "artist"


def extract_links(bio: str) -> dict:
    links = {}
    m = re.search(r"twitter[^@]{0,12}@\s*([A-Za-z0-9_]{2,20})", bio, re.I) \
        or re.search(r"@([A-Za-z0-9_]{3,20})\b", bio)
    if m:
        links["twitter"] = "https://twitter.com/" + m.group(1)
    for u in re.findall(r"\b([a-z0-9-]+\.(?:art|xyz|io|com|studio|design)(?:/\S*)?)", bio, re.I):
        dom = u.lower()
        if not any(s in dom for s in ("twitter", "fxhash", "artblocks", "opensea",
                                      "spotify", "apple", "youtube", "anchor", "patreon")):
            links["website"] = "https://" + u if not u.startswith("http") else u
            break
    return links


LINK_RE = re.compile(r"\[([^\]]+)\]\((https?://[^)\s]+)\)")


def _esc_em(s: str) -> str:
    return re.sub(r"\*([^*\n]+)\*", r"<em>\1</em>", htmllib.escape(s))


def render_inline(text: str) -> str:
    # markdown links [label](url) (label may itself be *italic*), then italics
    out, pos = [], 0
    for m in LINK_RE.finditer(text):
        out.append(_esc_em(text[pos:m.start()]))
        url = htmllib.escape(m.group(2), quote=True)
        out.append(f'<a href="{url}" target="_blank" rel="noopener">'
                   f'{_esc_em(m.group(1))}</a>')
        pos = m.end()
    out.append(_esc_em(text[pos:]))
    return "".join(out)


# Image marker placed on its own line/block between turns:
#   [img: filename.jpg | caption (optional) | credit-URL (optional)]
IMG_RE = re.compile(r"^\[img:\s*([^|\]]+?)\s*(?:\|\s*([^|\]]*?))?\s*(?:\|\s*([^|\]]*?))?\s*\]$")


def render_figure(m, slug: str) -> str:
    # filename field may be a comma-separated list -> gallery of one work's outputs
    files = [f.strip() for f in m.group(1).split(",") if f.strip()]
    caption = (m.group(2) or "").strip()
    credit = (m.group(3) or "").strip()
    imgs = []
    for fn in files:
        # bare filename -> self-hosted under images/<slug>/; full URL/path used as-is
        src = fn if re.match(r"^(https?:)?/", fn) else f"images/{slug}/{fn}"
        imgs.append(f'<img src="{htmllib.escape(src)}" '
                    f'alt="{htmllib.escape(caption)}" loading="lazy">')
    cap = ""
    if caption or credit:
        inner = htmllib.escape(caption)
        if credit:
            inner += (" &middot; " if caption else "") + \
                f'<a href="{htmllib.escape(credit)}" target="_blank" rel="noopener">source</a>'
        cap = f"<figcaption>{inner}</figcaption>"
    if len(imgs) == 2:
        cls = "ep-figure ep-pair"          # two side by side
    elif len(imgs) > 2:
        cls = "ep-figure ep-gallery"       # 3+ fallback grid
    else:
        cls = "ep-figure"                  # single
    grid = f' style="--n:{len(imgs)}"' if len(imgs) > 2 else ""
    return f'<figure class="{cls}"{grid}>{"".join(imgs)}{cap}</figure>'


# Random-pool slot: [pool: <work-prefix> | caption | credit-url]
# Filled at page load with a random image from images/<slug>/<prefix>_*.
POOL_RE = re.compile(r"^\[pool:\s*([^|\]]+?)\s*(?:\|\s*([^|\]]*?))?\s*(?:\|\s*([^|\]]*?))?\s*\]$")


def pool_manifest(slug: str) -> dict:
    """Group an episode's images by work-prefix (strip trailing _<id>.<ext>)."""
    d = IMAGES / slug
    pools = {}
    if d.exists():
        for f in sorted(p.name for p in d.iterdir() if p.is_file()):
            key = re.sub(r"_[^_]+\.[^.]+$", "", f)
            pools.setdefault(key, []).append(f)
    return pools


def render_pool(m) -> str:
    work = m.group(1).strip()
    caption = (m.group(2) or "").strip()
    credit = (m.group(3) or "").strip()
    cap = ""
    if caption or credit:
        inner = htmllib.escape(caption)
        if credit:
            inner += (" &middot; " if caption else "") + \
                f'<a href="{htmllib.escape(credit)}" target="_blank" rel="noopener">source</a>'
        cap = f"<figcaption>{inner}</figcaption>"
    return (f'<figure class="ep-figure ep-pool" data-pool="{htmllib.escape(work)}" '
            f'data-alt="{htmllib.escape(caption)}">{cap}</figure>')


def render_transcript(raw: str, slug: str = "") -> str:
    blocks = [b.strip() for b in raw.split("\n\n") if b.strip()]
    cand = Counter()
    for b in blocks:
        if IMG_RE.match(b) or POOL_RE.match(b):
            continue
        m = re.match(r"^([^\n:]{1,38}):\s", b)
        if m:
            cand[m.group(1).strip()] += 1
    speakers = {n for n, c in cand.items() if c >= 3} | ({"Will", "Trinity"} & set(cand))
    label_re = None
    if speakers:
        alt = "|".join(re.escape(s) for s in sorted(speakers, key=len, reverse=True))
        label_re = re.compile(r"^(" + alt + r"):\s*(.*)$", re.DOTALL)
    out = []
    for i, b in enumerate(blocks):
        img = IMG_RE.match(b)
        if img:
            out.append(render_figure(img, slug))
            continue
        pool = POOL_RE.match(b)
        if pool:
            out.append(render_pool(pool))
            continue
        m = label_re.match(b) if label_re else None
        if m:
            out.append(f'<p class="turn" data-idx="{i}"><span class="who">'
                       f'{htmllib.escape(m.group(1))}:</span> {render_inline(m.group(2).strip())}</p>')
        else:
            out.append(f'<p class="turn cont" data-idx="{i}">{render_inline(b)}</p>')
    return "\n".join(out)


def main() -> None:
    meta, feed_total = feed_metadata()
    changelog = load_changelog()
    env = Environment(loader=FileSystemLoader(str(ROOT / "templates")), autoescape=False)
    FINAL.mkdir(parents=True, exist_ok=True)

    episodes = []
    for r in csv.DictReader((ROOT / "episodes.csv").open(encoding="utf-8")):
        final_path, clean_path = FINAL / f"{r['slug']}.txt", CLEAN / f"{r['slug']}.txt"
        if not final_path.exists() and clean_path.exists():
            shutil.copy(clean_path, final_path)
        src = final_path if final_path.exists() else clean_path
        if not src.exists():
            continue
        m = meta.get(r["title"], {})
        dt = m.get("dt")
        guest = clean_guest(r["guests"])
        raw = src.read_text(encoding="utf-8")
        bio = (ROOT / r["bio_file"]).read_text(encoding="utf-8") if (ROOT / r["bio_file"]).exists() else ""
        role, platform = role_and_platform(r["title"], r["guests"], bio + " " + raw[:3000])
        asr_path = RAW_ASR / f"{r['slug']}.txt"
        asr = asr_path.read_text(encoding="utf-8") if asr_path.exists() else ""
        episodes.append({
            "slug": r["slug"], "type": "Interview", "title": r["title"],
            "display_title": display_title(r["title"], guest), "guest": guest,
            "date_str": f"{dt:%B} {dt.day}, {dt.year}" if dt else "",
            "date_short": f"{dt:%b %Y}".upper() if dt else "",
            "year": dt.year if dt else 0, "date_sort": dt.timestamp() if dt else 0,
            "duration": hm(m.get("secs", 0)), "role": role, "platform": platform,
            "platform_key": PLATFORM_KEY.get(platform, "other"),
            "guest_type": guest_type(role, bio), "is_founder": role.startswith("Founder"),
            "summary": summary_from(m.get("description", "")),
            "audio_src": m.get("audio_url") or f"../audio/{r['audio_file']}",
            "transcript_html": render_transcript(raw, r["slug"]),
            "raw_html": render_transcript(asr, r["slug"]) if asr else "",
            "pools": pool_manifest(r["slug"]),
            "links": extract_links(bio), "quote": pull_quote(raw),
            "changelog": changelog.get(r["slug"], []) + [BASELINE_ENTRY],
            "edit_count": len(changelog.get(r["slug"], [])),
            "search": f"{r['title']} {guest} {role} {platform}".lower(),
        })

    episodes.sort(key=lambda e: e["date_sort"], reverse=True)
    n = len(episodes)
    for i, e in enumerate(episodes):
        e["num"] = f"{n - i:03d}"

    years = [e["year"] for e in episodes if e["year"]]
    founders = sum(1 for e in episodes if e["role"] != "Generative artist")
    platform_founders = len({re.sub(r"\(.*?\)", "", e["guest"]).strip().lower()
                             for e in episodes if e["is_founder"] and e["platform"] in BIG3})
    stats = {
        "episodes": feed_total, "interviews": n,
        "years": f"{min(years)}–{max(years) % 100:02d}" if years else "",
        "founders": founders,
        "platform_founders": f"{platform_founders:02d}",
        "seasons": f"{len(set(years)):02d}" if years else "",
    }
    ticker = [e["guest"] for e in episodes if e["guest"]]
    quotes = [{"text": e["quote"], "name": e["guest"], "title": e["display_title"],
               "platform": e["platform"]} for e in episodes if e["quote"]][:8]

    if SITE.exists():
        shutil.rmtree(SITE)
    SITE.mkdir()
    shutil.copy(ROOT / "templates" / "style.css", SITE / "style.css")
    shutil.copy(ROOT / "templates" / "suggest.js", SITE / "suggest.js")
    if IMAGES.exists():
        shutil.copytree(IMAGES, SITE / "images")
    (SITE / "episodes.json").write_text(
        json.dumps([e["slug"] for e in episodes]), encoding="utf-8")

    env.get_template("index.html").stream(
        root="", episodes=episodes, stats=stats, ticker=ticker, quotes=quotes,
        show=SHOW).dump(str(SITE / "index.html"))
    for ep in episodes:
        env.get_template("episode.html").stream(
            root="", ep=ep, show=SHOW, suggest_endpoint=SUGGEST_ENDPOINT).dump(
            str(SITE / f"{ep['slug']}.html"))

    print(f"Built {n} episode pages + ledger index into {SITE}/")


if __name__ == "__main__":
    main()
