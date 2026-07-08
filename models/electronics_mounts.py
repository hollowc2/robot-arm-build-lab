from __future__ import annotations

from dataclasses import dataclass

from build123d import Align, Box, BuildPart, Compound, Cylinder, Locations, Mode, Part

try:
    from models.common import M3_CLEARANCE, M3_TAP_HOLE, assert_printable_extent, export_model
except ModuleNotFoundError:
    from common import M3_CLEARANCE, M3_TAP_HOLE, assert_printable_extent, export_model


UNO_TRAY_NAME = "arduino_uno_r4_minima_tray"
NEMA17_DRIVER_TRAY_NAME = "nema17_driver_board_tray"
BYJ_ULN_TRAY_NAME = "28byj_uln2003_board_tray"

BASE_THICKNESS = 3.0
WALL_THICKNESS = 2.4
WALL_HEIGHT = 5.0
BOARD_CLEARANCE = 1.0
CABLE_GAP_WIDTH = 16.0

STANDOFF_DIAMETER = 7.0
STANDOFF_HEIGHT = 5.5
STANDOFF_PILOT = M3_TAP_HOLE

BASE_MOUNT_INSET = 6.0
BASE_MOUNT_BOSS_DIAMETER = 9.0

UNO_BOARD_X = 68.6
UNO_BOARD_Y = 53.4
UNO_HOLE_POINTS = (
    (-31.5, -24.1),
    (19.3, -24.1),
    (-30.2, 23.9),
    (31.8, 20.6),
)

STEPSTICK_BOARD_X = 20.5
STEPSTICK_BOARD_Y = 15.5
STEPSTICK_SPACING_X = 25.0
STEPSTICK_HOLE_INSET = 2.8

ULN2003_BOARD_X = 35.0
ULN2003_BOARD_Y = 32.0
ULN2003_HOLE_POINTS = (
    (-14.0, -12.5),
    (14.0, -12.5),
    (-14.0, 12.5),
    (14.0, 12.5),
)


@dataclass(frozen=True)
class BoardTraySpec:
    """Reusable electronics tray dimensions in local X/Y/Z coordinates."""

    label: str
    board_x: float
    board_y: float
    standoff_points: tuple[tuple[float, float], ...]
    wall_gap_sides: tuple[str, ...] = ("front",)
    base_mounts: bool = True

    @property
    def tray_x(self) -> float:
        return self.board_x + 2 * (WALL_THICKNESS + BOARD_CLEARANCE)

    @property
    def tray_y(self) -> float:
        return self.board_y + 2 * (WALL_THICKNESS + BOARD_CLEARANCE)

    @property
    def height(self) -> float:
        return BASE_THICKNESS + max(WALL_HEIGHT, STANDOFF_HEIGHT)


def _add_rail(x: float, y: float, size_x: float, size_y: float) -> None:
    with Locations((x, y, BASE_THICKNESS)):
        Box(
            size_x,
            size_y,
            WALL_HEIGHT,
            align=(Align.CENTER, Align.CENTER, Align.MIN),
        )


def _add_split_rail(side: str, tray_x: float, tray_y: float) -> None:
    if side in ("front", "back"):
        y = -tray_y / 2 + WALL_THICKNESS / 2 if side == "front" else tray_y / 2 - WALL_THICKNESS / 2
        rail_x = (tray_x - CABLE_GAP_WIDTH) / 2
        for x in (-(CABLE_GAP_WIDTH + rail_x) / 2, (CABLE_GAP_WIDTH + rail_x) / 2):
            _add_rail(x, y, rail_x, WALL_THICKNESS)
        return

    x = -tray_x / 2 + WALL_THICKNESS / 2 if side == "left" else tray_x / 2 - WALL_THICKNESS / 2
    rail_y = (tray_y - CABLE_GAP_WIDTH) / 2
    for y in (-(CABLE_GAP_WIDTH + rail_y) / 2, (CABLE_GAP_WIDTH + rail_y) / 2):
        _add_rail(x, y, WALL_THICKNESS, rail_y)


def _add_perimeter_lips(spec: BoardTraySpec) -> None:
    tray_x = spec.tray_x
    tray_y = spec.tray_y
    for side in ("front", "back", "left", "right"):
        if side in spec.wall_gap_sides:
            _add_split_rail(side, tray_x, tray_y)
        elif side in ("front", "back"):
            y = -tray_y / 2 + WALL_THICKNESS / 2 if side == "front" else tray_y / 2 - WALL_THICKNESS / 2
            _add_rail(0, y, tray_x, WALL_THICKNESS)
        else:
            x = -tray_x / 2 + WALL_THICKNESS / 2 if side == "left" else tray_x / 2 - WALL_THICKNESS / 2
            _add_rail(x, 0, WALL_THICKNESS, tray_y)


