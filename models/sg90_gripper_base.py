from __future__ import annotations

from build123d import (
    Align,
    BuildPart,
    BuildSketch,
    Cone,
    Cylinder,
    Mode,
    Plane,
    Polygon,
    Box,
    Locations,
    extrude,
)

try:
    from models.common import (
        BEARING_625_OD,
        M3_CLEARANCE,
        SG90_BODY_X,
        SG90_BODY_Y,
        SG90_TAB_SPACING,
        WRIST_PULLEY_BOLT_CIRCLE,
        assert_printable_extent,
        circle_points,
        export_model,
    )
except ModuleNotFoundError:
    from common import (
        BEARING_625_OD,
        M3_CLEARANCE,
        SG90_BODY_X,
        SG90_BODY_Y,
        SG90_TAB_SPACING,
        WRIST_PULLEY_BOLT_CIRCLE,
        assert_printable_extent,
        circle_points,
        export_model,
    )


MODEL_NAME = "sg90_gripper_base"

PLATE_THICKNESS = 5.0
CLEVIS_TONGUE_WIDTH = 14.0
PIVOT_BOSS_RADIUS = 16.0
PIVOT_SHAFT_CLEARANCE = 5.4
PILOT_HOLE_DIAMETER = 1.0
WRIST_JOINT_ROTATION_CLEARANCE_RADIUS = 22.0
DECK_ROOT_WIDTH = 15.0
DECK_FLARE_FULL_Y = 38.0

SERVO_CENTER_Y = 43.0
SERVO_CENTER_X = 11.5
SERVO_SHAFT_Y = SERVO_CENTER_Y + 6.5
GRIPPER_POST_Y = SERVO_SHAFT_Y + 25.0
GRIPPER_POST_DIAMETER = 5.0
GRIPPER_POST_HEIGHT = 14.0

OVERALL_WIDTH = 54.0
OVERALL_LENGTH = 106.0
OVERALL_HEIGHT = max(PIVOT_BOSS_RADIUS * 2, PLATE_THICKNESS + GRIPPER_POST_HEIGHT)


def _lightening_slot(x: float, y: float, width: float, length: float, cut_depth: float) -> None:
    """Cut a rounded rectangular slot normal to the XY servo deck."""
    with Locations((x, y, 0)):
        Box(width, length, cut_depth, mode=Mode.SUBTRACT)
    for end_y in (y - length / 2, y + length / 2):
        with Locations((x, end_y, 0)):
            Cylinder(radius=width / 2, height=cut_depth, mode=Mode.SUBTRACT)


