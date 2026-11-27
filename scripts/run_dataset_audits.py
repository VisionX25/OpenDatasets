#!/usr/bin/env python3
"""Run dataset quality and duplicate audits for CI with failure semantics and report validation.

Ensures:
1. Both metadata quality and semantic duplicate audits are executed independently.
2. Actual exit codes are captured without swallowing fatal errors.
3. Diagnostic reports are preserved if one audit fails.
4. Expected files exist and contain valid JSON.
5. Exit code is non-zero if any audit fails or reports are corrupted/missing.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Sequence

EXPECTED_METADATA_FILES = [
    "metadata-quality-report.json",
    "metadata-quality-summary.md",
]

EXPECTED_DUPLICATE_FILES = [
    "semantic-duplicate-report.json",
    "semantic-duplicate-summary.md",
]


def run_dataset_audits(
    repo_root: Path,
    output_dir: Path,
    datasets_dir: Path | None = None,
    audit_date: str | None = None,
) -> tuple[int, int, int, list[str]]:
    """Execute both audits independently and validate report integrity.

    Returns:
        (meta_exit_code, duplicate_exit_code, validation_exit_code, validation_errors)
    """
    if datasets_dir is None:
        datasets_dir = repo_root / "data" / "datasets"

    output_dir.mkdir(parents=True, exist_ok=True)

    meta_json = output_dir / "metadata-quality-report.json"
    meta_md = output_dir / "metadata-quality-summary.md"
    dup_json = output_dir / "semantic-duplicate-report.json"
    dup_md = output_dir / "semantic-duplicate-summary.md"

    print("=======================================================")
    print(" Executing CI Dataset Audit Suite")
    print("=======================================================")
    print(f" Repository root:    {repo_root}")
    print(f" Datasets directory: {datasets_dir}")
    print(f" Audit output dir:   {output_dir}")
    print("=======================================================")

    # 1. Execute Metadata Quality Audit
    print("\n--- Running Metadata Quality & Research Readiness Audit ---")
    meta_cmd = [
        sys.executable,
        str(repo_root / "scripts" / "audit_metadata_quality.py"),
        "--datasets-dir",
        str(datasets_dir),
        "--output-json",
        str(meta_json),
        "--output-md",
        str(meta_md),
    ]
    if audit_date:
        meta_cmd.extend(["--audit-date", audit_date])

    meta_proc = subprocess.run(meta_cmd, capture_output=True, text=True)
    meta_exit_code = meta_proc.returncode

    if meta_exit_code != 0:
        print(f"[ERROR] Metadata quality audit failed with exit code {meta_exit_code}:", file=sys.stderr)
        if meta_proc.stderr:
            print(meta_proc.stderr.strip(), file=sys.stderr)
        if meta_proc.stdout:
            print(meta_proc.stdout.strip(), file=sys.stderr)
    else:
        print("[OK] Metadata quality audit completed successfully.")

    # 2. Execute Cross-Dataset Semantic Duplicate Audit
    print("\n--- Running Cross-Dataset Semantic Duplicate Audit ---")
    dup_cmd = [
        sys.executable,
        str(repo_root / "scripts" / "audit_semantic_duplicates.py"),
        "--datasets-dir",
        str(datasets_dir),
        "--output-json",
        str(dup_json),
        "--output-md",
        str(dup_md),
        "--quiet",
    ]
    if audit_date:
        dup_cmd.extend(["--audit-date", audit_date])

    dup_proc = subprocess.run(dup_cmd, capture_output=True, text=True)
    dup_exit_code = dup_proc.returncode

    if dup_exit_code != 0:
        print(f"[ERROR] Semantic duplicate audit failed with exit code {dup_exit_code}:", file=sys.stderr)
        if dup_proc.stderr:
            print(dup_proc.stderr.strip(), file=sys.stderr)
        if dup_proc.stdout:
            print(dup_proc.stdout.strip(), file=sys.stderr)
    else:
        print("[OK] Semantic duplicate audit completed successfully.")

    # 3. Validate Generated Reports
    print("\n--- Validating Generated Audit Reports ---")
    validation_errors: list[str] = []

    # Check metadata reports if metadata audit exited 0
    if meta_exit_code == 0:
        for fname in EXPECTED_METADATA_FILES:
            fpath = output_dir / fname
            if not fpath.is_file():
                validation_errors.append(f"Expected metadata report file missing: {fname}")
            elif fpath.stat().st_size == 0:
                validation_errors.append(f"Expected metadata report file is empty: {fname}")

    # Check duplicate reports if duplicate audit exited 0
    if dup_exit_code == 0:
        for fname in EXPECTED_DUPLICATE_FILES:
            fpath = output_dir / fname
            if not fpath.is_file():
                validation_errors.append(f"Expected duplicate report file missing: {fname}")
            elif fpath.stat().st_size == 0:
                validation_errors.append(f"Expected duplicate report file is empty: {fname}")

    # Check valid JSON syntax for any generated JSON report
    for json_file in sorted(output_dir.glob("*.json")):
        try:
            content = json_file.read_text(encoding="utf-8")
            data = json.loads(content)
            if not isinstance(data, dict):
                validation_errors.append(f"JSON report root is not an object: {json_file.name}")
        except Exception as err:
            validation_errors.append(f"Invalid JSON syntax in {json_file.name}: {err}")

    validation_exit_code = 1 if validation_errors else 0

    if validation_errors:
        for err in validation_errors:
            print(f"[ERROR] Validation error: {err}", file=sys.stderr)
    else:
        print("[OK] All generated audit reports validated successfully.")

    return meta_exit_code, dup_exit_code, validation_exit_code, validation_errors


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point for running CI dataset audits."""
    parser = argparse.ArgumentParser(description="Run dataset audits with validation for CI")
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parent.parent,
        help="Path to repository root",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(os.environ.get("RUNNER_TEMP", "/tmp")) / "audit-reports",
        help="Directory to write audit reports into",
    )
    parser.add_argument(
        "--datasets-dir",
        type=Path,
        default=None,
        help="Directory containing dataset JSON records",
    )
    args = parser.parse_args(argv)

    meta_exit, dup_exit, val_exit, val_errors = run_dataset_audits(
        repo_root=args.repo_root,
        output_dir=args.output_dir,
        datasets_dir=args.datasets_dir,
    )

    overall_exit = 1 if (meta_exit != 0 or dup_exit != 0 or val_exit != 0) else 0

    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        try:
            with open(github_output, "a", encoding="utf-8") as fp:
                fp.write(f"meta_exit_code={meta_exit}\n")
                fp.write(f"duplicate_exit_code={dup_exit}\n")
                fp.write(f"validation_exit_code={val_exit}\n")
                fp.write(f"overall_exit_code={overall_exit}\n")
        except OSError as err:
            print(f"[WARNING] Could not write to GITHUB_OUTPUT: {err}", file=sys.stderr)

    return overall_exit


if __name__ == "__main__":
    sys.exit(main())
