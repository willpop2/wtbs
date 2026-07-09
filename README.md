# WTBS Transcription Pipeline

Accurate transcripts of WTBS podcast interviews (generative / on-chain / NFT
artists), tuned for the proper nouns and handles that trip up generic ASR.

Two steps:
1. **`transcribe.py`** — AssemblyAI `slam-1` model with your glossary as keyterms
   + speaker diarization → raw speaker-labeled transcript.
2. **`cleanup.py`** — Claude fixes names/terms against the glossary AND edits for
   readability (removes filler/false starts, fixes grammar, light rewrite for flow,
   preserving each speaker's meaning and voice) → publication-ready transcript.
   Maps `Speaker A/B` to real names via `--names`.

## One-time setup (already done)
- Python virtual environment in `.venv/` with `assemblyai`, `anthropic`,
  `openpyxl`, `python-dotenv`.
- API keys in `.env` (gitignored — never commit this file).
- `glossary.xlsx` — one term per row in column A.

## Run it

From this folder (`C:\Users\wilso\Downloads\WTBS`):

```bash
# 1. Transcribe (put your audio in audio/ first)
.venv/Scripts/python.exe transcribe.py audio/my-episode.mp3 --speakers 2

# 2. Clean up: readability edit + speaker names (bio improves name accuracy)
.venv/Scripts/python.exe cleanup.py transcripts/raw/my-episode.txt \
    --bio bios/my-episode.txt --names A=Will B=Jimmy
```

Results:
- `transcripts/raw/<name>.txt`   — straight from AssemblyAI
- `transcripts/clean/<name>.txt` — after Claude correction

## Options
- `transcribe.py --speakers N` — tell diarization how many voices to expect.
- `cleanup.py --bio bio.txt`   — pass a file instead of inline text.
- `cleanup.py --names A=Will B=Jimmy` — rename speaker labels.
- `cleanup.py --model claude-opus-4-8` — use Opus for the highest-quality
  editing (default is `claude-sonnet-5`, cheaper and already strong).

## Scaling to the backlog
Once a test episode looks good, the same two scripts run over every file in
`audio/` — we'll add a batch wrapper that loops the folder.

## Security
`.env` holds live API keys. It is gitignored. Rotate both keys in the
AssemblyAI and Anthropic dashboards once the backlog is processed.
