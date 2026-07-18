#!/usr/bin/env python3
"""Fetch the Reverie CC0 model pack from Poly Haven.

Downloads 1k glTF (+ .bin + jpg textures) for each asset in PACK into
models/<slug>/, then regenerates models/manifest.json (provenance + tier/mood
placement data — also the Credits screen's data source).

Idempotent: files that already exist with the expected size are skipped.
Usage: python3 fetch_polyhaven.py
"""

import concurrent.futures as cf
import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MODELS = ROOT / "models"
API = "https://api.polyhaven.com/files/{slug}"

# (slug, display name, tier, mood, scale)
# moods: 0 EMBER FLATS · 1 VELVET CIRCUIT · 2 TIDE GARDENS · 3 GLASS EXPANSE
# tiers: hero landmarks / medium props / scatter ground cover.
PACK = [
    # --- EMBER FLATS (desert rock & dry wood) ---
    ("boulder_01", "Boulder", "hero", 0, 1.4),
    ("dead_tree_trunk", "Dead Tree Trunk", "hero", 0, 1.0),
    ("namaqualand_boulder_02", "Namaqualand Boulder", "hero", 0, 1.2),
    ("namaqualand_cliff_01", "Namaqualand Cliff", "hero", 0, 1.0),
    ("quiver_tree_01", "Quiver Tree", "hero", 0, 1.0),
    ("dead_quiver_trunk", "Quiver Tree Trunk", "medium", 0, 1.0),
    ("tree_stump_02", "Tree Stump", "medium", 0, 1.1),
    ("searsia_burchellii", "Searsia Bush", "medium", 0, 1.0),
    ("wild_rooibos_bush", "Wild Rooibos Bush", "medium", 0, 1.0),
    ("dry_branches_medium_01", "Dry Branches", "scatter", 0, 1.0),
    ("dead_quiver_branch_01", "Quiver Branch", "scatter", 0, 1.0),
    ("cheiridopsis_succulent", "Cheiridopsis Succulent", "scatter", 0, 1.2),
    ("flower_ursinia", "Ursinia Flower", "scatter", 0, 1.2),
    # --- VELVET CIRCUIT (abstract neon & chrome) ---
    ("vintage_spacecraft_instrument", "Spacecraft Instrument", "hero", 1, 1.0),
    ("modular_industrial_pipes_01", "Industrial Pipes", "hero", 1, 1.0),
    ("modular_airduct_circular_01", "Airduct", "medium", 1, 1.0),
    ("utility_box_01", "Utility Box", "medium", 1, 1.0),
    ("power_box_01", "Power Box", "medium", 1, 1.0),
    ("metal_tool_chest", "Tool Chest", "medium", 1, 1.0),
    ("barrel_03", "Barrel", "medium", 1, 1.0),
    ("boombox", "Boombox", "medium", 1, 1.0),
    ("industrial_pipe_lamp", "Pipe Lamp", "medium", 1, 0.8),
    ("circuit_board", "Circuit Board", "scatter", 1, 1.5),
    ("metal_trash_can", "Trash Can", "scatter", 1, 1.0),
    ("security_camera_01", "Security Camera", "scatter", 1, 1.2),
    ("modular_electric_cables", "Electric Cables", "scatter", 1, 1.0),
    ("metal_jerrycan", "Jerrycan", "scatter", 1, 1.0),
    # --- TIDE GARDENS (coral & kelp) ---
    ("coast_rocks_05", "Reef Rocks", "hero", 2, 1.2),
    ("coastal_cliff_01", "Coastal Cliff", "hero", 2, 1.0),
    ("bronze_whale_statue", "Whale Statue", "hero", 2, 1.0),
    ("anthurium_botany_01", "Anthurium", "medium", 2, 1.3),
    ("calathea_orbifolia_01", "Calathea", "medium", 2, 1.3),
    ("coast_land_rocks_02", "Coast Rocks", "medium", 2, 1.0),
    ("ocean_buoy", "Ocean Buoy", "medium", 2, 1.0),
    ("fern_02", "Fern", "medium", 2, 1.2),
    ("lambis_shell", "Lambis Shell", "scatter", 2, 2.5),
    ("sand_rocks_small_01", "Sand Rocks", "scatter", 2, 1.2),
    ("moss_01", "Moss", "scatter", 2, 1.5),
    ("shrub_01", "Shrub", "scatter", 2, 1.2),
    ("periwinkle_plant", "Periwinkle", "scatter", 2, 1.2),
    # --- GLASS EXPANSE (ice & crystal) ---
    ("moon_rock_01", "Moon Rock", "hero", 3, 1.2),
    ("moon_rock_05", "Moon Rock Formation", "hero", 3, 1.2),
    ("marble_bust_01", "Marble Bust", "hero", 3, 1.0),
    ("horse_statue_01", "Porcelain Horse", "medium", 3, 1.0),
    ("moon_rock_02", "Moon Boulder", "medium", 3, 1.0),
    ("namaqualand_rocks_01", "Quartz Rocks", "medium", 3, 1.0),
    ("ceramic_vase_01", "Ceramic Vase", "medium", 3, 0.9),
    ("namaqualand_stones_01", "Quartz Stones", "scatter", 3, 1.2),
    ("crystalline_iceplant", "Crystalline Iceplant", "scatter", 3, 1.3),
    ("stone_01", "Quartz Gravel", "scatter", 3, 1.2),
    ("flower_heliophila", "Heliophila Flower", "scatter", 3, 1.3),
    ("jug_01", "White Jug", "scatter", 3, 0.9),
]


