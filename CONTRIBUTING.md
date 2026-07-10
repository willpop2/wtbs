# Contributing to WTBS

Two of us (plus our respective Claude Codes) work on this repo, so a few habits
keep us from stepping on each other.

## The golden rules

1. **Pull before you start, pull before you push.**
   ```
   git pull --rebase origin main
   ```
   Your local clone (and your Claude) only know what you last pulled. If the
   other person pushed since then, you're working against a stale copy. Pulling
   first is the single most important habit. If you use Claude Code, tell it to
   `git pull` at the start of a session.

2. **Use a branch + PR for anything non-trivial.**
   ```
   git checkout -b my-feature
   # ...work, commit...
   git push -u origin my-feature      # then open a Pull Request on GitHub
   ```
   Small typo fixes can go straight to `main`; features and refactors should go
   through a PR so the other person can glance at it and merges stay clean.

3. **Never force-push `main`** (`git push --force`). It's the one operation that
   can actually erase someone's work. Force-pushing *your own* feature branch is
   fine.

## Don't commit the built site

`site/` is **generated** and **gitignored**. GitHub Actions builds it from
source on every push to `main` and deploys to
https://willpop2.github.io/wtbs/. Never add `site/` back to git — that's what
used to cause constant conflicts.

To preview locally:
```
python build_site.py
python -m http.server 8000 --directory site
# open http://localhost:8000/
```

## Setup

```
git clone https://github.com/willpop2/wtbs.git
cd wtbs
python -m venv .venv
.venv/Scripts/activate            # Windows;  source .venv/bin/activate on mac/linux
pip install jinja2
python build_site.py
```

That's all you need for **website** work.

## Secrets & the pipeline

- `.env` is gitignored and holds API keys (AssemblyAI, Anthropic). It is **not**
  in the repo. Website work needs none of it.
- If you touch the transcription pipeline (`transcribe.py`, `cleanup.py`,
  `batch*.py`), create your own `.env` with your own keys.
- The feedback Worker (`worker/`) and its secrets live in a Cloudflare account,
  separate from this repo.

## What's tracked vs. not

- **Tracked:** source (`build_site.py`, `templates/`, `themes/`), content
  (`episodes.csv`, `transcripts/final/`, `transcripts/raw/*.txt`, `images/`,
  `bios/`, `changelog.csv`, `scratch_feed.xml`), the pipeline scripts, `worker/`.
- **Not tracked:** `site/` (built in CI), `.env`, `.venv/`, audio, raw JSON
  transcripts, and the numbered-episode sets.

## Applying reader edit-suggestions

Edit the relevant `transcripts/final/<slug>.txt`, then log it:
```
python log_edit.py <slug> "what changed" --credit "Name"
```
For hyperlink suggestions, link **every** occurrence of the term (not just the
first) unless told otherwise.
