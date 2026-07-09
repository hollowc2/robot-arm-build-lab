from __future__ import annotations

from build123d import Align, Box, BuildPart, Cone, Cylinder, Locations, Mode

try:
    from models.common import (
        BEARING_625_ID,
        BEARING_625_OD,
        BEARING_625_WIDTH,
        BYJ48_BODY,
        BYJ48_EAR_SPACING,
        M3_CLEARANCE,
        ELBOW_PULLEY_BOLT_CIRCLE,
        WRIST_BELT_CENTER_DISTANCE,
        assert_printable_extent,
        circle_points,
        export_model,
    )
except ModuleNotFoundError:
    from common import (
        BEARING_625_ID,
        BEARING_625_OD,
        BEARING_625_WIDTH,
        BYJ48_BODY,
        BYJ48_EAR_SPACING,
        M3_CLEARANCE,
        ELBOW_PULLEY_BOLT_CIRCLE,
        WRIST_BELT_CENTER_DISTANCE,
        assert_printable_extent,
        circle_points,
        export_model,
    )


PART_NAME = "forearm_link"

BOTTOM_PIVOT_HOLE = 5.0
BOTTOM_HUB_RADIUS = 24.0
BOTTOM_HUB_THICKNESS = 14.0

LINK_HALF_WIDTH_Y = 21.0
LINK_RAIL_WIDTH_Y = 7.0
LINK_THICKNESS_X = 12.0
LINK_RIB_THICKNESS_Z = 6.0

MOTOR_FACE_THICKNESS_X = 5.0
MOTOR_FACE_WIDTH_Y = 48.0
MOTOR_FACE_HEIGHT_Z = 46.0
MOTOR_MOUNT_ELBOW_END_CLEARANCE_Z = 8.0
MOTOR_MOUNT_BOTTOM_Z = BOTTOM_HUB_RADIUS + MOTOR_MOUNT_ELBOW_END_CLEARANCE_Z
MOTOR_SHAFT_Z = MOTOR_MOUNT_BOTTOM_Z + MOTOR_FACE_HEIGHT_Z / 2
TOP_WRIST_PIVOT_Z = MOTOR_SHAFT_Z + WRIST_BELT_CENTER_DISTANCE
MOTOR_BODY_POCKET_DEPTH = 2.8
MOTOR_BODY_POCKET_CLEARANCE = 0.35
MOTOR_SHAFT_CLEARANCE = 10.0
MOTOR_SUPPORT_RIB_THICKNESS_Y = 5.0
MOTOR_SUPPORT_RIB_DEPTH_X = 12.0
WRIST_MOTOR_SIDE_SIGN = -1

ELBOW_BOLT_HEAD_SIDE_SIGN = -1
ELBOW_M3_COUNTERSINK_DIAMETER = 6.8
ELBOW_M3_COUNTERSINK_DEPTH = 2.0

CLEVIS_GAP_X = 18.0
CLEVIS_EAR_THICKNESS_X = 6.0
CLEVIS_WIDTH_Y = 34.0
CLEVIS_HEIGHT_Z = 36.0
CLEVIS_BRIDGE_HEIGHT_Z = 10.0


def _x_cylinder(radius: float, height: float, mode: Mode = Mode.ADD) -> None:
    Cylinder(
        radius=radius,
        height=height,
        rotation=(0, 90, 0),
        align=(Align.CENTER, Align.CENTER, Align.CENTER),
        mode=mode,
    )


def _x_cone(bottom_radius: float, top_radius: float, height: float, mode: Mode = Mode.ADD) -> None:
    Cone(
        bottom_radius=bottom_radius,
        top_radius=top_radius,
        height=height,
        rotation=(0, 90, 0),
        align=(Align.CENTER, Align.CENTER, Align.CENTER),
        mode=mode,
    )


