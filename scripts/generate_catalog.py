#!/usr/bin/env python3
"""OpenDatasets Dataset Catalog Generator.

Reads dataset metadata records from data/datasets/, validates them against
schemas/dataset.v1.schema.json using the validator logic, and writes a
deterministically sorted catalog array to frontend/public/data/catalog.json
using atomic file replacement.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

import jsonschema

# Ensure scripts directory is on sys.path for direct script execution
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.validate_datasets import (
    DEFAULT_DATA_DIR,
    DEFAULT_SCHEMA_PATH,
    check_duplicate_ids_and_slugs,
    load_schema,
    validate_dataset_file,
)

DEFAULT_OUTPUT_PATH = (
    Path("frontend/public/data/catalog.json")
    if Path("frontend").exists()
    else REPO_ROOT / "frontend" / "public" / "data" / "catalog.json"
)


def generate_catalog_data(
    data_dir: Path,
    schema_path: Path,
) -> tuple[list[dict[str, Any]] | None, list[str]]:
    """Validate datasets and generate a deterministically sorted catalog list.

    Returns:
        (sorted_catalog_records, error_messages)
    """
    schema_data, schema_errors = load_schema(schema_path)
    if schema_errors or schema_data is None:
        return None, schema_errors

    validator = jsonschema.Draft7Validator(schema_data)

    if not data_dir.exists():
        return None, [f"Data directory '{data_dir}' does not exist."]

    files = sorted(data_dir.glob("*.json"))
    if not files:
        return None, [f"No dataset JSON files found in '{data_dir}'."]

    errors: list[str] = []
    loaded_datasets: list[tuple[Path, dict[str, Any]]] = []

    for file_path in files:
        data, file_errors = validate_dataset_file(file_path, validator)
        if file_errors:
            errors.extend(file_errors)
        elif data is not None:
            loaded_datasets.append((file_path, data))

    # Cross-dataset checks: uniqueness of id and slug
    dup_errors = check_duplicate_ids_and_slugs(loaded_datasets)
    if dup_errors:
        errors.extend(dup_errors)

    if errors:
        return None, errors

    # Deterministic sort by dataset id
    catalog = [data for _, data in loaded_datasets]
    catalog.sort(key=lambda item: item.get("id", ""))

    return catalog, []


def write_catalog_atomic(catalog_data: list[dict[str, Any]], output_path: Path) -> None:
    """Write catalog JSON atomically to avoid partial or corrupted writes."""
    output_path = output_path.resolve()
    output_dir = output_path.parent
    output_dir.mkdir(parents=True, exist_ok=True)

    # Serialize with deterministic key ordering and indentation
    content = json.dumps(catalog_data, indent=2, ensure_ascii=False) + "\n"

    # Write to a temporary file in the same directory, then rename atomically
    temp_file = tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=output_dir,
        delete=False,
        prefix=".catalog.",
        suffix=".tmp",
    )
    temp_path = Path(temp_file.name)
    try:
        temp_file.write(content)
        temp_file.flush()
        os.fsync(temp_file.fileno())
        temp_file.close()
        # Atomic replacement on POSIX
        temp_path.replace(output_path)
    except Exception:
        if temp_path.exists():
            temp_path.unlink()
        raise


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for catalog generation."""
    parser = argparse.ArgumentParser(
        description="Generate frontend/public/data/catalog.json from data/datasets/."
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=DEFAULT_DATA_DIR,
        help=f"Path to dataset JSON directory (default: {DEFAULT_DATA_DIR})",
    )
    parser.add_argument(
        "--schema",
        type=Path,
        default=DEFAULT_SCHEMA_PATH,
        help=f"Path to JSON schema (default: {DEFAULT_SCHEMA_PATH})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help=f"Target catalog file path (default: {DEFAULT_OUTPUT_PATH})",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress informational stdout output.",
    )

    args = parser.parse_args(argv)

    catalog, errors = generate_catalog_data(
        data_dir=args.data_dir,
        schema_path=args.schema,
    )

    if errors or catalog is None:
        print("\n=======================================================", file=sys.stderr)
        print(" [FAIL] Catalog Generation Aborted Due to Validation Errors", file=sys.stderr)
        print("=======================================================", file=sys.stderr)
        for err in errors:
            print(f"  ✗ {err}", file=sys.stderr)
        print("\nThe existing catalog (if any) was NOT modified.", file=sys.stderr)
        return 1

    try:
        write_catalog_atomic(catalog, args.output)
    except Exception as exc:
        print(f"Error writing catalog to '{args.output}': {exc}", file=sys.stderr)
        return 1

    if not args.quiet:
        print("=======================================================")
        print(" [OK] OpenDatasets Catalog Generated Successfully")
        print("=======================================================")
        print(f"  ✓ Source datasets: {args.data_dir} ({len(catalog)} datasets)")
        print(f"  ✓ Output file:     {args.output}")
        for ds in catalog:
            print(f"    • {ds.get('name')} (id: {ds.get('id')})")
        print("=======================================================")

    return 0


if __name__ == "__main__":
    sys.exit(main())
