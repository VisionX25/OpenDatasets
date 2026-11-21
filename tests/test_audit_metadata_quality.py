"""Unit tests for OpenDatasets Metadata Quality & Research Readiness Audit.

Tests scripts/audit_metadata_quality.py covering:
  - Required versus optional fields
  - Unknown versus missing metadata
  - Not-applicable fields
  - License classifications & access clarity
  - Sample-unit consistency & split arithmetic integrity
  - Deterministic report ordering
  - Duplicate source references within a record
  - Incorrect metadata types (DOIs, BibTeX braces, task-modality alignment)
  - Incomplete citations & authoritative non-academic repositories
  - Category-level aggregation
  - Absence of scientific-quality claims from documentation metrics
  - 100% offline execution without network dependencies
"""

from __future__ import annotations

import copy
from typing import Any
import pytest

from scripts.audit_metadata_quality import (
    DOI_PATTERN,
    RESEARCH_CATEGORIES,
    audit_catalog_metadata_quality,
    calculate_documentation_completeness,
    derive_dataset_categories,
    evaluate_licensing_and_access,
    evaluate_research_readiness,
    evaluate_scientific_consistency,
    generate_markdown_summary,
    is_geographic_coverage_applicable,
    is_language_applicable,
)


@pytest.fixture
def minimal_dataset() -> dict[str, Any]:
    """Provide a minimal valid synthetic dataset."""
    return {
        "schema_version": "1.0.0",
        "id": "synthetic-cv-benchmark",
        "slug": "synthetic-cv-benchmark",
        "name": "Synthetic Computer Vision Benchmark",
        "description": "A synthetic evaluation dataset for testing unit behaviors.",
        "homepage_url": "https://opendatasets.example.org/synthetic",
        "publisher": {
            "name": "OpenDatasets Lab",
            "type": "academic",
            "url": "https://opendatasets.example.org",
        },
        "modalities": ["vision"],
        "tasks": ["object-detection"],
        "tags": ["benchmark", "synthetic", "vision"],
        "license": {
            "status": "verified_open",
            "name": "Apache-2.0",
            "spdx_id": "Apache-2.0",
            "url": "https://www.apache.org/licenses/LICENSE-2.0",
            "commercial_use": "allowed",
            "notes": "Freely available for commercial and non-commercial research under Apache 2.0.",
        },
        "source_references": [
            {
                "title": "Official Portal",
                "url": "https://opendatasets.example.org/portal",
                "type": "official_website",
            },
            {
                "title": "Benchmark Paper",
                "url": "https://doi.org/10.1000/182",
                "type": "original_paper",
            },
        ],
        "verification": {
            "status": "verified",
            "verified_by": "Test Suite",
            "verified_date": "2026-11-15",
            "notes": "Verified against test schema.",
        },
        "sample_count": {
            "status": "verified",
            "total": 1000,
            "unit": "images",
            "splits": {"train": 800, "test": 200},
        },
        "size": {
            "status": "verified",
            "amount": 1.5,
            "unit": "GB",
            "file_formats": ["png", "json"],
        },
        "dates": {
            "published": "2026-01-01",
        },
        "citation": {
            "paper_title": "Synthetic Benchmark for Detection",
            "paper_url": "https://doi.org/10.1000/182",
            "authors": ["Alice Scientist", "Bob Engineer"],
            "doi": "10.1000/182",
            "bibtex": "@article{synthetic2026,\n  title={Synthetic Benchmark for Detection},\n  author={Scientist, Alice and Engineer, Bob},\n  year={2026}\n}",
        },
    }


def test_required_versus_optional_fields(minimal_dataset):
    """Test completeness calculations when optional blocks are omitted."""
    # Complete dataset
    full_comp = calculate_documentation_completeness(minimal_dataset)
    assert full_comp["breakdown"]["core_required_schema"] is True
    assert full_comp["breakdown"]["size_documentation"] is True
    assert full_comp["breakdown"]["citation_paper"] is True

    # Strip optional fields
    stripped = copy.deepcopy(minimal_dataset)
    del stripped["size"]
    del stripped["sample_count"]
    del stripped["citation"]

    stripped_comp = calculate_documentation_completeness(stripped)
    assert stripped_comp["breakdown"]["core_required_schema"] is True
    assert stripped_comp["breakdown"]["size_documentation"] is False
    assert stripped_comp["breakdown"]["sample_count_presence"] is False
    assert stripped_comp["breakdown"]["citation_paper"] is False
    assert stripped_comp["completeness_pct"] < full_comp["completeness_pct"]


