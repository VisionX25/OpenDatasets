#!/usr/bin/env python3
"""OpenDatasets Community Suggestion Duplicate Detector.

Compares incoming dataset suggestions against the existing published catalog
(data/datasets/*.json) to identify exact duplicates and potential candidate
collisions by ID/slug, normalized name, URL, DOI, and token/fuzzy similarity.
"""

from __future__ import annotations

import difflib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from scripts.suggestion_parser import ParsedSuggestion, extract_doi


@dataclass
class DuplicateMatch:
    """Represents a matched existing dataset and detection rationale."""

    existing_id: str
    existing_name: str
    match_type: str  # "exact_id", "exact_slug", "exact_doi", "exact_url", "normalized_url", "exact_name", "normalized_name", "token_overlap", "fuzzy_name"
    confidence: str  # "high_confidence" or "potential_duplicate"
    details: str

    def to_dict(self) -> dict[str, str]:
        return {
            "existing_id": self.existing_id,
            "existing_name": self.existing_name,
            "match_type": self.match_type,
            "confidence": self.confidence,
            "details": self.details,
        }


@dataclass
class DuplicateCheckResult:
    """Consolidated outcome of catalog duplicate detection."""

    is_duplicate: bool = False
    has_potential_matches: bool = False
    matches: list[DuplicateMatch] = field(default_factory=list)
    primary_match: DuplicateMatch | None = None
    summary: str = "No duplicate or similar datasets found."

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_duplicate": self.is_duplicate,
            "has_potential_matches": self.has_potential_matches,
            "summary": self.summary,
            "primary_match": self.primary_match.to_dict() if self.primary_match else None,
            "matches": [m.to_dict() for m in self.matches],
        }


def normalize_text_for_comparison(text: str) -> str:
    """Lowercase and strip non-alphanumeric characters for robust comparison."""
    if not text:
        return ""
    # Normalize unicode / lowercase and remove punctuation
    lowered = text.lower().strip()
    return re.sub(r"[^\w\s]", "", lowered)


def tokenize_name(name: str) -> set[str]:
    """Tokenize a dataset name into word tokens, ignoring trivial stop words."""
    stop_words = {"dataset", "data", "benchmark", "corpus", "the", "a", "an", "for", "in", "of", "and"}
    norm = normalize_text_for_comparison(name)
    tokens = {t for t in norm.split() if len(t) > 1 and t not in stop_words}
    return tokens


def normalize_url_canonical(url: str) -> str:
    """Canonicalize a URL for comparison (protocol-agnostic, strip trailing slash and tracking)."""
    if not url or not isinstance(url, str):
        return ""
    cleaned = url.strip()
    try:
        parsed = urlparse(cleaned)
        netloc = parsed.netloc.lower()
        if netloc.startswith("www."):
            netloc = netloc[4:]
        # Remove default ports
        if netloc.endswith(":80"):
            netloc = netloc[:-3]
        elif netloc.endswith(":443"):
            netloc = netloc[:-4]

        path = parsed.path.rstrip("/")
        # Query: filter out common UTM params
        query_parts = []
        if parsed.query:
            for param in parsed.query.split("&"):
                if not param.lower().startswith(("utm_", "ref=")):
                    query_parts.append(param)
        canonical_query = f"?{'&'.join(query_parts)}" if query_parts else ""

        return f"{netloc}{path}{canonical_query}"
    except Exception:
        return cleaned.lower().rstrip("/")


def normalize_doi_canonical(doi: str) -> str:
    """Canonicalize DOI string (strip doi.org prefix, lowercase)."""
    if not doi or not isinstance(doi, str):
        return ""
    cleaned = doi.strip()
    match = re.search(r"10\.\d{4,9}/[-._;()/:A-Za-z0-9]+", cleaned, re.IGNORECASE)
    if match:
        return match.group(0).lower().rstrip(".,;)")
    return cleaned.lower()


def load_catalog_datasets(data_dir: Path) -> list[dict[str, Any]]:
    """Load all existing JSON dataset records from data/datasets/."""
    datasets: list[dict[str, Any]] = []
    if not data_dir.exists():
        return datasets

    for json_file in sorted(data_dir.glob("*.json")):
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict) and "id" in data:
                    datasets.append(data)
        except Exception:
            continue
    return datasets


