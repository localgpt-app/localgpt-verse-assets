#!/usr/bin/env python3
"""Normalize the Reverie model pack to single-file .glb (PLAN.md §1.3).

Runs gltf-transform over each model fetched by fetch_polyhaven.py and writes
models/<slug>/<slug>.glb (dedupe/prune + repack, `--compress false`: bevy_gltf
supports neither KHR_mesh_quantization nor EXT_meshopt_compression, so
geometry stays uncompressed — the win is one file per model, not bytes),
then points the manifest at the packed files.

    python3 normalize.py                # pack + update manifest
    python3 normalize.py --sync DEST    # then copy manifest-referenced files
                                        # (and manifest.json) into DEST
                                        # (dev app dir or dist/ bundle)

Idempotent: .glb newer than the source .gltf is skipped. The original
.gltf/.bin/texture files stay in the repo as the auditable source of truth;
--sync ships only what the manifest references.
"""

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

from fetch_polyhaven import MODELS, PACK

OPTIMIZE = ["npx", "--yes", "@gltf-transform/cli", "optimize"]
# NOTE: quantization (--compress quantize → KHR_mesh_quantization) and meshopt
# (EXT_meshopt_compression) are both UNSUPPORTED by bevy_gltf 0.19 — geometry
# compression is off the table until the loader grows the extension. We pack
# with `--compress false` (dedupe/prune + single-file .glb only).


def normalize(slug: str) -> tuple[str, int, int]:
    """Pack one model to .glb. Returns (slug, src_bytes, glb_bytes)."""
    dest_dir = MODELS / slug
    gltfs = list(dest_dir.glob("*.gltf"))
    if not gltfs:
        raise FileNotFoundError(f"{slug}: no .gltf (run fetch_polyhaven.py)")
    src = gltfs[0]
    glb = dest_dir / f"{slug}.glb"
    if glb.exists() and glb.stat().st_mtime >= src.stat().st_mtime:
        return slug, src_size(dest_dir), glb.stat().st_size
    subprocess.run(
        [*OPTIMIZE, str(src), str(glb), "--compress", "false"],
        check=True,
        capture_output=True,
    )
    return slug, src_size(dest_dir), glb.stat().st_size


def src_size(dest_dir: Path) -> int:
    return sum(f.stat().st_size for f in dest_dir.rglob("*") if f.is_file())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sync", metavar="DEST", help="copy manifest-referenced files into DEST")
    args = ap.parse_args()

    manifest_path = MODELS / "manifest.json"
    manifest = json.loads(manifest_path.read_text())

    total_src = total_glb = 0
    failures = []
    for slug, _name, _tier, _mood, _scale in PACK:
        try:
            _, src_b, glb_b = normalize(slug)
            total_src += src_b
            total_glb += glb_b
            print(f"  ok {slug}: {src_b / 1e6:.1f} -> {glb_b / 1e6:.1f} MB")
        except Exception as e:  # noqa: BLE001
            print(f"FAIL {slug}: {e}")
            failures.append(slug)
    if failures:
        print(f"\n{len(failures)} failures: {failures}")
        return 1

    for entry in manifest["assets"]:
        slug = entry["id"]
        entry["file"] = f"{slug}/{slug}.glb"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"\n{len(PACK)} models, {total_src / 1e6:.0f} MB -> {total_glb / 1e6:.0f} MB")

    if args.sync:
        dest = Path(args.sync)
        dest.mkdir(parents=True, exist_ok=True)
        shutil.rmtree(dest)
        dest.mkdir(parents=True)
        shutil.copy2(manifest_path, dest / "manifest.json")
        for entry in manifest["assets"]:
            rel = entry["file"]
            out = dest / rel
            out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(MODELS / rel, out)
        size = sum(f.stat().st_size for f in dest.rglob("*") if f.is_file())
        print(f"synced manifest set -> {dest} ({size / 1e6:.0f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
