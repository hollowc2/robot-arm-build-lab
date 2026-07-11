from __future__ import annotations

from build123d import Align, Box, BuildPart, Compound, Cylinder, Location, Locations, Mode, Part

try:
    from models.common import (
        BEARING_608_ID,
        BEARING_608_OD,
        BEARING_608_WIDTH,
        HTD_342_3M_PITCH_LENGTH,
        M3_CLEARANCE,
        NEMA17_HOLE_SPACING,
        NEMA17_PILOT,
        assert_printable_extent,
        solve_open_belt_center_distance,
    )
except ModuleNotFoundError:
    from common import (
        BEARING_608_ID,
        BEARING_608_OD,
        BEARING_608_WIDTH,
        HTD_342_3M_PITCH_LENGTH,
        M3_CLEARANCE,
        NEMA17_HOLE_SPACING,
        NEMA17_PILOT,
        assert_printable_extent,
        solve_open_belt_center_distance,
    )


MODEL_NAME = "belt_base_candidate"
DRIVER_TEETH = 18
DRIVEN_TEETH = 108
BELT_CENTER_DISTANCE = solve_open_belt_center_distance(
    DRIVER_TEETH,
    DRIVEN_TEETH,
    HTD_342_3M_PITCH_LENGTH,
)
REDUCTION_RATIO = DRIVEN_TEETH / DRIVER_TEETH
TENSION_TRAVEL = 8.0
PLATE_X = 230.0
PLATE_Y = 160.0
PLATE_CENTER_X = 35.0
PLATE_THICKNESS = 8.0


def _horizontal_slot(radius: float, height: float) -> None:
    for x in (-TENSION_TRAVEL / 2, TENSION_TRAVEL / 2):
        with Locations((x, 0, 0)):
            Cylinder(radius, height, align=(Align.CENTER, Align.CENTER, Align.MIN), mode=Mode.SUBTRACT)
    Box(TENSION_TRAVEL, radius * 2, height, align=(Align.CENTER, Align.CENTER, Align.MIN), mode=Mode.SUBTRACT)


def build_stator() -> Part:
    with BuildPart() as stator:
        with Locations((PLATE_CENTER_X, 0, 0)):
            Box(PLATE_X, PLATE_Y, PLATE_THICKNESS, align=(Align.CENTER, Align.CENTER, Align.MIN))
        Cylinder(23.0, 26.0, align=(Align.CENTER, Align.CENTER, Align.MIN))
        Cylinder((BEARING_608_ID + 0.5) / 2, 27.0, align=(Align.CENTER, Align.CENTER, Align.MIN), mode=Mode.SUBTRACT)
        with Locations((0, 0, 26.0 - (2 * BEARING_608_WIDTH + 0.4))):
            Cylinder(BEARING_608_OD / 2, 2 * BEARING_608_WIDTH + 0.6, align=(Align.CENTER, Align.CENTER, Align.MIN), mode=Mode.SUBTRACT)
        with Locations((BELT_CENTER_DISTANCE, 0, 0)):
            _horizontal_slot((NEMA17_PILOT + 0.6) / 2, PLATE_THICKNESS + 0.4)
        hole_offset = NEMA17_HOLE_SPACING / 2
        for x in (-hole_offset, hole_offset):
            for y in (-hole_offset, hole_offset):
                with Locations((BELT_CENTER_DISTANCE + x, y, 0)):
                    _horizontal_slot(M3_CLEARANCE / 2, PLATE_THICKNESS + 0.4)
    stator.part.label = "belt_base_stator_342_3M"
    size = stator.part.bounding_box().size
    assert_printable_extent((size.X, size.Y, size.Z))
    return stator.part


def build_model() -> Compound:
    try:
        from models.nema17_stepper_motor import build_model as build_nema17
        from models.transmission_components import (
            build_base_belt_driven_pulley,
            build_base_belt_driver_pulley,
            build_base_htd_belt,
        )
    except ModuleNotFoundError:
        from nema17_stepper_motor import build_model as build_nema17
        from transmission_components import (
            build_base_belt_driven_pulley,
            build_base_belt_driver_pulley,
            build_base_htd_belt,
        )

    belt_z = PLATE_THICKNESS + 7.0
    return Compound(
        children=[
            build_stator(),
            build_base_belt_driven_pulley().moved(Location((0, 0, belt_z))),
            build_base_belt_driver_pulley().moved(Location((BELT_CENTER_DISTANCE, 0, belt_z))),
            build_base_htd_belt(BELT_CENTER_DISTANCE).moved(Location((BELT_CENTER_DISTANCE, 0, belt_z), (0, 0, 90))),
            build_nema17().moved(Location((BELT_CENTER_DISTANCE, 0, 0))),
        ],
        label=MODEL_NAME,
    )
