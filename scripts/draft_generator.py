#!/usr/bin/env python3
"""OpenDatasets Community Suggestion Draft Generator.

Converts a parsed community dataset suggestion into a schema-compliant
OpenDatasets v1 metadata draft (schemas/dataset.v1.schema.json).

DRAFTS MUST NEVER BE WRITTEN DIRECTLY TO data/datasets/ OR THE PUBLISHED CATALOG.
Drafts are strictly provisional until verified and approved by maintainers.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import jsonschema

from scripts.duplicate_detector import DuplicateCheckResult
from scripts.suggestion_parser import ParsedSuggestion

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
DEFAULT_SCHEMA_PATH = REPO_ROOT / "schemas" / "dataset.v1.schema.json"


KNOWN_PUBLISHER_DOMAINS: dict[str, dict[str, str]] = {
    "archive.ics.uci.edu": {
        "name": "UCI Machine Learning Repository",
        "type": "academic",
        "url": "https://archive.ics.uci.edu",
    },
    "physionet.org": {
        "name": "PhysioNet",
        "type": "academic",
        "url": "https://physionet.org",
    },
    "huggingface.co": {
        "name": "Hugging Face",
        "type": "community",
        "url": "https://huggingface.co",
    },
    "kaggle.com": {
        "name": "Kaggle",
        "type": "community",
        "url": "https://www.kaggle.com",
    },
    "github.com": {
        "name": "GitHub",
        "type": "community",
        "url": "https://github.com",
    },
    "stanford.edu": {
        "name": "Stanford University",
        "type": "academic",
        "url": "https://stanford.edu",
    },
    "mit.edu": {
        "name": "Massachusetts Institute of Technology (MIT)",
        "type": "academic",
        "url": "https://mit.edu",
    },
    "nih.gov": {
        "name": "National Institutes of Health (NIH)",
        "type": "government",
        "url": "https://www.nih.gov",
    },
}

MODALITY_MAPPING: list[tuple[list[str], str]] = [
    (["vision", "cv", "image", "video", "photo", "chest x-ray", "mri", "ct"], "vision"),
    (["nlp", "text", "language", "speech to text", "sentiment"], "nlp"),
    (["audio", "speech", "acoustic", "sound"], "audio"),
    (["tabular", "table", "csv", "features", "classification"], "tabular"),
    (["multimodal", "multi-modal", "vision-language"], "multimodal"),
    (["reinforcement", "rl", "gym"], "reinforcement-learning"),
    (["graph", "network", "node"], "graph"),
    (["time-series", "timeseries", "sensor", "signal"], "time-series"),
    (["3d", "point cloud", "mesh"], "3d"),
]


def generate_slug(
    name: str,
    fallback_prefix: str = "dataset",
    existing_slugs: set[str] | list[str] | None = None,
) -> str:
    """Generate a clean, kebab-case URL slug and schema-compliant ID.

    Handles Unicode, Bangla, and non-ASCII names safely via fallback hashing.
    Avoids collisions with existing catalog slugs if provided.
    Schema pattern: ^[a-z0-9]+(-[a-z0-9]+)*$
    ID pattern: ^[a-z0-9][a-z0-9_-]{1,62}[a-z0-9]$
    """
    if not name:
        return f"{fallback_prefix}-draft"

    # Normalize unicode to ASCII where possible
    ascii_norm = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    lowered = ascii_norm.lower()

    # Convert non-alphanumeric chars to hyphens
    clean = re.sub(r"[^a-z0-9]+", "-", lowered).strip("-")

    # If non-ASCII stripped everything (e.g. Bangla or CJK characters)
    if not clean or len(clean) < 2:
        name_hash = hashlib.sha256(name.encode("utf-8")).hexdigest()[:8]
        clean = f"{fallback_prefix}-{name_hash}"

    # Ensure length <= 60 characters and ends with alphanumeric
    clean = clean[:60].rstrip("-")
    if len(clean) < 2:
        clean = f"{fallback_prefix}-draft"

    # Collision avoidance with existing catalog entries
    if existing_slugs:
        slug_set = set(existing_slugs)
        if clean in slug_set:
            candidate = f"{clean}-draft"
            counter = 2
            while candidate in slug_set:
                candidate = f"{clean}-draft-{counter}"
                counter += 1
            clean = candidate[:60].rstrip("-")

    return clean


def infer_modalities(category: str, task: str, description: str) -> list[str]:
    """Map freeform category and description to standard schema modality enums."""
    combined = f"{category} {task} {description}".lower()
    modalities: list[str] = []

    for keywords, mod_enum in MODALITY_MAPPING:
        if any(kw in combined for kw in keywords):
            modalities.append(mod_enum)

    if not modalities:
        modalities = ["other"]

    # Return unique modalities
    return list(dict.fromkeys(modalities))


def infer_task_slug(task: str) -> str:
    """Format task into a valid kebab-case schema task token."""
    if not task:
        return "general-benchmark"
    clean = re.sub(r"[^a-z0-9]+", "-", task.lower()).strip("-")
    if not clean or len(clean) < 2:
        return "general-benchmark"
    return clean[:60].rstrip("-")


def infer_publisher(source_url: str) -> dict[str, str]:
    """Infer publisher metadata from source domain without fabricating unverified identities."""
    if not source_url:
        return {"name": "Unknown Publisher", "type": "unknown"}

    try:
        parsed = urlparse(source_url)
        netloc = parsed.netloc.lower()
        if netloc.startswith("www."):
            netloc = netloc[4:]

        # Direct domain match
        for domain, info in KNOWN_PUBLISHER_DOMAINS.items():
            if netloc == domain or netloc.endswith(f".{domain}"):
                return dict(info)

        # Domain type heuristic
        if netloc.endswith(".edu") or ".ac." in netloc:
            parts = netloc.split(".")
            inst = parts[-2].upper() if len(parts) >= 2 else "Academic Institution"
            return {
                "name": f"{inst} Research Lab",
                "type": "academic",
                "url": f"https://{netloc}",
            }
        elif netloc.endswith(".gov"):
            return {
                "name": f"{netloc} (Government Agency)",
                "type": "government",
                "url": f"https://{netloc}",
            }

        # Fallback without fabricating publisher
        domain_name = netloc.split(".")[0].capitalize()
        return {
            "name": f"{domain_name} Source",
            "type": "unknown",
            "url": f"https://{netloc}",
        }
    except Exception:
        return {"name": "Unknown Publisher", "type": "unknown"}


def infer_license(license_text: str) -> dict[str, Any]:
    """Infer license structure adhering strictly to schema rules.

    All contributor-claimed licenses are strictly assigned status 'unknown'
    to prevent unverified community claims from being automatically marked as
    verified ('verified_open', 'verified_non_commercial', etc.).
    Human maintainers must independently audit and verify licensing terms.
    """
    norm = license_text.lower().strip()

    if not norm or "unknown" in norm or "unspecified" in norm:
        return {
            "status": "unknown",
            "name": license_text if (license_text and len(license_text) >= 2) else "Unspecified / Pending Verification",
            "commercial_use": "unknown",
            "notes": "License terms require human maintainer verification before publishing.",
        }

    spdx_id = None
    canonical_name = license_text[:100]
    license_url = None

    if "cc-by-4.0" in norm or "cc by 4.0" in norm or "creative commons attribution 4.0" in norm:
        canonical_name = "Creative Commons Attribution 4.0 International"
        spdx_id = "CC-BY-4.0"
        license_url = "https://creativecommons.org/licenses/by/4.0/legalcode"
    elif "mit" in norm:
        canonical_name = "MIT License"
        spdx_id = "MIT"
        license_url = "https://opensource.org/licenses/MIT"
    elif "apache" in norm:
        canonical_name = "Apache License 2.0"
        spdx_id = "Apache-2.0"
        license_url = "https://www.apache.org/licenses/LICENSE-2.0"
    elif "public domain" in norm or "cc0" in norm:
        canonical_name = "Public Domain (CC0)"
        spdx_id = "CC0-1.0"

    lic_dict: dict[str, Any] = {
        "status": "unknown",  # Contributor claims are NEVER automatically verified
        "name": canonical_name,
        "commercial_use": "unknown",
        "notes": f"Contributor claimed: '{license_text}'. Terms must be independently verified by maintainers.",
    }
    if spdx_id:
        lic_dict["spdx_id"] = spdx_id
    if license_url:
        lic_dict["url"] = license_url

    return lic_dict


def generate_draft_metadata(
    suggestion: ParsedSuggestion,
    issue_number: int | None = None,
    existing_slugs: set[str] | list[str] | None = None,
) -> dict[str, Any]:
    """Build a complete, schema-compliant draft metadata dictionary.

    Enforces:
    - verification.status = 'provisional'
    - Publisher, license, and size fields are never fabricated
    - Provenance notes track community contribution origin
    - Avoids slug collisions with existing catalog datasets
    """
    slug = generate_slug(suggestion.name, existing_slugs=existing_slugs)
    modalities = infer_modalities(suggestion.category, suggestion.task, suggestion.description)
    task_slug = infer_task_slug(suggestion.task)

    # Base tags
    tags = [mod for mod in modalities if mod != "other"]
    if task_slug:
        tags.append(task_slug)
    # Add keywords from slug
    for token in slug.split("-"):
        if len(token) > 2 and token not in tags:
            tags.append(token)
    if not tags:
        tags = ["benchmark", "machine-learning"]

    publisher = infer_publisher(suggestion.source_url)
    license_obj = infer_license(suggestion.license_text)

    # Primary source reference
    source_references: list[dict[str, Any]] = [
        {
            "title": f"{suggestion.name} — Official Source Landing Page",
            "url": suggestion.source_url,
            "type": "official_website",
            "notes": "Provided in community suggestion issue.",
        }
    ]

    # Additional references from DOI or paper URL
    if suggestion.doi:
        doi_url = f"https://doi.org/{suggestion.doi}"
        source_references.append(
            {
                "title": f"Scientific Publication DOI: {suggestion.doi}",
                "url": doi_url,
                "type": "original_paper",
                "notes": "Permanent DOI reference extracted from community submission.",
            }
        )

    if suggestion.paper_url and suggestion.paper_url != suggestion.source_url:
        source_references.append(
            {
                "title": f"{suggestion.name} Research Paper",
                "url": suggestion.paper_url,
                "type": "original_paper",
                "notes": "Supporting paper URL provided by contributor.",
            }
        )

    # Provenance curation notes
    provenance_notes = [
        "Automated provisional draft generated from community suggestion.",
    ]
    if issue_number:
        provenance_notes.append(f"Origin: GitHub Issue #{issue_number}.")
    if suggestion.notes:
        provenance_notes.append(f"Contributor notes/evidence: {suggestion.notes}")
    provenance_notes.append(
        "Notice: Sample counts, disk size, and licensing terms have not been independently verified."
    )

    draft: dict[str, Any] = {
        "schema_version": "1.0.0",
        "id": slug,
        "slug": slug,
        "name": suggestion.name,
        "description": suggestion.description,
        "homepage_url": suggestion.source_url,
        "publisher": publisher,
        "modalities": modalities,
        "tasks": [task_slug],
        "tags": tags[:15],
        "license": license_obj,
        "source_references": source_references,
        "verification": {
            "status": "provisional",
            "verified_by": None,
            "verified_date": None,
            "notes": "Automated draft pending independent maintainer verification and catalog acceptance.",
        },
        "provenance": {
            "curation_notes": " ".join(provenance_notes),
        },
    }

    # Optional citation block if DOI or paper is known
    if suggestion.doi or suggestion.paper_url:
        citation: dict[str, Any] = {
            "paper_title": suggestion.name,
        }
        if suggestion.doi:
            citation["doi"] = suggestion.doi
            citation["paper_url"] = f"https://doi.org/{suggestion.doi}"
        elif suggestion.paper_url:
            citation["paper_url"] = suggestion.paper_url

        draft["citation"] = citation

    return draft


def validate_draft_dict(
    draft_data: dict[str, Any],
    schema_path: Path = DEFAULT_SCHEMA_PATH,
) -> list[str]:
    """Validate generated draft dictionary against schemas/dataset.v1.schema.json."""
    if not schema_path.exists():
        return [f"Schema file not found at '{schema_path}'."]

    try:
        with open(schema_path, "r", encoding="utf-8") as f:
            schema_json = json.load(f)
        validator = jsonschema.Draft7Validator(schema_json)
        errors = [f"[{'.'.join(str(p) for p in e.path)}]: {e.message}" for e in validator.iter_errors(draft_data)]
        return errors
    except Exception as exc:
        return [f"Failed to validate draft against schema: {exc}"]


def format_unsupported_issue_report(issue_number: int | None = None) -> str:
    """Format a diagnostic Markdown report for non-dataset suggestion issues."""
    lines: list[str] = []
    lines.append("# Community Dataset Suggestion Triage Report\n")
    lines.append("> [!NOTE]")
    num_str = f"Issue #{issue_number}" if issue_number else "This issue"
    lines.append(f"> **Non-Dataset Suggestion:** {num_str} does not match the dataset suggestion form template structure.\n")
    lines.append("## Triage Outcome\n")
    lines.append("- **Status:** Skipped automated dataset triage.")
    lines.append("- **Reason:** Issue body does not contain required dataset suggestion form headings (`Dataset name`, `Official dataset URL`, `Modality, task, and usefulness`).")
    lines.append("- **Action:** No metadata draft generated. Issue remains available for standard repository discussions or bug triage.\n")
    return "\n".join(lines)


def format_maintainer_report(
    suggestion: ParsedSuggestion,
    duplicate_result: DuplicateCheckResult,
    draft_data: dict[str, Any] | None,
    validation_errors: list[str],
    draft_file_path: Path | None = None,
    issue_number: int | None = None,
) -> str:
    """Format a detailed Markdown triage report for maintainers and issue comments."""
    lines: list[str] = []
    lines.append("# Community Dataset Suggestion Triage Report\n")

    # Overall Status Banner
    if not suggestion.is_valid:
        lines.append("> [!CAUTION]")
        lines.append("> **Invalid Submission:** Missing or malformed required fields.\n")
    elif duplicate_result.is_duplicate:
        lines.append("> [!WARNING]")
        lines.append(f"> **Duplicate Detected:** Highly matches existing catalog entry `{duplicate_result.primary_match.existing_id}`.\n")
    elif duplicate_result.has_potential_matches:
        lines.append("> [!NOTE]")
        lines.append(f"> **Potential Similarities Found:** Requires maintainer review against existing entries.\n")
    else:
        lines.append("> [!TIP]")
        lines.append("> **Valid New Suggestion:** Candidate is eligible for draft generation and maintainer review.\n")

    # Submission Overview Table
    lines.append("## Submission Overview\n")
    if issue_number:
        lines.append(f"- **GitHub Issue:** #{issue_number}")
    lines.append(f"- **Dataset Name:** {suggestion.name or '*(missing)*'}")
    lines.append(f"- **Source URL:** {suggestion.source_url or '*(missing)*'}")
    lines.append(f"- **Category / Modality:** {suggestion.category or '*(unspecified)*'}")
    lines.append(f"- **Primary Task:** {suggestion.task or '*(unspecified)*'}")
    lines.append(f"- **License:** {suggestion.license_text or '*(unspecified)*'}")
    if suggestion.doi:
        lines.append(f"- **DOI:** {suggestion.doi}")
    if suggestion.paper_url:
        lines.append(f"- **Supporting Paper:** {suggestion.paper_url}")
    lines.append("")

    # Validation Results
    lines.append("## Parsing & Validation\n")
    if suggestion.errors:
        lines.append("**Parsing Errors:**")
        for err in suggestion.errors:
            lines.append(f"- :x: {err}")
        lines.append("")
    else:
        lines.append("- :white_check_mark: All required suggestion fields parsed successfully.")

    if suggestion.warnings:
        lines.append("\n**Warnings:**")
        for warn in suggestion.warnings:
            lines.append(f"- :warning: {warn}")
        lines.append("")

    # Duplicate Detection Section
    lines.append("## Duplicate Check\n")
    lines.append(f"- **Status:** {duplicate_result.summary}")
    if duplicate_result.matches:
        lines.append("\n| Existing Dataset | ID | Match Type | Confidence | Details |")
        lines.append("| --- | --- | --- | --- | --- |")
        for m in duplicate_result.matches:
            lines.append(f"| {m.existing_name} | `{m.existing_id}` | {m.match_type} | {m.confidence} | {m.details} |")
        lines.append("")

    # Schema Validation Section
    lines.append("## Schema Compliance (Draft)\n")
    if validation_errors:
        lines.append("**Schema Validation Errors:**")
        for err in validation_errors:
            lines.append(f"- :x: {err}")
        lines.append("")
    elif draft_data:
        lines.append("- :white_check_mark: Draft conforms 100% to OpenDatasets JSON Schema v1.")
        lines.append(f"- **Generated Slug / ID:** `{draft_data.get('id')}`")
        lines.append(f"- **Verification Status:** `{draft_data.get('verification', {}).get('status')}`")
        if draft_file_path:
            lines.append(f"- **Draft File Saved:** `{draft_file_path}`")
        lines.append("")

    # Unknown or Unverified Claims Section
    lines.append("## Unknown or Unverified Claims\n")
    if draft_data:
        lic = draft_data.get("license", {})
        lines.append(f"- **License Terms:** `{lic.get('name')}` (Verification status: `{lic.get('status')}`, Commercial use: `{lic.get('commercial_use')}`). Contributor claims have not been legally audited.")
        pub = draft_data.get("publisher", {})
        lines.append(f"- **Publisher Identity:** Inferred as `{pub.get('name')}` ({pub.get('type')}) from source domain. Verification required.")
        lines.append("- **Sample Counts & Download Payload:** Omitted from draft. Must be determined from official distribution archives.")
        prov = draft_data.get("provenance", {})
        if prov.get("curation_notes"):
            lines.append(f"- **Contributor Notes & Limitations:** {prov.get('curation_notes')}")
    else:
        lines.append("- Submission is incomplete or invalid; no unverified claims structured into draft metadata.")
    lines.append("")

    # Required Manual Verification Steps Section
    lines.append("## Required Manual Verification Steps\n")
    lines.append("Maintainers must complete the following checks before approving this dataset into the catalog:")
    lines.append("1. [ ] **Source Verification:** Navigate to the official URL, confirm page resolves, and verify data accessibility.")
    lines.append("2. [ ] **Academic Citation & DOI:** Verify DOI resolves to the specific publication and authors match claimed dataset.")
    lines.append("3. [ ] **License Audit:** Inspect repository/data distribution terms directly; distinguish software code licenses from dataset annotation terms.")
    lines.append("4. [ ] **Sample Distribution & Splits:** Audit instance counts, splits, and file formats against authoritative source documents.")
    lines.append("5. [ ] **Catalog Integration:** Move verified draft from `drafts/` to `data/datasets/<slug>.json`, update verification block, and run catalog generation.")
    lines.append("")

    # Recommended Next Steps
    lines.append("## Recommended Next Steps\n")
    if not suggestion.is_valid:
        lines.append("1. **Request Contributor Input:** Ask contributor to provide missing required fields.")
        lines.append("2. Add label: `needs-info`.")
    elif duplicate_result.is_duplicate:
        lines.append(f"1. **Confirm Existing Record:** Verify if `{duplicate_result.primary_match.existing_id}` already fulfills this dataset.")
        lines.append("2. If identical, close issue with link to existing dataset.")
        lines.append("3. Add label: `duplicate`.")
    else:
        lines.append("1. **Maintainer Fact-Check:** Verify official URL, DOI, license, and sample counts.")
        lines.append("2. **Create Feature Branch:** When ready, promote draft to `data/datasets/` and run `scripts/generate_catalog.py`.")
        lines.append("3. Add label: `candidate-approved`.")

    return "\n".join(lines)