def build_model():
    """Build the SG90 gripper base with the wrist pivot axis on local X."""
    assert_printable_extent((OVERALL_WIDTH, OVERALL_LENGTH, OVERALL_HEIGHT))

    deck_outline = [
        (-CLEVIS_TONGUE_WIDTH / 2, -PIVOT_BOSS_RADIUS),
        (CLEVIS_TONGUE_WIDTH / 2, -PIVOT_BOSS_RADIUS),
        (DECK_ROOT_WIDTH / 2, WRIST_JOINT_ROTATION_CLEARANCE_RADIUS),
        (OVERALL_WIDTH / 2, DECK_FLARE_FULL_Y),
        (OVERALL_WIDTH / 2, 82.0),
        (18.0, OVERALL_LENGTH - PIVOT_BOSS_RADIUS),
        (-18.0, OVERALL_LENGTH - PIVOT_BOSS_RADIUS),
        (-OVERALL_WIDTH / 2, 82.0),
        (-OVERALL_WIDTH / 2, DECK_FLARE_FULL_Y),
        (-DECK_ROOT_WIDTH / 2, WRIST_JOINT_ROTATION_CLEARANCE_RADIUS),
    ]

    with BuildPart() as part:
        with BuildSketch(Plane.XY):
            Polygon(deck_outline)
        extrude(amount=PLATE_THICKNESS, both=True)

        # Wrist pivot tongue: X is the installed wrist shaft axis and local origin.
        Cylinder(
            radius=PIVOT_BOSS_RADIUS,
            height=CLEVIS_TONGUE_WIDTH,
            rotation=(0, 90, 0),
        )

        # Small center spine ties the round wrist boss into the servo deck.
        with Locations((0, 11.0, 0)):
            Box(
                CLEVIS_TONGUE_WIDTH,
                34.0,
                10.0,
                align=(Align.CENTER, Align.CENTER, Align.CENTER),
            )

        # Wrist pivot clearance and two shallow 625-sized registration pockets.
        Cylinder(
            radius=PIVOT_SHAFT_CLEARANCE / 2,
            height=CLEVIS_TONGUE_WIDTH + 4.0,
            rotation=(0, 90, 0),
            mode=Mode.SUBTRACT,
        )
        for pocket_x in (
            -CLEVIS_TONGUE_WIDTH / 2 + 0.7,
            CLEVIS_TONGUE_WIDTH / 2 - 0.7,
        ):
            with Locations((pocket_x, 0, 0)):
                Cylinder(
                    radius=BEARING_625_OD / 2,
                    height=1.4,
                    rotation=(0, 90, 0),
                    mode=Mode.SUBTRACT,
                )

        # Four M3 wrist pulley holes on the integrated 60T pulley bolt pattern.
        for bolt_y, bolt_z in circle_points(4, WRIST_PULLEY_BOLT_CIRCLE, start_angle=45):
            with Locations((0, bolt_y, bolt_z)):
                Cylinder(
                    radius=M3_CLEARANCE / 2,
                    height=CLEVIS_TONGUE_WIDTH + 4.0,
                    rotation=(0, 90, 0),
                    mode=Mode.SUBTRACT,
                )

        # SG90 body pockets and 1 mm tab screw pilot holes.
        for servo_x in (-SERVO_CENTER_X, SERVO_CENTER_X):
            with Locations((servo_x, SERVO_CENTER_Y, 0)):
                Box(
                    SG90_BODY_Y,
                    SG90_BODY_X,
                    PLATE_THICKNESS + 2.0,
                    mode=Mode.SUBTRACT,
                )
            for screw_y in (
                SERVO_CENTER_Y - SG90_TAB_SPACING / 2,
                SERVO_CENTER_Y + SG90_TAB_SPACING / 2,
            ):
                with Locations((servo_x, screw_y, 0)):
                    Cylinder(
                        radius=PILOT_HOLE_DIAMETER / 2,
                        height=PLATE_THICKNESS + 2.0,
                        mode=Mode.SUBTRACT,
                    )

        # Skeletal relief slots, leaving perimeter rails and the servo/post ribs intact.
        _lightening_slot(-20.5, 54.0, 4.8, 39.0, PLATE_THICKNESS + 2.0)
        _lightening_slot(20.5, 54.0, 4.8, 39.0, PLATE_THICKNESS + 2.0)
        _lightening_slot(0.0, 77.5, 7.0, 20.0, PLATE_THICKNESS + 2.0)

        # Two vertical gripper fulcrum posts, 25 mm forward of the assumed servo shaft line.
        post_start_z = PLATE_THICKNESS / 2
        post_stem_height = GRIPPER_POST_HEIGHT - 2.5
        for post_x in (-SERVO_CENTER_X, SERVO_CENTER_X):
            with Locations((post_x, GRIPPER_POST_Y, post_start_z + 0.5)):
                Cylinder(radius=4.0, height=1.0)
            with Locations((post_x, GRIPPER_POST_Y, post_start_z + 1.75)):
                Cone(
                    bottom_radius=4.0,
                    top_radius=GRIPPER_POST_DIAMETER / 2,
                    height=1.5,
                )
            with Locations((post_x, GRIPPER_POST_Y, post_start_z + 2.5 + post_stem_height / 2)):
                Cylinder(radius=GRIPPER_POST_DIAMETER / 2, height=post_stem_height)

    return part.part


def main() -> None:
    model = build_model()
    export_model(model, MODEL_NAME)

    try:
        from ocp_vscode import show
    except ImportError:
        show = None

    if show is not None:
        show(model)


if __name__ == "__main__":
    main()
