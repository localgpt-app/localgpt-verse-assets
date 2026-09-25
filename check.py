#!/usr/bin/env python3
"""Check that the manifests describe what the repository holds.

CI runs this on every change (.github/workflows/ci.yml). Model files may be
Git LFS pointers; only their presence is checked, never their contents.

    python3 check.py
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TIERS = {"hero", "medium", "scatter"}


def check_models(problems):
    manifest = json.loads((ROOT / "models" / "manifest.json").read_text())
    if manifest.get("version") != 2:
        problems.append(f"models/manifest.json: version {manifest.get('version')!r}, expected 2")
    assets = manifest.get("assets", [])
    ids = set()
    files = set()
    mood_ids = {}
    for asset in assets:
        label = f"models/manifest.json: {asset.get('id', '<no id>')}"
        for key in ("id", "name", "file", "kind", "tier", "mood", "mood_id",
                    "scale", "license", "author", "source", "dims"):
            if key not in asset:
                problems.append(f"{label}: missing {key}")
        if asset.get("id") in ids:
            problems.append(f"{label}: duplicate id")
        ids.add(asset.get("id"))
        if asset.get("tier") not in TIERS:
            problems.append(f"{label}: tier {asset.get('tier')!r} not in {sorted(TIERS)}")
        if not isinstance(asset.get("kind"), str) or not asset.get("kind"):
            problems.append(f"{label}: kind must be a non-empty string")
        if not (isinstance(asset.get("scale"), (int, float)) and asset["scale"] > 0):
            problems.append(f"{label}: scale must be a positive number")
        dims = asset.get("dims")
        if not (isinstance(dims, list) and len(dims) == 3
                and all(isinstance(d, (int, float)) and d > 0 for d in dims)):
            problems.append(f"{label}: dims must be three positive numbers")
        if asset.get("license") != "CC0":
            problems.append(f"{label}: license {asset.get('license')!r}, expected CC0")
        # `mood` is the position in Verse's world list; `mood_id` its stable
        # id. One must map to exactly one of the other.
        mood, mood_id = asset.get("mood"), asset.get("mood_id")
        if mood_ids.setdefault(mood, mood_id) != mood_id:
            problems.append(f"{label}: mood {mood} is {mood_ids[mood]!r} elsewhere, {mood_id!r} here")
        file = asset.get("file", "")
        files.add(file)
        if not (ROOT / "models" / file).is_file():
            problems.append(f"{label}: models/{file} does not exist")
    # Every shipped .glb must be listed; an unlisted one is dead weight.
    for glb in sorted((ROOT / "models").glob("*/*.glb")):
        rel = glb.relative_to(ROOT / "models").as_posix()
        if rel not in files:
            problems.append(f"models/{rel}: not in models/manifest.json")
    return len(assets)


def check_music(problems):
    music = json.loads((ROOT / "music" / "music.json").read_text())
    if music.get("license") != "CC0-1.0":
        problems.append(f"music/music.json: license {music.get('license')!r}, expected CC0-1.0")
    tracks = music.get("tracks", [])
    titles = set()
    for track in tracks:
        label = f"music/music.json: {track.get('title', '<no title>')}"
        for key in ("title", "artist", "album", "file", "license", "bpm"):
            if key not in track:
                problems.append(f"{label}: missing {key}")
        if track.get("title") in titles:
            problems.append(f"{label}: duplicate title")
        titles.add(track.get("title"))
        if not (ROOT / "music" / track.get("file", "")).is_file():
            problems.append(f"{label}: music/{track.get('file')} does not exist")
        if not (isinstance(track.get("bpm"), (int, float)) and track["bpm"] > 0):
            problems.append(f"{label}: bpm must be a positive number")
    if not (ROOT / "music" / "NOTICE").is_file():
        problems.append("music/NOTICE is missing")
    return len(tracks)


def main():
    problems = []
    models = check_models(problems)
    tracks = check_music(problems)
    for problem in problems:
        print(f"error: {problem}")
    if problems:
        print(f"{len(problems)} problem(s)")
        return 1
    print(f"ok: {models} models and {tracks} tracks match the repository")
    return 0


if __name__ == "__main__":
    sys.exit(main())
