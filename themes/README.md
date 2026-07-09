# WTBS site looks (themes)

Each folder here is a saved "look" — the layout templates + stylesheet that
define the site's design. The active look lives in `../templates/`; `build_site.py`
renders from there. Switching a look never touches the transcripts, audio, or
`suggest.js` (those are shared across all looks).

## Looks
- **provenance** — bold editorial / on-chain "ledger" design. Archivo + Space
  Mono, cream & teal with hot-pink and lime accents; every guest is "signed"
  into the ledger. (Current default.)

## Commands
```bash
python use_theme.py                 # list looks
python use_theme.py provenance      # activate a look → then: python build_site.py
python use_theme.py --save <name>   # snapshot current templates/ as a new look
```

## Trying a new look
1. Save the current one if it isn't already: `python use_theme.py --save provenance`
2. Edit `../templates/` freely (or start from a copy).
3. When happy: `python use_theme.py --save <new-name>`.
4. Revert anytime: `python use_theme.py provenance && python build_site.py`.
