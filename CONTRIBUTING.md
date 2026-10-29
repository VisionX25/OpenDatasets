# Contributing to OpenDatasets

Thank you for helping make dataset information easier to discover and check.

## Choose a contribution

- Suggest a dataset using the dataset suggestion issue form.
- Correct metadata with a link to an authoritative source.
- Report a reproducible UI bug or propose an improvement.
- Improve documentation or help with an open roadmap issue.

Search existing issues and catalog entries before starting. For larger changes, discuss the approach in an issue first.

## Local setup

Fork the repository, clone your fork, and create a focused branch. Use Python 3.10+ and a supported Node version compatible with the locked frontend dependencies (Node 22.12+ or 24 recommended).

From the repository root:

```bash
python3 -m pip install -r requirements-dev.txt
cd frontend
npm ci
npm run dev
```

The frontend development command regenerates the catalog using Python. See [README](README.md) for the architecture and additional commands.

## Add or correct a dataset

1. Check `data/datasets/` for an existing entry and choose unique IDs and slugs.
2. Follow `schemas/dataset.v1.schema.json`; use an existing entry as a structural example, not as evidence for factual values.
3. Use the original publisher's website, documentation, or paper for names, counts, splits, licenses, dates, and collection details.
4. Include source references and accurate verification information. Preserve explicit unknown or unspecified states when a source does not establish a value. Do not guess a license or verification date.
5. Do not mark a dataset as open merely because a download link is public. Describe restrictions and access conditions accurately.
6. Store metadata only. Do not commit raw datasets, credentials, private personal information, or material you lack permission to redistribute.
7. Regenerate and commit `frontend/public/data/catalog.json` along with the source record.

Metadata verification means checking documented claims against sources. The offline validator checks structure and URL syntax; it does not check live links or audit the underlying dataset's quality, bias, or labels.

## Validate your change

From the repository root:

```bash
python3 scripts/validate_datasets.py
python3 scripts/generate_catalog.py
pytest
cd frontend
npm test
npm run lint
npm run build
```

For documentation-only changes, check spelling, links, and command accuracy; explain in the PR when runtime checks were not applicable. For UI changes, include screenshots at desktop and mobile sizes and keyboard-navigation observations. For data changes, cite the sources you checked.

## Submit a pull request

- Keep each PR focused and explain the user-visible change.
- Link the related issue, when there is one.
- Include validation results and any remaining limitations.
- Respond respectfully to review feedback.
- Wait for applicable CI checks before requesting a merge.

The application code uses the [MIT License](LICENSE). External datasets keep their original licenses; catalog inclusion does not change their terms.

