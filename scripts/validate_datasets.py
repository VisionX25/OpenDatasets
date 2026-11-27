#!/usr/bin/env python3
"""OpenDatasets Dataset Metadata Validator & Quality Ratchet Engine.

Validates dataset JSON metadata files against the OpenDatasets JSON Schema,
verifies URL syntax without performing network requests, ensures uniqueness
of dataset IDs and slugs, enforces scientific metadata rules (licensing, dates,
formatting, sample count units, languages), and manages the legacy violation
baseline with monotonic ratchet enforcement.
"""

from __future__ import annotations

import argparse
import collections
from collections import defaultdict
import dataclasses
from dataclasses import asdict, dataclass, field
import datetime
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Any
from urllib.parse import urlparse

try:
    import jsonschema
    from jsonschema.exceptions import ValidationError
except ImportError:
    print(
        "Error: 'jsonschema' package is required. Install with: pip install jsonschema",
        file=sys.stderr,
    )
    sys.exit(1)


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.validation_helpers import (
    ENTITY_STEMS,
    KNOWN_SPECIAL_SEMANTIC_REVIEWS,
    STANDARD_PARTITION_KEYWORDS,
    check_unit_compatibility,
    extract_discriminating_features,
    is_generic_hosting_url,
    is_partition_key,
    normalize_doi,
    normalize_title,
    normalize_url,
)

DEFAULT_SCHEMA_PATH = (
    Path("schemas/dataset.v1.schema.json")
    if Path("schemas/dataset.v1.schema.json").exists()
    else REPO_ROOT / "schemas" / "dataset.v1.schema.json"
)
DEFAULT_DATA_DIR = (
    Path("data/datasets")
    if Path("data/datasets").exists()
    else REPO_ROOT / "data" / "datasets"
)
DEFAULT_BASELINE_PATH = (
    Path("data/legacy-baseline.json")
    if Path("data/legacy-baseline.json").exists()
    else REPO_ROOT / "data" / "legacy-baseline.json"
)

# Severities
SEVERITY_FATAL_ERROR = "fatal_error"
SEVERITY_RATCHETABLE_WARNING = "ratchetable_warning"
SEVERITY_MANUAL_REVIEW = "manual_review"
SEVERITY_INFORMATIONAL = "informational"

# BCP 47 language tag validation regex
# Allows standard language codes (2 or 3 letters) optionally followed by script, region, or variant subtags
BCP47_REGEX = re.compile(r"^[a-zA-Z]{2,3}(?:-[a-zA-Z0-9]{2,8})*$")

# Non-commercial license keywords
NON_COMMERCIAL_PATTERNS = ("-nc", "nc-", "non-commercial")

# Permissive license prefixes
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

# Textual NLP tasks
NLP_TASKS = {
    "text-classification",
    "question-answering",
    "machine-translation",
    "named-entity-recognition",
    "natural-language-inference",
    "summarization",
    "sentiment-analysis",
    "dialogue",
    "reading-comprehension",
    "speech-recognition",
    "audio-transcription",
    "text-generation",
    "language-modeling",
    "information-extraction",
    "pos-tagging",
    "token-classification",
    "coreference-resolution",
    "semantic-parsing",
    "relation-extraction",
    "dependency-parsing",
}


@dataclass
class ValidationFinding:
    """Structured validation finding with stable rule ID and deterministic fingerprint."""

    rule_id: str
    dataset_id: str
    file_path: str
    field_path: str
    severity: str  # fatal_error, ratchetable_warning, manual_review, informational
    message: str
    fingerprint: str
    is_grandfathered: bool = False
    blocks_validation: bool = False
    remediation: str = ""

    def __str__(self) -> str:
        return f"{self.file_path} [{self.field_path}]: {self.message}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "fingerprint": self.fingerprint,
            "rule_id": self.rule_id,
            "dataset_id": self.dataset_id,
            "file_path": self.file_path,
            "field_path": self.field_path,
            "severity": self.severity,
            "message": self.message,
            "is_grandfathered": self.is_grandfathered,
            "blocks_validation": self.blocks_validation,
            "remediation": self.remediation,
        }


def make_fingerprint(rule_id: str, dataset_id: str, field_path: str) -> str:
    """Generate deterministic fingerprint free of volatile timestamps or system paths."""
    clean_field = field_path.strip().replace(" ", "_") if field_path else "<root>"
    return f"{rule_id}:{dataset_id}:{clean_field}"


def is_valid_http_url(url: Any) -> tuple[bool, str]:
    """Validate HTTP/HTTPS URL syntax without making network requests."""
    if not isinstance(url, str):
        return False, "URL must be a string."
    if not url.strip():
        return False, "URL must not be empty or whitespace."
    if re.search(r"\s", url):
        return False, f"URL contains whitespace: '{url}'"

    try:
        parsed = urlparse(url)
    except Exception as exc:
        return False, f"Failed to parse URL '{url}': {exc}"

    if parsed.scheme not in ("http", "https"):
        return (
            False,
            f"URL scheme must be 'http' or 'https', got '{parsed.scheme}' in '{url}'",
        )
    if not parsed.netloc:
        return False, f"URL is missing a network domain (netloc) in '{url}'"

    return True, ""


def find_urls_in_dict(obj: Any, current_path: str = "") -> list[tuple[str, str]]:
    """Recursively collect (json_path, url_value) pairs from a JSON structure."""
    urls: list[tuple[str, str]] = []
    if isinstance(obj, dict):
        for key, val in obj.items():
            sub_path = f"{current_path}.{key}" if current_path else key
            if key == "url" or key.endswith("_url"):
                if isinstance(val, str):
                    urls.append((sub_path, val))
            urls.extend(find_urls_in_dict(val, sub_path))
    elif isinstance(obj, list):
        for idx, item in enumerate(obj):
            sub_path = f"{current_path}[{idx}]"
            urls.extend(find_urls_in_dict(item, sub_path))
    return urls


