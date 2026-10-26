"""Automated tests for OpenDatasets dataset metadata and validation engine."""

from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import jsonschema
import pytest

from scripts.validate_datasets import (
    DEFAULT_DATA_DIR,
    DEFAULT_SCHEMA_PATH,
    check_duplicate_ids_and_slugs,
    is_valid_http_url,
    load_json_file,
    load_schema,
    main,
    validate_all_datasets,
    validate_dataset_data,
    validate_dataset_file,
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
def sample_dataset() -> dict[str, Any]:
    """Provide a minimal valid dataset dictionary for unit testing."""
    return {
        "schema_version": "1.0.0",
        "id": "sample-dataset",
        "slug": "sample-dataset",
        "name": "Sample Benchmark Dataset",
        "description": "A well-structured sample dataset created for automated testing purposes.",
        "homepage_url": "https://opendatasets.org/sample",
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
    }


# ==============================================================================
# 1. Schema Integrity & Catalog Validation
# ==============================================================================


def test_schema_is_valid_draft7(schema_data: dict[str, Any]) -> None:
    """Verify that schemas/dataset.v1.schema.json complies with JSON Schema Draft-7."""
    jsonschema.Draft7Validator.check_schema(schema_data)


def test_all_catalog_datasets_are_valid(
    validator: jsonschema.Draft7Validator,
) -> None:
    """Ensure all dataset files currently stored in data/datasets pass validation."""
    dataset_files = list(DEFAULT_DATA_DIR.glob("*.json"))
    assert len(dataset_files) >= 2, f"Expected at least 2 datasets in {DEFAULT_DATA_DIR}, found {len(dataset_files)}"

    for file_path in dataset_files:
        data, errors = validate_dataset_file(file_path, validator)
        assert not errors, f"Validation errors in {file_path}:\n" + "\n".join(errors)
        assert data is not None


def test_catalog_has_no_duplicate_ids_or_slugs() -> None:
    """Ensure the repository contains no duplicate dataset IDs or slugs."""
    total, passed, errors = validate_all_datasets(
        data_dir=DEFAULT_DATA_DIR,
        schema_path=DEFAULT_SCHEMA_PATH,
    )
    assert total >= 2
    assert total == passed
    assert not errors


# ==============================================================================
# 2. Missing Required Fields
# ==============================================================================


@pytest.mark.parametrize(
    "missing_field",
    [
        "schema_version",
        "id",
        "slug",
        "name",
        "description",
        "homepage_url",
        "publisher",
        "modalities",
        "tasks",
        "tags",
        "license",
        "source_references",
        "verification",
    ],
)
def test_validator_detects_missing_required_fields(
    validator: jsonschema.Draft7Validator,
    sample_dataset: dict[str, Any],
    missing_field: str,
) -> None:
    """Ensure omitting any required top-level field produces a validation error."""
    invalid_data = copy.deepcopy(sample_dataset)
    del invalid_data[missing_field]

    errors = validate_dataset_data(invalid_data, validator, filename="test.json")
    assert errors, f"Expected error when '{missing_field}' is missing, but validation passed."
    assert any(missing_field in err and "required" in err.lower() for err in errors)


# ==============================================================================
# 3. URL Syntax Validation
# ==============================================================================


@pytest.mark.parametrize(
    "valid_url",
    [
        "http://yann.lecun.com/exdb/mnist/",
        "https://www.cs.toronto.edu/~kriz/cifar.html",
        "https://archive.ics.uci.edu/dataset/53/iris",
        "https://example.org/path?query=val#frag",
    ],
)
def test_is_valid_http_url_accepts_valid_urls(valid_url: str) -> None:
    """Check that legitimate HTTP/HTTPS URLs pass syntax check."""
    valid, msg = is_valid_http_url(valid_url)
    assert valid is True
    assert msg == ""


@pytest.mark.parametrize(
    "invalid_url",
    [
        "ftp://example.com/file.zip",
        "file:///local/path",
        "not_a_url",
        "http://",
        "https://",
        "https:// example.com",
        "https://example.com/has space/data",
        "",
        "   ",
        12345,
        None,
    ],
)
def test_is_valid_http_url_rejects_invalid_urls(invalid_url: Any) -> None:
    """Check that non-HTTP, malformed, or blank URLs are rejected."""
    valid, msg = is_valid_http_url(invalid_url)
    assert valid is False
    assert len(msg) > 0


def test_validator_flags_invalid_homepage_url(
    validator: jsonschema.Draft7Validator,
    sample_dataset: dict[str, Any],
) -> None:
    """Ensure invalid homepage_url is caught by the validator."""
    data = copy.deepcopy(sample_dataset)
    data["homepage_url"] = "ftp://ftp.example.org/dataset"
    errors = validate_dataset_data(data, validator, filename="test.json")
    assert any("homepage_url" in err for err in errors)


def test_validator_flags_invalid_nested_reference_url(
    validator: jsonschema.Draft7Validator,
    sample_dataset: dict[str, Any],
) -> None:
    """Ensure invalid URLs in source_references are caught by the validator."""
    data = copy.deepcopy(sample_dataset)
    data["source_references"][0]["url"] = "http://"
    errors = validate_dataset_data(data, validator, filename="test.json")
    assert any("source_references" in err for err in errors)


# ==============================================================================
# 4. Modalities and Allowed Enum Values
# ==============================================================================


def test_validator_flags_invalid_modality(
    validator: jsonschema.Draft7Validator,
    sample_dataset: dict[str, Any],
) -> None:
    """Ensure unsupported modality strings fail enum validation."""
    data = copy.deepcopy(sample_dataset)
    data["modalities"] = ["quantum-neural-telepathy"]
    errors = validate_dataset_data(data, validator, filename="test.json")
    assert any("modalities" in err and "is not one of" in err for err in errors)


def test_validator_flags_empty_modalities(
    validator: jsonschema.Draft7Validator,
    sample_dataset: dict[str, Any],
) -> None:
    """Ensure empty modalities list fails minItems constraint."""
    data = copy.deepcopy(sample_dataset)
    data["modalities"] = []
    errors = validate_dataset_data(data, validator, filename="test.json")
    assert any("modalities" in err for err in errors)


def test_validator_accepts_explicit_unspecified_license_and_verification(
    validator: jsonschema.Draft7Validator,
    sample_dataset: dict[str, Any],
) -> None:
    """Ensure explicit states for unknown or unverified metadata are accepted."""
    data = copy.deepcopy(sample_dataset)
    data["license"]["status"] = "unspecified_by_source"
    data["license"]["commercial_use"] = "unknown"
    data["verification"]["status"] = "unverified"
    data["verification"]["verified_by"] = None
    data["verification"]["verified_date"] = None

    errors = validate_dataset_data(data, validator, filename="test.json")
    assert not errors, f"Unexpected errors with explicit unknown states: {errors}"


# ==============================================================================
# 5. Duplicate Detection (IDs and Slugs)
# ==============================================================================


def test_check_duplicate_ids(tmp_path: Path) -> None:
    """Ensure check_duplicate_ids_and_slugs detects duplicated IDs across files."""
    file1 = tmp_path / "ds1.json"
    file2 = tmp_path / "ds2.json"
    ds_list = [
        (file1, {"id": "shared-id", "slug": "slug-one"}),
        (file2, {"id": "shared-id", "slug": "slug-two"}),
    ]
    errors = check_duplicate_ids_and_slugs(ds_list)
    assert len(errors) == 1
    assert "Duplicate dataset ID 'shared-id'" in errors[0]
    assert str(file1) in errors[0]
    assert str(file2) in errors[0]


def test_check_duplicate_slugs(tmp_path: Path) -> None:
    """Ensure check_duplicate_ids_and_slugs detects duplicated slugs across files."""
    file1 = tmp_path / "ds1.json"
    file2 = tmp_path / "ds2.json"
    ds_list = [
        (file1, {"id": "id-one", "slug": "shared-slug"}),
        (file2, {"id": "id-two", "slug": "shared-slug"}),
    ]
    errors = check_duplicate_ids_and_slugs(ds_list)
    assert len(errors) == 1
    assert "Duplicate dataset slug 'shared-slug'" in errors[0]
    assert str(file1) in errors[0]
    assert str(file2) in errors[0]


# ==============================================================================
# 6. Malformed JSON
# ==============================================================================


def test_validator_handles_malformed_json(
    tmp_path: Path,
    validator: jsonschema.Draft7Validator,
) -> None:
    """Ensure malformed JSON files produce clean syntax errors instead of crashing."""
    bad_json_file = tmp_path / "broken.json"
    bad_json_file.write_text('{\n  "id": "unclosed",\n', encoding="utf-8")

    data, errors = validate_dataset_file(bad_json_file, validator)
    assert data is None
    assert errors
    assert "Malformed JSON" in errors[0]
    assert str(bad_json_file) in errors[0]


def test_validator_handles_empty_file(
    tmp_path: Path,
    validator: jsonschema.Draft7Validator,
) -> None:
    """Ensure empty files are flagged with a readable error."""
    empty_file = tmp_path / "empty.json"
    empty_file.write_text("", encoding="utf-8")

    data, errors = load_json_file(empty_file)
    assert data is None
    assert errors
    assert "File is empty" in errors[0]


# ==============================================================================
# 7. Validator CLI & Exit Codes
# ==============================================================================


def test_main_cli_success() -> None:
    """Ensure main() returns exit code 0 when catalog is valid."""
    exit_code = main(["--quiet"])
    assert exit_code == 0


def test_main_cli_failure_on_invalid_file(tmp_path: Path) -> None:
    """Ensure main() returns exit code 1 when an invalid file is passed."""
    invalid_file = tmp_path / "invalid.json"
    invalid_file.write_text(json.dumps({"name": "incomplete"}), encoding="utf-8")

    exit_code = main(["--data-dir", str(tmp_path), "--quiet"])
    assert exit_code == 1


def test_cli_subprocess_execution() -> None:
    """Ensure scripts/validate_datasets.py can be invoked directly as a CLI script."""
    result = subprocess.run(
        [sys.executable, "scripts/validate_datasets.py"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, f"Validator CLI failed: {result.stderr}"
    assert "[PASS] OpenDatasets Metadata Validation" in result.stdout
