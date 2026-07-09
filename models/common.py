from __future__ import annotations

from math import cos, radians, sin
from pathlib import Path
from typing import Iterable

from build123d import export_step, export_stl


OUT_DIR = Path(__file__).parent / "out"


M3_CLEARANCE = 3.4
M3_TAP_HOLE = 2.5
M3_COUNTERBORE = 6.0
M3_COUNTERBORE_DEPTH = 3.5
M3_NUT_FLATS = 6.2
M3_NUT_DEPTH = 2.7

DESK_MOUNT_CLEARANCE = 5.0

BEARING_608_OD = 22.15
BEARING_608_ID = 8.0
BEARING_608_WIDTH = 7.0

BEARING_625_OD = 16.15
BEARING_625_ID = 5.0
BEARING_625_WIDTH = 5.0

NEMA17_BODY = 42.3
NEMA17_HOLE_SPACING = 31.0
NEMA17_PILOT = 22.0
NEMA17_SHAFT = 5.0

BYJ48_BODY = 28.0
BYJ48_EAR_SPACING = 35.0
BYJ48_MOUNT_HOLE = 4.2

SG90_BODY_X = 23.0
SG90_BODY_Y = 12.2
SG90_HEIGHT = 29.0
SG90_TAB_SPACING = 32.0

BASE_GEAR_CENTER_DISTANCE = 70.0
SHOULDER_BELT_CENTER_DISTANCE = 94.03
ELBOW_BELT_CENTER_DISTANCE = 90.56
WRIST_BELT_CENTER_DISTANCE = 109.33

WRIST_DRIVER_TEETH = 20
WRIST_DRIVEN_TEETH = 32

BASE_GEAR_BOLT_CIRCLE = 60.0
SHOULDER_PULLEY_BOLT_CIRCLE = 25.0
ELBOW_PULLEY_BOLT_CIRCLE = 25.0
WRIST_PULLEY_BOLT_CIRCLE = 20.0

PRINT_BED_LIMIT = 256.0


def circle_points(count: int, bolt_circle_diameter: float, start_angle: float = 0.0) -> list[tuple[float, float]]:
    radius = bolt_circle_diameter / 2
    return [
        (
            radius * cos(radians(start_angle + i * 360 / count)),
            radius * sin(radians(start_angle + i * 360 / count)),
        )
        for i in range(count)
    ]


def export_model(model, name: str) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    export_step(model, OUT_DIR / f"{name}.step")
    export_stl(model, OUT_DIR / f"{name}.stl")
    print(f"Wrote {OUT_DIR / f'{name}.step'}")
    print(f"Wrote {OUT_DIR / f'{name}.stl'}")


def assert_printable_extent(size_xyz: Iterable[float]) -> None:
    too_large = [axis for axis in size_xyz if axis > PRINT_BED_LIMIT]
    if too_large:
        raise ValueError(f"Model exceeds {PRINT_BED_LIMIT}mm print bed limit: {tuple(size_xyz)}")
