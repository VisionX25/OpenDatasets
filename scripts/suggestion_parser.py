#!/usr/bin/env python3
"""OpenDatasets Community Suggestion Parser.

Securely parses, sanitizes, and validates dataset suggestion issues submitted
via GitHub Issue Forms (.github/ISSUE_TEMPLATE/dataset_suggestion.yml).
Treats all issue contents as untrusted contributor input.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse


@dataclass
class ParsedSuggestion:
    """Structured representation of a parsed dataset suggestion."""

    name: str = ""
    source_url: str = ""
    category: str = ""
    task: str = ""
    description: str = ""
    license_text: str = ""
    doi: str = ""
    paper_url: str = ""
    notes: str = ""
    is_template_match: bool = True
    raw_sections: dict[str, str] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        """Returns True if all required fields are present and valid."""
        return len(self.errors) == 0


def sanitize_untrusted_text(text: Any) -> str:
    """Sanitize raw contributor input by stripping control chars and null bytes.

    Never executes or interprets input. Preserves printable characters,
    newlines, tabs, and Unicode (including Bangla and non-Latin scripts).
    """
    if not isinstance(text, str):
        return ""
    # Strip null bytes and unsafe ASCII control characters (keep \t and \n)
    sanitized = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    return sanitized.strip()


def is_no_response(text: str) -> bool:
    """Check if the field contains GitHub's default empty marker."""
    norm = text.strip()
    return norm in ("_No response_", "No response", "N/A", "n/a", "none", "None", "")


def is_valid_url(candidate: str) -> tuple[bool, str]:
    """Validate HTTP/HTTPS URL syntax strictly without network requests."""
    if not candidate or not isinstance(candidate, str):
        return False, "URL is missing or empty."
    if re.search(r"\s", candidate):
        return False, "URL contains illegal whitespace characters."

    try:
        parsed = urlparse(candidate.strip())
    except Exception as exc:
        return False, f"URL parsing error: {exc}"

    if parsed.scheme not in ("http", "https"):
        return False, f"URL scheme must be http or https, got '{parsed.scheme}'."
    if not parsed.netloc or "." not in parsed.netloc:
        return False, f"URL missing a valid host domain: '{candidate}'."

    return True, ""


def split_issue_form_sections(body: str) -> dict[str, str]:
    """Split issue markdown into section dictionary keyed by normalized heading."""
    sections: dict[str, str] = {}
    cleaned_body = sanitize_untrusted_text(body)

    # Match markdown headings level 2 or 3 (e.g., '### Dataset name')
    header_pattern = re.compile(r"^(#{2,3})\s+(.+?)\s*$", re.MULTILINE)
    matches = list(header_pattern.finditer(cleaned_body))

    if not matches:
        return sections

    for idx, match in enumerate(matches):
        raw_heading = match.group(2).strip()
        start_pos = match.end()
        end_pos = matches[idx + 1].start() if idx + 1 < len(matches) else len(cleaned_body)
        content = cleaned_body[start_pos:end_pos].strip()

        # Normalize heading key: lowercase, strip punctuation
        norm_key = re.sub(r"[^a-z0-9]+", " ", raw_heading.lower()).strip()
        sections[norm_key] = content

    return sections


def extract_doi(text: str) -> str:
    """Extract standard DOI pattern from text if present."""
    if not text or is_no_response(text):
        return ""
    # Standard DOI regex: 10.xxxx/...
    match = re.search(r"\b(10\.\d{4,9}/[-._;()/:A-Za-z0-9]+)", text)
    if match:
        doi = match.group(1).rstrip(".,;)")
        return doi
    return ""


def parse_usefulness_section(text: str) -> tuple[str, str, str]:
    """Extract category, task, and description from the usefulness section.

    Handles both structured Markdown emitted by OpenDatasets submission portal
    and free-form text submitted directly via GitHub.
    """
    category = ""
    task = ""
    description = ""

    # Check for structured keys: **Category:**, **Primary Task:**, **Description:**
    cat_match = re.search(r"\*\*Category:\*\*\s*([^\n]+)", text, re.IGNORECASE)
    task_match = re.search(r"\*\*Primary Task:\*\*\s*([^\n]+)", text, re.IGNORECASE)
    desc_match = re.search(r"\*\*Description:\*\*\s*(.+)$", text, re.IGNORECASE | re.DOTALL)

    if cat_match:
        category = cat_match.group(1).strip()
    if task_match:
        task = task_match.group(1).strip()
    if desc_match:
        description = desc_match.group(1).strip()
    else:
        # Fallback for freeform: remove Category and Task lines if matched, remainder is description
        remainder = text
        if cat_match:
            remainder = remainder.replace(cat_match.group(0), "")
        if task_match:
            remainder = remainder.replace(task_match.group(0), "")
        # Remove bold headers like **Description:** if present without newline
        remainder = re.sub(r"\*\*Description:\*\*", "", remainder, flags=re.IGNORECASE)
        description = remainder.strip()

    return category, task, description


