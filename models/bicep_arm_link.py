from __future__ import annotations

from math import isclose

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
    add,
    extrude,
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

BOTTOM_PIVOT_Z = 0.0
MOTOR_SHAFT_Z = 52.0
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
MOTOR_BODY_POCKET_CLEARANCE = 1.2
MOTOR_PILOT_CLEARANCE = NEMA17_PILOT + 0.6
MOTOR_PILOT_POCKET_DEPTH = 3.0
MOTOR_SHAFT_CLEARANCE = NEMA17_SHAFT + 3.0
MOTOR_DRIVER_PULLEY_RELIEF_RADIUS = 14.0
MOTOR_DRIVER_PULLEY_RELIEF_DEPTH = 12.0
ELBOW_REINFORCEMENT_WIDTH_Y = 46.0
ELBOW_REINFORCEMENT_HEIGHT_Z = 86.0

THROUGH_X = 28.0


def _x_axis_hole(radius: float, height: float = THROUGH_X, mode: Mode = Mode.SUBTRACT) -> None:
    Cylinder(radius, height, rotation=(0, 90, 0), mode=mode)


def _vertical_slot_along_x(y: float, z: float, travel: float, width: float) -> None:
    radius = width / 2
    with Locations((0, y, z - travel / 2), (0, y, z + travel / 2)):
        _x_axis_hole(radius)
    with Locations((0, y, z)):
        Box(THROUGH_X, width, travel, mode=Mode.SUBTRACT)


def _vertical_counterbored_slot_along_x(y: float, z: float, travel: float) -> None:
    _vertical_slot_along_x(y, z, travel, M3_CLEARANCE)
    custom_depth = M3_COUNTERBORE_DEPTH + 2.0
    inset_x = MOTOR_PLATE_BACK_X + custom_depth / 2
    with Locations((inset_x, y, z)):
        Box(custom_depth, M3_COUNTERBORE, travel, mode=Mode.SUBTRACT)
    for z_offset in (-travel / 2, travel / 2):
        with Locations((inset_x, y, z + z_offset)):
            Cylinder(M3_COUNTERBORE / 2, custom_depth, rotation=(0, 90, 0), mode=Mode.SUBTRACT)


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


def _add_elbow_organic_reinforcement() -> None:
    add(_build_elbow_organic_reinforcement())


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

    rail_length = TOP_PIVOT_Z
    rail_center_z = rail_length / 2

    with BuildPart() as bicep:
        with Locations((0, 0, BOTTOM_PIVOT_Z)):
            Cylinder(LOWER_HUB_OD / 2, LINK_X_THICKNESS, rotation=(0, 90, 0))
        with Locations((-REAR_WEB_X_THICKNESS / 2, 0, rail_center_z)):
            Box(REAR_WEB_X_THICKNESS, 35.0, rail_length, align=(Align.CENTER, Align.CENTER, Align.CENTER))
        for rail_y in (-15.0, 15.0):
            with Locations((LINK_X_THICKNESS / 2 - SIDE_RAIL_X_THICKNESS / 2, rail_y, rail_center_z)):
                Box(SIDE_RAIL_X_THICKNESS, 5.0, rail_length, align=(Align.CENTER, Align.CENTER, Align.CENTER))

        add(_build_flush_motor_reinforcement())

        _add_elbow_clevis()
        _add_elbow_organic_reinforcement()
        with Locations((0, 0, BOTTOM_PIVOT_Z)):
            _x_axis_hole(4.0)
        for y, z in circle_points(4, SHOULDER_PULLEY_BOLT_CIRCLE, start_angle=45.0):
            _counterbored_x_hole(y, z)

        _cut_motor_body_inset()
        _cut_nema17_tension_mount()
        _cut_driver_pulley_relief()
        _cut_elbow_clevis_clearance()
        _cut_elbow_bearing_pockets()

        # Adjusted pocket steps for web-lightening over the longer span
        for z in (95.0, 125.0):
            with Locations((0, 0, z)):
                Box(THROUGH_X, 14.0, 18.0, mode=Mode.SUBTRACT)

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
