from __future__ import annotations
from math import cos, radians, sin

from build123d import (
    Align,
    Box,
    BuildPart,
    BuildSketch,
    Circle,
    Cylinder,
    Location,
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
        BASE_GEAR_BOLT_CIRCLE,
        BEARING_608_ID,
        BEARING_608_OD,
        BEARING_608_WIDTH,
        M3_CLEARANCE,
        M3_TAP_HOLE,
        NEMA17_HOLE_SPACING,
        NEMA17_PILOT,
        SHOULDER_BELT_CENTER_DISTANCE,
        assert_printable_extent,
        circle_points,
        export_model,
    )
    from models.electronics_mounts import (
        STANDOFF_DIAMETER as ARDUINO_STANDOFF_DIAMETER,
        STANDOFF_PILOT as ARDUINO_STANDOFF_PILOT,
        UNO_BOARD_X,
        UNO_BOARD_Y,
        UNO_HOLE_POINTS,
    )
except ModuleNotFoundError:
    from common import (
        BASE_GEAR_BOLT_CIRCLE,
        BEARING_608_ID,
        BEARING_608_OD,
        BEARING_608_WIDTH,
        M3_CLEARANCE,
        M3_TAP_HOLE,
        NEMA17_HOLE_SPACING,
        NEMA17_PILOT,
        SHOULDER_BELT_CENTER_DISTANCE,
        assert_printable_extent,
        circle_points,
        export_model,
    )
    from electronics_mounts import (
        STANDOFF_DIAMETER as ARDUINO_STANDOFF_DIAMETER,
        STANDOFF_PILOT as ARDUINO_STANDOFF_PILOT,
        UNO_BOARD_X,
        UNO_BOARD_Y,
        UNO_HOLE_POINTS,
    )


MODEL_NAME = "azimuth_turntable_shoulder_cleat"

PLATE_RADIUS = 72.0
PLATE_THICKNESS = 12.0
OUTER_RIM_WIDTH = 8.0
OUTER_RIM_THICKNESS = 6.0
GEAR_HUB_RADIUS = 40.0
DECK_SPOKE_WIDTH = 8.0
CENTER_SHAFT_CLEARANCE = BEARING_608_ID + 0.5
STATOR_BOSS_RELIEF_DIAMETER = 49.0
STATOR_BOSS_RELIEF_DEPTH = 7.0
BASE_GEAR_THREAD_PILOT = M3_TAP_HOLE
BASE_GEAR_THREAD_DEPTH = 9.0

CLEVIS_CLEAR_GAP = 43.0
CLEVIS_WALL_THICKNESS = 12.0
CLEVIS_ROOT_THICKNESS = 18.0
CLEVIS_DEPTH = 90.0
CLEVIS_ROOT_DEPTH = 102.0
CLEVIS_TOP_RADIUS = 25.0

MOTOR_SHAFT_Z = 40.0
PIVOT_Z = MOTOR_SHAFT_Z + SHOULDER_BELT_CENTER_DISTANCE

MOTOR_SLOT_TRAVEL = 4.0
CLEVIS_TAPER_MID_Z = MOTOR_SHAFT_Z + 35.0
CLEVIS_TAPER_MID_DEPTH = 78.0

OUTER_CLEVIS_WIDTH = CLEVIS_CLEAR_GAP + 2 * CLEVIS_WALL_THICKNESS
LEFT_WALL_X = -(CLEVIS_CLEAR_GAP / 2 + CLEVIS_WALL_THICKNESS / 2)
RIGHT_WALL_X = -LEFT_WALL_X
LEFT_OUTER_X = -OUTER_CLEVIS_WIDTH / 2
RIGHT_OUTER_X = OUTER_CLEVIS_WIDTH / 2

