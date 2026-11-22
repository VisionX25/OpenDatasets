#!/usr/bin/env python3
"""OpenDatasets Sample Count Split and Breakdown Migration Tool.

Audits sample_count across all catalog datasets, cleanly separates true
partition splits (train/val/test) from quantitative breakdown metrics (distances,
durations, secondary entity counts), generates audit inventories, and safely
migrates metadata without loss of numerical information.
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

# Ensure repository root is on sys.path
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

DEFAULT_DATASETS_DIR = REPO_ROOT / "data" / "datasets"
DEFAULT_REPORT_JSON = REPO_ROOT / "docs" / "audits" / "sample-count-breakdown-inventory.json"
DEFAULT_REPORT_MD = REPO_ROOT / "docs" / "audits" / "sample-count-breakdown-audit.md"

STANDARD_PARTITION_KEYWORDS = (
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

# Explicit, documented migrations for pure non-partition metrics
# Map dataset_id -> list of (split_key, breakdown_label, breakdown_unit)
SAFE_PURE_METRIC_MIGRATIONS: dict[str, list[tuple[str, str, str]]] = {
    "boreas": [
        ("driving_sequences", "driving sequences", "sequences"),
        ("total_driving_km", "total driving distance", "km"),
    ],
    "bigearthnet": [
        ("sentinel2_patches", "Sentinel-2 image patches", "patches"),
        ("corine_labels", "CORINE land cover classes", "classes"),
    ],
    "furniture-bench": [
        ("hours", "demonstration duration", "hours"),
    ],
    "dsec-stereo-event": [
        ("driving_sequences", "driving sequences", "sequences"),
        ("duration_minutes", "recording duration", "minutes"),
    ],
    "kitti-360": [
        ("driving_distance_km", "driving distance", "km"),
        ("laser_scans", "laser scans", "scans"),
        ("camera_images", "camera images", "images"),
    ],
    "semanticposs": [
        ("scans", "LiDAR scans", "scans"),
        ("points_millions", "point cloud points", "million_points"),
    ],
    "robonet": [
        ("frames", "video frames", "frames"),
    ],
    "openlane-v2": [
        ("sequences", "driving sequences", "sequences"),
        ("frames", "annotated frames", "frames"),
    ],
    "pandaset": [
        ("driving_scenes", "driving scenes", "scenes"),
        ("annotated_frames", "annotated frames", "frames"),
    ],
    "cadc-snow": [
        ("driving_sequences", "driving sequences", "sequences"),
        ("annotated_frames", "annotated frames", "frames"),
    ],
    "h3d-honda": [
        ("crowded_scenes", "crowded scenes", "scenes"),
        ("annotated_frames", "annotated frames", "frames"),
    ],
    "radiate": [
        ("annotated_radar_frames", "annotated radar frames", "frames"),
        ("scenarios", "driving scenarios", "scenarios"),
    ],
    "rellis-3d": [
        ("lidar_scans", "LiDAR scans", "scans"),
        ("annotated_images", "annotated images", "images"),
    ],
    "zod-zenseact": [
        ("single_frames", "single frames", "frames"),
        ("sequences", "sequences", "sequences"),
        ("drives", "drives", "drives"),
    ],
    "v2x-seq": [
        ("sequential_perception_frames", "sequential perception frames", "frames"),
        ("trajectory_forecasting_scenarios", "trajectory forecasting scenarios", "scenarios"),
    ],
    "contactpose": [
        ("participants", "participants", "participants"),
        ("objects", "objects", "objects"),
    ],
    "cropharvest": [
        ("geographical_tiles", "geographical tiles", "tiles"),
        ("countries", "countries", "countries"),
    ],
    "plantdoc": [
        ("bounding_boxes", "bounding boxes", "bounding_boxes"),
        ("classes", "classes", "classes"),
    ],
    "plantvillage": [
        ("classes", "classes", "classes"),
        ("crop_species", "crop species", "species"),
    ],
    "eurosat": [
        ("classes", "classes", "classes"),
        ("samples_per_class", "samples per class", "patches"),
    ],
    "deepweeds": [
        ("weed_classes", "weed classes", "classes"),
        ("negative_flora", "negative flora classes", "classes"),
    ],
    "hmdb51": [
        ("action_classes", "action classes", "classes"),
        ("minimum_per_class", "minimum clips per class", "videos"),
    ],
    "ucf101": [
        ("action_classes", "action classes", "classes"),
        ("video_groups", "video groups", "groups"),
    ],
    "ntu-rgbd": [
        ("action_classes", "action classes", "classes"),
        ("subjects", "subjects", "subjects"),
        ("camera_views", "camera views", "views"),
    ],
    "dex-ycb": [
        ("sequences", "sequences", "sequences"),
        ("subjects", "subjects", "subjects"),
        ("objects", "objects", "objects"),
        ("camera_views", "camera views", "views"),
    ],
    "graspnet-1billion": [
        ("scenes", "scenes", "scenes"),
        ("grasp_annotations", "grasp annotations", "annotations"),
        ("objects", "objects", "objects"),
    ],
    "homes-of-new-york-dobb-e": [
        ("homes", "homes", "homes"),
        ("environments", "environments", "environments"),
        ("rgbd_frames", "RGB-D frames", "frames"),
    ],
    "robocasa-365": [
        ("human_demonstrations_hours", "human demonstrations duration", "hours"),
        ("automated_demonstrations_hours", "automated demonstrations duration", "hours"),
        ("tasks", "tasks", "tasks"),
        ("kitchen_scenes", "kitchen scenes", "scenes"),
    ],
    "robomind": [
        ("tasks", "tasks", "tasks"),
        ("object_classes", "object classes", "classes"),
        ("embodiments", "robot embodiments", "embodiments"),
    ],
    "behavior-1k-2026-demos": [
        ("tasks", "tasks", "tasks"),
    ],
    "mimicgen": [
        ("tasks", "tasks", "tasks"),
    ],
    "st-petersburg-incart-arrhythmia": [
        ("recordings", "recordings", "recordings"),
        ("patients", "patients", "patients"),
    ],
    "oasis-3": [
        ("mr_sessions", "MR sessions", "sessions"),
        ("pet_sessions", "PET sessions", "sessions"),
    ],
    "iam-handwriting": [
        ("pages", "scanned pages", "pages"),
        ("sentences", "sentences", "sentences"),
        ("lines", "text lines", "lines"),
        ("words", "words", "words"),
        ("writers", "writers", "writers"),
    ],
    "lfw": [
        ("unique_people", "unique individuals", "people"),
        ("people_with_2plus_images", "individuals with 2+ images", "people"),
    ],
    "mimic-iii": [
        ("admissions", "hospital admissions", "admissions"),
        ("patients", "unique patients", "patients"),
    ],
    "mimic-iv-ecg": [
        ("recordings", "ECG recordings", "recordings"),
        ("patients", "unique patients", "patients"),
    ],
    "mimic-iv-ed": [
        ("stays", "emergency department stays", "stays"),
        ("patients", "unique patients", "patients"),
    ],
    "aflw": [
        ("total_faces", "annotated faces", "faces"),
        ("images", "source images", "images"),
    ],
    "a2d2-audi-autonomous-driving": [
        ("semantic_segmentation", "semantic segmentation frames", "frames"),
        ("3d_bounding_boxes", "3D bounding box frames", "frames"),
    ],
    "apolloscape": [
        ("annotated_video_frames", "annotated video frames", "frames"),
    ],
    "milk10k": [
        ("lesions", "annotated lesions", "lesions"),
        ("images", "source images", "images"),
    ],
}

# Redundant duplicate total in splits
REDUNDANT_TOTAL_DATASETS = {
    "california-housing": "total",
    "iris": "total",
}

# Explicit, documented migrations for mixed partition/metric datasets
# Map dataset_id -> list of (split_key_to_extract, breakdown_label, breakdown_unit)
SAFE_MIXED_METRIC_MIGRATIONS: dict[str, list[tuple[str, str, str]]] = {
    "docvqa": [
        ("documents", "source documents", "documents"),
    ],
    "total-text": [
        ("text_instances", "annotated text instances", "instances"),
    ],
    "khatt": [
        ("writers", "contributing writers", "writers"),
    ],
    "inaturalist-2021": [
        ("species", "taxonomic species", "species"),
    ],
    "waymo-open-perception": [
        ("expanded_total", "expanded total segments", "segments"),
    ],
    "xfund": [
        ("chinese", "Chinese form count", "forms"),
        ("japanese", "Japanese form count", "forms"),
        ("spanish", "Spanish form count", "forms"),
        ("french", "French form count", "forms"),
        ("italian", "Italian form count", "forms"),
        ("german", "German form count", "forms"),
        ("portuguese", "Portuguese form count", "forms"),
    ],
    "mbpp": [
        ("prompt", "few-shot prompt problems", "programming-problems"),
    ],
    "cityscapes": [
        ("coarse", "coarsely annotated images", "images"),
    ],
    "infographicvqa": [
        ("train_images", "train images", "images"),
        ("val_images", "validation images", "images"),
        ("test_images", "test images", "images"),
        ("total_images", "total images", "images"),
    ],
    "dude": [
        ("train_documents", "train documents", "documents"),
        ("val_documents", "validation documents", "documents"),
        ("test_documents", "test documents", "documents"),
        ("total_documents", "total documents", "documents"),
    ],
    "mp-docvqa": [
        ("train_documents", "train documents", "documents"),
        ("val_documents", "validation documents", "documents"),
        ("test_documents", "test documents", "documents"),
        ("total_documents", "total documents", "documents"),
        ("total_pages", "total document pages", "pages"),
    ],
    "betel-leaf-bangladesh": [
        ("original", "original unaugmented images", "images"),
    ],
}

KNOWN_SPECIAL_SEMANTIC_REVIEWS: dict[str, str] = {
    "ava-action": "Unit mismatch: declared total is 1.62M action labels, while splits represent 430 movie clips",
    "pubmed-200k-rct": "Unit/version mismatch: declared total is abstracts (195,654) while splits record sentences (237,690) from 20k subset",
    "isic-2018": "Multi-task benchmark: splits represent task1, task2, and task3 subsets with overlapping sample images",
    "btad-beantech-anomaly-detection": "Multi-subset benchmark: splits include both aggregate train/test and per-product subsets train_01..03, test_01..03",
    "unsw-nb15": "Benchmark subset partition: splits represent official partitioned subset (257,673 flows) of raw archive (2,540,044 flows)",
    "ms-coco": "Benchmark subset partition: splits represent 2017 detection train/val/test subset (163,957 images) of 330k raw archive",
    "hotpotqa": "Multi-evaluation benchmark: splits include both dev_distractor and dev_fullwiki evaluation settings",
}


def is_partition_key(key: str) -> bool:
    """Return True if split key represents a standard dataset partition."""
    k_low = key.lower().strip()
    return any(p in k_low for p in STANDARD_PARTITION_KEYWORDS)


def classify_dataset_splits(dataset: dict[str, Any]) -> dict[str, Any]:
    """Audit and classify the dataset's sample_count and splits structure."""
    did = dataset.get("id", "unknown")
    sc = dataset.get("sample_count")

    if not sc or not isinstance(sc, dict):
        return {
            "id": did,
            "status": "NO_SAMPLE_COUNT",
            "has_splits": False,
            "classification": "no_sample_count",
            "action": "NO_OP",
            "reason": "Dataset has no sample_count field",
        }

    splits = sc.get("splits")
    if not splits or not isinstance(splits, dict):
        if did in SAFE_PURE_METRIC_MIGRATIONS:
            return {
                "id": did,
                "status": "APPLIED_PURE_METRIC",
                "has_splits": False,
                "classification": "pure_metric_in_splits",
                "action": "ALREADY_MIGRATED",
                "reason": "Splits represent physical/sensor metrics or entity counts; migrated to breakdown",
            }
        if did in REDUNDANT_TOTAL_DATASETS:
            return {
                "id": did,
                "status": "APPLIED_REDUNDANT_TOTAL",
                "has_splits": False,
                "classification": "redundant_total",
                "action": "ALREADY_MIGRATED",
                "reason": "Split key 'total' redundantly duplicates sample_count.total; removed from splits",
            }
        return {
            "id": did,
            "status": "NO_SPLITS",
            "has_splits": False,
            "classification": "no_splits",
            "action": "NO_OP",
            "reason": "Dataset has no splits dictionary",
        }

    keys = list(splits.keys())
    partition_keys = [k for k in keys if is_partition_key(k)]
    non_partition_keys = [k for k in keys if not is_partition_key(k)]

    # Check for redundant total
    if did in REDUNDANT_TOTAL_DATASETS:
        return {
            "id": did,
            "status": "REDUNDANT_TOTAL",
            "has_splits": True,
            "keys": keys,
            "partition_keys": [],
            "non_partition_keys": non_partition_keys,
            "classification": "redundant_total",
            "action": "SAFE_MIGRATE",
            "reason": f"Split key '{keys[0]}' redundantly duplicates sample_count.total",
        }

    # Check for safe pure metric migration
    if did in SAFE_PURE_METRIC_MIGRATIONS:
        return {
            "id": did,
            "status": "PURE_NON_PARTITION_METRIC",
            "has_splits": True,
            "keys": keys,
            "partition_keys": partition_keys,
            "non_partition_keys": non_partition_keys,
            "classification": "pure_metric_in_splits",
            "action": "SAFE_MIGRATE",
            "reason": "Splits represent physical/sensor metrics or entity counts; migrated to breakdown",
        }

    # Check for safe mixed migration
    if did in SAFE_MIXED_METRIC_MIGRATIONS:
        metric_keys = {key for key, _, _ in SAFE_MIXED_METRIC_MIGRATIONS[did]}
        has_unmigrated_metric = bool(set(keys) & metric_keys)
        action = "SAFE_MIGRATE" if has_unmigrated_metric else "ALREADY_MIGRATED"
        return {
            "id": did,
            "status": "MIXED_PARTITIONS_AND_METRICS",
            "has_splits": True,
            "keys": keys,
            "partition_keys": partition_keys,
            "non_partition_keys": non_partition_keys,
            "classification": "mixed_partitions_and_metrics",
            "action": action,
            "reason": "Separated non-partition metrics to breakdown while preserving true partitions in splits",
        }

    # Check for known special partition semantic reviews (unit mismatch, multi-task, benchmark subset)
    if did in KNOWN_SPECIAL_SEMANTIC_REVIEWS:
        return {
            "id": did,
            "status": "NEEDS_MANUAL_REVIEW",
            "has_splits": True,
            "keys": keys,
            "partition_keys": partition_keys,
            "non_partition_keys": non_partition_keys,
            "classification": "needs_manual_review",
            "action": "NEEDS_MANUAL_REVIEW",
            "reason": KNOWN_SPECIAL_SEMANTIC_REVIEWS[did],
        }

    # Check if pure standard partitions
    if not non_partition_keys:
        return {
            "id": did,
            "status": "STANDARD_PARTITIONS",
            "has_splits": True,
            "keys": keys,
            "partition_keys": partition_keys,
            "non_partition_keys": [],
            "classification": "standard_partitions",
            "action": "NO_OP",
            "reason": "All split keys represent standard dataset partitions (train/val/test)",
        }

    # Needs manual review
    # Class distribution, sub-benchmarks, or unit mismatch (e.g. ava-action)
    review_reason = "Uncertain split semantics or class/subset distribution; requires primary source confirmation"
    if did == "ava-action":
        review_reason = "Unit mismatch: declared total is 1.62M action labels, while splits represent 430 movie clips"
    elif any(k in ("normal", "attack", "benign", "malignant", "positive", "negative", "ckd", "not_ckd") for k in keys):
        review_reason = "Splits represent class label frequencies rather than train/test partitions"

    return {
        "id": did,
        "status": "NEEDS_MANUAL_REVIEW",
        "has_splits": True,
        "keys": keys,
        "partition_keys": partition_keys,
        "non_partition_keys": non_partition_keys,
        "classification": "needs_manual_review",
        "action": "NEEDS_MANUAL_REVIEW",
        "reason": review_reason,
    }


