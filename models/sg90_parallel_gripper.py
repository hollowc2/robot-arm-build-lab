from __future__ import annotations

from math import atan2, cos, degrees, hypot, sin, radians

from build123d import (
    Align,
    Box,
    BuildPart,
    BuildSketch,
    Compound,
    Cylinder,
    Locations,
    Mode,
    Plane,
    Polygon,
    Pos,
    extrude,
)

try:
    from models.common import M3_CLEARANCE, M3_TAP_HOLE, assert_printable_extent, export_model
    from models import sg90_gripper_base as base_model
except ModuleNotFoundError:
    from common import M3_CLEARANCE, M3_TAP_HOLE, assert_printable_extent, export_model
    import sg90_gripper_base as base_model


MODEL_NAME = "sg90_parallel_gripper"

PIVOT_X = base_model.SERVO_CENTER_X
PIVOT_Y = base_model.GRIPPER_POST_Y
SERVO_SHAFT_Y = base_model.SERVO_SHAFT_Y

JAW_THICKNESS = 4.0
JAW_Z_CENTER = base_model.PLATE_THICKNESS / 2 + base_model.GRIPPER_POST_HEIGHT - JAW_THICKNESS / 2
JAW_PIVOT_CLEARANCE = base_model.GRIPPER_POST_DIAMETER + 0.5
JAW_RETAINING_SCREW_PILOT = M3_TAP_HOLE
JAW_DRIVE_HOLE_OFFSET_U = -3.5
JAW_DRIVE_HOLE_OFFSET_Y = 17.0
JAW_TIP_Y = PIVOT_Y + 61.0
JAW_TIP_GAP = 13.0
JAW_MAX_WIDTH_X = 45.0

HORN_THICKNESS = 3.0
HORN_Z_CENTER = base_model.PLATE_THICKNESS / 2 + 6.2
HORN_LINK_Y = SERVO_SHAFT_Y + 15.5
HORN_LINK_OUTBOARD_X = 6.0
HORN_CENTER_SCREW_CLEARANCE = 2.2
HORN_STOCK_SCREW_PILOT = 1.2

LINK_THICKNESS = 3.0
LINK_WIDTH = 6.5
LINK_Z_CENTER = JAW_Z_CENTER + JAW_THICKNESS / 2 + LINK_THICKNESS / 2 + 0.8

PAD_THICKNESS = 2.4
PAD_HEIGHT = 14.0
PAD_Z_CENTER = JAW_Z_CENTER

OVERALL_WIDTH = max(base_model.OVERALL_WIDTH, JAW_MAX_WIDTH_X)
OVERALL_LENGTH = JAW_TIP_Y + 3.0
OVERALL_HEIGHT = LINK_Z_CENTER + LINK_THICKNESS / 2


