"""Unit and integration tests for scripts/repo_health.py (Phase 0).

Ensures robust metric collection, license review candidate detection, partition
arithmetic classification, formatting detection, artifact calculation, and CLI reporting
across temporary fixture repositories.

Does NOT hard-code production catalog counts to maintain robustness under future expansions.
Does NOT require network access or live DOI resolution.
"""

from __future__ import annotations

import gzip
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from scripts.repo_health import (
    HISTORICAL_BASELINE,
    SCHEMA_VERSION,
    Finding,
    build_health_report,
    build_historical_comparison,
    check_frontend_matches_category,
    collect_automation_metrics,
    collect_catalog_health,
    collect_formatting_metrics,
    collect_frontend_metrics,
    collect_generated_artifact_metrics,
    collect_license_metrics,
    collect_repository_metadata,
    collect_sample_count_metrics,
    collect_source_monitoring_metrics,
    collect_taxonomy_metrics,
    collect_test_metrics,
    compact_report_for_budget,
    generate_minimal_bounded_report,
    main,
    render_json_report,
    render_markdown_report,
    render_minimal_markdown_report,
)


# ---------------------------------------------------------------------------
# Fixture Helpers
# ---------------------------------------------------------------------------

def create_mock_dataset(
    dataset_id: str,
    slug: str | None = None,
    name: str | None = None,
    modalities: list[str] | None = None,
    tasks: list[str] | None = None,
    tags: list[str] | None = None,
    license_status: str = "verified_open",
    license_spdx: str = "MIT",
    commercial_use: str = "allowed",
    sample_total: int = 1000,
    sample_unit: str = "samples",
    splits: dict[str, int] | None = None,
    partition_completeness: str = "complete",
    partition_overlap: str = "disjoint",
    missing_newline: bool = False,
    homepage_url: str = "https://example.org/dataset",
) -> dict[str, Any]:
    """Generate a valid schema-compliant dataset dictionary for testing."""
    if slug is None:
        slug = dataset_id
    if name is None:
        name = f"Dataset {dataset_id}"
    if modalities is None:
        modalities = ["vision"]
    if tasks is None:
        tasks = ["image-classification"]
    if tags is None:
        tags = ["benchmark", "cv"]
    if splits is None:
        splits = {"train": 800, "test": 200}

    return {
        "schema_version": "1.0",
        "id": dataset_id,
        "slug": slug,
        "name": name,
        "description": f"Standard test description for {dataset_id}.",
        "homepage_url": homepage_url,
        "publisher": {
            "name": "Test Lab",
            "type": "academic",
            "url": "https://example.org/lab",
        },
        "modalities": modalities,
        "tasks": tasks,
        "tags": tags,
        "license": {
            "name": "MIT License",
            "status": license_status,
            "spdx_id": license_spdx,
            "commercial_use": commercial_use,
            "url": "https://opensource.org/licenses/MIT",
        },
        "source_references": [
            {
                "url": "https://example.org/download",
                "kind": "download",
            }
        ],
        "verification": {
            "status": "verified",
            "date": "2026-01-01",
            "verified_by": "test-curator",
        },
        "citation": {
            "paper_title": f"Paper for {dataset_id}",
            "paper_url": "https://example.org/paper",
            "doi": "10.1000/182",
        },
        "dates": {
            "published": "2024-01-01",
        },
        "sample_count": {
            "total": sample_total,
            "unit": sample_unit,
            "splits": splits,
            "partition_completeness": partition_completeness,
            "partition_overlap": partition_overlap,
        },
        "size": {
            "amount": 100,
            "unit": "MB",
        },
    }


def write_fixture_repo(tmp_path: Path, datasets: list[dict[str, Any]], trailing_newlines: dict[str, bool] | None = None) -> Path:
    """Populate a temporary directory with repository layout and dataset JSON files."""
    datasets_dir = tmp_path / "data" / "datasets"
    datasets_dir.mkdir(parents=True, exist_ok=True)

    if trailing_newlines is None:
        trailing_newlines = {}

    for idx, d in enumerate(datasets):
        did = d["id"]
        # Use unique filenames even if dataset IDs collide
        file_path = datasets_dir / f"{did}_{idx}.json"
        content = json.dumps(d, indent=2)
        has_newline = trailing_newlines.get(did, True)
        if has_newline:
            content += "\n"
        with open(file_path, "wb") as f:
            f.write(content.encode("utf-8"))

    # Create dummy catalog.json
    cat_dir = tmp_path / "frontend" / "public" / "data"
    cat_dir.mkdir(parents=True, exist_ok=True)
    cat_path = cat_dir / "catalog.json"
    cat_path.write_text(json.dumps(datasets, indent=2) + "\n", encoding="utf-8")

    # Create dummy workflows
    wf_dir = tmp_path / ".github" / "workflows"
    wf_dir.mkdir(parents=True, exist_ok=True)
    (wf_dir / "ci.yml").write_text("name: CI\non: push\njobs:\n  build:\n    runs-on: ubuntu-latest\n")

    return tmp_path


# ---------------------------------------------------------------------------
# Test Cases
# ---------------------------------------------------------------------------