def test_unknown_versus_missing_metadata(minimal_dataset):
    """Distinguish metadata explicitly documented as unknown from omitted metadata."""
    # Case 1: sample_count explicitly declared unknown from source
    ds_unknown = copy.deepcopy(minimal_dataset)
    ds_unknown["sample_count"] = {"status": "unknown"}
    comp_unknown = calculate_documentation_completeness(ds_unknown)
    # Status unknown is recognized as documented metadata
    assert comp_unknown["breakdown"]["sample_count_presence"] is True
    assert comp_unknown["breakdown"]["sample_unit_clarity"] is True

    # Case 2: sample_count missing completely
    ds_missing = copy.deepcopy(minimal_dataset)
    del ds_missing["sample_count"]
    comp_missing = calculate_documentation_completeness(ds_missing)
    assert comp_missing["breakdown"]["sample_count_presence"] is False
    assert comp_missing["breakdown"]["sample_unit_clarity"] is False


def test_not_applicable_fields(minimal_dataset):
    """Ensure non-applicable domain fields do not penalize completeness denominator."""
    # Pure vision dataset: languages is not applicable
    assert is_language_applicable(minimal_dataset) is False
    comp_vision = calculate_documentation_completeness(minimal_dataset)
    assert "language_coverage" not in comp_vision["breakdown"]

    # NLP dataset: languages is applicable
    ds_nlp = copy.deepcopy(minimal_dataset)
    ds_nlp["modalities"] = ["nlp"]
    ds_nlp["tasks"] = ["text-classification"]
    assert is_language_applicable(ds_nlp) is True
    comp_nlp = calculate_documentation_completeness(ds_nlp)
    assert "language_coverage" in comp_nlp["breakdown"]

    # Geographic coverage applicable only to remote sensing / geospatial / weather
    assert is_geographic_coverage_applicable(minimal_dataset) is False
    ds_geo = copy.deepcopy(minimal_dataset)
    ds_geo["tags"].append("satellite-imagery")
    assert is_geographic_coverage_applicable(ds_geo) is True


def test_license_classifications(minimal_dataset):
    """Test auditing of various licensing statuses and access requirements."""
    # Verified Open
    res_open = evaluate_licensing_and_access(minimal_dataset)
    assert res_open["status"] == "verified_open"
    assert res_open["commercial_use"] == "allowed"
    assert res_open["access_requirement"] == "open"
    assert res_open["flags"] == []

    # Unspecified by source
    ds_unspec = copy.deepcopy(minimal_dataset)
    ds_unspec["license"] = {
        "status": "unspecified_by_source",
        "name": "Unspecified by Source",
        "commercial_use": "unknown",
        "notes": "No license grant in repository.",
    }
    res_unspec = evaluate_licensing_and_access(ds_unspec)
    assert "license_unspecified_by_source" in res_unspec["flags"]
    assert "commercial_use_unknown" in res_unspec["flags"]

    # Gated with DUA / credentialing requirement
    ds_dua = copy.deepcopy(minimal_dataset)
    ds_dua["license"]["notes"] = "Access requires signed institutional Data Use Agreement (DUA) and credentialing."
    res_dua = evaluate_licensing_and_access(ds_dua)
    assert res_dua["access_requirement"] == "credentialed_or_dua"

    # Custom Permissive with forbidden commercial use
    ds_custom_nc = copy.deepcopy(minimal_dataset)
    ds_custom_nc["license"] = {
        "status": "custom_permissive",
        "name": "Custom Research Terms",
        "commercial_use": "forbidden",
        "notes": "Academic non-commercial research use only.",
    }
    res_custom_nc = evaluate_licensing_and_access(ds_custom_nc)
    assert "custom_permissive_non_commercial" in res_custom_nc["flags"]

    # Discrepancy: verified_non_commercial with unknown commercial_use
    ds_discrepancy = copy.deepcopy(minimal_dataset)
    ds_discrepancy["license"]["status"] = "verified_non_commercial"
    ds_discrepancy["license"]["commercial_use"] = "unknown"
    res_disc = evaluate_licensing_and_access(ds_discrepancy)
    assert "non_commercial_status_with_unforbidden_commercial_use" in res_disc["flags"]


