from __future__ import annotations

from build123d import Align, Box, BuildPart, BuildSketch, Locations, Mode, Plane, RectangleRounded, add, loft

try:
    from models.bicep_arm_link import MOTOR_SHAFT_Z, TOP_PIVOT_Z
    from models.common import assert_printable_extent, export_model
except ModuleNotFoundError:
    from bicep_arm_link import MOTOR_SHAFT_Z, TOP_PIVOT_Z
    from common import assert_printable_extent, export_model


PART_NAME = "bicep_elbow_belt_snap_cover"

# The cover sits on the negative-X (pulley) side of the M-link.  The changing
# X envelope follows the flush motor plate at the bottom and the wider elbow
# clevis at the top.
WALL_THICKNESS = 2.4
BELT_CLEARANCE = 2.0
COVER_BOTTOM_Z = MOTOR_SHAFT_Z - 30.0
COVER_TOP_Z = TOP_PIVOT_Z + 23.0
COVER_FRONT_X_LOWER = -18.5
COVER_FRONT_X_UPPER = -25.5
COVER_REAR_X_LOWER = -9.8
COVER_REAR_X_UPPER = -13.2
LOWER_OUTER_WIDTH_Y = 43.0
UPPER_OUTER_WIDTH_Y = 68.0

SNAP_ARM_THICKNESS_X = 1.8
SNAP_ARM_WIDTH_Y = 7.0
SNAP_ARM_LENGTH_Z = 16.0
SNAP_HOOK_PROJECTION_X = 1.2
SNAP_FIT_CLEARANCE = 0.35
SNAP_PAIR_Y = 13.0


def _section(
    z: float,
    front_x: float,
    rear_x: float,
    width_y: float,
):
    depth_x = rear_x - front_x
    if depth_x <= 0:
        raise ValueError("Bicep belt cover section has no depth.")
    with BuildSketch(Plane.XY.offset(z)) as section:
        with Locations(((front_x + rear_x) / 2, 0)):
            RectangleRounded(depth_x, width_y, min(3.2, depth_x / 2 - 0.05))
    return section.sketch


def _add_outer_envelope() -> None:
    stations = (
        (COVER_BOTTOM_Z, COVER_FRONT_X_LOWER, COVER_REAR_X_LOWER, LOWER_OUTER_WIDTH_Y),
        (MOTOR_SHAFT_Z + 22.0, COVER_FRONT_X_LOWER, COVER_REAR_X_LOWER, LOWER_OUTER_WIDTH_Y),
        (
            (MOTOR_SHAFT_Z + TOP_PIVOT_Z) / 2,
            (COVER_FRONT_X_LOWER + COVER_FRONT_X_UPPER) / 2,
            (COVER_REAR_X_LOWER + COVER_REAR_X_UPPER) / 2,
            (LOWER_OUTER_WIDTH_Y + UPPER_OUTER_WIDTH_Y) / 2,
        ),
        (TOP_PIVOT_Z, COVER_FRONT_X_UPPER, COVER_REAR_X_UPPER, UPPER_OUTER_WIDTH_Y),
        (COVER_TOP_Z, COVER_FRONT_X_UPPER, COVER_REAR_X_UPPER, UPPER_OUTER_WIDTH_Y),
    )
    loft([_section(z, front_x, rear_x, width_y) for z, front_x, rear_x, width_y in stations])


