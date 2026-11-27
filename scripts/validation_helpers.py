#!/usr/bin/env python3
"""Shared validation and normalization helpers for OpenDatasets.

Decouples core dataset validation (scripts/validate_datasets.py) from heavy audit
modules (scripts/audit_semantic_duplicates.py, scripts/migrate_sample_count_breakdowns.py)
by providing pure, lightweight normalization and classification functions without
cross-dependencies.
"""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

# Stop words for title token extraction
STOP_WORDS: set[str] = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "based",
    "benchmark",
    "by",
    "challenge",
    "corpus",
    "data",
    "database",
    "dataset",
    "datasets",
    "evaluation",
    "for",
    "from",
    "in",
    "of",
    "on",
    "the",
    "using",
    "with",
}

# Generic hosting / publisher root domains that MUST NOT trigger duplicate match on domain alone
GENERIC_HOSTING_DOMAINS: set[str] = {
    "archive.ics.uci.edu",
    "arxiv.org",
    "challenge.isic-archive.com",
    "crossref.org",
    "data.gov",
    "disc.gsfc.nasa.gov",
    "doi.org",
    "dx.doi.org",
    "github.com",
    "huggingface.co",
    "isic-archive.com",
    "kaggle.com",
    "ncbi.nlm.nih.gov",
    "nih.gov",
    "openml.org",
    "openreview.net",
    "paperswithcode.com",
    "physionet.org",
    "registry.opendata.aws",
    "rrc.cvc.uab.cat",
    "rrc.cvc.uab.es",
    "spacenet.ai",
    "wikipedia.org",
    "zenodo.org",
}

# Generic root path segments on multi-dataset hosting portals
GENERIC_PATH_SEGMENTS: set[str] = {
    "",
    "/",
    "/data",
    "/dataset",
    "/datasets",
    "/forum",
    "/record",
    "/records",
    "/resources",
    "/archive",
    "/downloads",
}

# Tracking and analytics query parameters to safely strip
TRACKING_QUERY_PARAMS: set[str] = {
    "campaign",
    "fbclid",
    "gclid",
    "medium",
    "ref",
    "ref_src",
    "ref_url",
    "source",
    "utm_campaign",
    "utm_content",
    "utm_medium",
    "utm_source",
    "utm_term",
}

# Regular expressions for discriminating tokens (version, class count, sensor, sub-product)
DISCRIMINATING_PATTERNS: list[str] = [
    r"\bv\d+(\.\d+)?\b",
    r"(?<=[a-z])v\d+\b",
    r"(?<!\d)(?:19\d\d|20\d\d)(?!\d)",
    r"\b\d{1,4}\b",
    r"\b(?:i|ii|iii|iv|v|vi)\b",
    r"\b(lidar|sensor|motion|camera|radar|sonar|eeg|ecg|emg|fmri|imu|gps|tabular|graph|3d|2d|audio|speech|video|image|text|nlp|pcb|phone|charity|nda|reference|global|active|cropland|note|daily|hourly|monthly|loco|perceptual|flow|depth|semantic|instance|panoptic|multimodal)\b",
    r"\b(code2|molpcba|molhiv|moltox21|ppa|citation2|collab|wikikg2|mag|papers100m|products|proteins|mag240m|pcqm4mv2|wikikg90mv2)\b",
]

# Standard partition keywords recognized by validator
STANDARD_PARTITION_KEYWORDS: tuple[str, ...] = (
    "train",
    "training",
    "val",
    "valid",
    "validation",
    "dev",
    "development",
    "test",
    "testing",
    "eval",
    "evaluation",
    "fold",
    "fine_tuning",
    "pretraining",
    "unsupervised",
    "unlabeled",
    "extra",
    "calibration",
    "holdout",
    "set-a",
    "set-b",
    "set-c",
    "set_a",
    "set_b",
    "set_c",
    "public_eval",
)

# Known entity stems for partition key and unit checks
ENTITY_STEMS: tuple[str, ...] = (
    "clip",
    "label",
    "image",
    "frame",
    "scan",
    "document",
    "page",
    "sentence",
    "word",
    "question",
    "query",
    "flow",
    "session",
    "participant",
    "patient",
    "subject",
    "traversal",
    "run",
    "patch",
    "box",
    "hour",
    "km",
    "class",
    "species",
    "sequence",
)

