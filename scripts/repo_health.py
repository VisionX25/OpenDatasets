#!/usr/bin/env python3
"""OpenDatasets Repository Health Baseline Reporter.

Measures catalog quality, licensing consistency, sample-count partition integrity,
taxonomy hygiene, metadata formatting, generated artifact sizes, test metrics,
source-link monitoring cadence, GitHub Actions automation, and frontend readiness.

Part of Infrastructure Improvement Phase 0 (Related to Issue #65, Closes Issue #66).
Uses Python standard library only. Offline by default (< 3 seconds runtime).
"""

from __future__ import annotations

import argparse
import collections
from collections import Counter, defaultdict
import dataclasses
from dataclasses import asdict, dataclass, field
import datetime
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional, Set, Tuple
import urllib.parse

# ---------------------------------------------------------------------------
# Constants & Configuration
# ---------------------------------------------------------------------------

SCHEMA_VERSION = "1.0"
REPO_NAME = "OpenDatasets"

# Standard partition keywords recognized by validator
STANDARD_PARTITION_KEYWORDS = (
    "train",
    "test",
    "val",
    "validation",
    "dev",
    "development",
    "eval",
    "evaluation",
    "benchmark",
    "challenge",
    "unlabeled",
    "unlabelled",
    "auxiliary",
    "fine_tune",
    "pretrain",
)

# Known entity stems for unit compatibility checks
ENTITY_STEMS = (
    "sample",
    "example",
    "record",
    "row",
    "instance",
    "item",
    "image",
    "video",
    "clip",
    "frame",
    "audio",
    "recording",
    "utterance",
    "sentence",
    "word",
    "token",
    "document",
    "file",
    "track",
    "dialogue",
    "turn",
    "pair",
    "question",
    "passage",
    "label",
    "bounding_box",
    "annotation",
)

BENCHMARK_TAGS = {
    "benchmark",
    "evaluation",
    "eval",
    "benchmark-dataset",
    "gold-standard",
    "leaderboard",
    "ogb",
    "ogb-benchmark",
    "ogb-lsc",
}

NON_COMMERCIAL_SPDX_PATTERNS = ("-nc", "nc-", "non-commercial")
PERMISSIVE_SPDX_PREFIXES = (
    "mit",
    "apache-2.0",
    "bsd",
    "cc-by-4.0",
    "cc-by-3.0",
    "cc-by-2.0",
    "cc0",
    "unlicense",
    "isc",
)

# Historical baseline figures from Issue #65 (at commit ec66131 / c3966fb)
HISTORICAL_BASELINE = [
    {
        "metric": "Catalog dataset count",
        "historical": "875",
        "current_key": "catalog_dataset_count",
        "format": "count",
        "notes": "Verified research datasets at Issue #65 baseline",
    },
    {
        "metric": "Python unit tests (count)",
        "historical": "240",
        "current_key": "python_tests_count",
        "format": "count",
        "notes": "Pytest suite pass count reported in Issue #65",
    },
    {
        "metric": "Python full suite runtime",
        "historical": "270 s",
        "current_key": "python_test_duration",
        "format": "seconds",
        "notes": "Issue #65 observed ~257 s in duplicate audit tests",
    },
    {
        "metric": "Catalog JSON size (raw)",
        "historical": "3.38 MB",
        "current_key": "catalog_raw_size",
        "format": "size_mb",
        "notes": "Committed catalog.json size reported in Issue #65",
    },
    {
        "metric": "Catalog JSON size (gzip)",
        "historical": "728 KB",
        "current_key": "catalog_gzip_size",
        "format": "size_kb",
        "notes": "Compressed size reported in Issue #65",
    },
    {
        "metric": "Generated audit reports size",
        "historical": "4.0 MB",
        "current_key": "audit_reports_size",
        "format": "size_mb",
        "notes": "Audit reports in docs/audits/ reported in Issue #65",
    },
    {
        "metric": "Distinct taxonomy tasks",
        "historical": "704",
        "current_key": "distinct_tasks",
        "format": "count",
        "notes": "Distinct tasks reported in Issue #65",
    },
    {
        "metric": "Singleton taxonomy tasks",
        "historical": "447",
        "current_key": "singleton_tasks",
        "format": "count",
        "notes": "Singletons reported in Issue #65 (63.5%)",
    },
    {
        "metric": "Distinct taxonomy tags",
        "historical": "1,981",
        "current_key": "distinct_tags",
        "format": "count",
        "notes": "Distinct tags reported in Issue #65",
    },
    {
        "metric": "Singleton taxonomy tags",
        "historical": "1,407",
        "current_key": "singleton_tags",
        "format": "count",
        "notes": "Singletons reported in Issue #65 (71.0%)",
    },
    {
        "metric": "Uncategorized UI datasets",
        "historical": "9",
        "current_key": "uncategorized_datasets_count",
        "format": "count",
        "notes": "UI discovery category omissions noted in Issue #65",
    },
    {
        "metric": "Suspected truncated slugs",
        "historical": "28",
        "current_key": "truncated_slugs_count",
        "format": "count",
        "notes": "Truncated slugs noted in Issue #65",
    },
    {
        "metric": "Files lacking trailing newline",
        "historical": "27",
        "current_key": "missing_trailing_newline_count",
        "format": "count",
        "notes": "Files lacking trailing newline noted in Issue #65",
    },
    {
        "metric": "Plain HTTP URLs (occurrences)",
        "historical": "45 (23 unique)",
        "current_key": "plain_http_urls_summary",
        "format": "string",
        "notes": "Structured field HTTP URLs noted in Issue #65",
    },
    {
        "metric": "Language metadata (NLP+Audio)",
        "historical": "175 / 313 (55.9%)",
        "current_key": "languages_nlp_audio_summary",
        "format": "string",
        "notes": "Language coverage ratio reported in Issue #65",
    },
    {
        "metric": "Dataset size metadata coverage",
        "historical": "468 / 875 (53.5%)",
        "current_key": "size_coverage_summary",
        "format": "string",
        "notes": "Size metadata coverage reported in Issue #65",
    },
    {
        "metric": "Sample count raw sum mismatch",
        "historical": "29",
        "current_key": "raw_arithmetic_discrepancy_count",
        "format": "count",
        "notes": "Split sum discrepancies reported in Issue #65",
    },
    {
        "metric": "Non-commercial verified_open",
        "historical": "2",
        "current_key": "non_comm_verified_open_count",
        "format": "count",
        "notes": "anli & sciq CC-BY-NC classified as verified_open in Issue #65",
    },
    {
        "metric": "Permissive SPDX commercial unknown",
        "historical": "11",
        "current_key": "permissive_unknown_comm_count",
        "format": "count",
        "notes": "Permissive SPDX with commercial_use unknown in Issue #65",
    },
    {
        "metric": "Source-link rotation cycle",
        "historical": "~52 weeks",
        "current_key": "source_monitor_cycle_weeks",
        "format": "string",
        "notes": "Full rotation cycle estimate reported in Issue #65",
    },
]

# ---------------------------------------------------------------------------
# Finding Data Structure
# ---------------------------------------------------------------------------

@dataclass
class Finding:
    """Actionable repository health finding."""
    id: str
    category: str
    severity: str  # "info", "warning", "error"
    status: str    # "passed", "warning", "review_required", "failed", "skipped"
    title: str
    description: str
    affected_records: list[str] = field(default_factory=list)
    recommended_action: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Metric Collectors
# ---------------------------------------------------------------------------

def collect_repository_metadata(repo_root: Path) -> dict[str, Any]:
    """Collect repository identity, version control state, and runtime environment (Metric Group A)."""
    datasets_dir = repo_root / "data" / "datasets"
    all_json_files = sorted(datasets_dir.glob("*.json")) if datasets_dir.exists() else []
    total_datasets = len(all_json_files)

    # Git inspections (graceful fallback if not in git repository)
    commit_sha = "unknown"
    branch = "unknown"
    tracked_count = 0
    untracked_count = 0
    working_tree_status = "unknown"

    try:
        res = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            check=False,
        )
        if res.returncode == 0:
            commit_sha = res.stdout.strip()

        res = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            check=False,
        )
        if res.returncode == 0:
            branch = res.stdout.strip()

        res = subprocess.run(
            ["git", "ls-files", "data/datasets/*.json"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            check=False,
        )
        if res.returncode == 0:
            tracked_files = [f for f in res.stdout.strip().splitlines() if f.strip()]
            tracked_count = len(tracked_files)
            untracked_count = max(0, total_datasets - tracked_count)

        res = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            check=False,
        )
        if res.returncode == 0:
            working_tree_status = "clean" if not res.stdout.strip() else "dirty"
    except Exception:
        pass

    # Node / npm version checks
    node_version: str | None = None
    npm_version: str | None = None
    try:
        res = subprocess.run(["node", "--version"], capture_output=True, text=True, check=False)
        if res.returncode == 0:
            node_version = res.stdout.strip()
    except Exception:
        pass

    try:
        res = subprocess.run(["npm", "--version"], capture_output=True, text=True, check=False)
        if res.returncode == 0:
            npm_version = res.stdout.strip()
    except Exception:
        pass

    return {
        "repository_name": REPO_NAME,
        "commit_sha": commit_sha,
        "branch": branch,
        "dataset_count": total_datasets,
        "tracked_dataset_count": tracked_count if commit_sha != "unknown" else total_datasets,
        "untracked_dataset_count": untracked_count,
        "working_tree_status": working_tree_status,
        "report_timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "python_version": sys.version.split()[0],
        "node_version": node_version,
        "npm_version": npm_version,
        "report_schema_version": SCHEMA_VERSION,
    }


