# OpenDatasets Quality Ratchet and Validation Architecture

## 1. Overview

Infrastructure Phase 2 introduces a structured metadata quality validation engine and a monotonic legacy quality ratchet for the OpenDatasets repository.

Prior to Phase 2, `scripts/validate_datasets.py` focused strictly on JSON schema compliance and structural uniqueness, while data quality, formatting, arithmetic, licensing, and metadata conventions were audited out-of-band by secondary audit scripts (`audit_metadata_quality.py`, `audit_semantic_duplicates.py`).

The Phase 2 architecture:
- **Decouples** core validation logic from heavyweight quadratic audits via `scripts/validation_helpers.py`.
- **Introduces structured findings** (`ValidationFinding`) with stable rule identifiers, precise field paths, and severity tiers.
- **Establishes a deterministic legacy baseline** (`data/legacy-baseline.json`) capturing historical exceptions without mutating existing dataset records.
- **Enforces a monotonic ratchet** preventing new or modified datasets from introducing prohibited violations, ensuring legacy baseline exceptions can only shrink over time.

---

## 2. Architecture & Module Decoupling

The validation subsystem is organized into modular components:

```
OpenDatasets /
├── scripts /
│   ├── validation_helpers.py      # Lightweight shared constants, string normalization, partition helpers
│   ├── validate_datasets.py       # Core fast validator, rule engines, baseline CLI & ratchet logic
│   ├── audit_metadata_quality.py  # Out-of-band statistical metadata quality audit
│   └── audit_semantic_duplicates.py# Out-of-band O(N^2) semantic duplicate detection
├── data /
│   ├── legacy-baseline.json       # Authoritative tracked baseline of grandfathered exceptions (164 entries)
│   └── datasets /                 # 875 immutable dataset JSON records
└── schemas /
    └── dataset.v1.schema.json     # Authoritative Draft-07 JSON Schema contract
```

### Decoupling Guarantee
`scripts/validate_datasets.py` imports only pure normalization functions and constants from `scripts.validation_helpers`. It **never** imports or triggers `audit_semantic_duplicates.py` or `audit_metadata_quality.py`. This ensures fast offline execution (< 0.25 seconds for all 875 datasets) without quadratic comparisons.

---

## 3. Structured Finding Format

Every issue identified during validation produces a `ValidationFinding` dataclass instance:

```python
@dataclass
class ValidationFinding:
    rule_id: str
    dataset_id: str
    file_path: str
    field_path: str
    severity: str  # fatal_error | ratchetable_warning | manual_review | informational
    message: str
    fingerprint: str  # deterministic stable key: rule_id:dataset_id:field_path
    is_grandfathered: bool = False
    blocks_validation: bool = False
    remediation: str | None = None
```

### Deterministic Fingerprint
Fingerprints are computed deterministically as:
$$\text{fingerprint} = \text{rule\_id} : \text{dataset\_id} : \text{field\_path}$$
Example: `SMP-001:math:sample_count.unit`

---

## 4. Rule Inventory and Severity Classifications

Findings are categorized into four severity tiers:

| Severity | CLI Visibility | CI Exit Code | Grandfatherable? | Description |
|---|---|---|---|---|
| `fatal_error` | Error | Exit 1 (Blocking) | **No** | Violates JSON syntax, schema contract, or ID uniqueness |
| `ratchetable_warning` | Warning | Exit 1 if new/changed (Blocking) | **Yes** (if in baseline) | Objective metadata defect subject to monotonic ratchet |
| `manual_review` | Review | Exit 0 (Non-blocking) | N/A | Ambiguity or edge case requiring expert human review |
| `informational` | Info | Exit 0 (Non-blocking) | N/A | Contextual observations or notices |

### Implemented Quality Rules

#### Licensing Rules (`LIC-*`)
- `LIC-001` (`fatal_error`): Non-commercial license clause (e.g., `-NC` SPDX) combined with `commercial_use: "allowed"`. Unambiguous contradiction.
- `LIC-002` (`ratchetable_warning`): Non-commercial SPDX identifier combined with `license.status: "verified_open"`. Open definition requires commercial freedom.
- `LIC-REV-001` (`manual_review`): Permissive SPDX identifier with `commercial_use: "unknown"` or non-verified status, signaling mixed-asset or downstream restrictions.

#### Date Sanity Rules (`DATE-*`)
- `DATE-001` (`fatal_error`): Invalid calendar dates (e.g., `2024-02-31`, `2024-13-01`) or non-ISO date formats.
- `DATE-002` (`ratchetable_warning`): Inverted chronology where `dates.last_updated < dates.published`.
- `DATE-003` (`ratchetable_warning`): Future-dated verification events exceeding the reference boundary.
- `DATE-REV-001` (`manual_review`): Publication dates preceding the modern computing era (< 1940), requiring historical validation.

