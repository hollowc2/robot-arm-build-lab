# Sorting Factory

## Current Experience

The landing page at `/robot-arm/` runs the CAD arm as a Three.js/cannon-es simulation. **Factory** and **Joints** are the only control tabs. The former LEGO Build tab, architectural previews, structure selector, supply batching, and stud-locking behavior have been removed from the active simulator.

Each batch has six rigid, stud-free cubes, 24 mm on each side: two red, two blue, and two yellow. Their physics mass is a 2 g simulation parameter, not a measured physical payload. Six fixed pickup centers sit on a 240 mm radius at 60° intervals. The three trays sit at a 300 mm radius, centered at 60°, 180°, and 300°. Each tray has two target positions offset by ±8° from its center angle. Tray rims are 4 mm high and have matching physics collision bodies. The outlined pickup slots are flat visual markers.

The planner already knows each block's color and pose. There is no camera, random-pile perception, or autonomous color detection. Shuffle changes the color assignment while keeping the six pickup centers fixed.

## Controls and Lifecycle

- On mesh load, sorting starts automatically unless the browser requests reduced motion. Reduced motion leaves the batch idle with **Start sorting** available.
- **Shuffle & sort** stops the old batch, clears its deliveries, opens and homes the simulated arm, creates a new color arrangement, and starts immediately. It also clears a paused state.
- **Pause / Resume** freezes or resumes the shared simulation clock, including the arm, held block, and physics.
- **Joints** opens the manual controls. Selecting the tab alone does not stop sorting. Moving a slider, using Home, or giving gamepad input takes over and stops the automatic sequence.
- Opening the gripper during manual control releases a held block. **Start sorting** restarts the current batch from its supply positions after a stop; it does not resume a partially completed sequence.
- A completed batch parks the arm and waits. **Shuffle & sort** starts the next batch.
- Speed scales from 0.5× to 4×, initially 1×. The fixed simulation step is 1/120 second. Long frame gaps are capped rather than replayed as a burst.

Each block follows approach, lower, grip, lift, carry, align, place, release, and retract stages. The planner uses a 70 mm grip-height waypoint for carrying. Grip contact uses the exported finger triangles rather than accepting a pickup based only on proximity. A missed grasp, failed delivery, or stalled step stops the sequence and reports the failure.

## Delivery and Physics

A factory delivery is accepted at release when the entire rotated block fits inside the matching tray's clear interior: ±64 mm across and ±34 mm along the tray's local axes. The block center must also be near the floor, between half its height minus 2 mm and half its height plus 5 mm. Small yaw and position differences are allowed; there is no stud alignment or snap-to-target operation.

Delivered blocks remain dynamic physics bodies. Progress records accepted releases; it is not a continuous vision check of whether a block remains in its tray afterward. Foam elasticity, crushing, real friction variability, motor torque, and physical grip reliability are not validated by this simulation.

## Source Map

- `site/src/Simulator.tsx`: scene, CAD mesh loading, physics bodies, tray collisions, CAD-based grasp/release, controls, and displayed progress.
- `site/src/sortPlan.ts`: colors, cube dimensions, fixed layout, shuffle, waypoint planning, and `insideSortBin` delivery checks.
- `site/src/waypoints.ts`: grip offset, approach opening, stage labels, and straight-line inverse-kinematics following shared with the regression fixtures.
- `site/src/buildRunner.ts`: shared joint driver and sequence state machine. The historical `BuildSequencer` name is internal; it does not imply a Build tab.
- `site/src/arm.ts`, `gripper.ts`, and `grasp.ts`: joint limits, linkage geometry, inverse kinematics, and CAD finger contact.
- `site/src/simClock.ts`: fixed-step clock, speed scaling, pause, and frame-gap handling.

Historical `bricks.ts`, `buildPlan.ts`, `brickMesh.ts`, and headless building fixtures remain in the source tree. Shared types and headless fixtures still support motion regressions; `brickMesh.ts` is a legacy mesh helper unused by the active simulator. The active factory does not import the LEGO preset or mesh-generation code at runtime. Do not restore a Build view merely because these internal files still exist.

## Verification

Generate or restore validated CAD meshes, install site dependencies and the Playwright browser, then run from `site/`:

```bash
npm run build
npm run test:motion
npm run smoke -- --workers=1
```

For a focused factory browser check:

```bash
npx playwright test tests/sort.spec.ts --workers=1
```

`tests/sort.test.mjs` checks repeated reachable layouts, non-overlap, fixed pickup positions, upright poses, consistent carried transforms, CAD jaw contact and release clearance, tray access, and acceptance/rejection of bin deliveries. `tests/sort.spec.ts` covers default startup, complete batches, per-bin counts, shuffle, manual takeover, reduced-motion startup, and the two-tab UI. `tests/smoke.spec.ts` checks manual motion and release, pause, mid-batch shuffle, the part viewer, mobile off-screen controls, the absence of Build controls, and the legacy URL redirect.

## Physical Implementation Boundary

The website is not a hardware controller and does not send these waypoints to the Uno or ESP32. General hardware point-to-point motion remains disabled pending calibration, as described in [the firmware README](../firmware/README.md).

Before selecting real blocks or running a tabletop factory, measure the usable gripper opening, verify jaw contact and release on the chosen material, validate tray/finger clearances, and record repeated successful transfers. A simulator pass does not establish physical readiness or change any requirement in [the safety checklist](../content/safety-validation.md).