def get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "reverie-assets-fetch/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def fetch_asset(slug: str) -> tuple[str, int, int]:
    """Download one model's gltf-1k + includes. Returns (slug, files, bytes)."""
    meta = json.loads(get(API.format(slug=slug)))
    # Structure: gltf -> <res> -> "gltf" -> {url, size, include{...}}.
    # Fall back to 2k when a model has no 1k resolution.
    by_res = meta["gltf"]
    res = "1k" if "1k" in by_res else "2k"
    entry = by_res[res]["gltf"]
    dest_dir = MODELS / slug
    dest_dir.mkdir(parents=True, exist_ok=True)

    # Name the local gltf after the remote filename (matches the res fallback).
    gltf_name = entry["url"].rsplit("/", 1)[-1]
    files = {dest_dir / gltf_name: entry}
    for rel, info in entry.get("include", {}).items():
        files[dest_dir / rel] = info

    n, total = 0, 0
    for dest, info in files.items():
        size = info["size"]
        if dest.exists() and dest.stat().st_size == size:
            n += 1
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(get(info["url"]))
        if dest.stat().st_size != size:
            raise RuntimeError(f"size mismatch on {dest}")
        n += 1
        total += size
    return slug, n, total, gltf_name


def main() -> int:
    slugs = [p[0] for p in PACK]
    assert len(slugs) == len(set(slugs)), "duplicate slugs in PACK"

    failures = []
    gltf_names = {}
    with cf.ThreadPoolExecutor(max_workers=4) as ex:
        futs = {ex.submit(fetch_asset, s): s for s in slugs}
        for fut in cf.as_completed(futs):
            slug = futs[fut]
            try:
                _, n, size, gltf_name = fut.result()
                gltf_names[slug] = gltf_name
                print(f"  ok {slug} ({n} files, {size / 1e6:.1f} MB new)")
            except Exception as e:  # noqa: BLE001 — report and continue
                print(f"FAIL {slug}: {e}")
                failures.append(slug)
    if failures:
        print(f"\n{len(failures)} failures: {failures}")
        return 1

    manifest = {
        "version": 1,
        "assets": [
            {
                "id": slug,
                "name": name,
                "file": f"{slug}/{gltf_names[slug]}",
                "tier": tier,
                "mood": mood,
                "scale": scale,
                "license": "CC0",
                "author": "Poly Haven",
                "source": f"https://polyhaven.com/a/{slug}",
            }
            for slug, name, tier, mood, scale in PACK
        ],
    }
    # Native dimensions (mm -> m) let the app rescale each model to its
    # tier's target span — raw Poly Haven scans range from 0.1 m (shell)
    # to 90 m (cliff).
    catalog = json.loads(get("https://api.polyhaven.com/assets?t=models"))
    for entry in manifest["assets"]:
        dims = catalog.get(entry["id"], {}).get("dimensions")
        if dims:
            entry["dims"] = [round(d / 1000.0, 3) for d in dims]
    out = MODELS / "manifest.json"
    out.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"\n{len(PACK)} assets -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
