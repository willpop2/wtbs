"""
Switch the active WTBS site "look".

Each look is a set of layout templates + stylesheet saved under themes/<name>/.
Activating one copies those files into templates/, which build_site.py uses.

    python use_theme.py                 # list available looks
    python use_theme.py provenance      # activate a look
    python use_theme.py --save <name>   # snapshot current templates/ as a new look

After activating, rebuild:  python build_site.py
"""

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).parent
THEMES = ROOT / "themes"
TPL = ROOT / "templates"
FILES = ["base.html", "index.html", "episode.html", "style.css"]  # the "look" files


def names() -> list:
    return sorted(p.name for p in THEMES.iterdir() if p.is_dir()) if THEMES.exists() else []


def main() -> None:
    args = sys.argv[1:]
    if not args:
        print("Available looks:", ", ".join(names()) or "(none)")
        print("Activate:  python use_theme.py <name>   then  python build_site.py")
        print("Save current templates/ as a look:  python use_theme.py --save <name>")
        return

    if args[0] == "--save":
        if len(args) < 2:
            sys.exit("Usage: python use_theme.py --save <name>")
        dest = THEMES / args[1]
        dest.mkdir(parents=True, exist_ok=True)
        for f in FILES:
            if (TPL / f).exists():
                shutil.copy(TPL / f, dest / f)
        print(f"Saved current look as '{args[1]}' in {dest}/")
        return

    name = args[0]
    src = THEMES / name
    if not src.exists():
        sys.exit(f"No look named '{name}'. Available: {', '.join(names()) or '(none)'}")
    for f in FILES:
        if (src / f).exists():
            shutil.copy(src / f, TPL / f)
    print(f"Activated look '{name}'. Now run:  python build_site.py")


if __name__ == "__main__":
    main()
