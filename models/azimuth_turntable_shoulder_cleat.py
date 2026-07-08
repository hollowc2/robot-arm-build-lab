from __future__ import annotations

from build123d import (
    Align,
    Box,
    BuildLine,
    BuildPart,
    BuildSketch,
    Cylinder,
    Location,
    Locations,
    Mode,
    Plane,
    Polygon,
    Polyline,
    ThreePointArc,
    add,
    extrude,
    make_face,
)

try:
    from models.common import (
        BASE_GEAR_BOLT_CIRCLE,
        BEARING_608_ID,
        BEARING_608_OD,
        BEARING_608_WIDTH,
        M3_CLEARANCE,
        NEMA17_HOLE_SPACING,
        NEMA17_PILOT,
        SHOULDER_BELT_CENTER_DISTANCE,
        assert_printable_extent,
        circle_points,
        export_model,
    )
except ModuleNotFoundError:
    from common import (
        BASE_GEAR_BOLT_CIRCLE,
        BEARING_608_ID,
        BEARING_608_OD,
        BEARING_608_WIDTH,
        M3_CLEARANCE,
        NEMA17_HOLE_SPACING,
        NEMA17_PILOT,
        SHOULDER_BELT_CENTER_DISTANCE,
        assert_printable_extent,
        circle_points,
        export_model,
    )


MODEL_NAME = "azimuth_turntable_shoulder_cleat"

PLATE_RADIUS = 72.0
PLATE_THICKNESS = 12.0
DOWNWARD_BOSS_LENGTH = 8.0
DOWNWARD_BOSS_DIAMETER = BEARING_608_ID

CLEVIS_CLEAR_GAP = 43.0
CLEVIS_WALL_THICKNESS = 12.0
CLEVIS_DEPTH = 90.0  # Widened to provide solid pillars around the motor swing relief
CLEVIS_TOP_RADIUS = 25.0

MOTOR_SHAFT_Z = 40.0
PIVOT_Z = MOTOR_SHAFT_Z + SHOULDER_BELT_CENTER_DISTANCE

MOTOR_PAD_THICKNESS = 4.0
MOTOR_PAD_FACE = 54.0
MOTOR_SLOT_TRAVEL = 4.0

OUTER_CLEVIS_WIDTH = CLEVIS_CLEAR_GAP + 2 * CLEVIS_WALL_THICKNESS
LEFT_WALL_X = -(CLEVIS_CLEAR_GAP / 2 + CLEVIS_WALL_THICKNESS / 2)
RIGHT_WALL_X = -LEFT_WALL_X
LEFT_OUTER_X = -OUTER_CLEVIS_WIDTH / 2
RIGHT_OUTER_X = OUTER_CLEVIS_WIDTH / 2

ELBOW_MOTOR_RELIEF_SIDE_CLEARANCE = 8.0
ELBOW_MOTOR_RELIEF_Y = 70.0
ELBOW_MOTOR_RELIEF_TOP_MARGIN = 25.0
ELBOW_MOTOR_RELIEF_Z_MIN = PLATE_THICKNESS + 4.0
ELBOW_MOTOR_RELIEF_Z_MAX = PIVOT_Z - ELBOW_MOTOR_RELIEF_TOP_MARGIN


def _build_clevis_wall():
    """Build one shaft-holder side plate, tapering to a smaller circular top."""
    base_radius = CLEVIS_DEPTH / 2
    top_radius = CLEVIS_TOP_RADIUS

    with BuildPart() as wall:
        with BuildSketch(Plane.YZ):
            with BuildLine():
                Polyline(
                    (-base_radius, PLATE_THICKNESS),
                    (base_radius, PLATE_THICKNESS),
                    (top_radius, PIVOT_Z),
                )
                # ThreePointArc forces the bulge upwards through the exact top-center
                ThreePointArc(
                    (top_radius, PIVOT_Z),
                    (0, PIVOT_Z + top_radius),
                    (-top_radius, PIVOT_Z),
                )
                Polyline(
                    (-top_radius, PIVOT_Z),
                    (-base_radius, PLATE_THICKNESS),
                )
            make_face()
        extrude(amount=CLEVIS_WALL_THICKNESS / 2, both=True)
    return wall.part


def _add_clevis_walls() -> None:
    """Add both shaft-holder side plates without narrowing the 43 mm gap."""
    wall = _build_clevis_wall()
    for wall_x in (LEFT_WALL_X, RIGHT_WALL_X):
        add(wall.moved(Location((wall_x, 0, 0))))