def parse_evidence_section(text: str) -> tuple[str, str, str]:
    """Extract DOI, supporting paper URL, and additional notes from evidence section."""
    doi = ""
    paper_url = ""
    notes = ""

    # 1. Extract DOI
    doi_match = re.search(r"-\s*\*\*DOI:\*\*\s*([^\n]+)", text, re.IGNORECASE)
    if doi_match:
        cand = doi_match.group(1).strip()
        if not is_no_response(cand):
            doi = extract_doi(cand) or cand
    else:
        doi = extract_doi(text)

    # 2. Extract Supporting Paper URL
    paper_match = re.search(r"-\s*\*\*Supporting Paper URL:\*\*\s*([^\n]+)", text, re.IGNORECASE)
    if paper_match:
        cand = paper_match.group(1).strip()
        if not is_no_response(cand):
            valid, _ = is_valid_url(cand)
            if valid:
                paper_url = cand

    # 3. Extract Additional Notes / Limitations
    notes_match = re.search(
        r"-\s*\*\*Additional Notes / Limitations:\*\*\s*(.+)$",
        text,
        re.IGNORECASE | re.DOTALL,
    )
    if notes_match:
        cand_notes = notes_match.group(1).strip()
        if not is_no_response(cand_notes):
            notes = cand_notes
    else:
        # Free-form fallback: strip DOI and Paper URL lines
        lines = []
        for line in text.splitlines():
            if re.search(r"\*\*DOI:\*\*", line, re.IGNORECASE):
                continue
            if re.search(r"\*\*Supporting Paper URL:\*\*", line, re.IGNORECASE):
                continue
            lines.append(line)
        free_notes = "\n".join(lines).strip()
        if not is_no_response(free_notes):
            notes = free_notes

    return doi, paper_url, notes


def is_dataset_suggestion_template(issue_body: str) -> bool:
    """Check whether an issue body adheres to the dataset suggestion template structure.

    Requires at least the dataset name section and at least one other standard section
    (source URL, modality/usefulness, or license terms).
    """
    sections = split_issue_form_sections(issue_body)
    if not sections:
        return False
    has_name = any("dataset name" in k or k == "name" for k in sections)
    has_source = any("source" in k or "url" in k or "publisher" in k for k in sections)
    has_usefulness = any("usefulness" in k or "modality" in k or "task" in k for k in sections)
    has_license = any("license" in k for k in sections)

    return has_name and (has_source or has_usefulness or has_license)


def parse_dataset_suggestion(issue_body: str) -> ParsedSuggestion:
    """Parse and validate a GitHub issue body into a ParsedSuggestion.

    Validates all required fields against OpenDatasets standards:
    - Dataset Name: non-empty, >= 2 chars
    - Source URL: valid http/https URL with domain
    - Description: non-empty, >= 10 chars
    """
    suggestion = ParsedSuggestion()
    sections = split_issue_form_sections(issue_body)
    suggestion.raw_sections = sections

    # Verify that this issue matches the dataset suggestion template structure
    if not is_dataset_suggestion_template(issue_body):
        suggestion.is_template_match = False
        suggestion.errors.append("Issue body does not match the dataset suggestion template format.")
        return suggestion

    # Match section keys flexibly
    name_content = ""
    source_content = ""
    usefulness_content = ""
    license_content = ""
    evidence_content = ""

    for key, val in sections.items():
        if "dataset name" in key or key == "name":
            name_content = val
        elif "source" in key or "url" in key or "publisher" in key:
            source_content = val
        elif "usefulness" in key or "modality" in key or "task" in key:
            usefulness_content = val
        elif "license" in key:
            license_content = val
        elif "evidence" in key or "limitation" in key:
            evidence_content = val

    # 1. Dataset Name
    clean_name = sanitize_untrusted_text(name_content)
    if not clean_name or is_no_response(clean_name):
        suggestion.errors.append("Required field 'Dataset name' is missing or empty.")
    elif len(clean_name) < 2:
        suggestion.errors.append(f"Dataset name '{clean_name}' must be at least 2 characters long.")
    elif len(clean_name) > 150:
        suggestion.errors.append(f"Dataset name exceeds maximum schema length of 150 characters ({len(clean_name)}).")
    else:
        suggestion.name = clean_name

    # 2. Official Source URL
    clean_source = sanitize_untrusted_text(source_content)
    # If the user included markdown links like [https://...](https://...), extract raw URL
    link_match = re.search(r"https?://[^\s)\]]+", clean_source)
    target_url = link_match.group(0) if link_match else clean_source

    valid_url, url_err = is_valid_url(target_url)
    if not valid_url:
        suggestion.errors.append(f"Required field 'Official dataset URL' is invalid: {url_err}")
    else:
        suggestion.source_url = target_url

    # 3. Usefulness (Category, Task, Description)
    clean_usefulness = sanitize_untrusted_text(usefulness_content)
    if not clean_usefulness or is_no_response(clean_usefulness):
        suggestion.errors.append("Required section 'Modality, task, and usefulness' is missing.")
    else:
        cat, task, desc = parse_usefulness_section(clean_usefulness)
        suggestion.category = cat
        suggestion.task = task
        if not desc or is_no_response(desc):
            suggestion.errors.append("Required 'Description' is missing from the submission.")
        elif len(desc) < 10:
            suggestion.errors.append(
                f"Description must be at least 10 characters long (received {len(desc)} characters)."
            )
        else:
            suggestion.description = desc

    # 4. License Information
    clean_license = sanitize_untrusted_text(license_content)
    if not clean_license or is_no_response(clean_license):
        suggestion.license_text = "Unknown / Not specified by source"
        suggestion.warnings.append("License is not established in submission; defaulting to Unknown.")
    else:
        suggestion.license_text = clean_license

    # 5. Additional Evidence & Limitations
    clean_evidence = sanitize_untrusted_text(evidence_content)
    if clean_evidence and not is_no_response(clean_evidence):
        doi, paper_url, notes = parse_evidence_section(clean_evidence)
        suggestion.doi = doi
        suggestion.paper_url = paper_url
        suggestion.notes = notes

    return suggestion