ELBOW_MOTOR_RELIEF_Y = 70.0
ELBOW_MOTOR_RELIEF_TOP_MARGIN = 25.0
ELBOW_MOTOR_RELIEF_Z_MIN = PLATE_THICKNESS + 4.0
ELBOW_MOTOR_RELIEF_Z_MAX = PIVOT_Z - ELBOW_MOTOR_RELIEF_TOP_MARGIN
ELBOW_MOTOR_RELIEF_BACK_SKIN = 3.2  # Eight 0.4 mm extrusion widths
ELBOW_MOTOR_RELIEF_BOTTOM_RADIUS = 10.0
ELBOW_MOTOR_RELIEF_TOP_RADIUS = 28.0
ARDUINO_STANDOFF_HEIGHT = 4.0
ARDUINO_BOARD_BOTTOM_CLEARANCE = 0.5
# Keep the board low: a bare PCB only reaches the elbow motor at the nominal
# +/-130 degree endpoints. Revalidate limits with the populated board installed.
ARDUINO_BOARD_CENTER_Z = (
    ELBOW_MOTOR_RELIEF_Z_MIN + UNO_BOARD_X / 2 + ARDUINO_BOARD_BOTTOM_CLEARANCE
)
ARDUINO_STANDOFF_POINTS_YZ = tuple(
    (board_y, ARDUINO_BOARD_CENTER_Z + board_x) for board_x, board_y in UNO_HOLE_POINTS
)
UPPER_WINDOW_WIDTH_Y = 24.0
UPPER_WINDOW_HEIGHT_Z = 28.0
UPPER_WINDOW_CENTER_Z = 91.0


def _build_clevis_wall(side_sign: float):
    """Loft one rounded, outward-flared monocoque clevis wall."""
    wall_x = side_sign * (CLEVIS_CLEAR_GAP / 2 + CLEVIS_WALL_THICKNESS / 2)
    root_x = side_sign * (CLEVIS_CLEAR_GAP / 2 + CLEVIS_ROOT_THICKNESS / 2)
    root_top_z = PLATE_THICKNESS + (CLEVIS_ROOT_THICKNESS - CLEVIS_WALL_THICKNESS)
    taper_mid_z = CLEVIS_TAPER_MID_Z

    with BuildPart() as wall:
        # A six-millimeter-high 45-degree root flare prints without supports.
        with BuildSketch(Plane.XY.offset(PLATE_THICKNESS)):
            with Locations((root_x, 0)):
                RectangleRounded(
                    CLEVIS_ROOT_THICKNESS,
                    CLEVIS_ROOT_DEPTH,
                    radius=7.0,
                )
        with BuildSketch(Plane.XY.offset(root_top_z)):
            with Locations((wall_x, 0)):
                RectangleRounded(
                    CLEVIS_WALL_THICKNESS,
                    CLEVIS_DEPTH,
                    radius=5.0,
                )
        loft()

        with BuildSketch(Plane.XY.offset(root_top_z)):
            with Locations((wall_x, 0)):
                RectangleRounded(
                    CLEVIS_WALL_THICKNESS,
                    CLEVIS_DEPTH,
                    radius=5.0,
                )
        with BuildSketch(Plane.XY.offset(taper_mid_z)):
            with Locations((wall_x, 0)):
                RectangleRounded(
                    CLEVIS_WALL_THICKNESS,
                    CLEVIS_TAPER_MID_DEPTH,
                    radius=5.0,
                )
        loft()

        with BuildSketch(Plane.XY.offset(taper_mid_z)):
            with Locations((wall_x, 0)):
                RectangleRounded(
                    CLEVIS_WALL_THICKNESS,
                    CLEVIS_TAPER_MID_DEPTH,
                    radius=5.0,
                )
        with BuildSketch(Plane.XY.offset(PIVOT_Z)):
            with Locations((wall_x, 0)):
                RectangleRounded(
                    CLEVIS_WALL_THICKNESS,
                    2 * CLEVIS_TOP_RADIUS,
                    radius=5.0,
                )
        loft()

        with Locations((wall_x, 0, PIVOT_Z)):
            Cylinder(
                CLEVIS_TOP_RADIUS,
                CLEVIS_WALL_THICKNESS,
                rotation=(0, 90, 0),
                align=(Align.CENTER, Align.CENTER, Align.CENTER),
            )

    return wall.part


