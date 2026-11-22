"""Automated unit and regression tests for sample count splits and quantitative breakdowns.

Verifies:
1. Complete partitions where sum(splits) == total.
2. Partial partitions (e.g. unreleased test sets or subset benchmarks) pass schema validation.
3. Overlapping or multi-task partitions pass schema validation.
4. Multi-unit partitions (such as ava-action video clips vs action labels).
5. Structured breakdown schema validation (Draft-7 conformance, required fields, optional unit).
6. Datasets with unknown totals (status: unknown without total).
7. Backward compatibility for datasets lacking breakdown blocks.
8. Migration idempotence and classification fidelity.
9. Full catalog validation check across all 725 dataset files.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import jsonschema
import pytest

from scripts.validate_datasets import (
    DEFAULT_DATA_DIR,
    DEFAULT_SCHEMA_PATH,
    load_json_file,
    load_schema,
    validate_dataset_data,
)
from scripts.migrate_sample_count_breakdowns import (
    SAFE_MIXED_METRIC_MIGRATIONS,
    SAFE_PURE_METRIC_MIGRATIONS,
    REDUNDANT_TOTAL_DATASETS,
    KNOWN_SPECIAL_SEMANTIC_REVIEWS,
    classify_dataset_splits,
    is_partition_key,
    migrate_dataset_record,
)


@pytest.fixture(scope="session")
def schema_data() -> dict[str, Any]:
    """Load the canonical dataset JSON schema."""
    data, errors = load_schema(DEFAULT_SCHEMA_PATH)
    assert not errors, f"Failed to load schema: {errors}"
    assert data is not None
    return data


@pytest.fixture(scope="session")
def validator(schema_data: dict[str, Any]) -> jsonschema.Draft7Validator:
    """Instantiate a Draft7Validator with the canonical schema."""
    return jsonschema.Draft7Validator(schema_data)


@pytest.fixture
def minimal_dataset() -> dict[str, Any]:
    """Provide a minimal schema-valid dataset dictionary."""
    return {
        "schema_version": "1.0.0",
        "id": "fixture-dataset",
        "slug": "fixture-dataset",
        "name": "Fixture Benchmark Dataset",
        "description": "A well-structured fixture dataset for testing sample counts and breakdowns.",
        "homepage_url": "https://opendatasets.org/fixture",
        "publisher": {
            "name": "VisionX25 Testing Lab",
            "type": "academic",
            "url": "https://opendatasets.org",
        },
        "modalities": ["vision"],
        "tasks": ["image-classification"],
        "tags": ["benchmark", "sample"],
        "license": {
            "status": "verified_open",
            "name": "MIT License",
            "spdx_id": "MIT",
            "url": "https://opensource.org/licenses/MIT",
            "commercial_use": "allowed",
        },
        "source_references": [
            {
                "title": "Sample Dataset Source",
                "url": "https://opendatasets.org/sample-source",
                "type": "official_website",
            }
        ],
        "verification": {
            "status": "verified",
            "verified_by": "Test Suite",
            "verified_date": "2026-10-26",
            "notes": "Verified in testing fixture.",
        },
        "sample_count": {
            "total": 1000,
            "unit": "images",
            "status": "verified",
        },
    }


def test_complete_partition_validation(minimal_dataset: dict[str, Any], validator: jsonschema.Draft7Validator) -> None:
    """Test that complete partitions summing exactly to total pass validation."""
    data = copy.deepcopy(minimal_dataset)
    data["sample_count"]["splits"] = {
        "train": 800,
        "val": 100,
        "test": 100,
    }
    errors = validate_dataset_data(data, validator)
    assert not errors, f"Unexpected validation errors: {errors}"


def test_partial_partition_validation(minimal_dataset: dict[str, Any], validator: jsonschema.Draft7Validator) -> None:
    """Test that partial partitions (e.g. unreleased test split where sum < total) pass schema validation."""
    data = copy.deepcopy(minimal_dataset)
    data["sample_count"]["total"] = 1000
    data["sample_count"]["splits"] = {
        "train": 700,
        "val": 100,
        # test set is held out by benchmark organizers (200 missing)
    }
    errors = validate_dataset_data(data, validator)
    assert not errors, f"Partial partitions must not fail schema validation: {errors}"


def test_overlapping_multitask_partitions(minimal_dataset: dict[str, Any], validator: jsonschema.Draft7Validator) -> None:
    """Test that multi-task benchmark partitions (where sum of tasks > total images) pass schema validation."""
    data = copy.deepcopy(minimal_dataset)
    data["sample_count"]["total"] = 500
    data["sample_count"]["splits"] = {
        "task1_train": 400,
        "task1_test": 100,
        "task2_train": 350,
        "task2_test": 150,
    }
    errors = validate_dataset_data(data, validator)
    assert not errors, f"Overlapping multi-task splits must not fail schema validation: {errors}"


def test_mixed_units_ava_action_semantics(minimal_dataset: dict[str, Any], validator: jsonschema.Draft7Validator) -> None:
    """Test multi-unit datasets where splits represent movie clips while total represents action labels."""
    data = copy.deepcopy(minimal_dataset)
    data["id"] = "ava-action"
    data["sample_count"]["total"] = 1620000
    data["sample_count"]["unit"] = "labels"
    data["sample_count"]["splits"] = {
        "train_clips": 235,
        "val_clips": 64,
        "test_clips": 131,
    }
    errors = validate_dataset_data(data, validator)
    assert not errors, f"Multi-unit clip/label partitions must validate cleanly: {errors}"


def test_structured_breakdown_schema_validation(minimal_dataset: dict[str, Any], validator: jsonschema.Draft7Validator) -> None:
    """Test valid structured breakdown array conforming to schema."""
    data = copy.deepcopy(minimal_dataset)
    data["breakdown"] = [
        {"label": "driving distance", "value": 350, "unit": "km"},
        {"label": "laser scans", "value": 50000, "unit": "scans"},
        {"label": "driving sequences", "value": 44},  # optional unit omitted
    ]
    errors = validate_dataset_data(data, validator)
    assert not errors, f"Valid breakdown items must pass schema validation: {errors}"


def test_structured_breakdown_schema_rejections(minimal_dataset: dict[str, Any], validator: jsonschema.Draft7Validator) -> None:
    """Test that malformed breakdown items are rejected by schema validator."""
    data = copy.deepcopy(minimal_dataset)

    # Missing required 'value'
    data["breakdown"] = [{"label": "invalid item"}]
    errors = validate_dataset_data(data, validator)
    assert any("value" in err for err in errors), "Schema must require 'value' in breakdown items"

    # Missing required 'label'
    data["breakdown"] = [{"value": 42}]
    errors = validate_dataset_data(data, validator)
    assert any("label" in err for err in errors), "Schema must require 'label' in breakdown items"

    # Non-numeric value
    data["breakdown"] = [{"label": "distance", "value": "350km"}]
    errors = validate_dataset_data(data, validator)
    assert any("value" in err for err in errors), "Schema must require numeric 'value'"

    # Extra disallowed property
    data["breakdown"] = [{"label": "test", "value": 10, "extra_field": "disallowed"}]
    errors = validate_dataset_data(data, validator)
    assert any("extra_field" in err or "additionalProperties" in err for err in errors)


def test_unknown_sample_totals(minimal_dataset: dict[str, Any], validator: jsonschema.Draft7Validator) -> None:
    """Test that datasets with unknown sample totals (status: unknown without total) validate cleanly."""
    data = copy.deepcopy(minimal_dataset)
    data["sample_count"] = {
        "status": "unknown",
    }
    data["breakdown"] = [
        {"label": "demonstration duration", "value": 219, "unit": "hours"}
    ]
    errors = validate_dataset_data(data, validator)
    assert not errors, f"Unknown totals with breakdowns must validate cleanly: {errors}"


def test_backward_compatibility_without_breakdown(minimal_dataset: dict[str, Any], validator: jsonschema.Draft7Validator) -> None:
    """Test that existing datasets without breakdown property remain 100% valid."""
    data = copy.deepcopy(minimal_dataset)
    assert "breakdown" not in data
    errors = validate_dataset_data(data, validator)
    assert not errors, f"Datasets without breakdown must pass validation: {errors}"


def test_migration_classification_fidelity() -> None:
    """Test that classify_dataset_splits accurately categorizes dataset records."""
    # Pure metric
    boreas_mock = {
        "id": "boreas",
        "sample_count": {
            "total": 44,
            "splits": {"driving_sequences": 44, "total_driving_km": 350},
        },
    }
    cls_boreas = classify_dataset_splits(boreas_mock)
    assert cls_boreas["action"] == "SAFE_MIGRATE"
    assert cls_boreas["classification"] == "pure_metric_in_splits"

    # Redundant total
    iris_mock = {
        "id": "iris",
        "sample_count": {
            "total": 150,
            "splits": {"total": 150},
        },
    }
    cls_iris = classify_dataset_splits(iris_mock)
    assert cls_iris["action"] == "SAFE_MIGRATE"
    assert cls_iris["classification"] == "redundant_total"

    # Mixed partitions and metrics
    docvqa_mock = {
        "id": "docvqa",
        "sample_count": {
            "total": 50000,
            "splits": {
                "train_questions": 39463,
                "val_questions": 5349,
                "test_questions": 5188,
                "documents": 12707,
            },
        },
    }
    cls_docvqa = classify_dataset_splits(docvqa_mock)
    assert cls_docvqa["action"] == "SAFE_MIGRATE"
    assert cls_docvqa["classification"] == "mixed_partitions_and_metrics"

    # Manual review candidate (class distributions)
    wine_mock = {
        "id": "wine-quality",
        "sample_count": {
            "total": 6497,
            "splits": {"red": 1599, "white": 4898},
        },
    }
    cls_wine = classify_dataset_splits(wine_mock)
    assert cls_wine["action"] == "NEEDS_MANUAL_REVIEW"
    assert cls_wine["classification"] == "needs_manual_review"

    # Manual review candidate (unit mismatch)
    ava_mock = {
        "id": "ava-action",
        "sample_count": {
            "total": 1620000,
            "unit": "labels",
            "splits": {"train_clips": 235, "val_clips": 64, "test_clips": 131},
        },
    }
    cls_ava = classify_dataset_splits(ava_mock)
    assert cls_ava["action"] == "NEEDS_MANUAL_REVIEW"
    assert "Unit mismatch" in cls_ava["reason"]


def test_migration_idempotence() -> None:
    """Test that migrating an already migrated record produces zero modifications."""
    migrated_boreas = {
        "schema_version": "1.0.0",
        "id": "boreas",
        "slug": "boreas",
        "name": "Boreas",
        "description": "Autonomous driving dataset.",
        "homepage_url": "https://boreas.org",
        "publisher": {"name": "UTIAS", "type": "academic"},
        "modalities": ["sensor"],
        "tasks": ["odometry"],
        "tags": ["driving", "lidar"],
        "license": {"status": "verified_open", "name": "CC-BY-4.0"},
        "source_references": [{"title": "Source", "url": "https://boreas.org", "type": "official_website"}],
        "verification": {"status": "verified", "verified_by": "Test", "verified_date": "2026-01-01"},
        "sample_count": {
            "total": 44,
            "unit": "sequences",
            "status": "verified",
        },
        "breakdown": [
            {"label": "driving sequences", "value": 44, "unit": "sequences"},
            {"label": "total driving distance", "value": 350, "unit": "km"},
        ],
    }
    updated, was_modified, _ = migrate_dataset_record(migrated_boreas)
    assert not was_modified
    assert updated == migrated_boreas


def test_all_catalog_datasets_valid(validator: jsonschema.Draft7Validator) -> None:
    """Test that every dataset in data/datasets/ conforms 100% to schema."""
    dataset_files = sorted(DEFAULT_DATA_DIR.glob("*.json"))
    assert len(dataset_files) == 725, f"Expected 725 datasets, found {len(dataset_files)}"

    failures = []
    for f in dataset_files:
        data, load_errs = load_json_file(f)
        if load_errs or data is None:
            failures.append(f"{f.name}: load errors {load_errs}")
            continue
        errs = validate_dataset_data(data, validator, filename=f.name)
        if errs:
            failures.append(f"{f.name}: {errs}")

    assert not failures, f"Catalog validation failures:\n" + "\n".join(failures[:10])