# Catalog datasets requiring documented manual review for partition/unit semantic divergence
KNOWN_SPECIAL_SEMANTIC_REVIEWS: dict[str, str] = {
    "ava-action": "Unit mismatch: declared total is 1.62M action labels, while splits represent 430 movie clips",
    "pubmed-200k-rct": "Unit/version mismatch: declared total is abstracts (195,654) while splits record sentences (237,690) from 20k subset",
    "isic-2018": "Multi-task benchmark: splits represent task1, task2, and task3 subsets with overlapping sample images",
    "btad-beantech-anomaly-detection": "Multi-subset benchmark: splits include both aggregate train/test and per-product subsets train_01..03, test_01..03",
    "unsw-nb15": "Benchmark subset partition: splits represent official partitioned subset (257,673 flows) of raw archive (2,540,044 flows)",
    "ms-coco": "Benchmark subset partition: splits represent 2017 detection train/val/test subset (163,957 images) of 330k raw archive",
    "hotpotqa": "Multi-evaluation benchmark: splits include both dev_distractor and dev_fullwiki evaluation settings",
}


def normalize_title(title: str) -> str:
    """Normalize dataset title by lowercasing and stripping non-alphanumeric characters."""
    if not title or not isinstance(title, str):
        return ""
    lowered = title.lower().strip()
    return re.sub(r"[^\w\s]", "", lowered)


def normalize_doi(doi: str) -> str:
    """Normalize DOI to canonical lowercase '10.xxxx/yyyy' format without resolver prefixes."""
    if not doi or not isinstance(doi, str):
        return ""
    cleaned = doi.strip()
    match = re.search(r"10\.\d{4,9}/[-._;()/:A-Za-z0-9]+", cleaned, re.IGNORECASE)
    if match:
        return match.group(0).lower().rstrip(".,;)")
    return cleaned.lower()


def normalize_url(url: str, preserve_paper_params: bool = True) -> str:
    """Safely canonicalize a URL for comparison.

    - Strips http/https scheme and www prefix
    - Lowercases hostname
    - Strips default ports (:80, :443)
    - Strips trailing slashes
    - Removes tracking/analytics parameters while preserving functional IDs
    - Normalizes DOI URLs to canonical resolver path
    """
    if not url or not isinstance(url, str):
        return ""
    cleaned = url.strip()
    try:
        parsed = urlparse(cleaned)
        netloc = parsed.netloc.lower()
        if netloc.startswith("www."):
            netloc = netloc[4:]
        if netloc.endswith(":80"):
            netloc = netloc[:-3]
        elif netloc.endswith(":443"):
            netloc = netloc[:-4]

        path = parsed.path.rstrip("/")

        # Handle DOI URLs: normalize https://doi.org/10.xxxx/... -> doi.org/10.xxxx/...
        if netloc in ("doi.org", "dx.doi.org"):
            doi_extracted = normalize_doi(path)
            if doi_extracted:
                return f"doi.org/{doi_extracted}"

        # Filter query parameters
        kept_query: list[str] = []
        if parsed.query:
            for param in parsed.query.split("&"):
                if not param:
                    continue
                k = param.split("=")[0].lower()
                if k in TRACKING_QUERY_PARAMS:
                    continue
                # Keep functional parameters (e.g. id= on openreview, ch= on rrc)
                if preserve_paper_params:
                    kept_query.append(param)

        canonical_query = f"?{'&'.join(sorted(kept_query))}" if kept_query else ""
        return f"{netloc}{path}{canonical_query}"
    except Exception:
        return cleaned.lower().rstrip("/")


