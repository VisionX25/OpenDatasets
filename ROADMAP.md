# OpenDatasets Roadmap

This roadmap clearly separates delivered and verified features from planned future development. It is an evolving plan, not a rigid delivery commitment.

---

## 1. Implemented & Available Features

### Discovery & Catalog Browsing
- [x] **Six Research Categories**: Organized into Computer Vision, NLP, Audio & Speech, Tabular & Time-Series, Multimodal & Generative, and Evaluation & Benchmarks.
- [x] **Full-Text Multi-Field Search**: Real-time matching across dataset names, descriptions, publishers, tasks, and tags.
- [x] **Faceted Filtering**: Filter by Category, Modality, Primary Task, License Status, and Publication Year.
- [x] **Lightweight Catalog Sorting**: Order datasets by Default, Name (A–Z / Z–A), Publication Year (Newest / Oldest), and Sample Count (Largest / Smallest) with stable tie-breaking and URL persistence.
- [x] **URL Synchronization**: Shareable deep-links capturing all active search, filter, and sort states.

### Category-Specific Dataset Comparison
- [x] **Side-by-Side Comparison Engine**: Compare 2 to 3 datasets from the same category at `/compare?datasets=slug1,slug2,slug3`.
- [x] **In-Card Compare Action**: Subtle, borderless footer button enabling comparison inside category pages.
- [x] **Comparison Selection Bar**: Floating accessible bar tracking selected items with clear-all and compare actions.
- [x] **Multi-Attribute Matrix**: Detailed side-by-side analysis of tasks, modalities, licenses, splits, sample counts, disk sizes, dates, and citations.

### Bookmarks & Saved Datasets
- [x] **Corner Bookmark Action**: Clean, icon-only bookmark button anchored to the top-right of every dataset card with keyboard accessibility.
- [x] **Client-Side Persistence**: Browser `localStorage` storage (`opendatasets_saved_bookmarks`) with zero tracking and zero backend dependencies.
- [x] **Discreet Catalog Access**: Single-click "Saved (X)" toggle in the filter toolbar and shareable `/datasets?saved=true` view.

### Academic Citation & Provenance
- [x] **Multi-Format Export**: Standardized BibTeX, APA 7th Edition, and IEEE citation generators directly on dataset detail pages.
- [x] **One-Click Actions**: Copy citation to clipboard and download citation files (`.bib`, `.txt`).
- [x] **Transparent Limitations**: Clear notices when citation fields are incomplete, without fabricating missing data.

### Metadata Quality & Architecture
- [x] **Strict JSON Schema (Draft-7)**: Versioned schema (`schemas/dataset.v1.schema.json`) with automated offline validation.
- [x] **Static GitHub Pages Deployment**: Fully static architecture with `scripts/prepare_pages.py` generating deep-link entry points for client-side routing.
- [x] **Automated CI/CD**: GitHub Actions workflow verifying schemas, catalog synchronization, Python tests, Vitest frontend tests, ESLint, and production builds.

---

## 2. Planned & Future Milestones

### Metadata Depth & Automation
- [ ] **Automated Source-Link Health Monitoring**: Periodic background workflow to detect dead links or domain changes across original publisher pages.
- [ ] **Dataset Versioning & Changelogs**: Document minor revisions and upstream dataset splits over time.
- [ ] **Extended Research Metadata**: Deeper documentation of curation protocols, annotation guidelines, and known demographic/linguistic coverage.

### Regional Research Datasets
- [ ] **Curated South Asian & Bangladesh Datasets**: Carefully verified open-access datasets in regional NLP (Bangla, Sylheti, Chittagonian), local agriculture, and regional climate/weather research with verified licensing.

### Advanced Analytical Capabilities (Later Exploration)
- [ ] **Reproducible Data Profiling**: Optional statistical distribution profiles for tabular and benchmark datasets with documented, reproducible methods.
- [ ] **Headless Metadata API**: Lightweight read-only endpoints if external integration needs arise, while keeping the main platform 100% static and zero-cost.

---

## Proposing Improvements

To suggest new features, report an issue, or propose a dataset, please visit:
- [Suggest a Dataset](https://github.com/VisionX25/OpenDatasets/issues/new?template=dataset_suggestion.yml)
- [Open an Issue](https://github.com/VisionX25/OpenDatasets/issues/new/choose)
- [Contribution Guidelines](CONTRIBUTING.md)
