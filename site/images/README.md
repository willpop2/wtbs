# Interview images

Drop images that illustrate an interview here, one folder per episode:

```
images/<slug>/your-image.jpg      e.g. images/Remnynt/architectonica.jpg
```

`<slug>` is the episode's filename stem (same as `transcripts/final/<slug>.txt`
and the page `<slug>.html`). The build copies this whole folder into the site.

## Placing an image in a transcript

Edit `transcripts/final/<slug>.txt` and put a marker on its own line (a blank
line above and below) between two speaker turns, where you want the image to
appear:

```
[img: architectonica.jpg | Architectonica — Remnynt, 2025 | https://www.artblocks.io/...]
```

Format: `filename | caption | credit-URL` — caption and credit are optional.

- **filename** — just the file name; it resolves to `images/<slug>/<filename>`.
  (A full `https://…` URL also works if you'd rather hotlink, but self-hosting
  is safer.)
- **caption** — shown under the image.
- **credit-URL** — renders a "source" link under the caption (use the artist's
  page or the work's page — please credit the artist).

Then rebuild: `python build_site.py`.

## Tips
- Keep images reasonably sized (long edge ~1600px, compressed) — they ship with
  the site.
- One or two per interview is plenty to break up the text.
- `images/_sample/placeholder.svg` is a demo asset you can delete.