def load_json_findings(file_path: Path) -> tuple[dict[str, Any] | None, list[ValidationFinding]]:
    """Load JSON from a file with duplicate key and formatting checks, returning findings."""
    findings: list[ValidationFinding] = []
    if not file_path.exists():
        fp = make_fingerprint("FMT-003", file_path.stem, "<file>")
        findings.append(
            ValidationFinding(
                rule_id="FMT-003",
                dataset_id=file_path.stem,
                file_path=str(file_path),
                field_path="<file>",
                severity=SEVERITY_FATAL_ERROR,
                message=f"File not found: {file_path}",
                fingerprint=fp,
                blocks_validation=True,
            )
        )
        return None, findings

    if not file_path.is_file():
        fp = make_fingerprint("FMT-003", file_path.stem, "<file>")
        findings.append(
            ValidationFinding(
                rule_id="FMT-003",
                dataset_id=file_path.stem,
                file_path=str(file_path),
                field_path="<file>",
                severity=SEVERITY_FATAL_ERROR,
                message=f"Path is not a regular file: {file_path}",
                fingerprint=fp,
                blocks_validation=True,
            )
        )
        return None, findings

    try:
        raw_bytes = file_path.read_bytes()
    except Exception as exc:
        fp = make_fingerprint("FMT-003", file_path.stem, "<file>")
        findings.append(
            ValidationFinding(
                rule_id="FMT-003",
                dataset_id=file_path.stem,
                file_path=str(file_path),
                field_path="<file>",
                severity=SEVERITY_FATAL_ERROR,
                message=f"Error reading raw bytes: {exc}",
                fingerprint=fp,
                blocks_validation=True,
            )
        )
        return None, findings

    # FMT-003: UTF-8 validation
    try:
        content = raw_bytes.decode("utf-8")
        if "\ufffd" in content:
            fp = make_fingerprint("FMT-003", file_path.stem, "<file>")
            findings.append(
                ValidationFinding(
                    rule_id="FMT-003",
                    dataset_id=file_path.stem,
                    file_path=str(file_path),
                    field_path="<file>",
                    severity=SEVERITY_FATAL_ERROR,
                    message="File contains Unicode replacement characters (invalid UTF-8 sequence)",
                    fingerprint=fp,
                    blocks_validation=True,
                )
            )
    except UnicodeDecodeError as exc:
        fp = make_fingerprint("FMT-003", file_path.stem, "<file>")
        findings.append(
            ValidationFinding(
                rule_id="FMT-003",
                dataset_id=file_path.stem,
                file_path=str(file_path),
                field_path="<file>",
                severity=SEVERITY_FATAL_ERROR,
                message=f"Invalid UTF-8 encoding: {exc}",
                fingerprint=fp,
                blocks_validation=True,
            )
        )
        return None, findings

    # FMT-001: Trailing newline check (Ratchetable Warning)
    if not raw_bytes.endswith(b"\n"):
        fp = make_fingerprint("FMT-001", file_path.stem, "formatting.trailing_newline")
        findings.append(
            ValidationFinding(
                rule_id="FMT-001",
                dataset_id=file_path.stem,
                file_path=str(file_path),
                field_path="formatting.trailing_newline",
                severity=SEVERITY_RATCHETABLE_WARNING,
                message="File is missing a trailing newline",
                fingerprint=fp,
                remediation="Add a trailing newline at end of file",
            )
        )

    if not content.strip():
        fp = make_fingerprint("FMT-003", file_path.stem, "<file>")
        findings.append(
            ValidationFinding(
                rule_id="FMT-003",
                dataset_id=file_path.stem,
                file_path=str(file_path),
                field_path="<file>",
                severity=SEVERITY_FATAL_ERROR,
                message="File is empty",
                fingerprint=fp,
                blocks_validation=True,
            )
        )
        return None, findings

    # FMT-002: Duplicate key detection (Fatal Error)
    duplicate_keys: list[str] = []

    def object_pairs_hook(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        seen = set()
        for k, v in pairs:
            if k in seen:
                duplicate_keys.append(k)
            seen.add(k)
        return dict(pairs)

    try:
        data = json.loads(content, object_pairs_hook=object_pairs_hook)
    except json.JSONDecodeError as exc:
        fp = make_fingerprint("FMT-003", file_path.stem, "<syntax>")
        findings.append(
            ValidationFinding(
                rule_id="FMT-003",
                dataset_id=file_path.stem,
                file_path=str(file_path),
                field_path="<syntax>",
                severity=SEVERITY_FATAL_ERROR,
                message=f"Malformed JSON (line {exc.lineno}, col {exc.colno}): {exc.msg}",
                fingerprint=fp,
                blocks_validation=True,
            )
        )
        return None, findings

    if duplicate_keys:
        for dup in duplicate_keys:
            fp = make_fingerprint("FMT-002", file_path.stem, dup)
            findings.append(
                ValidationFinding(
                    rule_id="FMT-002",
                    dataset_id=file_path.stem,
                    file_path=str(file_path),
                    field_path=dup,
                    severity=SEVERITY_FATAL_ERROR,
                    message=f"Duplicate JSON key '{dup}' detected",
                    fingerprint=fp,
                    blocks_validation=True,
                )
            )

    if not isinstance(data, dict):
        fp = make_fingerprint("FMT-003", file_path.stem, "<root>")
        findings.append(
            ValidationFinding(
                rule_id="FMT-003",
                dataset_id=file_path.stem,
                file_path=str(file_path),
                field_path="<root>",
                severity=SEVERITY_FATAL_ERROR,
                message="Top-level JSON entity must be an object",
                fingerprint=fp,
                blocks_validation=True,
            )
        )
        return None, findings

    return data, findings


def load_json_file(file_path: Path) -> tuple[dict[str, Any] | None, list[str]]:
    """Load JSON from a file, returning (parsed_data, error_messages)."""
    data, findings = load_json_findings(file_path)
    if data is None:
        errors = [f.message for f in findings if f.severity == SEVERITY_FATAL_ERROR]
        return None, errors or ["Failed to load JSON file"]
    return data, []


def load_schema(schema_path: Path) -> tuple[dict[str, Any] | None, list[str]]:
    """Load and validate the JSON schema definition."""
    if not schema_path.exists():
        return None, [f"Schema file not found: {schema_path}"]
    try:
        content = schema_path.read_text(encoding="utf-8")
        data = json.loads(content)
        jsonschema.Draft7Validator.check_schema(data)
        return data, []
    except Exception as exc:
        return None, [f"Schema '{schema_path}' is invalid: {exc}"]


def parse_iso_date(date_str: Any) -> tuple[tuple[int, int, int] | None, str]:
    """Parse ISO date (YYYY, YYYY-MM, YYYY-MM-DD) and validate calendar bounds."""
    if not isinstance(date_str, str):
        return None, "Date must be a string"
    clean = date_str.strip()
    match = re.match(r"^(\d{4})(?:-(\d{2})(?:-(\d{2}))?)?$", clean)
    if not match:
        return None, f"Invalid date format '{date_str}'; expected YYYY, YYYY-MM, or YYYY-MM-DD"
    year = int(match.group(1))
    m_str = match.group(2)
    d_str = match.group(3)
    month = int(m_str) if m_str is not None else 1
    day = int(d_str) if d_str is not None else 1

    if m_str is not None and (month < 1 or month > 12):
        return None, f"Invalid calendar month in '{date_str}'"

    if d_str is not None:
        try:
            datetime.date(year, month, day)
        except ValueError as exc:
            return None, f"Invalid calendar date '{date_str}': {exc}"

    return (year, month, day), ""


def check_licensing_rules(data: dict[str, Any], file_path: str) -> list[ValidationFinding]:
    """Check licensing consistency rules (LIC-001, LIC-002, LIC-REV-001)."""
    findings: list[ValidationFinding] = []
    did = data.get("id", Path(file_path).stem)
    lic = data.get("license")

    if not lic or not isinstance(lic, dict):
        return findings

    spdx = (lic.get("spdx_id") or "").strip()
    spdx_lower = spdx.lower()
    name = (lic.get("name") or "").strip()
    name_lower = name.lower()
    status = lic.get("status", "")
    comm_use = lic.get("commercial_use")

    is_nc_spdx = any(p in spdx_lower for p in NON_COMMERCIAL_PATTERNS)
    is_mixed_or_conditional = any(kw in name_lower for kw in ["subset", "dual", "mixed", "except", "derivative", "/", "code and", "data and"])
    is_nc_name = (not is_mixed_or_conditional) and any(p in name_lower for p in NON_COMMERCIAL_PATTERNS)
    is_non_commercial = is_nc_spdx or is_nc_name

    # LIC-001: Contradiction: non-commercial license with commercial_use allowed (Fatal Error)
    if is_non_commercial and (comm_use is True or comm_use == "allowed"):
        fp = make_fingerprint("LIC-001", did, "license.commercial_use")
        findings.append(
            ValidationFinding(
                rule_id="LIC-001",
                dataset_id=did,
                file_path=file_path,
                field_path="license.commercial_use",
                severity=SEVERITY_FATAL_ERROR,
                message=f"Contradictory licensing: non-commercial license '{spdx or name}' declared with commercial_use={comm_use}",
                fingerprint=fp,
                blocks_validation=True,
                remediation="Set license.commercial_use to forbidden or update license if commercial use is permitted",
            )
        )

    # LIC-002: Non-commercial SPDX identifier with status verified_open (Ratchetable Warning)
    if is_nc_spdx and status == "verified_open":
        fp = make_fingerprint("LIC-002", did, "license.status")
        findings.append(
            ValidationFinding(
                rule_id="LIC-002",
                dataset_id=did,
                file_path=file_path,
                field_path="license.status",
                severity=SEVERITY_RATCHETABLE_WARNING,
                message=f"Non-commercial SPDX identifier '{spdx}' is incompatible with license status 'verified_open'",
                fingerprint=fp,
                remediation="Update license.status to 'custom_license' or another accurate non-open status",
            )
        )

    # LIC-REV-001: Permissive SPDX where commercial_use is unspecified or unverified (Manual Review)
    is_permissive = any(spdx_lower.startswith(prefix) for prefix in PERMISSIVE_SPDX_PREFIXES)
    if is_permissive and (comm_use in (None, "unknown") or status != "verified_open"):
        fp = make_fingerprint("LIC-REV-001", did, "license.commercial_use")
        findings.append(
            ValidationFinding(
                rule_id="LIC-REV-001",
                dataset_id=did,
                file_path=file_path,
                field_path="license.commercial_use",
                severity=SEVERITY_MANUAL_REVIEW,
                message=f"Permissive SPDX identifier '{spdx}' has unverified commercial_use ({comm_use}) or status ({status})",
                fingerprint=fp,
                remediation="Review license terms and verify commercial_use and verification status",
            )
        )

    return findings


def check_date_rules(data: dict[str, Any], file_path: str) -> list[ValidationFinding]:
    """Check date sanity and chronological consistency rules (DATE-001, DATE-002, DATE-003, DATE-REV-001)."""
    findings: list[ValidationFinding] = []
    did = data.get("id", Path(file_path).stem)

    dates_obj = data.get("dates") if isinstance(data.get("dates"), dict) else {}
    pub_str = dates_obj.get("published") or data.get("published")
    pub_field = "dates.published" if dates_obj.get("published") else "published"

    upd_str = dates_obj.get("last_updated") or data.get("last_updated")
    upd_field = "dates.last_updated" if dates_obj.get("last_updated") else "last_updated"

    ver_data = data.get("verification") if isinstance(data.get("verification"), dict) else {}
    ver_str = ver_data.get("verified_date") or data.get("verified_date")
    ver_field = "verification.verified_date" if ver_data.get("verified_date") else "verified_date"

    parsed_pub, pub_err = parse_iso_date(pub_str) if pub_str else (None, "")
    parsed_upd, upd_err = parse_iso_date(upd_str) if upd_str else (None, "")
    parsed_ver, ver_err = parse_iso_date(ver_str) if ver_str else (None, "")

    # DATE-001: Invalid calendar dates (Fatal Error)
    if pub_str and pub_err:
        fp = make_fingerprint("DATE-001", did, pub_field)
        findings.append(
            ValidationFinding(
                rule_id="DATE-001",
                dataset_id=did,
                file_path=file_path,
                field_path=pub_field,
                severity=SEVERITY_FATAL_ERROR,
                message=f"Invalid published date: {pub_err}",
                fingerprint=fp,
                blocks_validation=True,
            )
        )
    if upd_str and upd_err:
        fp = make_fingerprint("DATE-001", did, upd_field)
        findings.append(
            ValidationFinding(
                rule_id="DATE-001",
                dataset_id=did,
                file_path=file_path,
                field_path=upd_field,
                severity=SEVERITY_FATAL_ERROR,
                message=f"Invalid last_updated date: {upd_err}",
                fingerprint=fp,
                blocks_validation=True,
            )
        )
    if ver_str and ver_err:
        fp = make_fingerprint("DATE-001", did, ver_field)
        findings.append(
            ValidationFinding(
                rule_id="DATE-001",
                dataset_id=did,
                file_path=file_path,
                field_path=ver_field,
                severity=SEVERITY_FATAL_ERROR,
                message=f"Invalid verified_date: {ver_err}",
                fingerprint=fp,
                blocks_validation=True,
            )
        )

    # DATE-002: Inverted chronology last_updated < published (Ratchetable Warning)
    if parsed_pub and parsed_upd and parsed_upd < parsed_pub:
        fp = make_fingerprint("DATE-002", did, upd_field)
        findings.append(
            ValidationFinding(
                rule_id="DATE-002",
                dataset_id=did,
                file_path=file_path,
                field_path=upd_field,
                severity=SEVERITY_RATCHETABLE_WARNING,
                message=f"Inverted date chronology: last_updated ({upd_str}) is earlier than published ({pub_str})",
                fingerprint=fp,
                remediation="Ensure last_updated is on or after published date",
            )
        )

    # DATE-003: Future verification dates (Ratchetable Warning)
    current_year = datetime.datetime.now().year
    if parsed_ver and parsed_ver[0] > current_year:
        fp = make_fingerprint("DATE-003", did, ver_field)
        findings.append(
            ValidationFinding(
                rule_id="DATE-003",
                dataset_id=did,
                file_path=file_path,
                field_path=ver_field,
                severity=SEVERITY_RATCHETABLE_WARNING,
                message=f"Verification date '{ver_str}' is in the future",
                fingerprint=fp,
                remediation="Correct verified_date to actual date of verification",
            )
        )

    # DATE-REV-001: Publication date earlier than computing era (< 1940) (Manual Review)
    if parsed_pub and parsed_pub[0] < 1940:
        fp = make_fingerprint("DATE-REV-001", did, "published")
        findings.append(
            ValidationFinding(
                rule_id="DATE-REV-001",
                dataset_id=did,
                file_path=file_path,
                field_path="published",
                severity=SEVERITY_MANUAL_REVIEW,
                message=f"Publication date ({pub_str}) precedes modern computing era; review for historical digitization",
                fingerprint=fp,
                remediation="Confirm publication date represents historical archive release or digitization",
            )
        )

    return findings


def check_sample_count_rules(data: dict[str, Any], file_path: str) -> list[ValidationFinding]:
    """Check sample-count unit and partition arithmetic rules (SMP-001, SMP-002, SMP-REV-001)."""
    findings: list[ValidationFinding] = []
    did = data.get("id", Path(file_path).stem)
    sc = data.get("sample_count")

    if not sc or not isinstance(sc, dict):
        return findings

    # SMP-001: Missing unit when sample_count present (Ratchetable Warning)
    unit = sc.get("unit")
    if not unit or not str(unit).strip():
        fp = make_fingerprint("SMP-001", did, "sample_count.unit")
        findings.append(
            ValidationFinding(
                rule_id="SMP-001",
                dataset_id=did,
                file_path=file_path,
                field_path="sample_count.unit",
                severity=SEVERITY_RATCHETABLE_WARNING,
                message="Missing required 'unit' in sample_count metadata",
                fingerprint=fp,
                remediation="Specify the sample unit (e.g., 'samples', 'images', 'recordings', 'documents')",
            )
        )

    # Partition consistency checks
    total = sc.get("total")
    splits = sc.get("splits")
    if total is not None and isinstance(total, int) and splits and isinstance(splits, dict):
        split_values = [v for v in splits.values() if isinstance(v, (int, float))]
        if split_values:
            split_sum = sum(split_values)
            completeness = sc.get("partition_completeness", "unspecified")
            overlap = sc.get("partition_overlap", "unspecified")
            u_str = str(unit or "")

            is_compatible, unit_reason = check_unit_compatibility(splits, u_str, did=did)

            # SMP-002: Partition split sum mismatch when complete, disjoint, compatible (Fatal Error)
            if completeness in ("complete", "exhaustive") and overlap in ("disjoint", "mutually_exclusive"):
                if is_compatible:
                    if split_sum != total:
                        fp = make_fingerprint("SMP-002", did, "sample_count.splits")
                        findings.append(
                            ValidationFinding(
                                rule_id="SMP-002",
                                dataset_id=did,
                                file_path=file_path,
                                field_path="sample_count.splits",
                                severity=SEVERITY_FATAL_ERROR,
                                message=f"Partition splits sum ({split_sum}) does not equal declared total ({total}) despite explicit declaration of complete and disjoint partitions.",
                                fingerprint=fp,
                                blocks_validation=True,
                                remediation="Correct split counts or declared total, or adjust partition completeness/overlap metadata",
                            )
                        )
                else:
                    fp = make_fingerprint("SMP-REV-001", did, "sample_count.splits")
                    findings.append(
                        ValidationFinding(
                            rule_id="SMP-REV-001",
                            dataset_id=did,
                            file_path=file_path,
                            field_path="sample_count.splits",
                            severity=SEVERITY_MANUAL_REVIEW,
                            message=f"Declared complete and disjoint partitions have unresolved unit compatibility ({unit_reason}) — review required.",
                            fingerprint=fp,
                            remediation="Review partition split units for consistency with sample count unit",
                        )
                    )
            elif completeness == "partial":
                if split_sum > total and overlap in ("disjoint", "mutually_exclusive"):
                    fp = make_fingerprint("SMP-REV-001", did, "sample_count.splits")
                    findings.append(
                        ValidationFinding(
                            rule_id="SMP-REV-001",
                            dataset_id=did,
                            file_path=file_path,
                            field_path="sample_count.splits",
                            severity=SEVERITY_MANUAL_REVIEW,
                            message=f"Disjoint partial splits sum ({split_sum}) exceeds declared total ({total}).",
                            fingerprint=fp,
                            remediation="Ensure partial partition splits do not exceed declared sample count total",
                        )
                    )
            elif completeness == "unspecified":
                u_display = unit or "unspecified"
                if not is_compatible:
                    if "mismatch" in unit_reason.lower() or did in KNOWN_SPECIAL_SEMANTIC_REVIEWS:
                        msg = f"Apparent unit mismatch between splits and total ({u_display}) — review required."
                    elif "non-partition" in unit_reason.lower() or "mixed" in unit_reason.lower():
                        msg = f"Heterogeneous or non-partition split keys detected ({unit_reason}) — review required."
                    elif split_sum != total:
                        msg = (
                            f"Partition splits sum ({split_sum}) does not match total ({total}) "
                            "under unspecified partition semantics (completeness/overlap) — review required."
                        )
                    else:
                        msg = None
                    if msg:
                        fp = make_fingerprint("SMP-REV-001", did, "sample_count.splits")
                        findings.append(
                            ValidationFinding(
                                rule_id="SMP-REV-001",
                                dataset_id=did,
                                file_path=file_path,
                                field_path="sample_count.splits",
                                severity=SEVERITY_MANUAL_REVIEW,
                                message=msg,
                                fingerprint=fp,
                                remediation="Review partition splits for completeness or overlap",
                            )
                        )
                elif split_sum != total:
                    fp = make_fingerprint("SMP-REV-001", did, "sample_count.splits")
                    findings.append(
                        ValidationFinding(
                            rule_id="SMP-REV-001",
                            dataset_id=did,
                            file_path=file_path,
                            field_path="sample_count.splits",
                            severity=SEVERITY_MANUAL_REVIEW,
                            message=(
                                f"Partition splits sum ({split_sum}) does not match total ({total}) "
                                "under unspecified partition semantics (completeness/overlap) — review required."
                            ),
                            fingerprint=fp,
                            remediation="Review partition splits for completeness or overlap",
                        )
                    )

    return findings


def check_slug_rules(data: dict[str, Any], file_path: str) -> list[ValidationFinding]:
    """Check slug format and length rules (SLUG-001, SLUG-002, SLUG-REV-001)."""
    findings: list[ValidationFinding] = []
    file_stem = Path(file_path).stem
    did = data.get("id", file_stem)
    slug = data.get("slug")

    if not slug or not isinstance(slug, str):
        fp = make_fingerprint("SLUG-001", did, "slug")
        findings.append(
            ValidationFinding(
                rule_id="SLUG-001",
                dataset_id=did,
                file_path=file_path,
                field_path="slug",
                severity=SEVERITY_FATAL_ERROR,
                message=f"Missing or non-string slug in {file_path}",
                fingerprint=fp,
                blocks_validation=True,
            )
        )
        return findings

    # SLUG-001: Slug matches lowercase kebab-case (Fatal Error)
    kebab_match = re.match(r"^[a-z0-9]+(-[a-z0-9]+)*$", slug)
    if not kebab_match:
        fp = make_fingerprint("SLUG-001", did, "slug")
        findings.append(
            ValidationFinding(
                rule_id="SLUG-001",
                dataset_id=did,
                file_path=file_path,
                field_path="slug",
                severity=SEVERITY_FATAL_ERROR,
                message=f"Slug '{slug}' is not valid lowercase kebab-case",
                fingerprint=fp,
                blocks_validation=True,
                remediation="Ensure slug contains only lowercase letters, digits, and single hyphens",
            )
        )

    # SLUG-001: Slug length bounds [2, 80] (Fatal Error)
    if len(slug) < 2 or len(slug) > 80:
        fp = make_fingerprint("SLUG-001", did, "slug")
        findings.append(
            ValidationFinding(
                rule_id="SLUG-001",
                dataset_id=did,
                file_path=file_path,
                field_path="slug",
                severity=SEVERITY_FATAL_ERROR,
                message=f"Slug '{slug}' length ({len(slug)}) out of bounds [2, 80]",
                fingerprint=fp,
                blocks_validation=True,
            )
        )

    # SLUG-002: Slug matches dataset id and file stem (Ratchetable Warning)
    if slug != did:
        fp = make_fingerprint("SLUG-002", did, "slug")
        findings.append(
            ValidationFinding(
                rule_id="SLUG-002",
                dataset_id=did,
                file_path=file_path,
                field_path="slug",
                severity=SEVERITY_RATCHETABLE_WARNING,
                message=f"Slug '{slug}' does not match dataset id '{did}'",
                fingerprint=fp,
                remediation="Align slug and id to be identical",
            )
        )

    if file_stem not in ("<memory>", "test") and file_path.endswith(".json") and Path(file_path).exists():
        if slug != file_stem:
            fp = make_fingerprint("SLUG-002", did, "slug")
            findings.append(
                ValidationFinding(
                    rule_id="SLUG-002",
                    dataset_id=did,
                    file_path=file_path,
                    field_path="slug",
                    severity=SEVERITY_RATCHETABLE_WARNING,
                    message=f"Slug '{slug}' does not match JSON file stem '{file_stem}'",
                    fingerprint=fp,
                    remediation="Align slug and file stem to be identical",
                )
            )

    # SLUG-REV-001: 45-character mid-word truncation heuristic (Manual Review)
    if len(slug) == 45 and not slug.endswith("-"):
        fp = make_fingerprint("SLUG-REV-001", did, "slug")
        findings.append(
            ValidationFinding(
                rule_id="SLUG-REV-001",
                dataset_id=did,
                file_path=file_path,
                field_path="slug",
                severity=SEVERITY_MANUAL_REVIEW,
                message=f"Slug '{slug}' has length 45; review for legacy mid-word truncation",
                fingerprint=fp,
                remediation="Review if slug was truncated mid-word during import",
            )
        )

    return findings


def check_language_rules(data: dict[str, Any], file_path: str) -> list[ValidationFinding]:
    """Check language metadata rules (LANG-001, LANG-002, LANG-REV-001)."""
    findings: list[ValidationFinding] = []
    did = data.get("id", Path(file_path).stem)
    langs = data.get("languages")
    mods = data.get("modalities", [])
    tasks = data.get("tasks", [])

    # LANG-001: Valid BCP 47 language tags (Ratchetable Warning)
    if langs is not None and isinstance(langs, list):
        for idx, tag in enumerate(langs):
            if not isinstance(tag, str) or not BCP47_REGEX.match(tag.strip()):
                tag_display = str(tag)
                fp = make_fingerprint("LANG-001", did, f"languages[{idx}]")
                findings.append(
                    ValidationFinding(
                        rule_id="LANG-001",
                        dataset_id=did,
                        file_path=file_path,
                        field_path=f"languages[{idx}]",
                        severity=SEVERITY_RATCHETABLE_WARNING,
                        message=f"Language tag '{tag_display}' is not a valid BCP 47 tag (e.g. use 'mul' instead of 'multilingual')",
                        fingerprint=fp,
                        remediation="Replace with valid BCP 47 language code (e.g., 'en', 'mul', 'und', 'zh-CN')",
                    )
                )

    # LANG-002: Require languages for NLP modality datasets (Ratchetable Warning)
    # Non-speech audio (environmental, music, animal calls) is exempt since modality is 'audio' without 'nlp'
    is_nlp = "nlp" in mods
    has_languages = bool(langs and isinstance(langs, list) and len(langs) > 0)
    if is_nlp and not has_languages:
        fp = make_fingerprint("LANG-002", did, "languages")
        findings.append(
            ValidationFinding(
                rule_id="LANG-002",
                dataset_id=did,
                file_path=file_path,
                field_path="languages",
                severity=SEVERITY_RATCHETABLE_WARNING,
                message="Textual NLP dataset is missing required 'languages' metadata",
                fingerprint=fp,
                remediation="Declare applicable BCP 47 language tags in languages array (e.g., ['en'], ['mul'])",
            )
        )

    return findings


def validate_dataset_data(
    data: dict[str, Any],
    validator: jsonschema.Draft7Validator,
    filename: str = "<memory>",
    return_findings: bool = False,
) -> Any:
    """Validate a parsed dataset dictionary against schema and all Phase 2 semantic rules."""
    findings: list[ValidationFinding] = []
    did = data.get("id", Path(filename).stem)

    # 1. JSON Schema validation
    schema_errors = sorted(validator.iter_errors(data), key=lambda e: e.path)
    for err in schema_errors:
        path = ".".join(str(p) for p in err.path) if err.path else "<root>"
        fp = make_fingerprint("SCHEMA-001", did, path)
        findings.append(
            ValidationFinding(
                rule_id="SCHEMA-001",
                dataset_id=did,
                file_path=filename,
                field_path=path,
                severity=SEVERITY_FATAL_ERROR,
                message=f"Schema validation error: {err.message}",
                fingerprint=fp,
                blocks_validation=True,
            )
        )

    # 2. Deep URL syntax checks (no network access)
    urls = find_urls_in_dict(data)
    for json_path, url_val in urls:
        valid, msg = is_valid_http_url(url_val)
        if not valid:
            fp = make_fingerprint("URL-001", did, json_path)
            findings.append(
                ValidationFinding(
                    rule_id="URL-001",
                    dataset_id=did,
                    file_path=filename,
                    field_path=json_path,
                    severity=SEVERITY_FATAL_ERROR,
                    message=f"Invalid URL syntax - {msg}",
                    fingerprint=fp,
                    blocks_validation=True,
                )
            )

    # 3. Licensing rules
    findings.extend(check_licensing_rules(data, filename))

    # 4. Date sanity rules
    findings.extend(check_date_rules(data, filename))

    # 5. Sample count and partition rules
    findings.extend(check_sample_count_rules(data, filename))

    # 6. Slug rules
    findings.extend(check_slug_rules(data, filename))

    # 7. Language metadata rules
    findings.extend(check_language_rules(data, filename))

    if not return_findings:
        return [str(f) for f in findings if f.severity == SEVERITY_FATAL_ERROR]
    return findings


def check_partition_consistency(
    data: dict[str, Any],
    filename: str = "<memory>",
) -> tuple[list[str], list[str]]:
    """Legacy compatibility helper returning (errors, warnings) strings."""
    findings = check_sample_count_rules(data, filename)
    errors = [
        f"{filename} [sample_count]: {f.message}" if "[sample_count]" not in f.message else f.message
        for f in findings if f.severity == SEVERITY_FATAL_ERROR
    ]
    warnings = [
        f"{filename} [sample_count]: {f.message}" if "[sample_count]" not in f.message else f.message
        for f in findings if f.severity in (SEVERITY_MANUAL_REVIEW, SEVERITY_INFORMATIONAL) and f.rule_id == "SMP-REV-001"
    ]
    return errors, warnings


def validate_dataset_file(
    file_path: Path,
    validator: jsonschema.Draft7Validator,
    return_findings: bool = False,
) -> Any:
    """Validate a single dataset file, returning (data, errors) or (data, findings)."""
    data, load_findings = load_json_findings(file_path)
    if data is None:
        if not return_findings:
            return None, [str(f) for f in load_findings if f.severity == SEVERITY_FATAL_ERROR]
        return None, load_findings

    all_findings = list(load_findings)
    semantic_findings = validate_dataset_data(data, validator, filename=str(file_path), return_findings=True)
    all_findings.extend(semantic_findings)

    if not return_findings:
        fatal_errors = [str(f) for f in all_findings if f.severity == SEVERITY_FATAL_ERROR]
        return data, fatal_errors
    return data, all_findings


def normalize_dataset_name(name: str) -> str:
    """Normalize a dataset name for uniqueness check (lowercased, stripped of punctuation and whitespace)."""
    if not name or not isinstance(name, str):
        return ""
    return re.sub(r"[^\w]", "", name.lower())


def check_duplicate_findings(
    datasets: list[tuple[Path, dict[str, Any]]]
) -> list[ValidationFinding]:
    """Ensure dataset records are unique across the repository."""
    findings: list[ValidationFinding] = []
    id_map: dict[str, list[str]] = defaultdict(list)
    slug_map: dict[str, list[str]] = defaultdict(list)
    name_map: dict[str, list[tuple[str, str]]] = defaultdict(list)
    doi_map: dict[str, list[tuple[Path, dict[str, Any]]]] = defaultdict(list)
    url_map: dict[str, list[tuple[Path, dict[str, Any]]]] = defaultdict(list)

    for path, data in datasets:
        ds_id = data.get("id")
        ds_slug = data.get("slug")
        ds_name = data.get("name")
        path_str = str(path)

        if ds_id and isinstance(ds_id, str):
            id_map[ds_id].append(path_str)
        if ds_slug and isinstance(ds_slug, str):
            slug_map[ds_slug].append(path_str)
        if ds_name and isinstance(ds_name, str):
            norm_name = normalize_dataset_name(ds_name)
            if norm_name:
                name_map[norm_name].append((path_str, ds_name))

        cit = data.get("citation") or {}
        doi = normalize_doi(cit.get("doi", ""))
        if doi:
            doi_map[doi].append((path, data))

        hp = data.get("homepage_url", "")
        if hp and not is_generic_hosting_url(hp):
            norm_hp = normalize_url(hp)
            if norm_hp:
                url_map[norm_hp].append((path, data))

    # 1. Duplicate ID check (Fatal error)
    for ds_id, paths in sorted(id_map.items()):
        if len(paths) > 1:
            fp = make_fingerprint("DUP-001", ds_id, "id")
            findings.append(
                ValidationFinding(
                    rule_id="DUP-001",
                    dataset_id=ds_id,
                    file_path=paths[0],
                    field_path="id",
                    severity=SEVERITY_FATAL_ERROR,
                    message=f"Duplicate dataset ID '{ds_id}' found across files: {', '.join(paths)}",
                    fingerprint=fp,
                    blocks_validation=True,
                )
            )

    # 2. Duplicate slug check (Fatal error)
    for ds_slug, paths in sorted(slug_map.items()):
        if len(paths) > 1:
            fp = make_fingerprint("DUP-002", ds_slug, "slug")
            findings.append(
                ValidationFinding(
                    rule_id="DUP-002",
                    dataset_id=ds_slug,
                    file_path=paths[0],
                    field_path="slug",
                    severity=SEVERITY_FATAL_ERROR,
                    message=f"Duplicate dataset slug '{ds_slug}' found across files: {', '.join(paths)}",
                    fingerprint=fp,
                    blocks_validation=True,
                )
            )

    # 3. Duplicate normalized name check (Fatal error)
    for norm_name, items in sorted(name_map.items()):
        if len(items) > 1:
            paths = [it[0] for it in items]
            names = [f"'{it[1]}'" for it in items]
            first_did = Path(paths[0]).stem
            fp = make_fingerprint("DUP-003", first_did, "name")
            findings.append(
                ValidationFinding(
                    rule_id="DUP-003",
                    dataset_id=first_did,
                    file_path=paths[0],
                    field_path="name",
                    severity=SEVERITY_FATAL_ERROR,
                    message=f"Duplicate normalized dataset name '{norm_name}' ({', '.join(names)}) across files: {', '.join(paths)}",
                    fingerprint=fp,
                    blocks_validation=True,
                )
            )

    # 4. Shared DOI check
    for doi, entries in sorted(doi_map.items()):
        if len(entries) > 1:
            for i in range(len(entries)):
                for j in range(i + 1, len(entries)):
                    p1, d1 = entries[i]
                    p2, d2 = entries[j]
                    id1 = d1.get("id", "")
                    id2 = d2.get("id", "")
                    name1 = d1.get("name", "")
                    name2 = d2.get("name", "")
                    same_name = normalize_dataset_name(name1) == normalize_dataset_name(name2)
                    disc = extract_discriminating_features(d1, d2)
                    if same_name:
                        fp = make_fingerprint("DUP-004", id1, "citation.doi")
                        findings.append(
                            ValidationFinding(
                                rule_id="DUP-004",
                                dataset_id=id1,
                                file_path=str(p1),
                                field_path="citation.doi",
                                severity=SEVERITY_FATAL_ERROR,
                                message=f"Identical duplicate dataset sharing citation DOI '{doi}': '{id1}' ({p1}) and '{id2}' ({p2})",
                                fingerprint=fp,
                                blocks_validation=True,
                            )
                        )
                    elif not disc:
                        fp = make_fingerprint("DUP-REV-001", id1, "citation.doi")
                        findings.append(
                            ValidationFinding(
                                rule_id="DUP-REV-001",
                                dataset_id=id1,
                                file_path=str(p1),
                                field_path="citation.doi",
                                severity=SEVERITY_MANUAL_REVIEW,
                                message=f"Ambiguous collision / possible duplicate (alternative title candidate) sharing citation DOI '{doi}': '{id1}' ('{name1}') and '{id2}' ('{name2}') lack discriminating features — unresolved human review required",
                                fingerprint=fp,
                            )
                        )
                    else:
                        mods1 = set(d1.get("modalities", []))
                        mods2 = set(d2.get("modalities", []))
                        pub1 = d1.get("publisher", {}).get("name", "")
                        pub2 = d2.get("publisher", {}).get("name", "")
                        is_same_pub = bool(pub1 and pub2 and pub1.strip().lower() == pub2.strip().lower())
                        shares_domain = bool(mods1 & mods2)
                        fp = make_fingerprint("DUP-REV-001", id1, "citation.doi")
                        if is_same_pub or shares_domain:
                            findings.append(
                                ValidationFinding(
                                    rule_id="DUP-REV-001",
                                    dataset_id=id1,
                                    file_path=str(p1),
                                    field_path="citation.doi",
                                    severity=SEVERITY_INFORMATIONAL,
                                    message=f"Legitimate benchmark family sharing DOI '{doi}': '{id1}' and '{id2}' (differentiating features: {', '.join(disc)})",
                                    fingerprint=fp,
                                )
                            )
                        else:
                            findings.append(
                                ValidationFinding(
                                    rule_id="DUP-REV-001",
                                    dataset_id=id1,
                                    file_path=str(p1),
                                    field_path="citation.doi",
                                    severity=SEVERITY_INFORMATIONAL,
                                    message=f"Shared publication / paper reference for distinct datasets sharing DOI '{doi}': '{id1}' and '{id2}' (differentiating features: {', '.join(disc)})",
                                    fingerprint=fp,
                                )
                            )

    # 5. Shared Homepage check
    for url, entries in sorted(url_map.items()):
        if len(entries) > 1:
            for i in range(len(entries)):
                for j in range(i + 1, len(entries)):
                    p1, d1 = entries[i]
                    p2, d2 = entries[j]
                    id1 = d1.get("id", "")
                    id2 = d2.get("id", "")
                    name1 = d1.get("name", "")
                    name2 = d2.get("name", "")
                    same_name = normalize_dataset_name(name1) == normalize_dataset_name(name2)
                    disc = extract_discriminating_features(d1, d2)
                    if same_name:
                        fp = make_fingerprint("DUP-005", id1, "homepage_url")
                        findings.append(
                            ValidationFinding(
                                rule_id="DUP-005",
                                dataset_id=id1,
                                file_path=str(p1),
                                field_path="homepage_url",
                                severity=SEVERITY_FATAL_ERROR,
                                message=f"Identical duplicate dataset sharing homepage URL '{url}': '{id1}' ({p1}) and '{id2}' ({p2})",
                                fingerprint=fp,
                                blocks_validation=True,
                            )
                        )
                    elif not disc:
                        fp = make_fingerprint("DUP-REV-002", id1, "homepage_url")
                        findings.append(
                            ValidationFinding(
                                rule_id="DUP-REV-002",
                                dataset_id=id1,
                                file_path=str(p1),
                                field_path="homepage_url",
                                severity=SEVERITY_MANUAL_REVIEW,
                                message=f"Ambiguous collision / possible duplicate (alternative title candidate) sharing homepage URL '{url}': '{id1}' ('{name1}') and '{id2}' ('{name2}') lack discriminating features — unresolved human review required",
                                fingerprint=fp,
                            )
                        )
                    else:
                        mods1 = set(d1.get("modalities", []))
                        mods2 = set(d2.get("modalities", []))
                        pub1 = d1.get("publisher", {}).get("name", "")
                        pub2 = d2.get("publisher", {}).get("name", "")
                        is_same_pub = bool(pub1 and pub2 and pub1.strip().lower() == pub2.strip().lower())
                        shares_domain = bool(mods1 & mods2)
                        fp = make_fingerprint("DUP-REV-002", id1, "homepage_url")
                        if is_same_pub or shares_domain:
                            findings.append(
                                ValidationFinding(
                                    rule_id="DUP-REV-002",
                                    dataset_id=id1,
                                    file_path=str(p1),
                                    field_path="homepage_url",
                                    severity=SEVERITY_INFORMATIONAL,
                                    message=f"Legitimate benchmark family sharing homepage '{url}': '{id1}' and '{id2}' (differentiating features: {', '.join(disc)})",
                                    fingerprint=fp,
                                )
                            )
                        else:
                            findings.append(
                                ValidationFinding(
                                    rule_id="DUP-REV-002",
                                    dataset_id=id1,
                                    file_path=str(p1),
                                    field_path="homepage_url",
                                    severity=SEVERITY_INFORMATIONAL,
                                    message=f"Shared homepage reference for distinct datasets sharing '{url}': '{id1}' and '{id2}' (differentiating features: {', '.join(disc)})",
                                    fingerprint=fp,
                                )
                            )

    return findings


def check_duplicate_records(
    datasets: list[tuple[Path, dict[str, Any]]]
) -> tuple[list[str], list[str]]:
    """Ensure dataset records are unique across the repository.

    Returns:
        (errors, warnings) as list of strings for backwards compatibility.
    """
    findings = check_duplicate_findings(datasets)
    errors = [f.message for f in findings if f.severity == SEVERITY_FATAL_ERROR]
    warnings = [f.message for f in findings if f.severity != SEVERITY_FATAL_ERROR]
    return errors, warnings


def check_duplicate_ids_and_slugs(
    datasets: list[tuple[Path, dict[str, Any]]]
) -> list[str]:
    """Ensure dataset IDs and slugs are unique across the repository (backwards compatibility)."""
    errors, _ = check_duplicate_records(datasets)
    return errors


# ==============================================================================
# Legacy Baseline & Quality Ratchet Engine
# ==============================================================================


def get_current_git_commit(repo_root: Path) -> str:
    """Retrieve current authoritative git commit SHA."""
    try:
        res = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=True,
        )
        return res.stdout.strip()
    except Exception:
        return "unknown"


