# Architectural clearance candidates — incomplete

The four selectors now contain accessible two-stud-wide architectures rather than dense preview-only buildings. The gripper CAD, arm joint stops, build site, physical jaw travel and 12-brick replenishing tray are unchanged.

- Garden pavilion: 48 bricks, three open glazed colonnades, white lintels and green stepped gables.
- Terraced monument: 42 bricks, four receding sandstone/terracotta terraces in three bays.
- City skyline: 48 bricks, five towers of differing heights, glazed elevations and gold crowns.
- Grand citadel: 60 bricks, three gate arcades, white stone piers and raised tan battlements.

The bays leave 40 mm of lateral clearance between their nominal two-stud footprints. Each height is assembled from the central bay outward. Every pickup presents a two-stud face. Courses above doorways overlap their piers; towers and bays intentionally remain separate rather than adding ungrippable cross-lane connectors.

## Checked

`npm run test:motion`: 30 passing tests. Every architecture completes the shared-clock trajectory harness at 0.5x, 1x and 4x, with no reported obstacle collisions. Tests include CAD jaw contact, two-sided pinch rejection, intermediate IK reach and joint limits, intentionally blocked/undersized/unreachable layouts, supply separation and reuse, and complete placement order.

`npm run build`: passed. Desktop Playwright selector and finished-preview tests: 2 passed. All four screenshots were inspected. Browser previews are not evidence of complete physical assembly.

The simulator now rejects one-sided CAD contact and checks its conservative tool and carried-brick envelopes against supplied/placed obstacles on every build step. This supplements Cannon, which does not resolve kinematic-versus-static pairs.

## Remaining release blocker

The existing simulator sets a picked brick to `KINEMATIC`, stores its wrist-relative pose, and reapplies that pose throughout transport. The trajectory test explicitly uses an ideal grasp. These mechanisms do not demonstrate friction-only retention; claiming they satisfy the requested prohibition on invisible grips would be misleading.

Exploratory free-body pinch tests did not establish reliable retention. Those experiments were removed from the candidate implementation rather than changing friction, allowing a dropped brick to count as held, or replacing the established physics with an unvalidated solver. Scratch investigation files remain in `/tmp/robot-arm-pinch-investigation` for diagnosis; they are exploratory, not regression coverage or proof that the hardware cannot work.

The free-body grasp, complete browser assembly under that grasp, and tray-refill observation during those assemblies remain unverified. Corey explicitly authorized committing, pushing and deploying these candidates after reviewing this limitation. Publication does not establish friction-only retention; this release must not be described as a finished physical-gripper redesign.
