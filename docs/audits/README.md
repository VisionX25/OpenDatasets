# OpenDatasets Audit Reports and Archives

## 1. Audit Report Storage Policy (Phase 1 Modernization)

Starting in Infrastructure Improvement Phase 1 (Issue #68, parent roadmap #65):

- **No Committed Generated Reports:** Audit reports (such as metadata quality evaluations, semantic duplicate pair matrices, and source link verification tables) are **not** committed to Git tracking.
- **CI Artifact Storage:** Automated audit jobs in CI generate reports on demand and upload them as temporary workflow run artifacts with standard 7-day retention.
- **Resource Protection:** This policy prevents repository bloat, reduces clone bandwidth for contributors, and eliminates megabytes of repetitive diffs with each dataset expansion batch.

## 2. Historical Audit Archive

Historical audit reports generated during earlier milestones (Tasks 38, 40, 43, 49, 50, and 51) are preserved in Git history at authoritative commit `11e0015db060a940a0eb9f117ff622ebdaec802b`.

A complete cryptographic inventory of all 31 archived files with their respective byte sizes and SHA-256 hashes is maintained in [`ARCHIVE_MANIFEST.json`](file:///docs/audits/ARCHIVE_MANIFEST.json).

### How to Retrieve Archived Reports

Archived files can be retrieved at any time directly from the Git object database without checking out older branches:

```bash
# View or extract any historical report by path:
git show 11e0015db060a940a0eb9f117ff622ebdaec802b:docs/audits/task-38/summary.md

# Extract a specific CSV or JSON finding report:
git show 11e0015db060a940a0eb9f117ff622ebdaec802b:docs/audits/task-50/metadata-quality-report.json > /tmp/task-50-report.json
```

## 3. Persistent Audit Documentation

The following manually maintained audit documentation remains tracked in this directory:

- [`README.md`](file:///docs/audits/README.md): This policy guide and archive index.
- [`ARCHIVE_MANIFEST.json`](file:///docs/audits/ARCHIVE_MANIFEST.json): Cryptographic SHA-256 catalog of archived historical reports.
- [`sample-count-breakdown-audit.md`](file:///docs/audits/sample-count-breakdown-audit.md): Quantitative breakdown methodology and partition census documentation.