def _add_clevis_walls() -> None:
    """Add mirrored walls while preserving the 43 mm shoulder stack gap."""
    for side_sign in (-1.0, 1.0):
        add(_build_clevis_wall(side_sign))


def _add_lightweight_turntable_deck() -> None:
    """Build an open rim-and-spoke deck around the full-depth gear hub."""
    with BuildSketch(Plane.XY) as rim:
        Circle(PLATE_RADIUS)
        Circle(PLATE_RADIUS - OUTER_RIM_WIDTH, mode=Mode.SUBTRACT)
    extrude(rim.sketch, amount=OUTER_RIM_THICKNESS)

    Cylinder(
        GEAR_HUB_RADIUS,
        PLATE_THICKNESS,
        align=(Align.CENTER, Align.CENTER, Align.MIN),
    )

    spoke_center_radius = (GEAR_HUB_RADIUS + PLATE_RADIUS - OUTER_RIM_WIDTH / 2) / 2
    spoke_center_distance = PLATE_RADIUS - OUTER_RIM_WIDTH / 2 - GEAR_HUB_RADIUS
    with BuildSketch(Plane.XY) as spokes:
        for angle in range(0, 360, 60):
            angle_radians = radians(angle)
            with Locations(
                Location(
                    (
                        spoke_center_radius * cos(angle_radians),
                        spoke_center_radius * sin(angle_radians),
                        0,
                    ),
                    (0, 0, angle),
                )
            ):
                SlotCenterToCenter(spoke_center_distance, DECK_SPOKE_WIDTH)
    extrude(spokes.sketch, amount=OUTER_RIM_THICKNESS)

    # Full-depth rounded rails directly support the two clevis roots.
    root_x = CLEVIS_CLEAR_GAP / 2 + CLEVIS_ROOT_THICKNESS / 2
    with BuildSketch(Plane.XY) as rails:
        with Locations((-root_x, 0), (root_x, 0)):
            RectangleRounded(
                CLEVIS_ROOT_THICKNESS,
                CLEVIS_ROOT_DEPTH,
                radius=7.0,
            )
    extrude(rails.sketch, amount=PLATE_THICKNESS)


def _add_vertical_m3_slot_through_x(
    x: float, y: float, z: float, through_length: float
) -> None:
    """Cut one M3 vertical adjustment slot and an inside recess for flush bolt heads."""
    with Locations((x, y, z)):
        Box(
            through_length,
            M3_CLEARANCE,
            MOTOR_SLOT_TRAVEL,
            align=(Align.CENTER, Align.CENTER, Align.CENTER),
            mode=Mode.SUBTRACT,
        )
    for z_offset in (-MOTOR_SLOT_TRAVEL / 2, MOTOR_SLOT_TRAVEL / 2):
        with Locations((x, y, z + z_offset)):
            Cylinder(
                M3_CLEARANCE / 2,
                through_length,
                rotation=(0, 90, 0),
                align=(Align.CENTER, Align.CENTER, Align.CENTER),
                mode=Mode.SUBTRACT,
            )

    recess_depth = 3.5
    recess_dia = 6.5
    recess_x = -CLEVIS_CLEAR_GAP / 2 - recess_depth / 2
    with Locations((recess_x, y, z)):
        Box(
            recess_depth,
            recess_dia,
            MOTOR_SLOT_TRAVEL,
            align=(Align.CENTER, Align.CENTER, Align.CENTER),
            mode=Mode.SUBTRACT,
        )
    for z_offset in (-MOTOR_SLOT_TRAVEL / 2, MOTOR_SLOT_TRAVEL / 2):
        with Locations((recess_x, y, z + z_offset)):
            Cylinder(
                recess_dia / 2,
                recess_depth,
                rotation=(0, 90, 0),
                align=(Align.CENTER, Align.CENTER, Align.CENTER),
                mode=Mode.SUBTRACT,
            )