def _signed_points(side: int, pivot_x: float, points_uv: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """Map jaw-local inward/forward points into gripper XY coordinates."""
    inward_x = -side
    return [(pivot_x + inward_x * u, PIVOT_Y + y) for u, y in points_uv]


def _capsule_between(
    start: tuple[float, float],
    end: tuple[float, float],
    *,
    width: float,
    thickness: float,
    z_center: float,
    label: str,
):
    sx, sy = start
    ex, ey = end
    dx = ex - sx
    dy = ey - sy
    length = hypot(dx, dy)
    if length <= 0:
        raise ValueError("capsule endpoints must be distinct")
    nx = -dy / length
    ny = dx / length
    half_width = width / 2
    outline = [
        (sx + nx * half_width, sy + ny * half_width),
        (ex + nx * half_width, ey + ny * half_width),
        (ex - nx * half_width, ey - ny * half_width),
        (sx - nx * half_width, sy - ny * half_width),
    ]

    with BuildPart() as link:
        with BuildSketch(Plane.XY):
            Polygon(outline)
        extrude(amount=thickness, both=True)
        for x, y in (start, end):
            with Locations((x, y, 0)):
                Cylinder(width / 2, thickness, align=(Align.CENTER, Align.CENTER, Align.CENTER))
                Cylinder(
                    M3_CLEARANCE / 2,
                    thickness + 1.0,
                    align=(Align.CENTER, Align.CENTER, Align.CENTER),
                    mode=Mode.SUBTRACT,
                )

    part = link.part.moved(Pos(0, 0, z_center))
    part.label = label
    return part


def _build_jaw(side: int):
    pivot_x = side * PIVOT_X
    jaw_outline = _signed_points(
        side,
        pivot_x,
        [
            (-6.5, -8.0),
            (6.0, -7.0),
            (7.3, 15.0),
            (12.0, 40.0),
            (9.4, 56.0),
            (5.0, 61.0),
            (-2.5, 57.5),
            (-5.4, 25.0),
        ],
    )
    drive_x, drive_y = _signed_points(
        side,
        pivot_x,
        [(JAW_DRIVE_HOLE_OFFSET_U, JAW_DRIVE_HOLE_OFFSET_Y)],
    )[0]
    spring_x, spring_y = _signed_points(side, pivot_x, [(-4.0, 45.0)])[0]
    pad_center_x = side * (JAW_TIP_GAP / 2 + PAD_THICKNESS / 2)

    with BuildPart() as jaw:
        with BuildSketch(Plane.XY):
            Polygon(jaw_outline)
        extrude(amount=JAW_THICKNESS, both=True)

        for x, y, diameter in (
            (pivot_x, PIVOT_Y, JAW_PIVOT_CLEARANCE),
            (drive_x, drive_y, M3_CLEARANCE),
        ):
            with Locations((x, y, 0)):
                Cylinder(
                    diameter / 2,
                    JAW_THICKNESS + 1.0,
                    align=(Align.CENTER, Align.CENTER, Align.CENTER),
                    mode=Mode.SUBTRACT,
                )

        with Locations((pivot_x, PIVOT_Y, 0)):
            Cylinder(
                JAW_RETAINING_SCREW_PILOT / 2,
                JAW_THICKNESS + 1.0,
                align=(Align.CENTER, Align.CENTER, Align.CENTER),
                mode=Mode.SUBTRACT,
            )
        with Locations((spring_x, spring_y, 0)):
            Cylinder(
                1.2,
                JAW_THICKNESS + 1.0,
                align=(Align.CENTER, Align.CENTER, Align.CENTER),
                mode=Mode.SUBTRACT,
            )

        # Serrated printable/TPU contact pad at the nose. It is part of this preview,
        # but it can also be printed separately in a flexible material from the pad builders.
        with Locations((pad_center_x, JAW_TIP_Y - PAD_HEIGHT / 2, 0)):
            Box(
                PAD_THICKNESS,
                PAD_HEIGHT,
                JAW_THICKNESS,
                align=(Align.CENTER, Align.CENTER, Align.CENTER),
            )
        for i in range(4):
            tooth_y = JAW_TIP_Y - 2.4 - i * 3.0
            with Locations((side * JAW_TIP_GAP / 2, tooth_y, 0)):
                Box(
                    1.0,
                    1.2,
                    JAW_THICKNESS + 0.6,
                    align=(Align.CENTER, Align.CENTER, Align.CENTER),
                    rotation=(0, 0, 18.0 * -side),
                    mode=Mode.SUBTRACT,
                )

    part = jaw.part.moved(Pos(0, 0, JAW_Z_CENTER))
    part.label = "left_sg90_gripper_jaw" if side < 0 else "right_sg90_gripper_jaw"
    return part


def _build_servo_horn_adapter(side: int):
    shaft_x = side * base_model.SERVO_CENTER_X
    link_x = shaft_x + side * HORN_LINK_OUTBOARD_X
    link_y = HORN_LINK_Y
    dx = link_x - shaft_x
    dy = link_y - SERVO_SHAFT_Y
    angle = degrees(atan2(-dx, dy))

    with BuildPart() as horn:
        with Locations((shaft_x, SERVO_SHAFT_Y, 0)):
            Cylinder(7.0, HORN_THICKNESS, align=(Align.CENTER, Align.CENTER, Align.CENTER))
        with Locations((link_x, link_y, 0)):
            Cylinder(4.2, HORN_THICKNESS, align=(Align.CENTER, Align.CENTER, Align.CENTER))
        with Locations(((shaft_x + link_x) / 2, (SERVO_SHAFT_Y + link_y) / 2, 0)):
            Box(
                7.0,
                hypot(dx, dy),
                HORN_THICKNESS,
                align=(Align.CENTER, Align.CENTER, Align.CENTER),
                rotation=(0, 0, angle),
            )

        with Locations((shaft_x, SERVO_SHAFT_Y, 0)):
            Cylinder(
                HORN_CENTER_SCREW_CLEARANCE / 2,
                HORN_THICKNESS + 1.0,
                align=(Align.CENTER, Align.CENTER, Align.CENTER),
                mode=Mode.SUBTRACT,
            )
        for spoke_angle in (35.0, 145.0, 215.0, 325.0):
            x = shaft_x + 4.6 * cos(radians(spoke_angle))
            y = SERVO_SHAFT_Y + 4.6 * sin(radians(spoke_angle))
            with Locations((x, y, 0)):
                Cylinder(
                    HORN_STOCK_SCREW_PILOT / 2,
                    HORN_THICKNESS + 1.0,
                    align=(Align.CENTER, Align.CENTER, Align.CENTER),
                    mode=Mode.SUBTRACT,
                )
        with Locations((link_x, link_y, 0)):
            Cylinder(
                M3_CLEARANCE / 2,
                HORN_THICKNESS + 1.0,
                align=(Align.CENTER, Align.CENTER, Align.CENTER),
                mode=Mode.SUBTRACT,
            )

    part = horn.part.moved(Pos(0, 0, HORN_Z_CENTER))
    part.label = "left_sg90_servo_horn_adapter" if side < 0 else "right_sg90_servo_horn_adapter"
    return part


def _build_link(side: int):
    pivot_x = side * PIVOT_X
    horn_point = (pivot_x + side * HORN_LINK_OUTBOARD_X, HORN_LINK_Y)
    jaw_point = _signed_points(
        side,
        pivot_x,
        [(JAW_DRIVE_HOLE_OFFSET_U, JAW_DRIVE_HOLE_OFFSET_Y)],
    )[0]
    label = "left_sg90_gripper_pushrod" if side < 0 else "right_sg90_gripper_pushrod"
    return _capsule_between(
        horn_point,
        jaw_point,
        width=LINK_WIDTH,
        thickness=LINK_THICKNESS,
        z_center=LINK_Z_CENTER,
        label=label,
    )


def build_model() -> Compound:
    """Build a dual-SG90, M3-pinned parallel-ish pincer gripper preview."""
    assert_printable_extent((OVERALL_WIDTH, OVERALL_LENGTH, OVERALL_HEIGHT))

    base = base_model.build_model()
    base.label = "sg90_gripper_base"

    children = [base]
    for side in (-1, 1):
        children.append(_build_jaw(side))
        children.append(_build_servo_horn_adapter(side))
        children.append(_build_link(side))

    assembly = Compound(children=children, label=MODEL_NAME)
    size = assembly.bounding_box().size
    assert_printable_extent((size.X, size.Y, size.Z))
    return assembly


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
