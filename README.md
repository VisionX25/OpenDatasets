# OpenDatasets

An open-source platform for discovering, exploring, and validating machine learning datasets.

## Project Overview

OpenDatasets is an independent open-source platform by **VisionX25** built to help researchers, data scientists, and ML engineers discover verified datasets, inspect data quality metrics, and collaborate transparently.

### Current Implementation Status

- **Task 01 (Frontend Shell)**: Completed — React 19 + TypeScript + Vite responsive application shell with client-side routing, Tailwind CSS, and Lucide React.
- **Task 02 (Dataset Metadata Foundation)**: Completed — Versioned JSON Schema (`v1`), structured catalog in `data/datasets/`, strict offline validator (`scripts/validate_datasets.py`), and 43 automated pytest checks.
- **Planned Milestones**:
  - Python + FastAPI backend service (endpoints, search, dataset ingestion).
  - Automated dataset schema & distribution profiling pipelines.
  - Interactive web explorer with faceted filtering.
  - CI/CD via GitHub Actions.

## Tech Stack

- **Frontend**:
  - React 19
  - TypeScript
  - Vite
  - Tailwind CSS
  - React Router
  - Lucide React
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
├── data/
│   └── datasets/            # Validated JSON metadata records for ML datasets
│       ├── cifar-10.json
│       ├── iris.json
│       └── mnist.json
├── frontend/                # React + TypeScript + Vite frontend application
│   ├── public/              # Static assets
│   ├── src/                 # Application source code
│   │   ├── components/      # UI components (Header, Footer, Layout, Icons)
│   │   ├── pages/           # Page routes (HomePage, ExplorePage, AboutPage)
│   │   ├── App.tsx          # Client-side router configuration
│   │   ├── index.css        # Tailwind CSS styles
│   │   └── main.tsx         # Application entry point
│   ├── eslint.config.js     # ESLint configuration
│   ├── package.json         # Frontend dependencies and scripts
│   ├── tsconfig.json        # TypeScript configuration
│   └── vite.config.ts       # Vite build & Tailwind configuration
├── schemas/
│   └── dataset.v1.schema.json # JSON Schema definition for dataset metadata
├── scripts/
│   └── validate_datasets.py # Strict offline CLI validator for dataset metadata
├── tests/
│   └── test_metadata_validation.py # Pytest suite covering schema, URLs, and edge cases
├── .gitignore               # Repository ignore rules
├── LICENSE                  # MIT License
├── README.md                # Project documentation
└── requirements-dev.txt     # Python development and validation dependencies
```

## Dataset Metadata Foundation

OpenDatasets maintains dataset metadata as structured, versioned JSON records located in `data/datasets/`. Original dataset binary payloads are never downloaded or checked into Git.

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
5. Run the validator:
   ```bash
   python3 scripts/validate_datasets.py data/datasets/<slug>.json
   ```
6. Run the test suite:
   ```bash
   python3 -m pytest tests/ -v
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
   *Options:*
   - `--schema <path>`: Specify custom schema file (default: `schemas/dataset.v1.schema.json`).
   - `--data-dir <path>`: Specify custom dataset directory (default: `data/datasets`).
   - `--quiet`: Suppress verbose success logs.

3. **Run automated tests**:
   ```bash
   python3 -m pytest tests/ -v
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
   The application will be accessible at `http://localhost:5173/`.

4. **Frontend quality checks**:
   ```bash
   npx tsc --noEmit   # TypeScript type check
   npm run lint       # ESLint quality check
   npm run build      # Production build
   ```

## License

This project is licensed under the [MIT License](LICENSE).