def get_changed_dataset_files(
    repo_root: Path,
    trusted_base: str | None = None,
) -> set[str] | None:
    """Detect added or modified dataset files relative to trusted base commit.

    Returns:
        Set of relative file paths (e.g. {'data/datasets/mnist.json'}), or None if
        git comparison is not available / applicable.
    """
    if not trusted_base:
        return None

    # Check if trusted_base is a git commit / ref
    try:
        base_ref = trusted_base.split(":")[0] if ":" in trusted_base else trusted_base
        res = subprocess.run(
            ["git", "diff", "--name-only", base_ref, "--", "data/datasets/"],
            cwd=repo_root,
            capture_output=True,
            text=True,
        )
        if res.returncode == 0:
            changed = {line.strip() for line in res.stdout.splitlines() if line.strip()}
            return changed
    except Exception:
        pass

    return None


def load_baseline_file(baseline_path: Path) -> dict[str, Any] | None:
    """Load and parse the legacy baseline JSON file."""
    if not baseline_path.exists():
        return None
    try:
        content = baseline_path.read_text(encoding="utf-8")
        return json.loads(content)
    except Exception as exc:
        print(f"Warning: Failed to load baseline from '{baseline_path}': {exc}", file=sys.stderr)
        return None


def generate_baseline_data(
    ratchetable_findings: list[ValidationFinding],
    commit_sha: str,
) -> dict[str, Any]:
    """Serialize ratchetable findings into deterministic baseline data structure."""
    counts_by_rule: dict[str, int] = defaultdict(int)
    violations_list: list[dict[str, Any]] = []
    seen_fps: set[str] = set()

    for f in sorted(ratchetable_findings, key=lambda x: x.fingerprint):
        if f.fingerprint in seen_fps:
            continue
        seen_fps.add(f.fingerprint)
        counts_by_rule[f.rule_id] += 1
        violations_list.append({
            "dataset_id": f.dataset_id,
            "field_path": f.field_path,
            "file_path": f.file_path,
            "fingerprint": f.fingerprint,
            "message": f.message,
            "rule_id": f.rule_id,
        })

    return {
        "generated_at_commit": commit_sha,
        "schema_version": "1.0",
        "total_violations": len(violations_list),
        "violation_counts_by_rule": dict(sorted(counts_by_rule.items())),
        "violations": violations_list,
    }