def _cut_base_mounts(tray_x: float, tray_y: float) -> None:
    mount_x = tray_x / 2 - BASE_MOUNT_INSET
    mount_y = tray_y / 2 - BASE_MOUNT_INSET
    for x in (-mount_x, mount_x):
        for y in (-mount_y, mount_y):
            with Locations((x, y, BASE_THICKNESS)):
                Cylinder(
                    BASE_MOUNT_BOSS_DIAMETER / 2,
                    1.6,
                    align=(Align.CENTER, Align.CENTER, Align.MIN),
                )
            with Locations((x, y, 0)):
                Cylinder(
                    M3_CLEARANCE / 2,
                    BASE_THICKNESS + 2.0,
                    align=(Align.CENTER, Align.CENTER, Align.MIN),
                    mode=Mode.SUBTRACT,
                )


def _add_standoffs(spec: BoardTraySpec) -> None:
    for x, y in spec.standoff_points:
        with Locations((x, y, BASE_THICKNESS)):
            Cylinder(
                STANDOFF_DIAMETER / 2,
                STANDOFF_HEIGHT,
                align=(Align.CENTER, Align.CENTER, Align.MIN),
            )
        with Locations((x, y, BASE_THICKNESS)):
            Cylinder(
                STANDOFF_PILOT / 2,
                STANDOFF_HEIGHT + 0.6,
                align=(Align.CENTER, Align.CENTER, Align.MIN),
                mode=Mode.SUBTRACT,
            )


def build_board_tray(spec: BoardTraySpec) -> Part:
    """Build a ventilated electronics tray from a board footprint and hole pattern."""
    assert_printable_extent((spec.tray_x, spec.tray_y, spec.height))

    with BuildPart() as tray:
        Box(
            spec.tray_x,
            spec.tray_y,
            BASE_THICKNESS,
            align=(Align.CENTER, Align.CENTER, Align.MIN),
        )

        _add_perimeter_lips(spec)
        _add_standoffs(spec)

        if spec.base_mounts:
            _cut_base_mounts(spec.tray_x, spec.tray_y)

        # A shallow underside relief reduces plastic while leaving screw bosses supported.
        with Locations((0, 0, 0)):
            Box(
                max(4.0, spec.tray_x - 28.0),
                max(4.0, spec.tray_y - 28.0),
                BASE_THICKNESS + 0.2,
                align=(Align.CENTER, Align.CENTER, Align.MIN),
                mode=Mode.SUBTRACT,
            )

    tray.part.label = spec.label
    return tray.part


def build_arduino_uno_r4_minima_tray() -> Part:
    """Build a tray for the Arduino Uno R4 Minima mounting-hole pattern."""
    return build_board_tray(
        BoardTraySpec(
            label=UNO_TRAY_NAME,
            board_x=UNO_BOARD_X,
            board_y=UNO_BOARD_Y,
            standoff_points=UNO_HOLE_POINTS,
            wall_gap_sides=("front", "left", "right"),
        )
    )


def build_nema17_driver_board_tray(driver_count: int = 1) -> Part:
    """Build a tray for one or more StepStick-style NEMA17 driver carrier boards."""
    if driver_count < 1:
        raise ValueError("driver_count must be at least 1")

    board_x = STEPSTICK_BOARD_X + (driver_count - 1) * STEPSTICK_SPACING_X
    x0 = -(driver_count - 1) * STEPSTICK_SPACING_X / 2
    standoffs: list[tuple[float, float]] = []
    for index in range(driver_count):
        center_x = x0 + index * STEPSTICK_SPACING_X
        for y in (-STEPSTICK_BOARD_Y / 2 + STEPSTICK_HOLE_INSET, STEPSTICK_BOARD_Y / 2 - STEPSTICK_HOLE_INSET):
            standoffs.append((center_x, y))

    label = NEMA17_DRIVER_TRAY_NAME if driver_count == 1 else f"{driver_count}x_{NEMA17_DRIVER_TRAY_NAME}"
    return build_board_tray(
        BoardTraySpec(
            label=label,
            board_x=board_x,
            board_y=STEPSTICK_BOARD_Y,
            standoff_points=tuple(standoffs),
            wall_gap_sides=("front", "back"),
        )
    )


def build_28byj_uln_board_tray() -> Part:
    """Build a compact tray for the common ULN2003 board used with 28BYJ steppers."""
    return build_board_tray(
        BoardTraySpec(
            label=BYJ_ULN_TRAY_NAME,
            board_x=ULN2003_BOARD_X,
            board_y=ULN2003_BOARD_Y,
            standoff_points=ULN2003_HOLE_POINTS,
            wall_gap_sides=("front", "right"),
        )
    )


def build_model() -> Compound:
    """Return all electronics trays as a labeled compound for quick inspection."""
    trays = [
        build_arduino_uno_r4_minima_tray(),
        build_nema17_driver_board_tray(),
        build_nema17_driver_board_tray(driver_count=4),
        build_28byj_uln_board_tray(),
    ]
    assembly = Compound(children=trays, label="electronics_mounts")
    size = assembly.bounding_box().size
    assert_printable_extent((size.X, size.Y, size.Z))
    return assembly


def main() -> None:
    models = (
        build_arduino_uno_r4_minima_tray(),
        build_nema17_driver_board_tray(),
        build_nema17_driver_board_tray(driver_count=4),
        build_28byj_uln_board_tray(),
    )
    for model in models:
        export_model(model, model.label)

    try:
        from ocp_vscode import show
    except ImportError:
        return

    show(*models)


if __name__ == "__main__":
    main()
