from __future__ import annotations

from math import atan2, degrees, hypot

from build123d import (
    Align,
    BuildPart,
    BuildSketch,
    Circle,
    Cylinder,
    GridLocations,
    Location,
    Locations,
    Mode,
    Part,
    Plane,
    RectangleRounded,
    SlotCenterToCenter,
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
HUB_DECK_OD = 112.0
HUB_DECK_ID = 64.0
CENTER_DECK_OD = 54.0

BEARING_BOSS_OD = 46.0
BEARING_BOSS_HEIGHT = 26.0
BEARING_POCKET_DEPTH = (2 * BEARING_608_WIDTH) + 0.4
SHAFT_CLEARANCE = BEARING_608_ID + 0.5

MOTOR_PILOT_CLEARANCE = NEMA17_PILOT + 0.6
MOTOR_SHAFT_CLEARANCE = NEMA17_SHAFT + 3.0
MOTOR_TAB_SIZE = NEMA17_BODY + 12.0
MOTOR_FRAME_WALL_THICKNESS = 1.6  # Four 0.4 mm extrusion widths
MOTOR_FRAME_CORNER_RADIUS = 7.0

MOTOR_BOTTOM_CLEARANCE = 2.0
BASE_MOTOR_FACE_Z = 0.0  # Motor mounts directly to the bottom face
FOOT_HEIGHT = (
    NEMA17_BODY_DEPTH
    + NEMA17_REAR_CAP_DEPTH
    - BASE_MOTOR_FACE_Z
    + MOTOR_BOTTOM_CLEARANCE
)
FOOT_OD = BASE_SIZE - CORNER_HOLE_SPACING
FOOT_CAVITY_OD = 12.0
FRAME_RIB_WIDTH = 3.2  # Eight 0.4 mm extrusion widths
LOWER_HUB_OD = 47.2
LOWER_HUB_ID = 40.0


def build_model() -> Part:
    """Build a lightweight, self-supporting monocoque base stator."""
    motor_x = BASE_GEAR_CENTER_DISTANCE
    top_z = BASE_THICKNESS
    boss_top_z = top_z + BEARING_BOSS_HEIGHT
    corner_offset = CORNER_HOLE_SPACING / 2
    corner_distance = hypot(corner_offset, corner_offset)

    assert_printable_extent((BASE_SIZE, BASE_SIZE, FOOT_HEIGHT + boss_top_z))

    with BuildPart() as stator:
        # The lower frame prints directly from the bed. Thin diagonal webs carry
        # turntable loads into four mounting feet without a support-heavy slab.
        with BuildSketch(Plane.XY.offset(-FOOT_HEIGHT)):
            with GridLocations(CORNER_HOLE_SPACING, CORNER_HOLE_SPACING, 2, 2):
                Circle(FOOT_OD / 2)

            Circle(LOWER_HUB_OD / 2)
            Circle(LOWER_HUB_ID / 2, mode=Mode.SUBTRACT)

            for corner_x in (-corner_offset, corner_offset):
                for corner_y in (-corner_offset, corner_offset):
                    with Locations(
                        Location(
                            (corner_x / 2, corner_y / 2, 0),
                            (0, 0, degrees(atan2(corner_y, corner_x))),
                        )
                    ):
                        SlotCenterToCenter(corner_distance, FRAME_RIB_WIDTH)

            # A thin perimeter tower carries the motor deck continuously while
            # preserving a generous, support-free NEMA17 body envelope.
            with Locations((motor_x, 0)):
                RectangleRounded(
                    MOTOR_TAB_SIZE,
                    MOTOR_TAB_SIZE,
                    radius=MOTOR_FRAME_CORNER_RADIUS,
                )
                RectangleRounded(
                    MOTOR_TAB_SIZE - 2 * MOTOR_FRAME_WALL_THICKNESS,
                    MOTOR_TAB_SIZE - 2 * MOTOR_FRAME_WALL_THICKNESS,
                    radius=MOTOR_FRAME_CORNER_RADIUS - MOTOR_FRAME_WALL_THICKNESS,
                    mode=Mode.SUBTRACT,
                )
        extrude(amount=FOOT_HEIGHT + 0.2)

        # Solid top caps distribute each desk fastener into its hollow foot.
        with GridLocations(CORNER_HOLE_SPACING, CORNER_HOLE_SPACING, 2, 2):
            Cylinder(
                FOOT_OD / 2,
                BASE_THICKNESS,
                align=(Align.CENTER, Align.CENTER, Align.MIN),
            )

        # An annular thrust deck, a compact bearing deck, and the motor face
        # replace the former 160 x 160 mm solid plate.
        with BuildSketch(Plane.XY):
            Circle(HUB_DECK_OD / 2)
            Circle(HUB_DECK_ID / 2, mode=Mode.SUBTRACT)
            Circle(CENTER_DECK_OD / 2)
        extrude(amount=BASE_THICKNESS)

        with BuildSketch(Plane.XY):
            with Locations((motor_x, 0)):
                RectangleRounded(
                    MOTOR_TAB_SIZE,
                    MOTOR_TAB_SIZE,
                    radius=MOTOR_FRAME_CORNER_RADIUS,
                )
        extrude(amount=BASE_THICKNESS)

        # Bottom-open cavities keep washer-bearing top caps over each foot.
        with GridLocations(CORNER_HOLE_SPACING, CORNER_HOLE_SPACING, 2, 2):
            Cylinder(
                FOOT_CAVITY_OD / 2,
                FOOT_HEIGHT + 0.2,
                align=(Align.CENTER, Align.CENTER, Align.MAX),
                mode=Mode.SUBTRACT,
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

            Cylinder(
                BEARING_BOSS_OD / 2,
                BEARING_BOSS_HEIGHT,
                align=(Align.CENTER, Align.CENTER, Align.MIN),
            )

        with Locations((0, 0, -FOOT_HEIGHT - 0.5)):
            Cylinder(
                SHAFT_CLEARANCE / 2,
                FOOT_HEIGHT + boss_top_z + 1.0,
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

        # NEMA17 pilot and shaft clearances open from the motor side.
        with Locations((motor_x, 0, -0.1)):
            Cylinder(
                MOTOR_PILOT_CLEARANCE / 2,
                2.4,
                align=(Align.CENTER, Align.CENTER, Align.MIN),
                mode=Mode.SUBTRACT,
            )
        with Locations((motor_x, 0, -0.5)):
            Cylinder(
                MOTOR_SHAFT_CLEARANCE / 2,
                BASE_THICKNESS + 1.0,
                align=(Align.CENTER, Align.CENTER, Align.MIN),
                mode=Mode.SUBTRACT,
            )

        motor_hole_offset = NEMA17_HOLE_SPACING / 2
        motor_holes = (
            (motor_x - motor_hole_offset, -motor_hole_offset),
            (motor_x - motor_hole_offset, motor_hole_offset),
            (motor_x + motor_hole_offset, -motor_hole_offset),
            (motor_x + motor_hole_offset, motor_hole_offset),
        )
        with BuildSketch(Plane.XY.offset(top_z + 0.1)):
            with Locations(*motor_holes):
                Circle(M3_CLEARANCE / 2)
        extrude(amount=-(BASE_THICKNESS + 0.2), mode=Mode.SUBTRACT)

        with BuildSketch(Plane.XY.offset(top_z + 0.1)):
            with Locations(*motor_holes):
                Circle(M3_COUNTERBORE / 2)
        extrude(amount=-(M3_COUNTERBORE_DEPTH + 0.1), mode=Mode.SUBTRACT)

        with BuildSketch(Plane.XY.offset(boss_top_z + 0.1)):
            Circle((BEARING_608_OD + 1.2) / 2, mode=Mode.ADD)
            Circle((SHAFT_CLEARANCE + 1.2) / 2, mode=Mode.SUBTRACT)
        extrude(amount=-1.0, mode=Mode.SUBTRACT)

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
