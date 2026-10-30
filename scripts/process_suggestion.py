#!/usr/bin/env python3
"""OpenDatasets Community Suggestion Orchestrator.

CLI entrypoint that ties together the suggestion parser, duplicate detector,
and draft generator for GitHub Actions CI and local maintainer workflow.

Usage:
  python3 scripts/process_suggestion.py --issue-file <path>
  python3 scripts/process_suggestion.py --event-path <path_to_github_event.json>
  python3 scripts/process_suggestion.py --issue-body "<raw_markdown>"

Exit codes:
  0: Successful parse and draft generation (valid novel suggestion)
  1: Validation or parsing failure (malformed or missing required fields)
  2: Duplicate detected with high confidence
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

# Ensure scripts directory is on sys.path for direct execution
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.draft_generator import (
    DEFAULT_SCHEMA_PATH,
    format_maintainer_report,
    format_unsupported_issue_report,
    generate_draft_metadata,
    generate_slug,
    validate_draft_dict,
)
from scripts.duplicate_detector import (
    DuplicateCheckResult,
    check_suggestion_for_duplicates,
    load_catalog_datasets,
)
from scripts.suggestion_parser import (
    ParsedSuggestion,
    parse_dataset_suggestion,
    sanitize_untrusted_text,
)

DEFAULT_DATA_DIR = REPO_ROOT / "data" / "datasets"
DEFAULT_DRAFTS_DIR = REPO_ROOT / "drafts"


def extract_issue_data_from_event(event_path: Path) -> tuple[str, int | None, str | None]:
    """Extract issue body, number, and title from a GitHub event payload."""
    if not event_path.exists():
        raise FileNotFoundError(f"GitHub event file not found: {event_path}")

    with open(event_path, "r", encoding="utf-8") as f:
        event = json.load(f)

    issue = event.get("issue", {})
    body = issue.get("body", "")
    number = issue.get("number")
    title = issue.get("title")
    return body, number, title


def process_suggestion(
    raw_body: str,
    data_dir: Path = DEFAULT_DATA_DIR,
    schema_path: Path = DEFAULT_SCHEMA_PATH,
    output_dir: Path = DEFAULT_DRAFTS_DIR,
    issue_number: int | None = None,
    save_draft: bool = True,
) -> tuple[int, dict[str, Any], str]:
    """Execute the full end-to-end community contribution triage pipeline.

    Returns:
        (exit_code, result_dict, report_markdown)
    """
    # 1. Parse and sanitize suggestion
    suggestion = parse_dataset_suggestion(raw_body)

    # 1a. Handle unsupported issue types (not matching dataset suggestion template)
    if not suggestion.is_template_match:
        report_markdown = format_unsupported_issue_report(issue_number=issue_number)
        result_dict: dict[str, Any] = {
            "status": "unsupported",
            "exit_code": 0,
            "is_template_match": False,
            "is_valid": False,
            "is_duplicate": False,
            "has_potential_matches": False,
            "errors": suggestion.errors,
            "warnings": suggestion.warnings,
            "slug": "",
            "draft_path": None,
            "recommended_label": "unsupported",
            "duplicate_check": None,
            "draft_metadata": None,
        }
        return 0, result_dict, report_markdown

    # 2. Duplicate detection
    existing_datasets = load_catalog_datasets(data_dir)
    existing_slugs = {ds.get("slug") for ds in existing_datasets if ds.get("slug")}
    candidate_slug = generate_slug(suggestion.name) if suggestion.name else ""
    duplicate_result = check_suggestion_for_duplicates(suggestion, existing_datasets, candidate_slug)

    # 3. Draft generation (if valid)
    draft_data: dict[str, Any] | None = None
    validation_errors: list[str] = []
    draft_path: Path | None = None

    if suggestion.is_valid:
        draft_data = generate_draft_metadata(
            suggestion,
            issue_number=issue_number,
            existing_slugs=existing_slugs if not duplicate_result.is_duplicate else None,
        )
        validation_errors = validate_draft_dict(draft_data, schema_path=schema_path)

        if save_draft and draft_data and not validation_errors:
            output_dir.mkdir(parents=True, exist_ok=True)
            draft_filename = (
                f"{draft_data['slug']}-issue{issue_number}.draft.json"
                if issue_number
                else f"{draft_data['slug']}.draft.json"
            )
            draft_path = output_dir / draft_filename
            with open(draft_path, "w", encoding="utf-8") as f:
                json.dump(draft_data, f, indent=2, ensure_ascii=False)
                f.write("\n")

    # 4. Generate Maintainer Report
    report_markdown = format_maintainer_report(
        suggestion=suggestion,
        duplicate_result=duplicate_result,
        draft_data=draft_data,
        validation_errors=validation_errors,
        draft_file_path=draft_path,
        issue_number=issue_number,
    )

    # 5. Determine Exit Code and Status
    if not suggestion.is_valid:
        exit_code = 1
        status = "invalid"
        recommended_label = "needs-info"
    elif duplicate_result.is_duplicate:
        exit_code = 2
        status = "duplicate"
        recommended_label = "duplicate"
    else:
        exit_code = 0
        status = "valid"
        recommended_label = "candidate-approved"

    result_dict: dict[str, Any] = {
        "status": status,
        "exit_code": exit_code,
        "is_valid": suggestion.is_valid,
        "is_duplicate": duplicate_result.is_duplicate,
        "has_potential_matches": duplicate_result.has_potential_matches,
        "errors": suggestion.errors + validation_errors,
        "warnings": suggestion.warnings,
        "slug": candidate_slug,
        "draft_path": str(draft_path) if draft_path else None,
        "recommended_label": recommended_label,
        "duplicate_check": duplicate_result.to_dict(),
        "draft_metadata": draft_data,
    }

    return exit_code, result_dict, report_markdown


def main() -> int:
    """CLI handler."""
    parser = argparse.ArgumentParser(
        description="Process OpenDatasets community dataset suggestions."
    )
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        "--issue-file",
        type=Path,
        help="Path to file containing raw issue body markdown.",
    )
    input_group.add_argument(
        "--event-path",
        type=Path,
        help="Path to GitHub Actions event payload ($GITHUB_EVENT_PATH).",
    )
    input_group.add_argument(
        "--issue-body",
        type=str,
        help="Raw issue body markdown string.",
    )

    parser.add_argument(
        "--issue-number",
        type=int,
        default=None,
        help="GitHub issue number if not reading from event payload.",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=DEFAULT_DATA_DIR,
        help=f"Path to published datasets directory (default: {DEFAULT_DATA_DIR}).",
    )
    parser.add_argument(
        "--schema-path",
        type=Path,
        default=DEFAULT_SCHEMA_PATH,
        help=f"Path to JSON schema (default: {DEFAULT_SCHEMA_PATH}).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_DRAFTS_DIR,
        help=f"Directory to save generated draft JSON files (default: {DEFAULT_DRAFTS_DIR}).",
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="Do not save draft JSON to disk (dry run).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Output machine-readable JSON rather than Markdown report.",
    )
    parser.add_argument(
        "--report-file",
        type=Path,
        default=None,
        help="Optional path to write the markdown report to.",
    )
    parser.add_argument(
        "--summary-file",
        type=Path,
        default=None,
        help="Optional path to append the markdown report to (e.g. $GITHUB_STEP_SUMMARY).",
    )

    args = parser.parse_args()

    raw_body = ""
    issue_number = args.issue_number

    if args.issue_file:
        if not args.issue_file.exists():
            print(f"Error: Issue file not found: {args.issue_file}", file=sys.stderr)
            return 1
        with open(args.issue_file, "r", encoding="utf-8") as f:
            raw_body = f.read()
    elif args.event_path:
        try:
            raw_body, event_num, _ = extract_issue_data_from_event(args.event_path)
            if issue_number is None:
                issue_number = event_num
        except Exception as exc:
            print(f"Error reading GitHub event: {exc}", file=sys.stderr)
            return 1
    elif args.issue_body:
        raw_body = args.issue_body

    exit_code, result_dict, report_markdown = process_suggestion(
        raw_body=raw_body,
        data_dir=args.data_dir,
        schema_path=args.schema_path,
        output_dir=args.output_dir,
        issue_number=issue_number,
        save_draft=not args.no_save,
    )

    if args.report_file:
        args.report_file.parent.mkdir(parents=True, exist_ok=True)
        with open(args.report_file, "w", encoding="utf-8") as f:
            f.write(report_markdown)

    if args.summary_file:
        args.summary_file.parent.mkdir(parents=True, exist_ok=True)
        with open(args.summary_file, "a", encoding="utf-8") as f:
            f.write(report_markdown)
            f.write("\n")

    if args.json_output:
        print(json.dumps(result_dict, indent=2, ensure_ascii=False))
    else:
        print(report_markdown)

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