def migrate_dataset_record(dataset: dict[str, Any]) -> tuple[dict[str, Any], bool, str]:
    """Apply safe migration to a dataset record if classified for SAFE_MIGRATE.

    Returns:
        (updated_dataset, was_modified, diff_summary)
    """
    did = dataset.get("id", "unknown")
    classification = classify_dataset_splits(dataset)

    if classification["action"] != "SAFE_MIGRATE":
        return dataset, False, f"[{did}] No changes (Status: {classification['status']})"

    updated = copy.deepcopy(dataset)
    sc = updated.get("sample_count", {})
    splits = sc.get("splits", {})

    diff_lines = [f"=== Migrating dataset: {did} ==="]

    # Case 1: Redundant total in splits
    if did in REDUNDANT_TOTAL_DATASETS:
        del sc["splits"]
        diff_lines.append(f"  - Removed redundant splits dictionary: {splits}")
        return updated, True, "\n".join(diff_lines)

    # Case 2: Pure non-partition metrics
    if did in SAFE_PURE_METRIC_MIGRATIONS:
        metric_specs = SAFE_PURE_METRIC_MIGRATIONS[did]
        migrated_keys = {key for key, _, _ in metric_specs}
        unhandled_keys = set(splits.keys()) - migrated_keys
        if unhandled_keys:
            raise ValueError(
                f"[{did}] Cannot safely migrate pure metrics: unrecognized split keys would be discarded: {unhandled_keys}"
            )

        breakdown_items = []
        for key, label, unit in metric_specs:
            if key in splits:
                val = splits[key]
                item = {"label": label, "value": val}
                if unit:
                    item["unit"] = unit
                breakdown_items.append(item)
                diff_lines.append(f"  + Added breakdown: '{label}' = {val} ({unit})")

        # Preserve any existing breakdown items without overwriting
        existing_breakdown = list(updated.get("breakdown", []))
        existing_labels = {b.get("label") for b in existing_breakdown if isinstance(b, dict)}
        for item in breakdown_items:
            if item["label"] not in existing_labels:
                existing_breakdown.append(item)
                existing_labels.add(item["label"])

        updated["breakdown"] = existing_breakdown
        diff_lines.append(f"  - Removed non-partition splits: {splits}")
        del sc["splits"]
        return updated, True, "\n".join(diff_lines)

    # Case 3: Mixed partitions and metrics
    if did in SAFE_MIXED_METRIC_MIGRATIONS:
        metric_specs = SAFE_MIXED_METRIC_MIGRATIONS[did]
        existing_breakdown = list(updated.get("breakdown", []))
        existing_labels = {b.get("label") for b in existing_breakdown if isinstance(b, dict)}
        keys_to_remove = []

        for key, label, unit in metric_specs:
            if key in splits:
                val = splits[key]
                item = {"label": label, "value": val}
                if unit:
                    item["unit"] = unit
                if label not in existing_labels:
                    existing_breakdown.append(item)
                    existing_labels.add(label)
                keys_to_remove.append(key)
                diff_lines.append(f"  + Moved '{key}' to breakdown: '{label}' = {val} ({unit})")

        for k in keys_to_remove:
            del splits[k]

        updated["breakdown"] = existing_breakdown
        diff_lines.append(f"  ✓ Retained clean partition splits: {splits}")
        return updated, True, "\n".join(diff_lines)

    return dataset, False, f"[{did}] Unhandled SAFE_MIGRATE case"


