# Billy Bitcoin's Robot Arm Build Lab

Public monorepo for the robot arm CAD source, build notes, automation, and static workshop dashboard deployed at `/robot-arm/`.

## Layout

- `models/`: build123d source for printable parts and the current master assembly.
- `tests/`: CAD regression tests and generated metadata checks.
- `scripts/`: local and CI automation for CAD exports, catalog generation, and public progress feeds.
- `content/`: build logs, design decisions, print logs, photos, and pipeline notes.
- `site/`: Vite + React + TypeScript static dashboard with a Three.js model viewer.
- `.github/workflows/`: CI for CAD/test/site build and deployment scaffolding.

Generated STEP/STL/glTF/render files are not committed by default. CI regenerates them from source, uploads heavyweight files as Actions artifacts, and copies small JSON/web assets into the static site build.

## Local CAD

```bash
UV_CACHE_DIR=.uv-cache UV_PYTHON_INSTALL_DIR=.uv-python uv sync
uv run pytest
uv run python scripts/generate_catalog.py
uv run python scripts/export_models.py
```

`scripts/generate_catalog.py` writes `site/public/generated/catalog.json` and `site/public/generated/viewer-model.json` for the dashboard. `scripts/export_models.py` writes STEP/STL exports to `models/out/`.

## Local Site

```bash
cd site
npm install
npm run build
npm run smoke
```

The site is built with `base: "/robot-arm/"` and uses bundled assets only.

## Deployment

The `deploy.yml` workflow builds on `main` and includes an explicit `production` GitHub Environment gate before syncing `site/dist/` to Helios:

`/var/www/billybitcoin.cloud/html/robot-arm/`

First production deployment should be approved manually after checking a dry run or staging output.
