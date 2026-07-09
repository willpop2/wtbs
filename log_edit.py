"""
Record an edit to an interview transcript in the public change log.

Appends a row to changelog.csv, which build_site.py renders as the "Change log"
on that episode's page. Run this whenever you apply a correction (e.g. an accepted
reader suggestion), then rebuild the site.

    python log_edit.py <slug> "What changed" [--credit "Name"] [--date YYYY-MM-DD]

Example:
    python log_edit.py Remnynt "Fixed spelling: 'Mathcastles'" --credit "A. Reader"
"""

import argparse
import csv
from datetime import date
from pathlib import Path

ROOT = Path(__file__).parent
CSV = ROOT / "changelog.csv"
FIELDS = ["slug", "date", "summary", "credit"]


def main() -> None:
    ap = argparse.ArgumentParser(description="Add a change-log entry for an episode.")
    ap.add_argument("slug", help="Episode slug (matches episodes.csv / the page filename).")
    ap.add_argument("summary", help="Short description of the edit.")
    ap.add_argument("--credit", default="", help="Who suggested it (optional).")
    ap.add_argument("--date", default=date.today().isoformat(), help="YYYY-MM-DD (default: today).")
    args = ap.parse_args()

    new_file = not CSV.exists()
    with CSV.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if new_file:
            w.writeheader()
        w.writerow({"slug": args.slug, "date": args.date,
                    "summary": args.summary, "credit": args.credit})
    print(f"Logged edit for '{args.slug}' ({args.date}). Rebuild with: python build_site.py")


if __name__ == "__main__":
    main()
