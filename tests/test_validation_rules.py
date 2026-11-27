"""Automated test suite for Phase 2 validation rules.

Tests deterministic validation rules across:
- Licensing consistency (LIC-001, LIC-002, LIC-REV-001)
- Date sanity & chronology (DATE-001, DATE-002, DATE-003, DATE-REV-001)
- Canonical formatting (FMT-001, FMT-002, FMT-003)
- Sample-count unit and partitions (SMP-001, SMP-002, SMP-REV-001)
- Slugs (SLUG-001, SLUG-002, SLUG-REV-001)
- Languages (LANG-001, LANG-002)
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest
import jsonschema

from scripts.validate_datasets import (
    DEFAULT_SCHEMA_PATH,
    SEVERITY_FATAL_ERROR,
    SEVERITY_INFORMATIONAL,
    SEVERITY_MANUAL_REVIEW,
    SEVERITY_RATCHETABLE_WARNING,
    check_date_rules,
    check_language_rules,
    check_licensing_rules,
    check_sample_count_rules,
    check_slug_rules,
    load_json_findings,
    load_schema,
    validate_dataset_data,
)


@pytest.fixture
def validator() -> jsonschema.Draft7Validator:
    schema_data, errors = load_schema(DEFAULT_SCHEMA_PATH)
    assert not errors
    assert schema_data is not None
    return jsonschema.Draft7Validator(schema_data)


@pytest.fixture
def base_dataset() -> dict[str, Any]:
    return {
        "schema_version": "1.0.0",
        "id": "synthetic-benchmark",
        "slug": "synthetic-benchmark",
        "name": "Synthetic Benchmark Dataset",
        "description": "Comprehensive synthetic benchmark dataset for testing validation rules.",
        "homepage_url": "https://example.org/synthetic-benchmark",
        "publisher": {
            "name": "Research Institute",
            "type": "academic",
            "url": "https://example.org",
        },
        "modalities": ["vision"],
        "tasks": ["image-classification"],
        "tags": ["benchmark", "vision"],
        "license": {
            "name": "MIT License",
            "spdx_id": "MIT",
            "status": "verified_open",
            "commercial_use": "allowed",
            "url": "https://opensource.org/licenses/MIT",
        },
        "sample_count": {
            "total": 1000,
            "unit": "images",
            "splits": {"train": 800, "test": 200},
            "partition_completeness": "complete",
            "partition_overlap": "disjoint",
        },
        "dates": {
            "published": "2024-01-15",
            "last_updated": "2024-06-20",
        },
        "verification": {
            "status": "verified",
            "verified_by": "Curator",
            "verified_date": "2024-06-20",
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
# 1. Licensing Rules (LIC-*)
# ==============================================================================


def test_lic_001_fatal_error_on_non_commercial_with_commercial_use_true(base_dataset: dict[str, Any]) -> None:
    """LIC-001: Non-commercial license combined with commercial_use=true must produce a fatal error."""
    data = copy.deepcopy(base_dataset)
    data["license"]["spdx_id"] = "CC-BY-NC-4.0"
    data["license"]["commercial_use"] = True

    findings = check_licensing_rules(data, "test.json")
    fatal = [f for f in findings if f.rule_id == "LIC-001" and f.severity == SEVERITY_FATAL_ERROR]
    assert len(fatal) == 1
    assert "Contradictory licensing" in fatal[0].message
    assert fatal[0].blocks_validation is True


def test_lic_002_ratchetable_warning_on_nc_with_verified_open(base_dataset: dict[str, Any]) -> None:
    """LIC-002: Non-commercial SPDX identifier with status=verified_open must produce a ratchetable warning."""
    data = copy.deepcopy(base_dataset)
    data["license"]["spdx_id"] = "CC-BY-NC-4.0"
    data["license"]["status"] = "verified_open"
    data["license"]["commercial_use"] = False

    findings = check_licensing_rules(data, "test.json")
    warns = [f for f in findings if f.rule_id == "LIC-002" and f.severity == SEVERITY_RATCHETABLE_WARNING]
    assert len(warns) == 1
    assert "incompatible with license status 'verified_open'" in warns[0].message


def test_lic_rev_001_manual_review_on_permissive_with_unknown_commercial_use(base_dataset: dict[str, Any]) -> None:
    """LIC-REV-001: Permissive SPDX identifier with unknown commercial_use produces manual review finding."""
    data = copy.deepcopy(base_dataset)
    data["license"]["spdx_id"] = "Apache-2.0"
    data["license"]["commercial_use"] = None
    data["license"]["status"] = "unverified"

    findings = check_licensing_rules(data, "test.json")
    reviews = [f for f in findings if f.rule_id == "LIC-REV-001" and f.severity == SEVERITY_MANUAL_REVIEW]
    assert len(reviews) == 1
    assert "unverified commercial_use" in reviews[0].message


def test_lic_compliant_open_license_produces_no_findings(base_dataset: dict[str, Any]) -> None:
    """Fully compliant open license produces no licensing findings."""
    findings = check_licensing_rules(base_dataset, "test.json")
    assert not findings


# ==============================================================================
# 2. Date Rules (DATE-*)
# ==============================================================================


@pytest.mark.parametrize(
    "invalid_date_str,field_name",
    [
        ("2024-02-31", "published"),
        ("2024-13-01", "last_updated"),
        ("not-a-date", "verified_date"),
        ("2024-04-31", "published"),
    ],
)
def test_date_001_fatal_error_on_invalid_calendar_date(
    base_dataset: dict[str, Any], invalid_date_str: str, field_name: str
) -> None:
    """DATE-001: Malformed dates or non-existent calendar dates must produce a fatal error."""
    data = copy.deepcopy(base_dataset)
    if field_name == "verified_date":
        data["verification"]["verified_date"] = invalid_date_str
    else:
        if "dates" in data and isinstance(data["dates"], dict):
            data["dates"][field_name] = invalid_date_str
        else:
            data[field_name] = invalid_date_str

    findings = check_date_rules(data, "test.json")
    fatal = [f for f in findings if f.rule_id == "DATE-001" and f.severity == SEVERITY_FATAL_ERROR]
    assert len(fatal) == 1
    assert "Invalid" in fatal[0].message


def test_date_002_ratchetable_warning_on_inverted_chronology(base_dataset: dict[str, Any]) -> None:
    """DATE-002: Inverted chronology where last_updated < published produces a ratchetable warning."""
    data = copy.deepcopy(base_dataset)
    data["dates"]["published"] = "2024-06-01"
    data["dates"]["last_updated"] = "2023-01-01"

    findings = check_date_rules(data, "test.json")
    warns = [f for f in findings if f.rule_id == "DATE-002" and f.severity == SEVERITY_RATCHETABLE_WARNING]
    assert len(warns) == 1
    assert "Inverted date chronology" in warns[0].message


def test_date_003_ratchetable_warning_on_future_verification(base_dataset: dict[str, Any]) -> None:
    """DATE-003: Future verification dates beyond current year produce a ratchetable warning."""
    data = copy.deepcopy(base_dataset)
    data["verification"]["verified_date"] = "2099-01-01"

    findings = check_date_rules(data, "test.json")
    warns = [f for f in findings if f.rule_id == "DATE-003" and f.severity == SEVERITY_RATCHETABLE_WARNING]
    assert len(warns) == 1
    assert "in the future" in warns[0].message


def test_date_rev_001_manual_review_on_pre_1940_publication(base_dataset: dict[str, Any]) -> None:
    """DATE-REV-001: Pre-computing era publication date produces manual review finding."""
    data = copy.deepcopy(base_dataset)
    data["dates"]["published"] = "1920-05-10"

    findings = check_date_rules(data, "test.json")
    reviews = [f for f in findings if f.rule_id == "DATE-REV-001" and f.severity == SEVERITY_MANUAL_REVIEW]
    assert len(reviews) == 1
    assert "precedes modern computing era" in reviews[0].message


# ==============================================================================
# 3. Canonical Formatting Rules (FMT-*)
# ==============================================================================


def test_fmt_001_ratchetable_warning_on_missing_trailing_newline(tmp_path: Path) -> None:
    """FMT-001: Missing trailing newline produces a ratchetable warning."""
    file_path = tmp_path / "no_newline.json"
    file_path.write_bytes(b'{"name": "test"}')

    data, findings = load_json_findings(file_path)
    assert data is not None
    warns = [f for f in findings if f.rule_id == "FMT-001" and f.severity == SEVERITY_RATCHETABLE_WARNING]
    assert len(warns) == 1
    assert "missing a trailing newline" in warns[0].message


def test_fmt_002_fatal_error_on_duplicate_json_keys(tmp_path: Path) -> None:
    """FMT-002: Duplicate keys in JSON file produce a fatal error."""
    file_path = tmp_path / "dup_keys.json"
    file_path.write_text('{"name": "first", "name": "second"}\n', encoding="utf-8")

    data, findings = load_json_findings(file_path)
    assert data is not None
    fatal = [f for f in findings if f.rule_id == "FMT-002" and f.severity == SEVERITY_FATAL_ERROR]
    assert len(fatal) == 1
    assert "Duplicate JSON key 'name' detected" in fatal[0].message


def test_fmt_003_fatal_error_on_invalid_utf8(tmp_path: Path) -> None:
    """FMT-003: Invalid UTF-8 bytes produce a fatal error."""
    file_path = tmp_path / "invalid_utf8.json"
    file_path.write_bytes(b'{"name": "\xff\xfe"}\n')

    data, findings = load_json_findings(file_path)
    assert data is None
    fatal = [f for f in findings if f.rule_id == "FMT-003" and f.severity == SEVERITY_FATAL_ERROR]
    assert len(fatal) == 1
    assert "Invalid UTF-8" in fatal[0].message


# ==============================================================================
# 4. Sample-Count Unit and Partition Rules (SMP-*)
# ==============================================================================


def test_smp_001_ratchetable_warning_on_missing_unit(base_dataset: dict[str, Any]) -> None:
    """SMP-001: Missing sample_count.unit produces a ratchetable warning."""
    data = copy.deepcopy(base_dataset)
    del data["sample_count"]["unit"]

    findings = check_sample_count_rules(data, "test.json")
    warns = [f for f in findings if f.rule_id == "SMP-001" and f.severity == SEVERITY_RATCHETABLE_WARNING]
    assert len(warns) == 1
    assert "Missing required 'unit'" in warns[0].message


def test_smp_002_fatal_error_on_complete_disjoint_arithmetic_mismatch(base_dataset: dict[str, Any]) -> None:
    """SMP-002: Arithmetic mismatch when completeness=complete and overlap=disjoint produces a fatal error."""
    data = copy.deepcopy(base_dataset)
    data["sample_count"]["total"] = 1000
    data["sample_count"]["splits"] = {"train": 600, "test": 300}  # sum = 900 != 1000
    data["sample_count"]["partition_completeness"] = "complete"
    data["sample_count"]["partition_overlap"] = "disjoint"

    findings = check_sample_count_rules(data, "test.json")
    fatal = [f for f in findings if f.rule_id == "SMP-002" and f.severity == SEVERITY_FATAL_ERROR]
    assert len(fatal) == 1
    assert "does not equal declared total" in fatal[0].message


def test_smp_rev_001_manual_review_on_unspecified_partition_arithmetic_mismatch(base_dataset: dict[str, Any]) -> None:
    """SMP-REV-001: Split sum mismatch under unspecified partitions produces a manual review finding."""
    data = copy.deepcopy(base_dataset)
    data["sample_count"]["total"] = 1000
    data["sample_count"]["splits"] = {"train": 600, "test": 300}
    data["sample_count"]["partition_completeness"] = "unspecified"
    data["sample_count"]["partition_overlap"] = "unspecified"

    findings = check_sample_count_rules(data, "test.json")
    reviews = [f for f in findings if f.rule_id == "SMP-REV-001" and f.severity == SEVERITY_MANUAL_REVIEW]
    assert len(reviews) == 1
    assert "unspecified partition semantics" in reviews[0].message


# ==============================================================================
# 5. Slug Rules (SLUG-*)
# ==============================================================================


@pytest.mark.parametrize(
    "invalid_slug",
    [
        "CamelCase-Slug",
        "under_score_slug",
        "trailing-hyphen-",
        "-leading-hyphen",
        "double--hyphen",
        "a",  # length < 2
        "x" * 85,  # length > 80
    ],
)
def test_slug_001_fatal_error_on_invalid_slug_format(base_dataset: dict[str, Any], invalid_slug: str) -> None:
    """SLUG-001: Slugs violating lowercase kebab-case or length bounds produce fatal errors."""
    data = copy.deepcopy(base_dataset)
    data["slug"] = invalid_slug
    data["id"] = invalid_slug

    findings = check_slug_rules(data, "test.json")
    fatal = [f for f in findings if f.rule_id == "SLUG-001" and f.severity == SEVERITY_FATAL_ERROR]
    assert len(fatal) >= 1


def test_slug_002_ratchetable_warning_on_mismatched_id(base_dataset: dict[str, Any]) -> None:
    """SLUG-002: Slug not matching id produces a ratchetable warning."""
    data = copy.deepcopy(base_dataset)
    data["id"] = "benchmark-dataset-id"
    data["slug"] = "benchmark-dataset-slug"

    findings = check_slug_rules(data, "test.json")
    warns = [f for f in findings if f.rule_id == "SLUG-002" and f.severity == SEVERITY_RATCHETABLE_WARNING]
    assert len(warns) == 1
    assert "does not match dataset id" in warns[0].message


def test_slug_rev_001_manual_review_on_45_char_slug(base_dataset: dict[str, Any]) -> None:
    """SLUG-REV-001: 45-character slug produces manual review finding for suspected truncation."""
    data = copy.deepcopy(base_dataset)
    slug_45 = "a" * 45
    data["id"] = slug_45
    data["slug"] = slug_45

    findings = check_slug_rules(data, "test.json")
    reviews = [f for f in findings if f.rule_id == "SLUG-REV-001" and f.severity == SEVERITY_MANUAL_REVIEW]
    assert len(reviews) == 1
    assert "has length 45" in reviews[0].message


# ==============================================================================
# 6. Language Metadata Rules (LANG-*)
# ==============================================================================


@pytest.mark.parametrize(
    "invalid_lang_tag",
    [
        "multilingual",
        "english",
        "spanish",
        "en_US",  # underscores not standard in BCP 47
        "12345",
    ],
)
def test_lang_001_ratchetable_warning_on_invalid_bcp47(base_dataset: dict[str, Any], invalid_lang_tag: str) -> None:
    """LANG-001: Invalid BCP 47 language tags produce a ratchetable warning."""
    data = copy.deepcopy(base_dataset)
    data["languages"] = [invalid_lang_tag]

    findings = check_language_rules(data, "test.json")
    warns = [f for f in findings if f.rule_id == "LANG-001" and f.severity == SEVERITY_RATCHETABLE_WARNING]
    assert len(warns) == 1
    assert "not a valid BCP 47 tag" in warns[0].message


def test_lang_002_ratchetable_warning_on_nlp_missing_languages(base_dataset: dict[str, Any]) -> None:
    """LANG-002: NLP dataset missing languages produces a ratchetable warning."""
    data = copy.deepcopy(base_dataset)
    data["modalities"] = ["nlp"]
    data["tasks"] = ["text-classification"]
    if "languages" in data:
        del data["languages"]

    findings = check_language_rules(data, "test.json")
    warns = [f for f in findings if f.rule_id == "LANG-002" and f.severity == SEVERITY_RATCHETABLE_WARNING]
    assert len(warns) == 1
    assert "missing required 'languages'" in warns[0].message


def test_lang_002_exempts_non_speech_audio(base_dataset: dict[str, Any]) -> None:
    """LANG-002: Non-speech audio datasets without nlp modality are exempt from languages requirement."""
    data = copy.deepcopy(base_dataset)
    data["modalities"] = ["audio"]
    data["tasks"] = ["audio-classification", "sound-event-detection"]
    if "languages" in data:
        del data["languages"]

    findings = check_language_rules(data, "test.json")
    lang_002 = [f for f in findings if f.rule_id == "LANG-002"]
    assert not lang_002
