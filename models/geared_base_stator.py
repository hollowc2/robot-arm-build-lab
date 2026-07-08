from __future__ import annotations

from build123d import (
    Align,
    Axis,
    Box,
    BuildPart,
    BuildSketch,
    Circle,
    Cylinder,
    GridLocations,
    Locations,
    Mode,
    Part,
    Plane,
    chamfer,
    extrude,
)

try:
    from models.common import (
        BASE_GEAR_CENTER_DISTANCE,
        BEARING_608_ID,
        BEARING_608_OD,
        BEARING_608_WIDTH,
        DESK_MOUNT_CLEARANCE,
        M3_CLEARANCE,
        M3_COUNTERBORE,
        M3_COUNTERBORE_DEPTH,
        NEMA17_BODY,
        NEMA17_HOLE_SPACING,
        NEMA17_PILOT,
        NEMA17_SHAFT,
        assert_printable_extent,
        export_model,
    )
    from models.nema17_stepper_motor import BODY_DEPTH as NEMA17_BODY_DEPTH
    from models.nema17_stepper_motor import REAR_CAP_DEPTH as NEMA17_REAR_CAP_DEPTH
except ModuleNotFoundError:
    from common import (
        BASE_GEAR_CENTER_DISTANCE,
        BEARING_608_ID,
        BEARING_608_OD,
        BEARING_608_WIDTH,
        DESK_MOUNT_CLEARANCE,
        M3_CLEARANCE,
        M3_COUNTERBORE,
        M3_COUNTERBORE_DEPTH,
        NEMA17_BODY,
        NEMA17_HOLE_SPACING,
        NEMA17_PILOT,
        NEMA17_SHAFT,
        assert_printable_extent,
        export_model,
    )
    from nema17_stepper_motor import BODY_DEPTH as NEMA17_BODY_DEPTH
    from nema17_stepper_motor import REAR_CAP_DEPTH as NEMA17_REAR_CAP_DEPTH


PART_NAME = "geared_base_stator"

BASE_SIZE = 160.0
BASE_THICKNESS = 8.0
CORNER_HOLE_SPACING = 140.0

THRUST_RING_OD = 100.0
THRUST_RING_ID = 72.0
THRUST_RING_HEIGHT = 2.2

BEARING_BOSS_OD = 46.0
BEARING_BOSS_HEIGHT = 26.0
BEARING_POCKET_DEPTH = (2 * BEARING_608_WIDTH) + 0.4
SHAFT_CLEARANCE = BEARING_608_ID + 0.5

MOTOR_PILOT_CLEARANCE = NEMA17_PILOT + 0.6
MOTOR_SHAFT_CLEARANCE = NEMA17_SHAFT + 3.0
MOTOR_TAB_SIZE = NEMA17_BODY + 12.0

MOTOR_BOTTOM_CLEARANCE = 2.0
BASE_MOTOR_FACE_Z = 0.0  # Motor mounts directly to the bottom face
FOOT_HEIGHT = NEMA17_BODY_DEPTH + NEMA17_REAR_CAP_DEPTH - BASE_MOTOR_FACE_Z + MOTOR_BOTTOM_CLEARANCE
FOOT_OD = BASE_SIZE - CORNER_HOLE_SPACING


