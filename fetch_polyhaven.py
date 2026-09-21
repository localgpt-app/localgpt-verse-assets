#!/usr/bin/env python3
"""Fetch the Reverie CC0 model pack from Poly Haven.

Downloads 1k glTF (+ .bin + jpg textures) for each asset in PACK into
models/<slug>/, then regenerates models/manifest.json (provenance + kind/tier/
mood placement data — also the Credits screen's data source).

Manifest v2 adds `kind` (the semantic vocabulary the agent's place_asset enum
exposes — variants behind a kind rotate) and `mood_id` (the stable mood id the
app prefers over the positional `mood`).

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
CATALOG = "https://api.polyhaven.com/assets?t=models"

# Stable mood ids (must match theme::WorldMood::id in the app).
MOOD_IDS = [
    "ember-flats",  # 0
    "velvet-circuit",  # 1
    "tide-gardens",  # 2
    "glass-expanse",  # 3
    "cinder-reach",  # 4 (extended: borrows ember + own accents)
    "mirage-circuit",  # 5 (extended: velvet + own accents)
    "abyss-terraces",  # 6 (extended: tide + own accents)
    "dawn-expanse",  # 7 (extended: glass + own accents)
]

# (slug, display name, kind, tier, mood, scale)
# kinds: the stable semantic vocabulary (place_asset's enum) — rock, dead_tree,
#   tree, plant, flower, shell, statue, vase, decor, ruin, machine, container,
#   tool, furniture, electronics, instrument, lamp, nautical, creature.
# tiers: hero landmarks / medium props / scatter ground cover.
# moods: indices into MOOD_IDS above.
PACK = [
    # --- EMBER FLATS (desert rock & dry wood) ---
    ("boulder_01", "Boulder", "rock", "hero", 0, 1.4),
    ("dead_tree_trunk", "Dead Tree Trunk", "dead_tree", "hero", 0, 1.0),
    ("namaqualand_boulder_02", "Namaqualand Boulder", "rock", "hero", 0, 1.2),
    ("namaqualand_cliff_01", "Namaqualand Cliff", "rock", "hero", 0, 1.0),
    ("quiver_tree_01", "Quiver Tree", "tree", "hero", 0, 1.0),
    ("dead_quiver_trunk", "Quiver Tree Trunk", "dead_tree", "medium", 0, 1.0),
    ("tree_stump_02", "Tree Stump", "dead_tree", "medium", 0, 1.1),
    ("searsia_burchellii", "Searsia Bush", "plant", "medium", 0, 1.0),
    ("wild_rooibos_bush", "Wild Rooibos Bush", "plant", "medium", 0, 1.0),
    ("dry_branches_medium_01", "Dry Branches", "dead_tree", "scatter", 0, 1.0),
    ("dead_quiver_branch_01", "Quiver Branch", "dead_tree", "scatter", 0, 1.0),
    ("cheiridopsis_succulent", "Cheiridopsis Succulent", "plant", "scatter", 0, 1.2),
    ("flower_ursinia", "Ursinia Flower", "flower", "scatter", 0, 1.2),
    ("namaqualand_boulder_03", "Namaqualand Boulder 03", "rock", "hero", 0, 1.2),
    ("namaqualand_boulder_04", "Namaqualand Boulder 04", "rock", "hero", 0, 1.2),
    ("namaqualand_cliff_02", "Namaqualand Cliff 02", "rock", "hero", 0, 1.0),
    ("dead_tree_trunk_02", "Dead Tree Trunk 02", "dead_tree", "hero", 0, 1.0),
    ("othonna_cerarioides", "Othonna Tree", "tree", "hero", 0, 1.0),
    ("rock_face_01", "Rock Face", "rock", "hero", 0, 1.0),
    ("mountainside", "Mountainside", "rock", "hero", 0, 0.9),
    ("rock_face_02", "Rock Face 02", "rock", "medium", 0, 1.0),
    ("namaqualand_boulders_01", "Namaqualand Boulders", "rock", "medium", 0, 1.0),
    ("namaqualand_boulder_06", "Namaqualand Boulder 06", "rock", "medium", 0, 1.0),
    ("root_cluster_01", "Root Cluster", "dead_tree", "medium", 0, 1.0),
    ("pine_roots", "Pine Roots", "dead_tree", "medium", 0, 1.0),
    ("didelta_spinosa", "Didelta Bush", "plant", "medium", 0, 1.0),
    ("leipoldtia_schultzei", "Leipoldtia Bush", "plant", "medium", 0, 1.0),
    ("single_root", "Single Root", "dead_tree", "scatter", 0, 1.0),
    ("nettle_plant", "Nettle Plant", "plant", "scatter", 0, 1.0),
    ("weed_plant_02", "Weed Plant", "plant", "scatter", 0, 1.0),
    ("flower_gazania", "Gazania Flower", "flower", "scatter", 0, 1.2),
    ("flower_empodium", "Empodium Flower", "flower", "scatter", 0, 1.2),
    ("flower_stinkkruid", "Stinkkruid Flower", "flower", "scatter", 0, 1.1),
    ("shrub_sorrel_01", "Sorrel Flower", "flower", "scatter", 0, 1.2),
    ("dry_quiver_leaf", "Dry Quiver Leaf", "dead_tree", "scatter", 0, 1.0),
    ("dead_quiver_branch_02", "Quiver Branch 02", "dead_tree", "scatter", 0, 1.0),
    # --- VELVET CIRCUIT (abstract neon & chrome) ---
    ("vintage_spacecraft_instrument", "Spacecraft Instrument", "instrument", "hero", 1, 1.0),
    ("modular_industrial_pipes_01", "Industrial Pipes", "machine", "hero", 1, 1.0),
    ("modular_airduct_circular_01", "Airduct", "machine", "medium", 1, 1.0),
    ("utility_box_01", "Utility Box", "container", "medium", 1, 1.0),
    ("power_box_01", "Power Box", "machine", "medium", 1, 1.0),
    ("metal_tool_chest", "Tool Chest", "container", "medium", 1, 1.0),
    ("barrel_03", "Barrel", "container", "medium", 1, 1.0),
    ("boombox", "Boombox", "electronics", "medium", 1, 1.0),
    ("industrial_pipe_lamp", "Pipe Lamp", "lamp", "medium", 1, 0.8),
    ("circuit_board", "Circuit Board", "electronics", "scatter", 1, 1.5),
    ("metal_trash_can", "Trash Can", "container", "scatter", 1, 1.0),
    ("security_camera_01", "Security Camera", "electronics", "scatter", 1, 1.2),
    ("modular_electric_cables", "Electric Cables", "machine", "scatter", 1, 1.0),
    ("metal_jerrycan", "Jerrycan", "container", "scatter", 1, 1.0),
    ("large_iron_gate", "Iron Gate", "ruin", "hero", 1, 1.0),
    ("modular_factory_facade", "Factory Facade", "machine", "hero", 1, 1.0),
    ("modular_fire_escape", "Fire Escape", "machine", "hero", 1, 1.0),
    ("modular_electricity_poles", "Electricity Poles", "machine", "hero", 1, 1.0),
    ("overhead_crane", "Overhead Crane", "machine", "hero", 1, 1.0),
    ("street_lamp_01", "Street Lamp", "lamp", "hero", 1, 1.0),
    ("rollershutter_door", "Rollershutter Door", "machine", "medium", 1, 1.0),
    ("modular_chainlink_fence", "Chainlink Fence", "machine", "medium", 1, 1.0),
    ("fire_hydrant", "Fire Hydrant", "machine", "medium", 1, 1.0),
    ("concrete_road_barrier", "Road Barrier", "machine", "medium", 1, 1.0),
    ("korean_fire_extinguisher_01", "Fire Extinguisher", "machine", "medium", 1, 1.0),
    ("modular_street_seating", "Street Seating", "furniture", "medium", 1, 1.0),
    ("painted_wooden_bench", "Wooden Bench", "furniture", "medium", 1, 1.0),
    ("metal_stool_01", "Metal Stool", "furniture", "medium", 1, 1.0),
    ("wooden_picnic_table", "Picnic Table", "furniture", "medium", 1, 1.0),
    ("vintage_radio_transceiver", "Radio Transceiver", "electronics", "medium", 1, 1.0),
    ("security_light", "Security Light", "lamp", "medium", 1, 1.0),
    ("caged_hanging_light", "Caged Hanging Light", "lamp", "medium", 1, 1.0),
    ("industrial_caged_sconce", "Caged Sconce", "lamp", "medium", 1, 1.0),
    ("mounted_fluorescent_lights", "Fluorescent Lights", "lamp", "medium", 1, 1.0),
    ("water_manhole_cover", "Manhole Cover", "machine", "scatter", 1, 1.0),
    ("old_tyre", "Old Tyre", "machine", "scatter", 1, 1.0),
    ("rusted_wheel_rim_01", "Wheel Rim", "machine", "scatter", 1, 1.0),
    ("cardboard_box_01", "Cardboard Box", "container", "scatter", 1, 1.0),
    ("plastic_crate_02", "Plastic Crate", "container", "scatter", 1, 1.0),
    ("trashbag", "Trashbag", "container", "scatter", 1, 1.0),
    ("spray_paint_bottles_02", "Spray Paint", "tool", "scatter", 1, 1.0),
    ("cassette_player", "Cassette Player", "electronics", "scatter", 1, 1.0),
    ("television_02", "Television", "electronics", "scatter", 1, 1.0),
    ("street_rat", "Street Rat", "creature", "scatter", 1, 1.2),
    # --- TIDE GARDENS (coral & kelp) ---
    ("coast_rocks_05", "Reef Rocks", "rock", "hero", 2, 1.2),
    ("coastal_cliff_01", "Coastal Cliff", "rock", "hero", 2, 1.0),
    ("bronze_whale_statue", "Whale Statue", "statue", "hero", 2, 1.0),
    ("anthurium_botany_01", "Anthurium", "plant", "medium", 2, 1.3),
    ("calathea_orbifolia_01", "Calathea", "plant", "medium", 2, 1.3),
    ("coast_land_rocks_02", "Coast Rocks", "rock", "medium", 2, 1.0),
    ("ocean_buoy", "Ocean Buoy", "nautical", "medium", 2, 1.0),
    ("fern_02", "Fern", "plant", "medium", 2, 1.2),
    ("lambis_shell", "Lambis Shell", "shell", "scatter", 2, 2.5),
    ("sand_rocks_small_01", "Sand Rocks", "rock", "scatter", 2, 1.2),
    ("moss_01", "Moss", "plant", "scatter", 2, 1.5),
    ("shrub_01", "Shrub", "plant", "scatter", 2, 1.2),
    ("periwinkle_plant", "Periwinkle", "plant", "scatter", 2, 1.2),
    ("coast_rocks_03", "Coast Rocks 03", "rock", "hero", 2, 1.0),
    ("pachira_aquatica_01", "Pachira Tree", "tree", "hero", 2, 1.0),
    ("modular_wooden_pier", "Wooden Pier", "nautical", "hero", 2, 1.0),
    ("lateral_sea_marker", "Sea Marker", "nautical", "hero", 2, 1.0),
    ("bronze_shark_statue", "Shark Statue", "statue", "medium", 2, 1.0),
    ("bronze_ray_statue", "Ray Statue", "statue", "medium", 2, 1.0),
    ("wooden_barrels_01", "Wooden Barrels", "container", "medium", 2, 1.0),
    ("wooden_crate_01", "Wooden Crate", "container", "medium", 2, 1.0),
    ("wooden_lantern_01", "Wooden Lantern", "lamp", "medium", 2, 1.0),
    ("shrub_02", "Shrub 02", "plant", "medium", 2, 1.0),
    ("potted_plant_01", "Potted Plant", "plant", "medium", 2, 1.0),
    ("planter_box_02", "Planter Box", "vase", "medium", 2, 1.0),
    ("shrub_03", "Shrub 03", "plant", "scatter", 2, 1.0),
    ("shrub_04", "Shrub 04", "plant", "scatter", 2, 1.0),
    ("grass_bermuda_01", "Bermuda Grass", "plant", "scatter", 2, 1.0),
    ("lifebuoy", "Lifebuoy", "nautical", "scatter", 2, 1.0),
    ("life_jacket", "Life Jacket", "nautical", "scatter", 2, 1.0),
    ("wooden_bucket_01", "Wooden Bucket", "container", "scatter", 2, 1.0),
    ("Ukulele_01", "Ukulele", "instrument", "scatter", 2, 1.0),
    # --- GLASS EXPANSE (ice & crystal) ---
    ("moon_rock_01", "Moon Rock", "rock", "hero", 3, 1.2),
    ("moon_rock_05", "Moon Rock Formation", "rock", "hero", 3, 1.2),
    ("marble_bust_01", "Marble Bust", "statue", "hero", 3, 1.0),
    ("horse_statue_01", "Porcelain Horse", "statue", "medium", 3, 1.0),
    ("moon_rock_02", "Moon Boulder", "rock", "medium", 3, 1.0),
    ("namaqualand_rocks_01", "Quartz Rocks", "rock", "medium", 3, 1.0),
    ("ceramic_vase_01", "Ceramic Vase", "vase", "medium", 3, 0.9),
    ("namaqualand_stones_01", "Quartz Stones", "rock", "scatter", 3, 1.2),
    ("crystalline_iceplant", "Crystalline Iceplant", "plant", "scatter", 3, 1.3),
    ("stone_01", "Quartz Gravel", "rock", "scatter", 3, 1.2),
    ("flower_heliophila", "Heliophila Flower", "flower", "scatter", 3, 1.3),
    ("jug_01", "White Jug", "vase", "scatter", 3, 0.9),
    ("Chandelier_01", "Chandelier", "lamp", "hero", 3, 1.0),
    ("rock_moss_set_01", "Moss Rock Set", "rock", "hero", 3, 1.0),
    ("gothic_statue", "Gothic Statue", "statue", "hero", 3, 1.0),
    ("Chandelier_02", "Chandelier 02", "lamp", "medium", 3, 1.0),
    ("concrete_cat_statue", "Cat Statue", "statue", "medium", 3, 1.0),
    ("lion_head", "Lion Head", "statue", "medium", 3, 1.0),
    ("horse_head", "Horse Head", "statue", "medium", 3, 1.0),
    ("bull_head", "Bull Head", "statue", "medium", 3, 1.0),
    ("antique_ceramic_vase_01", "Antique Vase", "vase", "medium", 3, 1.0),
    ("brass_vase_01", "Brass Vase", "vase", "medium", 3, 1.0),
    ("brass_vase_02", "Brass Vase 02", "vase", "medium", 3, 1.0),
    ("brass_candleholders", "Brass Candleholders", "lamp", "medium", 3, 1.0),
    ("lantern_chandelier_01", "Lantern Chandelier", "lamp", "medium", 3, 1.0),
    ("chinese_chandelier", "Chinese Chandelier", "lamp", "medium", 3, 1.0),
    ("chess_set", "Chess Set", "decor", "medium", 3, 1.0),
    ("ornate_mirror_01", "Ornate Mirror", "decor", "medium", 3, 1.0),
    ("mantel_clock_01", "Mantel Clock", "decor", "medium", 3, 1.0),
    ("moon_rock_03", "Moon Rock 03", "rock", "scatter", 3, 1.2),
    ("moon_rock_04", "Moon Rock 04", "rock", "scatter", 3, 1.2),
    ("moon_rock_06", "Moon Rock 06", "rock", "scatter", 3, 1.2),
    ("moon_rock_07", "Moon Rock 07", "rock", "scatter", 3, 1.2),
    ("rock_07", "Rock", "rock", "scatter", 3, 1.0),
    ("rock_09", "Rock 09", "rock", "scatter", 3, 1.0),
    ("brass_goblets", "Brass Goblets", "vase", "scatter", 3, 1.0),
    ("brass_pot_01", "Brass Pot", "vase", "scatter", 3, 1.0),
    ("wooden_candlestick", "Candlestick", "lamp", "scatter", 3, 1.0),
    ("carved_wooden_elephant", "Carved Elephant", "decor", "scatter", 3, 1.0),
    ("carved_wooden_plate", "Carved Plate", "decor", "scatter", 3, 1.0),
    # --- CINDER REACH (ember at dusk, with fire) ---
    ("stone_fire_pit", "Stone Fire Pit", "ruin", "hero", 4, 1.0),
    ("barrel_stove", "Barrel Stove", "machine", "medium", 4, 1.0),
    ("brass_diya_lantern", "Diya Lantern", "lamp", "medium", 4, 1.0),
    ("vintage_oil_lamp", "Oil Lamp", "lamp", "medium", 4, 1.0),
    ("Lantern_01", "Lantern", "lamp", "medium", 4, 1.0),
    ("propane_tank", "Propane Tank", "machine", "scatter", 4, 1.0),
    # --- MIRAGE CIRCUIT (sun-bleached velvet) ---
    ("covered_car", "Covered Car", "machine", "hero", 5, 1.0),
    ("street_lamp_02", "Street Lamp", "lamp", "medium", 5, 1.0),
    ("vintage_suitcase", "Vintage Suitcase", "decor", "medium", 5, 1.0),
    ("wooden_ladder", "Wooden Ladder", "tool", "medium", 5, 1.0),
    # --- ABYSS TERRACES (deep tide, shipwreck cove) ---
    ("dutch_ship_medium", "Dutch Ship", "nautical", "hero", 6, 1.0),
    ("treasure_chest", "Treasure Chest", "container", "medium", 6, 1.0),
    ("old_military_crate", "Military Crate", "container", "medium", 6, 1.0),
    ("seadogs_compass", "Seadogs Compass", "tool", "scatter", 6, 1.0),
    # --- DAWN EXPANSE (pale glass morning, garden) ---
    ("jacaranda_tree", "Jacaranda Tree", "tree", "hero", 7, 1.0),
    ("garden_gnome", "Garden Gnome", "decor", "medium", 7, 1.0),
    ("dandelion_01", "Dandelion", "flower", "scatter", 7, 1.0),
    ("potted_plant_04", "Potted Plant", "plant", "scatter", 7, 1.0),
    ("rubber_duck_toy", "Rubber Duck", "decor", "scatter", 7, 1.0),
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
    kinds = {p[2] for p in PACK}
    tiers = {p[3] for p in PACK}
    moods_used = {p[4] for p in PACK}
    assert tiers <= {"hero", "medium", "scatter"}, f"bad tiers: {tiers - {'hero', 'medium', 'scatter'}}"
    assert moods_used <= set(range(len(MOOD_IDS))), "mood index out of range"

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
        "version": 2,
        "assets": [
            {
                "id": slug,
                "name": name,
                "file": f"{slug}/{gltf_names[slug]}",
                "kind": kind,
                "tier": tier,
                "mood": mood,
                "mood_id": MOOD_IDS[mood],
                "scale": scale,
                "license": "CC0",
                "author": "Poly Haven",
                "source": f"https://polyhaven.com/a/{slug}",
            }
            for slug, name, kind, tier, mood, scale in PACK
        ],
    }
    # Native dimensions (mm -> m) let the app rescale each model to its
    # tier's target span — raw Poly Haven scans range from 0.1 m (shell)
    # to 90 m (cliff).
    catalog = json.loads(get(CATALOG))
    for entry in manifest["assets"]:
        dims = catalog.get(entry["id"], {}).get("dimensions")
        if dims:
            entry["dims"] = [round(d / 1000.0, 3) for d in dims]
    out = MODELS / "manifest.json"
    out.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"\n{len(PACK)} assets, {len(kinds)} kinds -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
