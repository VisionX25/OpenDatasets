"""Automated test suite for OpenDatasets community suggestion automation foundation.

Covers:
- Scenario 1: Valid suggestion parsing and draft generation (Issue #6 fixture)
- Scenario 2: Missing required fields rejection (name, URL, description)
- Scenario 3: Multiline content and rich markdown formatting preservation
- Scenario 4: Duplicate dataset name detection (exact, normalized, token overlap)
- Scenario 5: Duplicate URL and DOI detection
- Scenario 6: Unknown / unspecified license handling
- Scenario 7: Malformed / malicious untrusted input containment
- Scenario 8: Unicode and Bangla dataset names handling
- Scenario 9: Metadata schema compatibility of generated drafts (all modalities)
- Scenario 10: Preservation of the existing 101-dataset published catalog
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import jsonschema
import pytest

from scripts.draft_generator import (
    DEFAULT_SCHEMA_PATH,
    generate_draft_metadata,
    generate_slug,
    infer_modalities,
    validate_draft_dict,
)
from scripts.duplicate_detector import (
    check_suggestion_for_duplicates,
    load_catalog_datasets,
    normalize_doi_canonical,
    normalize_url_canonical,
)
from scripts.process_suggestion import process_suggestion
from scripts.suggestion_parser import (
    ParsedSuggestion,
    extract_doi,
    is_valid_url,
    parse_dataset_suggestion,
    sanitize_untrusted_text,
)
from scripts.validate_datasets import (
    DEFAULT_DATA_DIR,
    check_duplicate_ids_and_slugs,
    load_schema,
    validate_all_datasets,
)

REPO_ROOT = Path(__file__).resolve().parent.parent

# Fixture representing the real community submission from GitHub Issue #6
ISSUE_6_BODY = """### Dataset name
Banknote Authentication

### Official dataset URL
https://archive.ics.uci.edu/dataset/267/banknote+authentication

### Modality, task, and usefulness
**Category:** Tabular
**Primary Task:** Binary Classification
**Description:**
The Banknote Authentication dataset from the UCI Machine Learning Repository consists of 1,372 instances with 4 continuous numerical features extracted from genuine and counterfeit banknote-like specimens using wavelet transforms.

### License information
Creative Commons Attribution 4.0 International (CC BY 4.0)

### Additional evidence and limitations
- **DOI:** 10.24432/C55P57
- **Supporting Paper URL:** https://doi.org/10.24432/C55P57
- **Additional Notes / Limitations:**
Donated in 2012 by Volker Lohweg. Binary class label: 0 for genuine, 1 for forged.
"""


@pytest.fixture(scope="session")
def catalog_datasets() -> list[dict[str, Any]]:
    """Load all published catalog datasets."""
    datasets = load_catalog_datasets(DEFAULT_DATA_DIR)
    assert len(datasets) == 101, f"Expected exactly 101 datasets, found {len(datasets)}"
    return datasets


@pytest.fixture(scope="session")
def schema_validator() -> jsonschema.Draft7Validator:
    """Load schema and return Draft7Validator."""
    schema, errors = load_schema(DEFAULT_SCHEMA_PATH)
    assert not errors, f"Failed to load schema: {errors}"
    assert schema is not None
    return jsonschema.Draft7Validator(schema)


# ==============================================================================
# Scenario 1: Valid suggestion (Issue #6 Banknote Authentication fixture)
# ==============================================================================
def test_scenario_1_valid_suggestion_issue_6():
    """Verify parsing and draft generation of a complete, valid community submission."""
    suggestion = parse_dataset_suggestion(ISSUE_6_BODY)

    assert suggestion.is_valid, f"Suggestion failed validation: {suggestion.errors}"
    assert suggestion.name == "Banknote Authentication"
    assert suggestion.source_url == "https://archive.ics.uci.edu/dataset/267/banknote+authentication"
    assert suggestion.category == "Tabular"
    assert suggestion.task == "Binary Classification"
    assert "UCI Machine Learning Repository" in suggestion.description
    assert "CC BY 4.0" in suggestion.license_text
    assert suggestion.doi == "10.24432/C55P57"
    assert suggestion.paper_url == "https://doi.org/10.24432/C55P57"
    assert "Volker Lohweg" in suggestion.notes

    # Generate draft
    draft = generate_draft_metadata(suggestion, issue_number=6)
    assert draft["slug"] == "banknote-authentication"
    assert draft["verification"]["status"] == "provisional"
    assert draft["verification"]["verified_by"] is None
    assert draft["publisher"]["name"] == "UCI Machine Learning Repository"
    assert "tabular" in draft["modalities"]

    # Verify schema compliance
    errors = validate_draft_dict(draft)
    assert not errors, f"Draft schema errors: {errors}"


# ==============================================================================
# Scenario 2: Missing required fields rejection
# ==============================================================================
def test_scenario_2_missing_required_fields():
    """Verify robust rejection of missing required fields."""
    # A. Missing name
    body_no_name = """### Dataset name
