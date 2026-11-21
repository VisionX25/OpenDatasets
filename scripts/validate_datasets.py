#!/usr/bin/env python3
"""OpenDatasets Dataset Metadata Validator.

Validates dataset JSON metadata files against the OpenDatasets JSON Schema,
verifies URL syntax without performing network requests, and ensures uniqueness
of dataset IDs and slugs across the catalog.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

try:
    import jsonschema
    from jsonschema.exceptions import ValidationError
except ImportError:
    print(
        "Error: 'jsonschema' package is required. Install with: pip install jsonschema",
        file=sys.stderr,
    )
    sys.exit(1)


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.audit_semantic_duplicates import (
    normalize_title,
    normalize_url,
    normalize_doi,
    is_generic_hosting_url,
    extract_discriminating_features,
)

DEFAULT_SCHEMA_PATH = (
    Path("schemas/dataset.v1.schema.json")
    if Path("schemas/dataset.v1.schema.json").exists()
    else REPO_ROOT / "schemas" / "dataset.v1.schema.json"
)
DEFAULT_DATA_DIR = (
    Path("data/datasets")
    if Path("data/datasets").exists()
    else REPO_ROOT / "data" / "datasets"
)


def is_valid_http_url(url: Any) -> tuple[bool, str]:
    """Validate HTTP/HTTPS URL syntax without making network requests."""
    if not isinstance(url, str):
        return False, "URL must be a string."
    if not url.strip():
        return False, "URL must not be empty or whitespace."
    if re.search(r"\s", url):
        return False, f"URL contains whitespace: '{url}'"

    try:
        parsed = urlparse(url)
    except Exception as exc:
        return False, f"Failed to parse URL '{url}': {exc}"

    if parsed.scheme not in ("http", "https"):
        return (
            False,
            f"URL scheme must be 'http' or 'https', got '{parsed.scheme}' in '{url}'",
        )
    if not parsed.netloc:
        return False, f"URL is missing a network domain (netloc) in '{url}'"

    return True, ""


def find_urls_in_dict(obj: Any, current_path: str = "") -> list[tuple[str, str]]:
    """Recursively collect (json_path, url_value) pairs from a JSON structure."""
    urls: list[tuple[str, str]] = []
    if isinstance(obj, dict):
        for key, val in obj.items():
            sub_path = f"{current_path}.{key}" if current_path else key
            if key == "url" or key.endswith("_url"):
                if isinstance(val, str):
                    urls.append((sub_path, val))
            urls.extend(find_urls_in_dict(val, sub_path))
    elif isinstance(obj, list):
        for idx, item in enumerate(obj):
            sub_path = f"{current_path}[{idx}]"
            urls.extend(find_urls_in_dict(item, sub_path))
    return urls


def load_json_file(file_path: Path) -> tuple[dict[str, Any] | None, list[str]]:
    """Load JSON from a file, returning (parsed_data, error_messages)."""
    errors: list[str] = []
    if not file_path.exists():
        return None, [f"File not found: {file_path}"]
    if not file_path.is_file():
        return None, [f"Path is not a regular file: {file_path}"]

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            if not content.strip():
                return None, [f"{file_path}: File is empty."]
            data = json.loads(content)
            if not isinstance(data, dict):
                return None, [f"{file_path}: Top-level JSON entity must be an object."]
            return data, []
    except json.JSONDecodeError as exc:
        return None, [f"{file_path}: Malformed JSON (line {exc.lineno}, col {exc.colno}): {exc.msg}"]
    except Exception as exc:
        return None, [f"{file_path}: Error reading file: {exc}"]


def load_schema(schema_path: Path) -> tuple[dict[str, Any] | None, list[str]]:
    """Load and validate the JSON schema definition."""
    data, errors = load_json_file(schema_path)
    if errors or data is None:
        return None, errors

    try:
        jsonschema.Draft7Validator.check_schema(data)
    except Exception as exc:
        return None, [f"Schema '{schema_path}' is not valid Draft-7 schema: {exc}"]

    return data, []


def validate_dataset_data(
    data: dict[str, Any],
    validator: jsonschema.Draft7Validator,
    filename: str = "<memory>",
) -> list[str]:
    """Validate a parsed dataset dictionary against schema and semantic rules."""
    errors: list[str] = []

    # 1. JSON Schema validation
    schema_errors = sorted(validator.iter_errors(data), key=lambda e: e.path)
    for err in schema_errors:
        path = ".".join(str(p) for p in err.path) if err.path else "<root>"
        errors.append(f"{filename} [{path}]: {err.message}")

    # 2. Deep URL syntax checks (no network access)
    urls = find_urls_in_dict(data)
    for json_path, url_val in urls:
        valid, msg = is_valid_http_url(url_val)
        if not valid:
            errors.append(f"{filename} [{json_path}]: Invalid URL syntax - {msg}")

    return errors


def validate_dataset_file(
    file_path: Path,
    validator: jsonschema.Draft7Validator,
) -> tuple[dict[str, Any] | None, list[str]]:
    """Validate a single dataset file, returning (data, errors)."""
    data, load_errors = load_json_file(file_path)
    if load_errors or data is None:
        return None, load_errors

    validation_errors = validate_dataset_data(
        data, validator, filename=str(file_path)
    )
    return data, validation_errors


def normalize_dataset_name(name: str) -> str:
    """Normalize a dataset name for uniqueness check (lowercased, stripped of punctuation and whitespace)."""
    if not name or not isinstance(name, str):
        return ""
    return re.sub(r"[^\w]", "", name.lower())


def check_duplicate_records(
    datasets: list[tuple[Path, dict[str, Any]]]
) -> tuple[list[str], list[str]]:
    """Ensure dataset records are unique across the repository.

    Returns:
        (errors, warnings)

    Hard Errors (must fail CI):
        - Duplicate dataset ID across multiple files
        - Duplicate dataset slug across multiple files
        - Duplicate normalized dataset name across multiple files
        - Unambiguous identical duplicate dataset (shared canonical DOI/URL with identical normalized name)

    Warnings (for maintainer human review, does not fail CI):
        - Legitimate related benchmark families sharing DOI or homepage with distinguishing features
        - High fuzzy title similarity (> 0.85) between distinct benchmark iterations (e.g., ISIC 2018 vs 2019)
    """
    errors: list[str] = []
    warnings: list[str] = []
    id_map: dict[str, list[str]] = defaultdict(list)
    slug_map: dict[str, list[str]] = defaultdict(list)
    name_map: dict[str, list[tuple[str, str]]] = defaultdict(list)
    doi_map: dict[str, list[tuple[Path, dict[str, Any]]]] = defaultdict(list)
    url_map: dict[str, list[tuple[Path, dict[str, Any]]]] = defaultdict(list)

    for path, data in datasets:
        ds_id = data.get("id")
        ds_slug = data.get("slug")
        ds_name = data.get("name")
        path_str = str(path)

        if ds_id and isinstance(ds_id, str):
            id_map[ds_id].append(path_str)
        if ds_slug and isinstance(ds_slug, str):
            slug_map[ds_slug].append(path_str)
        if ds_name and isinstance(ds_name, str):
            norm_name = normalize_dataset_name(ds_name)
            if norm_name:
                name_map[norm_name].append((path_str, ds_name))

        cit = data.get("citation") or {}
        doi = normalize_doi(cit.get("doi", ""))
        if doi:
            doi_map[doi].append((path, data))

        hp = data.get("homepage_url", "")
        if hp and not is_generic_hosting_url(hp):
            norm_hp = normalize_url(hp)
            if norm_hp:
                url_map[norm_hp].append((path, data))

    # 1. Duplicate ID check (Hard error)
    for ds_id, paths in sorted(id_map.items()):
        if len(paths) > 1:
            errors.append(
                f"Duplicate dataset ID '{ds_id}' found across multiple files: {', '.join(paths)}"
            )

    # 2. Duplicate slug check (Hard error)
    for ds_slug, paths in sorted(slug_map.items()):
        if len(paths) > 1:
            errors.append(
                f"Duplicate dataset slug '{ds_slug}' found across multiple files: {', '.join(paths)}"
            )

    # 3. Duplicate normalized name check (Hard error)
    for norm_name, items in sorted(name_map.items()):
        if len(items) > 1:
            paths = [it[0] for it in items]
            names = [f"'{it[1]}'" for it in items]
            errors.append(
                f"Duplicate normalized dataset name '{norm_name}' ({', '.join(names)}) found across multiple files: {', '.join(paths)}"
            )

    # 4. Shared DOI check (Differentiate hard duplicate vs alternative title candidate vs legitimate benchmark family)
    for doi, entries in sorted(doi_map.items()):
        if len(entries) > 1:
            for i in range(len(entries)):
                for j in range(i + 1, len(entries)):
                    p1, d1 = entries[i]
                    p2, d2 = entries[j]
                    id1 = d1.get("id", "")
                    id2 = d2.get("id", "")
                    name1 = d1.get("name", "")
                    name2 = d2.get("name", "")
                    same_name = normalize_dataset_name(name1) == normalize_dataset_name(name2)
                    disc = extract_discriminating_features(d1, d2)
                    if same_name:
                        errors.append(
                            f"Identical duplicate dataset sharing citation DOI '{doi}': '{id1}' ({p1}) and '{id2}' ({p2})"
                        )
                    elif not disc:
                        warnings.append(
                            f"Ambiguous collision / possible duplicate (alternative title candidate) sharing citation DOI '{doi}': '{id1}' ('{name1}') and '{id2}' ('{name2}') lack discriminating features — unresolved human review required"
                        )
                    else:
                        mods1 = set(d1.get("modalities", []))
                        mods2 = set(d2.get("modalities", []))
                        pub1 = d1.get("publisher", {}).get("name", "")
                        pub2 = d2.get("publisher", {}).get("name", "")
                        is_same_pub = bool(pub1 and pub2 and pub1.strip().lower() == pub2.strip().lower())
                        shares_domain = bool(mods1 & mods2)
                        if is_same_pub or shares_domain:
                            warnings.append(
                                f"Legitimate benchmark family sharing DOI '{doi}': '{id1}' and '{id2}' (differentiating features: {', '.join(disc)})"
                            )
                        else:
                            warnings.append(
                                f"Shared publication / paper reference for distinct datasets sharing DOI '{doi}': '{id1}' and '{id2}' (differentiating features: {', '.join(disc)})"
                            )

    # 5. Shared Homepage check (Differentiate hard duplicate vs alternative title candidate vs legitimate benchmark family)
    for url, entries in sorted(url_map.items()):
        if len(entries) > 1:
            for i in range(len(entries)):
                for j in range(i + 1, len(entries)):
                    p1, d1 = entries[i]
                    p2, d2 = entries[j]
                    id1 = d1.get("id", "")
                    id2 = d2.get("id", "")
                    name1 = d1.get("name", "")
                    name2 = d2.get("name", "")
                    same_name = normalize_dataset_name(name1) == normalize_dataset_name(name2)
                    disc = extract_discriminating_features(d1, d2)
                    if same_name:
                        errors.append(
                            f"Identical duplicate dataset sharing homepage URL '{url}': '{id1}' ({p1}) and '{id2}' ({p2})"
                        )
                    elif not disc:
                        warnings.append(
                            f"Ambiguous collision / possible duplicate (alternative title candidate) sharing homepage URL '{url}': '{id1}' ('{name1}') and '{id2}' ('{name2}') lack discriminating features — unresolved human review required"
                        )
                    else:
                        mods1 = set(d1.get("modalities", []))
                        mods2 = set(d2.get("modalities", []))
                        pub1 = d1.get("publisher", {}).get("name", "")
                        pub2 = d2.get("publisher", {}).get("name", "")
                        is_same_pub = bool(pub1 and pub2 and pub1.strip().lower() == pub2.strip().lower())
                        shares_domain = bool(mods1 & mods2)
                        if is_same_pub or shares_domain:
                            warnings.append(
                                f"Legitimate benchmark family sharing homepage '{url}': '{id1}' and '{id2}' (differentiating features: {', '.join(disc)})"
                            )
                        else:
                            warnings.append(
                                f"Shared homepage reference for distinct datasets sharing '{url}': '{id1}' and '{id2}' (differentiating features: {', '.join(disc)})"
                            )

    return errors, warnings


def check_duplicate_ids_and_slugs(
    datasets: list[tuple[Path, dict[str, Any]]]
) -> list[str]:
    """Ensure dataset IDs and slugs are unique across the repository (backwards compatibility)."""
    errors, _ = check_duplicate_records(datasets)
    return errors


def validate_all_datasets(
    data_dir: Path,
    schema_path: Path,
    target_files: list[Path] | None = None,
    verbose: bool = False,
) -> tuple[int, int, list[str]]:
    """Validate all dataset files or a specified subset.

    Returns:
        (total_checked, total_passed, all_errors)
    """
    schema_data, schema_errors = load_schema(schema_path)
    if schema_errors or schema_data is None:
        return 0, 0, schema_errors

    validator = jsonschema.Draft7Validator(schema_data)

    if target_files:
        files = target_files
    else:
        if not data_dir.exists():
            return 0, 0, [f"Data directory '{data_dir}' does not exist."]
        files = sorted(data_dir.glob("*.json"))

    if not files:
        return 0, 0, [f"No dataset JSON files found in '{data_dir}'."]

    all_errors: list[str] = []
    loaded_datasets: list[tuple[Path, dict[str, Any]]] = []
    total_passed = 0

    for file_path in files:
        data, errors = validate_dataset_file(file_path, validator)
        if errors:
            all_errors.extend(errors)
        else:
            total_passed += 1
            if data is not None:
                loaded_datasets.append((file_path, data))

    # Cross-dataset checks (duplicates across all files)
    dup_errors, dup_warnings = check_duplicate_records(loaded_datasets)
    if dup_errors:
        all_errors.extend(dup_errors)

    if verbose and dup_warnings:
        for w in dup_warnings:
            print(f"  [WARN] {w}")

    return len(files), total_passed, all_errors


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for validate_datasets.py."""
    parser = argparse.ArgumentParser(
        description="Validate OpenDatasets JSON metadata against dataset schema."
    )
    parser.add_argument(
        "--schema",
        type=Path,
        default=DEFAULT_SCHEMA_PATH,
        help=f"Path to JSON schema file (default: {DEFAULT_SCHEMA_PATH})",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=DEFAULT_DATA_DIR,
        help=f"Directory containing dataset JSON files (default: {DEFAULT_DATA_DIR})",
    )
    parser.add_argument(
        "files",
        nargs="*",
        type=Path,
        help="Optional specific dataset JSON files to validate.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Only display errors and final status summary.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Display detailed diagnostic output.",
    )

    args = parser.parse_args(argv)

    target_files = [Path(f) for f in args.files] if args.files else None

    total, passed, errors = validate_all_datasets(
        data_dir=args.data_dir,
        schema_path=args.schema,
        target_files=target_files,
        verbose=args.verbose,
    )

    if errors:
        print("\n=======================================================", file=sys.stderr)
        print(" [FAIL] OpenDatasets Metadata Validation Errors", file=sys.stderr)
        print("=======================================================", file=sys.stderr)
        for err in errors:
            print(f"  ✗ {err}", file=sys.stderr)
        print(f"\nResult: FAILED ({len(errors)} error(s) detected across {total} checked file(s))", file=sys.stderr)
        return 1

    if not args.quiet:
        print("=======================================================")
        print(" [PASS] OpenDatasets Metadata Validation")
        print("=======================================================")
        print(f"  ✓ Schema: {args.schema}")
        print(f"  ✓ Validated {total} dataset file(s)")
        print("  ✓ All required fields present")
        print("  ✓ Modalities and types conform to schema")
        print("  ✓ URL syntaxes verified (no network calls)")
        print("  ✓ Dataset IDs and slugs are unique")
        print("=======================================================")
        print("Result: ALL DATASETS VALID")

    return 0


if __name__ == "__main__":
    sys.exit(main())
