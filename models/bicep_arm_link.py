from __future__ import annotations

from math import atan2, degrees, hypot, isclose

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
        ELBOW_BELT_CENTER_DISTANCE,
        M3_CLEARANCE,
        M3_COUNTERBORE,
        M3_COUNTERBORE_DEPTH,
        NEMA17_HOLE_SPACING,
        NEMA17_PILOT,
        NEMA17_SHAFT,
        SHOULDER_PULLEY_BOLT_CIRCLE,
        assert_printable_extent,
        circle_points,
        export_model,
    )
except ModuleNotFoundError:
    from common import (
        BEARING_625_ID,
        BEARING_625_OD,
        BEARING_625_WIDTH,
        ELBOW_BELT_CENTER_DISTANCE,
        M3_CLEARANCE,
        M3_COUNTERBORE,
        M3_COUNTERBORE_DEPTH,
        NEMA17_HOLE_SPACING,
        NEMA17_PILOT,
        NEMA17_SHAFT,
        SHOULDER_PULLEY_BOLT_CIRCLE,
        assert_printable_extent,
        circle_points,
        export_model,
    )

# Override center distance to match the HTD 342-3M belt specification
ELBOW_BELT_CENTER_DISTANCE = 113.35

PART_NAME = "bicep_arm_link"

LINK_EXTENSION_Z = 10.0
BOTTOM_PIVOT_Z = 0.0
MOTOR_SHAFT_Z = 52.0 + LINK_EXTENSION_Z
TOP_PIVOT_Z = MOTOR_SHAFT_Z + ELBOW_BELT_CENTER_DISTANCE

LOWER_HUB_OD = 38.5
TOP_HUB_OD = 38.0
LINK_X_THICKNESS = 18.0
REAR_WEB_X_THICKNESS = 6.0
SIDE_RAIL_X_THICKNESS = 13.0
ELBOW_CLEVIS_GAP_X = 28.0
ELBOW_CLEVIS_EAR_THICKNESS_X = 8.0
ELBOW_CLEVIS_TOTAL_X = ELBOW_CLEVIS_GAP_X + 2 * ELBOW_CLEVIS_EAR_THICKNESS_X
ELBOW_CLEVIS_DROP_Z = 42.0
ELBOW_CLEVIS_CLEARANCE_Z = 72.0
MOTOR_PLATE_X_THICKNESS = 15.0
MOTOR_PLATE_WIDTH_Y = 54.0
MOTOR_PLATE_HEIGHT_Z = 54.0
MOTOR_SLOT_TRAVEL = 4.0
MOTOR_PLATE_OUTER_X = LINK_X_THICKNESS / 2
MOTOR_FACE_INSET_X = 6.0
MOTOR_FACE_X = MOTOR_PLATE_OUTER_X - MOTOR_FACE_INSET_X
MOTOR_PLATE_BACK_X = MOTOR_PLATE_OUTER_X - MOTOR_PLATE_X_THICKNESS
MOTOR_PLATE_CENTER_X = MOTOR_PLATE_OUTER_X - MOTOR_PLATE_X_THICKNESS / 2
MOTOR_COUNTERBORE_FACE_X = -LINK_X_THICKNESS / 2
MOTOR_COUNTERBORE_DIAMETER = 6.8
MOTOR_COUNTERBORE_SLOT_TRAVEL = MOTOR_SLOT_TRAVEL + 2.0
MOTOR_COUNTERBORE_DEPTH = M3_COUNTERBORE_DEPTH + 2.0
MOTOR_BODY_POCKET_CLEARANCE = 1.2
MOTOR_PILOT_CLEARANCE = NEMA17_PILOT + 0.6
MOTOR_PILOT_POCKET_DEPTH = 3.0
MOTOR_SHAFT_CLEARANCE = NEMA17_SHAFT + 3.0
MOTOR_DRIVER_PULLEY_RELIEF_RADIUS = 14.0
MOTOR_DRIVER_PULLEY_RELIEF_DEPTH = 12.0
PULLEY_CHANNEL_CLEARANCE_X = 0.75
ELBOW_BELT_CHANNEL_FACE_X = -2.5
ELBOW_BELT_CHANNEL_OUTER_X = -12.75
ELBOW_BELT_CHANNEL_WIDTH_Y = 11.0
ELBOW_BELT_CHANNEL_Y_AT_MOTOR = 7.0
ELBOW_BELT_CHANNEL_Y_AT_CLEVIS = 27.0
ELBOW_BELT_CHANNEL_Z_MIN = MOTOR_SHAFT_Z + 4.0
ELBOW_BELT_CHANNEL_Z_MAX = TOP_PIVOT_Z - ELBOW_CLEVIS_CLEARANCE_Z / 2 + 2.0
SHOULDER_PULLEY_EXTRA_CLEARANCE_X = 1.0
SHOULDER_PULLEY_FLAT_FACE_X = -8.5
SHOULDER_PULLEY_FLAT_SIZE_YZ = 84.0
ELBOW_REINFORCEMENT_WIDTH_Y = 46.0
ELBOW_REINFORCEMENT_HEIGHT_Z = 86.0