_No response_

### Official dataset URL
https://example.org/dataset

### Modality, task, and usefulness
**Description:** A valid description of at least ten characters.
"""
    sug_no_name = parse_dataset_suggestion(body_no_name)
    assert not sug_no_name.is_valid
    assert any("Dataset name" in err for err in sug_no_name.errors)

    # B. Invalid URL
    body_invalid_url = """### Dataset name
Valid Dataset Name

### Official dataset URL
not-a-valid-url

### Modality, task, and usefulness
**Description:** A valid description of at least ten characters.
"""
    sug_bad_url = parse_dataset_suggestion(body_invalid_url)
    assert not sug_bad_url.is_valid
    assert any("Official dataset URL" in err for err in sug_bad_url.errors)

    # C. Missing / too short description
    body_short_desc = """### Dataset name
Valid Dataset Name

### Official dataset URL
https://example.org/data

### Modality, task, and usefulness
**Description:** Short
"""
    sug_short_desc = parse_dataset_suggestion(body_short_desc)
    assert not sug_short_desc.is_valid
    assert any("Description must be at least 10 characters" in err for err in sug_short_desc.errors)


# ==============================================================================
# Scenario 3: Multiline content with markdown formatting
# ==============================================================================
def test_scenario_3_multiline_markdown_preservation():
    """Verify that multiline formatting, bullet points, and code snippets are preserved."""
    multiline_desc = (
        "This dataset contains extensive telemetry recordings:\n\n"
        "- Parameter A: Temperature (°C)\n"
        "- Parameter B: Pressure (kPa)\n"
        "- Parameter C: Vibrational frequencies\n\n"
        "Collected over 180 continuous operating cycles under load."
    )
    body = f"""### Dataset name
Industrial Sensor Telemetry

### Official dataset URL
https://sensors.example.edu/telemetry

### Modality, task, and usefulness
**Category:** Time-Series
**Primary Task:** Anomaly Detection
**Description:**
{multiline_desc}

