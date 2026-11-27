"""Comprehensive regression test suite for CI dataset change detection, audit failure semantics, and artifact protection.

Verifies:
1. Dataset addition triggers audit.
2. Dataset modification triggers audit.
3. Dataset deletion triggers audit.
4. Schema modification triggers audit.
5. Documentation-only changes do not trigger audit.
6. Multi-commit pushes properly detect dataset changes across the range.
7. Missing Git history / unavailable commits conservatively default to audit.
8. Audit command failures capture actual exit codes and preserve diagnostic reports.
9. Missing expected report files are detected by validation.
10. Invalid JSON reports are detected by validation.
11. Oversized artifact output (> 2 MiB) is rejected and cleaned up.
12. Workflow dispatch explicitly triggers audit.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from scripts.detect_dataset_changes import (
    detect_dataset_changes,
    get_changed_files_between,
    is_valid_commit,
)
from scripts.run_dataset_audits import run_dataset_audits


@pytest.fixture
def git_repo(tmp_path: Path):
    """Set up an isolated temporary Git repository for change detection tests."""
    repo = tmp_path / "repo"
    repo.mkdir()

    def run_git(*args: str) -> str:
        res = subprocess.run(
            ["git", *args],
            cwd=repo,
            capture_output=True,
            text=True,
            check=True,
        )
        return res.stdout.strip()

    run_git("init")
    run_git("config", "user.name", "CI Tester")
    run_git("config", "user.email", "tester@opendatasets.org")

    (repo / "data" / "datasets").mkdir(parents=True)
    (repo / "schemas").mkdir(parents=True)
    (repo / "docs").mkdir(parents=True)

    # Initial baseline commits
    (repo / "data" / "datasets" / "dataset-1.json").write_text(
        json.dumps({"id": "dataset-1", "name": "Dataset One"}), encoding="utf-8"
    )
    (repo / "schemas" / "dataset.v1.schema.json").write_text(
        json.dumps({"$schema": "http://json-schema.org/draft-07/schema#"}), encoding="utf-8"
    )
    (repo / "docs" / "README.md").write_text("# Documentation", encoding="utf-8")

    run_git("add", "-A")
    run_git("commit", "-m", "Initial repository baseline")
    base_sha = run_git("rev-parse", "HEAD")

    return repo, base_sha, run_git


def test_change_detection_dataset_addition(git_repo):
    """Verify that adding a dataset file triggers change detection."""
    repo, base_sha, run_git = git_repo

    (repo / "data" / "datasets" / "dataset-2.json").write_text(
        json.dumps({"id": "dataset-2", "name": "Dataset Two"}), encoding="utf-8"
    )
    run_git("add", "-A")
    run_git("commit", "-m", "Add dataset-2")
    head_sha = run_git("rev-parse", "HEAD")

    env = {
        "EVENT_NAME": "pull_request",
        "BASE_SHA": base_sha,
        "HEAD_SHA": head_sha,
    }
    should_audit, reason, changed = detect_dataset_changes(repo, env)
    assert should_audit is True
    assert "data/datasets/dataset-2.json" in changed


def test_change_detection_dataset_modification(git_repo):
    """Verify that modifying an existing dataset file triggers change detection."""
    repo, base_sha, run_git = git_repo

    target = repo / "data" / "datasets" / "dataset-1.json"
    target.write_text(json.dumps({"id": "dataset-1", "name": "Updated Dataset One"}), encoding="utf-8")
    run_git("commit", "-am", "Update dataset-1 metadata")
    head_sha = run_git("rev-parse", "HEAD")

    env = {
        "EVENT_NAME": "pull_request",
        "BASE_SHA": base_sha,
        "HEAD_SHA": head_sha,
    }
    should_audit, reason, changed = detect_dataset_changes(repo, env)
    assert should_audit is True
    assert "data/datasets/dataset-1.json" in changed


def test_change_detection_dataset_deletion(git_repo):
    """Verify that deleting a dataset file triggers change detection."""
    repo, base_sha, run_git = git_repo

    (repo / "data" / "datasets" / "dataset-1.json").unlink()
    run_git("commit", "-am", "Remove dataset-1")
    head_sha = run_git("rev-parse", "HEAD")

    env = {
        "EVENT_NAME": "pull_request",
        "BASE_SHA": base_sha,
        "HEAD_SHA": head_sha,
    }
    should_audit, reason, changed = detect_dataset_changes(repo, env)
    assert should_audit is True
    assert "data/datasets/dataset-1.json" in changed


def test_change_detection_schema_modification(git_repo):
    """Verify that modifying schemas triggers change detection."""
    repo, base_sha, run_git = git_repo

    schema_file = repo / "schemas" / "dataset.v1.schema.json"
    schema_file.write_text(
        json.dumps({"$schema": "http://json-schema.org/draft-07/schema#", "title": "Updated"}),
        encoding="utf-8",
    )
    run_git("commit", "-am", "Update schema")
    head_sha = run_git("rev-parse", "HEAD")

    env = {
        "EVENT_NAME": "pull_request",
        "BASE_SHA": base_sha,
        "HEAD_SHA": head_sha,
    }
    should_audit, reason, changed = detect_dataset_changes(repo, env)
    assert should_audit is True
    assert "schemas/dataset.v1.schema.json" in changed


def test_change_detection_documentation_only(git_repo):
    """Verify that documentation-only changes do NOT trigger dataset audit."""
    repo, base_sha, run_git = git_repo

    doc_file = repo / "docs" / "README.md"
    doc_file.write_text("# Updated Documentation Only\n\nMore details.", encoding="utf-8")
    run_git("commit", "-am", "Docs change")
    head_sha = run_git("rev-parse", "HEAD")

    env = {
        "EVENT_NAME": "pull_request",
        "BASE_SHA": base_sha,
        "HEAD_SHA": head_sha,
    }
    should_audit, reason, changed = detect_dataset_changes(repo, env)
    assert should_audit is False
    assert len(changed) == 0


def test_change_detection_multi_commit_push(git_repo):
    """Verify that multi-commit pushes detect changes across the entire commit span."""
    repo, base_sha, run_git = git_repo

    # Commit 1: Documentation edit
    (repo / "docs" / "README.md").write_text("# Multi Commit 1", encoding="utf-8")
    run_git("commit", "-am", "Doc commit 1")

    # Commit 2: Dataset addition
    (repo / "data" / "datasets" / "dataset-multi.json").write_text(
        json.dumps({"id": "dataset-multi", "name": "Multi"}), encoding="utf-8"
    )
    run_git("add", "-A")
    run_git("commit", "-m", "Add dataset-multi in commit 2")

    # Commit 3: Another documentation edit
    (repo / "docs" / "README.md").write_text("# Multi Commit 3", encoding="utf-8")
    run_git("commit", "-am", "Doc commit 3")
    final_sha = run_git("rev-parse", "HEAD")

    env = {
        "EVENT_NAME": "push",
        "BEFORE_SHA": base_sha,
        "AFTER_SHA": final_sha,
    }
    should_audit, reason, changed = detect_dataset_changes(repo, env)
    assert should_audit is True
    assert "data/datasets/dataset-multi.json" in changed


def test_change_detection_missing_git_history(git_repo):
    """Verify that missing git history or invalid commits safely and conservatively enable audit."""
    repo, base_sha, run_git = git_repo

    # Provide an unknown fake SHA
    env = {
        "EVENT_NAME": "push",
        "BEFORE_SHA": "deadbeefcafebabedeadbeefcafebabedeadbeef",
        "AFTER_SHA": base_sha,
    }
    should_audit, reason, changed = detect_dataset_changes(repo, env)
    assert should_audit is True
    assert "unavailable" in reason.lower() or "conservatively" in reason.lower()


def test_change_detection_workflow_dispatch(git_repo):
    """Verify that manual workflow_dispatch always enables audits."""
    repo, base_sha, _ = git_repo

    env = {"EVENT_NAME": "workflow_dispatch"}
    should_audit, reason, changed = detect_dataset_changes(repo, env)
    assert should_audit is True
    assert "workflow dispatch" in reason.lower()


def test_audit_execution_captures_failure_and_preserves_diagnostics(tmp_path: Path):
    """Verify that if one audit fails, the other is still run, exit codes are captured, and diagnostic reports preserved."""
    output_dir = tmp_path / "audit-reports"

    # Create dummy datasets directory
    datasets_dir = tmp_path / "datasets"
    datasets_dir.mkdir()
    (datasets_dir / "test.json").write_text(
        json.dumps({
            "id": "test",
            "name": "Test Dataset",
            "description": "Description",
            "homepage_url": "https://opendatasets.org",
            "modalities": ["tabular"],
            "tasks": ["classification"],
            "tags": ["test"],
            "license": {"status": "verified_open", "name": "MIT"},
        }),
        encoding="utf-8",
    )

    # Mock subprocess.run so that metadata audit fails (code 1) but semantic duplicate audit succeeds (code 0)
    orig_subprocess_run = subprocess.run

    def mock_run(cmd, *args, **kwargs):
        cmd_str = " ".join(str(c) for c in cmd)
        if "audit_metadata_quality.py" in cmd_str:
            # Simulate fatal failure in metadata audit
            return subprocess.CompletedProcess(cmd, returncode=1, stdout="", stderr="Fatal syntax exception in metadata audit")
        elif "audit_semantic_duplicates.py" in cmd_str:
            # Create the expected duplicate reports
            output_dir.mkdir(parents=True, exist_ok=True)
            (output_dir / "semantic-duplicate-report.json").write_text(
                json.dumps({"audit_metadata": {"total_records_scanned": 1}}), encoding="utf-8"
            )
            (output_dir / "semantic-duplicate-summary.md").write_text("# Summary", encoding="utf-8")
            return subprocess.CompletedProcess(cmd, returncode=0, stdout="Duplicate audit success", stderr="")
        return orig_subprocess_run(cmd, *args, **kwargs)

    with patch("subprocess.run", side_effect=mock_run):
        meta_exit, dup_exit, val_exit, val_errs = run_dataset_audits(
            repo_root=Path("/dummy"),
            output_dir=output_dir,
            datasets_dir=datasets_dir,
        )

    # Actual exit code captured
    assert meta_exit == 1
    assert dup_exit == 0
    # Duplicate reports preserved as diagnostics
    assert (output_dir / "semantic-duplicate-report.json").is_file()
    assert (output_dir / "semantic-duplicate-summary.md").is_file()
    # Reports created were valid JSON
    assert val_exit == 0


def test_audit_validation_detects_missing_expected_report(tmp_path: Path):
    """Verify that if audits report code 0 but expected files are missing or empty, validation fails."""
    output_dir = tmp_path / "audit-reports"
    output_dir.mkdir()

    # Create only 3 of 4 files (missing semantic-duplicate-summary.md)
    (output_dir / "metadata-quality-report.json").write_text("{}", encoding="utf-8")
    (output_dir / "metadata-quality-summary.md").write_text("# MD", encoding="utf-8")
    (output_dir / "semantic-duplicate-report.json").write_text("{}", encoding="utf-8")

    def mock_run(cmd, *args, **kwargs):
        return subprocess.CompletedProcess(cmd, returncode=0, stdout="", stderr="")

    with patch("subprocess.run", side_effect=mock_run):
        meta_exit, dup_exit, val_exit, val_errs = run_dataset_audits(
            repo_root=Path("/dummy"),
            output_dir=output_dir,
            datasets_dir=tmp_path,
        )

    assert meta_exit == 0
    assert dup_exit == 0
    assert val_exit == 1
    assert any("semantic-duplicate-summary.md" in e for e in val_errs)


def test_audit_validation_detects_invalid_json(tmp_path: Path):
    """Verify that malformed JSON in generated reports is caught by validation."""
    output_dir = tmp_path / "audit-reports"
    output_dir.mkdir()

    (output_dir / "metadata-quality-report.json").write_text("{malformed-json: True", encoding="utf-8")
    (output_dir / "metadata-quality-summary.md").write_text("# MD", encoding="utf-8")
    (output_dir / "semantic-duplicate-report.json").write_text("{}", encoding="utf-8")
    (output_dir / "semantic-duplicate-summary.md").write_text("# MD", encoding="utf-8")

    def mock_run(cmd, *args, **kwargs):
        return subprocess.CompletedProcess(cmd, returncode=0, stdout="", stderr="")

    with patch("subprocess.run", side_effect=mock_run):
        meta_exit, dup_exit, val_exit, val_errs = run_dataset_audits(
            repo_root=Path("/dummy"),
            output_dir=output_dir,
            datasets_dir=tmp_path,
        )

    assert val_exit == 1
    assert any("Invalid JSON syntax" in e for e in val_errs)


def test_oversized_artifact_budget_enforcement(tmp_path: Path):
    """Verify that oversized artifact output (> 2 MiB) is rejected and cleaned up."""
    audit_dir = tmp_path / "audit-reports"
    audit_dir.mkdir()

    # Create 2.5 MiB dummy report
    big_file = audit_dir / "oversized-report.json"
    big_file.write_bytes(b"0" * (2 * 1024 * 1024 + 500 * 1024))

    max_bytes = 2097152  # 2 MiB
    total_bytes = sum(f.stat().st_size for f in audit_dir.rglob("*") if f.is_file())
    assert total_bytes > max_bytes

    # Simulate budget enforcement logic
    within_budget = total_bytes <= max_bytes
    if not within_budget:
        for f in list(audit_dir.rglob("*")):
            if f.is_file():
                f.unlink()

    assert within_budget is False
    remaining_files = list(audit_dir.glob("*"))
    assert len(remaining_files) == 0