THROUGH_X = 28.0
A1_NOZZLE_WIDTH = 0.4
SPAN_WINDOW_WIDTH_Y = 15.2
SPAN_WINDOW_TRAVEL_Z = 22.0
SPAN_WINDOW_ZS = tuple(z + LINK_EXTENSION_Z for z in (91.0, 117.0))
SPAN_WINDOW_THROUGH_X = LINK_X_THICKNESS + 2.0
MOTOR_PLATE_RIB_WIDTH_Y = 5.6
MOTOR_PLATE_RIB_HEIGHT_Z = 48.0
MOTOR_PLATE_RIB_DEPTH_X = 4.0


def _x_axis_hole(radius: float, height: float = THROUGH_X, mode: Mode = Mode.SUBTRACT) -> None:
    Cylinder(radius, height, rotation=(0, 90, 0), mode=mode)


def _vertical_slot_along_x(
    y: float,
    z: float,
    travel: float,
    width: float,
    *,
    x_start: float = -THROUGH_X / 2,
    depth: float = THROUGH_X,
) -> None:
    with BuildSketch(Plane.YZ.offset(x_start)) as slot:
        with Locations((y, z)):
            SlotCenterToCenter(travel, width, rotation=90)
    extrude(slot.sketch, amount=depth, mode=Mode.SUBTRACT)


def _vertical_counterbored_slot_along_x(y: float, z: float, travel: float) -> None:
    _vertical_slot_along_x(y, z, travel, M3_CLEARANCE)
    _vertical_slot_along_x(
        y,
        z,
        MOTOR_COUNTERBORE_SLOT_TRAVEL,
        MOTOR_COUNTERBORE_DIAMETER,
        x_start=MOTOR_COUNTERBORE_FACE_X - 0.05,
        depth=MOTOR_COUNTERBORE_DEPTH + 0.1,
    )


def _slotted_pilot_pocket_along_x(z: float, travel: float) -> None:
    pocket_x = MOTOR_FACE_X - MOTOR_PILOT_POCKET_DEPTH / 2
    radius = MOTOR_PILOT_CLEARANCE / 2
    with Locations((pocket_x, 0, z - travel / 2), (pocket_x, 0, z + travel / 2)):
        _x_axis_hole(radius, height=MOTOR_PILOT_POCKET_DEPTH)
    with Locations((pocket_x, 0, z)):
        Box(MOTOR_PILOT_POCKET_DEPTH, MOTOR_PILOT_CLEARANCE, travel, mode=Mode.SUBTRACT)


def _slotted_shaft_hole_along_x(z: float, travel: float) -> None:
    _vertical_slot_along_x(0.0, z, travel, MOTOR_SHAFT_CLEARANCE)


def _counterbored_x_hole(y: float, z: float) -> None:
    with Locations((0, y, z)):
        _x_axis_hole(M3_CLEARANCE / 2)
    with Locations((LINK_X_THICKNESS / 2 - 1.8, y, z)):
        _x_axis_hole(3.0, height=3.8)


def _build_flush_motor_reinforcement():
    with BuildPart() as plate:
        with BuildSketch(Plane.YZ.offset(MOTOR_PLATE_OUTER_X)):
            with Locations((0, MOTOR_SHAFT_Z)):
                RectangleRounded(MOTOR_PLATE_WIDTH_Y, MOTOR_PLATE_HEIGHT_Z, radius=3.0)
        extrude(amount=-MOTOR_PLATE_X_THICKNESS)
    return plate.part