def test_empty_repository(tmp_path: Path):
    """Test health reporting on an empty directory structure."""
    report = build_health_report(tmp_path)
    assert report["report_schema_version"] == SCHEMA_VERSION
    assert report["catalog"]["total_records"] == 0
    assert report["catalog"]["parsed_records"] == 0
    assert report["sample_counts"]["sample_count_records"] == 0
    assert report["taxonomy"]["distinct_tasks_count"] == 0


def test_valid_dataset_parsing(tmp_path: Path):
    """Test standard parsing and metric aggregation across valid fixture datasets."""
    d1 = create_mock_dataset("dataset-a", modalities=["vision"], tasks=["image-classification"])
    d2 = create_mock_dataset("dataset-b", modalities=["nlp"], tasks=["text-generation"], tags=["llm"])
    repo_dir = write_fixture_repo(tmp_path, [d1, d2])

    metrics, findings, records = collect_catalog_health(repo_dir)
    assert metrics["total_records"] == 2
    assert metrics["parsed_records"] == 2
    assert metrics["invalid_json_records"] == 0
    assert metrics["duplicate_exact_ids"] == 0
    assert metrics["citation_coverage"] == 2
    assert metrics["doi_coverage"] == 2
    assert metrics["publication_date_coverage"] == 2
    assert len(findings) == 0


def test_invalid_json_handling(tmp_path: Path):
    """Test detection and finding creation for malformed JSON files."""
    datasets_dir = tmp_path / "data" / "datasets"
    datasets_dir.mkdir(parents=True, exist_ok=True)
    (datasets_dir / "valid.json").write_text('{"id": "valid"}\n')
    (datasets_dir / "malformed.json").write_text('{"id": "malformed",\n')  # trailing comma, syntax error

    metrics, findings, records = collect_catalog_health(tmp_path)
    assert metrics["total_records"] == 2
    assert metrics["parsed_records"] == 1
    assert metrics["invalid_json_records"] == 1
    assert "malformed.json" in metrics["invalid_json_files"]
    assert any(f.id == "FINDING-CAT-001" and f.severity == "error" for f in findings)


def test_duplicate_id_and_slug_detection(tmp_path: Path):
    """Test collision detection on exact and case/punctuation normalized IDs."""
    d1 = create_mock_dataset("dataset_one", slug="dataset-one")
    d2 = create_mock_dataset("dataset-one", slug="dataset_one")  # Normalized collision with d1
    d3 = create_mock_dataset("dataset_one", slug="dataset-three")  # Exact ID collision with d1
    repo_dir = write_fixture_repo(tmp_path, [d1, d2, d3])

    metrics, findings, _ = collect_catalog_health(repo_dir)
    assert metrics["total_records"] == 3
    assert metrics["duplicate_exact_ids"] >= 1
    assert metrics["duplicate_normalized_ids"] >= 1
    assert any(f.id == "FINDING-CAT-002" for f in findings)


def test_missing_required_fields(tmp_path: Path):
    """Test flagging of records that omit core schema v1 required fields."""
    d = create_mock_dataset("incomplete-dataset")
    del d["description"]
    del d["homepage_url"]
    repo_dir = write_fixture_repo(tmp_path, [d])

    metrics, findings, _ = collect_catalog_health(repo_dir)
    assert "description" in metrics["missing_required_fields"]
    assert "homepage_url" in metrics["missing_required_fields"]
    assert any("DESCRIPTION" in f.id for f in findings)


def test_license_consistency_classification(tmp_path: Path):
    """Test classification of verified_open vs non-commercial vs permissive unknown."""
    # 1. Non-commercial SPDX classified as verified_open (review candidate)
    d1 = create_mock_dataset("anli-test", license_status="verified_open", license_spdx="CC-BY-NC-4.0", commercial_use="forbidden")
    # 2. Permissive SPDX with unknown commercial use (review candidate)
    d2 = create_mock_dataset("desed-test", license_status="custom_permissive", license_spdx="MIT", commercial_use="unknown")
    # 3. Clean permissive open
    d3 = create_mock_dataset("clean-open", license_status="verified_open", license_spdx="Apache-2.0", commercial_use="allowed")

    records = {"d1.json": d1, "d2.json": d2, "d3.json": d3}
    lic_metrics, findings = collect_license_metrics(records)

    assert lic_metrics["spdx_identifier_coverage"] == 3
    assert lic_metrics["missing_spdx_count"] == 0
    assert lic_metrics["unknown_commercial_use_count"] == 1
    assert lic_metrics["review_candidates_count"] == 2

    types = [c["type"] for c in lic_metrics["review_candidates"]]
    assert "non_commercial_spdx_verified_open" in types
    assert "permissive_spdx_commercial_unknown" in types
    assert any(f.id == "FINDING-LIC-001" and f.status == "review_required" for f in findings)


