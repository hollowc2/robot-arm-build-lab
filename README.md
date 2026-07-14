# Billy Bitcoin's Robot Arm Build Lab

Public monorepo for the robot arm CAD source, build notes, automation, and static workshop dashboard deployed at `/robot-arm/`.

This repository root is `robot-arm-build-lab/`. If there is a sibling
`../models/` directory under `RobotArm/`, treat it as legacy scratch/archive
content; the canonical CAD source lives in this repo's `models/` directory.

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

The export also creates the rigid-link meshes used by `/robot-arm/simulator/`.

## Current CAD Notes

- The base drive uses a 120T module-1 herringbone gear driven by a 20T NEMA17 pinion at a 70 mm center distance.
- The 120T gear's six M3 turntable holes are clocked to match the azimuth turntable and include bottom-side counterbores so hardware can sit below the gear when bolting up into the turntable.
- The geared base stator carries the fixed center boss/bearing stack; keep the 120T gear center bore and vertical stack clear of that boss when adjusting the base assembly.
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

## Deployment

The `deploy.yml` workflow builds on `main` and includes an explicit `production` GitHub Environment gate before syncing `site/dist/` to Helios:

`/var/www/billybitcoin.cloud/html/robot-arm/`

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