### License information
MIT License
"""
    suggestion = parse_dataset_suggestion(body)
    assert suggestion.is_valid
    assert "Parameter A: Temperature" in suggestion.description
    assert "Parameter C: Vibrational frequencies" in suggestion.description
    assert "180 continuous operating cycles" in suggestion.description

    draft = generate_draft_metadata(suggestion)
    assert draft["description"] == multiline_desc
    errors = validate_draft_dict(draft)
    assert not errors, f"Draft schema errors: {errors}"


# ==============================================================================
# Scenario 4: Duplicate dataset names detection
# ==============================================================================
def test_scenario_4_duplicate_name_detection(catalog_datasets: list[dict[str, Any]]):
    """Verify exact, normalized, and fuzzy name duplicate detection."""
    # A. Exact match
    sug_exact = ParsedSuggestion(
        name="Banknote Authentication",
        source_url="https://novel-url.org/banknotes",
        description="A novel description.",
    )
    res_exact = check_suggestion_for_duplicates(sug_exact, catalog_datasets)
    assert res_exact.is_duplicate
    assert any(m.match_type == "exact_name" for m in res_exact.matches)

    # B. Normalized match (different case and punctuation)
    sug_norm = ParsedSuggestion(
        name="banknote authentication!",
        source_url="https://novel-url.org/banknotes",
        description="A novel description.",
    )
    res_norm = check_suggestion_for_duplicates(sug_norm, catalog_datasets)
    assert res_norm.is_duplicate

    # C. High token overlap (Fuzzy similarity must be a warning, not auto-rejection)
    sug_tokens = ParsedSuggestion(
        name="Banknote Authentication Benchmark Dataset",
        source_url="https://novel-url.org/banknotes",
        description="A novel description.",
    )
    res_tokens = check_suggestion_for_duplicates(sug_tokens, catalog_datasets)
    assert res_tokens.has_potential_matches
    assert not res_tokens.is_duplicate, "Fuzzy match must be a warning, not automatic rejection"
    assert res_tokens.primary_match.existing_id == "banknote-authentication"
    assert res_tokens.primary_match.confidence == "potential_duplicate"

    # D. Distinct novel dataset
    sug_novel = ParsedSuggestion(
        name="Antarctic Phytoplankton Fluorescence Survey",
        source_url="https://ocean-bio.org/antarctic-plankton",
        description="Unique oceanographic research dataset.",
    )
    res_novel = check_suggestion_for_duplicates(sug_novel, catalog_datasets)
    assert not res_novel.is_duplicate
    assert not res_novel.has_potential_matches


# ==============================================================================
# Scenario 5: Duplicate URLs and DOIs
# ==============================================================================
def test_scenario_5_duplicate_url_and_doi(catalog_datasets: list[dict[str, Any]]):
    """Verify canonical URL and DOI collision detection."""
    # A. Exact URL
    sug_url = ParsedSuggestion(
        name="Completely Random Alternative Name",
        source_url="https://archive.ics.uci.edu/dataset/267/banknote+authentication",
    )
    res_url = check_suggestion_for_duplicates(sug_url, catalog_datasets)
    assert res_url.is_duplicate
    assert any("banknote-authentication" == m.existing_id for m in res_url.matches)

    # B. Canonicalized URL with trailing slash
    sug_canon_url = ParsedSuggestion(
        name="Another Alternative Title",
        source_url="https://archive.ics.uci.edu/dataset/267/banknote+authentication/",
    )
    res_canon = check_suggestion_for_duplicates(sug_canon_url, catalog_datasets)
    assert res_canon.is_duplicate

    # C. DOI match
    sug_doi = ParsedSuggestion(
        name="Another Alternative Title",
        source_url="https://unrelated-mirror.net/data",
        doi="10.24432/c55p57",  # Lowercase variation of Banknote Authentication DOI
    )
    res_doi = check_suggestion_for_duplicates(sug_doi, catalog_datasets)
    assert res_doi.is_duplicate
    assert any(m.match_type == "exact_doi" for m in res_doi.matches)


# ==============================================================================
# Scenario 6: Unknown / unspecified license handling
# ==============================================================================
def test_scenario_6_unspecified_license_handling():
    """Verify that unknown/missing licenses default safely without schema violations."""
    body_no_license = """### Dataset name
Public Highway Traffic Cameras

### Official dataset URL
https://traffic.state.gov/cameras

### Modality, task, and usefulness
**Category:** Vision
**Primary Task:** Object Detection
**Description:** Continuous highway video streams for vehicular flow monitoring.

