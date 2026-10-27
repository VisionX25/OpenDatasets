# OpenDatasets

[![CI](https://github.com/VisionX25/OpenDatasets/actions/workflows/ci.yml/badge.svg)](https://github.com/VisionX25/OpenDatasets/actions/workflows/ci.yml)

An open-source platform for discovering, exploring, and validating machine learning datasets.

## Project Overview

OpenDatasets is an independent open-source platform by **VisionX25** built to help researchers, data scientists, and ML engineers discover verified datasets, inspect data quality metrics, and collaborate transparently.

### Current Implementation Status

- **Task 01 (Frontend Shell)**: Completed — React 19 + TypeScript + Vite responsive application shell with client-side routing, Tailwind CSS, and Lucide React.
- **Task 02 (Dataset Metadata Foundation)**: Completed — Versioned JSON Schema (`v1`), structured catalog in `data/datasets/`, strict offline validator (`scripts/validate_datasets.py`), and automated pytest suite.
- **Task 03 (Functional Dataset Explorer & Reliability)**: Completed — Automated atomic catalog generator (`scripts/generate_catalog.py`), interactive category-based discovery, multi-field search and filters, dataset details route (`/datasets/:slug`), runtime catalog validation, and reliable clipboard copying.
- **Task 04 (GitHub Actions CI/CD)**: Completed — Professional, lightweight CI workflow (`.github/workflows/ci.yml`) automatically validating metadata, testing schemas, enforcing catalog sync, and running frontend unit tests, lints, and builds on push and pull requests.
- **Planned Milestones**:
  - Python + FastAPI backend service (REST API endpoints, dataset ingestion pipeline).
  - Automated dataset schema & distribution profiling pipelines.

## Tech Stack

- **Frontend**:
  - React 19
  - TypeScript
  - Vite
  - Tailwind CSS
  - React Router
  - Lucide React
  - Vitest
- **Data Engineering & Backend Foundation**:
  - Python 3.10+
  - JSON Schema (Draft-7)
  - `jsonschema`
  - `pytest`
- **Planned Backend**:
  - Python
  - FastAPI

## Project Structure

```text
OpenDatasets/
├── .github/
│   └── workflows/
│       └── ci.yml           # GitHub Actions CI workflow (metadata validation & frontend checks)
├── data/
│   └── datasets/            # Source-of-truth metadata records (one JSON per dataset)
│       ├── cifar-10.json
│       ├── iris.json
│       └── mnist.json
├── frontend/                # React + TypeScript + Vite frontend application
│   ├── public/
│   │   ├── data/
│   │   │   └── catalog.json # Generated catalog for client-side discovery
│   │   ├── favicon.svg
│   │   └── icons.svg
│   ├── src/
│   │   ├── components/      # UI components (Header, Footer, Layout, DatasetCard, CategoryGrid)
│   │   ├── pages/           # Page routes (HomePage, ExplorePage, DatasetDetailPage, AboutPage)
│   │   ├── services/        # Catalog data loader (catalogService.ts)
│   │   ├── types/           # TypeScript schema definitions (dataset.ts)
│   │   ├── utils/           # Centralized category, filter, and clipboard utilities
│   │   ├── App.tsx          # Client-side router configuration
│   │   ├── index.css        # Tailwind CSS styles
│   │   └── main.tsx         # Application entry point
│   ├── eslint.config.js     # ESLint configuration
│   ├── package.json         # Frontend dependencies and scripts (with predev/prebuild hooks)
│   ├── tsconfig.json        # TypeScript configuration
│   └── vite.config.ts       # Vite build & Tailwind configuration
├── schemas/
│   └── dataset.v1.schema.json # JSON Schema definition for dataset metadata
├── scripts/
│   ├── generate_catalog.py  # Generates frontend/public/data/catalog.json with atomic replacement
│   └── validate_datasets.py # Strict offline CLI validator for dataset metadata
├── tests/
│   └── test_metadata_validation.py # Pytest suite covering schema, URLs, edge cases, and catalog generation
├── .gitignore               # Repository ignore rules
├── LICENSE                  # MIT License
├── pytest.ini               # Pytest configuration
├── README.md                # Project documentation
└── requirements-dev.txt     # Python development and validation dependencies
```

## Dataset Metadata Architecture

OpenDatasets adheres to a modular, file-per-dataset metadata pattern:

1. **Source of Truth (`data/datasets/*.json`)**:
   Each dataset is stored as an independent JSON record conforming to `schemas/dataset.v1.schema.json`.
2. **Deterministic Catalog (`frontend/public/data/catalog.json`)**:
   `scripts/generate_catalog.py` validates all dataset JSON files, enforces unique IDs and slugs, sorts them deterministically by dataset ID, and atomically writes the unified catalog.
3. **Build & Dev Integration**:
   `frontend/package.json` includes `predev` and `prebuild` hooks that automatically invoke `generate_catalog.py`, ensuring the web UI always serves fresh, validated dataset metadata.

### Schema Overview (`schemas/dataset.v1.schema.json`)

All dataset metadata files conform to JSON Schema Draft-7 (`dataset.v1.schema.json`):

| Field | Type | Description | Required |
| :--- | :--- | :--- | :--- |
| `schema_version` | String | Schema version (e.g., `"1.0.0"`). | Yes |
| `id` | String | Unique machine identifier (e.g., `"cifar-10"`). | Yes |
| `slug` | String | URL-friendly slug (e.g., `"cifar-10"`). | Yes |
| `name` | String | Official dataset title. | Yes |
| `description` | String | Comprehensive dataset summary. | Yes |
| `homepage_url` | String | Canonical dataset landing page (HTTP/HTTPS). | Yes |
| `publisher` | Object | Publishing organization or individual, with category. | Yes |
| `modalities` | Array | Data types (`vision`, `tabular`, `nlp`, `audio`, etc.). | Yes |
| `tasks` | Array | Standard ML tasks (`image-classification`, etc.). | Yes |
| `tags` | Array | Descriptive discovery tags. | Yes |
| `license` | Object | License details with explicit status (`verified_open`, `unspecified_by_source`, etc.). | Yes |
| `source_references` | Array | Primary and secondary source links and documentation. | Yes |
| `verification` | Object | Metadata audit trail (`status`, `verified_by`, `verified_date`). | Yes |
| `size` | Object | Disk / download size, formats, and verification status. | Optional |
| `sample_count` | Object | Total records, split breakdowns, and item unit. | Optional |
| `dates` | Object | `published` and `last_updated` ISO dates. | Optional |
| `citation` | Object | Academic paper citation, DOI, and BibTeX. | Optional |
| `provenance` | Object | Collection methodology and curation notes. | Optional |

> **Handling Missing or Unverified Information**: Do not guess or invent data. The schema provides explicit states such as `status: "unspecified_by_source"`, `status: "unknown"`, or `status: "unverified"` when authoritative values are not provided by the source.

### Instructions for Adding a Dataset

1. Create a new JSON file inside `data/datasets/` named after the dataset slug (e.g., `data/datasets/<slug>.json`).
2. Populate the required metadata fields using authoritative sources (official website, documentation, or original paper).
3. Ensure all URLs start with `http://` or `https://` and do not contain whitespace.
4. Verify that the `id` and `slug` do not collide with any existing catalog entry.
5. Validate the dataset:
   ```bash
   python3 scripts/validate_datasets.py data/datasets/<slug>.json
   ```
6. Regenerate the catalog:
   ```bash
   python3 scripts/generate_catalog.py
   ```
7. Run the test suites:
   ```bash
   pytest
   cd frontend && npm test
   ```

---

## Local Development Setup

### Prerequisites

- **Python**: v3.10 or later
- **Node.js**: v18.0.0 or later (v20+ / v24+ recommended)
- **npm**: v9.0.0 or later

### Python Environment & Validation

1. **Install Python dependencies**:
   ```bash
   pip install -r requirements-dev.txt
   ```

2. **Run metadata validation**:
   ```bash
   python3 scripts/validate_datasets.py
   ```

3. **Regenerate dataset catalog**:
   ```bash
   python3 scripts/generate_catalog.py
   ```

4. **Run Python automated tests**:
   ```bash
   pytest
   ```

### Frontend Setup

1. **Navigate to the frontend directory**:
   ```bash
   cd frontend
   ```

2. **Install dependencies**:
   ```bash
   npm install
   ```

3. **Start the local development server**:
   ```bash
   npm run dev
   ```
   *Note: `npm run dev` automatically runs the `predev` hook to regenerate `catalog.json` before booting Vite.*
   The application will be accessible at `http://localhost:5173/`.

4. **Frontend quality & test checks**:
   ```bash
   npm test           # Run Vitest unit tests (search, filter, category logic, clipboard, catalogService)
   npm run lint       # Run ESLint quality checks
   npx tsc --noEmit   # Run TypeScript compiler checks
   npm run build      # Run production build (includes prebuild catalog generation)
   ```

---

## Continuous Integration (CI/CD)

OpenDatasets uses a lightweight, secure GitHub Actions workflow defined in [`.github/workflows/ci.yml`](.github/workflows/ci.yml) to validate every contribution automatically.

### Workflow Purpose & Triggers

The CI pipeline runs on:
- Every **push** to the `main` branch.
- Every **pull request** targeting the `main` branch.
- Manual triggers via **`workflow_dispatch`**.

### Checks Performed

The pipeline executes two independent jobs concurrently:

1. **Python Metadata Validation (`python-validation`)**:
   - **Environment**: Python 3.11 on `ubuntu-latest`.
   - **Schema & Semantic Validation**: Executes `python3 scripts/validate_datasets.py` to ensure all dataset records in `data/datasets/*.json` adhere to `schemas/dataset.v1.schema.json`, contain valid HTTP/HTTPS URL formats without whitespace, and contain unique dataset IDs and slugs.
   - **Automated Test Suite**: Executes `pytest` to run all unit tests covering schema compliance, duplicate detection, and atomic catalog generation.
   - **Catalog Consistency Check**: Generates a temporary catalog and compares it against the committed `frontend/public/data/catalog.json` using `diff -u`. If a metadata change was made without regenerating and committing the catalog, the job fails.

2. **Frontend Quality & Build (`frontend-quality`)**:
   - **Environment**: Node.js 20 (LTS) and Python 3.11 on `ubuntu-latest`.
   - **Dependency Installation**: Uses `npm ci` with automated package caching based on `frontend/package-lock.json`.
   - **Unit Tests**: Executes Vitest suite (`npm test`) covering search filtering, category mapping, runtime catalog validation, and clipboard utilities.
   - **Static Analysis (Linting)**: Executes ESLint (`npm run lint`) to maintain strict code quality standards.
   - **Production Build**: Compiles TypeScript and builds the production bundle with Vite (`npm run build`).

### Running Checks Locally

Contributors can run the exact same checks locally before committing or opening a pull request:

```bash
# 1. Run Python metadata validation and tests
python3 scripts/validate_datasets.py
pytest

# 2. Verify catalog consistency (regenerate if needed)
python3 scripts/generate_catalog.py --output /tmp/catalog.test.json
diff -u frontend/public/data/catalog.json /tmp/catalog.test.json

# 3. Run frontend quality checks and production build
cd frontend
npm test
npm run lint
npm run build
```

### Regenerating the Catalog

If you add, modify, or remove any dataset in `data/datasets/`, regenerate the catalog and commit the result:

```bash
python3 scripts/generate_catalog.py
```

### Pre-PR Contribution Checklist

Before opening a pull request, ensure all verification steps pass cleanly:

- [ ] All new or modified dataset files conform to `schemas/dataset.v1.schema.json` (`python3 scripts/validate_datasets.py`).
- [ ] Pytest passes with zero failures (`pytest`).
- [ ] Catalog has been regenerated and synchronized (`python3 scripts/generate_catalog.py`).
- [ ] Frontend Vitest passes (`cd frontend && npm test`).
- [ ] ESLint passes without errors or warnings (`cd frontend && npm run lint`).
- [ ] Production build completes successfully (`cd frontend && npm run build`).

---

## License

This project is licensed under the [MIT License](LICENSE).
