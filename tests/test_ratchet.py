"""Automated test suite for Quality Ratchet Architecture & Monotonic Enforcement.

Covers the 9 required ratchet simulation scenarios:
- Scenario A: Unchanged legacy catalog (passes ratchet with grandfathered violations)
- Scenario B: New valid dataset (passes cleanly)
- Scenario C: New dataset with rule violation (fails ratchet, grandfathering denied)
- Scenario D: Modified legacy dataset introducing or retaining violation (fails ratchet)
- Scenario E: Modified legacy dataset resolving violation (passes, prunes baseline)
- Scenario F: Baseline expansion rejection (prohibited from adding new fingerprints)
- Scenario G: Exception substitution rejection (cannot replace violation A with B)
- Scenario H: Structural failure rejection (fatal schema/duplicate/JSON errors block)
- Scenario I: Missing or malformed baseline handling (safe diagnostics)
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest
import jsonschema

from scripts.validate_datasets import (
    DEFAULT_BASELINE_PATH,
    DEFAULT_DATA_DIR,
    DEFAULT_SCHEMA_PATH,
    SEVERITY_FATAL_ERROR,
    SEVERITY_RATCHETABLE_WARNING,
    evaluate_ratchet,
    generate_baseline_data,
    load_baseline_file,
    load_schema,
    main,
    validate_all_datasets,
    write_baseline_file,
)


@pytest.fixture
def schema_validator() -> jsonschema.Draft7Validator:
    schema_data, errors = load_schema(DEFAULT_SCHEMA_PATH)
    assert not errors
    assert schema_data is not None
    return jsonschema.Draft7Validator(schema_data)


@pytest.fixture
def valid_dataset_dict() -> dict[str, Any]:
    return {
        "schema_version": "1.0.0",
        "id": "scenario-test-dataset",
        "slug": "scenario-test-dataset",
        "name": "Scenario Test Dataset",
        "description": "Standardized test dataset for quality ratchet simulation scenarios.",
        "homepage_url": "https://example.org/scenario-test-dataset",
        "publisher": {
            "name": "Quality Assurance Lab",
            "type": "academic",
            "url": "https://example.org",
        },
        "modalities": ["vision"],
        "tasks": ["image-classification"],
        "tags": ["benchmark", "test"],
        "license": {
            "name": "MIT License",
            "spdx_id": "MIT",
            "status": "verified_open",
            "commercial_use": "allowed",
            "url": "https://opensource.org/licenses/MIT",
        },
        "sample_count": {
            "total": 500,
            "unit": "images",
            "status": "verified",
            "splits": {"train": 400, "test": 100},
            "partition_completeness": "complete",
            "partition_overlap": "disjoint",
        },
        "dates": {
            "published": "2024-03-01",
            "last_updated": "2024-03-15",
        },
        "verification": {
            "status": "verified",
            "verified_by": "Curator",
            "verified_date": "2024-03-15",
        },
        "source_references": [
            {
                "title": "Documentation",
                "type": "documentation",
                "url": "https://example.org/docs",
            }
        ],
    }


# ==============================================================================
# Scenario A: Unchanged Legacy Catalog
# ==============================================================================


def test_scenario_a_unchanged_legacy_catalog_passes_ratchet() -> None:
    """Scenario A: Running --ratchet on authoritative catalog passes with grandfathered exceptions."""
    assert DEFAULT_BASELINE_PATH.exists()
    exit_code = main(["--ratchet", "--quiet"])
    assert exit_code == 0

    total, passed, findings, metrics = validate_all_datasets(
        data_dir=DEFAULT_DATA_DIR,
        schema_path=DEFAULT_SCHEMA_PATH,
        baseline_path=DEFAULT_BASELINE_PATH,
        ratchet=True,
        strict=False,
        return_findings=True,
    )
    assert total == 875
    assert passed == 875
    assert metrics["fatal_errors"] == 0
    assert metrics["blocking_findings"] == 0
    assert metrics["grandfathered_violations"] == 164
    assert metrics["new_violations"] == 0


# ==============================================================================
# Scenario B: New Valid Dataset
# ==============================================================================


def test_scenario_b_new_valid_dataset_passes_ratchet(tmp_path: Path, valid_dataset_dict: dict[str, Any]) -> None:
    """Scenario B: Adding a new compliant dataset file passes validation cleanly."""
    data_dir = tmp_path / "datasets"
    data_dir.mkdir()
    new_file = data_dir / "scenario-test-dataset.json"
    new_file.write_text(json.dumps(valid_dataset_dict, indent=2) + "\n", encoding="utf-8")

    total, passed, findings, metrics = validate_all_datasets(
        data_dir=data_dir,
        schema_path=DEFAULT_SCHEMA_PATH,
        baseline_path=DEFAULT_BASELINE_PATH,
        ratchet=True,
        strict=False,
        return_findings=True,
    )
    assert total == 1
    assert passed == 1
    assert metrics["blocking_findings"] == 0
    assert metrics["new_violations"] == 0


# ==============================================================================
# Scenario C: New Dataset With Rule Violation
# ==============================================================================


def test_scenario_c_new_dataset_with_violation_fails_ratchet(tmp_path: Path, valid_dataset_dict: dict[str, Any]) -> None:
    """Scenario C: New dataset introducing ratchetable warning fails because grandfathering is denied."""
    data_dir = tmp_path / "datasets"
    data_dir.mkdir()
    new_file = data_dir / "scenario-test-dataset.json"

    # Introduce a ratchetable warning: missing sample_count.unit (SMP-001)
    invalid_data = copy.deepcopy(valid_dataset_dict)
    del invalid_data["sample_count"]["unit"]
    new_file.write_text(json.dumps(invalid_data, indent=2) + "\n", encoding="utf-8")

    total, passed, findings, metrics = validate_all_datasets(
        data_dir=data_dir,
        schema_path=DEFAULT_SCHEMA_PATH,
        baseline_path=DEFAULT_BASELINE_PATH,
        ratchet=True,
        strict=False,
        return_findings=True,
    )
    assert total == 1
    assert passed == 0
    assert metrics["blocking_findings"] == 1
    assert metrics["new_violations"] == 1
    blocking = [f for f in findings if f.blocks_validation]
    assert len(blocking) == 1
    assert blocking[0].rule_id == "SMP-001"


# ==============================================================================
# Scenario D: Modified Legacy Dataset Introducing Violation
# ==============================================================================


def test_scenario_d_modified_legacy_dataset_fails_ratchet(tmp_path: Path, valid_dataset_dict: dict[str, Any]) -> None:
    """Scenario D: Modifying a dataset file denies grandfathering for that file."""
    data_dir = tmp_path / "datasets"
    data_dir.mkdir()

    # Create a baseline containing an exception for this dataset ID
    ds_id = "legacy-dataset"
    valid_dataset_dict["id"] = ds_id
    valid_dataset_dict["slug"] = ds_id
    del valid_dataset_dict["sample_count"]["unit"]  # SMP-001

    dataset_file = data_dir / f"{ds_id}.json"
    dataset_file.write_text(json.dumps(valid_dataset_dict, indent=2) + "\n", encoding="utf-8")

    fp = f"SMP-001:{ds_id}:sample_count.unit"
    base_file = tmp_path / "baseline.json"
    write_baseline_file(
        base_file,
        {
            "schema_version": "1.0",
            "generated_at_commit": "abc1234",
            "total_violations": 1,
            "violations": [{"fingerprint": fp, "rule_id": "SMP-001", "dataset_id": ds_id, "file_path": str(dataset_file), "field_path": "sample_count.unit", "message": "msg"}],
        },
    )

    # When marked as a changed file, grandfathering is denied!
    changed_files = {f"datasets/{ds_id}.json"}
    total, passed, findings, metrics = validate_all_datasets(
        data_dir=data_dir,
        schema_path=DEFAULT_SCHEMA_PATH,
        baseline_path=base_file,
        trusted_base=None,
        ratchet=True,
        strict=False,
        return_findings=True,
    )
    # Without changed_files, grandfathering passes
    assert metrics["blocking_findings"] == 0

    # With changed_files set via evaluate_ratchet, it blocks
    evaluated, eval_metrics = evaluate_ratchet(
        findings=findings,
        baseline_data=load_baseline_file(base_file),
        changed_files={str(dataset_file)},
        ratchet=True,
    )
    assert eval_metrics["blocking_findings"] == 1
    assert eval_metrics["new_violations"] == 1


# ==============================================================================
# Scenario E: Modified Legacy Dataset Resolving Violation
# ==============================================================================


def test_scenario_e_resolved_violation_prunes_baseline(tmp_path: Path, valid_dataset_dict: dict[str, Any]) -> None:
    """Scenario E: Fixing a violation passes validation and --update-baseline successfully prunes it."""
    data_dir = tmp_path / "datasets"
    data_dir.mkdir()

    ds_id = "remediated-dataset"
    valid_dataset_dict["id"] = ds_id
    valid_dataset_dict["slug"] = ds_id
    # Dataset is completely clean (has unit, trailing newline, valid dates)
    dataset_file = data_dir / f"{ds_id}.json"
    dataset_file.write_text(json.dumps(valid_dataset_dict, indent=2) + "\n", encoding="utf-8")

    # Baseline has legacy violation that was now fixed
    fp = f"SMP-001:{ds_id}:sample_count.unit"
    base_file = tmp_path / "baseline.json"
    write_baseline_file(
        base_file,
        {
            "schema_version": "1.0",
            "generated_at_commit": "abc1234",
            "total_violations": 1,
            "violations": [{"fingerprint": fp, "rule_id": "SMP-001", "dataset_id": ds_id, "file_path": str(dataset_file), "field_path": "sample_count.unit", "message": "msg"}],
        },
    )

    # Update baseline: since the violation is resolved, new baseline has 0 violations
    exit_code = main(["--data-dir", str(data_dir), "--baseline", str(base_file), "--update-baseline", "--quiet"])
    assert exit_code == 0

    updated = load_baseline_file(base_file)
    assert updated is not None
    assert updated["total_violations"] == 0
    assert len(updated["violations"]) == 0


# ==============================================================================
# Scenario F: Baseline Expansion Rejection
# ==============================================================================


def test_scenario_f_baseline_expansion_is_strictly_rejected(tmp_path: Path, valid_dataset_dict: dict[str, Any]) -> None:
    """Scenario F: Attempting to add new violations to baseline fails with exit code 1."""
    data_dir = tmp_path / "datasets"
    data_dir.mkdir()

    ds_id = "expanded-dataset"
    valid_dataset_dict["id"] = ds_id
    valid_dataset_dict["slug"] = ds_id
    del valid_dataset_dict["sample_count"]["unit"]  # Violates SMP-001

    dataset_file = data_dir / f"{ds_id}.json"
    dataset_file.write_text(json.dumps(valid_dataset_dict, indent=2) + "\n", encoding="utf-8")

    # Empty baseline
    base_file = tmp_path / "baseline.json"
    write_baseline_file(
        base_file,
        {
            "schema_version": "1.0",
            "generated_at_commit": "abc1234",
            "total_violations": 0,
            "violations": [],
        },
    )

    # Attempting to update baseline must fail!
    exit_code = main(["--data-dir", str(data_dir), "--baseline", str(base_file), "--update-baseline", "--quiet"])
    assert exit_code == 1

    # Baseline remains unchanged at 0 violations
    persisted = load_baseline_file(base_file)
    assert persisted is not None
    assert persisted["total_violations"] == 0


# ==============================================================================
# Scenario G: Exception Substitution Rejection
# ==============================================================================


def test_scenario_g_exception_substitution_is_rejected(tmp_path: Path, valid_dataset_dict: dict[str, Any]) -> None:
    """Scenario G: Fixing violation A while adding violation B is rejected during baseline update."""
    data_dir = tmp_path / "datasets"
    data_dir.mkdir()

    ds_id = "subst-dataset"
    valid_dataset_dict["id"] = ds_id
    valid_dataset_dict["slug"] = ds_id
    # File has unit (fixing A), but is missing trailing newline (introducing B)
    content = json.dumps(valid_dataset_dict, indent=2)  # NO trailing newline -> FMT-001
    dataset_file = data_dir / f"{ds_id}.json"
    dataset_file.write_bytes(content.encode("utf-8"))

    # Baseline had SMP-001 for this dataset, but NOT FMT-001
    fp_a = f"SMP-001:{ds_id}:sample_count.unit"
    base_file = tmp_path / "baseline.json"
    write_baseline_file(
        base_file,
        {
            "schema_version": "1.0",
            "generated_at_commit": "abc1234",
            "total_violations": 1,
            "violations": [{"fingerprint": fp_a, "rule_id": "SMP-001", "dataset_id": ds_id, "file_path": str(dataset_file), "field_path": "sample_count.unit", "message": "msg"}],
        },
    )

    exit_code = main(["--data-dir", str(data_dir), "--baseline", str(base_file), "--update-baseline", "--quiet"])
    assert exit_code == 1


# ==============================================================================
# Scenario H: Structural Failure Rejection
# ==============================================================================


def test_scenario_h_structural_failures_block_unconditionally(tmp_path: Path) -> None:
    """Scenario H: Fatal structural errors (malformed JSON, duplicate keys) block unconditionally."""
    data_dir = tmp_path / "datasets"
    data_dir.mkdir()

    # File with duplicate keys
    (data_dir / "dup.json").write_text('{"id": "test", "id": "test"}\n', encoding="utf-8")

    total, passed, findings, metrics = validate_all_datasets(
        data_dir=data_dir,
        schema_path=DEFAULT_SCHEMA_PATH,
        baseline_path=DEFAULT_BASELINE_PATH,
        ratchet=True,
        strict=False,
        return_findings=True,
    )
    assert total == 1
    assert passed == 0
    assert metrics["fatal_errors"] >= 1
    assert metrics["blocking_findings"] >= 1


# ==============================================================================
# Scenario I: Missing or Malformed Baseline Handling
# ==============================================================================


def test_scenario_i_missing_baseline_fails_safely_on_update(tmp_path: Path, valid_dataset_dict: dict[str, Any]) -> None:
    """Scenario I: Missing baseline path during --update-baseline fails safely with descriptive message."""
    data_dir = tmp_path / "datasets"
    data_dir.mkdir()
    (data_dir / "ds.json").write_text(json.dumps(valid_dataset_dict) + "\n", encoding="utf-8")

    non_existent = tmp_path / "non-existent-baseline.json"
    exit_code = main(["--data-dir", str(data_dir), "--baseline", str(non_existent), "--update-baseline", "--quiet"])
    assert exit_code == 1