def test_sample_unit_consistency(minimal_dataset):
    """Test detection of vague, missing, or concrete sample units."""
    # Concrete unit: 'images'
    res_valid = evaluate_scientific_consistency(minimal_dataset)
    assert "missing_sample_unit" not in res_valid["flags"]
    assert "vague_sample_unit" not in res_valid["flags"]

    # Vague unit: 'items' or 'samples'
    ds_vague = copy.deepcopy(minimal_dataset)
    ds_vague["sample_count"]["unit"] = "items"
    res_vague = evaluate_scientific_consistency(ds_vague)
    assert "vague_sample_unit" in res_vague["flags"]

    # Missing unit
    ds_missing_unit = copy.deepcopy(minimal_dataset)
    del ds_missing_unit["sample_count"]["unit"]
    res_missing_unit = evaluate_scientific_consistency(ds_missing_unit)
    assert "missing_sample_unit" in res_missing_unit["flags"]


def test_split_arithmetic_consistency(minimal_dataset):
    """Test split partition arithmetic and detection of heterogeneous split structures."""
    # Valid split: 800 + 200 == 1000
    res_valid = evaluate_scientific_consistency(minimal_dataset)
    assert "partition_split_count_mismatch" not in res_valid["flags"]
    assert "heterogeneous_splits_structure" not in res_valid["flags"]

    # Arithmetic mismatch: 800 + 150 != 1000
    ds_mismatch = copy.deepcopy(minimal_dataset)
    ds_mismatch["sample_count"]["splits"] = {"train": 800, "test": 150}
    res_mismatch = evaluate_scientific_consistency(ds_mismatch)
    assert "partition_split_count_mismatch" in res_mismatch["flags"]

    # Heterogeneous split structure: classes mixed with samples
    ds_hetero = copy.deepcopy(minimal_dataset)
    ds_hetero["sample_count"]["splits"] = {"train": 800, "test": 200, "classes": 10}
    res_hetero = evaluate_scientific_consistency(ds_hetero)
    assert "heterogeneous_splits_structure" in res_hetero["flags"]


def test_partition_split_suffix_matching(minimal_dataset):
    """Test that split keys sharing a common unit suffix (e.g. InfographicVQA) sum correctly."""
    ds_suffix = copy.deepcopy(minimal_dataset)
    ds_suffix["sample_count"] = {
        "status": "verified",
        "total": 30035,
        "unit": "questions",
        "splits": {
            "train_questions": 23946,
            "val_questions": 2801,
            "test_questions": 3288,
            "train_images": 4406,
            "val_images": 500,
            "test_images": 579,
            "total_images": 5485,
        },
    }
    res = evaluate_scientific_consistency(ds_suffix)
    # The question partition sums to exactly 30035, so no mismatch flag should be raised
    assert "partition_split_count_mismatch" not in res["flags"]