def is_generic_hosting_url(url: str) -> bool:
    """Determine if a URL points to a generic hosting platform root or multi-dataset directory."""
    if not url or not isinstance(url, str):
        return True
    norm = normalize_url(url)
    if not norm:
        return True

    # Split netloc and path
    parts = norm.split("?", 1)[0].split("/")
    host = parts[0]
    path_segments = parts[1:]

    if host in GENERIC_HOSTING_DOMAINS:
        # Bare domain or single slash
        if not path_segments:
            return True
        first_segment = f"/{path_segments[0]}"
        if len(path_segments) == 1 and first_segment in GENERIC_PATH_SEGMENTS:
            return True
        # Portal listing directories like 'disc.gsfc.nasa.gov/datasets' or 'spacenet.ai/datasets'
        if len(path_segments) == 1 and path_segments[0] in ("datasets", "dataset", "data", "resources"):
            return True
        # Challenge general galleries like 'challenge.isic-archive.com/data'
        if host == "challenge.isic-archive.com" and path_segments == ["data"]:
            return True
        # OpenReview bare forum without paper id
        if host == "openreview.net" and path_segments == ["forum"] and "?" not in norm:
            return True

    return False


def extract_discriminating_features(record_a: dict[str, Any], record_b: dict[str, Any]) -> list[str]:
    """Detect presence of discriminating version, class count, or modality keywords."""
    discriminating: list[str] = []

    text_a = f"{record_a.get('id', '')} {record_a.get('name', '')}".lower()
    text_b = f"{record_b.get('id', '')} {record_b.get('name', '')}".lower()

    for pattern in DISCRIMINATING_PATTERNS:
        matches_a = set(re.findall(pattern, text_a))
        matches_b = set(re.findall(pattern, text_b))
        diff = (matches_a - matches_b) | (matches_b - matches_a)
        if diff:
            discriminating.extend(sorted(diff))

    # Modality differences
    mods_a = set(record_a.get("modalities", []))
    mods_b = set(record_b.get("modalities", []))
    diff_mods = (mods_a - mods_b) | (mods_b - mods_a)
    if diff_mods:
        discriminating.append(f"distinct_modalities:{sorted(mods_a)}_vs_{sorted(mods_b)}")

    # Task differences
    tasks_a = set(record_a.get("tasks", []))
    tasks_b = set(record_b.get("tasks", []))
    diff_tasks = (tasks_a - tasks_b) | (tasks_b - tasks_a)
    if diff_tasks:
        discriminating.append(f"distinct_tasks:{sorted(diff_tasks)}")

    return sorted(set(discriminating))


def is_partition_key(key: str) -> bool:
    """Return True if split key represents a standard dataset partition."""
    k_low = key.lower().strip()
    return any(p in k_low for p in STANDARD_PARTITION_KEYWORDS)


def check_unit_compatibility(
    splits: dict[str, Any],
    sample_unit: str,
    did: str = "",
) -> tuple[bool, str]:
    """Determine whether partition split units are compatible with the declared sample total.

    Returns:
        (is_compatible, diagnostic_reason)
    """
    if did in KNOWN_SPECIAL_SEMANTIC_REVIEWS:
        return False, KNOWN_SPECIAL_SEMANTIC_REVIEWS[did]

    clean_unit = sample_unit.strip().lower() if sample_unit else ""
    if not clean_unit:
        return False, "Sample unit is unspecified in sample_count"

    keys = list(splits.keys())
    if not keys:
        return False, "No partition split keys provided"

    # 1. Non-partition keys or class/entity distributions in splits
    non_partition_keys = [
        k for k in keys
        if not any(p in k.lower() for p in STANDARD_PARTITION_KEYWORDS)
    ]
    if non_partition_keys:
        return False, f"Splits contain non-partition or mixed-metric keys: {non_partition_keys[:3]}"

    # 2. Extract entity stems present in split keys
    split_entities = set()
    for k in keys:
        k_low = k.lower()
        for stem in ENTITY_STEMS:
            if stem in k_low:
                split_entities.add(stem)

    total_entities = {stem for stem in ENTITY_STEMS if stem in clean_unit}

    # 3. Detect conflicting unit entities between splits and declared total
    if split_entities and total_entities and not (split_entities & total_entities):
        return (
            False,
            f"Unit mismatch: splits indicate {sorted(split_entities)} while total unit is '{sample_unit}'",
        )

    # 4. Detect heterogeneous/mixed entity types across split keys
    if len(split_entities) > 1:
        return False, f"Mixed entity types within splits: {sorted(split_entities)}"

    return True, ""