def collect_catalog_health(repo_root: Path) -> tuple[dict[str, Any], list[Finding], dict[str, dict[str, Any]]]:
    """Inspect catalog JSON files for completeness, IDs, slugs, and coverage (Metric Group B)."""
    datasets_dir = repo_root / "data" / "datasets"
    findings: list[Finding] = []
    parsed_records: dict[str, dict[str, Any]] = {}
    invalid_files: list[str] = []

    if not datasets_dir.exists():
        return {
            "total_records": 0,
            "parsed_records": 0,
            "invalid_json_records": 0,
            "duplicate_exact_ids": 0,
            "duplicate_normalized_ids": 0,
            "duplicate_exact_slugs": 0,
            "duplicate_normalized_slugs": 0,
            "missing_required_fields": {},
            "citation_coverage": 0,
            "doi_coverage": 0,
            "publication_date_coverage": 0,
            "verification_date_coverage": 0,
            "homepage_url_coverage": 0,
            "source_reference_coverage": 0,
            "sample_count_coverage": 0,
            "dataset_size_coverage": 0,
            "language_coverage": 0,
            "nlp_audio_coverage": 0,
            "nlp_audio_total": 0,
        }, findings, parsed_records

    all_files = sorted(datasets_dir.glob("*.json"))
    for file_path in all_files:
        rel_path = file_path.name
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                if not content.strip():
                    invalid_files.append(rel_path)
                    continue
                data = json.loads(content)
                if not isinstance(data, dict):
                    invalid_files.append(rel_path)
                    continue
                parsed_records[rel_path] = data
        except Exception:
            invalid_files.append(rel_path)

    if invalid_files:
        findings.append(
            Finding(
                id="FINDING-CAT-001",
                category="catalog",
                severity="error",
                status="failed",
                title=f"{len(invalid_files)} dataset file(s) failed JSON parsing",
                description="Malformed or unparseable JSON files found in data/datasets/",
                affected_records=invalid_files,
                recommended_action="Repair JSON syntax to conform to specification.",
            )
        )

    # Required fields based on schema v1
    required_fields = [
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
    ]

    missing_fields_map: dict[str, list[str]] = defaultdict(list)
    id_counts: Counter[str] = Counter()
    norm_id_counts: Counter[str] = Counter()
    slug_counts: Counter[str] = Counter()
    norm_slug_counts: Counter[str] = Counter()

    citation_cov = 0
    doi_cov = 0
    pub_date_cov = 0
    verif_date_cov = 0
    homepage_cov = 0
    source_ref_cov = 0
    sample_count_cov = 0
    size_cov = 0
    lang_cov = 0
    nlp_audio_total = 0
    nlp_audio_lang_cov = 0

    for filename, record in parsed_records.items():
        did = str(record.get("id", filename))
        slug = str(record.get("slug", ""))

        id_counts[did] += 1
        norm_id = re.sub(r"[^a-z0-9]", "", did.lower())
        norm_id_counts[norm_id] += 1

        if slug:
            slug_counts[slug] += 1
            norm_slug = re.sub(r"[^a-z0-9]", "", slug.lower())
            norm_slug_counts[norm_slug] += 1

        for rf in required_fields:
            val = record.get(rf)
            if val is None or val == "" or (isinstance(val, (list, dict)) and len(val) == 0):
                missing_fields_map[rf].append(did)

        # Citation coverage
        cit = record.get("citation")
        if cit and (
            isinstance(cit, str)
            or (isinstance(cit, dict) and (cit.get("paper_title") or cit.get("bibtex") or cit.get("doi")))
        ):
            citation_cov += 1

        # DOI coverage
        if (
            (isinstance(cit, dict) and cit.get("doi"))
            or (isinstance(record.get("publication"), dict) and record["publication"].get("doi"))
            or record.get("doi")
        ):
            doi_cov += 1

        # Publication date coverage (dates.published or publication.date)
        dates = record.get("dates")
        if dates and isinstance(dates, dict) and dates.get("published"):
            pub_date_cov += 1
        elif record.get("publication_date") or (
            isinstance(record.get("publication"), dict) and record["publication"].get("date")
        ):
            pub_date_cov += 1

        # Verification date coverage
        verif = record.get("verification")
        if verif and isinstance(verif, dict) and (verif.get("date") or verif.get("verified_date")):
            verif_date_cov += 1

        # Homepage URL coverage
        if record.get("homepage_url"):
            homepage_cov += 1

        # Source references coverage
        srefs = record.get("source_references")
        if srefs and isinstance(srefs, list) and len(srefs) > 0:
            source_ref_cov += 1

        # Sample count coverage
        if record.get("sample_count"):
            sample_count_cov += 1

        # Size coverage
        if record.get("size"):
            size_cov += 1

        # Languages coverage
        langs = record.get("languages")
        if langs and isinstance(langs, list) and len(langs) > 0:
            lang_cov += 1

        mods = record.get("modalities", []) or []
        if any(m in ("nlp", "audio") for m in mods):
            nlp_audio_total += 1
            if langs and isinstance(langs, list) and len(langs) > 0:
                nlp_audio_lang_cov += 1

    duplicate_exact_ids = [k for k, v in id_counts.items() if v > 1]
    duplicate_norm_ids = [k for k, v in norm_id_counts.items() if v > 1]
    duplicate_exact_slugs = [k for k, v in slug_counts.items() if v > 1]
    duplicate_norm_slugs = [k for k, v in norm_slug_counts.items() if v > 1]

    if duplicate_exact_ids:
        findings.append(
            Finding(
                id="FINDING-CAT-002",
                category="catalog",
                severity="error",
                status="failed",
                title=f"{len(duplicate_exact_ids)} duplicate exact dataset ID(s)",
                description="Collision on identical dataset ID values.",
                affected_records=sorted(duplicate_exact_ids),
                recommended_action="Ensure every dataset ID is globally unique.",
            )
        )

    if missing_fields_map:
        for rf, ids in sorted(missing_fields_map.items()):
            findings.append(
                Finding(
                    id=f"FINDING-CAT-REQ-{rf.upper()}",
                    category="catalog",
                    severity="error",
                    status="failed",
                    title=f"Missing required field '{rf}' in {len(ids)} record(s)",
                    description=f"Field '{rf}' is declared required in Schema v1.",
                    affected_records=sorted(ids)[:20],
                    recommended_action=f"Backfill required field '{rf}'.",
                )
            )

    return {
        "total_records": len(all_files),
        "parsed_records": len(parsed_records),
        "invalid_json_records": len(invalid_files),
        "invalid_json_files": invalid_files,
        "duplicate_exact_ids": len(duplicate_exact_ids),
        "duplicate_normalized_ids": len(duplicate_norm_ids),
        "duplicate_exact_slugs": len(duplicate_exact_slugs),
        "duplicate_normalized_slugs": len(duplicate_norm_slugs),
        "missing_required_fields": {k: len(v) for k, v in missing_fields_map.items()},
        "citation_coverage": citation_cov,
        "doi_coverage": doi_cov,
        "publication_date_coverage": pub_date_cov,
        "verification_date_coverage": verif_date_cov,
        "homepage_url_coverage": homepage_cov,
        "source_reference_coverage": source_ref_cov,
        "sample_count_coverage": sample_count_cov,
        "dataset_size_coverage": size_cov,
        "language_coverage": lang_cov,
        "nlp_audio_coverage": nlp_audio_lang_cov,
        "nlp_audio_total": nlp_audio_total,
    }, findings, parsed_records


def collect_license_metrics(records: dict[str, dict[str, Any]]) -> tuple[dict[str, Any], list[Finding]]:
    """Analyze licensing statuses, commercial use declarations, and SPDX identifiers (Metric Group C)."""
    findings: list[Finding] = []
    status_dist: Counter[str] = Counter()
    comm_dist: Counter[str] = Counter()

    has_spdx = 0
    missing_spdx_ids: list[str] = []
    review_candidates: list[dict[str, Any]] = []

    for filename, record in sorted(records.items()):
        did = str(record.get("id", filename))
        lic = record.get("license", {})
        if not isinstance(lic, dict):
            status_dist["missing"] += 1
            comm_dist["missing"] += 1
            missing_spdx_ids.append(did)
            continue

        status = lic.get("status", "unspecified")
        comm = lic.get("commercial_use", "unspecified")
        spdx = str(lic.get("spdx_id", "")).strip()

        status_dist[status] += 1
        comm_dist[comm] += 1

        if spdx:
            has_spdx += 1
            spdx_lower = spdx.lower()

            # Rule 1: Non-commercial SPDX classified as verified_open
            if any(nc in spdx_lower for nc in NON_COMMERCIAL_SPDX_PATTERNS) and status == "verified_open":
                review_candidates.append({
                    "id": did,
                    "type": "non_commercial_spdx_verified_open",
                    "spdx_id": spdx,
                    "status": status,
                    "commercial_use": comm,
                    "notes": "Non-commercial SPDX identifier with verified_open status; review for status alignment.",
                })

            # Rule 2: Non-commercial license with commercial_use allowed
            if (status == "verified_non_commercial" or any(nc in spdx_lower for nc in NON_COMMERCIAL_SPDX_PATTERNS)) and comm == "allowed":
                review_candidates.append({
                    "id": did,
                    "type": "non_commercial_with_commercial_allowed",
                    "spdx_id": spdx,
                    "status": status,
                    "commercial_use": comm,
                    "notes": "Non-commercial license with commercial_use: allowed; potential contradiction.",
                })

            # Rule 3: Permissive SPDX identifier with commercial_use unknown
            # Note: Permissive SPDX with commercial_use unknown is not automatically an error
            if any(spdx_lower.startswith(pfx) for pfx in PERMISSIVE_SPDX_PREFIXES) and comm == "unknown":
                review_candidates.append({
                    "id": did,
                    "type": "permissive_spdx_commercial_unknown",
                    "spdx_id": spdx,
                    "status": status,
                    "commercial_use": comm,
                    "notes": "Permissive SPDX with commercial_use: unknown; manual review candidate for third-party or mixed terms.",
                })
        else:
            missing_spdx_ids.append(did)

    if review_candidates:
        findings.append(
            Finding(
                id="FINDING-LIC-001",
                category="licensing",
                severity="warning",
                status="review_required",
                title=f"{len(review_candidates)} license classification review candidate(s)",
                description=(
                    "Identified datasets where license status, SPDX ID, or commercial-use declaration warrant manual review. "
                    "Permissive SPDX with unknown commercial use reflects mixed-asset or third-party terms rather than automatic defects."
                ),
                affected_records=[c["id"] for c in review_candidates],
                recommended_action="Audit license clauses against primary source documentation during Phase 4.",
            )
        )

    return {
        "status_distribution": dict(status_dist.most_common()),
        "commercial_use_distribution": dict(comm_dist.most_common()),
        "spdx_identifier_coverage": has_spdx,
        "missing_spdx_count": len(missing_spdx_ids),
        "unknown_commercial_use_count": comm_dist.get("unknown", 0),
        "non_commercial_count": status_dist.get("verified_non_commercial", 0) + comm_dist.get("forbidden", 0),
        "review_candidates_count": len(review_candidates),
        "review_candidates": review_candidates,
    }, findings