### License information
_No response_
"""
    suggestion = parse_dataset_suggestion(body_no_license)
    assert suggestion.is_valid
    assert len(suggestion.warnings) > 0

    draft = generate_draft_metadata(suggestion)
    assert draft["license"]["status"] == "unknown"
    assert draft["license"]["commercial_use"] == "unknown"
    assert "Verification required" in draft["license"]["notes"] or "maintainer" in draft["license"]["notes"]

    errors = validate_draft_dict(draft)
    assert not errors, f"Draft schema errors: {errors}"

    # Also verify contributor-claimed licenses (e.g. CC BY 4.0, MIT, Apache) are NEVER marked verified
    for claimed_lic in ["CC BY 4.0", "MIT License", "Apache-2.0", "Public Domain", "GPLv3"]:
        sug_claimed = ParsedSuggestion(
            name="Claimed License Dataset",
            source_url="https://example.org/data",
            category="Vision",
            task="Detection",
            description="A valid benchmark dataset description for testing license status rules.",
            license_text=claimed_lic,
        )
        draft_claimed = generate_draft_metadata(sug_claimed)
        assert draft_claimed["license"]["status"] == "unknown", (
            f"Claimed license '{claimed_lic}' must have status 'unknown', got '{draft_claimed['license']['status']}'"
        )
        assert draft_claimed["license"]["commercial_use"] == "unknown"
        assert "verified" not in draft_claimed["license"]["status"].lower()
        errs = validate_draft_dict(draft_claimed)
        assert not errs, f"Draft validation errors on claimed license '{claimed_lic}': {errs}"


# ==============================================================================
# Scenario 7: Malformed / malicious untrusted input containment
# ==============================================================================
def test_scenario_7_malicious_input_containment():
    """Verify that script tags, shell commands, path traversals, and null bytes are sanitized."""
    # Raw input containing null bytes, path traversal, and script tags
    dirty_text = "\x00\x08<script>alert('pwned')</script> ../../../etc/passwd $(whoami)"
    sanitized = sanitize_untrusted_text(dirty_text)

    assert "\x00" not in sanitized
    assert "\x08" not in sanitized
    # Tags and symbols are treated purely as passive string characters
    assert "<script>" in sanitized

    # Verify slug generation neutralizes path traversal safely
    slug = generate_slug("../../../etc/passwd")
    assert "/" not in slug
    assert ".." not in slug
    assert slug == "etc-passwd"

    # Shell injection attempts in issue body
    body_injection = """### Dataset name
Test Dataset; rm -rf /; echo "pwn"

### Official dataset URL
https://safe-domain.org/data

### Modality, task, and usefulness
**Description:** Safe testing description of sufficient character length.
"""
    exit_code, result, report = process_suggestion(
        raw_body=body_injection,
        save_draft=False,
    )
    assert exit_code == 0
    # Slug is sanitized into safe kebab-case tokens
    assert result["slug"] == "test-dataset-rm-rf-echo-pwn"
    assert "/" not in result["slug"]
    assert ";" not in result["slug"]


# ==============================================================================
# Scenario 8: Unicode and Bangla dataset names
# ==============================================================================
def test_scenario_8_unicode_and_bangla_handling():
    """Verify full support for Unicode and Bangla characters in names and descriptions."""
    bangla_name = "বাংলা স্পিচ করপাস"
    bangla_desc = "উন্মুক্ত বাংলা ভাষার অডিও স্পিচ ডেটাসেট যা স্বয়ংক্রিয় বাচন শনাক্তকরণের জন্য তৈরি।"

    body_bangla = f"""### Dataset name
{bangla_name}

### Official dataset URL
https://bengali-speech.org/corpus

### Modality, task, and usefulness
**Category:** Audio
**Primary Task:** Speech Recognition
**Description:**
{bangla_desc}