def test_sample_count_partition_consistency(tmp_path: Path):
    """Test distinguishing raw arithmetic discrepancies vs actionable complete+disjoint errors."""
    # Case 1: Complete and disjoint with exact sum match -> PASS
    d1 = create_mock_dataset(
        "exact-match",
        sample_total=1000,
        splits={"train": 800, "test": 200},
        partition_completeness="complete",
        partition_overlap="disjoint",
    )
    # Case 2: Unspecified completeness/overlap with mismatch -> Raw discrepancy, NOT hard error
    d2 = create_mock_dataset(
        "legacy-unspecified-mismatch",
        sample_total=1000,
        splits={"train": 700, "test": 200},
        partition_completeness="unspecified",
        partition_overlap="unspecified",
    )
    # Case 3: Complete and disjoint with mismatch -> ACTIONABLE HARD ERROR
    d3 = create_mock_dataset(
        "actionable-contradiction",
        sample_total=1000,
        splits={"train": 800, "test": 150},
        partition_completeness="complete",
        partition_overlap="disjoint",
    )
    # Case 4: Missing unit
    d4 = create_mock_dataset("missing-unit", sample_unit="")

    records = {"d1.json": d1, "d2.json": d2, "d3.json": d3, "d4.json": d4}
    sc_metrics, findings = collect_sample_count_metrics(records)

    assert sc_metrics["sample_count_records"] == 4
    assert sc_metrics["missing_unit_count"] == 1
    assert sc_metrics["raw_arithmetic_discrepancy_count"] == 2  # d2 and d3
    assert sc_metrics["actionable_consistency_concerns"] == 1    # d3 only

    finding_ids = [f.id for f in findings]
    assert "FINDING-SC-001" in finding_ids  # raw discrepancy info
    assert "FINDING-SC-002" in finding_ids  # missing unit warning
    assert "FINDING-SC-003" in finding_ids  # actionable error


def test_taxonomy_singletons_and_punctuation_duplicates():
    """Test singleton counting and detection of punctuation-variant taxonomy tags."""
    # qa appears in d1 and d2 (count 2), common-task appears in d1 and d3 (count 2)
    # singleton-task appears only in d3 (count 1)
    d1 = create_mock_dataset("d1", tasks=["multi-class-classification", "qa", "common-task"], tags=["multi-channel-audio", "shared-tag"])
    d2 = create_mock_dataset("d2", tasks=["multiclass-classification", "qa"], tags=["multichannel-audio", "shared-tag"])
    d3 = create_mock_dataset("d3", tasks=["singleton-task", "common-task"], tags=["singleton-tag", "shared-tag"])

    records = {"d1.json": d1, "d2.json": d2, "d3.json": d3}
    tax_metrics, findings = collect_taxonomy_metrics(records)

    assert tax_metrics["distinct_tasks_count"] == 5
    # singletons are: multi-class-classification (1), multiclass-classification (1), singleton-task (1) -> 3 singletons
    assert tax_metrics["singleton_tasks_count"] == 3
    # singletons tags are: multi-channel-audio (1), multichannel-audio (1), singleton-tag (1) -> 3 singletons
    assert tax_metrics["singleton_tags_count"] == 3

    # Punctuation duplicate candidates
    assert "multiclassclassification" in tax_metrics["punctuation_duplicate_tasks"]
    assert "multichannelaudio" in tax_metrics["punctuation_duplicate_tags"]


def test_frontend_category_matching():
    """Test mapping of datasets to frontend research discovery categories."""
    cv_set = create_mock_dataset("cv-set", modalities=["vision"])
    nlp_set = create_mock_dataset("nlp-set", modalities=["nlp"])
    audio_set = create_mock_dataset("audio-set", modalities=["audio"])
    tabular_set = create_mock_dataset("tab-set", modalities=["tabular"])
    multi_set = create_mock_dataset("multi-set", modalities=["multimodal"])
    bench_set = create_mock_dataset("bench-set", modalities=["other"], tags=["ogb-benchmark"], tasks=["evaluation"])
    uncat_set = create_mock_dataset("uncat-set", modalities=["other"], tags=["music"], tasks=["generation"])

    assert check_frontend_matches_category(cv_set, "computer-vision") is True
    assert check_frontend_matches_category(nlp_set, "natural-language-processing") is True
    assert check_frontend_matches_category(audio_set, "audio-speech") is True
    assert check_frontend_matches_category(tabular_set, "tabular-time-series") is True
    assert check_frontend_matches_category(multi_set, "multimodal-generative") is True
    assert check_frontend_matches_category(bench_set, "evaluation-benchmarks") is True
    assert check_frontend_matches_category(uncat_set, "computer-vision") is False
    assert check_frontend_matches_category(uncat_set, "evaluation-benchmarks") is False

    records = {"uncat.json": uncat_set, "cv.json": cv_set}
    tax_metrics, findings = collect_taxonomy_metrics(records)
    assert tax_metrics["uncategorized_datasets_count"] == 1
    assert "uncat-set" in tax_metrics["uncategorized_datasets"]
    assert any(f.id == "FINDING-TAX-001" for f in findings)


def test_formatting_metrics_and_http_urls(tmp_path: Path):
    """Test detection of missing trailing newlines, plain HTTP URLs, and 45-character slugs."""
    # d1 has trailing newline, https URLs
    d1 = create_mock_dataset("d1", homepage_url="https://secure.example.org")
    # d2 lacks trailing newline, has plain http URL, and 45-character slug
    long_slug = "a" * 45
    d2 = create_mock_dataset("d2", slug=long_slug, homepage_url="http://insecure.example.org/dataset")

    repo_dir = write_fixture_repo(tmp_path, [d1, d2], trailing_newlines={"d1": True, "d2": False})
    records = {"d1.json": d1, "d2.json": d2}

    fmt_metrics, findings = collect_formatting_metrics(repo_dir, records)
    assert fmt_metrics["missing_trailing_newline_count"] == 1
    assert any(fn.startswith("d2") for fn in fmt_metrics["missing_trailing_newline_files"])
    assert fmt_metrics["plain_http_url_occurrences"] >= 1
    assert fmt_metrics["suspected_truncated_slugs_count"] == 1
    assert any(f.id == "FINDING-FMT-001" for f in findings)
    assert any(f.id == "FINDING-FMT-002" for f in findings)
    assert any(f.id == "FINDING-FMT-003" for f in findings)


