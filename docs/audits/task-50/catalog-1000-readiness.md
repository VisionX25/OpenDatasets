# OpenDatasets 1,000-Dataset Readiness & Strategic Expansion Plan

> **Audit Task:** Task 50 — Catalog Quality Baseline, Duplicate Prevention & 1,000-Dataset Readiness<br>
> **Audit Date:** 2026-11-21<br>
> **Current Catalog Baseline:** Exactly 700 unique, schema-valid research dataset metadata records<br>
> **Expansion Target:** 1,000 unique datasets (+300 net new datasets across 12 structured batches)

---

## 1. Executive Summary & Foundation Baseline

The OpenDatasets repository has reached a stable milestone of **700 unique, scientifically verified dataset metadata records** across six core machine learning domains. Before embarking on the roadmap expansion to 1,000 datasets, Task 50 establishes an exhaustive quality baseline, audits all pairwise relationships, strengthens deterministic duplicate prevention in CI, and defines a disciplined intake strategy.

### Baseline Health Metrics
- **Total Validated Records:** Exactly 700 JSON files under `data/datasets/`.
- **Duplicate IDs & Slugs:** 0 duplicate IDs; 0 duplicate slugs.
- **Duplicate Normalized Names:** 0 duplicate lowercase alphanumeric dataset names.
- **High-Confidence Duplicates:** 0 confirmed redundant or copy-paste dataset records.
- **Schema Compliance:** 100% adherence to `schemas/dataset.v1.schema.json`.
- **Core Documentation Completeness:** Average of 79.8% across applicable attributes.
- **Research Readiness Tiers:**
  - *Ready for Evaluation:* 484 datasets (69.1%)
  - *Documented with Caveats:* 171 datasets (24.4%)
  - *Needs Information Review:* 45 datasets (6.4%) (34 unspecified licenses + 11 unverified partition split deltas)

---

## 2. Technical Architecture Readiness for 1,000 Datasets

The repository infrastructure was evaluated for operational performance and algorithmic scaling as the catalog expands from 700 to 1,000+ datasets:

### A. Metadata Validation Performance
- **Deterministic Check Execution:** `scripts/validate_datasets.py` performs full Draft-7 schema validation, deep URL syntax checks, and cross-dataset duplicate checks (IDs, slugs, normalized names, shared DOI/URL collisions) in **0.08 seconds** for 700 records.
- **Scaling Projection:** Empirical profiling indicates that cross-dataset duplicate detection for 1,000 records requires **0.035 seconds**, and full validation requires under **0.15 seconds**, presenting zero risk of CI bottlenecks.

### B. Catalog Compilation & Frontend Prebuild
- **Compilation Speed:** `scripts/generate_catalog.py` compiles all 700 JSON records into `frontend/public/data/catalog.json` in **0.12 seconds**.
- **Bundle & Memory Footprint:** The generated `catalog.json` is approximately 750 KB uncompressed (~160 KB gzipped). At 1,000 records, the bundle will remain well below 1.1 MB uncompressed (~230 KB gzipped), loading virtually instantaneously in modern web browsers.
- **Client-Side Discovery Engine:** The frontend search and multi-facet filtering engine (`frontend/src/utils/datasetFilters.ts`) executes instantaneous in-memory searches in under **2 milliseconds**, scaling seamlessly beyond 5,000 records without requiring external search backends.

---

## 3. Strategic Domain Expansion Plan (+300 Datasets)

To reach the 1,000-dataset milestone with high scientific utility and diversity, additions must be balanced across modalities and domains, avoiding over-indexing on well-known standard computer vision benchmarks while prioritizing underrepresented languages and regional scientific challenges:

| Research Domain | Current Count | Target Additions | Target Total | Strategic Priority Areas |
| :--- | :---: | :---: | :---: | :--- |
| **Computer Vision** | 373 | **+65** | 438 | 3D point cloud perception, surgical & endoscopic vision, fine-grained agricultural disease classification, UAV surveillance, industrial anomaly detection |
| **Natural Language Processing** | 168 | **+65** | 233 | Underrepresented South Asian and African languages, dialectal NLP, mathematical & legal reasoning, instruction tuning, clinical dialogue summarization |
| **Tabular & Time-Series** | 191 | **+50** | 241 | Renewable energy forecasting (solar/wind), industrial IoT telemetry, climate & environmental monitoring, financial risk & fraud benchmarks |
| **Evaluation & Benchmarks** | 292 | **+45** | 337 | LLM safety & alignment, agentic code execution, hallucination detection, adversarial robustness, multi-turn tool-calling benchmarks |
| **Audio & Speech** | 53 | **+40** | 93 | Low-resource speech recognition (ASR), multi-speaker bioacoustics, environmental acoustic scene classification, audio-visual speech separation |
| **Multimodal & Generative** | 98 | **+35** | 133 | Embodied robotics manipulation, document visual question answering (DocVQA), multi-sensor autonomous platforms, vision-language grounding |
| **Total Catalog** | **700** | **+300** | **1,000** | Balanced, peer-reviewed, reproducible academic research foundation |

