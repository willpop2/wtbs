"""
Clean the NUMBERED (non-interview) WTBS episodes.

For each raw transcript in transcripts/raw_numbered/: identify which Speaker
A/B/C is Will / Trinity / (co-host) Ken / any guest named in the title, then run
the readability cleanup with the shared weekly-show context (bios/_numbered.txt).
Output goes to transcripts/clean_numbered/ — kept separate from the interview
site content, since publishing these is undecided. Fully resumable.

Usage:
    python batch_numbered.py
    python batch_numbered.py --limit 5      # first N (handy for a test run)
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

import anthropic
from dotenv import load_dotenv

import transcribe_numbered as tn  # reuse its feed parsing for episode titles

ROOT = Path(__file__).parent
RAW = ROOT / "transcripts" / "raw_numbered"
CLEAN = ROOT / "transcripts" / "clean_numbered"
BIO = ROOT / "bios" / "_numbered.txt"
PY = sys.executable
HOSTS = "Will (handle Willpop) and Trinity are the hosts; Ken is an occasional co-host"


def identify_speakers(client, raw_txt: Path, title: str) -> dict:
    text = raw_txt.read_text(encoding="utf-8")
    excerpt = " ".join(text.split()[:1800])
    system = (
        "You assign real names to speaker labels in a podcast transcript. The show "
        "'Waiting To Be Signed' is a weekly show about generative and on-chain art. " + HOSTS
        + f'. This episode is titled: "{title}". If the title names a guest, map them too. '
        "Below is the start of a diarized transcript with generic labels. Using cues -- who "
        "greets/introduces whom, who leads vs. responds, self-references -- map every generic "
        "label that appears to a name. Hosts map to 'Will', 'Trinity', or 'Ken'; a guest to the "
        "name given in the title. Respond with ONLY a JSON object, e.g. "
        '{"Speaker A": "Will", "Speaker B": "Trinity"}. If a label is genuinely unclear, map it '
        "to itself unchanged."
    )
    msg = client.messages.create(
        model="claude-sonnet-5", max_tokens=500, thinking={"type": "disabled"},
        system=system, messages=[{"role": "user", "content": excerpt}],
    )
    out = "".join(b.text for b in msg.content if b.type == "text").strip()
    out = out[out.find("{"): out.rfind("}") + 1]
    return json.loads(out)


def run(cmd: list) -> None:
    if subprocess.run(cmd).returncode != 0:
        raise RuntimeError("command failed: " + " ".join(str(c) for c in cmd))


def main() -> None:
    ap = argparse.ArgumentParser(description="Clean the numbered WTBS episodes.")
    ap.add_argument("--limit", type=int, default=None, help="Only the first N transcripts.")
    args = ap.parse_args()

    load_dotenv(ROOT / ".env")
    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("ANTHROPIC_API_KEY missing — check .env")
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    titles = {e["slug"]: e["title"] for e in tn.numbered_episodes()}
    CLEAN.mkdir(parents=True, exist_ok=True)
    files = sorted(RAW.glob("*.txt"))
    if args.limit:
        files = files[: args.limit]
    print(f"{len(files)} numbered transcripts. Cleaning to {CLEAN}/\n")

    for i, raw in enumerate(files, 1):
        slug = raw.stem
        out = CLEAN / f"{slug}.txt"
        print(f"[{i}/{len(files)}] {slug} — {titles.get(slug, '')[:50]}")
        if out.exists():
            print("  clean exists — skipping.\n")
            continue
        try:
            mapping = identify_speakers(client, raw, titles.get(slug, slug))
            names = [f"{k.replace('Speaker ', '')}={v}" for k, v in mapping.items()
                     if not v.startswith("Speaker ")]
            print("    " + ", ".join(f"{k}->{v}" for k, v in mapping.items()))
            cmd = [PY, str(ROOT / "cleanup.py"), str(raw), "--out-dir", str(CLEAN)]
            if BIO.exists():
                cmd += ["--bio", str(BIO)]
            if names:
                cmd += ["--names", *names]
            run(cmd)
            print("  done.\n")
        except Exception as e:
            print(f"  ERROR on {slug}: {e}\n  (skipping; rerun later to retry)\n")

    print("Numbered cleanup complete.")


if __name__ == "__main__":
    main()