def test_generated_artifact_metrics(tmp_path: Path):
    """Test raw size, deterministic gzip compression, and SHA-256 calculation."""
    cat_dir = tmp_path / "frontend" / "public" / "data"
    cat_dir.mkdir(parents=True, exist_ok=True)
    test_json = json.dumps([{"id": "item1"}, {"id": "item2"}], indent=2)
    cat_file = cat_dir / "catalog.json"
    cat_file.write_text(test_json, encoding="utf-8")

    art_metrics, findings = collect_generated_artifact_metrics(tmp_path)
    cat_res = art_metrics["catalog_json"]
    assert cat_res["exists"] is True
    assert cat_res["size_bytes"] == len(test_json.encode("utf-8"))
    assert cat_res["gzip_bytes"] > 0
    assert len(cat_res["sha256"]) == 64

    # Verify deterministic gzip output
    deterministic_gz = gzip.compress(test_json.encode("utf-8"), compresslevel=9, mtime=0)
    assert cat_res["gzip_bytes"] == len(deterministic_gz)


def test_source_monitoring_cycle_calculation():
    """Test URL extraction and monitoring cycle calculation based on batch size 50."""
    d1 = create_mock_dataset(
        "d1",
        homepage_url="https://example.org/home1",
    )
    d1["source_references"] = [
        {"url": "https://example.org/src1"},
        {"url": "https://doi.org/10.1000/1"},
    ]
    records = {"d1.json": d1}

    src_metrics, findings = collect_source_monitoring_metrics(Path("/nonexistent"), records)
    assert src_metrics["unique_urls_count"] >= 3
    assert src_metrics["batch_size"] == 50
    assert src_metrics["frequency"] == "weekly"
    assert src_metrics["estimated_cycle_weeks"] == round(src_metrics["unique_urls_count"] / 50, 2)


def test_historical_comparison_builder():
    """Test alignment of historical Issue #65 numbers with report metrics."""
    mock_report = {
        "catalog": {"total_records": 875},
        "licenses": {"review_candidates_count": 11},
        "sample_counts": {"raw_arithmetic_discrepancy_count": 29},
        "taxonomy": {
            "distinct_tasks_count": 704,
            "singleton_tasks_count": 447,
            "distinct_tags_count": 1981,
            "singleton_tags_count": 1407,
            "uncategorized_datasets_count": 1,
        },
        "formatting": {
            "suspected_truncated_slugs_count": 22,
            "missing_trailing_newline_count": 39,
            "plain_http_url_occurrences": 78,
            "unique_plain_http_urls": 42,
        },
        "generated_artifacts": {
            "catalog_json": {"size_mb_decimal": 3.39, "gzip_kb_decimal": 727.0},
            "audit_reports": {"total_mb_decimal": 4.06},
        },
        "tests": {"passed": 240, "duration_seconds": None},
        "source_monitoring": {"estimated_cycle_weeks": 52.34},
    }

    rows = build_historical_comparison(mock_report)
    assert len(rows) == len(HISTORICAL_BASELINE)
    lookup = {r["metric"]: r for r in rows}

    assert lookup["Catalog dataset count"]["current"] == "875"
    assert lookup["Catalog dataset count"]["difference"] == "0"
    assert lookup["Distinct taxonomy tasks"]["current"] == "704"
    assert lookup["Distinct taxonomy tasks"]["difference"] == "0"
    assert lookup["Sample count raw sum mismatch"]["current"] == "29"
    assert lookup["Sample count raw sum mismatch"]["difference"] == "0"


def test_json_and_markdown_rendering(tmp_path: Path):
    """Test deterministic JSON serialization and Markdown section generation."""
    d = create_mock_dataset("dataset-render")
    repo_dir = write_fixture_repo(tmp_path, [d])

    report = build_health_report(repo_dir)
    json_output = render_json_report(report)
    md_output = render_markdown_report(report)

    # Validate JSON
    parsed = json.loads(json_output)
    assert parsed["report_schema_version"] == "1.0"
    assert parsed["catalog"]["total_records"] == 1
    assert "findings" in parsed
    assert "limitations" in parsed

    # Validate Markdown sections
    assert "# OpenDatasets Repository Health Report" in md_output
    assert "## Executive Summary" in md_output
    assert "## Catalog Health" in md_output
    assert "## Licensing Consistency" in md_output
    assert "## Sample-Count Consistency" in md_output
    assert "## Taxonomy Health" in md_output
    assert "## Formatting and Metadata Hygiene" in md_output
    assert "## Generated Artifact Sizes" in md_output
    assert "## Comparison With Issue #65 Historical Baseline" in md_output
    assert "## Prioritized Improvement Candidates" in md_output
    assert "## Limitations" in md_output