def run_migration_audit(
    datasets_dir: Path,
    dry_run: bool = True,
    report_json_path: Path | None = None,
    report_md_path: Path | None = None,
    verbose: bool = False,
) -> dict[str, Any]:
    """Execute catalog audit, optionally apply safe migrations, and produce reports."""
    files = sorted(datasets_dir.glob("*.json"))
    scanned_count = len(files)

    audit_records = []
    safely_migrated = []
    needs_manual_review = []
    standard_partitions = []
    no_splits = []
    diff_summaries = []

    for file_path in files:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        classification = classify_dataset_splits(data)
        audit_records.append(classification)

        action = classification["action"]
        did = classification["id"]

        if action in ("SAFE_MIGRATE", "ALREADY_MIGRATED"):
            if action == "SAFE_MIGRATE":
                migrated_data, modified, diff_text = migrate_dataset_record(data)
                diff_msg = diff_text
            else:
                modified = False
                diff_msg = f"=== Dataset: {did} (Already safely migrated) ==="

            safely_migrated.append({
                "id": did,
                "file": file_path.name,
                "classification": classification["classification"],
                "reason": classification["reason"],
                "diff": diff_msg,
            })
            diff_summaries.append(diff_msg)

            if not dry_run and modified:
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(migrated_data, f, indent=2, ensure_ascii=False)
                    f.write("\n")

        elif action == "NEEDS_MANUAL_REVIEW":
            needs_manual_review.append({
                "id": did,
                "file": file_path.name,
                "keys": classification.get("keys", []),
                "reason": classification["reason"],
            })
        elif classification["status"] == "STANDARD_PARTITIONS":
            standard_partitions.append(did)
        else:
            no_splits.append(did)

    nonstandard_split_count = len(safely_migrated) + len(needs_manual_review)

    # Compute current post-migration reconciliation metrics
    # 42 pure metrics + 2 redundant totals = 44 had splits removed.
    # 12 mixed datasets retained clean partition splits.
    # 64 manual review candidates retained existing splits.
    post_clean_partitions_count = len(standard_partitions) + len(SAFE_MIXED_METRIC_MIGRATIONS)
    post_unresolved_reviews_count = len(needs_manual_review)
    post_datasets_with_splits = post_clean_partitions_count + post_unresolved_reviews_count
    post_datasets_with_breakdown = len(SAFE_PURE_METRIC_MIGRATIONS) + len(SAFE_MIXED_METRIC_MIGRATIONS)
    post_datasets_without_splits = scanned_count - post_datasets_with_splits

    summary_data = {
        "audit_metadata": {
            "task": "Phase 1A — Sample Count Split & Breakdown Migration",
            "dry_run": dry_run,
            "total_datasets_scanned": scanned_count,
            "pre_migration_baseline": {
                "total_with_splits": len(standard_partitions) + nonstandard_split_count,
                "standard_partitions_count": len(standard_partitions),
                "nonstandard_split_count": nonstandard_split_count,
                "safely_migrated_count": len(safely_migrated),
                "needs_manual_review_count": len(needs_manual_review),
                "no_splits_count": len(no_splits),
            },
            "post_migration_state": {
                "total_datasets": scanned_count,
                "datasets_with_splits": post_datasets_with_splits,
                "clean_standard_partitions": post_clean_partitions_count,
                "remaining_manual_review_cases": post_unresolved_reviews_count,
                "datasets_without_splits": post_datasets_without_splits,
                "datasets_with_structured_breakdown": post_datasets_with_breakdown,
            },
            "total_with_splits": len(standard_partitions) + nonstandard_split_count,
            "standard_partitions_count": len(standard_partitions),
            "nonstandard_split_count": nonstandard_split_count,
            "safely_migrated_count": len(safely_migrated),
            "needs_manual_review_count": len(needs_manual_review),
            "no_splits_count": len(no_splits),
        },
        "safely_migrated": safely_migrated,
        "needs_manual_review": needs_manual_review,
        "standard_partitions": standard_partitions,
    }

    # Write JSON report
    if report_json_path:
        report_json_path.parent.mkdir(parents=True, exist_ok=True)
        with open(report_json_path, "w", encoding="utf-8") as f:
            json.dump(summary_data, f, indent=2)

    # Write Markdown summary report
    if report_md_path:
        report_md_path.parent.mkdir(parents=True, exist_ok=True)
        md_content = generate_markdown_report(summary_data)
        with open(report_md_path, "w", encoding="utf-8") as f:
            f.write(md_content)

    return summary_data