def _cut_nema17_horizontal_face_mount(
    x: float, z: float, through_length: float
) -> None:
    """Cut NEMA17 pilot and vertically slotted mount holes along the X axis."""
    with Locations((x, 0, z)):
        Cylinder(
            NEMA17_PILOT / 2,
            through_length,
            rotation=(0, 90, 0),
            align=(Align.CENTER, Align.CENTER, Align.CENTER),
            mode=Mode.SUBTRACT,
        )

    half_spacing = NEMA17_HOLE_SPACING / 2
    for y_offset in (-half_spacing, half_spacing):
        for z_offset in (-half_spacing, half_spacing):
            _add_vertical_m3_slot_through_x(x, y_offset, z + z_offset, through_length)


def _cut_608_pivot_pockets() -> None:
    """Cut coaxial 608 pockets into the outer faces of both upper clevis walls."""
    through_length = OUTER_CLEVIS_WIDTH + 8.0
    with Locations((0, 0, PIVOT_Z)):
        Cylinder(
            BEARING_608_ID / 2,
            through_length,
            rotation=(0, 90, 0),
            align=(Align.CENTER, Align.CENTER, Align.CENTER),
            mode=Mode.SUBTRACT,
        )

    left_pocket_x = LEFT_OUTER_X + BEARING_608_WIDTH / 2
    right_pocket_x = RIGHT_OUTER_X - BEARING_608_WIDTH / 2
    for pocket_x in (left_pocket_x, right_pocket_x):
        with Locations((pocket_x, 0, PIVOT_Z)):
            Cylinder(
                BEARING_608_OD / 2,
                BEARING_608_WIDTH,
                rotation=(0, 90, 0),
                align=(Align.CENTER, Align.CENTER, Align.CENTER),
                mode=Mode.SUBTRACT,
            )


def _cut_right_elbow_motor_swing_relief() -> None:
    """Open a large radiused motor-swing window through the right wall."""
    relief_height = ELBOW_MOTOR_RELIEF_Z_MAX - ELBOW_MOTOR_RELIEF_Z_MIN
    if relief_height <= 0:
        raise ValueError("Elbow motor relief window collapsed.")

    relief_z = ELBOW_MOTOR_RELIEF_Z_MIN + relief_height / 2
    lower_relief_height = relief_height / 2
    lower_relief_z = ELBOW_MOTOR_RELIEF_Z_MIN + lower_relief_height / 2
    relief_start_x = CLEVIS_CLEAR_GAP / 2 + ELBOW_MOTOR_RELIEF_BACK_SKIN
    with BuildSketch(Plane.YZ.offset(relief_start_x)) as relief:
        with Locations((0, relief_z)):
            RectangleRounded(
                ELBOW_MOTOR_RELIEF_Y,
                relief_height,
                radius=ELBOW_MOTOR_RELIEF_TOP_RADIUS,
            )
        # Expand only the lower corners back to the original 10 mm radius.
        # The larger upper radius fills the two small gaps without new ribs.
        with Locations((0, lower_relief_z)):
            RectangleRounded(
                ELBOW_MOTOR_RELIEF_Y,
                lower_relief_height,
                radius=ELBOW_MOTOR_RELIEF_BOTTOM_RADIUS,
            )
    extrude(
        relief.sketch,
        amount=CLEVIS_ROOT_THICKNESS - ELBOW_MOTOR_RELIEF_BACK_SKIN + 0.2,
        mode=Mode.SUBTRACT,
    )


def _add_arduino_uno_standoffs() -> None:
    """Add four recessed, M3-tapped Arduino Uno R4 mounting bosses."""
    relief_floor_x = CLEVIS_CLEAR_GAP / 2 + ELBOW_MOTOR_RELIEF_BACK_SKIN
    boss_center_x = relief_floor_x + ARDUINO_STANDOFF_HEIGHT / 2 - 0.2
    for y, z in ARDUINO_STANDOFF_POINTS_YZ:
        with Locations((boss_center_x, y, z)):
            Cylinder(
                ARDUINO_STANDOFF_DIAMETER / 2,
                ARDUINO_STANDOFF_HEIGHT,
                rotation=(0, 90, 0),
                align=(Align.CENTER, Align.CENTER, Align.CENTER),
            )
            Cylinder(
                ARDUINO_STANDOFF_PILOT / 2,
                ARDUINO_STANDOFF_HEIGHT + 0.8,
                rotation=(0, 90, 0),
                align=(Align.CENTER, Align.CENTER, Align.CENTER),
                mode=Mode.SUBTRACT,
            )