def test_cli_execution_with_output_files(tmp_path: Path):
    """Test CLI arguments handling, exit code, and file output generation."""
    d = create_mock_dataset("cli-test")
    repo_dir = write_fixture_repo(tmp_path, [d])

    json_path = tmp_path / "out-health.json"
    md_path = tmp_path / "out-health.md"

    exit_code = main([
        "--repo-root", str(repo_dir),
        "--json-output", str(json_path),
        "--markdown-output", str(md_path),
        "--format", "summary",
        "--quiet",
    ])

    assert exit_code == 0
    assert json_path.exists()
    assert md_path.exists()
    assert json_path.stat().st_size > 0
    assert md_path.stat().st_size > 0


def test_test_metrics_skipped_by_default(tmp_path: Path):
    """Ensure expensive test checks remain skipped by default."""
    d = create_mock_dataset("skip-test")
    repo_dir = write_fixture_repo(tmp_path, [d])

    report = build_health_report(repo_dir, run_tests=False, benchmark=False)
    assert report["tests"]["status"] == "skipped"
    assert report["tests"]["passed"] is None
    assert report["tests"]["duration_seconds"] is None


def test_subprocess_failure_handling(tmp_path: Path):
    """Ensure metric collectors gracefully survive failed external commands (e.g. git)."""
    with patch("subprocess.run", side_effect=OSError("Command 'git' not found")):
        meta = collect_repository_metadata(tmp_path)
        assert meta["commit_sha"] == "unknown"
        assert meta["working_tree_status"] == "unknown"


def test_findings_deterministic_ordering(tmp_path: Path):
    """Ensure all findings are deterministically sorted by finding ID."""
    d1 = create_mock_dataset("d1", sample_unit="")  # FINDING-SC-002
    d2 = create_mock_dataset("d2", license_spdx="CC-BY-NC-4.0", license_status="verified_open")  # FINDING-LIC-001
    repo_dir = write_fixture_repo(tmp_path, [d1, d2])

    report = build_health_report(repo_dir)
    findings = report["findings"]
    ids = [f["id"] for f in findings]
    assert ids == sorted(ids)


def test_validation_flag_execution(tmp_path: Path):
    """Test optional validation execution via build_health_report."""
    d = create_mock_dataset("val-test")
    repo_dir = write_fixture_repo(tmp_path, [d])

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="All datasets valid\n", stderr="")
        # Create a mock validate_datasets.py
        scripts_dir = repo_dir / "scripts"
        scripts_dir.mkdir(parents=True, exist_ok=True)
        (scripts_dir / "validate_datasets.py").write_text("# mock\n")

        report = build_health_report(repo_dir, run_validation=True)
        assert report["validation"]["status"] == "passed"
        assert report["validation"]["returncode"] == 0


def test_cli_exit_code_propagation_and_report_preservation(tmp_path: Path):
    """Test CLI exit-code semantics: 0 on success, 1 on failure, outputs preserved on error."""
    d = create_mock_dataset("exit-code-test")
    repo_dir = write_fixture_repo(tmp_path, [d])

    json_out = tmp_path / "diag.json"
    md_out = tmp_path / "diag.md"

    # 1. Default run with no extra flags succeeds (code 0)
    ret_ok = main([
        "--repo-root", str(repo_dir),
        "--json-output", str(json_out),
        "--markdown-output", str(md_out),
        "--quiet",
    ])
    assert ret_ok == 0
    assert json_out.exists()
    assert md_out.exists()

    # 2. Validation failure returns exit code 1 AND preserves output reports
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="Validation error\n")
        scripts_dir = repo_dir / "scripts"
        scripts_dir.mkdir(parents=True, exist_ok=True)
        (scripts_dir / "validate_datasets.py").write_text("# mock\n")

        json_fail = tmp_path / "fail_val.json"
        md_fail = tmp_path / "fail_val.md"

        ret_val_fail = main([
            "--repo-root", str(repo_dir),
            "--run-validation",
            "--json-output", str(json_fail),
            "--markdown-output", str(md_fail),
            "--quiet",
        ])
        assert ret_val_fail == 1
        assert json_fail.exists()
        assert md_fail.exists()
        # Ensure diagnostic reports were written and contain the failed status
        val_data = json.loads(json_fail.read_text(encoding="utf-8"))
        assert val_data["validation"]["status"] == "failed"

    # 3. Test execution failure returns exit code 1 AND preserves output reports
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=1, stdout="1 failed\n", stderr="")
        json_test_fail = tmp_path / "fail_test.json"
        md_test_fail = tmp_path / "fail_test.md"

        ret_test_fail = main([
            "--repo-root", str(repo_dir),
            "--run-tests",
            "--json-output", str(json_test_fail),
            "--markdown-output", str(md_test_fail),
            "--quiet",
        ])
        assert ret_test_fail == 1
        assert json_test_fail.exists()
        assert md_test_fail.exists()
        test_data = json.loads(json_test_fail.read_text(encoding="utf-8"))
        assert test_data["tests"]["status"] == "failed"


