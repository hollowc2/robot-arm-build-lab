from __future__ import annotations

from math import atan2, degrees, hypot, pi

from build123d import (
    Align,
    Box,
    BuildPart,
    BuildSketch,
    Cylinder,
    Locations,
    Mode,
    Plane,
    RectangleRounded,
    SlotCenterToCenter,
    add,
    extrude,
    loft,
)

try:
    from models.common import (
        BEARING_625_ID,
        BEARING_625_OD,
        BEARING_625_WIDTH,
        BYJ48_BODY,
        BYJ48_MOUNT_HOLE,
        BYJ48_EAR_SPACING,
        M3_CLEARANCE,
        M3_COUNTERBORE_DEPTH,
        ELBOW_PULLEY_BOLT_CIRCLE,
        WRIST_BELT_CENTER_DISTANCE,
        WRIST_DRIVER_TEETH,
        WRIST_DRIVEN_TEETH,
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
        BYJ48_MOUNT_HOLE,
        BYJ48_EAR_SPACING,
        M3_CLEARANCE,
        M3_COUNTERBORE_DEPTH,
        ELBOW_PULLEY_BOLT_CIRCLE,
        WRIST_BELT_CENTER_DISTANCE,
        WRIST_DRIVER_TEETH,
        WRIST_DRIVEN_TEETH,
        assert_printable_extent,
        circle_points,
        export_model,
    )


PART_NAME = "forearm_link"

BOTTOM_PIVOT_HOLE = 5.0
BOTTOM_HUB_RADIUS = 24.0
BOTTOM_HUB_THICKNESS = 14.0

LINK_HALF_WIDTH_Y = 24.0
LINK_RAIL_WIDTH_Y = 6.0
LINK_THICKNESS_X = 12.0
LINK_RIB_THICKNESS_Z = 6.0

MOTOR_FACE_THICKNESS_X = 5.0
MOTOR_FACE_WIDTH_Y = 48.0
MOTOR_FACE_HEIGHT_Z = 46.0
MOTOR_MOUNT_ELBOW_END_CLEARANCE_Z = 11.0
MOTOR_MOUNT_BOTTOM_Z = BOTTOM_HUB_RADIUS + MOTOR_MOUNT_ELBOW_END_CLEARANCE_Z
MOTOR_SHAFT_Z = MOTOR_MOUNT_BOTTOM_Z + MOTOR_FACE_HEIGHT_Z / 2
TOP_WRIST_PIVOT_Z = MOTOR_SHAFT_Z + WRIST_BELT_CENTER_DISTANCE
MOTOR_SLOT_TRAVEL = 6.0
MOTOR_BODY_POCKET_DEPTH = 2.8
MOTOR_BODY_POCKET_CLEARANCE = 0.35
MOTOR_SHAFT_CLEARANCE = 10.0
MOTOR_SUPPORT_RIB_THICKNESS_Y = 5.0
MOTOR_SUPPORT_RIB_DEPTH_X = 12.0
WRIST_MOTOR_SIDE_SIGN = -1

# The elbow pulley stack moves the forearm 5.875 mm to the positive-X side of
# the base centerline.  The pulley/tongue wrist stack would add a further
# 8 mm.  Move the complete wrist drive and clevis back by their combined
# amount so the gripper center plane returns to X=0 in the straight-arm pose.
WRIST_ASSEMBLY_OFFSET_X = -13.875