def check_suggestion_for_duplicates(
    suggestion: ParsedSuggestion,
    existing_datasets: list[dict[str, Any]],
    candidate_slug: str = "",
) -> DuplicateCheckResult:
    """Compare a parsed suggestion against existing datasets in the catalog.

    Checks:
    1. Exact ID / Slug match (High confidence)
    2. Exact / Normalized DOI match (High confidence)
    3. Exact / Canonical URL match (High confidence)
    4. Exact / Normalized dataset name match (High confidence)
    5. High token overlap / fuzzy name similarity (Potential duplicate for review)
    """
    matches: list[DuplicateMatch] = []

    sug_name = suggestion.name.strip()
    sug_norm_name = normalize_text_for_comparison(sug_name)
    sug_tokens = tokenize_name(sug_name)

    sug_canonical_url = normalize_url_canonical(suggestion.source_url)
    sug_canonical_doi = normalize_doi_canonical(suggestion.doi)

    for ds in existing_datasets:
        ds_id = ds.get("id", "")
        ds_slug = ds.get("slug", "")
        ds_name = ds.get("name", "")
        ds_norm_name = normalize_text_for_comparison(ds_name)
        ds_tokens = tokenize_name(ds_name)

        # 1. Exact ID / Slug match
        if candidate_slug:
            if candidate_slug.lower() == ds_slug.lower() or candidate_slug.lower() == ds_id.lower():
                matches.append(
                    DuplicateMatch(
                        existing_id=ds_id,
                        existing_name=ds_name,
                        match_type="exact_slug",
                        confidence="high_confidence",
                        details=f"Candidate slug '{candidate_slug}' exactly matches existing dataset ID '{ds_id}'.",
                    )
                )
                continue

        # 2. Exact or Normalized Name match
        if sug_name.lower() == ds_name.lower():
            matches.append(
                DuplicateMatch(
                    existing_id=ds_id,
                    existing_name=ds_name,
                    match_type="exact_name",
                    confidence="high_confidence",
                    details=f"Suggestion name exactly matches existing dataset '{ds_name}'.",
                )
            )
            continue
        elif sug_norm_name and sug_norm_name == ds_norm_name and len(sug_norm_name) > 3:
            matches.append(
                DuplicateMatch(
                    existing_id=ds_id,
                    existing_name=ds_name,
                    match_type="normalized_name",
                    confidence="high_confidence",
                    details=f"Normalized name '{sug_norm_name}' matches '{ds_name}'.",
                )
            )
            continue

        # 3. DOI match (if suggestion has DOI)
        if sug_canonical_doi:
            ds_citation = ds.get("citation", {})
            ds_doi = normalize_doi_canonical(ds_citation.get("doi", ""))
            if not ds_doi:
                # Also check source_references for DOI
                for ref in ds.get("source_references", []):
                    ref_doi = normalize_doi_canonical(extract_doi(ref.get("url", "")))
                    if ref_doi:
                        ds_doi = ref_doi
                        break

            if ds_doi and ds_doi == sug_canonical_doi:
                matches.append(
                    DuplicateMatch(
                        existing_id=ds_id,
                        existing_name=ds_name,
                        match_type="exact_doi",
                        confidence="high_confidence",
                        details=f"DOI '{suggestion.doi}' matches existing dataset '{ds_name}' ({ds_doi}).",
                    )
                )
                continue

        # 4. Canonical URL match
        if sug_canonical_url:
            ds_urls = [normalize_url_canonical(ds.get("homepage_url", ""))]
            for ref in ds.get("source_references", []):
                ds_urls.append(normalize_url_canonical(ref.get("url", "")))

            if sug_canonical_url in ds_urls:
                matches.append(
                    DuplicateMatch(
                        existing_id=ds_id,
                        existing_name=ds_name,
                        match_type="canonical_url",
                        confidence="high_confidence",
                        details=f"Source URL '{suggestion.source_url}' matches existing dataset '{ds_name}'.",
                    )
                )
                continue

        # 5. Token Overlap & Fuzzy Similarity (Warnings only, never automatic rejection)
        if sug_tokens and ds_tokens:
            intersection = sug_tokens & ds_tokens
            union = sug_tokens | ds_tokens
            jaccard = len(intersection) / len(union) if union else 0.0

            fuzzy_ratio = difflib.SequenceMatcher(None, sug_norm_name, ds_norm_name).ratio()

            if jaccard >= 0.70 or fuzzy_ratio >= 0.82:
                matches.append(
                    DuplicateMatch(
                        existing_id=ds_id,
                        existing_name=ds_name,
                        match_type="token_overlap" if jaccard >= 0.70 else "fuzzy_name",
                        confidence="potential_duplicate",
                        details=(
                            f"Name similarity warning with '{ds_name}' "
                            f"(Jaccard token overlap: {jaccard:.2f}, String ratio: {fuzzy_ratio:.2f}). "
                            "Flagged for human maintainer review (not auto-rejected)."
                        ),
                    )
                )

    # Sort matches: high_confidence first
    matches.sort(key=lambda m: 0 if m.confidence == "high_confidence" else 1)

    result = DuplicateCheckResult()
    result.matches = matches
    result.has_potential_matches = len(matches) > 0
    result.is_duplicate = any(m.confidence == "high_confidence" for m in matches)

    if matches:
        result.primary_match = matches[0]
        if result.is_duplicate:
            result.summary = (
                f"Duplicate detected with high confidence against existing dataset "
                f"'{result.primary_match.existing_name}' ({result.primary_match.existing_id}): "
                f"{result.primary_match.details}"
            )
        else:
            result.summary = (
                f"Potential similarity flagged for maintainer review with "
                f"'{result.primary_match.existing_name}' ({result.primary_match.existing_id}): "
                f"{result.primary_match.details}"
            )
    else:
        result.summary = "No duplicate or similar datasets detected in published catalog."

    return result