### License information
Creative Commons Attribution 4.0 International
"""
    suggestion = parse_dataset_suggestion(body_bangla)
    assert suggestion.is_valid
    assert suggestion.name == bangla_name
    assert suggestion.description == bangla_desc

    draft = generate_draft_metadata(suggestion)
    assert draft["name"] == bangla_name
    assert draft["description"] == bangla_desc
    assert "audio" in draft["modalities"]

    # Slug must be safe ASCII alphanumeric conforming to pattern ^[a-z0-9]+(-[a-z0-9]+)*$
    assert draft["slug"].startswith("dataset-")
    errors = validate_draft_dict(draft)
    assert not errors, f"Draft schema errors on Bangla dataset: {errors}"


# ==============================================================================
# Scenario 9: Metadata schema compatibility across modalities
# ==============================================================================
@pytest.mark.parametrize(
    "category,task,modality_expected",
    [
        ("Computer Vision", "Object Detection", "vision"),
        ("Natural Language Processing", "Text Classification", "nlp"),
        ("Acoustic Audio", "Speaker Identification", "audio"),
        ("Tabular Records", "Regression", "tabular"),
        ("Multimodal Vision-Language", "Visual Question Answering", "multimodal"),
        ("Reinforcement Learning", "Policy Optimization", "reinforcement-learning"),
    ],
)
def test_scenario_9_schema_compatibility_modalities(category: str, task: str, modality_expected: str):
    """Verify that drafts generated for any supported modality conform 100% to schema."""
    sug = ParsedSuggestion(
        name=f"Standard Benchmark for {category}",
        source_url=f"https://benchmark-{modality_expected}.org/data",
        category=category,
        task=task,
        description=f"A high-quality standard benchmark dataset designed for {category} research tasks.",
        license_text="Apache License 2.0",
        doi=f"10.1234/test.{modality_expected}.2026",
    )
    draft = generate_draft_metadata(sug)
    assert modality_expected in draft["modalities"]
    assert draft["verification"]["status"] == "provisional"
    errors = validate_draft_dict(draft)
    assert not errors, f"Schema validation errors for {category}: {errors}"


# ==============================================================================
# Scenario 10: Preservation of the existing 101-dataset catalog
# ==============================================================================
def test_scenario_10_catalog_preservation(catalog_datasets: list[dict[str, Any]]):
    """Verify that existing 101 datasets remain intact and valid with zero regressions."""
    assert len(catalog_datasets) == 101

    # Validate all 101 dataset files using the project validator
    data_dir = REPO_ROOT / "data" / "datasets"
    schema_path = REPO_ROOT / "schemas" / "dataset.v1.schema.json"

    total_checked, total_passed, errors = validate_all_datasets(data_dir=data_dir, schema_path=schema_path)
    assert total_checked == 101
    assert total_passed == 101
    assert len(errors) == 0

    # Ensure no duplicates exist in current catalog
    dup_errors = check_duplicate_ids_and_slugs([(Path(d["id"]), d) for d in catalog_datasets])
    assert not dup_errors, f"Catalog duplicate errors: {dup_errors}"


# ==============================================================================
# CLI Entrypoint Tests (subprocess & GitHub Actions event payloads)
# ==============================================================================
def test_cli_entrypoint_event_path(tmp_path: Path):
    """Verify CLI behavior when processing GitHub event payload file."""
    import subprocess
    import sys

    event_payload = {
        "action": "opened",
        "issue": {
            "number": 88,
            "title": "Dataset: Oceanic Temperature Profiles",
            "body": """### Dataset name
Oceanic Temperature Profiles

### Official dataset URL
https://noaa.gov/oceanic-temperature

### Modality, task, and usefulness
**Category:** Time-Series
**Primary Task:** Forecasting
**Description:** Global ocean temperature profiles recorded from drifting buoys and weather stations.

### License information
Public Domain (CC0)
""",
        },
    }
    event_file = tmp_path / "github_event.json"
    event_file.write_text(json.dumps(event_payload), encoding="utf-8")

    output_dir = tmp_path / "drafts"
    cmd = [
        sys.executable,
        str(REPO_ROOT / "scripts" / "process_suggestion.py"),
        "--event-path",
        str(event_file),
        "--output-dir",
        str(output_dir),
        "--json",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    assert proc.returncode == 0
    data = json.loads(proc.stdout)
    assert data["status"] == "valid"
    assert data["recommended_label"] == "candidate-approved"
    assert data["slug"] == "oceanic-temperature-profiles"
    assert Path(data["draft_path"]).exists()


def test_cli_duplicate_exit_code(tmp_path: Path):
    """Verify CLI exit code 2 when duplicate is encountered."""
    import subprocess
    import sys

    issue_file = tmp_path / "dup_issue.md"
    issue_file.write_text(ISSUE_6_BODY, encoding="utf-8")

    cmd = [
        sys.executable,
        str(REPO_ROOT / "scripts" / "process_suggestion.py"),
        "--issue-file",
        str(issue_file),
        "--no-save",
        "--json",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    assert proc.returncode == 2
    data = json.loads(proc.stdout)
    assert data["status"] == "duplicate"
    assert data["is_duplicate"] is True
    assert data["recommended_label"] == "duplicate"


def test_cli_invalid_exit_code(tmp_path: Path):
    """Verify CLI exit code 1 when required fields are missing."""
    import subprocess
    import sys

    issue_file = tmp_path / "invalid_issue.md"
    issue_file.write_text("### Dataset name\n\n### Official dataset URL\n\n", encoding="utf-8")

    cmd = [
        sys.executable,
        str(REPO_ROOT / "scripts" / "process_suggestion.py"),
        "--issue-file",
        str(issue_file),
        "--no-save",
        "--json",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    assert proc.returncode == 1
    data = json.loads(proc.stdout)
    assert data["status"] == "invalid"
    assert data["is_valid"] is False
    assert data["recommended_label"] == "needs-info"


def test_slug_and_filename_collision_handling(tmp_path: Path):
    """Verify that slug collisions with existing catalog datasets are resolved safely."""
    # 1. Slug collision with an existing dataset name
    existing_slugs = {"banknote-authentication", "cifar-10", "mnist"}
    new_slug = generate_slug("Banknote Authentication", existing_slugs=existing_slugs)
    assert new_slug == "banknote-authentication-draft"
    assert new_slug not in existing_slugs

    # 2. Filename collision handling across different issue numbers
    output_dir = tmp_path / "drafts"
    sug = ParsedSuggestion(
        name="Unique Sensor Data",
        source_url="https://sensors.org/unique",
        category="Time-Series",
        task="Forecasting",
        description="A unique sensory dataset from automotive test vehicles.",
        license_text="MIT",
    )
    from scripts.process_suggestion import process_suggestion
    body = """### Dataset name