def _cut_open_back_cavity() -> None:
    # Extending the cavity through the rear makes the link-facing side fully
    # open.  The remaining front skin and perimeter are one printable shell.
    stations = (
        (
            COVER_BOTTOM_Z + WALL_THICKNESS,
            COVER_FRONT_X_LOWER + WALL_THICKNESS,
            COVER_REAR_X_LOWER + BELT_CLEARANCE,
            LOWER_OUTER_WIDTH_Y - 2 * WALL_THICKNESS,
        ),
        (
            MOTOR_SHAFT_Z + 22.0,
            COVER_FRONT_X_LOWER + WALL_THICKNESS,
            COVER_REAR_X_LOWER + BELT_CLEARANCE,
            LOWER_OUTER_WIDTH_Y - 2 * WALL_THICKNESS,
        ),
        (
            (MOTOR_SHAFT_Z + TOP_PIVOT_Z) / 2,
            (COVER_FRONT_X_LOWER + COVER_FRONT_X_UPPER) / 2 + WALL_THICKNESS,
            (COVER_REAR_X_LOWER + COVER_REAR_X_UPPER) / 2 + BELT_CLEARANCE,
            (LOWER_OUTER_WIDTH_Y + UPPER_OUTER_WIDTH_Y) / 2 - 2 * WALL_THICKNESS,
        ),
        (
            TOP_PIVOT_Z,
            COVER_FRONT_X_UPPER + WALL_THICKNESS,
            COVER_REAR_X_UPPER + BELT_CLEARANCE,
            UPPER_OUTER_WIDTH_Y - 2 * WALL_THICKNESS,
        ),
        (
            COVER_TOP_Z - WALL_THICKNESS,
            COVER_FRONT_X_UPPER + WALL_THICKNESS,
            COVER_REAR_X_UPPER + BELT_CLEARANCE,
            UPPER_OUTER_WIDTH_Y - 2 * WALL_THICKNESS,
        ),
    )
    loft(
        [_section(z, front_x, rear_x, width_y) for z, front_x, rear_x, width_y in stations],
        mode=Mode.SUBTRACT,
    )


def _add_snap_pair(*, rear_x: float, z: float, hook_toward_positive_x: bool) -> None:
    """Add two compliant face-contact fingers at one green attachment zone."""
    arm_center_x = rear_x - SNAP_ARM_THICKNESS_X / 2
    for y in (-SNAP_PAIR_Y, SNAP_PAIR_Y):
        with Locations((arm_center_x, y, z)):
            Box(
                SNAP_ARM_THICKNESS_X,
                SNAP_ARM_WIDTH_Y,
                SNAP_ARM_LENGTH_Z,
                align=(Align.CENTER, Align.CENTER, Align.CENTER),
            )
        hook_center_x = rear_x + (SNAP_HOOK_PROJECTION_X / 2 if hook_toward_positive_x else -SNAP_HOOK_PROJECTION_X / 2)
        hook_z = z + (SNAP_ARM_LENGTH_Z / 2 - 1.3 if hook_toward_positive_x else -SNAP_ARM_LENGTH_Z / 2 + 1.3)
        with Locations((hook_center_x, y, hook_z)):
            Box(
                SNAP_HOOK_PROJECTION_X,
                SNAP_ARM_WIDTH_Y,
                2.6,
                align=(Align.CENTER, Align.CENTER, Align.CENTER),
            )


def build_model():
    if WALL_THICKNESS < 2.0:
        raise ValueError("Snap cover wall is too thin for a durable FDM print.")
    if SNAP_FIT_CLEARANCE <= 0:
        raise ValueError("Snap fit needs positive assembly clearance.")

    with BuildPart() as cover:
        _add_outer_envelope()
        _cut_open_back_cavity()
        _add_snap_pair(
            rear_x=COVER_REAR_X_LOWER,
            z=MOTOR_SHAFT_Z - 13.0,
            hook_toward_positive_x=True,
        )
        _add_snap_pair(
            rear_x=COVER_REAR_X_UPPER,
            z=TOP_PIVOT_Z + 10.0,
            hook_toward_positive_x=False,
        )

    model = cover.part
    model.label = PART_NAME
    bbox = model.bounding_box().size
    assert_printable_extent((bbox.X, bbox.Y, bbox.Z))
    return model


def main() -> None:
    part = build_model()
    export_model(part, PART_NAME)

    try:
        from ocp_vscode import show
    except ImportError:
        return
    show(part)


if __name__ == "__main__":
    main()
