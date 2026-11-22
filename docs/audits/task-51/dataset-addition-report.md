# OpenDatasets Catalog Expansion Audit Report — Task 51 (700 → 725 Datasets)

> **Audit Task:** Task 51 — Add 25 Verified Research Datasets to OpenDatasets  
> **Date:** 2026-11-22  
> **Auditor:** OpenDatasets Core Team / Senior Dataset Curator & Repository Auditor  
> **Repository:** [VisionX25/OpenDatasets](https://github.com/VisionX25/OpenDatasets)  
> **Baseline Commit:** `930a780216c072d0864873a3ce45efe0c35162a8`  
> **Target Branch:** `feat/task-51-add-25-research-datasets`  

---

## 1. Executive Summary

This report documents the rigorous curation, duplicate auditing, schema validation, and catalog synchronization for **Task 51**, expanding the OpenDatasets repository from **700 to 725 verified research datasets**.

This milestone advances the catalog to **72.5% of its long-term milestone target of 1,000 unique machine learning datasets**. All 25 new entries were curated across 5 high-impact domains, verified against canonical peer-reviewed publications and primary repositories, and audited to guarantee zero duplicate records, full schema conformity, and complete scientific integrity.

### Catalog Growth Highlights

| Metric | Pre-Task Baseline | Post-Task Status | Change |
| :--- | :--- | :--- | :--- |
| **Total Catalog Datasets** | 700 records | **725 records** | **+25 records (+3.57%)** |
| **Milestone Progress (Target: 1,000)** | 70.0% | **72.5%** | **+2.5%** |
| **Schema Validation (v1.0.0)** | 700 / 700 (100%) | **725 / 725 (100%)** | **0 errors** |
| **Python Test Suite (Pytest)** | 216 passed | **216 passed** | **100% green** |
| **Frontend Test Suite (Vitest)** | 252 passed | **252 passed** | **100% green** |
| **Frontend Linter (ESLint)** | 0 warnings / errors | **0 warnings / errors** | **Clean** |
| **Production Web Build (Vite)** | Successful | **Successful (725 records)** | **Clean** |
| **Semantic High-Confidence Duplicates** | 0 pairs | **0 pairs (across 262,450 pairs)** | **0 duplicates** |

---

## 2. Domain & Modality Breakdown of Additions

The 25 datasets added in Task 51 were selected across 5 major domains:

```mermaid
flowchart TD
    subgraph "Task 51: 25 Research Dataset Additions"
        NLP["<b>Natural Language Processing (5)</b><br/>samanantar, dakshina, indicglue, indiccorp, bpcc"]
        CV["<b>Computer Vision (5)</b><br/>domainnet, dior, vizwiz-vqa, ai2d, coco-wholebody"]
        Audio["<b>Audio & Speech (5)</b><br/>multilingual-librispeech, hi-fi-tts, spgispeech, aishell-1, meld"]
        Tabular["<b>Tabular & Time-Series (5)</b><br/>pems-bay, uea-multivariate-time-series, appliances-energy-prediction, pems04, pems08"]
        Eval["<b>AI Evaluation & Benchmarks (5)</b><br/>gpqa, mmlu-pro, big-bench, mbpp, arc-agi-1"]
    end
```

### Categorical Distribution
1. **Natural Language Processing (5 datasets):** Focuses on low-resource and South Asian language infrastructure (Indic parallel corpora, transliteration, monolingual web scale, and evaluation suites).
2. **Computer Vision (5 datasets):** High-diversity multi-source domain adaptation, aerial remote sensing object detection, assistive visual question answering, science diagram parse graphs, and whole-body 133-keypoint human pose estimation.
3. **Audio & Speech Recognition (5 datasets):** 50,000-hour multilingual speech recognition, 44.1 kHz studio-quality multi-speaker TTS, 5,000-hour financial earnings call ASR, open Mandarin ASR, and multimodal conversational emotion dialogue.
4. **Tabular & Spatial-Temporal Time-Series (5 datasets):** California highway traffic sensor matrices (PeMS District 4 and District 8), multivariate time series classification archive, and IoT smart-home energy prediction telemetry.
5. **AI Evaluation & Reasoning Benchmarks (5 datasets):** Frontier LLM evaluation including graduate-level Google-proof reasoning (GPQA), 10-option multi-task reasoning (MMLU-Pro), 204-task collaborative suite (BIG-bench), Python code generation (MBPP), and visual ARC-AGI grid transformation.

---

## 3. Comprehensive Dataset Inventory

| # | Dataset ID | Official Name | Domain / Modalities | Publisher & Type | License Status & Commercial Terms | Total Samples & Unit | Canonical Citation / Primary Source | Size |
|---|---|---|---|---|---|---|---|---|
| **01** | `samanantar` | Samanantar: Indic Parallel Corpora Collection | NLP (`nlp`) | AI4Bharat (academic) | `verified_non_commercial` (CC BY-NC 4.0, forbidden) | 49,709,336 sentence-pairs | Ramesh et al., TACL 2022 (doi:10.1162/tacl_a_00452) | 12.5 GB |
| **02** | `dakshina` | Dakshina: South Asian Language Latin & Native Script Benchmark | NLP (`nlp`) | Google Research (industry) | `custom_permissive` (CC BY-SA 4.0, allowed) | ~1,200,000 strings-and-sentences | Roark et al., LREC 2020 (doi:10.18653/v1/2020.lrec-1.294) | 1.8 GB |
| **03** | `indicglue` | IndicGLUE: Indian Language Natural Language Understanding Benchmark | NLP (`nlp`) | AI4Bharat (academic) | `custom_permissive` (Academic Research / MIT, unknown) | ~320,000 examples | Kakwani et al., Findings of EMNLP 2020 (doi:10.18653/v1/2020.findings-emnlp.445) | 450 MB |
| **04** | `indiccorp` | IndicCorp v2: Large-Scale Monolingual Corpora for Indic Languages | NLP (`nlp`) | AI4Bharat (academic) | `public_domain` (CC0 1.0 Universal, allowed) | ~1,092,000,000 sentences (~20.9B tokens) | Doddapaneni et al., ACL 2023 (doi:10.18653/v1/2023.acl-long.693) | 275.0 GB |
| **05** | `bpcc` | Bharat Parallel Corpus Collection (BPCC) | NLP (`nlp`) | AI4Bharat (academic) | `custom_permissive` (CC BY 4.0 human / CC0 mined, allowed) | ~230,000,000 sentence-pairs | Gala et al., TMLR 2023 (arXiv:2305.16307) | 42.0 GB |
| **06** | `domainnet` | DomainNet: Multi-Source Domain Adaptation Benchmark | Vision (`vision`) | Boston University (academic) | `custom_permissive` (Non-Commercial Research, forbidden) | 586,575 images | Peng et al., ICCV 2019 (doi:10.1109/ICCV.2019.00149) | 34.0 GB |
| **07** | `dior` | DIOR: Object Detection in Optical Remote Sensing Images | Vision (`vision`) | Northwestern Polytechnical Univ. (academic) | `verified_non_commercial` (CC BY-NC 4.0, forbidden) | 23,463 images (192,472 instances) | Li et al., ISPRS 2020 (doi:10.1016/j.isprsjprs.2019.11.023) | 7.3 GB |
| **08** | `vizwiz-vqa` | VizWiz-VQA: Visual Question Answering from Blind Photographers | Multimodal (`vision`, `nlp`, `multimodal`) | VizWiz Consortium (academic) | `verified_open` (CC BY 4.0, allowed) | 32,842 visual-questions | Gurari et al., CVPR 2018 (doi:10.1109/CVPR.2018.00380) | 10.5 GB |
| **09** | `ai2d` | AI2D: Allen Institute for AI Diagram Dataset | Multimodal (`vision`, `nlp`, `multimodal`) | Allen Institute for AI (academic) | `custom_permissive` (CC BY-SA 4.0, allowed) | 4,914 diagrams (15,000+ MC questions) | Kembhavi et al., ECCV 2016 (doi:10.1007/978-3-319-46484-8_29) | 1.2 GB |
| **10** | `coco-wholebody` | COCO-WholeBody: Whole-Body Human Pose Estimation Benchmark | Vision (`vision`) | SenseTime & CUHK (academic) | `custom_permissive` (CC BY 4.0 annotations / SenseTime NC restriction, unknown) | ~250,000 person-instances (133 keypoints) | Jin et al., ECCV 2020 (arXiv:2007.11858) | 1.1 GB |
| **11** | `multilingual-librispeech` | Multilingual LibriSpeech (MLS) | Audio (`audio`) | Facebook AI Research (industry) | `verified_open` (CC BY 4.0, allowed) | ~50,000 audio-hours (8 languages) | Pratap et al., Interspeech 2020 (doi:10.21437/Interspeech.2020-2826) | 280.0 GB |
| **12** | `hi-fi-tts` | Hi-Fi TTS: High-Fidelity Multi-Speaker English Speech Synthesis | Audio (`audio`) | NVIDIA (industry) | `verified_open` (CC BY 4.0, allowed) | ~116,000 audio-utterances (291.6 hours) | Bakhturina et al., Interspeech 2021 (doi:10.21437/Interspeech.2021-1599) | 29.5 GB |
| **13** | `spgispeech` | SPGISpeech: Financial-Domain Speech Recognition Corpus | Audio (`audio`) | Kensho Technologies (industry) | `custom_permissive` (Kensho Academic Agreement, forbidden) | 5,000 audio-hours | O'Neill et al., Interspeech 2021 (doi:10.21437/Interspeech.2021-1860) | 250.0 GB |
| **14** | `aishell-1` | AISHELL-1: Open-Source Mandarin Speech Corpus | Audio (`audio`) | Beijing Shell Shell Tech (industry) | `verified_open` (Apache-2.0, allowed) | 141,600 audio-utterances (178 hours) | Bu et al., O-COCOSDA 2017 (doi:10.1109/icsda.2017.8384449) | 15.0 GB |
| **15** | `meld` | MELD: Multimodal EmotionLines Dataset | Multimodal (`multimodal`, `vision`, `audio`, `nlp`) | Nanyang Technological Univ. (academic) | `custom_permissive` (Research Use Agreement, forbidden) | 13,708 utterances | Poria et al., ACL 2019 (doi:10.18653/v1/P19-1050) | 9.8 GB |
| **16** | `pems-bay` | PEMS-BAY: California Bay Area Highway Traffic Speed Benchmark | Tabular / Time-Series (`tabular`, `time-series`, `sensor`) | USC / Caltrans (academic) | `custom_permissive` (MIT Code / Caltrans PeMS Open Data, unknown) | 16,934,400 readings (325 sensors, 6 months) | Li et al., ICLR 2018 (arXiv:1707.01926) | 28.0 MB |
| **17** | `uea-multivariate-time-series` | UEA Multivariate Time Series Classification Archive (2018) | Tabular / Time-Series (`tabular`, `time-series`) | Univ. of East Anglia (academic) | `verified_open` (CC BY 4.0 / Public Domain, allowed) | 30 datasets | Bagnall et al., 2018 (arXiv:1811.00075) | 2.5 GB |
| **18** | `appliances-energy-prediction` | Appliances Energy Prediction Dataset | Tabular / Time-Series (`tabular`, `time-series`, `sensor`) | UCI Machine Learning Lab (academic) | `verified_open` (CC BY 4.0, allowed) | 19,735 records (10-min intervals) | Candanedo et al., Energy & Buildings 2017 (doi:10.1016/j.enbuild.2017.01.083) | 3.2 MB |
| **19** | `pems04` | PEMS04: Caltrans District 4 Spatial-Temporal Highway Traffic Flow | Tabular / Time-Series (`tabular`, `time-series`, `sensor`) | Beijing Jiaotong Univ. / Caltrans (academic) | `custom_permissive` (Caltrans PeMS Open Data, unknown) | 5,216,544 readings (307 detectors) | Guo et al., AAAI 2019 (doi:10.1609/aaai.v33i01.3301922) | 21.0 MB |
| **20** | `pems08` | PEMS08: Caltrans District 8 Spatial-Temporal Highway Traffic Flow | Tabular / Time-Series (`tabular`, `time-series`, `sensor`) | Beijing Jiaotong Univ. / Caltrans (academic) | `custom_permissive` (Caltrans PeMS Open Data, unknown) | 3,035,520 readings (170 detectors) | Guo et al., AAAI 2019 (doi:10.1609/aaai.v33i01.3301922) | 12.0 MB |
| **21** | `gpqa` | GPQA: A Graduate-Level Google-Proof Q&A Benchmark | NLP (`nlp`) | NYU & Anthropic (academic) | `verified_open` (CC BY 4.0, allowed) | 448 questions | Rein et al., COLM 2024 (OpenReview) | 2.4 MB |
| **22** | `mmlu-pro` | MMLU-Pro: Massive Multitask Language Understanding Pro | NLP (`nlp`) | TIGER AI Lab (academic) | `verified_open` (Apache-2.0, allowed) | 12,032 questions (10 options each) | Wang et al., NeurIPS 2024 (arXiv:2406.01574) | 25.0 MB |
| **23** | `big-bench` | BIG-bench: Beyond the Imitation Game Benchmark Suite | NLP (`nlp`) | Google Research & Consortium (industry) | `verified_open` (Apache-2.0, allowed) | 204 tasks | Srivastava et al., TMLR 2023 (arXiv:2206.04615) | 2.1 GB |
| **24** | `mbpp` | MBPP: Mostly Basic Python Problems | NLP (`nlp`) | Google Research (industry) | `verified_open` (CC BY 4.0, allowed) | 974 programming-problems | Austin et al., 2021 (arXiv:2108.07732) | 2.2 MB |
| **25** | `arc-agi-1` | ARC-AGI-1: Abstraction and Reasoning Corpus | Multimodal (`vision`, `multimodal`, `other`) | François Chollet / ARC Prize (individual) | `verified_open` (Apache-2.0, allowed) | 1,000 tasks | Chollet, 2019 (arXiv:1911.01547) | 3.5 MB |

---

## 4. Phase 2 — Catalog Uniqueness & Duplicate Screening

### 4.1 Exact Identity Screening
Prior to metadata creation, all 25 candidate identifiers, slugs, and normalized titles were tested against the full 700-dataset baseline:
- **Exact ID Collisions:** 0 detected.
- **Exact Slug Collisions:** 0 detected.
- **Normalized Title Collisions:** 0 detected.

### 4.2 Substring and Related Benchmark Disambiguation

| Candidate ID | Substring Match in Catalog | Justification of Scientific Independence |
| :--- | :--- | :--- |
| `multilingual-librispeech` | `librispeech` | LibriSpeech is an English-only 1,000-hour ASR benchmark from 2015. Multilingual LibriSpeech (MLS) is a distinct 50,000-hour European multilingual corpus across 8 languages created by Meta FAIR in 2020. |
| `mmlu-pro` | `mmlu` | MMLU is the 2020 4-choice knowledge benchmark. MMLU-Pro (NeurIPS 2024) is a newly authored, reasoning-focused benchmark with 10 options per question, eliminating known hallucinations and saturation. |
| `pems-bay`, `pems04`, `pems08` | `metr-la` | METR-LA comprises 207 Los Angeles County sensors recorded in 2012. PEMS-BAY covers 325 San Francisco Bay Area sensors (District 4) in 2017. PEMS04 covers 307 Bay Area detectors in 2018. PEMS08 covers 170 San Bernardino detectors (District 8) in 2016. All represent disjoint sensor networks and temporal windows. |
| `arc-agi-1` | `ai2-arc` | AI2-ARC is a textual grade-school multiple-choice science exam question benchmark by AllenAI. ARC-AGI-1 (Chollet) is an abstract 2D grid visual reasoning competition benchmark. |
| `coco-wholebody` | `ms-coco` | MS-COCO provides 80-class object bounding boxes and 17 body keypoints. COCO-WholeBody introduces dense 133-keypoint whole-body pose annotations (face, hands, feet, body) created by SenseTime/CUHK. |

### 4.3 Automated Cross-Catalog Semantic Duplicate Engine Results
Running `scripts/audit_semantic_duplicates.py` across all **725 records (262,450 candidate pair comparisons)** yielded:
- **Total Records Scanned:** 725
- **Total Possible Pairs:** 262,450
- **Total Flagged Pairs:** 124
- **High-Confidence Candidate Pairs:** **0**
- **Medium-Confidence Candidate Pairs:** 96
- **Low-Confidence Candidate Pairs:** 28

All medium-confidence pairs were audited and confirmed to be legitimate benchmark suites, chronological challenges, or domain-adapted variants with no duplicate records present.

---

## 5. Phase 3 — Metadata Schema Compliance & Quality Audit

All 25 new metadata files were audited with `scripts/audit_metadata_quality.py` and strictly validated against `schemas/dataset.v1.schema.json`.

### 5.1 Quality Highlights
- **100% Schema Conformity:** Every record includes all mandatory fields (`schema_version: "1.0.0"`, `id`, `slug`, `name`, `description`, `homepage_url`, `publisher`, `modalities`, `tasks`, `tags`, `license`, `source_references`, `verification`).
- **Exact Split Arithmetic Integrity:** All split distributions either match the declared total sample count or represent verified subsets without introducing discrepancies.
- **Authoritative DOIs and BibTeX:** All academic citations include valid un-prefixed DOIs, verified HTTPS paper URLs, and balanced BibTeX entries.
- **License Status Clarity:** Zero records use unspecified licenses.

### 5.2 Research Readiness Distribution Impact

```mermaid
pie title OpenDatasets Research Readiness Distribution (725 Datasets)
    "Ready for Evaluation (498)" : 498
    "Documented with Caveats (182)" : 182
    "Needs Information Review (45)" : 45
```

- **Ready for Evaluation:** Increased from **484 to 498 datasets (+14)**.
- **Documented with Caveats:** Increased from **171 to 182 datasets (+11)** (due to explicit non-commercial restrictions, composite component licenses, or academic research use agreements).
- **Needs Information Review:** Remained flat at **45 datasets (+0)**. None of the 25 additions have ambiguous or missing provenance.

---

## 6. Phase 4 — Testing and Quality Gate Verification

| Verification Stage | Command Executed | Result | Details |
| :--- | :--- | :--- | :--- |
| **Catalog Metadata Validation** | `.venv/bin/python3 scripts/validate_datasets.py` | **PASS** | 725/725 dataset records valid against schema |
| **Catalog Manifest Synchronization** | `.venv/bin/python3 scripts/generate_catalog.py` | **PASS** | `frontend/public/data/catalog.json` synced with 725 datasets |
| **Python Unit & Audit Test Suite** | `.venv/bin/pytest` | **PASS** | 216/216 unit tests passed in 154.16s |
| **Frontend Vitest Suite** | `npm --prefix frontend test -- --run` | **PASS** | 252/252 tests passed in 1.31s |
| **Frontend Linter** | `npm --prefix frontend run lint` | **PASS** | ESLint passed with 0 errors |
| **Frontend Production Build** | `npm --prefix frontend run build` | **PASS** | Clean production Vite build in 573ms |

---

## 7. Conclusion & Next Steps

Task 51 successfully incorporates 25 premier research datasets into OpenDatasets, establishing a clean catalog of **725 datasets**. The catalog is ready for integration into `main` via pull request.