def test_split_semantic_categories(minimal_dataset):
    """Test differentiation between genuine mismatch, unit mismatch, and multi-task splits."""
    # Unit mismatch: total is labels, splits are clips (AVA Action style)
    ds_unit_mismatch = copy.deepcopy(minimal_dataset)
    ds_unit_mismatch["id"] = "ava-action"
    ds_unit_mismatch["sample_count"] = {
        "status": "verified",
        "total": 1620000,
        "unit": "labels",
        "splits": {"train_clips": 235, "val_clips": 64, "test_clips": 131},
    }
    res_unit = evaluate_scientific_consistency(ds_unit_mismatch)
    assert "split_unit_or_hierarchy_mismatch" in res_unit["flags"]
    assert "partition_split_count_mismatch" not in res_unit["flags"]

    # Unit/version mismatch: PubMed 200k RCT (sentences from 20k subset vs abstracts declared total)
    ds_pubmed = copy.deepcopy(minimal_dataset)
    ds_pubmed["id"] = "pubmed-200k-rct"
    ds_pubmed["sample_count"] = {
        "status": "verified",
        "total": 195654,
        "unit": "abstracts",
        "splits": {"train": 180000, "dev": 28712, "test": 28978},
    }
    res_pubmed = evaluate_scientific_consistency(ds_pubmed)
    assert "split_unit_or_hierarchy_mismatch" in res_pubmed["flags"]
    assert "partition_split_count_mismatch" not in res_pubmed["flags"]

    # Multi-task challenge overlapping splits: ISIC-2018 style
    ds_multitask = copy.deepcopy(minimal_dataset)
    ds_multitask["id"] = "isic-2018"
    ds_multitask["sample_count"] = {
        "status": "verified",
        "total": 12720,
        "unit": "images",
        "splits": {
            "task1_train": 2594,
            "task1_val": 100,
            "task1_test": 1000,
            "task2_train": 2594,
            "task3_train": 10015,
            "task3_val": 193,
            "task3_test": 1512,
        },
    }
    res_multi = evaluate_scientific_consistency(ds_multitask)
    assert "multi_task_or_overlapping_splits" in res_multi["flags"]
    assert "partition_split_count_mismatch" not in res_multi["flags"]

    # Benchmark subset partition: UNSW-NB15 / MS-COCO style
    ds_subset = copy.deepcopy(minimal_dataset)
    ds_subset["id"] = "unsw-nb15"
    ds_subset["sample_count"] = {
        "status": "verified",
        "total": 2540044,
        "unit": "network flows",
        "splits": {"train": 175341, "test": 82332},
    }
    res_sub = evaluate_scientific_consistency(ds_subset)
    assert "benchmark_subset_partition" in res_sub["flags"]
    assert "partition_split_count_mismatch" not in res_sub["flags"]

    # iNaturalist-2021: train + val != total with species non-partition entity
    ds_inat = copy.deepcopy(minimal_dataset)
    ds_inat["id"] = "inaturalist-2021"
    ds_inat["sample_count"] = {
        "status": "verified",
        "total": 2729500,
        "unit": "images",
        "splits": {"train": 2686843, "val": 100000, "species": 10000},
    }
    res_inat = evaluate_scientific_consistency(ds_inat)
    assert "partition_split_count_mismatch" in res_inat["flags"]
    assert "heterogeneous_splits_structure" in res_inat["flags"]


def test_deterministic_report_ordering(minimal_dataset):
    """Ensure report dataset entries are deterministically sorted by stable ID."""
    ds_a = copy.deepcopy(minimal_dataset)
    ds_a["id"] = "dataset-alpha"
    ds_b = copy.deepcopy(minimal_dataset)
    ds_b["id"] = "dataset-beta"
    ds_c = copy.deepcopy(minimal_dataset)
    ds_c["id"] = "dataset-gamma"

    # Input in reverse order
    res_rev = audit_catalog_metadata_quality([ds_c, ds_a, ds_b])
    ids_rev = [d["id"] for d in res_rev["datasets"]]
    assert ids_rev == ["dataset-alpha", "dataset-beta", "dataset-gamma"]

    # Input in shuffled order
    res_shuf = audit_catalog_metadata_quality([ds_b, ds_c, ds_a])
    ids_shuf = [d["id"] for d in res_shuf["datasets"]]
    assert ids_shuf == ["dataset-alpha", "dataset-beta", "dataset-gamma"]


def test_duplicate_source_references(minimal_dataset):
    """Test detection of duplicate source reference URLs in a single record."""
    # Duplicate URL in source_references
    ds_dup = copy.deepcopy(minimal_dataset)
    ds_dup["source_references"].append({
        "title": "Redundant Entry",
        "url": "https://opendatasets.example.org/portal",
        "type": "official_website",
    })
    res_dup = evaluate_scientific_consistency(ds_dup)
    assert "duplicate_source_reference_urls" in res_dup["flags"]


