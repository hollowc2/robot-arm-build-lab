# Billy Bitcoin's Robot Arm Build Lab

Public monorepo for the robot arm CAD source, build notes, automation, and the static landing page deployed at `/robot-arm/`.

This repository root is `robot-arm-build-lab/`. If there is a sibling
`../models/` directory under `RobotArm/`, treat it as legacy scratch/archive
content; the canonical CAD source lives in this repo's `models/` directory.

## Layout

- `models/`: build123d source for printable parts and the current master assembly.
- `tests/`: CAD regression tests and generated metadata checks.
- `scripts/`: local and CI automation for CAD exports, catalog generation, and public progress feeds.
- `content/`: build logs, design decisions, print logs, photos, and pipeline notes.
- `site/`: Vite + React + TypeScript single-page site: a live Three.js/cannon-es simulator as the hero, plus anatomy, part viewer, process, and build log sections.
- `.github/workflows/`: CI for CAD/test/site build and deployment scaffolding.

Generated STEP/STL/glTF/render files are not committed by default. CI builds or restores validated CAD exports, uploads heavyweight files as Actions artifacts, and copies small JSON/web assets into the static site build.

## Local CAD

```bash
UV_CACHE_DIR=.uv-cache UV_PYTHON_INSTALL_DIR=.uv-python uv sync
uv run python -m pytest
uv run python scripts/generate_catalog.py
uv run python scripts/export_models.py
```

`scripts/generate_catalog.py` writes `site/public/generated/catalog.json` (the part list on the site) and `site/public/generated/viewer-model.json`. `scripts/export_models.py` writes STEP/STL exports to `models/out/`.

To rebuild only the full arm assembly:

```bash
uv run python models/master_assembly.py
```

That command updates `models/out/robot_arm_master_assembly.step` and `models/out/robot_arm_master_assembly.stl`.

To refresh the website after changing any model:

```bash
uv run python scripts/generate_catalog.py
uv run python scripts/generate_progress_feed.py
uv run python scripts/export_models.py
uv run python scripts/publish_web_models.py
cd site && npm run build
```

The export also creates the rigid-link `simulator_*` meshes used by the simulator at the top of `/robot-arm/`. The old `/robot-arm/simulator/` URL redirects there.

The simulator builds small interlocking-brick models. Presets are plain data in `site/src/bricks.ts` (brick type, color, grid cell, rotation, listed in assembly order); `site/src/buildPlan.ts` turns one into supply positions and arm waypoints and rejects layouts that are unsupported, out of reach, or would put the gripper through another brick. `npm run test:motion` (in `site/`) checks every preset headlessly at 0.5×, 1× and 4×; `BUILD_MATRIX=1 npx playwright test tests/build.spec.ts --project=desktop` runs the same builds in a GPU-backed browser.

## Current CAD Notes

- The base drive uses a 120T module-1 herringbone gear driven by a 20T NEMA17 pinion at a 70 mm center distance.
- The 120T gear's six M3 turntable holes are clocked to match the azimuth turntable and include bottom-side counterbores so hardware can sit below the gear when bolting up into the turntable.
- The geared base stator carries the fixed center boss/bearing stack; keep the 120T gear center bore and vertical stack clear of that boss when adjusting the base assembly.
- The shoulder and elbow driven pulleys are held by four M3 screws that drive from counterbores in the link (bicep at the shoulder, forearm hub at the elbow) into the pulley's thread holes, so the heads stay inside the clevis. The 8 mm and 5 mm steel shafts, not these screws, carry each joint.
- At the wrist, the gripper tongue sits snug on the 5 mm shaft, which turns in the forearm's two 625 bearings; the 32T pulley's four M3 screws thread into the tongue. The 28BYJ-48 stands 2 mm off the forearm plate on slotted ear pads so its front boss clears the 20T pulley and its shaft ends 8 mm into the pulley bore.
- `models/master_assembly.py` supports `mechanical` and `service` configurations. The default remains `mechanical`.
- The electronics enclosure is a prototype until physical fit, temperature, and interlock tests are recorded.