def write_baseline_file(baseline_path: Path, data: dict[str, Any]) -> None:
    """Write baseline file with deterministic JSON formatting."""
    content = json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    baseline_path.parent.mkdir(parents=True, exist_ok=True)
    baseline_path.write_text(content, encoding="utf-8")


def evaluate_ratchet(
    findings: list[ValidationFinding],
    baseline_data: dict[str, Any] | None,
    changed_files: set[str] | None = None,
    ratchet: bool = False,
    strict: bool = False,
) -> tuple[list[ValidationFinding], dict[str, int]]:
    """Apply ratchet rules to findings against the baseline.

    Rules:
    - Fatal errors always block validation (cannot be grandfathered).
    - Manual review and informational findings never block validation.
    - If strict=True, all ratchetable warnings block validation.
    - If ratchet=True and baseline_data is provided:
      - Changed/added files cannot use grandfathering: ratchetable warnings on changed files block validation.
      - For unchanged files, findings whose fingerprints exist in baseline are grandfathered.
      - New findings not in baseline block validation.
    - If ratchet=False and strict=False:
      - Ratchetable warnings are reported and visible, but do not block validation.
    """
    baseline_fps: set[str] = set()
    if baseline_data and "violations" in baseline_data:
        baseline_fps = {v["fingerprint"] for v in baseline_data["violations"] if "fingerprint" in v}

    active_fps: set[str] = set()
    evaluated: list[ValidationFinding] = []

    metrics = {
        "fatal_errors": 0,
        "ratchetable_warnings": 0,
        "grandfathered_violations": 0,
        "new_violations": 0,
        "resolved_violations": 0,
        "manual_reviews": 0,
        "informational": 0,
        "blocking_findings": 0,
    }

    for f in findings:
        if f.severity == SEVERITY_FATAL_ERROR:
            f.blocks_validation = True
            metrics["fatal_errors"] += 1
            metrics["blocking_findings"] += 1
        elif f.severity == SEVERITY_RATCHETABLE_WARNING:
            metrics["ratchetable_warnings"] += 1
            active_fps.add(f.fingerprint)

            if strict:
                f.blocks_validation = True
                f.is_grandfathered = False
                metrics["new_violations"] += 1
                metrics["blocking_findings"] += 1
            elif ratchet:
                if changed_files is not None and any(f.file_path.endswith(cf) or cf.endswith(f.file_path) for cf in changed_files):
                    # Changed files cannot claim grandfathering!
                    f.blocks_validation = True
                    f.is_grandfathered = False
                    metrics["new_violations"] += 1
                    metrics["blocking_findings"] += 1
                elif f.fingerprint in baseline_fps:
                    f.is_grandfathered = True
                    f.blocks_validation = False
                    metrics["grandfathered_violations"] += 1
                else:
                    f.blocks_validation = True
                    f.is_grandfathered = False
                    metrics["new_violations"] += 1
                    metrics["blocking_findings"] += 1
            else:
                f.blocks_validation = False
                if f.fingerprint in baseline_fps:
                    f.is_grandfathered = True
                    metrics["grandfathered_violations"] += 1
                else:
                    metrics["new_violations"] += 1
        elif f.severity == SEVERITY_MANUAL_REVIEW:
            f.blocks_validation = False
            metrics["manual_reviews"] += 1
        elif f.severity == SEVERITY_INFORMATIONAL:
            f.blocks_validation = False
            metrics["informational"] += 1

        evaluated.append(f)

    if baseline_fps:
        resolved_count = len(baseline_fps - active_fps)
        metrics["resolved_violations"] = max(0, resolved_count)

    return evaluated, metrics