def test_incorrect_metadata_types_and_citations(minimal_dataset):
    """Test handling of malformed DOIs, unbalanced BibTeX, and modality mismatches."""
    # Malformed DOI (URL prefix included or invalid pattern)
    ds_doi_url = copy.deepcopy(minimal_dataset)
    ds_doi_url["citation"]["doi"] = "https://doi.org/10.1000/182"
    res_doi_url = evaluate_scientific_consistency(ds_doi_url)
    assert "citation_doi_has_url_prefix" in res_doi_url["flags"]

    ds_doi_bad = copy.deepcopy(minimal_dataset)
    ds_doi_bad["citation"]["doi"] = "invalid-doi-123"
    res_doi_bad = evaluate_scientific_consistency(ds_doi_bad)
    assert "citation_doi_format_mismatch" in res_doi_bad["flags"]

    # Unbalanced BibTeX braces
    ds_bib_unbalanced = copy.deepcopy(minimal_dataset)
    ds_bib_unbalanced["citation"]["bibtex"] = "@article{bad, title={Missing closing brace"
    res_bib = evaluate_scientific_consistency(ds_bib_unbalanced)
    assert "citation_bibtex_unbalanced_braces" in res_bib["flags"]

    # Task without matching modality
    ds_audio_mismatch = copy.deepcopy(minimal_dataset)
    ds_audio_mismatch["modalities"] = ["tabular"]
    ds_audio_mismatch["tasks"] = ["speech-recognition"]
    res_mod_mismatch = evaluate_scientific_consistency(ds_audio_mismatch)
    assert "audio_task_without_audio_modality" in res_mod_mismatch["flags"]


def test_incomplete_citations_and_authoritative_sources(minimal_dataset):
    """Test citation readiness tiers and authoritative non-academic exception handling."""
    comp = calculate_documentation_completeness(minimal_dataset)
    lic = evaluate_licensing_and_access(minimal_dataset)
    cons = evaluate_scientific_consistency(minimal_dataset)

    # Complete academic citation -> High
    res_high = evaluate_research_readiness(minimal_dataset, comp, lic, cons)
    assert res_high["dimensions"]["citation_completeness"] == "High"

    # Missing citation on academic dataset -> Missing
    ds_missing_cit = copy.deepcopy(minimal_dataset)
    del ds_missing_cit["citation"]
    res_missing = evaluate_research_readiness(ds_missing_cit, comp, lic, cons)
    assert res_missing["dimensions"]["citation_completeness"] == "Missing"

    # Authoritative government climate dataset without citation -> Authoritative_Non_Academic
    ds_gov = copy.deepcopy(minimal_dataset)
    del ds_gov["citation"]
    ds_gov["publisher"]["type"] = "government"
    ds_gov["tags"].append("climate")
    res_gov = evaluate_research_readiness(ds_gov, comp, lic, cons)
    assert res_gov["dimensions"]["citation_completeness"] == "Authoritative_Non_Academic"


def test_category_level_aggregation(minimal_dataset):
    """Test multi-category mapping and category-level completeness aggregation."""
    # Benchmark + Computer Vision
    cats = derive_dataset_categories(minimal_dataset)
    assert "computer-vision" in cats
    assert "evaluation-benchmarks" in cats

    audit_res = audit_catalog_metadata_quality([minimal_dataset])
    cat_summaries = audit_res["category_summaries"]
    assert cat_summaries["computer-vision"]["total_datasets"] == 1
    assert cat_summaries["evaluation-benchmarks"]["total_datasets"] == 1
    assert cat_summaries["natural-language-processing"]["total_datasets"] == 0


def test_no_scientific_quality_claims_from_completeness_metrics(minimal_dataset):
    """Verify that audit explicitly disclaims scientific quality from documentation metrics."""
    audit_res = audit_catalog_metadata_quality([minimal_dataset])
    formula_note = audit_res["audit_metadata"]["completeness_formula"]
    assert "documentation coverage only" in formula_note
    assert "not scientific quality" in formula_note

    # Readiness tiers must be descriptive strings, not numeric scores
    readiness = evaluate_research_readiness(
        minimal_dataset,
        calculate_documentation_completeness(minimal_dataset),
        evaluate_licensing_and_access(minimal_dataset),
        evaluate_scientific_consistency(minimal_dataset),
    )
    tier = readiness["readiness_tier"]
    assert isinstance(tier, str)
    assert tier in ("Ready for Evaluation", "Documented with Caveats", "Needs Information Review")