Unique Sensor Data

### Official dataset URL
https://sensors.org/unique

### Modality, task, and usefulness
**Category:** Time-Series
**Primary Task:** Forecasting
**Description:** A unique sensory dataset from automotive test vehicles.

### License information
MIT
"""
    exit1, res1, _ = process_suggestion(raw_body=body, output_dir=output_dir, issue_number=10)
    exit2, res2, _ = process_suggestion(raw_body=body, output_dir=output_dir, issue_number=11)

    assert exit1 == 0 and exit2 == 0
    # Two separate files created without colliding or overwriting each other
    assert res1["draft_path"] != res2["draft_path"]
    assert "issue10" in res1["draft_path"]
    assert "issue11" in res2["draft_path"]
    assert Path(res1["draft_path"]).exists()
    assert Path(res2["draft_path"]).exists()


# ==============================================================================
# Task 14.2 Specific Tests (Unsupported Issue Types, Workflow, Summary File)
# ==============================================================================
def test_task_14_2_unsupported_issue_types():
    """Verify that bug reports and non-suggestion issues are safely identified and skipped."""
    from scripts.suggestion_parser import is_dataset_suggestion_template

    # 1. Bug report template body
    bug_body = """### Describe the bug
The dataset filter for 'vision' returns 0 results on mobile devices.

### Steps to Reproduce
1. Open mobile browser
2. Tap vision filter

### Expected behavior
Should show vision datasets.
"""
    assert not is_dataset_suggestion_template(bug_body)
    exit_code, res, report = process_suggestion(raw_body=bug_body, issue_number=123)
    assert exit_code == 0
    assert res["status"] == "unsupported"
    assert res["draft_path"] is None
    assert res["draft_metadata"] is None
    assert "Non-Dataset Suggestion" in report
    assert "Skipped automated dataset triage" in report

    # 2. General freeform question
    question_body = "Hello! Where can I find the raw images for CIFAR-10?"
    assert not is_dataset_suggestion_template(question_body)
    exit_q, res_q, report_q = process_suggestion(raw_body=question_body, issue_number=124)
    assert exit_q == 0
    assert res_q["status"] == "unsupported"
    assert "Non-Dataset Suggestion" in report_q

    # 3. Empty issue body
    assert not is_dataset_suggestion_template("")
    exit_e, res_e, _ = process_suggestion(raw_body="", issue_number=125)
    assert exit_e == 0
    assert res_e["status"] == "unsupported"


def test_task_14_2_summary_file_and_event_integration(tmp_path: Path):
    """Verify GitHub event payload parsing and summary file output generation."""
    event_payload = {
        "action": "opened",
        "issue": {
            "number": 200,
            "title": "[Dataset]: BioAcoustic Avian Vocalizations",
            "body": """### Dataset name
BioAcoustic Avian Vocalizations

### Official dataset URL
https://avian-bioacoustics.org/data

### Modality, task, and usefulness
**Category:** Audio
**Primary Task:** Audio Classification
**Description:** A curated collection of 10,000 avian audio recordings with species-level annotations.

### License information
Creative Commons Attribution 4.0 International

