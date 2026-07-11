from __future__ import annotations

from build123d import Align, Box, BuildPart, Compound, Cylinder, Location, Locations, Mode, Part

try:
    from models.common import M3_CLEARANCE, M3_TAP_HOLE, assert_printable_extent
except ModuleNotFoundError:
    from common import M3_CLEARANCE, M3_TAP_HOLE, assert_printable_extent


MODEL_NAME = "electronics_enclosure"
OUTER_X = 196.0
OUTER_Y = 188.0
BASE_HEIGHT = 58.0
WALL = 2.4
LID_THICKNESS = 3.0
VENT_WIDTH = 3.5


def _finalize(part: Part, label: str) -> Part:
    part.label = label
    size = part.bounding_box().size
    assert_printable_extent((size.X, size.Y, size.Z))
    return part


def _corner_points(inset: float = 8.0) -> tuple[tuple[float, float], ...]:
    return tuple(
        (x, y)
        for x in (-OUTER_X / 2 + inset, OUTER_X / 2 - inset)
        for y in (-OUTER_Y / 2 + inset, OUTER_Y / 2 - inset)
    )


def build_enclosure_base() -> Part:
    with BuildPart() as base:
        Box(OUTER_X, OUTER_Y, BASE_HEIGHT, align=(Align.CENTER, Align.CENTER, Align.MIN))
        with Locations((0, 0, WALL)):
            Box(
                OUTER_X - 2 * WALL,
                OUTER_Y - 2 * WALL,
                BASE_HEIGHT,
                align=(Align.CENTER, Align.CENTER, Align.MIN),
                mode=Mode.SUBTRACT,
            )
        for x, y in _corner_points():
            with Locations((x, y, WALL)):
                Cylinder(4.5, BASE_HEIGHT - WALL, align=(Align.CENTER, Align.CENTER, Align.MIN))
                Cylinder(M3_TAP_HOLE / 2, BASE_HEIGHT, align=(Align.CENTER, Align.CENTER, Align.MIN), mode=Mode.SUBTRACT)
        # Cable entry and guarded fan/air path openings remain below finger-access size.
        for z in (14.0, 22.0, 30.0, 38.0):
            with Locations((0, -OUTER_Y / 2, z)):
                Box(70.0, WALL + 1.0, VENT_WIDTH, mode=Mode.SUBTRACT)
        with Locations((OUTER_X / 2, 0, 20.0)):
            Box(WALL + 1.0, 18.0, 12.0, mode=Mode.SUBTRACT)
    return _finalize(base.part, "electronics_enclosure_base")


def build_enclosure_lid() -> Part:
    with BuildPart() as lid:
        Box(OUTER_X, OUTER_Y, LID_THICKNESS, align=(Align.CENTER, Align.CENTER, Align.MIN))
        for x, y in _corner_points():
            with Locations((x, y, 0)):
                Cylinder(M3_CLEARANCE / 2, LID_THICKNESS + 0.4, mode=Mode.SUBTRACT)
                with Locations((0, 0, LID_THICKNESS - 1.4)):
                    Cylinder(3.2, 1.6, mode=Mode.SUBTRACT)
        for y in range(-60, 61, 12):
            with Locations((0, float(y), 0)):
                Box(92.0, VENT_WIDTH, LID_THICKNESS + 0.4, mode=Mode.SUBTRACT)
    return _finalize(lid.part, "electronics_enclosure_lid")


def build_model() -> Compound:
    return Compound(
        children=[
            build_enclosure_base(),
            build_enclosure_lid().moved(Location((0, 0, BASE_HEIGHT))),
        ],
        label=MODEL_NAME,
    )