HTD_3M_PITCH = 3.0
WRIST_BELT_WIDTH = 8.0
WRIST_PULLEY_TOTAL_HEIGHT = 11.0
WRIST_BELT_CHANNEL_CLEARANCE_X = 0.8
WRIST_BELT_CHANNEL_SLOT_WIDTH_YZ = 4.8
WRIST_BELT_CHANNEL_RUN_EXTENSION = 4.0
WRIST_BELT_CHANNEL_CENTER_X = WRIST_ASSEMBLY_OFFSET_X + WRIST_MOTOR_SIDE_SIGN * (
    LINK_THICKNESS_X / 2 + MOTOR_FACE_THICKNESS_X - WRIST_PULLEY_TOTAL_HEIGHT / 2
)
WRIST_BELT_CHANNEL_OUTER_X = WRIST_BELT_CHANNEL_CENTER_X - WRIST_BELT_WIDTH / 2 - WRIST_BELT_CHANNEL_CLEARANCE_X
WRIST_BELT_CHANNEL_DEPTH_X = WRIST_BELT_WIDTH + 2 * WRIST_BELT_CHANNEL_CLEARANCE_X
WRIST_BELT_PULLEY_RELIEF_MARGIN = 3.0
# The belt channel clears the belt body, but the pulley flanges extend farther
# in X.  Keep the complete pulley stack out of the forearm, including a small
# print/assembly allowance on both flange faces.
WRIST_PULLEY_AXIAL_CLEARANCE_X = 0.8
WRIST_PULLEY_FLANGE_HEIGHT = 1.5
WRIST_PULLEY_TOTAL_HEIGHT = WRIST_BELT_WIDTH + 2 * WRIST_PULLEY_FLANGE_HEIGHT
WRIST_PULLEY_RELIEF_CENTER_X = WRIST_BELT_CHANNEL_CENTER_X
WRIST_PULLEY_RELIEF_DEPTH_X = WRIST_PULLEY_TOTAL_HEIGHT + 2 * WRIST_PULLEY_AXIAL_CLEARANCE_X


ELBOW_BOLT_HEAD_SIDE_SIGN = -1
ELBOW_M3_COUNTERBORE_DIAMETER = 6.8
ELBOW_M3_COUNTERBORE_DEPTH = M3_COUNTERBORE_DEPTH

CLEVIS_GAP_X = 29.0
WRIST_CLEVIS_GAP_CENTER_X = WRIST_ASSEMBLY_OFFSET_X + 2.0
CLEVIS_EAR_THICKNESS_X = 6.0
CLEVIS_WIDTH_Y = 26.0
CLEVIS_HEIGHT_Z = 36.0
CLEVIS_BRIDGE_HEIGHT_Z = 10.0
WRIST_CLEVIS_CLEARANCE_Z = 50.0
WRIST_HULL_TRANSITION_START_Z = TOP_WRIST_PIVOT_Z - 62.0
WRIST_HULL_WIDTH_Y = 28.0
WRIST_CLEVIS_CLEARANCE_BOTTOM_Z = TOP_WRIST_PIVOT_Z - WRIST_CLEVIS_CLEARANCE_Z / 2
WRIST_OFFSET_EAR_GUSSET_WIDTH_Y = 14.0
WRIST_OFFSET_EAR_GUSSET_FULL_Z = WRIST_CLEVIS_CLEARANCE_BOTTOM_Z - 10.0
WRIST_OFFSET_EAR_OUTER_X = (
    WRIST_CLEVIS_GAP_CENTER_X - CLEVIS_GAP_X / 2 - CLEVIS_EAR_THICKNESS_X
)
WRIST_OFFSET_EAR_GUSSET_INNER_X = -LINK_THICKNESS_X / 2



def _x_cylinder(radius: float, height: float, mode: Mode = Mode.ADD) -> None:
    Cylinder(
        radius=radius,
        height=height,
        rotation=(0, 90, 0),
        align=(Align.CENTER, Align.CENTER, Align.CENTER),
        mode=mode,
    )


def _vertical_slot_along_x(
    y: float,
    z: float,
    travel: float,
    width: float,
    *,
    x_start: float,
    depth: float,
) -> None:
    with BuildSketch(Plane.YZ.offset(x_start)) as slot:
        with Locations((y, z)):
            SlotCenterToCenter(travel, width, rotation=90)
    extrude(slot.sketch, amount=depth, mode=Mode.SUBTRACT)


def _slotted_x_pocket(
    y: float,
    z: float,
    travel: float,
    width: float,
    *,
    x_start: float,
    depth: float,
) -> None:
    _vertical_slot_along_x(y, z, travel, width, x_start=x_start, depth=depth)


def _pitch_radius(teeth: int) -> float:
    return teeth * HTD_3M_PITCH / (2 * pi)


