#!/usr/bin/env python3
"""Reliable dataset and schema change detection for CI workflows.

Detects added, modified, renamed, or deleted files under data/datasets/ or schemas/
across pull requests, multi-commit pushes, workflow dispatches, and edge cases.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path
from typing import Mapping

WATCHED_PREFIXES = ("data/datasets/", "schemas/")


def is_valid_commit(repo_root: Path, sha: str) -> bool:
    """Check if a commit SHA exists in the local Git object store."""
    if not sha or sha == "0000000000000000000000000000000000000000":
        return False
    res = subprocess.run(
        ["git", "cat-file", "-e", f"{sha}^{{commit}}"],
        cwd=repo_root,
        capture_output=True,
    )
    return res.returncode == 0


def fetch_ref_or_commit(repo_root: Path, sha: str | None = None, ref: str | None = None) -> bool:
    """Attempt to fetch a commit SHA or ref from origin if missing locally."""
    if sha and is_valid_commit(repo_root, sha):
        return True

    if sha:
        res = subprocess.run(
            ["git", "fetch", "origin", sha],
            cwd=repo_root,
            capture_output=True,
        )
        if res.returncode == 0 and is_valid_commit(repo_root, sha):
            return True

    if ref:
        res = subprocess.run(
            ["git", "fetch", "origin", ref, "--depth=100"],
            cwd=repo_root,
            capture_output=True,
        )
        if res.returncode == 0:
            return True

    return False


def get_changed_files_between(repo_root: Path, base: str, head: str) -> list[str]:
    """Return watched dataset/schema files that changed between two commits."""
    res = subprocess.run(
        ["git", "diff", "--name-only", "-M", base, head, "--", *WATCHED_PREFIXES],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=True,
    )
    return [line.strip() for line in res.stdout.splitlines() if line.strip()]


def detect_dataset_changes(
    repo_root: Path,
    env: Mapping[str, str] | None = None,
) -> tuple[bool, str, list[str]]:
    """Determine whether dataset quality and duplicate audits should run.

    Returns:
        (should_audit, reason, changed_files)
    """
    if env is None:
        env = os.environ

    event_name = (
        env.get("EVENT_NAME")
        or env.get("GITHUB_EVENT_NAME")
        or "pull_request"
    ).lower()

    # Manual workflow dispatch: always enable audits explicitly
    if event_name == "workflow_dispatch":
        return True, "Workflow dispatch trigger: full audit explicitly enabled.", []

    # Pull Request comparison
    if event_name == "pull_request":
        base_sha = env.get("BASE_SHA") or env.get("PR_BASE_SHA") or ""
        base_ref = env.get("BASE_REF") or env.get("GITHUB_BASE_REF") or ""
        head_sha = env.get("HEAD_SHA") or env.get("PR_HEAD_SHA") or "HEAD"

        # Attempt fetching base commit/ref if not available
        fetch_ref_or_commit(repo_root, sha=base_sha if base_sha else None, ref=base_ref if base_ref else None)

        target = None
        if base_sha and is_valid_commit(repo_root, base_sha):
            target = base_sha
        elif base_ref:
            ref_check = subprocess.run(
                ["git", "rev-parse", "--verify", f"origin/{base_ref}"],
                cwd=repo_root,
                capture_output=True,
                text=True,
            )
            if ref_check.returncode == 0:
                target = f"origin/{base_ref}"

        if not target:
            msg = (
                f"::warning::PR base commit ({base_sha}) or branch ({base_ref}) could not be resolved in Git. "
                "Conservatively enabling audit generation."
            )
            print(msg, file=sys.stderr)
            return True, "PR base commit/ref unavailable; conservatively enabling audits.", []

        # Find merge base
        mb_proc = subprocess.run(
            ["git", "merge-base", "HEAD", target],
            cwd=repo_root,
            capture_output=True,
            text=True,
        )
        if mb_proc.returncode != 0 or not mb_proc.stdout.strip():
            msg = (
                f"::warning::Merge base between HEAD and {target} could not be determined. "
                "Conservatively enabling audit generation."
            )
            print(msg, file=sys.stderr)
            return True, f"Merge base between HEAD and {target} unavailable; conservatively enabling audits.", []

        merge_base = mb_proc.stdout.strip()
        try:
            changed = get_changed_files_between(repo_root, merge_base, "HEAD")
        except subprocess.CalledProcessError as err:
            msg = f"::warning::git diff failed against merge base {merge_base}: {err}. Conservatively enabling audits."
            print(msg, file=sys.stderr)
            return True, f"Git diff failure against {merge_base}; conservatively enabling audits.", []

        if changed:
            return True, f"Detected {len(changed)} changed dataset/schema files against merge base {merge_base}.", changed
        return False, f"No dataset or schema changes detected against merge base {merge_base}.", []

    # Push event comparison (handles single-commit and multi-commit pushes)
    if event_name == "push":
        before_sha = env.get("BEFORE_SHA") or env.get("PUSH_BEFORE_SHA") or ""
        after_sha = env.get("AFTER_SHA") or env.get("PUSH_AFTER_SHA") or "HEAD"

        # Check for initial branch push or missing before_sha
        if not before_sha or before_sha == "0000000000000000000000000000000000000000":
            return True, f"Initial push detected ({before_sha}); conservatively enabling audits.", []

        if not is_valid_commit(repo_root, before_sha):
            fetch_ref_or_commit(repo_root, sha=before_sha)

        if not is_valid_commit(repo_root, before_sha):
            msg = (
                f"::warning::Push commit {before_sha} not available in Git history. "
                "Conservatively enabling audit generation."
            )
            print(msg, file=sys.stderr)
            return True, f"Push commit {before_sha} unavailable; conservatively enabling audits.", []

        try:
            changed = get_changed_files_between(repo_root, before_sha, "HEAD")
        except subprocess.CalledProcessError as err:
            msg = f"::warning::git diff failed between {before_sha} and HEAD: {err}. Conservatively enabling audits."
            print(msg, file=sys.stderr)
            return True, f"Git diff failure between {before_sha} and HEAD; conservatively enabling audits.", []

        if changed:
            return True, f"Detected {len(changed)} changed dataset/schema files between {before_sha} and HEAD.", changed
        return False, f"No dataset or schema changes detected between {before_sha} and HEAD.", []

    # Fallback for unrecognized or scheduled events
    print(f"::warning::Unrecognized event '{event_name}'. Conservatively enabling audits.", file=sys.stderr)
    return True, f"Unrecognized event '{event_name}'; conservatively enabling audits.", []


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for dataset change detection."""
    parser = argparse.ArgumentParser(description="Detect dataset and schema changes for CI workflow")
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parent.parent,
        help="Path to repository root (default: repo root containing scripts/)",
    )
    args = parser.parse_args(argv)

    should_audit, reason, changed_files = detect_dataset_changes(args.repo_root)

    print(f"[CHANGE DETECTION] should_audit={'true' if should_audit else 'false'}")
    print(f"[CHANGE DETECTION] reason: {reason}")
    if changed_files:
        print(f"[CHANGE DETECTION] changed files ({len(changed_files)}):")
        for f in changed_files:
            print(f"  • {f}")

    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        try:
            with open(github_output, "a", encoding="utf-8") as fp:
                fp.write(f"should_audit={'true' if should_audit else 'false'}\n")
                fp.write(f"reason={reason}\n")
                fp.write(f"changed_count={len(changed_files)}\n")
        except OSError as err:
            print(f"[WARNING] Could not write to GITHUB_OUTPUT ({github_output}): {err}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