def test_multi_category_accounting():
    """Verify category totals and handling of multi-category vs zero-category datasets."""
    # Synthetic dataset with no matching modality or benchmark tag
    ds_sensor = {
        "schema_version": "1.0.0",
        "id": "sensor-only",
        "slug": "sensor-only",
        "name": "Sensor Only",
        "description": "Pure sensor telemetry.",
        "homepage_url": "https://example.org",
        "publisher": {"name": "Lab", "type": "academic"},
        "modalities": ["sensor"],
        "tasks": ["signal-processing"],
        "tags": ["sensor", "signals"],
        "license": {"status": "verified_open", "name": "MIT"},
        "source_references": [{"title": "Ref", "url": "https://example.org", "type": "official_website"}],
        "verification": {"status": "verified"},
    }
    cats = derive_dataset_categories(ds_sensor)
    assert cats == []  # Handled as unclassified / all-categories

    # Dataset with 2 categories
    ds_nlp_bench = copy.deepcopy(ds_sensor)
    ds_nlp_bench["modalities"] = ["nlp"]
    ds_nlp_bench["tags"].append("benchmark")
    cats_2 = derive_dataset_categories(ds_nlp_bench)
    assert set(cats_2) == {"natural-language-processing", "evaluation-benchmarks"}


def test_report_compactness(minimal_dataset):
    """Verify that generated audit results stay compact and avoid redundant bloat."""
    import json
    res = audit_catalog_metadata_quality([minimal_dataset] * 10)
    raw_json = json.dumps(res, indent=2)
    # 10 records must be small (< 25 KB)
    assert len(raw_json.encode("utf-8")) < 25 * 1024


def test_catalog_split_discrepancy_census():
    """Verify exact census and mutual exclusivity of the 17 non-matching partition datasets."""
    import json
    from pathlib import Path

    catalog_dir = Path("data/datasets")
    records = [json.loads(p.read_text()) for p in sorted(catalog_dir.glob("*.json"))]
    assert len(records) == 700

    cat_a = []  # partition_split_count_mismatch
    cat_b = []  # benchmark_subset_partition
    cat_c = []  # multi_task_or_overlapping_splits
    cat_d = []  # split_unit_or_hierarchy_mismatch

    for r in records:
        did = r["id"]
        res = evaluate_scientific_consistency(r)
        flags = res["flags"]
        if "partition_split_count_mismatch" in flags:
            cat_a.append(did)
        if "benchmark_subset_partition" in flags:
            cat_b.append(did)
        if "multi_task_or_overlapping_splits" in flags:
            cat_c.append(did)
        if "split_unit_or_hierarchy_mismatch" in flags:
            cat_d.append(did)

    # 1. Exact counts
    assert len(cat_a) == 11, f"Expected 11 Category A datasets, got {len(cat_a)}: {cat_a}"
    assert len(cat_b) == 2, f"Expected 2 Category B datasets, got {len(cat_b)}: {cat_b}"
    assert len(cat_c) == 2, f"Expected 2 Category C datasets, got {len(cat_c)}: {cat_c}"
    assert len(cat_d) == 2, f"Expected 2 Category D datasets, got {len(cat_d)}: {cat_d}"
    assert len(cat_a) + len(cat_b) + len(cat_c) + len(cat_d) == 17

    # 2. Exact membership
    expected_a = [
        "chexpert", "doclaynet", "fgvc-aircraft", "hotpotqa", "inaturalist-2021",
        "medmcqa", "mura", "pascal-voc", "quac", "sroie", "whu-building"
    ]
    assert sorted(cat_a) == sorted(expected_a)
    assert sorted(cat_b) == ["ms-coco", "unsw-nb15"]
    assert sorted(cat_c) == ["isic-2018", "waymo-open-perception"]
    assert sorted(cat_d) == ["ava-action", "pubmed-200k-rct"]

    # 3. Pairwise disjoint (mutually exclusive)
    sets = [set(cat_a), set(cat_b), set(cat_c), set(cat_d)]
    for i in range(len(sets)):
        for j in range(i + 1, len(sets)):
            assert sets[i].isdisjoint(sets[j]), f"Overlap found between categories: {sets[i] & sets[j]}"