def _cut_wrist_belt_channels() -> None:
    driver_radius = _pitch_radius(WRIST_DRIVER_TEETH)
    driven_radius = _pitch_radius(WRIST_DRIVEN_TEETH)
    center_distance = TOP_WRIST_PIVOT_Z - MOTOR_SHAFT_Z
    tangent_bias = (driver_radius - driven_radius) / center_distance
    tangent_span = (1 - tangent_bias * tangent_bias) ** 0.5

    for side in (1.0, -1.0):
        start_y = -side * tangent_span * driver_radius
        start_z = MOTOR_SHAFT_Z + tangent_bias * driver_radius
        end_y = -side * tangent_span * driven_radius
        end_z = TOP_WRIST_PIVOT_Z + tangent_bias * driven_radius
        run_length = hypot(end_y - start_y, end_z - start_z)
        run_angle = degrees(atan2(end_z - start_z, end_y - start_y))
        center_y = (start_y + end_y) / 2
        center_z = (start_z + end_z) / 2

        with BuildSketch(Plane.YZ.offset(WRIST_BELT_CHANNEL_OUTER_X)) as channel_slot:
            with Locations((center_y, center_z)):
                SlotCenterToCenter(
                    run_length + 2 * WRIST_BELT_CHANNEL_RUN_EXTENSION,
                    WRIST_BELT_CHANNEL_SLOT_WIDTH_YZ,
                    rotation=run_angle,
                )
        extrude(channel_slot.sketch, amount=WRIST_BELT_CHANNEL_DEPTH_X, mode=Mode.SUBTRACT)


def _cut_wrist_belt_loading_relief() -> None:
    """Clear the complete pulley envelope, including both flanges."""
    relief_center_x = WRIST_PULLEY_RELIEF_CENTER_X
    driver_radius = _pitch_radius(WRIST_DRIVER_TEETH) + WRIST_BELT_CHANNEL_SLOT_WIDTH_YZ / 2
    driven_radius = _pitch_radius(WRIST_DRIVEN_TEETH) + WRIST_BELT_CHANNEL_SLOT_WIDTH_YZ / 2
    reliefs = (
        (MOTOR_SHAFT_Z, driver_radius + WRIST_BELT_PULLEY_RELIEF_MARGIN),
        (TOP_WRIST_PIVOT_Z, driven_radius + WRIST_BELT_PULLEY_RELIEF_MARGIN),
    )

    for z, radius in reliefs:
        with Locations((relief_center_x, 0, z)):
            _x_cylinder(radius, WRIST_PULLEY_RELIEF_DEPTH_X, Mode.SUBTRACT)




def _cut_wrist_clevis_clearance() -> None:
    """Open the wrist clevis gap around the gripper base pivot boss."""
    with Locations((WRIST_CLEVIS_GAP_CENTER_X, 0, TOP_WRIST_PIVOT_Z)):
        Box(
            CLEVIS_GAP_X,
            CLEVIS_WIDTH_Y + 32.0,
            WRIST_CLEVIS_CLEARANCE_Z,
            align=(Align.CENTER, Align.CENTER, Align.CENTER),
            mode=Mode.SUBTRACT,
        )


def _build_wrist_swept_hull():
    """Build a continuous rounded shoulder from the forearm span into the wrist clevis."""
    clevis_total_x = CLEVIS_GAP_X + 2 * CLEVIS_EAR_THICKNESS_X
    clevis_base_z = TOP_WRIST_PIVOT_Z - CLEVIS_HEIGHT_Z / 2

    with BuildPart() as hull:
        with BuildSketch(Plane.XY.offset(WRIST_HULL_TRANSITION_START_Z)):
            RectangleRounded(LINK_THICKNESS_X, LINK_HALF_WIDTH_Y * 2, radius=5.0)
        with BuildSketch(Plane.XY.offset(clevis_base_z)):
            with Locations((WRIST_CLEVIS_GAP_CENTER_X, 0)):
                RectangleRounded(clevis_total_x, WRIST_HULL_WIDTH_Y, radius=7.0)
        loft()

        with BuildSketch(Plane.XY.offset(clevis_base_z)):
            with Locations((WRIST_CLEVIS_GAP_CENTER_X, 0)):
                RectangleRounded(clevis_total_x, WRIST_HULL_WIDTH_Y, radius=7.0)
        with BuildSketch(Plane.XY.offset(TOP_WRIST_PIVOT_Z)):
            with Locations((WRIST_CLEVIS_GAP_CENTER_X, 0)):
                RectangleRounded(clevis_total_x, CLEVIS_WIDTH_Y, radius=7.0)
        loft()

        with Locations((WRIST_CLEVIS_GAP_CENTER_X, 0, TOP_WRIST_PIVOT_Z)):
            _x_cylinder(CLEVIS_WIDTH_Y / 2, clevis_total_x)

    return hull.part