def _cut_motor_body_inset() -> None:
    pocket_size = 42.3 + MOTOR_BODY_POCKET_CLEARANCE
    with Locations((MOTOR_FACE_X + MOTOR_FACE_INSET_X / 2, 0, MOTOR_SHAFT_Z)):
        Box(
            MOTOR_FACE_INSET_X,
            pocket_size,
            pocket_size,
            align=(Align.CENTER, Align.CENTER, Align.CENTER),
            mode=Mode.SUBTRACT,
        )


def _cut_driver_pulley_relief() -> None:
    relief_center_x = MOTOR_FACE_X - MOTOR_DRIVER_PULLEY_RELIEF_DEPTH / 2
    with Locations((relief_center_x, 0, MOTOR_SHAFT_Z)):
        _x_axis_hole(
            MOTOR_DRIVER_PULLEY_RELIEF_RADIUS,
            height=MOTOR_DRIVER_PULLEY_RELIEF_DEPTH,
        )


def _cut_negative_x_flat(face_x: float, width_y: float, z_min: float, z_max: float) -> None:
    if z_max <= z_min:
        raise ValueError("Negative-X clearance channel collapsed.")

    cut_min_x = -ELBOW_CLEVIS_TOTAL_X / 2 - 2.0
    cut_width_x = face_x - cut_min_x
    with Locations((cut_min_x + cut_width_x / 2, 0, z_min + (z_max - z_min) / 2)):
        Box(
            cut_width_x,
            width_y,
            z_max - z_min,
            align=(Align.CENTER, Align.CENTER, Align.CENTER),
            mode=Mode.SUBTRACT,
        )


def _cut_elbow_belt_channel() -> None:
    if ELBOW_BELT_CHANNEL_Z_MAX <= ELBOW_BELT_CHANNEL_Z_MIN:
        raise ValueError("Elbow belt clearance channel collapsed.")

    channel_depth_x = ELBOW_BELT_CHANNEL_FACE_X - ELBOW_BELT_CHANNEL_OUTER_X
    if channel_depth_x <= 0:
        raise ValueError("Elbow belt clearance channel has no X depth.")

    for side in (-1.0, 1.0):
        y_start = side * ELBOW_BELT_CHANNEL_Y_AT_MOTOR
        y_end = side * ELBOW_BELT_CHANNEL_Y_AT_CLEVIS
        z_start = ELBOW_BELT_CHANNEL_Z_MIN
        z_end = ELBOW_BELT_CHANNEL_Z_MAX
        center_y = (y_start + y_end) / 2
        center_z = (z_start + z_end) / 2
        slot_length = hypot(y_end - y_start, z_end - z_start)
        slot_angle = degrees(atan2(z_end - z_start, y_end - y_start))

        with BuildSketch(Plane.YZ.offset(ELBOW_BELT_CHANNEL_OUTER_X)) as channel_slot:
            with Locations((center_y, center_z)):
                SlotCenterToCenter(
                    slot_length,
                    ELBOW_BELT_CHANNEL_WIDTH_Y,
                    rotation=slot_angle,
                )
        extrude(channel_slot.sketch, amount=channel_depth_x, mode=Mode.SUBTRACT)


def _cut_shoulder_pulley_side_flat() -> None:
    _cut_negative_x_flat(
        SHOULDER_PULLEY_FLAT_FACE_X,
        SHOULDER_PULLEY_FLAT_SIZE_YZ,
        BOTTOM_PIVOT_Z - SHOULDER_PULLEY_FLAT_SIZE_YZ / 2,
        BOTTOM_PIVOT_Z + SHOULDER_PULLEY_FLAT_SIZE_YZ / 2,
    )


def _cut_nema17_tension_mount() -> None:
    _slotted_shaft_hole_along_x(MOTOR_SHAFT_Z, MOTOR_SLOT_TRAVEL)
    _slotted_pilot_pocket_along_x(MOTOR_SHAFT_Z, MOTOR_SLOT_TRAVEL)
    half_spacing = NEMA17_HOLE_SPACING / 2
    for y_offset in (-half_spacing, half_spacing):
        for z_offset in (-half_spacing, half_spacing):
            _vertical_counterbored_slot_along_x(y_offset, MOTOR_SHAFT_Z + z_offset, MOTOR_SLOT_TRAVEL)


