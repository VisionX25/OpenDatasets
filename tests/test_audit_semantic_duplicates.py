"""Automated test suite for Cross-Dataset Semantic Duplicate Detection Engine."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from scripts.audit_semantic_duplicates import (
    DEFAULT_DATASETS_DIR,
    audit_catalog_semantic_duplicates,
    calculate_title_fuzzy_ratio,
    calculate_token_jaccard,
    evaluate_candidate_pair,
    extract_archive_identifier,
    extract_discriminating_features,
    extract_repository_identifier,
    extract_title_aliases,
    extract_title_tokens,
    is_generic_hosting_url,
    main,
    normalize_doi,
    normalize_title,
    normalize_url,
)


# ==============================================================================
# 1. URL Normalization & Generic Domain Identification Tests
# ==============================================================================


def test_normalize_url_canonicalization() -> None:
    """Verify safe URL canonicalization across protocols, ports, and trailing slashes."""
    assert normalize_url("https://example.com/dataset/") == "example.com/dataset"
    assert normalize_url("http://EXAMPLE.COM/dataset") == "example.com/dataset"
    assert normalize_url("https://www.example.com/path/") == "example.com/path"
    assert normalize_url("http://example.com:80/path") == "example.com/path"
    assert normalize_url("https://example.com:443/path") == "example.com/path"


def test_normalize_url_tracking_param_removal() -> None:
    """Ensure analytics tracking query parameters are safely stripped while preserving functional params."""
    tracked_url = "https://example.com/data?utm_source=twitter&utm_medium=social&ref=github&version=2"
    normalized = normalize_url(tracked_url)
    assert "utm_source" not in normalized
    assert "utm_medium" not in normalized
    assert "ref" not in normalized
    assert "version=2" in normalized


def test_normalize_url_doi_canonicalization() -> None:
    """Ensure DOI URLs are transformed into canonical doi.org/10.xxxx format."""
    assert normalize_url("https://doi.org/10.1109/CVPR.2019.00686") == "doi.org/10.1109/cvpr.2019.00686"
    assert normalize_url("http://dx.doi.org/10.1145/3219819.3219845/") == "doi.org/10.1145/3219819.3219845"


def test_is_generic_hosting_url() -> None:
    """Verify detection of generic platform roots and multi-dataset directories."""
    # Generic roots
    assert is_generic_hosting_url("https://github.com") is True
    assert is_generic_hosting_url("https://github.com/") is True
    assert is_generic_hosting_url("https://huggingface.co/datasets") is True
    assert is_generic_hosting_url("https://archive.ics.uci.edu/datasets") is True
    assert is_generic_hosting_url("https://spacenet.ai/datasets") is True
    assert is_generic_hosting_url("https://disc.gsfc.nasa.gov/datasets") is True
    assert is_generic_hosting_url("https://challenge.isic-archive.com/data") is True

    # Specific dataset endpoints
    assert is_generic_hosting_url("https://github.com/facebookresearch/covost") is False
    assert is_generic_hosting_url("https://zenodo.org/records/3819968") is False
    assert is_generic_hosting_url("https://huggingface.co/datasets/cifar10") is False
    assert is_generic_hosting_url("https://archive.ics.uci.edu/dataset/53/iris") is False


# ==============================================================================
# 2. DOI Normalization Tests
# ==============================================================================


def test_normalize_doi() -> None:
    """Verify DOI prefix stripping, lowercasing, and trailing punctuation cleanup."""
    assert normalize_doi("10.1109/ICASSP40776.2020.9052990") == "10.1109/icassp40776.2020.9052990"
    assert normalize_doi("https://doi.org/10.1007/978-3-031-72658-3_13") == "10.1007/978-3-031-72658-3_13"
    assert normalize_doi("doi: 10.21437/Interspeech.2021-2027.") == "10.21437/interspeech.2021-2027"
    assert normalize_doi("http://dx.doi.org/10.22489/CinC.2020.236)") == "10.22489/cinc.2020.236"
    assert normalize_doi("") == ""


# ==============================================================================
# 3. Title Normalization, Tokenization, and Alias Extraction Tests
# ==============================================================================


def test_normalize_title() -> None:
    """Verify title normalization removes punctuation and lowercases."""
    assert normalize_title("Clotho: An Audio Captioning Dataset (v2.1)") == "clotho an audio captioning dataset v21"
    assert normalize_title("Argoverse 2 — Sensor Dataset") == "argoverse 2  sensor dataset"


def test_extract_title_tokens() -> None:
    """Ensure stop words are filtered out from title tokens."""
    tokens = extract_title_tokens("Clotho: An Audio Captioning Dataset for Benchmark")
    assert "clotho" in tokens
    assert "audio" in tokens
    assert "captioning" in tokens
    assert "dataset" not in tokens
    assert "benchmark" not in tokens
    assert "for" not in tokens
    assert "an" not in tokens


def test_extract_title_aliases() -> None:
    """Verify extraction of acronyms and aliases from titles and tags."""
    # Prefix before colon
    aliases_gqa = extract_title_aliases("GQA: A New Dataset for Real-World Visual Reasoning")
    assert "gqa" in aliases_gqa

    # Prefix before em-dash
    aliases_a2d2 = extract_title_aliases("A2D2 — Audi Autonomous Driving Dataset")
    assert "a2d2" in aliases_a2d2

    # Parenthetical acronym
    aliases_ghcn = extract_title_aliases("Global Historical Climatology Network daily (GHCNd)")
    assert "ghcnd" in aliases_ghcn

    # Tag-derived alias
    aliases_with_tags = extract_title_aliases("Sample Benchmark", tags=["mnist", "vision"])
    assert "mnist" in aliases_with_tags


# ==============================================================================
# 4. Repository & Archive Identifier Extraction Tests
# ==============================================================================


def test_extract_repository_identifier() -> None:
    """Verify canonical GitHub / GitLab repository parsing."""
    assert extract_repository_identifier("https://github.com/audio-captioning/clotho-dataset.git") == "github:audio-captioning/clotho-dataset"
    assert extract_repository_identifier("https://github.com/SharifMAbdullah/breaking-the-silence") == "github:sharifmabdullah/breaking-the-silence"
    assert extract_repository_identifier("https://example.com/not-a-repo") is None


def test_extract_archive_identifier() -> None:
    """Verify Zenodo and Hugging Face archive identifier parsing."""
    assert extract_archive_identifier("https://zenodo.org/records/3819968") == "zenodo:3819968"
    assert extract_archive_identifier("https://zenodo.org/record/1234567") == "zenodo:1234567"
    assert extract_archive_identifier("https://huggingface.co/datasets/nyu-mll/glue") == "hf:nyu-mll/glue"
    assert extract_archive_identifier("https://example.com/not-an-archive") is None


# ==============================================================================
# 5. Discriminating Feature Detection Tests
# ==============================================================================


def test_extract_discriminating_features() -> None:
    """Ensure versions, class counts, and sensor modalities are detected as discriminating."""
    rec_cifar10 = {"id": "cifar-10", "name": "CIFAR-10", "modalities": ["vision"]}
    rec_cifar100 = {"id": "cifar-100", "name": "CIFAR-100", "modalities": ["vision"]}
    disc_cifar = extract_discriminating_features(rec_cifar10, rec_cifar100)
    assert "10" in disc_cifar
    assert "100" in disc_cifar

    rec_v1 = {"id": "kolektorsdd", "name": "KolektorSDD: Kolektor Surface-Defect Dataset", "modalities": ["vision"]}
    rec_v2 = {"id": "kolektorsdd2", "name": "KolektorSDD2: Kolektor Surface-Defect Dataset 2", "modalities": ["vision"]}
    disc_ver = extract_discriminating_features(rec_v1, rec_v2)
    assert "2" in disc_ver

    rec_mimic3 = {"id": "mimic-iii", "name": "MIMIC-III Medical Information Mart III", "modalities": ["tabular"]}
    rec_mimic4 = {"id": "mimic-iv", "name": "MIMIC-IV Medical Information Mart IV", "modalities": ["tabular"]}
    disc_mimic = extract_discriminating_features(rec_mimic3, rec_mimic4)
    assert "iii" in disc_mimic
    assert "iv" in disc_mimic


# ==============================================================================
# 6. High-Confidence Detection Tests
# ==============================================================================


def test_high_confidence_exact_duplicate_detection() -> None:
    """Verify that identical records without discriminating factors are flagged as high confidence."""
    ds_orig = {
        "id": "synthetic-benchmark",
        "slug": "synthetic-benchmark",
        "name": "Synthetic Benchmark for Object Detection",
        "homepage_url": "https://example.org/synthetic-bench",
        "publisher": {"name": "Vision AI Lab", "type": "academic"},
        "modalities": ["vision"],
        "tasks": ["object-detection"],
    }
    ds_dup = {
        "id": "synthetic-benchmark-copy",
        "slug": "synthetic-benchmark-copy",
        "name": "Synthetic Benchmark for Object Detection",
        "homepage_url": "https://example.org/synthetic-bench",
        "publisher": {"name": "Vision AI Lab", "type": "academic"},
        "modalities": ["vision"],
        "tasks": ["object-detection"],
    }

    match = evaluate_candidate_pair(ds_orig, ds_dup)
    assert match is not None
    assert match.confidence == "high"
    assert match.recommended_action == "deprecate_or_merge_duplicate"


def test_high_confidence_id_slug_collision() -> None:
    """Verify that an exact ID or slug collision triggers high confidence."""
    ds_a = {"id": "collision-id", "slug": "slug-a", "name": "Dataset Alpha", "publisher": {"name": "Lab A"}}
    ds_b = {"id": "collision-id", "slug": "slug-b", "name": "Dataset Beta", "publisher": {"name": "Lab B"}}
    match = evaluate_candidate_pair(ds_a, ds_b)
    assert match is not None
    assert match.confidence == "high"


# ==============================================================================
# 7. Medium-Confidence Safeguard Tests (Subsets, Versions, Suite Publications)
# ==============================================================================


def test_different_dataset_versions_downgraded_to_medium() -> None:
    """Verify that different version numbers prevent premature high-confidence duplicate flagging."""
    ds_v1 = {
        "id": "challenge-2018",
        "name": "Medical Imaging Challenge 2018",
        "homepage_url": "https://challenge.example.org",
        "publisher": {"name": "Challenge Consortium", "type": "academic"},
        "modalities": ["vision"],
        "tasks": ["image-classification"],
    }
    ds_v2 = {
        "id": "challenge-2019",
        "name": "Medical Imaging Challenge 2019",
        "homepage_url": "https://challenge.example.org",
        "publisher": {"name": "Challenge Consortium", "type": "academic"},
        "modalities": ["vision"],
        "tasks": ["image-classification"],
    }

    match = evaluate_candidate_pair(ds_v1, ds_v2)
    assert match is not None
    assert match.confidence == "medium"
    assert "distinct_benchmark_subsets_under_shared_project_umbrella" in match.potential_false_positive_reasons


def test_dataset_subsets_under_shared_umbrella_homepage() -> None:
    """Verify that benchmark tracks sharing a homepage are medium confidence."""
    ds_lidar = {
        "id": "autonomous-lidar",
        "name": "Autonomous Driving LiDAR Dataset",
        "homepage_url": "https://driving.example.org/suite",
        "publisher": {"name": "Autonomous Lab", "type": "industry"},
        "modalities": ["sensor"],
        "tasks": ["3d-object-detection"],
    }
    ds_sensor = {
        "id": "autonomous-sensor",
        "name": "Autonomous Driving Sensor Dataset",
        "homepage_url": "https://driving.example.org/suite",
        "publisher": {"name": "Autonomous Lab", "type": "industry"},
        "modalities": ["sensor", "vision"],
        "tasks": ["tracking"],
    }

    match = evaluate_candidate_pair(ds_lidar, ds_sensor)
    assert match is not None
    assert match.confidence == "medium"
    assert match.recommended_action == "maintain_as_distinct_with_cross_reference"


def test_shared_research_paper_doi() -> None:
    """Verify that datasets sharing a research paper DOI are not classified as high confidence."""
    ds_maps = {
        "id": "crop-maps",
        "name": "Global Crop Landcover Maps",
        "citation": {"doi": "10.5194/essd-15-5491-2023"},
        "publisher": {"name": "Earth Observation Lab", "type": "government"},
        "modalities": ["tabular"],
    }
    ds_points = {
        "id": "crop-reference-data",
        "name": "Global Crop In-Situ Reference Points",
        "citation": {"doi": "10.5194/essd-15-5491-2023"},
        "publisher": {"name": "Earth Observation Lab", "type": "government"},
        "modalities": ["tabular"],
    }

    match = evaluate_candidate_pair(ds_maps, ds_points)
    assert match is not None
    assert match.confidence == "medium"
    assert "shared_foundational_or_benchmark_suite_publication" in match.potential_false_positive_reasons


# ==============================================================================
# 8. Low-Confidence & False-Positive Prevention Tests
# ==============================================================================


def test_cross_institution_lexical_similarity_is_low_confidence() -> None:
    """Verify that lexical phrasing overlap across independent institutions is low confidence."""
    ds_a = {
        "id": "lab-a-intrusion",
        "name": "CIC Network Intrusion Detection Dataset",
        "publisher": {"name": "University A", "type": "academic"},
        "modalities": ["tabular"],
    }
    ds_b = {
        "id": "lab-b-intrusion",
        "name": "UNSW Network Intrusion Detection Dataset",
        "publisher": {"name": "University B", "type": "academic"},
        "modalities": ["tabular"],
    }

    match = evaluate_candidate_pair(ds_a, ds_b)
    assert match is not None
    assert match.confidence == "low"
    assert "cross_institution_lexical_similarity" in match.potential_false_positive_reasons


def test_generic_portal_url_does_not_trigger_url_match() -> None:
    """Ensure two datasets sharing a generic portal URL are not flagged for matching homepages."""
    ds_a = {
        "id": "spacenet-task-a",
        "name": "SpaceNet Building Footprints",
        "homepage_url": "https://spacenet.ai/datasets",
        "publisher": {"name": "SpaceNet Consortium", "type": "community"},
        "modalities": ["vision"],
    }
    ds_b = {
        "id": "spacenet-task-b",
        "name": "SpaceNet Road Networks",
        "homepage_url": "https://spacenet.ai/datasets",
        "publisher": {"name": "SpaceNet Consortium", "type": "community"},
        "modalities": ["vision"],
    }

    match = evaluate_candidate_pair(ds_a, ds_b)
    # Since homepage is generic, canonical_homepage_match must be False
    if match:
        assert match.matching_signals["canonical_homepage_match"] is False


# ==============================================================================
# 9. Deterministic Catalog Audit & Report Generation Tests
# ==============================================================================


def test_audit_catalog_deterministic_output() -> None:
    """Verify that auditing the published catalog is completely deterministic across repeated executions."""
    data_dir = DEFAULT_DATASETS_DIR
    files = sorted(data_dir.glob("*.json"))
    assert len(files) == 750

    datasets = [json.loads(f.read_text(encoding="utf-8")) for f in files]

    res_1 = audit_catalog_semantic_duplicates(datasets)
    res_2 = audit_catalog_semantic_duplicates(datasets)

    assert res_1["audit_metadata"]["total_records_scanned"] == 750
    assert res_1["audit_metadata"]["total_candidate_pairs"] == res_2["audit_metadata"]["total_candidate_pairs"]
    assert res_1["audit_metadata"]["confidence_distribution"] == res_2["audit_metadata"]["confidence_distribution"]

    pair_ids_1 = [p["pair_id"] for p in res_1["candidate_pairs"]]
    pair_ids_2 = [p["pair_id"] for p in res_2["candidate_pairs"]]
    assert pair_ids_1 == pair_ids_2


def test_cli_main_generates_reports(tmp_path: Path) -> None:
    """Verify that running the audit CLI creates both JSON and Markdown reports with exit code 0."""
    json_path = tmp_path / "report.json"
    md_path = tmp_path / "summary.md"

    exit_code = main([
        "--datasets-dir", str(DEFAULT_DATASETS_DIR),
        "--output-json", str(json_path),
        "--output-md", str(md_path),
        "--quiet",
    ])

    assert exit_code == 0
    assert json_path.exists()
    assert md_path.exists()

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["audit_metadata"]["total_records_scanned"] == 750
    assert data["audit_metadata"]["confidence_distribution"]["high"] == 0


def test_audit_semantic_duplicates_dynamic_counts_and_provenance(tmp_path: Path) -> None:
    """Verify dynamic pair counts, custom task/date provenance, and updated text claims."""
    from scripts.audit_semantic_duplicates import generate_markdown_summary

    files = sorted(DEFAULT_DATASETS_DIR.glob("*.json"))
    datasets = [json.loads(f.read_text(encoding="utf-8")) for f in files]

    audit_task = "Task 49 — Cross-Dataset Semantic Duplicate Detection"
    audit_date = "2026-11-20"
    results = audit_catalog_semantic_duplicates(
        datasets,
        audit_task=audit_task,
        audit_date=audit_date,
    )

    meta = results["audit_metadata"]
    assert meta["audit_task"] == audit_task
    assert meta["audit_date"] == audit_date
    assert meta["total_records_scanned"] == 750
    assert meta["total_possible_pairs"] == 750 * 749 // 2  # 280,875

    md = generate_markdown_summary(results)
    assert f"> **Audit Task:** {audit_task}" in md
    assert f"> **Audit Date:** {audit_date}" in md
    assert "280,875" in md
    assert "262,450" not in md
    assert "625 dataset records" not in md
    assert "All 625 dataset records" not in md
    assert "Medium-confidence candidate pairs require manual review to establish scientific distinctness." in md
    assert "All medium-confidence candidate pairs have been reviewed and verified" not in md