def build_model() -> Part:
    """Build the stationary geared base stator."""
    motor_x = BASE_GEAR_CENTER_DISTANCE
    top_z = BASE_THICKNESS
    boss_top_z = top_z + BEARING_BOSS_HEIGHT

    assert_printable_extent((BASE_SIZE, BASE_SIZE, FOOT_HEIGHT + boss_top_z))

    with BuildPart() as stator:
        with GridLocations(CORNER_HOLE_SPACING, CORNER_HOLE_SPACING, 2, 2):
            Cylinder(
                FOOT_OD / 2,
                FOOT_HEIGHT,
                align=(Align.CENTER, Align.CENTER, Align.MAX),
            )

        Box(
            BASE_SIZE,
            BASE_SIZE,
            BASE_THICKNESS,
            align=(Align.CENTER, Align.CENTER, Align.MIN),
        )

        with Locations((motor_x, 0, 0)):
            Box(
                MOTOR_TAB_SIZE,
                MOTOR_TAB_SIZE,
                BASE_THICKNESS,
                align=(Align.CENTER, Align.CENTER, Align.MIN),
            )

        with GridLocations(CORNER_HOLE_SPACING, CORNER_HOLE_SPACING, 2, 2):
            Cylinder(
                DESK_MOUNT_CLEARANCE / 2,
                BASE_THICKNESS + FOOT_HEIGHT + 0.5,
                align=(Align.CENTER, Align.CENTER, Align.MAX),
                mode=Mode.SUBTRACT,
            )

        with Locations((0, 0, top_z)):
            Cylinder(
                THRUST_RING_OD / 2,
                THRUST_RING_HEIGHT,
                align=(Align.CENTER, Align.CENTER, Align.MIN),
            )
            Cylinder(
                THRUST_RING_ID / 2,
                THRUST_RING_HEIGHT + 0.4,
                align=(Align.CENTER, Align.CENTER, Align.MIN),
                mode=Mode.SUBTRACT,
            )

        with Locations((0, 0, top_z)):
            Cylinder(
                BEARING_BOSS_OD / 2,
                BEARING_BOSS_HEIGHT,
                align=(Align.CENTER, Align.CENTER, Align.MIN),
            )

        with Locations((0, 0, -0.5)):
            Cylinder(
                SHAFT_CLEARANCE / 2,
                boss_top_z + 1.0,
                align=(Align.CENTER, Align.CENTER, Align.MIN),
                mode=Mode.SUBTRACT,
            )

        with Locations((0, 0, boss_top_z - BEARING_POCKET_DEPTH)):
            Cylinder(
                BEARING_608_OD / 2,
                BEARING_POCKET_DEPTH + 0.2,
                align=(Align.CENTER, Align.CENTER, Align.MIN),
                mode=Mode.SUBTRACT,
            )

        # Cutout for the NEMA 17 front pilot boss (bottom-up)
        with Locations((motor_x, 0, -0.1)):
            Cylinder(
                MOTOR_PILOT_CLEARANCE / 2,
                2.4,
                align=(Align.CENTER, Align.CENTER, Align.MIN),
                mode=Mode.SUBTRACT,
            )

        # Clearance for the motor shaft to pass through
        with Locations((motor_x, 0, -0.5)):
            Cylinder(
                MOTOR_SHAFT_CLEARANCE / 2,
                BASE_THICKNESS + 1.0,
                align=(Align.CENTER, Align.CENTER, Align.MIN),
                mode=Mode.SUBTRACT,
            )

        motor_hole_offset = NEMA17_HOLE_SPACING / 2

        # 1. Clearance holes for the screw shafts (through holes)
        with BuildSketch(Plane.XY.offset(top_z + 0.1)):
            with Locations(
                (motor_x - motor_hole_offset, -motor_hole_offset),
                (motor_x - motor_hole_offset, motor_hole_offset),
                (motor_x + motor_hole_offset, -motor_hole_offset),
                (motor_x + motor_hole_offset, motor_hole_offset),
            ):
                Circle(M3_CLEARANCE / 2)
        extrude(amount=-(BASE_THICKNESS + 0.2), mode=Mode.SUBTRACT)

        # 2. Counterbores for the bolt heads (cut top-down so heads sit flush)
        with BuildSketch(Plane.XY.offset(top_z + 0.1)):
            with Locations(
                (motor_x - motor_hole_offset, -motor_hole_offset),
                (motor_x - motor_hole_offset, motor_hole_offset),
                (motor_x + motor_hole_offset, -motor_hole_offset),
                (motor_x + motor_hole_offset, motor_hole_offset),
            ):
                Circle(M3_COUNTERBORE / 2)
        extrude(amount=-(M3_COUNTERBORE_DEPTH + 0.1), mode=Mode.SUBTRACT)

        with BuildSketch(Plane.XY.offset(boss_top_z + 0.1)):
            Circle((BEARING_608_OD + 1.2) / 2, mode=Mode.ADD)
            Circle((SHAFT_CLEARANCE + 1.2) / 2, mode=Mode.SUBTRACT)
        extrude(amount=-1.0, mode=Mode.SUBTRACT)

        chamfer(stator.part.faces().sort_by(Axis.Z)[0].edges(), length=0.6)
        chamfer(stator.part.faces().sort_by(Axis.Z)[-1].edges(), length=0.6)

    return stator.part


def main() -> None:
    model = build_model()
    export_model(model, PART_NAME)

    try:
        from ocp_vscode import show
    except ImportError:
        return

    show(model)


if __name__ == "__main__":
    main()