def _add_elbow_clevis() -> None:
    ear_center_x = ELBOW_CLEVIS_GAP_X / 2 + ELBOW_CLEVIS_EAR_THICKNESS_X / 2
    for x in (-ear_center_x, ear_center_x):
        with Locations((x, 0, TOP_PIVOT_Z)):
            Cylinder(TOP_HUB_OD / 2, ELBOW_CLEVIS_EAR_THICKNESS_X, rotation=(0, 90, 0))
        with Locations((x, 0, TOP_PIVOT_Z - ELBOW_CLEVIS_DROP_Z / 2)):
            Box(
                ELBOW_CLEVIS_EAR_THICKNESS_X,
                30.0,
                ELBOW_CLEVIS_DROP_Z,
                align=(Align.CENTER, Align.CENTER, Align.CENTER),
            )

    with Locations((0, 0, TOP_PIVOT_Z - ELBOW_CLEVIS_DROP_Z + 2.5)):
        Box(
            ELBOW_CLEVIS_TOTAL_X,
            30.0,
            5.0,
            align=(Align.CENTER, Align.CENTER, Align.CENTER),
        )


def _build_elbow_organic_reinforcement():
    outer_x = ELBOW_CLEVIS_TOTAL_X / 2
    with BuildPart() as reinforcement:
        for plane_x, amount in (
            (outer_x, -ELBOW_CLEVIS_EAR_THICKNESS_X),
            (-outer_x, ELBOW_CLEVIS_EAR_THICKNESS_X),
        ):
            with BuildSketch(Plane.YZ.offset(plane_x)):
                with Locations((0, TOP_PIVOT_Z - 24.0)):
                    RectangleRounded(
                        ELBOW_REINFORCEMENT_WIDTH_Y,
                        ELBOW_REINFORCEMENT_HEIGHT_Z,
                        radius=18.0,
                    )
            extrude(amount=amount)
    return reinforcement.part

def _build_swept_monocoque_hull():
    """Builds a continuous, flowing structural body from the base to the elbow."""
    hull_width_y = 40.0
    transition_start_z = MOTOR_SHAFT_Z + 25.0
    clevis_base_z = TOP_PIVOT_Z - ELBOW_CLEVIS_DROP_Z

    with BuildPart() as hull:
        # 1. Lower Section (Straight column from pivot past the motor)
        with BuildSketch(Plane.XY.offset(BOTTOM_PIVOT_Z)):
            RectangleRounded(LINK_X_THICKNESS, LOWER_HUB_OD, radius=5.0)
        with BuildSketch(Plane.XY.offset(transition_start_z)):
            RectangleRounded(LINK_X_THICKNESS, hull_width_y, radius=5.0)
        loft()

        # 2. The Taper (Smoothly flares from 18mm wide to 44mm wide)
        with BuildSketch(Plane.XY.offset(transition_start_z)):
            RectangleRounded(LINK_X_THICKNESS, hull_width_y, radius=5.0)
        with BuildSketch(Plane.XY.offset(clevis_base_z)):
            RectangleRounded(ELBOW_CLEVIS_TOTAL_X, hull_width_y, radius=8.0)
        loft()

        # 3. The Upper Clevis Block (Straight section to house the bearings)
        with BuildSketch(Plane.XY.offset(clevis_base_z)):
            RectangleRounded(ELBOW_CLEVIS_TOTAL_X, hull_width_y, radius=8.0)
        with BuildSketch(Plane.XY.offset(TOP_PIVOT_Z)):
            RectangleRounded(ELBOW_CLEVIS_TOTAL_X, TOP_HUB_OD, radius=8.0)
        loft()

        # 4. Round over the top of the clevis ears perfectly
        with Locations((0, 0, TOP_PIVOT_Z)):
            Cylinder(TOP_HUB_OD / 2, ELBOW_CLEVIS_TOTAL_X, rotation=(0, 90, 0))

    return hull.part




def _add_elbow_organic_reinforcement() -> None:
    add(_build_elbow_organic_reinforcement())