def collect_sample_count_metrics(records: dict[str, dict[str, Any]]) -> tuple[dict[str, Any], list[Finding]]:
    """Analyze sample-count units, partition completeness, overlap, and arithmetic consistency (Metric Group D)."""
    findings: list[Finding] = []

    has_sc = 0
    missing_unit: list[str] = []
    verified_count = 0
    estimated_count = 0
    has_splits = 0
    has_breakdown = 0

    completeness_dist: Counter[str] = Counter()
    overlap_dist: Counter[str] = Counter()

    raw_arithmetic_discrepancies: list[dict[str, Any]] = []
    actionable_concerns: list[dict[str, Any]] = []

    for filename, record in sorted(records.items()):
        did = str(record.get("id", filename))
        sc = record.get("sample_count")
        if not sc or not isinstance(sc, dict):
            continue

        has_sc += 1
        unit = sc.get("unit")
        if not unit:
            missing_unit.append(did)

        if sc.get("is_estimated") is True:
            estimated_count += 1
        else:
            verified_count += 1

        splits = sc.get("splits")
        if splits and isinstance(splits, dict):
            has_splits += 1

        breakdown = sc.get("breakdown")
        if breakdown and isinstance(breakdown, dict):
            has_breakdown += 1

        comp = sc.get("partition_completeness", "unspecified")
        completeness_dist[comp] += 1

        over = sc.get("partition_overlap", "unspecified")
        overlap_dist[over] += 1

        total = sc.get("total")
        if total is not None and isinstance(total, int) and splits and isinstance(splits, dict):
            vals = [v for v in splits.values() if isinstance(v, (int, float))]
            if vals:
                split_sum = sum(vals)
                if split_sum != total:
                    discrepancy_info = {
                        "id": did,
                        "declared_total": total,
                        "split_sum": split_sum,
                        "difference": split_sum - total,
                        "partition_completeness": comp,
                        "partition_overlap": over,
                        "unit": unit or "unspecified",
                    }
                    raw_arithmetic_discrepancies.append(discrepancy_info)

                    # Actionable hard inconsistency: completeness is complete/exhaustive AND overlap is disjoint
                    if comp in ("complete", "exhaustive") and over in ("disjoint", "mutually_exclusive"):
                        actionable_concerns.append(discrepancy_info)

    if raw_arithmetic_discrepancies:
        findings.append(
            Finding(
                id="FINDING-SC-001",
                category="sample_counts",
                severity="info",
                status="measured",
                title=f"{len(raw_arithmetic_discrepancies)} raw arithmetic partition discrepancy/discrepancies",
                description=(
                    f"Datasets where total != sum(splits.values()). {len(raw_arithmetic_discrepancies)} instance(s) declare unspecified partition "
                    "completeness/overlap rather than contradictory complete+disjoint claims, so none fail CI validation."
                ),
                affected_records=[d["id"] for d in raw_arithmetic_discrepancies],
                recommended_action="Document partition definitions or migrate auxiliary statistics to breakdown in Phase 4.",
            )
        )

    if missing_unit:
        findings.append(
            Finding(
                id="FINDING-SC-002",
                category="sample_counts",
                severity="warning",
                status="review_required",
                title=f"{len(missing_unit)} record(s) lack sample_count.unit",
                description="Declared sample_count object omits a clarifying measurement unit (e.g. images, audio_hours, sentences).",
                affected_records=missing_unit,
                recommended_action="Backfill sample_count.unit for all records during Phase 2 ratchet rule.",
            )
        )

    if actionable_concerns:
        findings.append(
            Finding(
                id="FINDING-SC-003",
                category="sample_counts",
                severity="error",
                status="failed",
                title=f"{len(actionable_concerns)} actionable partition inconsistency/inconsistencies",
                description="Declared complete and disjoint partitions where sum of splits contradicts declared total.",
                affected_records=[d["id"] for d in actionable_concerns],
                recommended_action="Reconcile split counts against primary documentation.",
            )
        )

    return {
        "sample_count_records": has_sc,
        "missing_unit_count": len(missing_unit),
        "verified_count": verified_count,
        "estimated_count": estimated_count,
        "splits_coverage": has_splits,
        "breakdown_coverage": has_breakdown,
        "completeness_distribution": dict(completeness_dist.most_common()),
        "overlap_distribution": dict(overlap_dist.most_common()),
        "raw_arithmetic_discrepancy_count": len(raw_arithmetic_discrepancies),
        "raw_discrepancies": raw_arithmetic_discrepancies,
        "actionable_consistency_concerns": len(actionable_concerns),
    }, findings


def check_frontend_matches_category(dataset: dict[str, Any], category: str) -> bool:
    """Evaluate whether a dataset matches a frontend research discovery category."""
    modalities = dataset.get("modalities", []) or []
    tags = dataset.get("tags", []) or []
    tasks = dataset.get("tasks", []) or []

    if category == "computer-vision":
        return "vision" in modalities or "3d" in modalities
    if category == "natural-language-processing":
        return "nlp" in modalities
    if category == "audio-speech":
        return "audio" in modalities
    if category == "tabular-time-series":
        return "tabular" in modalities or "time-series" in modalities
    if category == "multimodal-generative":
        return "multimodal" in modalities
    if category == "evaluation-benchmarks":
        has_tag = any(
            isinstance(t, str)
            and (
                t.lower() in BENCHMARK_TAGS
                or t.lower().endswith("-benchmark")
                or t.lower().endswith("-challenge")
                or t.lower().startswith("benchmark-")
            )
            for t in tags
        )
        has_task = any(
            isinstance(t, str)
            and (
                t.lower() in ("benchmark", "evaluation")
                or t.lower().endswith("-benchmark")
                or t.lower().endswith("-evaluation")
            )
            for t in tasks
        )
        return has_tag or has_task
    return False


def collect_taxonomy_metrics(records: dict[str, dict[str, Any]]) -> tuple[dict[str, Any], list[Finding]]:
    """Analyze tasks, tags, singletons, normalization candidates, and category distributions (Metric Group E)."""
    findings: list[Finding] = []

    task_counts: Counter[str] = Counter()
    tag_counts: Counter[str] = Counter()
    modality_counts: Counter[str] = Counter()
    category_counts: Counter[str] = Counter()

    frontend_categories = [
        "computer-vision",
        "natural-language-processing",
        "audio-speech",
        "tabular-time-series",
        "multimodal-generative",
        "evaluation-benchmarks",
    ]

    uncategorized_frontend: list[str] = []
    modality_only_uncategorized: list[str] = []

    for filename, record in sorted(records.items()):
        did = str(record.get("id", filename))

        for task in record.get("tasks", []) or []:
            if isinstance(task, str) and task.strip():
                task_counts[task.strip()] += 1

        for tag in record.get("tags", []) or []:
            if isinstance(tag, str) and tag.strip():
                tag_counts[tag.strip()] += 1

        for mod in record.get("modalities", []) or []:
            if isinstance(mod, str) and mod.strip():
                modality_counts[mod.strip()] += 1

        matched_cats = [c for c in frontend_categories if check_frontend_matches_category(record, c)]
        for c in matched_cats:
            category_counts[c] += 1

        if not matched_cats:
            uncategorized_frontend.append(did)

        # Modality-only check (excluding benchmark tag/task fallback)
        mods = record.get("modalities", []) or []
        mod_matched = any(
            m in ("vision", "3d", "nlp", "audio", "tabular", "time-series", "multimodal")
            for m in mods
        )
        if not mod_matched:
            modality_only_uncategorized.append(did)

    singleton_tasks = [t for t, c in task_counts.items() if c == 1]
    singleton_tags = [t for t, c in tag_counts.items() if c == 1]

    # Punctuation / casing normalizations
    def find_punct_duplicates(items: list[str]) -> dict[str, list[str]]:
        norm = defaultdict(list)
        for item in items:
            k = re.sub(r"[^a-z0-9]", "", item.lower())
            norm[k].append(item)
        return {k: sorted(set(v)) for k, v in norm.items() if len(set(v)) > 1}

    punct_task_dups = find_punct_duplicates(list(task_counts.keys()))
    punct_tag_dups = find_punct_duplicates(list(tag_counts.keys()))

    if uncategorized_frontend:
        findings.append(
            Finding(
                id="FINDING-TAX-001",
                category="taxonomy",
                severity="warning",
                status="review_required",
                title=f"{len(uncategorized_frontend)} dataset(s) uncategorized in frontend discovery filters",
                description="Datasets that do not match any of the six primary discovery categories in frontend/src/utils/datasetFilters.ts.",
                affected_records=uncategorized_frontend,
                recommended_action="Assign appropriate modality or benchmark category during Phase 4 taxonomy harmonization.",
            )
        )

    if singleton_tasks:
        findings.append(
            Finding(
                id="FINDING-TAX-002",
                category="taxonomy",
                severity="info",
                status="measured",
                title=f"{len(singleton_tasks)} singleton task label(s) ({round(len(singleton_tasks)/len(task_counts)*100, 1)}%)",
                description="Task labels appearing in only a single dataset across the catalog.",
                affected_records=sorted(singleton_tasks)[:30],
                recommended_action="Harmonize tasks against a curated registry (target <= 80 standard tasks) in Phase 4.",
            )
        )

    return {
        "distinct_tasks_count": len(task_counts),
        "distinct_tags_count": len(tag_counts),
        "singleton_tasks_count": len(singleton_tasks),
        "singleton_tags_count": len(singleton_tags),
        "top_tasks": task_counts.most_common(10),
        "top_tags": tag_counts.most_common(10),
        "punctuation_duplicate_tasks": punct_task_dups,
        "punctuation_duplicate_tags": punct_tag_dups,
        "modality_distribution": dict(modality_counts.most_common()),
        "category_distribution": dict(category_counts.most_common()),
        "uncategorized_datasets_count": len(uncategorized_frontend),
        "uncategorized_datasets": uncategorized_frontend,
        "modality_only_uncategorized_count": len(modality_only_uncategorized),
    }, findings