#### Canonical Formatting Rules (`FMT-*`)
- `FMT-001` (`ratchetable_warning`): Missing trailing newline at the end of a dataset JSON file.
- `FMT-002` (`fatal_error`): Duplicate object keys in dataset JSON files.
- `FMT-003` (`fatal_error`): File encoding is not valid UTF-8 or file is empty.

#### Sample-Count Unit Rules (`SMP-*`)
- `SMP-001` (`ratchetable_warning`): `sample_count` object present without declared measurement `unit`.
- `SMP-002` (`fatal_error`): Partition split arithmetic discrepancy where splits are declared `complete` and `disjoint`.
- `SMP-REV-001` (`manual_review`): Arithmetic discrepancy where partition completeness or overlap is unspecified or overlapping.

#### Slug Rules (`SLUG-*`)
- `SLUG-001` (`fatal_error`): Slug format invalid (must be lowercase alphanumeric kebab-case between 2 and 80 characters).
- `SLUG-002` (`ratchetable_warning`): Slug does not match dataset `id` or JSON file stem.
- `SLUG-REV-001` (`manual_review`): Mid-word truncation heuristic (suspected cutoff at 45 characters).

#### Language Metadata Rules (`LANG-*`)
- `LANG-001` (`ratchetable_warning`): Language tag does not conform to BCP 47 format.
- `LANG-002` (`ratchetable_warning`): Dataset includes NLP modality but lacks declared `languages` list (non-speech audio exempt).

---

## 5. Legacy Baseline & Monotonic Ratchet

### Initial Baseline (`data/legacy-baseline.json`)
The legacy baseline records exactly **164** grandfathered rule violations across the authoritative 875 dataset catalog:

| Rule ID | Violation Count | Description |
|---|---|---|
| `LANG-002` | 97 | NLP modality dataset missing `languages` array |
| `FMT-001` | 39 | Dataset JSON file missing trailing newline |
| `SMP-001` | 25 | `sample_count` present without `unit` |
| `LIC-002` | 2 | Non-commercial SPDX with `status: "verified_open"` (`anli`, `sciq`) |
| `LANG-001` | 1 | Malformed language tag (`common-voice`: `["multilingual"]`) |
| **Total** | **164** | Grandfathered baseline entries |

### Monotonic Ratchet Enforcement
When running in ratchet mode (`--ratchet`):
1. **Unchanged Legacy Records:** Warnings matching fingerprints in `data/legacy-baseline.json` are marked `is_grandfathered=True` and do **not** block execution.
2. **New Dataset Records:** Any new dataset record must pass validation cleanly with 0 fatal errors and 0 ratchetable warnings.
3. **Modified Dataset Records:** If a dataset file was modified in the current branch/PR relative to the trusted base, grandfathering is **denied** for all findings in that file. Modifications cannot retain or introduce violations.
4. **Baseline Expansion Prohibited:** Baseline update (`--update-baseline`) strictly forbids adding new fingerprints or substituting one violation for another. The baseline entry count can only decrease monotonically.

---

## 6. CLI Usage

### Everyday Validation
```bash
# Standard local validation (visible warnings and errors)
python scripts/validate_datasets.py

# Ratchet validation (enforce baseline constraints)
python scripts/validate_datasets.py --ratchet

# Strict mode (all warnings block, zero tolerance)
python scripts/validate_datasets.py --strict
```

### Baseline Management
```bash
# Update baseline after fixing legacy dataset issues (prunes resolved entries)
python scripts/validate_datasets.py --update-baseline

# Verify ratchet against a specific git base ref
python scripts/validate_datasets.py --ratchet --trusted-base origin/main
```

### Output Options
```bash
# Generate Markdown summary for GitHub Step Summary
python scripts/validate_datasets.py --ratchet --summary

# Emit GitHub Actions inline annotations (::warning and ::error)
python scripts/validate_datasets.py --ratchet --annotations

# Output structured findings as JSON
python scripts/validate_datasets.py --json-output /tmp/findings.json
```

---

## 7. CI Integration

In `.github/workflows/ci.yml`, the validation step runs:
```yaml
- name: Run dataset metadata validation
  env:
    BASE_REF: ${{ github.base_ref }}
  run: |
    if [ -n "$BASE_REF" ]; then
      python3 scripts/validate_datasets.py --ratchet --summary --annotations --trusted-base "origin/$BASE_REF"
    else
      python3 scripts/validate_datasets.py --ratchet --summary --annotations
    fi
```

This guarantees:
- Step summary is appended to `$GITHUB_STEP_SUMMARY`.
- Workflow annotations are created on changed files.
- PRs modifying legacy datasets must remediate existing violations on those files.