def _cut_rounded_span_window(z: float) -> None:
    """Remove center web mass while leaving continuous side rails and rounded ends."""
    x_start = -SPAN_WINDOW_THROUGH_X / 2
    with BuildSketch(Plane.YZ.offset(x_start)) as slot:
        with Locations((0, z)):
            SlotCenterToCenter(
                SPAN_WINDOW_TRAVEL_Z,
                SPAN_WINDOW_WIDTH_Y,
                rotation=90,
            )
    extrude(slot.sketch, amount=SPAN_WINDOW_THROUGH_X, mode=Mode.SUBTRACT)


def _add_motor_plate_side_ribs() -> None:
    """Small 0.4mm-nozzle-friendly ribs stiffen the offset NEMA17 plate."""
    rib_center_x = MOTOR_PLATE_BACK_X + MOTOR_PLATE_RIB_DEPTH_X / 2
    rib_y = MOTOR_PLATE_WIDTH_Y / 2 - MOTOR_PLATE_RIB_WIDTH_Y / 2
    for y in (-rib_y, rib_y):
        with Locations((rib_center_x, y, MOTOR_SHAFT_Z)):
            Box(
                MOTOR_PLATE_RIB_DEPTH_X,
                MOTOR_PLATE_RIB_WIDTH_Y,
                MOTOR_PLATE_RIB_HEIGHT_Z,
                align=(Align.CENTER, Align.CENTER, Align.CENTER),
            )


def _cut_elbow_clevis_clearance() -> None:
    with Locations((0, 0, TOP_PIVOT_Z)):
        Box(
            ELBOW_CLEVIS_GAP_X,
            72.0,
            ELBOW_CLEVIS_CLEARANCE_Z,
            align=(Align.CENTER, Align.CENTER, Align.CENTER),
            mode=Mode.SUBTRACT,
        )


def _cut_elbow_bearing_pockets() -> None:
    with Locations((0, 0, TOP_PIVOT_Z)):
        _x_axis_hole(BEARING_625_ID / 2, height=ELBOW_CLEVIS_TOTAL_X + 4.0)

    bearing_pocket_depth = BEARING_625_WIDTH + 0.25
    pocket_x = ELBOW_CLEVIS_GAP_X / 2 + bearing_pocket_depth / 2
    for x in (-pocket_x, pocket_x):
        with Locations((x, 0, TOP_PIVOT_Z)):
            _x_axis_hole(BEARING_625_OD / 2, height=bearing_pocket_depth)


def build_model():
    if not isclose(TOP_PIVOT_Z - MOTOR_SHAFT_Z, ELBOW_BELT_CENTER_DISTANCE, abs_tol=0.001):
        raise ValueError("Elbow motor shaft to top pivot spacing must be exactly 113.35mm")
    if LOWER_HUB_OD > 39.0:
        raise ValueError("Lower shoulder pivot Y width must fit inside the 43mm azimuth clevis")
    nozzle_multiple = SPAN_WINDOW_WIDTH_Y / A1_NOZZLE_WIDTH
    if abs(nozzle_multiple - round(nozzle_multiple)) > 1e-9:
        raise ValueError("Span window width should stay on a 0.4mm nozzle multiple.")

    with BuildPart() as bicep:
        # 1. Base Shoulder Hub (Restores the rounded bottom and material for the lower holes)
        with Locations((0, 0, BOTTOM_PIVOT_Z)):
            Cylinder(LOWER_HUB_OD / 2, LINK_X_THICKNESS, rotation=(0, 90, 0))

        # 2. Main Structural Body
        add(_build_swept_monocoque_hull())

        # 3. Flush Motor Reinforcement
        add(_build_flush_motor_reinforcement())
        _add_motor_plate_side_ribs()

        # --- Subtractive Operations ---

        # Shoulder pivot holes
        with Locations((0, 0, BOTTOM_PIVOT_Z)):
            _x_axis_hole(4.0)
        for y, z in circle_points(4, SHOULDER_PULLEY_BOLT_CIRCLE, start_angle=45.0):
            _counterbored_x_hole(y, z)

        # Motor mounts and clearances
        _cut_motor_body_inset()
        _cut_nema17_tension_mount()
        _cut_driver_pulley_relief()
        _cut_elbow_belt_channel()
        _cut_shoulder_pulley_side_flat()

        # Clevis clearance and bearings
        _cut_elbow_clevis_clearance()
        _cut_elbow_bearing_pockets()

        # Web lightening cuts in the center span
        for z in SPAN_WINDOW_ZS:
            _cut_rounded_span_window(z)

    model = bicep.part
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
