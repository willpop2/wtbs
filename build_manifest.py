"""
Build an episode manifest for the WTBS backlog from the podcast RSS feed.

Fetches the feed, keeps the interview episodes, and for each one derives a
guest slug, the audio download URL, and an auto-drafted bio (from the episode
description). You review/tweak episodes.csv once before the batch run.

Usage:
    python build_manifest.py
    python build_manifest.py --feed <rss-url>   # override default feed

Outputs:
    episodes.csv         one row per interview episode (edit as needed)
    bios/<slug>.txt      auto-drafted bio per episode (from the show notes)
"""

import argparse
import csv
import html
import re
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).parent
BIOS_DIR = ROOT / "bios"
DEFAULT_FEED = "https://anchor.fm/s/7c35eb94/podcast/rss"


def strip_html(s: str) -> str:
    s = re.sub(r"<[^>]+>", " ", s or "")
    return re.sub(r"\s+", " ", html.unescape(s)).strip()


def guest_slug(guests_raw: str) -> str:
    """Derive a filename-safe slug from the 'Interview with ...' portion."""
    s = re.sub(r"\(.*?\)", "", guests_raw)          # drop "(real name)"
    s = re.sub(r"^\s*artist\s+", "", s, flags=re.I)  # drop leading "artist"
    s = re.sub(r"\s+of\s+.*$", "", s, flags=re.I)    # drop "of <Gallery>"
    parts = re.split(r"\s*(?:&|,|\band\b)\s*", s)     # split multiple guests
    parts = [re.sub(r"[^A-Za-z0-9]", "", p) for p in parts if p.strip()]
    roles = {"founder", "cofounder", "ceo", "head", "phd", "dr", "director",
             "curator", "president", "cohost", "host", "owner", "the"}
    parts = [p for p in parts if p.lower() not in roles]  # drop job titles
    slug = "_".join(parts[:2]) or "unknown"
    return slug


def main() -> None:
    ap = argparse.ArgumentParser(description="Build the WTBS episode manifest from RSS.")
    ap.add_argument("--feed", default=DEFAULT_FEED, help="RSS feed URL.")
    args = ap.parse_args()

    print(f"Fetching feed: {args.feed}")
    req = urllib.request.Request(args.feed, headers={"User-Agent": "Mozilla/5.0"})
    data = urllib.request.urlopen(req, timeout=60).read()
    root = ET.fromstring(data)

    BIOS_DIR.mkdir(exist_ok=True)
    rows = []
    seen = {}
    for item in root.findall(".//item"):
        title = (item.findtext("title") or "").strip()
        # Match "Interview with X" and "Interview w/ X" (guest after), plus the
        # guest-led "X ... Interview" form (e.g. "Ciphrd End of Beta Interview").
        m = re.search(r"interview\s+(?:with|w/)\s+([^,]+)", title, re.I)
        if m:
            guests_raw = m.group(1).strip()
        elif re.search(r"\binterview\b", title, re.I):
            guests_raw = re.match(r"^([A-Za-z0-9']+)", title).group(1)
        else:
            continue  # not an interview episode
        slug = guest_slug(guests_raw)
        # De-duplicate slugs case-insensitively (Windows filesystem is
        # case-insensitive, so "Ciphrd" and "ciphrd" would collide to one file).
        key = slug.lower()
        seen[key] = seen.get(key, 0) + 1
        if seen[key] > 1:
            slug = f"{slug}_{seen[key]}"

        enc = item.find("enclosure")
        audio_url = enc.get("url") if enc is not None else ""
        desc = strip_html(item.findtext("description"))

        bio_path = BIOS_DIR / f"{slug}.txt"
        if not bio_path.exists():  # never overwrite a hand-edited bio
            bio_path.write_text(
                f"Episode: {title}\nGuest(s): {guests_raw}\n\n{desc}\n", encoding="utf-8"
            )

        rows.append({
            "slug": slug,
            "audio_file": f"{slug}.mp3",
            "guests": guests_raw,
            "title": title,
            "audio_url": audio_url,
            "bio_file": f"bios/{slug}.txt",
        })

    out = ROOT / "episodes.csv"
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["slug", "audio_file", "guests", "title",
                                          "audio_url", "bio_file"])
        w.writeheader()
        w.writerows(rows)

    print(f"\nWrote {len(rows)} interview episodes to {out}")
    print(f"Auto-drafted {len(rows)} bios in {BIOS_DIR}/")
    print("Review episodes.csv (fix guest slugs for multi-guest / gallery episodes) "
          "before running the batch.")


if __name__ == "__main__":
    main()