def test_dynamic_markdown_recommendations_and_metrics(tmp_path: Path):
    """Ensure Markdown recommendations dynamically reflect fixture data rather than hard-coded constants."""
    # Fixture A: 1 missing newline, 1 HTTP URL, 2 singleton tasks, 1 license candidate
    # sharedA in both d1 and d2; taskA and taskB in d1 only (2 singletons)
    # commercial_use="forbidden" so CC-BY-NC-4.0 only triggers rule 1 (1 candidate)
    d1 = create_mock_dataset("fixA-d1", tasks=["taskA", "taskB", "sharedA"], homepage_url="http://insecure1.org", license_status="verified_open", license_spdx="CC-BY-NC-4.0", commercial_use="forbidden")
    d2 = create_mock_dataset("fixA-d2", tasks=["sharedA"], homepage_url="https://secure.org")
    repo_A = tmp_path / "repoA"
    write_fixture_repo(repo_A, [d1, d2], trailing_newlines={"fixA-d1": False, "fixA-d2": True})

    report_A = build_health_report(repo_A)
    md_A = render_markdown_report(report_A)

    assert "Normalize 1 missing newlines, verify 1 plain HTTP URLs, harmonize 2 singleton tasks, resolve 1 license review candidates" in md_A
    assert "39 missing newlines" not in md_A
    assert "447 singleton tasks" not in md_A
    assert "11 license review candidates" not in md_A

    # Fixture B: 2 missing newlines, 2 HTTP URLs, 3 singleton tasks, 2 license candidates
    d3 = create_mock_dataset("fixB-d3", tasks=["taskX", "common"], homepage_url="http://insecure2.org", license_status="verified_open", license_spdx="CC-BY-NC-4.0", commercial_use="forbidden")
    d4 = create_mock_dataset("fixB-d4", tasks=["taskY", "common"], homepage_url="http://insecure3.org", license_status="verified_open", license_spdx="CC-BY-NC-4.0", commercial_use="forbidden")
    d5 = create_mock_dataset("fixB-d5", tasks=["taskZ", "common"], homepage_url="https://secure.org")
    repo_B = tmp_path / "repoB"
    write_fixture_repo(repo_B, [d3, d4, d5], trailing_newlines={"fixB-d3": False, "fixB-d4": False, "fixB-d5": True})

    report_B = build_health_report(repo_B)
    md_B = render_markdown_report(report_B)

    assert "Normalize 2 missing newlines, verify 2 plain HTTP URLs, harmonize 3 singleton tasks, resolve 2 license review candidates" in md_B


def test_report_budget_fallback_execution(tmp_path: Path):
    """Test bounded compact fallback when combined report size exceeds configured byte budget but fits in compact mode."""
    # Create sufficient records so truncating affected_records and singletons achieves significant byte reduction
    datasets = [
        create_mock_dataset(
            f"record-budget-compact-test-{i}",
            tasks=[f"unique-singleton-task-identifier-{i}"],
            homepage_url=f"http://insecure-test-host-{i}.org/resource",
        )
        for i in range(60)
    ]
    repo_dir = write_fixture_repo(tmp_path, datasets, trailing_newlines={f"record-budget-compact-test-{i}": False for i in range(60)})

    # Measure actual sizes for deterministic threshold calculation
    raw_rep = build_health_report(repo_dir)
    full_bytes = len(render_json_report(raw_rep).encode("utf-8")) + len(render_markdown_report(raw_rep).encode("utf-8"))
    c_rep = compact_report_for_budget(raw_rep, full_bytes, full_bytes - 500)
    compact_bytes = len(render_json_report(c_rep).encode("utf-8")) + len(render_markdown_report(c_rep).encode("utf-8"))

    # Verify that compaction reduced the byte size
    assert compact_bytes < full_bytes

    # Set budget strictly between compact_bytes and full_bytes to trigger Tier 1 compact fallback
    target_budget = compact_bytes + 200
    assert target_budget < full_bytes

    json_path = tmp_path / "budget_report.json"
    md_path = tmp_path / "budget_report.md"

    exit_code = main([
        "--repo-root", str(repo_dir),
        "--json-output", str(json_path),
        "--markdown-output", str(md_path),
        "--max-report-bytes", str(target_budget),
        "--quiet",
    ])

    assert exit_code == 0
    assert json_path.exists()
    assert md_path.exists()

    # Verify JSON is valid and parseable
    content = json_path.read_text(encoding="utf-8")
    parsed = json.loads(content)
    assert parsed["budget_fallback"]["budget_exceeded"] is True
    assert parsed["budget_fallback"]["original_combined_bytes"] == full_bytes
    assert len(parsed["budget_fallback"]["omitted_details"]) > 0
    # Core health metrics preserved
    assert parsed["catalog"]["total_records"] == 60
    assert parsed["report_schema_version"] == "1.0"

    # Verify Markdown contains the warning banner
    md_content = md_path.read_text(encoding="utf-8")
    assert "> [!WARNING]" in md_content
    assert "**Report Budget Exceeded**" in md_content