def build_model():
    """Build the forearm link with the elbow pivot at the local origin.

    The lower elbow pivot and upper wrist pivot both use X as the pivot axis.
    The two wrist motor shaft centers are coaxial at MOTOR_SHAFT_Z, making
    the center-to-center distance to the wrist pivot exactly 109.33mm.
    """
    if MOTOR_MOUNT_BOTTOM_Z - BOTTOM_HUB_RADIUS < 6.0:
        raise ValueError("Forearm wrist motor mount must clear the elbow hub end by at least 6mm.")

    with BuildPart() as forearm:
        # Bottom elbow hub and elbow driven pulley interface.
        _x_cylinder(BOTTOM_HUB_RADIUS, BOTTOM_HUB_THICKNESS)

        with Locations((0, 0, 0)):
            _x_cylinder(BOTTOM_PIVOT_HOLE / 2, BOTTOM_HUB_THICKNESS + 4.0, Mode.SUBTRACT)

        for y, z in circle_points(4, ELBOW_PULLEY_BOLT_CIRCLE, start_angle=45):
            with Locations((0, y, z)):
                _x_cylinder(M3_CLEARANCE / 2, BOTTOM_HUB_THICKNESS + 4.0, Mode.SUBTRACT)
            countersink_x = ELBOW_BOLT_HEAD_SIDE_SIGN * (
                BOTTOM_HUB_THICKNESS / 2 - ELBOW_M3_COUNTERSINK_DEPTH / 2
            )
            with Locations((countersink_x, y, z)):
                _x_cone(
                    ELBOW_M3_COUNTERSINK_DIAMETER / 2,
                    M3_CLEARANCE / 2,
                    ELBOW_M3_COUNTERSINK_DEPTH,
                    Mode.SUBTRACT,
                )

        # Long lightweight rails from elbow hub to wrist clevis.
        rail_center_z = TOP_WRIST_PIVOT_Z / 2
        rail_height_z = TOP_WRIST_PIVOT_Z
        for y in (-LINK_HALF_WIDTH_Y + LINK_RAIL_WIDTH_Y / 2, LINK_HALF_WIDTH_Y - LINK_RAIL_WIDTH_Y / 2):
            with Locations((0, y, rail_center_z)):
                Box(
                    LINK_THICKNESS_X,
                    LINK_RAIL_WIDTH_Y,
                    rail_height_z,
                    align=(Align.CENTER, Align.CENTER, Align.CENTER),
                )

        # Sparse cross ribs keep the channel torsionally stiff without making it solid.
        for z in (18.0, 52.0, 86.0, 120.0):
            with Locations((0, 0, z)):
                Box(
                    LINK_THICKNESS_X,
                    LINK_HALF_WIDTH_Y * 2,
                    LINK_RIB_THICKNESS_Z,
                    align=(Align.CENTER, Align.CENTER, Align.CENTER),
                )

        # Single wrist motor mount on the pulley side of the forearm.
        face_x = WRIST_MOTOR_SIDE_SIGN * (LINK_THICKNESS_X / 2 + MOTOR_FACE_THICKNESS_X / 2)
        with Locations((face_x, 0, MOTOR_SHAFT_Z)):
            Box(
                MOTOR_FACE_THICKNESS_X,
                MOTOR_FACE_WIDTH_Y,
                MOTOR_FACE_HEIGHT_Z,
                align=(Align.CENTER, Align.CENTER, Align.CENTER),
            )

        support_x = WRIST_MOTOR_SIDE_SIGN * (
            LINK_THICKNESS_X / 2 + MOTOR_SUPPORT_RIB_DEPTH_X / 2 - MOTOR_FACE_THICKNESS_X
        )
        for y in (-LINK_HALF_WIDTH_Y + LINK_RAIL_WIDTH_Y / 2, LINK_HALF_WIDTH_Y - LINK_RAIL_WIDTH_Y / 2):
            with Locations((support_x, y, MOTOR_SHAFT_Z)):
                Box(
                    MOTOR_SUPPORT_RIB_DEPTH_X,
                    MOTOR_SUPPORT_RIB_THICKNESS_Y,
                    MOTOR_FACE_HEIGHT_Z,
                    align=(Align.CENTER, Align.CENTER, Align.CENTER),
                )

        for z in (MOTOR_MOUNT_BOTTOM_Z, MOTOR_MOUNT_BOTTOM_Z + MOTOR_FACE_HEIGHT_Z):
            with Locations((support_x, 0, z)):
                Box(
                    MOTOR_SUPPORT_RIB_DEPTH_X,
                    LINK_HALF_WIDTH_Y * 2,
                    LINK_RIB_THICKNESS_Z,
                    align=(Align.CENTER, Align.CENTER, Align.CENTER),
                )

        pocket_center_x = WRIST_MOTOR_SIDE_SIGN * (
            LINK_THICKNESS_X / 2 + MOTOR_FACE_THICKNESS_X - MOTOR_BODY_POCKET_DEPTH / 2
        )
        with Locations((pocket_center_x, 0, MOTOR_SHAFT_Z)):
            _x_cylinder((BYJ48_BODY + MOTOR_BODY_POCKET_CLEARANCE) / 2, MOTOR_BODY_POCKET_DEPTH, Mode.SUBTRACT)

        motor_mount_through_x = LINK_THICKNESS_X + MOTOR_FACE_THICKNESS_X + 2.0
        with Locations((face_x, 0, MOTOR_SHAFT_Z)):
            _x_cylinder(MOTOR_SHAFT_CLEARANCE / 2, motor_mount_through_x, Mode.SUBTRACT)

        for y in (-BYJ48_EAR_SPACING / 2, BYJ48_EAR_SPACING / 2):
            with Locations((face_x, y, MOTOR_SHAFT_Z)):
                _x_cylinder(M3_CLEARANCE / 2, motor_mount_through_x, Mode.SUBTRACT)

        # Top wrist clevis: two X-axis ears with 625z bearing pockets.
        ear_x = CLEVIS_GAP_X / 2 + CLEVIS_EAR_THICKNESS_X / 2
        for x in (-ear_x, ear_x):
            with Locations((x, 0, TOP_WRIST_PIVOT_Z)):
                Box(
                    CLEVIS_EAR_THICKNESS_X,
                    CLEVIS_WIDTH_Y,
                    CLEVIS_HEIGHT_Z,
                    align=(Align.CENTER, Align.CENTER, Align.CENTER),
                )

        with Locations((0, 0, TOP_WRIST_PIVOT_Z - CLEVIS_HEIGHT_Z / 2 + CLEVIS_BRIDGE_HEIGHT_Z / 2)):
            Box(
                CLEVIS_GAP_X + 2 * CLEVIS_EAR_THICKNESS_X,
                CLEVIS_WIDTH_Y,
                CLEVIS_BRIDGE_HEIGHT_Z,
                align=(Align.CENTER, Align.CENTER, Align.CENTER),
            )

        with Locations((0, 0, TOP_WRIST_PIVOT_Z)):
            _x_cylinder(BEARING_625_ID / 2, CLEVIS_GAP_X + 2 * CLEVIS_EAR_THICKNESS_X + 4.0, Mode.SUBTRACT)

        pocket_x = CLEVIS_GAP_X / 2 + CLEVIS_EAR_THICKNESS_X - BEARING_625_WIDTH / 2
        for x in (-pocket_x, pocket_x):
            with Locations((x, 0, TOP_WRIST_PIVOT_Z)):
                _x_cylinder(BEARING_625_OD / 2, BEARING_625_WIDTH, Mode.SUBTRACT)

    model = forearm.part
    size = model.bounding_box().size
    assert_printable_extent((size.X, size.Y, size.Z))
    return model


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