def test_unverified_partition_split_claims():
    """Verify that no speculative claims exist in generated markdown summary for partition splits."""
    from scripts.audit_metadata_quality import generate_markdown_summary, audit_catalog_metadata_quality
    import json
    from pathlib import Path

    catalog_dir = Path("data/datasets")
    records = [json.loads(p.read_text()) for p in sorted(catalog_dir.glob("*.json"))]
    audit_data = audit_catalog_metadata_quality(records)
    md = generate_markdown_summary(audit_data)

    # Speculative claims that must NOT appear
    prohibited_claims = [
        "single boundary tile excluded",
        "10 duplicate annotations",
        "200 rare aircraft variant",
        "1,100 withheld test questions",
        "13 unreadable receipts",
        "low-quality/redundant pages",
        "radiograph vs study count discrepancy",
    ]
    for claim in prohibited_claims:
        assert claim not in md, f"Prohibited speculative claim found in summary: '{claim}'"

    # All 11 Category A candidates must be explicitly noted as Unverified
    category_a_datasets = [
        "chexpert", "doclaynet", "fgvc-aircraft", "hotpotqa", "inaturalist-2021",
        "medmcqa", "mura", "pascal-voc", "quac", "sroie", "whu-building"
    ]
    for did in category_a_datasets:
        assert f"`{did}`:" in md, f"Dataset `{did}` missing from Category A breakdown"
        # Extract line for dataset
        for line in md.splitlines():
            if f"`{did}`:" in line:
                assert "Unverified" in line, f"Line for `{did}` must mark discrepancy as Unverified: {line}"


def test_duplicate_reference_semantics():
    """Verify duplicate reference handling and Iris Fisher (1936) citation semantics."""
    import json
    from pathlib import Path

    catalog_dir = Path("data/datasets")
    dup_ids = ["cebs-database", "fmow", "mit-bih-atrial-fibrillation", "mit-bih-noise-stress-test"]
    
    for did in dup_ids:
        p = catalog_dir / f"{did}.json"
        assert p.exists()
        d = json.loads(p.read_text())
        res = evaluate_scientific_consistency(d)
        assert "duplicate_source_reference_urls" in res["flags"], f"{did} should be flagged for duplicate URL reuse"

    # Iris has distinct dataset and original-paper URLs after Task 41 correction.
    iris_data = json.loads((catalog_dir / "iris.json").read_text())
    iris_flags = evaluate_scientific_consistency(iris_data)["flags"]
    assert "duplicate_source_reference_urls" not in iris_flags
    assert iris_data["citation"]["paper_title"] == "The Use of Multiple Measurements in Taxonomic Problems"
    assert "R. A. Fisher" in iris_data["citation"]["authors"]
    assert iris_data["citation"]["doi"] == "10.1111/j.1469-1809.1936.tb02137.x"
    assert iris_data["citation"]["paper_url"] == "https://doi.org/10.1111/j.1469-1809.1936.tb02137.x"
    # Source references retain the UCI repository URL
    urls = [r["url"] for r in iris_data["source_references"]]
    assert urls == ["https://archive.ics.uci.edu/dataset/53/iris", "https://doi.org/10.1111/j.1469-1809.1936.tb02137.x"]


def test_readiness_tier_counts_reconciliation():
    """Verify that catalog-wide readiness tiers sum to exactly 700 records."""
    import json
    from pathlib import Path

    catalog_dir = Path("data/datasets")
    records = [json.loads(p.read_text()) for p in sorted(catalog_dir.glob("*.json"))]
    audit_data = audit_catalog_metadata_quality(records)
    tier_dist = audit_data["research_readiness_summary"]["tier_distribution"]

    assert tier_dist["Ready for Evaluation"] == 484
    assert tier_dist["Documented with Caveats"] == 171
    assert tier_dist["Needs Information Review"] == 45
    assert sum(tier_dist.values()) == 700


def test_audit_metadata_quality_provenance_and_dynamic_counts():
    """Verify custom task provenance, dynamic licensing counts, and non-contradictory dates coverage."""
    import json
    from pathlib import Path

    catalog_dir = Path("data/datasets")
    records = [json.loads(p.read_text()) for p in sorted(catalog_dir.glob("*.json"))]

    audit_task = "Task 49 — 700-Record Metadata Quality Audit"
    audit_date = "2026-11-20"
    audit_data = audit_catalog_metadata_quality(
        records,
        audit_task=audit_task,
        audit_date=audit_date,
    )

    meta = audit_data["audit_metadata"]
    assert meta["audit_task"] == audit_task
    assert meta["audit_date"] == audit_date

    md = generate_markdown_summary(audit_data)
    assert f"> **Audit Task:** {audit_task}" in md
    assert f"> **Audit Date:** {audit_date}" in md
    assert "Complete across all 700 catalog records" not in md
    assert "Documented across 675/700 catalog records (25 undated)" in md
    assert f"modified during {audit_task}" in md
    assert "modified during Task 40" not in md