def test_budget_minimal_fallback_and_safe_suppression(tmp_path: Path):
    """Test Tier 2 (minimal bounded fallback) and Tier 3 (safe suppression when even minimal exceeds budget)."""
    d = create_mock_dataset("budget-tier-test")
    repo_dir = write_fixture_repo(tmp_path, [d])

    raw_rep = build_health_report(repo_dir)
    full_bytes = len(render_json_report(raw_rep).encode("utf-8")) + len(render_markdown_report(raw_rep).encode("utf-8"))
    c_rep = compact_report_for_budget(raw_rep, full_bytes, 1000)
    compact_bytes = len(render_json_report(c_rep).encode("utf-8")) + len(render_markdown_report(c_rep).encode("utf-8"))

    min_rep = generate_minimal_bounded_report(raw_rep, full_bytes, 1500)
    min_bytes = len(render_json_report(min_rep).encode("utf-8")) + len(render_minimal_markdown_report(min_rep).encode("utf-8"))

    # 1. Tier 2: Budget between min_bytes and compact_bytes triggers minimal bounded fallback
    tier2_budget = min_bytes + 200
    assert tier2_budget < compact_bytes

    json_min = tmp_path / "min_report.json"
    md_min = tmp_path / "min_report.md"

    ret_tier2 = main([
        "--repo-root", str(repo_dir),
        "--json-output", str(json_min),
        "--markdown-output", str(md_min),
        "--max-report-bytes", str(tier2_budget),
        "--quiet",
    ])

    assert ret_tier2 == 0
    assert json_min.exists()
    assert md_min.exists()

    parsed_min = json.loads(json_min.read_text(encoding="utf-8"))
    assert parsed_min["budget_fallback"]["minimal_fallback"] is True
    assert parsed_min["catalog"]["total_records"] == 1
    assert "Minimal Bounded Summary" in md_min.read_text(encoding="utf-8")

    # 2. Tier 3: Budget below min_bytes fails safely (exit code 2) without writing oversized artifacts
    json_fail = tmp_path / "fail_report.json"
    md_fail = tmp_path / "fail_report.md"
    json_fail.write_text("pre-existing oversized artifact\n", encoding="utf-8")
    md_fail.write_text("pre-existing oversized artifact\n", encoding="utf-8")

    ret_tier3 = main([
        "--repo-root", str(repo_dir),
        "--json-output", str(json_fail),
        "--markdown-output", str(md_fail),
        "--max-report-bytes", "50",
        "--quiet",
    ])

    assert ret_tier3 == 2
    # Pre-existing oversized files must be purged to prevent accidental upload
    assert not json_fail.exists()
    assert not md_fail.exists()


def test_historical_comparison_pytest_count_when_tests_skipped_or_unavailable():
    """Verify that 240 is retained exclusively as historical baseline and current is skipped/unavailable when not run."""
    # 1. Tests skipped
    skipped_rep = {
        "catalog": {"total_records": 875},
        "licenses": {"review_candidates_count": 0},
        "sample_counts": {"raw_arithmetic_discrepancy_count": 0},
        "taxonomy": {"distinct_tasks_count": 704, "singleton_tasks_count": 447, "distinct_tags_count": 1981, "singleton_tags_count": 1407},
        "formatting": {"missing_trailing_newline_count": 39, "suspected_truncated_slugs_count": 22},
        "generated_artifacts": {"catalog_json": {}, "audit_reports": {}},
        "tests": {"status": "skipped", "passed": None, "duration_seconds": None},
        "source_monitoring": {"estimated_cycle_weeks": 52.34},
    }
    rows_skip = build_historical_comparison(skipped_rep)
    lookup_skip = {r["metric"]: r for r in rows_skip}
    assert lookup_skip["Python unit tests (count)"]["historical"] == "240"
    assert lookup_skip["Python unit tests (count)"]["current"] == "Skipped in fast default"
    assert lookup_skip["Python unit tests (count)"]["difference"] == "N/A"

    # 2. Tests error/unavailable
    error_rep = dict(skipped_rep)
    error_rep["tests"] = {"status": "error", "passed": None, "duration_seconds": None}
    rows_err = build_historical_comparison(error_rep)
    lookup_err = {r["metric"]: r for r in rows_err}
    assert lookup_err["Python unit tests (count)"]["historical"] == "240"
    assert lookup_err["Python unit tests (count)"]["current"] == "Unavailable"
    assert lookup_err["Python unit tests (count)"]["difference"] == "N/A"

    # 3. Tests executed and passed (263)
    pass_rep = dict(skipped_rep)
    pass_rep["tests"] = {"status": "passed", "passed": 263, "duration_seconds": 12.34}
    rows_pass = build_historical_comparison(pass_rep)
    lookup_pass = {r["metric"]: r for r in rows_pass}
    assert lookup_pass["Python unit tests (count)"]["historical"] == "240"
    assert lookup_pass["Python unit tests (count)"]["current"] == "263"
    assert lookup_pass["Python unit tests (count)"]["difference"] == "+23"


