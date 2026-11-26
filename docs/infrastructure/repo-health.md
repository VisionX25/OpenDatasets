# OpenDatasets Repository Health Monitoring Architecture (Phase 0)

## Overview

The OpenDatasets Repository Health Monitoring system provides automated, offline-first, reproducible measurements of repository integrity, catalog metadata completeness, licensing consistency, sample-count partition hygiene, taxonomy health, formatting compliance, generated artifact storage, automated test performance, and CI automation posture.

This tool was established in **Phase 0** of the OpenDatasets Infrastructure Improvement Roadmap ([Parent Issue #65](https://github.com/VisionX25/OpenDatasets/issues/65), [Phase 0 Tracking Issue #66](https://github.com/VisionX25/OpenDatasets/issues/66)).

---

## 1. Primary Script: `scripts/repo_health.py`

`scripts/repo_health.py` is a standalone, modular Python utility designed to run with Python's standard library only. It executes in less than 2 seconds by default and avoids network calls or quadratic pairwise comparisons.

### Command-Line Usage

```bash
# Display help and command options
python3 scripts/repo_health.py --help

# Run default health assessment and print Markdown to stdout
python3 scripts/repo_health.py

# Output machine-readable JSON
python3 scripts/repo_health.py --format json

# Output human-readable Markdown
python3 scripts/repo_health.py --format markdown

# Output a concise 3-line terminal summary
python3 scripts/repo_health.py --format summary

# Write both JSON and Markdown reports to explicit paths
python3 scripts/repo_health.py \
  --json-output /tmp/repo-health.json \
  --markdown-output /tmp/repo-health.md

# Include optional dataset JSON schema validation
python3 scripts/repo_health.py --run-validation

# Include complete pytest test suite execution and timing
python3 scripts/repo_health.py --run-tests

# Include full pytest benchmark reporting slowest tests (--durations=20)
python3 scripts/repo_health.py --benchmark

# Specify custom report byte budget threshold (triggers bounded compact fallback)
python3 scripts/repo_health.py --max-report-bytes 2097152

# Target an alternative repository root (supports temporary fixture testing)
python3 scripts/repo_health.py --repo-root /path/to/repo
```

### Exit-Code Semantics

`scripts/repo_health.py` implements explicit execution-status semantics:
- `0`: Successful health report generation where all requested checks succeed. Ordinary catalog findings and manual-review candidates do **not** fail the CLI.
- `1`: Explicitly requested checks failed (either `--run-validation` detected schema errors or `--run-tests` / `--benchmark` detected test failures).
- `2`: Fatal execution error or unhandled runtime failure.

**Diagnostic Report Preservation:** When requested checks fail, diagnostic reports (`--json-output` and `--markdown-output`) are fully generated and saved to disk **before** the script exits with code 1. This ensures CI workflows can always publish diagnostic summaries and upload artifacts regardless of job failure status.

---

## 2. Metric Groups

The health tool collects measurements across 11 structured metric groups:

### Metric Group A: Repository Identity
Captures repository name, active Git commit SHA, branch, total/tracked/untracked dataset counts, working tree status (`clean` or `dirty`), UTC generation timestamp, Python version, Node.js version, and npm version. Absolute user paths and credentials are strictly excluded.

### Metric Group B: Catalog Health
Measures total dataset records, JSON parsing validity, exact ID collisions, case/punctuation normalized ID collisions, slug collisions, core schema field completeness, and coverage across:
- Academic citations (`citation.paper_title`, `bibtex`, or text)
- Digital Object Identifiers (`doi`)
- Milestone milestone publication dates (`dates.published`)
- Curator verification metadata (`verification.status` and `verification.date`)
- Canonical homepage URLs (`homepage_url`)
- Authoritative source references (`source_references`)
- Declared physical byte sizes (`size`)
- Spoken/written languages for NLP and Audio datasets (`languages`)

### Metric Group C: Licensing Consistency
Audits license status distribution (`verified_open`, `verified_non_commercial`, `custom_permissive`, `public_domain`, `unspecified_by_source`, `proprietary`), commercial-use distribution (`allowed`, `forbidden`, `unknown`), and SPDX identifier coverage.
Identifies manual review candidates:
1. Non-commercial SPDX identifiers classified as `verified_open` (e.g. `anli`, `sciq`).
2. Non-commercial licenses with `commercial_use: allowed`.
3. Permissive SPDX identifiers with `commercial_use: unknown` (e.g. `desed`, `caltech-256`, `winoground`, `vggsound`, `livecodebench`, `lakh-midi`, `voxceleb1`).
4. Multi-license or per-object terms (e.g. `objaverse`, `objaverse-xl`).

*Note: Permissive SPDX combined with unknown commercial use reflects mixed-asset rights rather than automatic compliance errors.*

### Metric Group D: Sample-Count Consistency
Evaluates dataset sample totals, unit declarations, split definitions, auxiliary breakdowns, partition completeness (`complete`, `partial`, `unspecified`), and partition overlap (`disjoint`, `overlapping`, `unspecified`).
Strictly separates:
- **Raw arithmetic discrepancies:** Datasets where `total != sum(splits.values())` under legacy `unspecified` semantics (29 catalog records).
- **Actionable hard errors:** Datasets where explicit `complete` and `disjoint` partition declarations contradict split arithmetic (0 catalog records).

### Metric Group E: Taxonomy Health
Measures distinct tasks (704) and tags (1,981), singleton tasks (447) and tags (1,407), top frequencies, and punctuation-normalized duplicate candidates (e.g., `multiclass-classification` vs `multi-class-classification`). Evaluates catalog mapping against the six research discovery categories defined in `frontend/src/utils/datasetFilters.ts`.

### Metric Group F: Formatting and Metadata Hygiene
Checks POSIX trailing newline compliance across all catalog files (39 files lacking trailing newline), scans for plain `http://` URL occurrences (78 occurrences across 42 unique URLs), and flags suspected truncated slugs hitting the historical 45-character boundary (22 records).

### Metric Group G: Generated Artifact Sizes
Measures actual file sizes and deterministic gzip compression (level 9, `mtime=0`) for:
- `frontend/public/data/catalog.json` (3.39 MB raw, 727.0 KB gzip)
- `docs/audits/` (4.06 MB across 31 audit reports)
Computes generated artifact share of total tracked Git repository bytes (**60.4%** of repository storage).

### Metric Group H: Automated Test Health
Inventories Python test modules (8 test files) and identifies catalog-count-dependent assertions (18 hardcoded `== 875` assertions). Supports optional execution of `pytest` and pytest duration benchmarking (`--durations=20`).

### Metric Group I: Source-Link Monitoring Cadence
Analyzes total catalog URL references (5,462 references across 2,617 unique URLs), batch size (50 URLs/week), and rotation cycle (**52.34 weeks** / ~1.0 year). Audits artifact retention (90 days) and automated issue alerting posture.

### Metric Group J: GitHub Actions & Security Automation
Audits workflow files under `.github/workflows/`, job timeouts, concurrency controls, permissions blocks, Dependabot configuration, CODEOWNERS, pre-commit hooks, Python dependency lockfiles, and Node.js engines.

### Metric Group K: Frontend Readiness
Static code inspection of frontend SEO, discoverability, and accessibility infrastructure:
- Per-route `document.title` handling (absent)
- Wildcard 404 NotFound routing (absent; redirects to `/`)
- Search discovery files: `sitemap.xml` and `robots.txt` (absent)
- Schema.org `Dataset` JSON-LD structured data (absent)
- Automated axe-core accessibility gates (absent)

---

## 3. Finding Status and Severity Semantics

Every finding produced by `scripts/repo_health.py` carries explicit semantics:

| Severity | Status | Meaning | Action Required |
| :--- | :--- | :--- | :--- |
| `error` | `failed` | Contradictory metadata or schema violation (e.g. malformed JSON, complete+disjoint arithmetic mismatch). | Must be fixed before merge. |
| `warning` | `review_required` | Potential inconsistency requiring curator review (e.g. permissive SPDX with unknown commercial use, missing units). | Scheduled for manual review in future roadmap phase. |
| `warning` | `warning` | Operational bottleneck (e.g. 52-week monitoring cycle). | Addressed in infrastructure roadmap. |
| `info` | `measured` | Descriptive catalog metric (e.g. singleton task count, raw arithmetic sum discrepancy under unspecified semantics). | Monitored over time. |
| `info` | `skipped` | Optional check not executed in fast default mode (e.g. full test suite). | Informational. |

---

## 4. Free-Tier Resource Protection Guardrails

OpenDatasets relies on GitHub free-tier hosting and GitHub Pages. The health monitoring architecture strictly enforces free-tier resource protections:

1. **Zero Generated Report Commits:** Health reports are never committed to Git. They are stored temporarily in `$RUNNER_TEMP` and uploaded as CI artifacts.
2. **Zero Additional GitHub Pages Storage:** Generated reports are never written to `frontend/public/` or `dist/`, keeping deployment bundles slim.
3. **Seven-Day CI Artifact Retention:** All workflow run artifacts use `retention-days: 7` to conserve GitHub Actions storage quota.
4. **2 MB Combined Report Budget & Compact Fallback:** A strict CI gate verifies that `repo-health.json` + `repo-health.md` <= 2,097,152 bytes (actual size is ~55 KB). If the combined report ever exceeds the budget, `scripts/repo_health.py` automatically generates a valid compact fallback JSON and Markdown report with explicit omission tracking (`budget_fallback` metadata) rather than truncating into invalid output.
5. **Dependency Consistency:** The nightly workflow uses the repository-defined `requirements-dev.txt` (`cache: pip`) in Python 3.11, matching standard CI environments and preventing dependency drift.
6. **Cadence Partitioning:** Lightweight offline health audits run daily (Mon-Sat, ~0.43s runtime). Heavy pytest duration benchmarks run only weekly on Sundays.
7. **Concurrency Control:** Workflows use `concurrency: group: repo-health, cancel-in-progress: true` to prevent redundant runner execution.
8. **Timeout Limits:** All health jobs enforce an explicit 15-minute timeout.
9. **Failure Propagation Without Artifact Loss:** CI steps use `continue-on-error: true` on health script execution combined with `if: always()` on summary/artifact publishing and final failure propagation, guaranteeing that failed runs upload full diagnostic reports while properly marking the GitHub Actions run as failed.

---

## 5. Nightly GitHub Actions Workflow

Configured in `.github/workflows/repo-health.yml`:
- **Workflow Name:** `Repository Health Monitoring`
- **Schedule:** Daily at 03:00 UTC (`0 3 * * *`).
- **Manual Trigger:** `workflow_dispatch` with options for `--benchmark`, `--run-validation`, and `--run-tests`.
- **Permissions:** `contents: read` (least privilege).
- **Outputs:** Publishes full Markdown report to `$GITHUB_STEP_SUMMARY` and uploads JSON + Markdown as a workflow artifact.

---

## 6. Historical Baseline Comparison (Issue #65)

| Metric | Issue #65 Historical | Current Measured | Difference | Methodological Notes |
| :--- | ---: | ---: | ---: | :--- |
| Catalog dataset count | 875 | 875 | 0 | Exactly 875 verified research datasets. |
| Python unit tests (count) | 240 | 240 (259 with health tests) | +19 | 19 new fixture-based health unit tests added. |
| Catalog JSON size (raw) | 3.38 MB | 3.39 MB (3,386,173 B) | +0.01 MB | 27.5% of tracked repository storage. |
| Catalog JSON size (gzip) | 728 KB | 727.0 KB (726,994 B) | -1.0 KB | Deterministic gzip level 9, mtime=0. |
| Generated audit reports size | 4.0 MB | 4.06 MB (4,055,047 B) | +0.06 MB | 31 audit files in `docs/audits/`. |
| Distinct taxonomy tasks | 704 | 704 | 0 | 447 singleton tasks (63.5%). |
| Distinct taxonomy tags | 1,981 | 1,981 | 0 | 1,407 singleton tags (71.0%). |
| Uncategorized UI datasets | 9 | 1 | -8 | 1 completely uncategorized (`lakh-midi`); 16 lack primary modality category. |
| Suspected truncated slugs | 28 | 22 | -6 | Slugs hitting historical 45-character ceiling. |
| Files lacking trailing newline | 27 | 39 | +12 | 39 dataset files in `data/datasets/` lack trailing newline. |
| Plain HTTP URLs | 45 (23 unique) | 78 (42 unique) | +33 | Historical measured structured fields; 78 occurrences across all JSON strings. |
| Language metadata (NLP+Audio) | 175 / 313 (55.9%) | 175 / 313 (55.9%) | 0 | 138 records lack languages. |
| Dataset size metadata coverage | 468 / 875 (53.5%) | 468 / 875 (53.5%) | 0 | 407 records lack size (94 unspecified, 313 absent). |
| Sample count raw sum mismatch | 29 | 29 | 0 | Legacy records with unspecified completeness/overlap; 0 actionable errors. |
| Non-commercial `verified_open` | 2 | 2 | 0 | `anli` and `sciq` (CC-BY-NC). |
| Permissive SPDX unknown comm | 11 | 11 | 0 | Review candidates due to mixed/per-object terms. |
| Source monitoring cycle | ~52 weeks | 52.34 weeks | 0 | 50 URLs/week over 2,617 unique URLs. |

---

## 7. Roadmap Handoff

Measurements established in Phase 0 guide the execution of subsequent improvement phases:
- **Phase 1 (Artifacts & Tests):** Untrack `frontend/public/data/catalog.json`, stop committing `docs/audits/`, decouple tests from catalog record count using frozen fixtures.
- **Phase 2 (Validator & Ratchet):** Surface warnings in CI, enforce `sample_count.unit`, introduce `data/legacy-baseline.json` ratchet.
- **Phase 3 (CI Speed & Hardening):** Fast candidate blocking for duplicate audit (< 30s pytest), add timeouts and PR concurrency.
- **Phase 4 (Legacy Data Migration):** Normalize newlines, resolve HTTP URLs, harmonize singleton tasks, audit license review candidates.
- **Phase 6 (Automation & Monitoring):** Increase link monitor batch size to 250, automate rolling issue updates.
- **Phase 7 (Frontend, SEO & A11y):** Implement per-route document titles, sitemap.xml, robots.txt, Schema.org JSON-LD, axe-core gate.
