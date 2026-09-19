# reverie-assets

The 3D models and starter music bundled with
[Reverie](https://github.com/localgpt-app/reverie), a desktop app that builds a
3D world for every song. Everything here is public domain under
[CC0 1.0](LICENSE).

The assets are kept apart from Reverie's code because they're large and change
on their own schedule. Reverie bundles them into its download when it's
packaged, so the app never downloads them at runtime.

## Contents

| Path | What it is |
|------|------------|
| `models/<id>/` | One model from [Poly Haven](https://polyhaven.com): the original `<id>_1k.gltf` with its `.bin` and `textures/`, plus `<id>.glb`, the single-file version Reverie loads |
| `models/manifest.json` | The list of models Reverie reads: placement data and provenance |
| `music/` | Four original tracks, `music.json` (the track list Reverie reads) and `NOTICE` |
| `fetch_polyhaven.py` | Downloads the models from Poly Haven and rewrites the manifest |
| `normalize.py` | Packs each model into its `.glb`, and copies the shipped set into a Reverie checkout |
| `generate_music.py` | Synthesizes the four tracks |

### Models

52 models, 12–14 for each of Reverie's four base worlds, in three placement
tiers: hero landmarks, medium props and ground scatter. Reverie's other four
worlds reuse these for now.

| World | Models | Examples |
|-------|-------:|----------|
| Ember Flats | 13 | boulders, a cliff, quiver trees, dry branches, a succulent |
| Velvet Circuit | 14 | industrial pipes, an air duct, utility boxes, a boombox, a circuit board |
| Tide Gardens | 13 | a coastal cliff, rocks, a bronze whale statue, a buoy, tropical plants |
| Glass Expanse | 12 | moon rocks, quartz stones, a marble bust, porcelain and ceramics |

Each entry in `models/manifest.json` has:

- `id` and `name`: the Poly Haven asset id and a display name
- `file`: the path to the `.glb`, relative to `models/`
- `tier`: `hero`, `medium` or `scatter`
- `mood`: the world, as a position in Reverie's list (0 Ember Flats, 1 Velvet
  Circuit, 2 Tide Gardens, 3 Glass Expanse). If Reverie's first four worlds
  change order, update `PACK` in `fetch_polyhaven.py` and regenerate.
- `scale` and `dims`: a per-model adjustment and the native size in metres.
  Reverie rescales each model to its tier's size.
- `license`, `author` and `source`: provenance. Reverie's Credits screen shows
  each model's author and license.

Only the manifest and the `.glb` files ship, about 165 MB. The originals stay
here as the auditable source.

### Music

| Track | Tempo |
|-------|------:|
| Amber Drift | 68 BPM |
| Tidewater | 60 BPM |
| Nightglass | 92 BPM |
| Emberfall | 112 BPM |

Original compositions synthesized from scratch by `generate_music.py` (pads,
sine bass, plucked bells, soft percussion and reverb), with no samples or
recordings. They give Reverie something to play before you import your own
music.

## Using with Reverie

Keep this repository beside your Reverie checkout:

```
reverie/           the app
reverie-assets/    this repository
```

- **Packaging.** Reverie's `scripts/bundle.sh` reads this repository from
  `../reverie-assets` (set `REVERIE_ASSETS` to use another path) and copies
  the manifest, the `.glb` files and the music into the bundle.
- **Development.** Reverie loads assets from its own `assets/` folder, where
  the models and music are gitignored. To fill it, run this from this
  repository:

  ```sh
  python3 normalize.py --sync ../reverie/assets/models
  mkdir -p ../reverie/assets/music
  cp music/*.mp3 music/music.json music/NOTICE ../reverie/assets/music/
  ```

  `--sync` only copies files, so it needs neither Node.js nor the original
  downloads. It empties its destination first, so point it at the `models`
  folder itself.

## Regenerating

You need Python 3, Node.js for `normalize.py` (it packs models with
[glTF-Transform](https://gltf-transform.dev) through `npx`), and
[LAME](https://lame.sourceforge.io) for `generate_music.py`.

```sh
python3 fetch_polyhaven.py   # download the models and rewrite the manifest
python3 normalize.py         # pack new models, point the manifest at the .glb files
python3 generate_music.py    # re-render the tracks and music.json
```

Run `normalize.py` after every fetch: the fetch writes `.gltf` paths into the
manifest, and normalizing points them back at the `.glb` files.

`normalize.py` packs only the models that don't have a `.glb` yet; `--force`
re-packs all of them. glTF-Transform is pinned to the version that built the
committed files, so re-packing doesn't drift with new releases.

To add a model, pick a CC0 model on Poly Haven, add a
`(slug, name, tier, mood, scale)` row to `PACK` in `fetch_polyhaven.py`, run
both scripts, and commit the originals, the `.glb` and the manifest together.

## License

Everything in this repository is dedicated to the public domain under
[CC0 1.0 Universal](LICENSE).

- **Models** are by the artists of [Poly Haven](https://polyhaven.com), which
  publishes all its assets under CC0. Credit isn't required, but Poly Haven
  appreciates it, and Reverie's Credits screen lists every model.
- **Music and scripts:** to the extent possible under law, the author(s) have
  dedicated all copyright and related and neighboring rights to them to the
  public domain worldwide. They are distributed without any warranty.

Only add CC0 material. This repository has a single license, and Reverie ships
these files in an open `assets/` folder beside its binary. Marketplace
"royalty-free" models (TurboSquid, CGTrader, Fab) are ruled out for a second
reason: their licenses forbid shipping in an extractable format.
