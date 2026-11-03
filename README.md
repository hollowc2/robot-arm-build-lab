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
- `docs/`: [sorting-factory behavior and implementation](docs/sorting-factory.md) and [deployment/rollback instructions](docs/deployment.md).
- `site/`: Vite + React + TypeScript single-page site: a live Three.js/cannon-es simulator as the hero, plus anatomy, part viewer, process, and build log sections.
- `.github/workflows/`: CI for CAD, site tests, artifact publishing, and the production deployment workflow.

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

## Sorting Factory Demo

The site has two control tabs: **Factory** and **Joints**. There is no LEGO Build view or structure selector.

Six stud-free, 24 mm foam-block proxies wait at fixed pickup slots. The arm delivers two blocks each to red, blue, and yellow receiving trays. Factory shows per-bin counts and batch progress, **Shuffle & sort**, and **Pause / Resume**. **Start sorting** appears when the sequence is idle or stopped. Joint sliders, Home, and gamepad input take over manual control and stop the sequence; opening the gripper releases a held block.

Sorting starts when the CAD meshes finish loading, except when reduced motion is requested. Shuffle starts a fresh batch, resets the arm to an open home pose, and redistributes the colors across the same six pickup positions. A completed batch waits for another shuffle rather than looping automatically. Simulation speed ranges from 0.5× to 4×.

Colors and pickup poses are predefined simulator data, not camera recognition. The foam blocks are rigid physics proxies; the browser does not model foam compression or validate real grip force. Physical grip reliability and final block dimensions still need bench testing. The website does not command the real arm; firmware motion remains subject to calibration and safety validation.

See [the factory guide](docs/sorting-factory.md) for the source map, delivery checks, and test coverage.

## Current CAD Notes

- The base drive uses a 120T module-1 herringbone gear driven by a 20T NEMA17 pinion at a 70 mm center distance.
- The 120T gear's six M3 turntable holes are clocked to match the azimuth turntable and include bottom-side counterbores so hardware can sit below the gear when bolting up into the turntable.
- The geared base stator carries the fixed center boss/bearing stack; keep the 120T gear center bore and vertical stack clear of that boss when adjusting the base assembly.
- The shoulder and elbow driven pulleys are held by four M3 screws that drive from counterbores in the link (bicep at the shoulder, forearm hub at the elbow) into the pulley's thread holes, so the heads stay inside the clevis. The 8 mm and 5 mm steel shafts, not these screws, carry each joint.
- At the wrist, the gripper tongue sits snug on the 5 mm shaft, which turns in the forearm's two 625 bearings; the 32T pulley's four M3 screws thread into the tongue. The 28BYJ-48 stands 2 mm off the forearm plate on slotted ear pads so its front boss clears the 20T pulley and its shaft ends 8 mm into the pulley bore.
- Two M3 × 6 mm socket screws fasten the 28BYJ-48 ears directly into Ø2.5 mm blind pilots in the plastic pads, with 4.4 mm of engagement and no nuts. Three pilot pairs at −5, 0 and +5 mm retain the 10 mm belt-tension range in discrete positions.
- `models/master_assembly.py` supports `mechanical` and `service` configurations. The default remains `mechanical`.
- The electronics enclosure is a prototype until physical fit, temperature, and interlock tests are recorded.

## Child-Facing Safety Boundary

This is an adult-supervised educational machine, not a certified toy. Do not energize it around children until the transmission guards, electronics enclosure, normally-closed limits, guard interlocks, external motor-power E-stop, current limits, homing, and bounded demonstration mode have all passed the checks in `content/safety-validation.md`.

The Uno R4 owns motion safety. The ESP32 may provide a user interface but cannot directly enable drivers. Firmware opening an enable pin is secondary protection: the latching E-stop must interrupt 12 V motor power using appropriately rated external hardware.

## Local Site

Use Node.js 22 (the CI version). Generate the CAD web meshes first using the commands above, or reuse an existing validated `site/public/generated/models/` directory. A fresh npm install does not generate meshes.

```bash
cd site
npm ci
npx playwright install chromium
npm run dev
```

Open `http://127.0.0.1:5173/robot-arm/`. Vite can select another port if 5173 is occupied. For validation, run from `site/`:

```bash
npm run build
npm run test:motion
npm run smoke -- --workers=1
```

Playwright starts its own local Vite server on port 4174 and runs desktop and mobile checks. Linux hosts without browser system dependencies may need `npx playwright install --with-deps chromium` instead of the browser-only install above.

`test:motion` covers the shared joint driver, CAD finger contact, factory layouts, and bin-delivery rules. It also retains historical headless building fixtures as motion regressions; these do not expose a LEGO demo in the application. Browser tests cover factory completion, shuffle, pause/resume, manual pickup/release, reduced motion, mobile controls, and the part viewer. The removed LEGO browser suites are no longer part of the site.

The site is built with `base: "/robot-arm/"` and uses bundled assets only. The old `/robot-arm/simulator/` URL redirects to the main page.

## Faster Iteration

For a site-only edit, reuse your existing `site/public/generated/models/` meshes and run the site build, motion tests, and smoke tests. Regenerate the meshes when CAD sources or export scripts change.

For a CAD edit, run the affected tests first, then the complete suite before opening a PR:

```bash
uv run python -m pytest tests/test_robot_parts.py -k wrist
uv run python -m pytest
```

Always invoke pytest through `python -m pytest`; the environment's standalone pytest launcher may have a stale shebang. Run the full CAD suite and master-assembly exports sequentially, never together on the same machine. The tests build one master assembly per session and give each test an independent deep copy.

CI restores CAD exports only on an exact cache-key match. The key includes Python sources under `models/`, `scripts/`, and `tests/`, `site/src/arm.ts`, all firmware files, `pyproject.toml`, `uv.lock`, and the CI workflow, plus the runner platform and Python version family. Any changed input or missing cache runs the full CAD suite and regenerates exports. When introducing CAD input files outside these paths, extend the key before relying on reuse. Catalog and progress JSON regenerate for every revision; the site build, motion tests, and desktop/mobile smoke checks always run.

Caches from a PR are scoped to that PR; main must populate its own cache after merge. New commits cancel older CI runs for the same PR. Main runs are retained so deployment can consume their tested artifacts.

CI runs smoke tests with one browser worker so desktop and mobile software WebGL do not compete for CPU on the same runner. Both projects keep their original assertions and timeouts.

## Deployment

The public site is [billybitcoin.cloud/robot-arm/](https://billybitcoin.cloud/robot-arm/), served from `/var/www/billybitcoin.cloud/html/robot-arm/` on Helios.

After successful push CI on `main`, `.github/workflows/deploy.yml` downloads that run's tested `robot-arm-site-dist` artifact and deploys through the `production` GitHub Environment. It skips failed CI, PR runs, and revisions already superseded when preparing the release. Manual `workflow_dispatch` rebuilds the site and defaults to a dry run; it does not run the full CI test suite itself.

The workflow needs `HELIOS_HOST`, `HELIOS_USER`, `HELIOS_SSH_KEY`, and `TS_AUTHKEY` in the production environment. A successful CI run does not prove deployment succeeded: the deployment job and public page must also be checked. The factory rollout used the direct SSH fallback after the Actions Tailscale join failed with an invalid key.

See [deployment and rollback](docs/deployment.md) for environment setup, the approved direct SSH procedure, release identification, and public validation. This is a static-file deployment; it needs no Nginx restart, container rebuild, database change, or robot firmware update.