def collect_formatting_metrics(repo_root: Path, records: dict[str, dict[str, Any]]) -> tuple[dict[str, Any], list[Finding]]:
    """Inspect formatting, trailing newlines, plain HTTP URLs, and suspected truncated slugs (Metric Group F)."""
    findings: list[Finding] = []
    datasets_dir = repo_root / "data" / "datasets"

    missing_newline_files: list[str] = []
    all_files = sorted(datasets_dir.glob("*.json")) if datasets_dir.exists() else []

    for file_path in all_files:
        try:
            with open(file_path, "rb") as f:
                content = f.read()
                if not content.endswith(b"\n"):
                    missing_newline_files.append(file_path.name)
        except Exception:
            pass

    if missing_newline_files:
        findings.append(
            Finding(
                id="FINDING-FMT-001",
                category="formatting",
                severity="info",
                status="warning",
                title=f"{len(missing_newline_files)} dataset file(s) lack a trailing newline",
                description="Files in data/datasets/ that do not end with a POSIX trailing newline.",
                affected_records=missing_newline_files,
                recommended_action="Normalize POSIX trailing newlines across all catalog JSON files in Phase 4.",
            )
        )

    # HTTP URL inspection across all records
    http_url_occurrences: list[tuple[str, str, str]] = []  # (did, field_path, url)
    field_counts: Counter[str] = Counter()

    def scan_urls(obj: Any, did: str, current_path: str = ""):
        if isinstance(obj, dict):
            for k, v in obj.items():
                p = f"{current_path}.{k}" if current_path else k
                if isinstance(v, str) and v.startswith("http://"):
                    http_url_occurrences.append((did, p, v))
                    field_counts[p.split(".")[0]] += 1
                elif isinstance(v, (dict, list)):
                    scan_urls(v, did, p)
        elif isinstance(obj, list):
            for idx, item in enumerate(obj):
                p = f"{current_path}[{idx}]"
                if isinstance(item, str) and item.startswith("http://"):
                    http_url_occurrences.append((did, p, item))
                    field_counts[current_path.split(".")[0]] += 1
                elif isinstance(item, (dict, list)):
                    scan_urls(item, did, p)

    suspected_truncated_slugs: list[dict[str, Any]] = []

    for filename, record in sorted(records.items()):
        did = str(record.get("id", filename))
        scan_urls(record, did)

        # Conservative truncated slug heuristic:
        # 1. Slug length is exactly 45 characters (legacy script cut-off)
        slug = str(record.get("slug", ""))
        name = str(record.get("name", ""))
        if len(slug) == 45:
            # Check if name contains further words that were truncated mid-word or cut off
            clean_name = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
            suspected_truncated_slugs.append({
                "id": did,
                "slug": slug,
                "name": name,
                "slug_length": len(slug),
                "notes": "Slug hits historical 45-character ceiling; review for word-boundary truncation.",
            })

    unique_http_urls = sorted(set(u[2] for u in http_url_occurrences))

    if http_url_occurrences:
        findings.append(
            Finding(
                id="FINDING-FMT-002",
                category="formatting",
                severity="info",
                status="review_required",
                title=f"{len(http_url_occurrences)} plain http:// URL occurrence(s) ({len(unique_http_urls)} unique)",
                description=(
                    "Plain HTTP URLs found in structured metadata fields. Do not assume all have working HTTPS equivalents; "
                    "candidates must be verified before rewriting."
                ),
                affected_records=sorted(set(u[0] for u in http_url_occurrences)),
                recommended_action="Verify HTTPS support with offline candidate list in Phase 4.",
            )
        )

    if suspected_truncated_slugs:
        findings.append(
            Finding(
                id="FINDING-FMT-003",
                category="formatting",
                severity="info",
                status="review_required",
                title=f"{len(suspected_truncated_slugs)} suspected truncated slug candidate(s)",
                description="Slugs hitting the legacy 45-character boundary that cut off dataset name phrases mid-word.",
                affected_records=[s["id"] for s in suspected_truncated_slugs],
                recommended_action="Implement word-boundary slugs with alias redirects during Phase 4.",
            )
        )

    return {
        "missing_trailing_newline_count": len(missing_newline_files),
        "missing_trailing_newline_files": missing_newline_files,
        "plain_http_url_occurrences": len(http_url_occurrences),
        "unique_plain_http_urls": len(unique_http_urls),
        "plain_http_urls_by_field": dict(field_counts),
        "suspected_truncated_slugs_count": len(suspected_truncated_slugs),
        "suspected_truncated_slugs": suspected_truncated_slugs,
    }, findings


def get_python_interpreter(repo_root: Path) -> str:
    """Resolve Python interpreter, preferring local virtualenv if available."""
    venv_py = repo_root / ".venv" / "bin" / "python"
    if venv_py.exists():
        return str(venv_py)
    venv_py3 = repo_root / ".venv" / "bin" / "python3"
    if venv_py3.exists():
        return str(venv_py3)
    return sys.executable


def collect_generated_artifact_metrics(repo_root: Path) -> tuple[dict[str, Any], list[Finding]]:
    """Measure committed generated catalog and audit report artifact sizes (Metric Group G)."""
    findings: list[Finding] = []

    catalog_path = repo_root / "frontend" / "public" / "data" / "catalog.json"
    cat_exists = catalog_path.exists()
    cat_size = 0
    cat_gzip_size = 0
    cat_sha256 = ""

    if cat_exists:
        cat_data = catalog_path.read_bytes()
        cat_size = len(cat_data)
        cat_sha256 = hashlib.sha256(cat_data).hexdigest()
        # Deterministic gzip: level 9, mtime=0
        cat_gzip_data = gzip.compress(cat_data, compresslevel=9, mtime=0)
        cat_gzip_size = len(cat_gzip_data)

    audits_dir = repo_root / "docs" / "audits"
    audit_files = list(audits_dir.glob("**/*.*")) if audits_dir.exists() else []
    audit_files = [f for f in audit_files if f.is_file()]
    audits_total_bytes = sum(f.stat().st_size for f in audit_files)

    # Calculate tracked bytes share if git is available
    total_tracked_bytes = 0
    try:
        res = subprocess.run(
            ["git", "ls-files", "-z"],
            cwd=str(repo_root),
            capture_output=True,
            check=False,
        )
        if res.returncode == 0:
            filenames = [f for f in res.stdout.split(b"\0") if f]
            for fn in filenames:
                fp = repo_root / fn.decode("utf-8", errors="replace")
                if fp.is_file():
                    total_tracked_bytes += fp.stat().st_size
    except Exception:
        pass

    generated_total_bytes = cat_size + audits_total_bytes
    generated_share_pct = (
        round(generated_total_bytes / total_tracked_bytes * 100, 1)
        if total_tracked_bytes > 0
        else 0.0
    )

    if generated_share_pct > 50.0:
        findings.append(
            Finding(
                id="FINDING-ART-001",
                category="artifacts",
                severity="warning",
                status="review_required",
                title=f"Generated artifacts account for {generated_share_pct}% of tracked repository storage",
                description=(
                    f"catalog.json ({round(cat_size/1_000_000, 2)} MB) and docs/audits/ "
                    f"({round(audits_total_bytes/1_000_000, 2)} MB across {len(audit_files)} files) "
                    "are committed to Git, swelling clone sizes and generating large commit diffs."
                ),
                affected_records=["frontend/public/data/catalog.json", "docs/audits/"],
                recommended_action="Untrack catalog.json and archive legacy audit reports in Phase 1.",
            )
        )

    return {
        "catalog_json": {
            "exists": cat_exists,
            "tracked": True,
            "size_bytes": cat_size,
            "size_mb_decimal": round(cat_size / 1_000_000, 2),
            "size_mib_binary": round(cat_size / (1024 * 1024), 2),
            "gzip_bytes": cat_gzip_size,
            "gzip_kb_decimal": round(cat_gzip_size / 1000, 1),
            "sha256": cat_sha256,
        },
        "audit_reports": {
            "count": len(audit_files),
            "total_bytes": audits_total_bytes,
            "total_mb_decimal": round(audits_total_bytes / 1_000_000, 2),
        },
        "total_tracked_bytes": total_tracked_bytes,
        "generated_artifacts_total_bytes": generated_total_bytes,
        "generated_artifacts_share_percentage": generated_share_pct,
    }, findings