### Additional evidence and limitations
- **DOI:** 10.1234/avian.2026.01
- **Additional Notes / Limitations:**
Field recordings across 5 distinct forest habitats.
""",
        },
    }
    event_file = tmp_path / "github_event.json"
    event_file.write_text(json.dumps(event_payload), encoding="utf-8")

    report_file = tmp_path / "triage_output" / "report.md"
    summary_file = tmp_path / "step_summary.md"
    drafts_dir = tmp_path / "drafts"

    import subprocess
    import sys

    cmd = [
        sys.executable,
        str(REPO_ROOT / "scripts" / "process_suggestion.py"),
        "--event-path",
        str(event_file),
        "--output-dir",
        str(drafts_dir),
        "--report-file",
        str(report_file),
        "--summary-file",
        str(summary_file),
        "--json",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    assert proc.returncode == 0
    data = json.loads(proc.stdout)

    assert data["status"] == "valid"
    assert data["is_valid"] is True
    assert data["slug"] == "bioacoustic-avian-vocalizations"
    assert Path(data["draft_path"]).exists()

    # Check that report_file and summary_file were written with all required sections
    assert report_file.exists()
    assert summary_file.exists()
    summary_content = summary_file.read_text(encoding="utf-8")
    assert "# Community Dataset Suggestion Triage Report" in summary_content
    assert "Issue #200" in summary_content
    assert "BioAcoustic Avian Vocalizations" in summary_content
    assert "## Parsing & Validation" in summary_content
    assert "## Duplicate Check" in summary_content
    assert "## Schema Compliance (Draft)" in summary_content
    assert "## Unknown or Unverified Claims" in summary_content
    assert "## Required Manual Verification Steps" in summary_content
    assert "## Recommended Next Steps" in summary_content


def test_task_14_2_workflow_file_security_and_structure():
    """Verify that dataset-suggestion.yml conforms to strict security requirements."""
    import re

    workflow_path = REPO_ROOT / ".github" / "workflows" / "dataset-suggestion.yml"
    assert workflow_path.exists(), "Workflow file .github/workflows/dataset-suggestion.yml is missing"

    raw_yaml_text = workflow_path.read_text(encoding="utf-8")

    # 1. Triggered on issues: [opened]
    assert re.search(r"['\"]?on['\"]?:\s*\n\s+issues:\s*\n\s+types:\s*\[\s*opened\s*\]", raw_yaml_text), (
        "Workflow must trigger on issues: [opened]"
    )

    # 2. Minimal permissions: contents: read only
    assert re.search(r"permissions:\s*\n\s+contents:\s*read", raw_yaml_text), (
        "Workflow permissions must be strictly contents: read"
    )

    # 3. Concurrency configured
    assert re.search(
        r"concurrency:\s*\n\s+group:\s*dataset-suggestion-\$\{\{\s*github\.event\.issue\.number\s*\}\}",
        raw_yaml_text,
    ), "Workflow must configure concurrency grouped by issue number"
    assert re.search(r"cancel-in-progress:\s*false", raw_yaml_text)

    # 4. Triage job configuration
    assert re.search(r"jobs:\s*\n\s+triage:", raw_yaml_text)
    assert re.search(r"timeout-minutes:\s*5", raw_yaml_text), (
        "Triage job must specify a 5-minute timeout"
    )

    # If PyYAML is available, verify full parsed dictionary structure as well
    try:
        import yaml
        wf = yaml.safe_load(raw_yaml_text)
        assert isinstance(wf, dict)
        on_trigger = wf.get("on") or wf.get(True) or wf.get("'on'")
        assert on_trigger is not None
        assert "issues" in on_trigger
        assert on_trigger["issues"]["types"] == ["opened"]
        assert wf.get("permissions") == {"contents": "read"}
        assert "dataset-suggestion" in wf.get("concurrency", {}).get("group", "")
        job = wf.get("jobs", {}).get("triage", {})
        assert job.get("timeout-minutes") == 5
    except ImportError:
        pass

    # 5. Verify security: no raw issue interpolation in steps
    assert "${{ github.event.issue.body }}" not in raw_yaml_text, "Remote script injection risk detected!"
    assert "${{ github.event.issue.title }}" not in raw_yaml_text, "Remote script injection risk detected!"
    assert "$GITHUB_EVENT_PATH" in raw_yaml_text, "Must pass event payload via file path!"


def test_task_14_2_nine_scenario_checklist(catalog_datasets: list[dict[str, Any]]):
    """Explicitly verify all 9 scenarios specified in Task 14.2 requirements."""
    # 1. New valid dataset issue
    valid_body = """### Dataset name
