"""
Batch-process the WTBS interview backlog end to end.

For each episode in episodes.csv:
  1. download audio from the feed (skip if already present)
  2. transcribe with AssemblyAI (skip if raw transcript exists)
  3. auto-identify which Speaker A/B/C is Will / Trinity / the guest(s)
  4. readability cleanup with Claude (skip if clean transcript exists)

Fully resumable -- rerun any time; finished steps are skipped. Nothing here
sends anything outward except to AssemblyAI (transcription) and Anthropic
(cleanup); audio is pulled from your own podcast feed.

Usage:
    python batch.py                      # process every episode in the manifest
    python batch.py --only Zancan,McLlama
    python batch.py --limit 3            # first N episodes (handy for a test run)
    python batch.py --delete-audio       # remove the mp3 after a clean transcript
"""

import argparse
import csv
import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

import anthropic
from dotenv import load_dotenv

ROOT = Path(__file__).parent
AUDIO_DIR = ROOT / "audio"
RAW_DIR = ROOT / "transcripts" / "raw"
CLEAN_DIR = ROOT / "transcripts" / "clean"
PY = sys.executable  # the venv python running this script

HOSTS = "Will (handle Willpop) hosts; Trinity is the recurring co-host"


def download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=120) as r, tmp.open("wb") as f:
        while chunk := r.read(1 << 20):
            f.write(chunk)
    tmp.replace(dest)


def identify_speakers(client: anthropic.Anthropic, raw_txt: Path, guests: str) -> dict:
    """Map generic Speaker labels to real names using the transcript intro."""
    text = raw_txt.read_text(encoding="utf-8")
    excerpt = " ".join(text.split()[:1800])  # first ~1800 words is plenty
    system = (
        "You assign real names to speaker labels in a podcast transcript. The show "
        "'Waiting To Be Signed' is about generative/on-chain art. " + HOSTS + ". "
        f"This episode's guest(s): {guests}. Below is the start of a diarized transcript "
        "with generic labels. Using cues -- who welcomes/introduces the guest, who asks "
        "vs. answers, self-references -- map every generic label that appears to a name. "
        "Hosts map to exactly 'Will' or 'Trinity'. For the guest(s), use their full name or "
        "handle EXACTLY as written above -- never shorten to a first name only. "
        'Respond with ONLY a JSON object, e.g. {"Speaker A": "Will", "Speaker B": "Jimmy"}. '
        "If a label is genuinely unclear, map it to itself unchanged."
    )
    msg = client.messages.create(
        model="claude-sonnet-5",
        max_tokens=500,
        thinking={"type": "disabled"},
        system=system,
        messages=[{"role": "user", "content": excerpt}],
    )
    out = "".join(b.text for b in msg.content if b.type == "text").strip()
    out = out[out.find("{"): out.rfind("}") + 1]  # strip any stray prose
    return json.loads(out)


def run(cmd: list) -> None:
    result = subprocess.run(cmd)
    if result.returncode != 0:
        raise RuntimeError(f"command failed: {' '.join(str(c) for c in cmd)}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Batch-process the WTBS backlog.")
    ap.add_argument("--only", default=None, help="Comma-separated slugs to process.")
    ap.add_argument("--limit", type=int, default=None, help="Only the first N episodes.")
    ap.add_argument("--delete-audio", action="store_true",
                    help="Delete the mp3 once a clean transcript exists (saves disk).")
    ap.add_argument("--model", default="claude-sonnet-5", help="Cleanup model id.")
    args = ap.parse_args()

    load_dotenv(ROOT / ".env")
    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("ANTHROPIC_API_KEY missing — check .env")
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    rows = list(csv.DictReader((ROOT / "episodes.csv").open(encoding="utf-8")))
    if args.only:
        wanted = {s.strip() for s in args.only.split(",")}
        rows = [r for r in rows if r["slug"] in wanted]
    if args.limit:
        rows = rows[: args.limit]

    print(f"Processing {len(rows)} episode(s).\n")
    for i, r in enumerate(rows, 1):
        slug = r["slug"]
        audio = AUDIO_DIR / r["audio_file"]
        raw = RAW_DIR / f"{slug}.txt"
        clean = CLEAN_DIR / f"{slug}.txt"
        bio = ROOT / r["bio_file"]
        print(f"[{i}/{len(rows)}] {slug} — {r['title'][:60]}")

        if clean.exists():
            print("  clean transcript exists — skipping.\n")
            continue

        try:
            if not audio.exists() and r.get("audio_url"):
                print("  downloading audio ...")
                download(r["audio_url"], audio)
            if not raw.exists():
                print("  transcribing ...")
                run([PY, str(ROOT / "transcribe.py"), str(audio)])
            print("  identifying speakers ...")
            mapping = identify_speakers(client, raw, r["guests"])
            names = [f"{k.replace('Speaker ', '')}={v}" for k, v in mapping.items()
                     if not v.startswith("Speaker ")]
            print("    " + ", ".join(f"{k}->{v}" for k, v in mapping.items()))
            print("  cleaning up ...")
            cmd = [PY, str(ROOT / "cleanup.py"), str(raw), "--model", args.model]
            if bio.exists():
                cmd += ["--bio", str(bio)]
            if names:
                cmd += ["--names", *names]
            run(cmd)
            if args.delete_audio and clean.exists() and audio.exists():
                audio.unlink()
                print("  deleted audio to save disk.")
            print("  done.\n")
        except Exception as e:
            print(f"  ERROR on {slug}: {e}\n  (skipping; rerun later to retry)\n")

    print("Batch complete.")


if __name__ == "__main__":
    main()