### Special Focus: Underrepresented South Asian & Bangla Research Datasets
Special attention must be given to academically verified datasets from Bangladesh and South Asian research institutions (e.g. Independent University, Bangladesh; BUET; University of Dhaka; Mendeley Data; Zenodo):
- Dialectal Bangla speech and sentiment corpora (Chittagonian, Sylheti, Noakhali, Rangpuri).
- Subcontinental medical imaging (oral cancer screening, regional clinical records, rural telehealth diagnostics).
- South Asian agricultural phenotyping (rice disease classification, jute pest detection, regional weather station networks).

---

## 4. Disciplined Batch-Based Intake Workflow

To maintain rigorous peer-review and avoid regressions, additions must proceed in **12 distinct batches of exactly 25 datasets per Pull Request**:

```
Current Baseline: 700 datasets (PR #46 / Task 50)
  ├── Batch 51: Datasets 701–725 (Multilingual & Regional NLP)
  ├── Batch 52: Datasets 726–750 (Computer Vision: 3D & Autonomous Perception)
  ├── Batch 53: Datasets 751–775 (Audio & Speech AI)
  ├── Batch 54: Datasets 776–800 (Tabular & Environmental Time-Series)
  ├── Batch 55: Datasets 801–825 (Multimodal & Embodied Robotics)
  ├── Batch 56: Datasets 826–850 (LLM Evaluation, Safety & Alignment)
  ├── Batch 57: Datasets 851–875 (Medical Imaging & Healthcare Diagnostics)
  ├── Batch 58: Datasets 876–900 (South Asian & Bangla Research Datasets)
  ├── Batch 59: Datasets 901–925 (Fine-Grained Agricultural & Environmental AI)
  ├── Batch 60: Datasets 926–950 (Graph Learning & Scientific Machine Learning)
  ├── Batch 61: Datasets 951–975 (Audio-Visual & Multi-Sensor AI)
  └── Batch 62: Datasets 976–1,000 (1,000-Dataset Milestone Celebration & Capstone Audit)
```

---

## 5. Duplicate Prevention & Intake Quality Gate

Each proposed dataset record in incoming PRs must pass a mandatory four-tier quality gate prior to merging:

### Gate 1: Automated Hard-Failure Checks (CI)
Implemented in `scripts/validate_datasets.py`:
1. **Unique ID & Slug:** No collision with any existing dataset ID or slug.
2. **Normalized Name Uniqueness:** Alphanumeric lowercase normalization (`re.sub(r"[^\w]", "", name.lower())`) must not match any existing record. Prevents reintroduction under trivial punctuation or case variations (e.g., "CIFAR 10" vs "CIFAR-10").
3. **Exact Identity Matching:** Rejection if an incoming dataset shares an exact canonical homepage or publication DOI with an existing record and lacks distinguishing tokens (e.g., version numbers, class counts, modality qualifiers).

### Gate 2: Automated Maintainer Review Warnings (Advisory)
1. **Shared Foundational Publication / Portal:** Datasets legitimately sharing a publication (e.g., benchmark suite introduction papers like OGB, WorldCereal, Argoverse 2) emit an advisory warning in CI logs and review summaries, prompting maintainer confirmation of distinct tasks.
2. **High Lexical Similarity:** Datasets with fuzzy title similarity > 0.85 (e.g., consecutive challenge years) are flagged for version progression documentation.

### Gate 3: Minimum Evidence Requirements
Every new record must supply:
1. **Authoritative Primary Source:** Direct link to official publisher portal, institutional repository, or verified code repository (GitHub, Zenodo, Hugging Face, Kaggle, Figshare, Mendeley Data).
2. **Transparent Licensing:** Explicit SPDX identifier or documented custom license terms. If terms are not formally published, status must be explicitly recorded as `unspecified_by_source` with commercial use `unknown` or `forbidden`.
3. **Sample Unit & Scale:** Concrete unit of observation (e.g. `images`, `audio-recordings`, `sentences`, `patients`, `point-clouds`) with verified counts or explicit `status: unknown`.
4. **Structured Citation:** Canonical publication title, authors, venue/year, and DOI (where published).

### Gate 4: Zero Automatic Deletions & Audit Traceability
- Community suggestions and pull requests must never automatically delete, overwrite, or deprecate existing datasets without maintainer confirmation.
- Each addition batch must run catalog regeneration, complete unit tests, frontend builds, and update audit reports.