Marine Debris Optical Benchmark

### Official dataset URL
https://marinedebris.org/benchmark

### Modality, task, and usefulness
**Category:** Vision
**Primary Task:** Object Detection
**Description:** A comprehensive benchmark of underwater floating marine plastic debris annotated for object detection.

### License information
Creative Commons Attribution 4.0 International

### Additional evidence and limitations
- **DOI:** 10.1234/marine.debris.2026
"""
    code_v, res_v, rep_v = process_suggestion(raw_body=valid_body, issue_number=10)
    assert code_v == 0
    assert res_v["status"] == "valid"
    assert res_v["is_valid"] is True

    # 2. Missing required fields
    code_m, res_m, _ = process_suggestion(raw_body="### Dataset name\n_No response_\n### Official dataset URL\nhttps://example.org\n")
    assert code_m == 1
    assert res_m["status"] == "invalid"
    assert res_m["is_valid"] is False

    # 3. Exact duplicate
    code_d, res_d, _ = process_suggestion(raw_body="### Dataset name\nBanknote Authentication\n### Official dataset URL\nhttps://archive.ics.uci.edu/dataset/267/banknote+authentication\n### Modality, task, and usefulness\n**Description:** A valid description of at least ten characters.\n")
    assert code_d == 2
    assert res_d["status"] == "duplicate"
    assert res_d["is_duplicate"] is True

    # 4. Fuzzy duplicate warning (must NOT auto-reject)
    fuzzy_sug = ParsedSuggestion(
        name="Banknote Authentication Benchmark Dataset",
        source_url="https://example.org/different-url",
        category="Tabular",
        task="Classification",
        description="A different extension of banknote classification records.",
        license_text="MIT",
    )
    fuzzy_res = check_suggestion_for_duplicates(fuzzy_sug, catalog_datasets)
    assert fuzzy_res.has_potential_matches
    assert not fuzzy_res.is_duplicate, "Fuzzy match must be a warning, not automatic rejection"

    # 5. Malicious issue content (containment check)
    dirty_body = "### Dataset name\n$(whoami) <script>alert(1)</script>; rm -rf /\n### Official dataset URL\nhttps://safe.org\n### Modality, task, and usefulness\n**Description:** Valid description of at least ten characters."
    code_mal, res_mal, _ = process_suggestion(raw_body=dirty_body)
    assert code_mal == 0
    assert "/" not in res_mal["slug"]
    assert ";" not in res_mal["slug"]

    # 6. Unsupported issue types
    code_u, res_u, rep_u = process_suggestion(raw_body="### Describe the bug\nBug in website\n", issue_number=50)
    assert code_u == 0
    assert res_u["status"] == "unsupported"
    assert "Non-Dataset Suggestion" in rep_u

    # 7. Provisional verification status
    draft = generate_draft_metadata(ParsedSuggestion(
        name="Provisional Check Dataset",
        source_url="https://prov.org/data",
        category="Vision",
        task="Classification",
        description="A valid benchmark dataset description for testing provisional status rules.",
    ))
    assert draft["verification"]["status"] == "provisional"
    assert draft["verification"]["verified_by"] is None

    # 8. Unknown licenses
    assert draft["license"]["status"] == "unknown"
    assert draft["license"]["commercial_use"] == "unknown"

    # 9. GitHub event payload handling
    event_payload = {
        "action": "opened",
        "issue": {
            "number": 300,
            "title": "[Dataset]: Check Event",
            "body": valid_body,
        },
    }
    from scripts.process_suggestion import extract_issue_data_from_event
    import tempfile
    with tempfile.NamedTemporaryFile("w+", encoding="utf-8", suffix=".json") as f:
        json.dump(event_payload, f)
        f.flush()
        body_ev, num_ev, _ = extract_issue_data_from_event(Path(f.name))
        assert num_ev == 300
        assert "Marine Debris Optical Benchmark" in body_ev