def _build_wrist_offset_ear_gusset():
    """Brace the offset clevis ear through the belt-free space between both runs."""
    gusset_span_x = WRIST_OFFSET_EAR_GUSSET_INNER_X - WRIST_OFFSET_EAR_OUTER_X
    gusset_center_x = WRIST_OFFSET_EAR_OUTER_X + gusset_span_x / 2
    if gusset_span_x <= 0:
        raise ValueError("Offset wrist ear gusset has no X span.")

    with BuildPart() as gusset:
        with BuildSketch(Plane.XY.offset(WRIST_HULL_TRANSITION_START_Z)):
            RectangleRounded(
                LINK_THICKNESS_X,
                WRIST_OFFSET_EAR_GUSSET_WIDTH_Y,
                radius=3.0,
            )
        with BuildSketch(Plane.XY.offset(WRIST_OFFSET_EAR_GUSSET_FULL_Z)):
            with Locations((gusset_center_x, 0)):
                RectangleRounded(
                    gusset_span_x,
                    WRIST_OFFSET_EAR_GUSSET_WIDTH_Y,
                    radius=3.0,
                )
        loft()

        with BuildSketch(Plane.XY.offset(WRIST_OFFSET_EAR_GUSSET_FULL_Z)):
            with Locations((gusset_center_x, 0)):
                RectangleRounded(
                    gusset_span_x,
                    WRIST_OFFSET_EAR_GUSSET_WIDTH_Y,
                    radius=3.0,
                )
        with BuildSketch(Plane.XY.offset(WRIST_CLEVIS_CLEARANCE_BOTTOM_Z)):
            with Locations(
                (WRIST_OFFSET_EAR_OUTER_X + CLEVIS_EAR_THICKNESS_X / 2, 0)
            ):
                RectangleRounded(
                    CLEVIS_EAR_THICKNESS_X,
                    CLEVIS_WIDTH_Y,
                    radius=2.5,
                )
        loft()

        with BuildSketch(Plane.XY.offset(WRIST_CLEVIS_CLEARANCE_BOTTOM_Z)):
            with Locations(
                (WRIST_OFFSET_EAR_OUTER_X + CLEVIS_EAR_THICKNESS_X / 2, 0)
            ):
                RectangleRounded(
                    CLEVIS_EAR_THICKNESS_X,
                    CLEVIS_WIDTH_Y,
                    radius=2.5,
                )
        with BuildSketch(Plane.XY.offset(TOP_WRIST_PIVOT_Z)):
            with Locations(
                (WRIST_OFFSET_EAR_OUTER_X + CLEVIS_EAR_THICKNESS_X / 2, 0)
            ):
                RectangleRounded(
                    CLEVIS_EAR_THICKNESS_X,
                    CLEVIS_WIDTH_Y,
                    radius=2.5,
                )
        loft()

    return gusset.part