def _add_right_wall_gussets() -> None:
    """Add small, clean structural triangular gussets to the thin right wall pillars."""
    gusset_height = PLATE_THICKNESS + 25.0
    gusset_ext_x = RIGHT_OUTER_X + 12.0
    # Start 2mm inside the wall to guarantee a perfect manifold union
    gusset_start_x = RIGHT_OUTER_X - 2.0

    with BuildPart() as rib:
        with BuildSketch(Plane.XZ):
            Polygon([
                (gusset_start_x, PLATE_THICKNESS),
                (gusset_start_x, gusset_height),
                (gusset_ext_x, PLATE_THICKNESS),
            ])
        # Extrude 4mm both ways to make an 8mm wide rib that sits clean on the 10mm pillar
        extrude(amount=4.0, both=True)

    # Place the ribs centered on the solid pillars outside the 70mm relief window
    for y_offset in (-40.0, 40.0):
        add(rib.part.moved(Location((0, y_offset, 0))))


def _add_vertical_m3_slot_through_x(x: float, y: float, z: float, through_length: float) -> None:
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


def _cut_nema17_horizontal_face_mount(x: float, z: float, through_length: float) -> None:
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
    """Open the right clevis side below the shoulder pivot for the elbow motor body."""
    relief_height = ELBOW_MOTOR_RELIEF_Z_MAX - ELBOW_MOTOR_RELIEF_Z_MIN
    if relief_height <= 0:
        raise ValueError("Elbow motor relief window collapsed.")

    relief_x = RIGHT_OUTER_X + ELBOW_MOTOR_RELIEF_SIDE_CLEARANCE / 2
    relief_width = CLEVIS_WALL_THICKNESS + ELBOW_MOTOR_RELIEF_SIDE_CLEARANCE + 0.2
    relief_z = ELBOW_MOTOR_RELIEF_Z_MIN + relief_height / 2

    with Locations((relief_x, 0, relief_z)):
        Box(
            relief_width,
            ELBOW_MOTOR_RELIEF_Y,
            relief_height,
            align=(Align.CENTER, Align.CENTER, Align.CENTER),
            mode=Mode.SUBTRACT,
        )


def build_model():
    if abs((PIVOT_Z - MOTOR_SHAFT_Z) - SHOULDER_BELT_CENTER_DISTANCE) > 1e-9:
        raise ValueError("Shoulder NEMA17 shaft to pivot center distance drifted.")

    with BuildPart() as part:
        Cylinder(
            PLATE_RADIUS,
            PLATE_THICKNESS,
            align=(Align.CENTER, Align.CENTER, Align.MIN),
        )

        with Locations((0, 0, -DOWNWARD_BOSS_LENGTH / 2)):
            Cylinder(
                DOWNWARD_BOSS_DIAMETER / 2,
                DOWNWARD_BOSS_LENGTH,
                align=(Align.CENTER, Align.CENTER, Align.CENTER),
            )

        _add_clevis_walls()

        motor_pad_x = LEFT_OUTER_X - MOTOR_PAD_THICKNESS / 2
        with Locations((motor_pad_x, 0, MOTOR_SHAFT_Z)):
            Box(
                MOTOR_PAD_THICKNESS,
                MOTOR_PAD_FACE,
                MOTOR_PAD_FACE,
                align=(Align.CENTER, Align.CENTER, Align.CENTER),
            )

        # Internal foot on the right side to keep the outside clean and remain hidden.
        foot_z = PLATE_THICKNESS + 5.0
        with Locations((CLEVIS_CLEAR_GAP / 2, 0, foot_z)):
            Box(
                8.0,
                CLEVIS_DEPTH,
                10.0,
                align=(Align.MAX, Align.CENTER, Align.CENTER),
            )

        for hole_x, hole_y in circle_points(6, BASE_GEAR_BOLT_CIRCLE, start_angle=30.0):
            with Locations((hole_x, hole_y, PLATE_THICKNESS / 2)):
                Cylinder(
                    M3_CLEARANCE / 2,
                    PLATE_THICKNESS + 4.0,
                    align=(Align.CENTER, Align.CENTER, Align.CENTER),
                    mode=Mode.SUBTRACT,
                )

        _cut_nema17_horizontal_face_mount(
            x=LEFT_OUTER_X - MOTOR_PAD_THICKNESS / 2,
            z=MOTOR_SHAFT_Z,
            through_length=MOTOR_PAD_THICKNESS + CLEVIS_WALL_THICKNESS + 20.0,
        )
        _cut_right_elbow_motor_swing_relief()
        _cut_608_pivot_pockets()

        # Add the structural gussets last so they cleanly join the finished wall
        _add_right_wall_gussets()

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
