# Reproducible Development Environments (Phase 1)

This document outlines the environment pinning and dependency locking mechanisms established in Infrastructure Improvement Phase 1 (Issue #68, parent roadmap #65).

## 1. Node.js Environment

### Version Standard
- **Node.js:** `>= 20.0.0` (specified in [`.nvmrc`](file:///.nvmrc) and [`frontend/.nvmrc`](file:///frontend/.nvmrc))
- **npm:** `>= 10.0.0`

### Configuration
- Defined in [`frontend/package.json`](file:///frontend/package.json) under `"engines"`:
  ```json
  "engines": {
    "node": ">=20.0.0",
    "npm": ">=10.0.0"
  }
  ```
- Fast version switching:
  ```bash
  nvm use
  ```
- Dependency installations must use `npm ci` rather than `npm install` in CI and production builds to ensure fidelity with [`frontend/package-lock.json`](file:///frontend/package-lock.json).

## 2. Python Environment

### Runtime Standard
- **Python:** `3.11` or `3.12`

### Locked Dependencies
- Direct specifications: [`requirements-dev.txt`](file:///requirements-dev.txt)
- Exact pinned lockfile: [`requirements-lock.txt`](file:///requirements-lock.txt) (and [`requirements.lock`](file:///requirements.lock))

### Installation
To install the verified, frozen dependencies:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements-lock.txt
```

### Regenerating or Updating the Lockfile
When adding or updating development dependencies:
1. Update direct constraints in `requirements-dev.txt`.
2. In a clean Python virtual environment, install the direct dependencies:
   ```bash
   pip install -r requirements-dev.txt
   ```
3. Export the deterministic dependency graph:
   ```bash
   pip freeze --all | grep -E "^(attrs|iniconfig|jsonschema|jsonschema-specifications|packaging|pluggy|Pygments|pytest|referencing|rpds-py|typing_extensions)==" | sort > requirements-lock.txt
   cp requirements-lock.txt requirements.lock
   ```
4. Run full repository verification:
   ```bash
   pytest
   python3 scripts/validate_datasets.py
   python3 scripts/repo_health.py --run-validation --run-tests
   ```
