# WTBS guest-artist themes (design mockups)

Exploratory "Look" themes: each is a FULL redesign around an interviewed artist —
own layout, type, palette, motion — same data + features underneath. NOT palette
swaps of Brutalist. Brutalist stays the default look. A visitor-facing "Look ▾"
switcher (persisted per browser) is planned but not built yet.

These are standalone HTML mockups (open directly / screenshot). The real build =
integrate each as a selectable look in templates/ + build_site.py.

- swahn-theme-mockup.html  — Erik Swahn: warm cream/sunset palette, solid color
  forms filled with tight dot/lune HALFTONE (read solid at distance, marks up
  close), chunky blocky display type, reseeding generative <canvas> hero.
  Status: approved starting point (revisit later).
- gysin-theme-mockup.html  — Andreas Gysin: dark animated ASCII/text-mode terminal,
  monospace everything, box-drawing rules, live reseeding character-field hero.
  Reseed varies palette (8, incl. Device 1) + charset (7) + motion pattern (6).
  Status: parked.
- zancan-theme-mockup.html  — Zancan: naturalist "field guide" — elegant serif +
  moss-green accents, fine technical grid, specimen-numbered index. Generative ink
  hero grows two plant types: thin curly leafy VINES + thick woody TREE BRANCHES
  (forking, budded twigs), with subtle pink/yellow leaves + blooms as highlights.
  regrow reseeds. (Tried stone columns/rocks — dropped, looked too primitive.)
  Status: parked.

- rudxane-theme-mockup.html  — Rudxane, themed on his work "Tych" (a polyptych):
  monochrome "contact sheet" — heavy condensed type on a newsprint ground, frame
  numbers, and a reseeding generative <canvas> grid of DISTRESSED textured panels
  (static, frayed bars, scratches, rain-streaks, brush blobs, halftone; frayed
  edges). Pure B&W, no color. Distinct from Brutalist by texture. "new print"
  reseeds. Status: parked (first crack).

All five original-list artists now have parked mockups (Swahn, Gysin, Zancan,
Rudxane) + Brutalist default. Remaining: build the visitor-facing Look switcher.