def format_github_annotations(findings: list[ValidationFinding]) -> list[str]:
    """Emit GitHub Actions workflow command strings for PR annotations."""
    annotations: list[str] = []
    for f in findings:
        rel_path = f.file_path
        if rel_path.startswith(str(REPO_ROOT)):
            rel_path = os.path.relpath(rel_path, str(REPO_ROOT))

        if f.blocks_validation:
            annotations.append(f"::error file={rel_path},title={f.rule_id}::{f.message}")
        elif f.is_grandfathered:
            annotations.append(f"::notice file={rel_path},title={f.rule_id} (Grandfathered)::{f.message}")
        elif f.severity == SEVERITY_MANUAL_REVIEW:
            annotations.append(f"::warning file={rel_path},title={f.rule_id} (Manual Review)::{f.message}")
    return annotations


def format_github_step_summary(
    total_checked: int,
    total_passed: int,
    metrics: dict[str, int],
    is_ratchet_enabled: bool,
    baseline_count: int,
) -> str:
    """Generate Markdown formatted GitHub step summary."""
    status_icon = "✅" if metrics.get("blocking_findings", 0) == 0 else "❌"
    ratchet_status = "Enforced" if is_ratchet_enabled else "Disabled"

    lines = [
        f"## {status_icon} OpenDatasets Quality & Ratchet Summary",
        "",
        "| Metric | Count | Note |",
        "|---|---|---|",
        f"| **Datasets Checked** | {total_checked} | Total metadata files scanned |",
        f"| **Passed Cleanly** | {total_passed} | Files without any violations |",
        f"| **Fatal Errors** | {metrics.get('fatal_errors', 0)} | Must be fixed (blocking) |",
        f"| **Ratchetable Warnings** | {metrics.get('ratchetable_warnings', 0)} | Quality rule violations |",
        f"| **Grandfathered Baseline** | {metrics.get('grandfathered_violations', 0)} | Legacy exceptions (allowed) |",
        f"| **New Violations** | {metrics.get('new_violations', 0)} | Prohibited new violations (blocking) |",
        f"| **Resolved Violations** | {metrics.get('resolved_violations', 0)} | Legacy issues fixed |",
        f"| **Manual Review Candidates** | {metrics.get('manual_reviews', 0)} | Domain review recommended |",
        f"| **Ratchet Mode** | {ratchet_status} | Baseline target: {baseline_count} violations |",
        "",
    ]

    if metrics.get("blocking_findings", 0) > 0:
        lines.append(f"> ❌ **Validation FAILED**: {metrics['blocking_findings']} blocking issue(s) detected.")
    else:
        lines.append("> ✅ **Validation PASSED**: Quality ratchet constraints satisfied.")

    return "\n".join(lines)


