#!/usr/bin/env python3
"""Normalize the Reverie model pack to single-file .glb (PLAN.md §1.3).

Runs gltf-transform over each model fetched by fetch_polyhaven.py and writes
models/<slug>/<slug>.glb (dedupe/prune + repack, `--compress false`: bevy_gltf
supports neither KHR_mesh_quantization nor EXT_meshopt_compression, so
geometry stays uncompressed — the win is one file per model, not bytes),
then points the manifest at the packed files.

    python3 normalize.py                # pack models that have no .glb yet
    python3 normalize.py --force        # re-pack every model
    python3 normalize.py --sync DEST    # copy manifest.json + the .glb files
                                        # it references into DEST (dev app
                                        # dir or dist/ bundle); never packs

The .glb files and the manifest are committed; the downloaded .gltf/.bin/
texture originals are gitignored. Packing therefore needs fetch_polyhaven.py
first (and Node.js), while --sync works on a fresh clone with neither.
"""

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

from fetch_polyhaven import MODELS, PACK

# Pinned: the committed .glb files are the only copy of the packed pack, and
# every one was built by this version. Pinning the CLI alone isn't enough — it
# takes the @gltf-transform/* libraries as ^ranges, so npx pulls the newest
# 4.x — but with all four pinned, re-packing sample models reproduced the
# committed files byte for byte. Bump deliberately, then --force.
GLTF_TRANSFORM = "4.4.1"
OPTIMIZE = [
    "npx",
    "--yes",
    *(
        f"--package=@gltf-transform/{pkg}@{GLTF_TRANSFORM}"
        for pkg in ("cli", "core", "extensions", "functions")
    ),
    "--",
    "gltf-transform",
    "optimize",
]
# NOTE: quantization (--compress quantize → KHR_mesh_quantization) and meshopt
# (EXT_meshopt_compression) are both UNSUPPORTED by bevy_gltf 0.19 — geometry
# compression is off the table until the loader grows the extension. We pack
# with `--compress false` (dedupe/prune + single-file .glb only).


def normalize(slug: str, force: bool) -> tuple[Optional[int], int]:
    """Pack one model to .glb. Returns (src_bytes, glb_bytes).

    An existing .glb is kept unless `force` — src_bytes is then None, since
    the originals it was packed from may not even be downloaded.
    """
    dest_dir = MODELS / slug
    glb = dest_dir / f"{slug}.glb"
    if glb.exists() and not force:
        return None, glb.stat().st_size
    gltfs = list(dest_dir.glob("*.gltf"))
    if not gltfs:
        raise FileNotFoundError(f"{slug}: no .gltf (run fetch_polyhaven.py)")
    subprocess.run(
        [*OPTIMIZE, str(gltfs[0]), str(glb), "--compress", "false"],
        check=True,
        capture_output=True,
    )
    return src_size(dest_dir), glb.stat().st_size


def src_size(dest_dir: Path) -> int:
    return sum(f.stat().st_size for f in dest_dir.rglob("*") if f.is_file() and f.suffix != ".glb")


def sync(manifest_path: Path, dest: Path) -> int:
    """Copy the manifest and the .glb files it references into dest.

    Checks everything first: a manifest still pointing at .gltf (fetched but
    not normalized) or at a missing file fails before dest is emptied.
    """
    manifest = json.loads(manifest_path.read_text())
    files = [entry["file"] for entry in manifest["assets"]]
    unpacked = [f for f in files if not f.endswith(".glb") or not (MODELS / f).is_file()]
    if unpacked:
        print(f"not synced: {len(unpacked)} entries have no packed .glb (run normalize.py)")
        print(f"  {unpacked}")
        return 1

    dest.mkdir(parents=True, exist_ok=True)
    shutil.rmtree(dest)
    dest.mkdir(parents=True)
    shutil.copy2(manifest_path, dest / "manifest.json")
    for rel in files:
        out = dest / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(MODELS / rel, out)
    size = sum(f.stat().st_size for f in dest.rglob("*") if f.is_file())
    print(f"synced manifest set -> {dest} ({size / 1e6:.0f} MB)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument(
        "--sync", metavar="DEST", help="copy manifest.json and its .glb files into DEST"
    )
    mode.add_argument("--force", action="store_true", help="re-pack models that have a .glb")
    args = ap.parse_args()

    manifest_path = MODELS / "manifest.json"
    if args.sync:
        return sync(manifest_path, Path(args.sync))

    manifest = json.loads(manifest_path.read_text())
    packed = 0
    failures = []
    for slug, *_rest in PACK:
        try:
            src_b, glb_b = normalize(slug, args.force)
        except Exception as e:  # noqa: BLE001
            print(f"FAIL {slug}: {e}")
            failures.append(slug)
            continue
        if src_b is not None:
            packed += 1
            print(f"  ok {slug}: {src_b / 1e6:.1f} -> {glb_b / 1e6:.1f} MB")
    if failures:
        print(f"\n{len(failures)} failures: {failures}")
        return 1

    for entry in manifest["assets"]:
        slug = entry["id"]
        entry["file"] = f"{slug}/{slug}.glb"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"\n{len(PACK)} models: {packed} packed, {len(PACK) - packed} already packed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
