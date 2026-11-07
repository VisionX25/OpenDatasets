# OpenDatasets

[![CI](https://github.com/VisionX25/OpenDatasets/actions/workflows/ci.yml/badge.svg)](https://github.com/VisionX25/OpenDatasets/actions/workflows/ci.yml)

An open-source catalog for discovering machine learning datasets and inspecting their structured metadata, source references, and access conditions.

## Project Overview

OpenDatasets is an academic, open-source initiative by [VisionX25](https://github.com/VisionX25) built for researchers, machine learning engineers, data scientists, and students. The platform provides clean, standardized dataset metadata across multiple modalities with documented access terms and authoritative citations.

The current catalog indexes **365 verified research dataset records** across six core machine learning domains. Users can explore records, search and filter facets, compare datasets side-by-side within categories, save datasets locally, and export academic citations.

> **Note on Data Hosting**: OpenDatasets catalogs structured metadata and links to original publishers and papers. It does not host or redistribute the underlying binary data files.

**Quick Links:** [Explore Datasets](https://visionx25.github.io/OpenDatasets/explore) · [Contribute](CONTRIBUTING.md) · [Suggest a Dataset](https://github.com/VisionX25/OpenDatasets/issues/new?template=dataset_suggestion.yml) · [Report an Issue](https://github.com/VisionX25/OpenDatasets/issues/new/choose) · [Roadmap](ROADMAP.md)

**[Open the Live Application](https://visionx25.github.io/OpenDatasets/)**

---

## Key Features

### 1. Six Curated Research Categories
OpenDatasets categorizes all records into six distinct machine learning categories:
- **Computer Vision (`computer-vision`)**: Object detection, segmentation, image classification, facial recognition, and medical imaging.
- **Natural Language Processing (`natural-language-processing`)**: Question answering, summarization, machine translation, sentiment analysis, and reasoning benchmarks.
- **Audio & Speech (`audio-speech`)**: Speech recognition (ASR), speaker verification, audio classification, and speech translation.
- **Tabular & Time-Series (`tabular-time-series`)**: Tabular classification, regression, weather forecasting, financial time-series, and sensor benchmarks.
- **Multimodal & Generative (`multimodal-generative`)**: Vision-language models, image captioning, text-to-image/video, and generative audio.
- **Evaluation & Benchmarks (`evaluation-benchmarks`)**: Holistic model evaluation suites, safety benchmarks, reasoning diagnostics, and code generation testbeds.

### 2. Dataset Discovery, Search & Filtering
- **Multi-Field Instant Search**: Full-text searching across dataset titles, descriptions, publisher names, tasks, and tags.
- **Faceted Filters**: Narrow the catalog by Category, Data Modality (`vision`, `nlp`, `audio`, `tabular`, `multimodal`), Task, License Status, and Publication Year.
- **Lightweight Sorting**: Order datasets by Default order, Name (A–Z / Z–A), Publication Year (Newest / Oldest), or Sample Count (Largest / Smallest) with deterministic tie-breaking and URL persistence.
- **URL Synchronization**: All search queries, filter facets, and sort preferences are mirrored in URL search parameters for seamless sharing.

### 3. Category-Specific Dataset Comparison
- **Side-by-Side Comparison**: Compare 2 to 3 datasets from the same category at `/compare?datasets=slug1,slug2,slug3`.
- **In-Context Activation**: Click the minimal "Compare" action in the footer of any dataset card within a category page to add it to the comparison selection.
- **Comparison Selection Bar**: A compact, accessible floating toolbar indicates selection progress (`X of 3 selected`), allows clearing selections, and navigates directly to the comparison matrix.
- **Detailed Attribute Matrix**: Evaluates modalities, primary tasks, license status, sample counts, split breakdowns, download sizes, publication dates, and citation metadata side-by-side. Handles missing, unverified, or non-comparable fields explicitly without fabricating information.

### 4. Bookmark & Saved Datasets
- **Minimal Card Action**: A subtle, borderless bookmark icon anchored at the top-right of every dataset card allows quick saving and removal.
- **Client-Side Persistence**: Saved dataset slugs are stored in browser `localStorage` (`opendatasets_saved_bookmarks`), ensuring zero tracking, zero accounts, and zero database requirements.
- **Catalog Integration**: Access your saved collection via the "Saved (X)" toggle button in the catalog filter bar or directly via `/datasets?saved=true`.

### 5. Academic Citation Export
- **Multi-Format Support**: Generate standard academic citations in **BibTeX**, **APA 7th edition**, and **IEEE** formats directly on dataset detail pages.
- **Authoritative Provenance**: Formatted from verified author lists, publication venues, years, and DOIs.
- **One-Click Actions**: Copy formatted citation text to the clipboard or download citation files (`.bib` / `.txt`).
- **Transparent Limitations**: If citation metadata is incomplete, clear limitation notices are displayed rather than inventing missing authors or dates.

---

## Metadata Verification & Audit Scope

Metadata is curated against official publications, institutional repositories, and original documentation.

Automated offline checks enforce:
- JSON Schema Draft-7 conformance (`schemas/dataset.v1.schema.json`).
- Valid HTTP/HTTPS URL syntax without whitespace.
- Unique dataset IDs and URL slugs.
- Arithmetic consistency of sample splits where exhaustive.
- Deterministic synchronization between `data/datasets/*.json` and `frontend/public/data/catalog.json`.

> **Verification Limitations**: Automated offline checks validate schema syntax and cited metadata. They do **not** inspect raw binary data files, measure labeling bias or accuracy, confirm live external mirror availability, or guarantee fitness for a particular application. Dataset licenses and access conditions remain strictly under each publisher's original terms; users must review them prior to downloading or using underlying data.

### Historical Audit Documentation
Earlier audits and verification manifests are preserved in `docs/`:
- [`docs/metadata-audit.md`](docs/metadata-audit.md): Historical audit of initial 27 baseline dataset records.
- [`docs/research-verification-manifest.md`](docs/research-verification-manifest.md): Research manifest for initial expansion batches.
- [`docs/medical-dataset-metadata-audit.md`](docs/medical-dataset-metadata-audit.md): Specialized audit of biomedical and clinical dataset records.
- [`docs/task20-nlp-weather-dataset-audit.md`](docs/task20-nlp-weather-dataset-audit.md): Split verification and license audit for NLP and environmental datasets.

---

## Architecture & Technology Stack

- **Frontend Application**:
  - React 19 with TypeScript
  - Vite build toolchain
  - Tailwind CSS (responsive layout, dark mode support)
  - React Router (client-side routing with deep linking)
  - Lucide React (minimal, accessible icons)
  - Vitest (unit and integration tests)
- **Data Engineering & Automation**:
  - Python 3.10+
  - JSON Schema Draft-7 (`jsonschema`)
  - Pytest (validation and automation test suite)
- **Deployment**:
  - Static GitHub Pages hosting
  - GitHub Actions CI/CD (`.github/workflows/ci.yml`)
  - `scripts/prepare_pages.py` deep-link generator for direct route navigation and page reloads

---

## Project Structure

| Path | Purpose |
| :--- | :--- |
| `data/datasets/` | Individual dataset metadata records (`<slug>.json`) |
| `frontend/src/` | React application source code, components, and pages |
| `frontend/public/data/catalog.json` | Deterministic, unified dataset catalog consumed by the frontend |
| `schemas/` | Versioned JSON Schemas (`dataset.v1.schema.json`) |
| `scripts/validate_datasets.py` | Offline dataset validator ensuring schema compliance |
| `scripts/generate_catalog.py` | Atomic, deterministic catalog generator |
| `scripts/prepare_pages.py` | GitHub Pages static entry points and routing preparation |
| `tests/` | Python test suite (`test_metadata_validation.py`, `test_pages.py`, etc.) |
| `docs/` | Deployment guides, accessibility audits, and historical review manifests |
| `CONTRIBUTING.md` | Guidelines for proposing and adding datasets |
| `ROADMAP.md` | Development roadmap of implemented features and planned research |

---

## Local Development & Testing

### Prerequisites
- **Python**: v3.10 or later
- **Node.js**: v20 or later (v22/v24 recommended)
- **npm**: v9.0.0 or later

### 1. Python Setup & Metadata Validation
```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run dataset schema validation
python3 scripts/validate_datasets.py

# Run Python automated test suite
pytest
```

### 2. Frontend Setup & Development
```bash
# Navigate to the frontend directory
cd frontend

# Install dependencies
npm ci

# Start local development server (automatically updates catalog.json via predev hook)
npm run dev
```
The application will be accessible at `http://localhost:5173/` (or your assigned Vite port).

### 3. Frontend Quality Checks & Production Build
```bash
# Run Vitest test suite
npm test

# Run ESLint quality checks
npm run lint

# Run TypeScript typechecks and production build
npm run build
```

### 4. GitHub Pages Static Route Preparation
```bash
# Prepare static HTML deep-link entry points for GitHub Pages
python3 scripts/prepare_pages.py
```

---

## Contributing & Adding Datasets

We welcome contributions of high-quality research datasets. To add a dataset:

1. **Verify Uniqueness**: Check that the dataset `id`, `slug`, `name`, or `homepage_url` does not already exist in `data/datasets/`.
2. **Create Metadata Record**: Create `data/datasets/<slug>.json` conforming to `schemas/dataset.v1.schema.json`.
3. **Reference Authoritative Sources**: Populate metadata using official documentation, publications, and repository pages.
4. **Mark Uncertainties Explicitly**: If license terms, split numbers, or sizes are not documented by original authors, mark them as `"unspecified_by_source"`, `"unknown"`, or `"unverified"` rather than guessing.
5. **Validate & Regenerate**:
   ```bash
   python3 scripts/validate_datasets.py data/datasets/<slug>.json
   python3 scripts/generate_catalog.py
   pytest
   npm test --prefix frontend
   npm run lint --prefix frontend
   ```
6. **Submit**: See [CONTRIBUTING.md](CONTRIBUTING.md) for complete details on opening pull requests.

---

## License

Application code is licensed under the [MIT License](LICENSE). Metadata records are compiled from publicly available research documentation. Cataloged datasets remain under their publishers' respective licenses.