## Child-Facing Safety Boundary

This is an adult-supervised educational machine, not a certified toy. Do not energize it around children until the transmission guards, electronics enclosure, normally-closed limits, guard interlocks, external motor-power E-stop, current limits, homing, and bounded demonstration mode have all passed the checks in `content/safety-validation.md`.

The Uno R4 owns motion safety. The ESP32 may provide a user interface but cannot directly enable drivers. Firmware opening an enable pin is secondary protection: the latching E-stop must interrupt 12 V motor power using appropriately rated external hardware.

## Local Site

```bash
cd site
npm install
npm run build
npm run smoke
```

The site is built with `base: "/robot-arm/"` and uses bundled assets only.

## Faster Iteration

For a site-only edit, reuse your existing `site/public/generated/models/` meshes and run the site build, motion tests, and smoke tests. Regenerate the meshes when CAD sources or export scripts change.

For a CAD edit, run the affected tests first, then the complete suite before opening a PR:

```bash
uv run python -m pytest tests/test_robot_parts.py -k wrist
uv run python -m pytest
```

Always invoke pytest through `python -m pytest`; the environment's standalone pytest launcher may have a stale shebang. Run the full CAD suite and master-assembly exports sequentially, never together on the same machine. The tests build one master assembly per session and give each test an independent deep copy.

CI restores CAD exports only on an exact cache-key match. The key includes Python sources under `models/`, `scripts/`, and `tests/`, all firmware files, `pyproject.toml`, `uv.lock`, and the CI workflow, plus the runner platform and Python version family. Any changed input or missing cache runs the full CAD suite and regenerates exports. When introducing CAD input files outside these paths, extend the key before relying on reuse. Catalog and progress JSON regenerate for every revision; the site build, motion tests, and desktop/mobile smoke checks always run.

Caches from a PR are scoped to that PR; main must populate its own cache after merge. New commits cancel older CI runs for the same PR. Main runs are retained so deployment can consume their tested artifacts.

CI runs smoke tests with one browser worker so desktop and mobile software WebGL do not compete for CPU on the same runner. Both projects keep their original assertions and timeouts.

## Deployment

After successful CI for a push to `main`, `deploy.yml` downloads that run's tested `robot-arm-site-dist` artifact. It skips failed CI, PR runs, and revisions superseded on main before preparing deployment. It uses the `production` GitHub Environment before syncing the bundle to Helios:

`/var/www/billybitcoin.cloud/html/robot-arm/`

Manual `workflow_dispatch` retains the rebuild option, with `dry_run` defaulting to true. A deployed run retains its own site artifact, so rerunning its deploy job can restore that bundle while the artifact remains available.

Required `production` environment secrets:

- `HELIOS_HOST`: Helios hostname or IP address.
- `HELIOS_USER`: SSH username only, for example `billy`.
- `HELIOS_SSH_KEY`: Private SSH key for that user.
- `TS_AUTHKEY`: Ephemeral reusable Tailscale auth key that lets GitHub Actions join the tailnet.

Set them with:

```bash
gh secret set HELIOS_HOST --repo hollowc2/robot-arm-build-lab --env production
gh secret set HELIOS_USER --repo hollowc2/robot-arm-build-lab --env production
gh secret set HELIOS_SSH_KEY --repo hollowc2/robot-arm-build-lab --env production < /path/to/private-key
gh secret set TS_AUTHKEY --repo hollowc2/robot-arm-build-lab --env production
```

`HELIOS_HOST` should be the Helios Tailscale IP or MagicDNS name. `HELIOS_USER` should not include a host, `@`, `:`, whitespace, or key contents. Create `TS_AUTHKEY` in the Tailscale admin console as an ephemeral reusable auth key.

First production deployment should be approved manually after checking a dry run or staging output.