def _cut_left_upper_lightening_window() -> None:
    """Remove low-stress web above the shoulder motor with rounded ends."""
    window_start_x = LEFT_OUTER_X - 0.1
    with BuildSketch(Plane.YZ.offset(window_start_x)) as window:
        with Locations((0, UPPER_WINDOW_CENTER_Z)):
            RectangleRounded(
                UPPER_WINDOW_WIDTH_Y,
                UPPER_WINDOW_HEIGHT_Z,
                radius=8.0,
            )
    extrude(
        window.sketch,
        amount=CLEVIS_WALL_THICKNESS + 0.2,
        mode=Mode.SUBTRACT,
    )


def build_model():
    if abs((PIVOT_Z - MOTOR_SHAFT_Z) - SHOULDER_BELT_CENTER_DISTANCE) > 1e-9:
        raise ValueError("Shoulder NEMA17 shaft to pivot center distance drifted.")
    if UNO_BOARD_Y > ELBOW_MOTOR_RELIEF_Y:
        raise ValueError("Arduino Uno is too wide for the recessed clevis face.")
    board_z_min = ARDUINO_BOARD_CENTER_Z - UNO_BOARD_X / 2
    board_z_max = ARDUINO_BOARD_CENTER_Z + UNO_BOARD_X / 2
    if not (
        ELBOW_MOTOR_RELIEF_Z_MIN <= board_z_min
        and board_z_max <= ELBOW_MOTOR_RELIEF_Z_MAX
    ):
        raise ValueError(
            "Arduino Uno does not fit vertically inside the clevis recess."
        )

    with BuildPart() as part:
        _add_lightweight_turntable_deck()

        with Locations((0, 0, STATOR_BOSS_RELIEF_DEPTH / 2 - 0.1)):
            Cylinder(
                STATOR_BOSS_RELIEF_DIAMETER / 2,
                STATOR_BOSS_RELIEF_DEPTH + 0.2,
                align=(Align.CENTER, Align.CENTER, Align.CENTER),
                mode=Mode.SUBTRACT,
            )

        with Locations((0, 0, PLATE_THICKNESS / 2)):
            Cylinder(
                CENTER_SHAFT_CLEARANCE / 2,
                PLATE_THICKNESS + 2.0,
                align=(Align.CENTER, Align.CENTER, Align.CENTER),
                mode=Mode.SUBTRACT,
            )

        _add_clevis_walls()

        for hole_x, hole_y in circle_points(6, BASE_GEAR_BOLT_CIRCLE, start_angle=30.0):
            with Locations((hole_x, hole_y, BASE_GEAR_THREAD_DEPTH / 2 - 0.1)):
                Cylinder(
                    BASE_GEAR_THREAD_PILOT / 2,
                    BASE_GEAR_THREAD_DEPTH + 0.2,
                    align=(Align.CENTER, Align.CENTER, Align.CENTER),
                    mode=Mode.SUBTRACT,
                )

        _cut_nema17_horizontal_face_mount(
            x=LEFT_OUTER_X,
            z=MOTOR_SHAFT_Z,
            through_length=CLEVIS_WALL_THICKNESS + 20.0,
        )
        _cut_right_elbow_motor_swing_relief()
        _cut_left_upper_lightening_window()
        _cut_608_pivot_pockets()
        _add_arduino_uno_standoffs()

    model = part.part
    size = model.bounding_box().size
    assert_printable_extent((size.X, size.Y, size.Z))
    return model


def main() -> None:
    model = build_model()
    export_model(model, MODEL_NAME)

    try:
        from ocp_vscode import show
    except ImportError:
        return

    show(model)


if __name__ == "__main__":
    main()