def generate_markdown_report(summary: dict[str, Any]) -> str:
    """Generate professional GitHub-flavored Markdown report."""
    meta = summary["audit_metadata"]
    migrated = summary["safely_migrated"]
    reviews = summary["needs_manual_review"]

    lines = [
        "# OpenDatasets Sample Count Split and Breakdown Audit (Phase 1A)",
        "",
        f"> **Audit Task:** {meta['task']}  ",
        f"> **Total Records Scanned:** {meta['total_datasets_scanned']} datasets  ",
        f"> **Datasets with Splits:** {meta['total_with_splits']} datasets  ",
        f"> **Execution Mode:** {'DRY-RUN (Simulated)' if meta['dry_run'] else 'APPLIED (Committed)'}  ",
        "",
        "---",
        "",
        "## 1. Executive Summary & Inventory",
        "",
        "| Audit Metric | Count | Proportion |",
        "| :--- | :--- | :--- |",
        f"| **Total Datasets Scanned** | **{meta['total_datasets_scanned']}** | 100.0% |",
        f"| **Datasets with Partition Splits** | **{meta['total_with_splits']}** | {meta['total_with_splits'] / meta['total_datasets_scanned'] * 100:.1f}% |",
        f"| **Standard Pure Partitions (train/val/test)** | **{meta['standard_partitions_count']}** | {meta['standard_partitions_count'] / meta['total_datasets_scanned'] * 100:.1f}% |",
        f"| **Datasets with Nonstandard Split Keys** | **{meta['nonstandard_split_count']}** | {meta['nonstandard_split_count'] / meta['total_datasets_scanned'] * 100:.1f}% |",
        f"| • **Safely Migrated to Structured Breakdown** | **{meta['safely_migrated_count']}** | {meta['safely_migrated_count'] / meta['total_datasets_scanned'] * 100:.1f}% |",
        f"| • **Requiring Maintainer Manual Review** | **{meta['needs_manual_review_count']}** | {meta['needs_manual_review_count'] / meta['total_datasets_scanned'] * 100:.1f}% |",
        f"| **Datasets without Splits (Continuous / Benchmark Suites)** | **{meta['no_splits_count']}** | {meta['no_splits_count'] / meta['total_datasets_scanned'] * 100:.1f}% |",
        "",
        "---",
        "",
        f"## 2. Safely Migrated Datasets ({meta['safely_migrated_count']} records)",
        "",
        "The following datasets contained non-partition physical measurements, secondary entity counts, or redundant totals erroneously stored inside `sample_count.splits`. These were cleanly separated into `breakdown` items preserving all numerical facts without fabrication:",
        "",
        "| Dataset ID | Classification | Action Taken |",
        "| :--- | :--- | :--- |",
    ]

    for item in migrated:
        lines.append(f"| `{item['id']}` | `{item['classification']}` | {item['reason']} |")

    lines.extend([
        "",
        "---",
        "",
        f"## 3. Candidates Requiring Manual Review ({meta['needs_manual_review_count']} records)",
        "",
        "In accordance with Phase 1A guidelines, fields whose partition semantics cannot be unambiguously proven from existing metadata were left unchanged to prevent unverified assumptions:",
        "",
        "| Dataset ID | Existing Split Keys | Scientific Review Reason |",
        "| :--- | :--- | :--- |",
    ])

    for item in reviews:
        keys_str = ", ".join(f"`{k}`" for k in item["keys"])
        lines.append(f"| `{item['id']}` | {keys_str} | {item['reason']} |")

    post = meta.get("post_migration_state", {})
    if post:
        lines.extend([
            "",
            "---",
            "",
            "## 4. Current Post-Migration State & Reconciliation",
            "",
            "The following census distinguishes historical pre-migration findings from the current active catalog state after safe migration:",
            "",
            "| Catalog Dimension | Pre-Migration Baseline | Changes Applied | Current Post-Migration State |",
            "| :--- | :--- | :--- | :--- |",
            f"| **Total Datasets Scanned** | {meta['total_datasets_scanned']} | 0 (no records created/deleted) | **{post['total_datasets']}** |",
            f"| **Datasets with Splits Field** | {meta['total_with_splits']} | -44 (splits removed from pure/redundant) | **{post['datasets_with_splits']}** |",
            f"| • Clean Standard Partitions | {meta['standard_partitions_count']} | +12 (clean partitions retained from mixed) | **{post['clean_standard_partitions']}** |",
            f"| • Remaining Unresolved Cases | {meta['needs_manual_review_count']} | 0 (preserved unchanged for manual review) | **{post['remaining_manual_review_cases']}** |",
            f"| **Datasets without Splits** | {meta['no_splits_count']} | +44 (non-partition/redundant splits removed) | **{post['datasets_without_splits']}** |",
            f"| **Datasets with Structured Breakdown** | 0 | +54 (migrated to structured breakdown) | **{post['datasets_with_structured_breakdown']}** |",
        ])

    lines.extend([
        "",
        "---",
        "",
        "*Report generated automatically by `scripts/migrate_sample_count_breakdowns.py`.*",
    ])

    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for migration runner."""
    parser = argparse.ArgumentParser(
        description="Audit and migrate sample_count splits to structured breakdowns."
    )
    parser.add_argument(
        "--datasets-dir",
        type=Path,
        default=DEFAULT_DATASETS_DIR,
        help=f"Path to dataset JSON files (default: {DEFAULT_DATASETS_DIR})",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply changes to disk. (Default is dry-run mode)",
    )
    parser.add_argument(
        "--report-json",
        type=Path,
        default=DEFAULT_REPORT_JSON,
        help=f"Path to output inventory JSON (default: {DEFAULT_REPORT_JSON})",
    )
    parser.add_argument(
        "--report-md",
        type=Path,
        default=DEFAULT_REPORT_MD,
        help=f"Path to output summary Markdown (default: {DEFAULT_REPORT_MD})",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print per-dataset diffs to stdout.",
    )

    args = parser.parse_args(argv)
    dry_run = not args.apply

    print("=======================================================")
    print(" OpenDatasets Sample Count Split & Breakdown Migration")
    print("=======================================================")
    print(f" Datasets Directory: {args.datasets_dir}")
    print(f" Execution Mode:     {'DRY-RUN (Simulated)' if dry_run else 'APPLY (Writing to disk)'}")
    print("=======================================================")

    summary = run_migration_audit(
        datasets_dir=args.datasets_dir,
        dry_run=dry_run,
        report_json_path=args.report_json,
        report_md_path=args.report_md,
        verbose=args.verbose,
    )

    meta = summary["audit_metadata"]
    print(" Audit Results:")
    print(f"   • Total datasets scanned:     {meta['total_datasets_scanned']}")
    print(f"   • Standard pure partitions:   {meta['standard_partitions_count']}")
    print(f"   • Nonstandard split keys:     {meta['nonstandard_split_count']}")
    print(f"     - Safely migrated:          {meta['safely_migrated_count']}")
    print(f"     - Requiring manual review:  {meta['needs_manual_review_count']}")
    print(f"   • No splits:                  {meta['no_splits_count']}")
    print("-------------------------------------------------------")
    print(f" [OK] Wrote JSON inventory to {args.report_json}")
    print(f" [OK] Wrote Markdown summary to {args.report_md}")
    print("=======================================================")

    if args.verbose:
        for item in summary["safely_migrated"]:
            print(item["diff"])
            print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
