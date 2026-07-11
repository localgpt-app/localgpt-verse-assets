# reverie-assets

Bundled 3D/audio assets for **Reverie** (`localgpt/apps/reverie`), kept in a
separate repo per the monorepo `*-assets` convention.

- `models/` — CC0 glTF props, grouped one dir per asset (`<id>/<id>_1k.gltf` +
  `.bin` + `textures/`).
- `models/manifest.json` — the vetted manifest the app loads: per-asset name,
  file, placement tier (hero/medium/scatter), mood index, scale, and
  **provenance (author, license, source)** — which feeds Reverie's Credits
  screen and serves as the CC0/CC-BY audit trail.

**Distribution:** these are **bundled into the app at packaging time** (no
first-run download). For development, copy `models/` into
`localgpt/apps/reverie/assets/models/` (gitignored there) — see
`localgpt/apps/reverie/PLAN.md` §5.

## Licensing

Every asset here is **CC0** (Poly Haven). CC0 is copyright-waived: safe to
bundle and redistribute in an extractable `assets/` folder with no attribution
required — Reverie credits them anyway. Do **not** add marketplace
"royalty-free" assets (TurboSquid/CGTrader/Fab): their licenses forbid shipping
in an extractable open format. See `localgpt/apps/reverie/idea.md`.

## Current pack

7 CC0 nature props from Poly Haven (rocks, dead trees, plants, a shell) for the
Ember Flats and Tide Gardens moods. Velvet Circuit and Glass Expanse have no
realistic CC0 match and stay procedural until stylized packs (Kenney/Quaternius)
are added.