def build_model():
    """Build the forearm link with the elbow pivot at the local origin.

    The lower elbow pivot and upper wrist pivot both use X as the pivot axis.
    The wrist motor shaft is coaxial at MOTOR_SHAFT_Z, and its center distance
    to the wrist pivot matches WRIST_BELT_CENTER_DISTANCE.
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
            counterbore_x = ELBOW_BOLT_HEAD_SIDE_SIGN * (
                BOTTOM_HUB_THICKNESS / 2 - ELBOW_M3_COUNTERBORE_DEPTH / 2
            )
            with Locations((counterbore_x, y, z)):
                _x_cylinder(
                    ELBOW_M3_COUNTERBORE_DIAMETER / 2,
                    ELBOW_M3_COUNTERBORE_DEPTH,
                    Mode.SUBTRACT,
                )

        # Long lightweight rails from elbow hub to wrist clevis.
        rail_center_z = WRIST_HULL_TRANSITION_START_Z / 2
        rail_height_z = WRIST_HULL_TRANSITION_START_Z
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
        face_x = WRIST_ASSEMBLY_OFFSET_X + WRIST_MOTOR_SIDE_SIGN * (
            LINK_THICKNESS_X / 2 + MOTOR_FACE_THICKNESS_X / 2
        )
        with Locations((face_x, 0, MOTOR_SHAFT_Z)):
            Box(
                MOTOR_FACE_THICKNESS_X,
                MOTOR_FACE_WIDTH_Y,
                MOTOR_FACE_HEIGHT_Z,
                align=(Align.CENTER, Align.CENTER, Align.CENTER),
            )

        support_x = WRIST_ASSEMBLY_OFFSET_X + WRIST_MOTOR_SIDE_SIGN * (
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

        # Tie the offset motor support back into the unshifted lower rails.
        # The two slim webs preserve the open center channel while giving the
        # shifted drive plate a continuous load path into the elbow hub.
        support_inner_x = support_x + MOTOR_SUPPORT_RIB_DEPTH_X / 2
        rail_outer_x = -LINK_THICKNESS_X / 2
        bridge_width_x = rail_outer_x - support_inner_x
        if bridge_width_x <= 0:
            raise ValueError("Offset wrist motor support must reach the forearm rails.")
        bridge_center_x = support_inner_x + bridge_width_x / 2
        for y in (-LINK_HALF_WIDTH_Y + LINK_RAIL_WIDTH_Y / 2, LINK_HALF_WIDTH_Y - LINK_RAIL_WIDTH_Y / 2):
            with Locations((bridge_center_x, y, MOTOR_SHAFT_Z)):
                Box(
                    bridge_width_x,
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

        pocket_center_x = WRIST_ASSEMBLY_OFFSET_X + WRIST_MOTOR_SIDE_SIGN * (
            LINK_THICKNESS_X / 2 + MOTOR_FACE_THICKNESS_X - MOTOR_BODY_POCKET_DEPTH / 2
        )
        _slotted_x_pocket(
            0,
            MOTOR_SHAFT_Z,
            MOTOR_SLOT_TRAVEL,
            BYJ48_BODY + MOTOR_BODY_POCKET_CLEARANCE,
            x_start=pocket_center_x - MOTOR_BODY_POCKET_DEPTH / 2,
            depth=MOTOR_BODY_POCKET_DEPTH,
        )

        motor_mount_through_x = LINK_THICKNESS_X + MOTOR_FACE_THICKNESS_X + 2.0
        _vertical_slot_along_x(
            0,
            MOTOR_SHAFT_Z,
            MOTOR_SLOT_TRAVEL,
            MOTOR_SHAFT_CLEARANCE,
            x_start=face_x - motor_mount_through_x / 2,
            depth=motor_mount_through_x,
        )

        for y in (-BYJ48_EAR_SPACING / 2, BYJ48_EAR_SPACING / 2):
            _vertical_slot_along_x(
                y,
                MOTOR_SHAFT_Z,
                MOTOR_SLOT_TRAVEL,
                BYJ48_MOUNT_HOLE,
                x_start=face_x - motor_mount_through_x / 2,
                depth=motor_mount_through_x,
            )

        # Top wrist clevis: a bicep-style swept shoulder cut back into two bearing ears.
        add(_build_wrist_swept_hull())
        add(_build_wrist_offset_ear_gusset())

        with Locations(
            (
                WRIST_CLEVIS_GAP_CENTER_X,
                0,
                TOP_WRIST_PIVOT_Z - CLEVIS_HEIGHT_Z / 2 + CLEVIS_BRIDGE_HEIGHT_Z / 2,
            )
        ):
            Box(
                CLEVIS_GAP_X + 2 * CLEVIS_EAR_THICKNESS_X,
                CLEVIS_WIDTH_Y,
                CLEVIS_BRIDGE_HEIGHT_Z,
                align=(Align.CENTER, Align.CENTER, Align.CENTER),
            )

        with Locations((WRIST_CLEVIS_GAP_CENTER_X, 0, TOP_WRIST_PIVOT_Z)):
            _x_cylinder(BEARING_625_ID / 2, CLEVIS_GAP_X + 2 * CLEVIS_EAR_THICKNESS_X + 4.0, Mode.SUBTRACT)

        left_gap_x = WRIST_CLEVIS_GAP_CENTER_X - CLEVIS_GAP_X / 2
        right_gap_x = WRIST_CLEVIS_GAP_CENTER_X + CLEVIS_GAP_X / 2
        pocket_positions_x = (
            left_gap_x - CLEVIS_EAR_THICKNESS_X + BEARING_625_WIDTH / 2,
            right_gap_x + CLEVIS_EAR_THICKNESS_X - BEARING_625_WIDTH / 2,
        )
        for x in pocket_positions_x:
            with Locations((x, 0, TOP_WRIST_PIVOT_Z)):
                _x_cylinder(BEARING_625_OD / 2, BEARING_625_WIDTH, Mode.SUBTRACT)

        _cut_wrist_clevis_clearance()
        _cut_wrist_belt_channels()
        _cut_wrist_belt_loading_relief()

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
