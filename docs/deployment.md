# GitHub Pages demo

The demo uses the repository's GitHub Pages environment. In repository Settings →
Pages, set **Source: GitHub Actions**. The `Publish demo` workflow builds and
publishes on pushes to `main` and can also be run manually.

## Build locally

Use Node 24, Python 3.11, and the locked frontend dependencies:

```bash
python3 -m pip install -r requirements-dev.txt
cd frontend
npm ci
```

From the repository root, on Linux/macOS:

```bash
DEPLOY_BASE=/OpenDatasets/ npm run build
python3 scripts/prepare_pages.py
```

On PowerShell, set `$env:DEPLOY_BASE = '/OpenDatasets/'` before `npm run build`.
Run `python scripts/prepare_pages.py` with the Python interpreter you installed.

The output is `frontend/dist`. Asset and catalog URLs use Vite's base URL, and
React Router uses the matching basename. Do not hard-code root `/data/` paths.

## Direct links and refresh

GitHub Pages does not provide a general SPA rewrite. `prepare_pages.py` emits
`index.html` entry points for explorer, About, listing, all six categories, every
catalog slug, and legacy `/datasets/:slug` paths. The legacy view canonicalizes
to `/dataset/:slug` while preserving query parameters. Add new records and rebuild
to emit their entry points automatically.

Unknown routes use `404.html` to render the app's not-found/redirect behavior.
Unknown dataset slugs display “Dataset Not Found” while preserving the HTTP 404
status on direct entry. This is intentional, not an assertion of HTTP 200 for an
unknown resource. There are no redirects through an external service.

## Release verification

After deployment, verify home, a category, search, a canonical detail link,
legacy detail links (with a query), reloads, unknown slugs, catalog loading,
keyboard navigation, and a 360px layout. See the linked GitHub issue and Actions
run for the actual deployed result; build success alone is insufficient.

## Verified deployment

Live demo: https://visionx25.github.io/OpenDatasets/

First successful run: https://github.com/VisionX25/OpenDatasets/actions/runs/40918880920

Verified home, category, MNIST search (two results), keyboard detail activation,
canonical direct entry and reload, legacy entry with query preservation, and the
unknown-slug “Dataset Not Found” view on the public deployment.
