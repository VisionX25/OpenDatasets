#!/usr/bin/env python3
"""Emit static entry points so GitHub Pages can serve SPA deep links directly."""

import argparse
import json
from pathlib import Path

CATEGORIES = (
    "computer-vision", "natural-language-processing", "audio-speech",
    "tabular-time-series", "multimodal-generative", "evaluation-benchmarks",
)


def prepare_pages(output: Path, slugs: list[str]) -> int:
    index = output / "index.html"
    if not index.is_file():
        raise ValueError(f"Build output is missing: {index}")
    shell = index.read_bytes()
    routes = {"explore", "datasets", "about"}
    routes.update(f"datasets/{category}" for category in CATEGORIES)
    for slug in slugs:
        # Catalog validation normally guarantees this; keep file writes bounded too.
        if not slug or any(c not in "abcdefghijklmnopqrstuvwxyz0123456789-" for c in slug):
            raise ValueError(f"Unsafe dataset slug: {slug!r}")
        routes.update((f"dataset/{slug}", f"datasets/{slug}"))
    for route in sorted(routes):
        target = output / route / "index.html"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(shell)
    # Unknown slugs still reach the app's accessible not-found view (HTTP 404).
    (output / "404.html").write_bytes(shell)
    (output / ".nojekyll").touch()
    return len(routes)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("frontend/dist"))
    parser.add_argument("--catalog", type=Path, default=Path("frontend/public/data/catalog.json"))
    args = parser.parse_args()
    records = json.loads(args.catalog.read_text(encoding="utf-8"))
    count = prepare_pages(args.output, [record["slug"] for record in records])
    print(f"Prepared {count} deep-link entry points and 404.html in {args.output}")