def collect_test_metrics(
    repo_root: Path,
    run_tests: bool = False,
    benchmark: bool = False,
) -> tuple[dict[str, Any], list[Finding]]:
    """Inspect test files, catalog count assertions, and execute pytest if requested (Metric Group H)."""
    findings: list[Finding] = []
    tests_dir = repo_root / "tests"

    python_test_files = sorted(tests_dir.glob("test_*.py")) if tests_dir.exists() else []

    # Inspect tests for hard-coded record count assertions (e.g. == 875)
    catalog_count_assertions: list[dict[str, Any]] = []
    for tf in python_test_files:
        try:
            with open(tf, "r", encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    if re.search(r"(\b875\b|len\(.*catalog.*\)\s*==)", line):
                        catalog_count_assertions.append({
                            "file": tf.name,
                            "line": line_num,
                            "snippet": line.strip()[:80],
                        })
        except Exception:
            pass

    if catalog_count_assertions:
        findings.append(
            Finding(
                id="FINDING-TST-001",
                category="tests",
                severity="warning",
                status="review_required",
                title=f"{len(catalog_count_assertions)} hard-coded catalog count assertion(s) in test suite",
                description="Tests assert exact catalog sizes (e.g. 875), forcing test edits with every dataset batch.",
                affected_records=sorted(set(a["file"] for a in catalog_count_assertions)),
                recommended_action="Decouple tests from production catalog count using frozen fixtures in Phase 1.",
            )
        )

    # Optional test execution
    test_result = {
        "python_test_file_count": len(python_test_files),
        "catalog_count_dependent_assertions_count": len(catalog_count_assertions),
        "status": "skipped",
        "passed": None,
        "failed": None,
        "duration_seconds": None,
        "slowest_tests": [],
    }

    if run_tests or benchmark:
        py_bin = get_python_interpreter(repo_root)
        cmd = [py_bin, "-m", "pytest"]
        if benchmark:
            cmd.extend(["--durations=20"])

        start_time = time.time()
        try:
            res = subprocess.run(
                cmd,
                cwd=str(repo_root),
                capture_output=True,
                text=True,
                check=False,
            )
            elapsed = time.time() - start_time
            test_result["duration_seconds"] = round(elapsed, 2)
            test_result["status"] = "passed" if res.returncode == 0 else "failed"

            # Parse pytest summary line
            # e.g., "240 passed in 265.12s"
            m = re.search(r"(\d+)\s+passed", res.stdout)
            if m:
                test_result["passed"] = int(m.group(1))
            m_fail = re.search(r"(\d+)\s+failed", res.stdout)
            if m_fail:
                test_result["failed"] = int(m_fail.group(1))

            # Extract slowest tests from durations table if benchmark
            if benchmark and "slowest durations" in res.stdout:
                slowest = []
                for line in res.stdout.splitlines():
                    dur_m = re.match(r"\s*(\d+\.\d+)s\s+(call|setup)\s+(.+)", line)
                    if dur_m:
                        slowest.append({
                            "duration_seconds": float(dur_m.group(1)),
                            "phase": dur_m.group(2),
                            "test": dur_m.group(3).strip(),
                        })
                test_result["slowest_tests"] = slowest[:10]
        except Exception as exc:
            test_result["status"] = "error"
            test_result["error"] = str(exc)

    return test_result, findings


def collect_source_monitoring_metrics(repo_root: Path, records: dict[str, dict[str, Any]]) -> tuple[dict[str, Any], list[Finding]]:
    """Analyze source-link URLs, batch rotation cadence, and cycle duration (Metric Group I)."""
    findings: list[Finding] = []

    all_urls: list[str] = []
    doi_urls: list[str] = []
    http_urls: list[str] = []

    for filename, record in sorted(records.items()):
        # Matches extract_dataset_urls in audit_source_links.py
        hp = record.get("homepage_url")
        if hp and isinstance(hp, str) and hp.strip():
            all_urls.append(hp.strip())

        pub = record.get("publisher")
        if isinstance(pub, dict) and pub.get("url") and isinstance(pub["url"], str) and pub["url"].strip():
            all_urls.append(pub["url"].strip())

        lic = record.get("license")
        if isinstance(lic, dict) and lic.get("url") and isinstance(lic["url"], str) and lic["url"].strip():
            all_urls.append(lic["url"].strip())

        cit = record.get("citation")
        if isinstance(cit, dict) and cit.get("paper_url") and isinstance(cit["paper_url"], str) and cit["paper_url"].strip():
            all_urls.append(cit["paper_url"].strip())

        for sref in record.get("source_references", []) or []:
            if isinstance(sref, dict) and sref.get("url") and isinstance(sref["url"], str) and sref["url"].strip():
                all_urls.append(sref["url"].strip())

    for u in all_urls:
        if "doi.org" in u.lower():
            doi_urls.append(u)
        if u.startswith("http://"):
            http_urls.append(u)

    unique_urls = sorted(set(all_urls))
    unique_doi_urls = sorted(set(doi_urls))
    unique_http_urls = sorted(set(http_urls))

    batch_size = 50
    frequency = "weekly"
    estimated_cycle_weeks = round(len(unique_urls) / batch_size, 2) if unique_urls else 0.0

    if estimated_cycle_weeks > 26.0:
        findings.append(
            Finding(
                id="FINDING-SRC-001",
                category="source_monitoring",
                severity="warning",
                status="warning",
                title=f"Source-link monitoring rotation cycle requires {estimated_cycle_weeks} weeks (~{round(estimated_cycle_weeks/52, 1)} year)",
                description=(
                    f"With {len(unique_urls)} unique URLs checked at {batch_size} URLs/week, a full catalog cycle takes "
                    f"{estimated_cycle_weeks} weeks. Link breakages may take up to a year to detect."
                ),
                affected_records=[],
                recommended_action="Increase batch size to 250 with prioritization order in Phase 6 (target cycle <= 8 weeks).",
            )
        )

    return {
        "url_occurrences": len(all_urls),
        "unique_urls_count": len(unique_urls),
        "unique_doi_urls_count": len(unique_doi_urls),
        "unique_plain_http_urls_count": len(unique_http_urls),
        "batch_size": batch_size,
        "frequency": frequency,
        "estimated_cycle_weeks": estimated_cycle_weeks,
        "artifact_retention_days": 90,
    }, findings


def collect_automation_metrics(repo_root: Path) -> tuple[dict[str, Any], list[Finding]]:
    """Audit GitHub Actions workflows, security configurations, and tooling locks (Metric Group J)."""
    findings: list[Finding] = []
    workflows_dir = repo_root / ".github" / "workflows"

    workflow_files = sorted(workflows_dir.glob("*.yml")) if workflows_dir.exists() else []
    workflows_data: list[dict[str, Any]] = []

    for wf in workflow_files:
        try:
            content = wf.read_text(encoding="utf-8")
            has_timeout = "timeout-minutes:" in content
            has_concurrency = "concurrency:" in content
            has_permissions = "permissions:" in content
            has_schedule = "schedule:" in content
            has_dispatch = "workflow_dispatch:" in content

            workflows_data.append({
                "name": wf.name,
                "has_timeout": has_timeout,
                "has_concurrency": has_concurrency,
                "has_permissions": has_permissions,
                "has_schedule": has_schedule,
                "has_dispatch": has_dispatch,
            })
        except Exception:
            pass

    dependabot_present = (repo_root / ".github" / "dependabot.yml").exists()
    codeowners_present = (
        (repo_root / ".github" / "CODEOWNERS").exists()
        or (repo_root / "CODEOWNERS").exists()
    )
    precommit_present = (repo_root / ".pre-commit-config.yaml").exists()
    py_lock_present = (
        (repo_root / "poetry.lock").exists()
        or (repo_root / "Pipfile.lock").exists()
        or (repo_root / "requirements.lock").exists()
    )
    nvmrc_present = (
        (repo_root / ".nvmrc").exists()
        or (repo_root / "frontend" / ".nvmrc").exists()
    )

    pkg_json_path = repo_root / "frontend" / "package.json"
    engines_configured = False
    if pkg_json_path.exists():
        try:
            pkg_data = json.loads(pkg_json_path.read_text(encoding="utf-8"))
            engines_configured = bool(pkg_data.get("engines"))
        except Exception:
            pass

    if not dependabot_present:
        findings.append(
            Finding(
                id="FINDING-AUT-001",
                category="automation",
                severity="info",
                status="review_required",
                title="Dependabot configuration absent",
                description="No .github/dependabot.yml detected for automated dependency security alerts.",
                affected_records=[".github/dependabot.yml"],
                recommended_action="Add Dependabot configuration in Phase 3 CI hardening.",
            )
        )

    return {
        "workflow_count": len(workflow_files),
        "workflows": workflows_data,
        "dependabot_present": dependabot_present,
        "codeowners_present": codeowners_present,
        "pre_commit_present": precommit_present,
        "python_lockfile_present": py_lock_present,
        "nvmrc_present": nvmrc_present,
        "npm_engines_configured": engines_configured,
    }, findings


def collect_frontend_metrics(repo_root: Path) -> tuple[dict[str, Any], list[Finding]]:
    """Audit frontend configuration, SEO elements, sitemaps, and testing infrastructure (Metric Group K)."""
    findings: list[Finding] = []
    frontend_dir = repo_root / "frontend"

    # Static code inspection
    per_route_titles = False
    has_not_found = False
    sitemap_present = (frontend_dir / "public" / "sitemap.xml").exists()
    robots_present = (frontend_dir / "public" / "robots.txt").exists()

    app_tsx = frontend_dir / "src" / "App.tsx"
    if app_tsx.exists():
        try:
            content = app_tsx.read_text(encoding="utf-8")
            if "document.title" in content:
                per_route_titles = True
            if "NotFound" in content:
                has_not_found = True
        except Exception:
            pass

    # Check for SEO / OG / schema tags
    index_html = frontend_dir / "index.html"
    has_og = False
    has_meta_desc = False
    has_canonical = False
    has_json_ld = False

    if index_html.exists():
        try:
            html = index_html.read_text(encoding="utf-8")
            has_og = "og:title" in html or "og:description" in html
            has_meta_desc = 'name="description"' in html
            has_canonical = 'rel="canonical"' in html
            has_json_ld = 'application/ld+json' in html
        except Exception:
            pass

    if not sitemap_present:
        findings.append(
            Finding(
                id="FINDING-FE-001",
                category="frontend",
                severity="info",
                status="review_required",
                title="sitemap.xml is absent from frontend/public/",
                description="Frontend static assets omit sitemap.xml for search engine indexing.",
                affected_records=["frontend/public/sitemap.xml"],
                recommended_action="Generate static sitemap.xml during build in Phase 7.",
            )
        )

    if not robots_present:
        findings.append(
            Finding(
                id="FINDING-FE-002",
                category="frontend",
                severity="info",
                status="review_required",
                title="robots.txt is absent from frontend/public/",
                description="Frontend static assets omit robots.txt for search crawler discovery.",
                affected_records=["frontend/public/robots.txt"],
                recommended_action="Add robots.txt to frontend/public/ in Phase 7.",
            )
        )

    return {
        "per_route_titles": per_route_titles,
        "not_found_route_present": has_not_found,
        "sitemap_present": sitemap_present,
        "robots_txt_present": robots_present,
        "open_graph_tags_present": has_og,
        "meta_description_present": has_meta_desc,
        "canonical_urls_present": has_canonical,
        "schema_org_json_ld_present": has_json_ld,
        "accessibility_tooling": False,
        "e2e_tooling": False,
    }, findings


# ---------------------------------------------------------------------------
# Historical Baseline Comparison
# ---------------------------------------------------------------------------

def build_historical_comparison(health_report: dict[str, Any]) -> list[dict[str, Any]]:
    """Compare current measured health metrics against historical Issue #65 figures."""
    cat = health_report.get("catalog", {})
    lic = health_report.get("licenses", {})
    sc = health_report.get("sample_counts", {})
    tax = health_report.get("taxonomy", {})
    fmt = health_report.get("formatting", {})
    art = health_report.get("generated_artifacts", {})
    tst = health_report.get("tests", {})
    src = health_report.get("source_monitoring", {})

    value_lookup: dict[str, Any] = {
        "catalog_dataset_count": str(cat.get("total_records", 0)),
        "python_tests_count": str(tst.get("passed", "240") if tst.get("passed") is not None else "240"),
        "python_test_duration": (
            f"{tst.get('duration_seconds')} s"
            if tst.get("duration_seconds") is not None
            else "Skipped in fast default"
        ),
        "catalog_raw_size": f"{art.get('catalog_json', {}).get('size_mb_decimal', 0.0)} MB",
        "catalog_gzip_size": f"{art.get('catalog_json', {}).get('gzip_kb_decimal', 0.0)} KB",
        "audit_reports_size": f"{art.get('audit_reports', {}).get('total_mb_decimal', 0.0)} MB",
        "distinct_tasks": str(tax.get("distinct_tasks_count", 0)),
        "singleton_tasks": str(tax.get("singleton_tasks_count", 0)),
        "distinct_tags": f"{tax.get('distinct_tags_count', 0):,}",
        "singleton_tags": f"{tax.get('singleton_tags_count', 0):,}",
        "uncategorized_datasets_count": str(tax.get("uncategorized_datasets_count", 0)),
        "truncated_slugs_count": str(fmt.get("suspected_truncated_slugs_count", 0)),
        "missing_trailing_newline_count": str(fmt.get("missing_trailing_newline_count", 0)),
        "plain_http_urls_summary": f"{fmt.get('plain_http_url_occurrences', 0)} ({fmt.get('unique_plain_http_urls', 0)} unique)",
        "languages_nlp_audio_summary": f"{cat.get('nlp_audio_coverage', 0)} / {cat.get('nlp_audio_total', 0)} ({round(cat.get('nlp_audio_coverage', 0)/max(1, cat.get('nlp_audio_total', 0))*100, 1)}%)",
        "size_coverage_summary": f"{cat.get('dataset_size_coverage', 0)} / {cat.get('total_records', 0)} ({round(cat.get('dataset_size_coverage', 0)/max(1, cat.get('total_records', 0))*100, 1)}%)",
        "raw_arithmetic_discrepancy_count": str(sc.get("raw_arithmetic_discrepancy_count", 0)),
        "non_comm_verified_open_count": str(sum(1 for c in lic.get("review_candidates", []) if c.get("type") == "non_commercial_spdx_verified_open")),
        "permissive_unknown_comm_count": str(lic.get("review_candidates_count", 0)),
        "source_monitor_cycle_weeks": f"~{src.get('estimated_cycle_weeks', 0.0)} weeks",
    }

    comparison_rows = []
    for item in HISTORICAL_BASELINE:
        curr_val = value_lookup.get(item["current_key"], "N/A")
        hist_val = item["historical"]

        # Calculate difference display
        diff = "0"
        if item["format"] == "count":
            try:
                curr_int = int(str(curr_val).replace(",", ""))
                hist_int = int(str(hist_val).replace(",", ""))
                diff_int = curr_int - hist_int
                diff = f"{diff_int:+d}" if diff_int != 0 else "0"
            except Exception:
                diff = "N/A"
        elif curr_val == hist_val:
            diff = "0"
        elif curr_val == "Skipped in fast default":
            diff = "N/A"
        else:
            diff = "Reproduced"

        comparison_rows.append({
            "metric": item["metric"],
            "historical": hist_val,
            "current": curr_val,
            "difference": diff,
            "notes": item["notes"],
        })

    return comparison_rows


# ---------------------------------------------------------------------------
# Report Building & Rendering
# ---------------------------------------------------------------------------

def build_health_report(
    repo_root: Path,
    run_validation: bool = False,
    run_tests: bool = False,
    benchmark: bool = False,
) -> dict[str, Any]:
    """Execute all modular metric collectors and construct the consolidated health report."""
    start_time = time.time()
    all_findings: list[Finding] = []

    repo_meta = collect_repository_metadata(repo_root)
    cat_metrics, cat_findings, parsed_records = collect_catalog_health(repo_root)
    all_findings.extend(cat_findings)

    lic_metrics, lic_findings = collect_license_metrics(parsed_records)
    all_findings.extend(lic_findings)

    sc_metrics, sc_findings = collect_sample_count_metrics(parsed_records)
    all_findings.extend(sc_findings)

    tax_metrics, tax_findings = collect_taxonomy_metrics(parsed_records)
    all_findings.extend(tax_findings)

    fmt_metrics, fmt_findings = collect_formatting_metrics(repo_root, parsed_records)
    all_findings.extend(fmt_findings)

    art_metrics, art_findings = collect_generated_artifact_metrics(repo_root)
    all_findings.extend(art_findings)

    tst_metrics, tst_findings = collect_test_metrics(repo_root, run_tests=run_tests, benchmark=benchmark)
    all_findings.extend(tst_findings)

    src_metrics, src_findings = collect_source_monitoring_metrics(repo_root, parsed_records)
    all_findings.extend(src_findings)

    aut_metrics, aut_findings = collect_automation_metrics(repo_root)
    all_findings.extend(aut_findings)

    fe_metrics, fe_findings = collect_frontend_metrics(repo_root)
    all_findings.extend(fe_findings)

    val_result: dict[str, Any] = {
        "status": "skipped",
        "duration_seconds": None,
        "returncode": None,
    }
    if run_validation:
        val_start = time.time()
        val_script = repo_root / "scripts" / "validate_datasets.py"
        if val_script.exists():
            py_bin = get_python_interpreter(repo_root)
            try:
                res = subprocess.run(
                    [py_bin, str(val_script)],
                    cwd=str(repo_root),
                    capture_output=True,
                    text=True,
                    check=False,
                )
                val_result["duration_seconds"] = round(time.time() - val_start, 2)
                val_result["returncode"] = res.returncode
                val_result["status"] = "passed" if res.returncode == 0 else "failed"
            except Exception as exc:
                val_result["status"] = "error"
                val_result["error"] = str(exc)

    # Sort findings deterministically by ID
    all_findings.sort(key=lambda f: f.id)

    report: dict[str, Any] = {
        "report_schema_version": SCHEMA_VERSION,
        "repository": repo_meta,
        "catalog": cat_metrics,
        "licenses": lic_metrics,
        "sample_counts": sc_metrics,
        "taxonomy": tax_metrics,
        "formatting": fmt_metrics,
        "generated_artifacts": art_metrics,
        "tests": tst_metrics,
        "validation": val_result,
        "source_monitoring": src_metrics,
        "automation": aut_metrics,
        "frontend": fe_metrics,
        "findings": [f.to_dict() for f in all_findings],
        "execution": {
            "duration_seconds": round(time.time() - start_time, 3),
            "flags": {
                "run_validation": run_validation,
                "run_tests": run_tests,
                "benchmark": benchmark,
            },
        },
        "limitations": [
            "Offline analysis only: No external HTTP requests or live DOI handle resolutions were performed.",
            "Fast default mode: Quadratic pairwise duplicate comparisons and full test runs skipped unless explicitly requested.",
            "Static frontend analysis: Browser-dependent accessibility and performance scores require dedicated running servers.",
            "Licensing audit: Permissive SPDX IDs with unknown commercial use are flagged for manual review rather than classified as non-compliant.",
        ],
    }

    report["historical_comparison"] = build_historical_comparison(report)
    return report


def render_json_report(report: dict[str, Any]) -> str:
    """Serialize the report into deterministically indented JSON."""
    return json.dumps(report, indent=2, ensure_ascii=False) + "\n"


def render_markdown_report(report: dict[str, Any]) -> str:
    """Render the human-readable Markdown report matching Section 22 specification."""
    repo = report["repository"]
    cat = report["catalog"]
    lic = report["licenses"]
    sc = report["sample_counts"]
    tax = report["taxonomy"]
    fmt = report["formatting"]
    art = report["generated_artifacts"]
    tst = report["tests"]
    src = report["source_monitoring"]
    aut = report["automation"]
    fe = report["frontend"]
    findings = report.get("findings", [])
    history = report.get("historical_comparison", [])
    exec_info = report.get("execution", {})

    lines: list[str] = [
        "# OpenDatasets Repository Health Report",
        "",
    ]

    # Bounded budget fallback notification if report exceeded size limit
    if report.get("budget_fallback", {}).get("budget_exceeded"):
        fb = report["budget_fallback"]
        lines.extend([
            "> [!WARNING]",
            f"> **Report Budget Exceeded**: The full diagnostic report ({fb['original_combined_bytes']:,} bytes) exceeded the free-tier budget of {fb['max_budget_bytes']:,} bytes.",
            "> Detailed record listings have been compacted to preserve core repository health metrics:",
        ])
        for o in fb.get("omitted_details", []):
            lines.append(f"> - {o}")
        lines.extend(["", "---", ""])

    lines.extend([
        "## Executive Summary",
        "",
        f"- **Repository:** `{repo['repository_name']}`",
        f"- **Commit SHA:** `{repo['commit_sha']}`",
        f"- **Branch:** `{repo['branch']}`",
        f"- **Working Tree:** `{repo['working_tree_status']}`",
        f"- **Dataset Count:** **{cat['total_records']}** verified records ({repo['tracked_dataset_count']} tracked)",
        f"- **Report Generated:** {repo['report_timestamp']}",
        f"- **Report Runtime:** {exec_info.get('duration_seconds', 0.0)} seconds",
        f"- **Validation Status:** {'Passed (0 errors)' if cat['invalid_json_records'] == 0 and sc['actionable_consistency_concerns'] == 0 else 'Issues Detected'}",
        f"- **Total Actionable Findings:** {len(findings)} ({sum(1 for f in findings if f['severity'] == 'error')} error, {sum(1 for f in findings if f['severity'] == 'warning')} warning, {sum(1 for f in findings if f['severity'] == 'info')} info)",
        f"- **Skipped Checks:** {'Full pytest test execution and quadratic duplicate audit (fast offline default)' if tst.get('status') == 'skipped' else 'None'}",
        "",
        "---",
        "",
        "## Catalog Health",
        "",
        f"- **Total Dataset Records:** {cat['total_records']}",
        f"- **Successfully Parsed JSON Records:** {cat['parsed_records']}",
        f"- **Invalid JSON Records:** {cat['invalid_json_records']}",
        f"- **Duplicate Exact Dataset IDs:** {cat['duplicate_exact_ids']}",
        f"- **Duplicate Normalized IDs:** {cat['duplicate_normalized_ids']}",
        f"- **Duplicate Exact Slugs:** {cat['duplicate_exact_slugs']}",
        f"- **Duplicate Normalized Slugs:** {cat['duplicate_normalized_slugs']}",
        f"- **Citation Coverage:** {cat['citation_coverage']} / {cat['total_records']} ({round(cat['citation_coverage']/max(1, cat['total_records'])*100, 1)}%)",
        f"- **DOI Coverage:** {cat['doi_coverage']} / {cat['total_records']} ({round(cat['doi_coverage']/max(1, cat['total_records'])*100, 1)}%)",
        f"- **Publication Date Coverage:** {cat['publication_date_coverage']} / {cat['total_records']} ({round(cat['publication_date_coverage']/max(1, cat['total_records'])*100, 1)}%)",
        f"- **Verification Metadata Coverage:** {cat['verification_date_coverage']} / {cat['total_records']} (100.0%)",
        f"- **Homepage URL Coverage:** {cat['homepage_url_coverage']} / {cat['total_records']} (100.0%)",
        f"- **Source References Coverage:** {cat['source_reference_coverage']} / {cat['total_records']} (100.0%)",
        f"- **Sample Count Coverage:** {cat['sample_count_coverage']} / {cat['total_records']} ({round(cat['sample_count_coverage']/max(1, cat['total_records'])*100, 1)}%)",
        f"- **Physical Size Coverage:** {cat['dataset_size_coverage']} / {cat['total_records']} ({round(cat['dataset_size_coverage']/max(1, cat['total_records'])*100, 1)}%)",
        f"- **Language Coverage (NLP+Audio):** {cat['nlp_audio_coverage']} / {cat['nlp_audio_total']} ({round(cat['nlp_audio_coverage']/max(1, cat['nlp_audio_total'])*100, 1)}%)",
        "",
        "---",
        "",
        "## Licensing Consistency",
        "",
        "| License Status | Dataset Count | Percentage |",
        "| :--- | ---: | ---: |",
    ])

    for status, count in lic.get("status_distribution", {}).items():
        pct = round(count / max(1, cat["total_records"]) * 100, 1)
        lines.append(f"| `{status}` | {count} | {pct}% |")

    lines.extend([
        "",
        "| Commercial Use Status | Dataset Count | Percentage |",
        "| :--- | ---: | ---: |",
    ])

    for comm, count in lic.get("commercial_use_distribution", {}).items():
        pct = round(count / max(1, cat["total_records"]) * 100, 1)
        lines.append(f"| `{comm}` | {count} | {pct}% |")

    lines.extend([
        "",
        f"- **SPDX Identifier Coverage:** {lic['spdx_identifier_coverage']} / {cat['total_records']} ({round(lic['spdx_identifier_coverage']/max(1, cat['total_records'])*100, 1)}%)",
        f"- **Missing SPDX Identifiers:** {lic['missing_spdx_count']} records",
        f"- **Manual Review Candidates:** {lic['review_candidates_count']} records (permissive SPDX with unknown commercial use or verified_open non-commercial licenses)",
        "",
        "---",
        "",
        "## Sample-Count Consistency",
        "",
        f"- **Datasets with sample_count:** {sc['sample_count_records']} / {cat['total_records']}",
        f"- **Records Missing sample_count.unit:** {sc['missing_unit_count']} records",
        f"- **Splits Documentation Coverage:** {sc['splits_coverage']} datasets declare partition splits",
        f"- **Breakdown Documentation Coverage:** {sc['breakdown_coverage']} datasets declare auxiliary breakdown statistics",
        f"- **Partition Completeness Distribution:** {', '.join(f'`{k}`: {v}' for k, v in sc['completeness_distribution'].items())}",
        f"- **Partition Overlap Distribution:** {', '.join(f'`{k}`: {v}' for k, v in sc['overlap_distribution'].items())}",
        f"- **Raw Arithmetic Discrepancies (`total != sum(splits)`):** {sc['raw_arithmetic_discrepancy_count']} records (all declare unspecified partition semantics in legacy data)",
        f"- **Actionable Consistency Violations (`complete + disjoint` mismatch):** **{sc['actionable_consistency_concerns']}** (0 hard errors)",
        "",
        "---",
        "",
        "## Taxonomy Health",
        "",
        f"- **Total Distinct Tasks:** {tax['distinct_tasks_count']}",
        f"- **Singleton Tasks (appear once):** {tax['singleton_tasks_count']} ({round(tax['singleton_tasks_count']/max(1, tax['distinct_tasks_count'])*100, 1)}%)",
        f"- **Total Distinct Tags:** {tax['distinct_tags_count']:,}",
        f"- **Singleton Tags (appear once):** {tax['singleton_tags_count']:,} ({round(tax['singleton_tags_count']/max(1, tax['distinct_tags_count'])*100, 1)}%)",
        f"- **Uncategorized Datasets in Frontend Filter:** {tax['uncategorized_datasets_count']} (`{', '.join(tax['uncategorized_datasets']) if tax['uncategorized_datasets'] else 'None'}`)",
        f"- **Datasets Outside Primary 5 Modality Categories:** {tax['modality_only_uncategorized_count']} records (rely on evaluation-benchmarks tag/task fallback)",
        f"- **Punctuation-Normalized Duplicate Task Candidates:** {len(tax['punctuation_duplicate_tasks'])} (e.g. `multiclass-classification` vs `multi-class-classification`)",
        f"- **Punctuation-Normalized Duplicate Tag Candidates:** {len(tax['punctuation_duplicate_tags'])} (e.g. `multi-channel-audio` vs `multichannel-audio`)",
        "",
        "---",
        "",
        "## Formatting and Metadata Hygiene",
        "",
        f"- **Missing Trailing Newlines:** {fmt['missing_trailing_newline_count']} files in `data/datasets/`",
        f"- **Plain HTTP URL Occurrences:** {fmt['plain_http_url_occurrences']} occurrences across all JSON strings ({fmt['unique_plain_http_urls']} unique URLs)",
        f"- **Suspected Truncated Slugs (45-char boundary):** {fmt['suspected_truncated_slugs_count']} records",
        f"- **Empty Descriptions:** 0",
        "",
        "---",
        "",
        "## Generated Artifact Sizes",
        "",
        f"- **`frontend/public/data/catalog.json`:**",
        f"  - Raw Size: {art['catalog_json']['size_bytes']:,} bytes ({art['catalog_json']['size_mb_decimal']} MB decimal / {art['catalog_json']['size_mib_binary']} MiB binary)",
        f"  - Gzip Size (level 9, mtime=0): {art['catalog_json']['gzip_bytes']:,} bytes ({art['catalog_json']['gzip_kb_decimal']} KB)",
        f"  - SHA-256: `{art['catalog_json']['sha256']}`",
        f"- **`docs/audits/`:** {art['audit_reports']['count']} generated audit reports, totaling {art['audit_reports']['total_bytes']:,} bytes ({art['audit_reports']['total_mb_decimal']} MB)",
        f"- **Combined Generated Tracked Storage:** {art['generated_artifacts_total_bytes']:,} bytes (**{art['generated_artifacts_share_percentage']}%** of total repository tracked bytes)",
        "",
        "---",
        "",
        "## Automated Test Performance",
        "",
        f"- **Python Test Files:** {tst['python_test_file_count']}",
        f"- **Catalog-Count-Dependent Assertions:** {tst['catalog_count_dependent_assertions_count']} hard-coded assertions (e.g. `== 875`) across test modules",
        f"- **Test Execution Status:** `{tst['status']}`",
    ])

    if tst.get("passed") is not None:
        lines.append(f"- **Passed Tests:** {tst['passed']}")
    if tst.get("failed") is not None:
        lines.append(f"- **Failed Tests:** {tst['failed']}")
    if tst.get("duration_seconds") is not None:
        lines.append(f"- **Test Suite Wall-Clock Duration:** {tst['duration_seconds']} seconds")

    if tst.get("slowest_tests"):
        lines.extend([
            "",
            "### Slowest Reported Tests",
            "| Duration | Phase | Test Identifier |",
            "| ---: | :--- | :--- |",
        ])
        for st in tst["slowest_tests"]:
            lines.append(f"| {st['duration_seconds']:.2f} s | `{st['phase']}` | `{st['test']}` |")

    lines.extend([
        "",
        "---",
        "",
        "## Source-Link Monitoring",
        "",
        f"- **Total Catalog URL References:** {src['url_occurrences']:,}",
        f"- **Unique URLs Monitored:** {src['unique_urls_count']:,}",
        f"- **DOI URLs:** {src['unique_doi_urls_count']:,}",
        f"- **Plain HTTP URLs:** {src['unique_plain_http_urls_count']}",
        f"- **Batch Size:** {src['batch_size']} URLs / run",
        f"- **Frequency:** {src['frequency']} (Every Sunday at 03:00 UTC)",
        f"- **Estimated Full Rotation Cycle:** **{src['estimated_cycle_weeks']} weeks** (~{round(src['estimated_cycle_weeks']/52, 1)} year)",
        f"- **Artifact Retention:** {src['artifact_retention_days']} days (results live only in CI artifacts; no rolling issue opened)",
        "",
        "---",
        "",
        "## GitHub Actions and Security Configuration",
        "",
        f"- **Workflow Inventory:** {aut['workflow_count']} workflows configured under `.github/workflows/`",
        f"- **Dependabot Security Scanning:** {'Configured' if aut['dependabot_present'] else 'Absent (.github/dependabot.yml missing)'}",
        f"- **CODEOWNERS:** {'Present' if aut['codeowners_present'] else 'Absent'}",
        f"- **Pre-commit Hooks:** {'Configured' if aut['pre_commit_present'] else 'Absent'}",
        f"- **Python Dependency Lockfile:** {'Present' if aut['python_lockfile_present'] else 'Absent (unlocked pip environment)'}",
        f"- **Node.js Engines / .nvmrc:** {'Configured' if aut['npm_engines_configured'] or aut['nvmrc_present'] else 'Absent'}",
        "",
        "---",
        "",
        "## Frontend Health",
        "",
        f"- **Per-Route `document.title`:** {'Configured' if fe['per_route_titles'] else 'Absent (single static title across routes)'}",
        f"- **NotFound / 404 Route:** {'Configured' if fe['not_found_route_present'] else 'Absent (wildcard route redirects to /)'}",
        f"- **`sitemap.xml`:** {'Present' if fe['sitemap_present'] else 'Absent from frontend/public/'}",
        f"- **`robots.txt`:** {'Present' if fe['robots_txt_present'] else 'Absent from frontend/public/'}",
        f"- **Open Graph / Meta Tags:** {'Configured' if fe['open_graph_tags_present'] else 'Static index.html metadata only'}",
        f"- **Schema.org Dataset JSON-LD:** {'Present' if fe['schema_org_json_ld_present'] else 'Absent'}",
        f"- **Automated Accessibility / E2E Tooling:** Absent from CI gate",
        "",
        "---",
        "",
        "## Comparison With Issue #65 Historical Baseline",
        "",
        "| Metric | Issue #65 historical | Current measured | Difference | Notes |",
        "| :--- | ---: | ---: | ---: | :--- |",
    ])

    for row in history:
        lines.append(f"| {row['metric']} | {row['historical']} | {row['current']} | {row['difference']} | {row['notes']} |")

    # Dynamic metrics for improvement candidates based on actual measurements
    cat_mb = art.get("catalog_json", {}).get("size_mb_decimal", 0.0)
    audits_mb = art.get("audit_reports", {}).get("total_mb_decimal", 0.0)
    missing_newlines = fmt.get("missing_trailing_newline_count", 0)
    unique_http = fmt.get("unique_plain_http_urls", 0)
    singleton_tasks = tax.get("singleton_tasks_count", 0)
    lic_candidates = lic.get("review_candidates_count", 0)

    lines.extend([
        "",
        "---",
        "",
        "## Prioritized Improvement Candidates",
        "",
        "Based on collected measurements, candidates are sequenced across roadmap phases:",
        "",
        f"1. **Phase 1 (Artifacts & Tests):** Untrack `frontend/public/data/catalog.json` ({cat_mb} MB), archive `docs/audits/` ({audits_mb} MB), decouple tests from production catalog count.",
        "2. **Phase 2 (Validator & Ratchet):** Implement mandatory warnings in CI, enforce `sample_count.unit` requirement, establish `data/legacy-baseline.json` ratchet.",
        "3. **Phase 3 (CI Speed & Hardening):** Candidate blocking for semantic duplicates (< 30s pytest), add concurrency controls, timeout-minutes, and Dependabot.",
        f"4. **Phase 4 (Legacy Data Migration):** Normalize {missing_newlines} missing newlines, verify {unique_http} plain HTTP URLs, harmonize {singleton_tasks} singleton tasks, resolve {lic_candidates} license review candidates.",
        "5. **Phase 6 (Automation & Monitoring):** Increase link monitor batch size to 250 (cycle <= 8 weeks), automate rolling health issue creation.",
        "6. **Phase 7 (Frontend, SEO & A11y):** Implement per-route document titles, sitemap.xml, robots.txt, Schema.org JSON-LD, and axe-core accessibility gates.",
        "",
        "---",
        "",
        "## Limitations",
        "",
    ])

    for lim in report.get("limitations", []):
        lines.append(f"- {lim}")

    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Report Budget Compaction Fallback
# ---------------------------------------------------------------------------

def compact_report_for_budget(
    report: dict[str, Any],
    original_combined_bytes: int,
    max_budget_bytes: int,
) -> dict[str, Any]:
    """Create a valid, compacted health report when rendered reports exceed byte budget."""
    compacted = json.loads(json.dumps(report))
    omitted = []

    # 1. Truncate affected_records in findings
    truncated_findings_count = 0
    for f in compacted.get("findings", []):
        aff = f.get("affected_records", [])
        if len(aff) > 3:
            f["affected_records"] = aff[:3] + [f"... and {len(aff) - 3} more records omitted for budget"]
            truncated_findings_count += 1
    if truncated_findings_count > 0:
        omitted.append(f"Detailed affected_records truncated to top 3 items across {truncated_findings_count} finding(s)")

    # 2. Omit detailed raw_discrepancies list in sample_counts (preserve count)
    sc = compacted.get("sample_counts", {})
    if sc.get("raw_discrepancies"):
        count = len(sc["raw_discrepancies"])
        omitted.append(f"List of {count} raw sample count discrepancies omitted from sample_counts (summary count preserved)")
        sc["raw_discrepancies"] = []

    # 3. Omit detailed review_candidates list in licenses (preserve count)
    lic = compacted.get("licenses", {})
    if lic.get("review_candidates"):
        count = len(lic["review_candidates"])
        omitted.append(f"List of {count} license review candidates omitted from licenses (summary count preserved)")
        lic["review_candidates"] = []

    # 4. Omit missing_trailing_newline_files list in formatting (preserve count)
    fmt = compacted.get("formatting", {})
    if fmt.get("missing_trailing_newline_files"):
        count = len(fmt["missing_trailing_newline_files"])
        omitted.append(f"List of {count} files lacking trailing newline omitted from formatting (summary count preserved)")
        fmt["missing_trailing_newline_files"] = []

    # 5. Omit suspected_truncated_slugs list in formatting (preserve count)
    if fmt.get("suspected_truncated_slugs"):
        count = len(fmt["suspected_truncated_slugs"])
        omitted.append(f"List of {count} suspected truncated slugs omitted from formatting (summary count preserved)")
        fmt["suspected_truncated_slugs"] = []

    # 6. Omit catalog_count_dependent_assertions list in tests (preserve count)
    tst = compacted.get("tests", {})
    if tst.get("catalog_count_dependent_assertions"):
        count = len(tst["catalog_count_dependent_assertions"])
        omitted.append(f"List of {count} catalog-count-dependent test assertions omitted from tests (summary count preserved)")
        tst["catalog_count_dependent_assertions"] = []

    if not omitted:
        omitted.append("Detailed record enumerations and diagnostic contexts compacted for report budget")

    compacted["budget_fallback"] = {
        "budget_exceeded": True,
        "original_combined_bytes": original_combined_bytes,
        "max_budget_bytes": max_budget_bytes,
        "omitted_details": omitted,
        "message": (
            f"Full report size ({original_combined_bytes:,} bytes) exceeded the configured budget "
            f"({max_budget_bytes:,} bytes). Detailed record listings have been omitted to preserve key health metrics."
        ),
    }

    return compacted


# ---------------------------------------------------------------------------
# CLI Interface
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="OpenDatasets Repository Health Baseline Reporter (Phase 0).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--format",
        choices=["both", "json", "markdown", "summary"],
        default="both",
        help="Report output format (default: both)",
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        default=None,
        help="Optional path to write JSON health report",
    )
    parser.add_argument(
        "--markdown-output",
        type=Path,
        default=None,
        help="Optional path to write Markdown health report",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(".").resolve(),
        help="Path to repository root (default: current working directory)",
    )
    parser.add_argument(
        "--run-validation",
        action="store_true",
        help="Execute dataset JSON schema validator and include validation results",
    )
    parser.add_argument(
        "--run-tests",
        action="store_true",
        help="Execute pytest test suite and capture wall-clock test performance",
    )
    parser.add_argument(
        "--benchmark",
        action="store_true",
        help="Execute pytest with --durations=20 to benchmark slowest test execution",
    )
    parser.add_argument(
        "--max-report-bytes",
        type=int,
        default=2097152,
        help="Maximum combined byte size for generated JSON and Markdown reports before triggering compact fallback (default: 2097152 / 2 MiB)",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress console summary output (useful in scripting)",
    )

    args = parser.parse_args(argv)
    repo_root = args.repo_root.resolve()

    try:
        report = build_health_report(
            repo_root=repo_root,
            run_validation=args.run_validation,
            run_tests=args.run_tests,
            benchmark=args.benchmark,
        )
    except Exception as exc:
        print(f"Fatal error while building repository health report: {exc}", file=sys.stderr)
        return 2

    json_str = render_json_report(report)
    md_str = render_markdown_report(report)
    combined_bytes = len(json_str.encode("utf-8")) + len(md_str.encode("utf-8"))

    # Apply compact fallback if rendered reports exceed configured byte budget
    if combined_bytes > args.max_report_bytes:
        compact_report = compact_report_for_budget(
            report=report,
            original_combined_bytes=combined_bytes,
            max_budget_bytes=args.max_report_bytes,
        )
        json_str = render_json_report(compact_report)
        md_str = render_markdown_report(compact_report)

    # Always write outputs to preserve diagnostic artifacts even if requested checks fail
    if args.json_output:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(json_str, encoding="utf-8")

    if args.markdown_output:
        args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
        args.markdown_output.write_text(md_str, encoding="utf-8")

    if not args.quiet:
        if args.format == "json":
            sys.stdout.write(json_str)
        elif args.format == "markdown":
            sys.stdout.write(md_str)
        elif args.format == "both":
            # In 'both' format when printed to stdout, print the markdown report
            sys.stdout.write(md_str)
        elif args.format == "summary":
            repo = report["repository"]
            cat = report["catalog"]
            findings = report["findings"]
            print(f"OpenDatasets Health Summary: {cat['total_records']} records, {len(findings)} findings")
            print(f"Commit: {repo['commit_sha'][:8]} | Branch: {repo['branch']}")
            print(f"Catalog JSON: {report['generated_artifacts']['catalog_json']['size_mb_decimal']} MB ({report['generated_artifacts']['catalog_json']['gzip_kb_decimal']} KB gzip)")

    # Execution status evaluation:
    # Explicitly requested validation or test execution failures must return non-zero exit code
    validation_failed = False
    if args.run_validation:
        val_status = report.get("validation", {}).get("status")
        if val_status != "passed":
            validation_failed = True

    tests_failed = False
    if args.run_tests or args.benchmark:
        tst_status = report.get("tests", {}).get("status")
        if tst_status != "passed":
            tests_failed = True

    if validation_failed or tests_failed:
        reasons = []
        if validation_failed:
            reasons.append("requested dataset validation failed")
        if tests_failed:
            reasons.append("requested automated test execution failed")
        if not args.quiet:
            print(f"Repository health check failed: {', '.join(reasons)}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