# ==============================================================================
# Main Orchestration & CLI
# ==============================================================================


def validate_all_datasets(
    data_dir: Path,
    schema_path: Path,
    target_files: list[Path] | None = None,
    baseline_path: Path | None = None,
    trusted_base: str | None = None,
    ratchet: bool = False,
    strict: bool = False,
    verbose: bool = False,
    return_findings: bool = False,
) -> Any:
    """Validate dataset files, returning (total_checked, total_passed, findings, metrics)."""
    schema_data, schema_errors = load_schema(schema_path)
    if schema_errors or schema_data is None:
        findings = [
            ValidationFinding(
                rule_id="SCHEMA-001",
                dataset_id="schema",
                file_path=str(schema_path),
                field_path="<schema>",
                severity=SEVERITY_FATAL_ERROR,
                message=err,
                fingerprint=make_fingerprint("SCHEMA-001", "schema", "<schema>"),
                blocks_validation=True,
            )
            for err in schema_errors
        ]
        metrics = {"blocking_findings": len(findings), "fatal_errors": len(findings)}
        if not return_findings:
            return 0, 0, [str(f) for f in findings]
        return 0, 0, findings, metrics

    validator = jsonschema.Draft7Validator(schema_data)

    if target_files:
        files = target_files
    else:
        if not data_dir.exists():
            fp = make_fingerprint("DIR-001", "catalog", str(data_dir))
            findings = [
                ValidationFinding(
                    rule_id="DIR-001",
                    dataset_id="catalog",
                    file_path=str(data_dir),
                    field_path="<catalog>",
                    severity=SEVERITY_FATAL_ERROR,
                    message=f"Data directory '{data_dir}' does not exist.",
                    fingerprint=fp,
                    blocks_validation=True,
                )
            ]
            if not return_findings:
                return 0, 0, [str(f) for f in findings]
            return 0, 0, findings, {"blocking_findings": 1, "fatal_errors": 1}
        files = sorted(data_dir.glob("*.json"))

    if not files:
        fp = make_fingerprint("DIR-001", "catalog", str(data_dir))
        findings = [
            ValidationFinding(
                rule_id="DIR-001",
                dataset_id="catalog",
                file_path=str(data_dir),
                field_path="<catalog>",
                severity=SEVERITY_FATAL_ERROR,
                message=f"No dataset JSON files found in '{data_dir}'.",
                fingerprint=fp,
                blocks_validation=True,
            )
        ]
        if not return_findings:
            return 0, 0, [str(f) for f in findings]
        return 0, 0, findings, {"blocking_findings": 1, "fatal_errors": 1}

    raw_findings: list[ValidationFinding] = []
    loaded_datasets: list[tuple[Path, dict[str, Any]]] = []

    for file_path in files:
        data, f_list = validate_dataset_file(file_path, validator, return_findings=True)
        raw_findings.extend(f_list)
        if data is not None:
            loaded_datasets.append((file_path, data))

    # Cross-dataset checks
    dup_findings = check_duplicate_findings(loaded_datasets)
    raw_findings.extend(dup_findings)

    # Determine changed files if ratchet enabled
    changed_files = None
    if ratchet and trusted_base:
        changed_files = get_changed_dataset_files(REPO_ROOT, trusted_base)

    # Baseline evaluation
    baseline_data = None
    effective_baseline = baseline_path or DEFAULT_BASELINE_PATH
    if effective_baseline and effective_baseline.exists():
        baseline_data = load_baseline_file(effective_baseline)

    evaluated_findings, metrics = evaluate_ratchet(
        findings=raw_findings,
        baseline_data=baseline_data,
        changed_files=changed_files,
        ratchet=ratchet,
        strict=strict,
    )

    # Count passed files (files without blocking findings)
    files_with_blocking = {f.file_path for f in evaluated_findings if f.blocks_validation}
    total_passed = len(files) - len(files_with_blocking)

    if not return_findings:
        blocking_errors = [str(f) for f in evaluated_findings if f.blocks_validation]
        return len(files), total_passed, blocking_errors

    return len(files), total_passed, evaluated_findings, metrics


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for validate_datasets.py."""
    parser = argparse.ArgumentParser(
        description="Validate OpenDatasets JSON metadata against schema and quality ratchet."
    )
    parser.add_argument(
        "--schema",
        type=Path,
        default=DEFAULT_SCHEMA_PATH,
        help=f"Path to JSON schema file (default: {DEFAULT_SCHEMA_PATH})",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=DEFAULT_DATA_DIR,
        help=f"Directory containing dataset JSON files (default: {DEFAULT_DATA_DIR})",
    )
    parser.add_argument(
        "--baseline",
        type=Path,
        default=DEFAULT_BASELINE_PATH,
        help=f"Path to legacy baseline file (default: {DEFAULT_BASELINE_PATH})",
    )
    parser.add_argument(
        "--trusted-base",
        type=str,
        default=None,
        help="Git ref or commit SHA for trusted base to detect changed files",
    )
    parser.add_argument(
        "--ratchet",
        action="store_true",
        help="Enforce quality ratchet: new violations or modified records fail validation",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat all warnings (even grandfathered) as fatal errors",
    )
    parser.add_argument(
        "--init-baseline",
        action="store_true",
        help="Scan catalog, generate data/legacy-baseline.json, and exit 0",
    )
    parser.add_argument(
        "--update-baseline",
        action="store_true",
        help="Update legacy baseline by pruning resolved violations (expansion prohibited)",
    )
    parser.add_argument(
        "--annotations",
        action="store_true",
        help="Emit GitHub Actions workflow commands for pull request annotations",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Output GitHub Actions Markdown step summary to $GITHUB_STEP_SUMMARY or stdout",
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        default=None,
        help="Write structured validation findings to JSON output file",
    )
    parser.add_argument(
        "files",
        nargs="*",
        type=Path,
        help="Optional specific dataset JSON files to validate.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Only display errors and final status summary.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Display detailed diagnostic output.",
    )

    args = parser.parse_args(argv)

    target_files = [Path(f) for f in args.files] if args.files else None

    # Handle --init-baseline
    if args.init_baseline:
        commit_sha = get_current_git_commit(REPO_ROOT)
        total, passed, findings, _ = validate_all_datasets(
            data_dir=args.data_dir,
            schema_path=args.schema,
            target_files=target_files,
            ratchet=False,
            strict=False,
            verbose=args.verbose,
            return_findings=True,
        )
        ratchetable = [f for f in findings if f.severity == SEVERITY_RATCHETABLE_WARNING]
        base_data = generate_baseline_data(ratchetable, commit_sha=commit_sha)
        write_baseline_file(args.baseline, base_data)
        print(f"Initialized legacy baseline at '{args.baseline}':")
        print(f"  Total violations: {base_data['total_violations']}")
        print(f"  Violation counts by rule: {base_data['violation_counts_by_rule']}")
        print(f"  Authoritative commit: {commit_sha}")
        return 0

    # Handle standard validation
    total, passed, findings, metrics = validate_all_datasets(
        data_dir=args.data_dir,
        schema_path=args.schema,
        target_files=target_files,
        baseline_path=args.baseline,
        trusted_base=args.trusted_base,
        ratchet=args.ratchet,
        strict=args.strict,
        verbose=args.verbose,
        return_findings=True,
    )

    # Handle --update-baseline
    if args.update_baseline:
        trusted_data = load_baseline_file(args.baseline)
        if not trusted_data:
            print(f"Error: Cannot update baseline: existing baseline '{args.baseline}' not found.", file=sys.stderr)
            return 1

        trusted_fps = {v["fingerprint"] for v in trusted_data.get("violations", [])}
        current_ratchetable = [f for f in findings if f.severity == SEVERITY_RATCHETABLE_WARNING]
        current_fps = {f.fingerprint for f in current_ratchetable}

        # Check subset rule: new violations cannot be added to baseline!
        added_fps = current_fps - trusted_fps
        if added_fps:
            print("Error: Baseline update failed! Baseline expansion / exception substitution is strictly prohibited.", file=sys.stderr)
            print(f"Attempted to add {len(added_fps)} new violation(s) to baseline:", file=sys.stderr)
            for afp in sorted(added_fps):
                print(f"  ✗ {afp}", file=sys.stderr)
            return 1

        commit_sha = get_current_git_commit(REPO_ROOT)
        updated_data = generate_baseline_data(current_ratchetable, commit_sha=commit_sha)
        write_baseline_file(args.baseline, updated_data)
        print(f"Updated legacy baseline at '{args.baseline}':")
        print(f"  Previous violations: {len(trusted_fps)}")
        print(f"  New violations total: {updated_data['total_violations']}")
        print(f"  Pruned/resolved: {len(trusted_fps) - len(current_fps)}")
        return 0

    # JSON output if requested
    if args.json_output:
        out_payload = {
            "summary": {
                "total_checked": total,
                "total_passed": passed,
                "metrics": metrics,
            },
            "findings": [f.to_dict() for f in findings],
        }
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(json.dumps(out_payload, indent=2) + "\n", encoding="utf-8")

    # GitHub annotations if requested
    if args.annotations:
        for ann in format_github_annotations(findings):
            print(ann)

    # Step summary if requested
    baseline_count = 0
    if args.baseline.exists():
        b_data = load_baseline_file(args.baseline)
        if b_data:
            baseline_count = b_data.get("total_violations", 0)

    summary_md = format_github_step_summary(
        total_checked=total,
        total_passed=passed,
        metrics=metrics,
        is_ratchet_enabled=args.ratchet,
        baseline_count=baseline_count,
    )

    if args.summary:
        summary_env_path = os.environ.get("GITHUB_STEP_SUMMARY")
        if summary_env_path:
            with open(summary_env_path, "a", encoding="utf-8") as sf:
                sf.write(summary_md + "\n")
        else:
            print("\n" + summary_md)

    # Console output
    blocking_findings = [f for f in findings if f.blocks_validation]
    manual_reviews = [f for f in findings if f.severity == SEVERITY_MANUAL_REVIEW]

    if blocking_findings:
        print("\n=======================================================", file=sys.stderr)
        print(" [FAIL] OpenDatasets Validation & Quality Ratchet Failed", file=sys.stderr)
        print("=======================================================", file=sys.stderr)
        for f in blocking_findings:
            print(f"  ✗ [{f.rule_id}] {f.file_path} [{f.field_path}]: {f.message}", file=sys.stderr)
            if f.remediation:
                print(f"    ↳ Remediation: {f.remediation}", file=sys.stderr)
        print(f"\nResult: FAILED ({len(blocking_findings)} blocking issue(s) detected across {total} checked file(s))", file=sys.stderr)
        return 1

    if not args.quiet:
        print("=======================================================")
        print(" [PASS] OpenDatasets Metadata Validation & Quality Ratchet")
        print("=======================================================")
        print(f"  ✓ Schema: {args.schema}")
        print(f"  ✓ Validated {total} dataset file(s)")
        print(f"  ✓ Fatal errors: {metrics.get('fatal_errors', 0)}")
        print(f"  ✓ Active ratchetable warnings: {metrics.get('ratchetable_warnings', 0)}")
        if args.ratchet:
            print(f"  ✓ Grandfathered baseline violations: {metrics.get('grandfathered_violations', 0)}")
            print(f"  ✓ New violations: {metrics.get('new_violations', 0)}")
            print(f"  ✓ Resolved violations: {metrics.get('resolved_violations', 0)}")
        print(f"  ✓ Manual review candidates: {metrics.get('manual_reviews', 0)}")
        print("=======================================================")
        print("Result: ALL DATASETS SATISFY QUALITY AND RATCHET CONSTRAINTS")

    if args.verbose and manual_reviews:
        print("\nManual Review Candidates:")
        for mr in manual_reviews:
            print(f"  [REVIEW] [{mr.rule_id}] {mr.file_path} [{mr.field_path}]: {mr.message}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