def test_compaction_preserves_summary_counts_and_execution_status():
    """Ensure report compaction preserves all summary counts, execution statuses, and historical comparisons."""
    finding_obj = Finding(
        id="FINDING-TEST-001",
        category="testing",
        severity="warning",
        status="review_required",
        title="Test Finding",
        description="Detailed finding description",
        affected_records=["rec1", "rec2", "rec3", "rec4", "rec5"],
    )

    full_rep = {
        "report_schema_version": "1.0",
        "repository": {"repository_name": "OpenDatasets", "commit_sha": "abc1234", "branch": "main", "working_tree_status": "clean", "report_timestamp": "now", "tracked_dataset_count": 875},
        "catalog": {"total_records": 875, "parsed_records": 875, "invalid_json_records": 0, "citation_coverage": 867, "doi_coverage": 753, "publication_date_coverage": 850, "verification_date_coverage": 875, "homepage_url_coverage": 875, "source_reference_coverage": 875, "sample_count_coverage": 834, "dataset_size_coverage": 468, "nlp_audio_coverage": 175, "nlp_audio_total": 313},
        "licenses": {
            "status_distribution": {"verified_open": 453},
            "commercial_use_distribution": {"allowed": 534},
            "spdx_identifier_coverage": 766,
            "missing_spdx_count": 109,
            "review_candidates_count": 2,
            "non_commercial_spdx_verified_open_count": 1,
            "permissive_spdx_commercial_unknown_count": 1,
            "review_candidates": [
                {"id": "c1", "type": "non_commercial_spdx_verified_open"},
                {"id": "c2", "type": "permissive_spdx_commercial_unknown"},
            ],
        },
        "sample_counts": {
            "sample_count_records": 834,
            "missing_unit_count": 25,
            "splits_coverage": 372,
            "breakdown_coverage": 0,
            "completeness_distribution": {"unspecified": 743},
            "overlap_distribution": {"unspecified": 726},
            "raw_arithmetic_discrepancy_count": 29,
            "actionable_consistency_concerns": 0,
            "raw_discrepancies": [{"id": f"d{i}"} for i in range(29)],
        },
        "taxonomy": {
            "distinct_tasks_count": 704,
            "singleton_tasks_count": 447,
            "distinct_tags_count": 1981,
            "singleton_tags_count": 1407,
            "uncategorized_datasets_count": 1,
            "uncategorized_datasets": ["lakh-midi"],
            "modality_only_uncategorized_count": 16,
            "punctuation_duplicate_tasks": [["taskA", "task-a"]],
            "punctuation_duplicate_tags": [["tagA", "tag-a"]],
            "punctuation_duplicate_tasks_count": 1,
            "punctuation_duplicate_tags_count": 1,
        },
        "formatting": {
            "missing_trailing_newline_count": 39,
            "missing_trailing_newline_files": [f"f{i}" for i in range(39)],
            "plain_http_url_occurrences": 78,
            "unique_plain_http_urls": 42,
            "suspected_truncated_slugs_count": 22,
            "suspected_truncated_slugs": [{"id": f"s{i}"} for i in range(22)],
        },
        "generated_artifacts": {"catalog_json": {"size_mb_decimal": 3.39, "gzip_kb_decimal": 727.0}, "audit_reports": {"total_mb_decimal": 4.06}},
        "tests": {
            "python_test_file_count": 9,
            "catalog_count_dependent_assertions_count": 20,
            "status": "passed",
            "passed": 263,
            "failed": 0,
            "duration_seconds": 15.2,
            "catalog_count_dependent_assertions": ["assert 875"],
        },
        "validation": {"status": "passed", "returncode": 0},
        "source_monitoring": {"estimated_cycle_weeks": 52.34},
        "automation": {"workflow_count": 5, "dependabot_present": False, "codeowners_present": False, "pre_commit_present": False, "python_lockfile_present": False, "npm_engines_configured": False, "nvmrc_present": False},
        "frontend": {"per_route_titles": False, "not_found_route_present": False, "sitemap_present": False, "robots_txt_present": False, "open_graph_tags_present": False, "schema_org_json_ld_present": False},
        "findings": [finding_obj.to_dict()],
        "findings_summary": {"total": 1, "error": 0, "warning": 1, "info": 0},
        "execution": {"duration_seconds": 0.45},
    }

    compacted = compact_report_for_budget(full_rep, original_combined_bytes=50000, max_budget_bytes=10000)

    # Summary counts and statuses must remain identical
    assert compacted["catalog"]["total_records"] == 875
    assert compacted["licenses"]["review_candidates_count"] == 2
    assert compacted["licenses"]["non_commercial_spdx_verified_open_count"] == 1
    assert compacted["licenses"]["permissive_spdx_commercial_unknown_count"] == 1
    assert compacted["sample_counts"]["raw_arithmetic_discrepancy_count"] == 29
    assert compacted["taxonomy"]["distinct_tasks_count"] == 704
    assert compacted["taxonomy"]["singleton_tasks_count"] == 447
    assert compacted["taxonomy"]["punctuation_duplicate_tasks_count"] == 1
    assert compacted["formatting"]["missing_trailing_newline_count"] == 39
    assert compacted["formatting"]["suspected_truncated_slugs_count"] == 22
    assert compacted["tests"]["catalog_count_dependent_assertions_count"] == 20
    assert compacted["tests"]["status"] == "passed"
    assert compacted["tests"]["passed"] == 263
    assert compacted["validation"]["status"] == "passed"
    assert compacted["findings_summary"] == {"total": 1, "error": 0, "warning": 1, "info": 0}

    # Finding affected_records_count preserved despite list truncation
    assert compacted["findings"][0]["affected_records_count"] == 5
    assert len(compacted["findings"][0]["affected_records"]) == 4  # top 3 + omitted notice

    # Historical comparison rows must match byte-for-byte
    hist_full = build_historical_comparison(full_rep)
    hist_compact = build_historical_comparison(compacted)
    assert hist_compact == hist_full


def test_skipped_checks_classification(tmp_path: Path):
    """Ensure skipped optional checks are explicitly marked skipped and do not cause failure."""
    d = create_mock_dataset("skip-check-test")
    repo_dir = write_fixture_repo(tmp_path, [d])

    report = build_health_report(repo_dir, run_validation=False, run_tests=False, benchmark=False)
    assert report["validation"]["status"] == "skipped"
    assert report["validation"]["returncode"] is None
    assert report["tests"]["status"] == "skipped"
    assert report["tests"]["passed"] is None
    assert report["tests"]["failed"] is None


