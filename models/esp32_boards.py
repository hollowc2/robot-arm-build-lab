"""Purchased 30-pin ESP32 references; millimetres, top view, power ports at +X.

Source-backed carrier outline/spans: Corey's expansion-dimensions.png (underside).
Top-side hole coordinates mirror underside X. Absolute offsets, component sizes,
DevKit clone outline, and header heights are estimates; see docs/esp32-boards.md.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from itertools import permutations
from math import cos, sin

from build123d import Align, Box, Color, Compound, Cylinder, Pos, Rot

EXPANSION_LENGTH = 68.6
EXPANSION_WIDTH = 53.4
PCB_THICKNESS = 1.6
MOUNT_HOLE_DIAMETER = 3.4
# Underside-to-top mirror; retain the photographed asymmetric hole ordering.
# Right underside X and upper Y anchors inherited from the existing mount datum.
EXPANSION_HOLE_POINTS = ((20.77, 24.13), (-31.75, 19.05), (-31.75, -8.91), (19.06, -24.26))
PIN_PITCH = 2.54
PIN_COUNT = 15
ROW_SPACING = 25.4
SOCKET_CENTER_X = -8.0
SOCKET_HEIGHT = 8.5
MALE_SPACER_HEIGHT = 2.5
PIN_INSERTION = 5.0
PIN_FREE_LENGTH = 6.0
# Seated male insulator contacts female header top. Pins stop 5 mm into sockets.
DEVKIT_SEATED_Z = PCB_THICKNESS + SOCKET_HEIGHT + MALE_SPACER_HEIGHT

FINISH_COLORS = {
    "pcb_black": "#202724", "electronics_black": "#101214",
    "electronics_silver": "#c8cdd2", "electronics_gold": "#c9a447",
    "electronics_white": "#e3e5d8", "electronics_red": "#b82820",
}


@dataclass(frozen=True)
class DevkitSpec:
    length: float = 53.0
    width: float = 28.2
    thickness: float = PCB_THICKNESS
    row_spacing: float = ROW_SPACING
    header_center_x: float = 0.0
    usb_variant: str = "micro-b"

    def __post_init__(self):
        if self.usb_variant not in {"micro-b", "usb-c"}:
            raise ValueError("usb_variant must be micro-b or usb-c")
        if self.width < self.row_spacing + 1.0 or self.length < PIN_COUNT * PIN_PITCH:
            raise ValueError("DevKit outline cannot contain its 30-pin headers")
        if self.thickness <= 0:
            raise ValueError("PCB thickness must be positive")


def header_points(center_x=0.0, row_spacing=ROW_SPACING):
    return tuple((center_x + (i - 7) * PIN_PITCH, side * row_spacing / 2)
                 for side in (-1, 1) for i in range(PIN_COUNT))


def _box(x, y, z, lx, ly, lz):
    return Pos(x, y, z) * Box(lx, ly, lz, align=(Align.CENTER, Align.CENTER, Align.MIN))


def _finish(parts, kind):
    leaves = []
    for part in parts:
        for solid in part.solids():
            solid.label = kind
            solid.color = Color(FINISH_COLORS[kind])
            leaves.append(solid)
    return leaves



def _usb(x, y, z, variant):
    width, depth, height = (8.6, 7.4, 3.2) if variant == "usb-c" else (7.5, 5.5, 2.8)
    shell = _box(x, y, z, depth, width, height)
    shell -= _box(x + 0.6, y, z + 0.5, depth + 1, width - 1.0, height - 1.0)
    return shell


def build_devkit(spec: DevkitSpec = DevkitSpec()):
    pcb = _box(0, 0, 0, spec.length, spec.width, spec.thickness)
    black, gold, silver, white = [], [], [], []
    for side in (-1, 1):
        black.append(_box(spec.header_center_x, side * spec.row_spacing / 2,
                          -MALE_SPACER_HEIGHT, PIN_COUNT * PIN_PITCH, 2.54, MALE_SPACER_HEIGHT))
    for x, y in header_points(spec.header_center_x, spec.row_spacing):
        gold.append(_box(x, y, -MALE_SPACER_HEIGHT - PIN_INSERTION, 0.64, 0.64,
                         MALE_SPACER_HEIGHT + PIN_INSERTION + spec.thickness + 0.8))
    # Espressif WROOM envelope: 25.5 long × 18 wide × 3.1 high, antenna at -X.
    module_x = -spec.length / 2 + 25.5 / 2
    black.append(_box(module_x, 0, spec.thickness, 25.5, 18, 0.8))
    silver.append(_box(module_x + 3.2, 0, spec.thickness + 0.8, 19.1, 17.0, 2.3))
    antenna_x = -spec.length / 2 + 3.0
    for i in range(5):
        gold.append(_box(antenna_x + i * 1.05 - 2.1, (-1)**i * 1.8,
                         spec.thickness + 0.8, 0.3, 7, 0.07))
    for i in range(4):
        gold.append(_box(antenna_x + i * 1.05 - 1.575, (-1)**i * 1.8 + 3.35,
                         spec.thickness + 0.8, 1.05, 0.3, 0.07))
    silver.append(_usb(spec.length / 2 - 1.5, 0, spec.thickness, spec.usb_variant))
    for y in (-8, 8):
        silver.append(_box(spec.length / 2 - 6, y, spec.thickness, 4.5, 3.8, 1.6))
        black.append(_box(spec.length / 2 - 6, y, spec.thickness + 1.6, 2, 2, 0.9))
    black.extend([_box(8, 0, spec.thickness, 5, 5, 1.2),
                  _box(17, 0, spec.thickness, 4.5, 3, 1.5)])
    silver.append(_box(15, 0, spec.thickness + 1.5, 1, 3, 0.2))
    for x, y in ((5, 6), (11, -5), (14, 5)):
        white.append(_box(x, y, spec.thickness, 2, 1.2, 0.7))
    red = [_box(19, 5, spec.thickness, 1.8, 1, 0.8)]
    return Compound(children=sum([_finish([pcb], "pcb_black"), _finish(black, "electronics_black"),
                             _finish(silver, "electronics_silver"), _finish(gold, "electronics_gold"),
                             _finish(white, "electronics_white"), _finish(red, "electronics_red")], []),
                    label="esp32_devkit_30pin")


def build_expansion():
    pcb = _box(0, 0, 0, EXPANSION_LENGTH, EXPANSION_WIDTH, PCB_THICKNESS)
    for x, y in EXPANSION_HOLE_POINTS:
        pcb -= Pos(x, y, PCB_THICKNESS / 2) * Cylinder(MOUNT_HOLE_DIAMETER / 2, PCB_THICKNESS + 0.4)
    black, gold, silver, white = [], [], [], []
    # Real socket openings receive the installed male pins rather than solid bars.
    for side in (-1, 1):
        socket = _box(SOCKET_CENTER_X, side * ROW_SPACING / 2, PCB_THICKNESS,
                      PIN_COUNT * PIN_PITCH, 2.54, SOCKET_HEIGHT)
        for x, y in header_points(SOCKET_CENTER_X):
            if y * side < 0:
                continue
            socket -= _box(x, y, PCB_THICKNESS + SOCKET_HEIGHT - PIN_FREE_LENGTH,
                           0.9, 0.9, PIN_FREE_LENGTH + 0.1)
        black.append(socket)
    # Outer signal/VCC/GND rows, photographed 15-position rails.
    for side in (-1, 1):
        for row in range(3):
            y = side * (18.0 + row * PIN_PITCH)
            black.append(_box(SOCKET_CENTER_X, y, PCB_THICKNESS, PIN_COUNT * PIN_PITCH, 2.54, 2.5))
            for i in range(PIN_COUNT):
                x = SOCKET_CENTER_X + (i - 7) * PIN_PITCH
                gold.append(_box(x, y, -0.8, 0.64, 0.64, PCB_THICKNESS + 9.3))
                silver.append(Pos(x, y, -0.6) * Cylinder(0.8, 0.6))
    # Power-end components from photograph. The small middle port is micro-B.
    silver.extend([_usb(32, -14, PCB_THICKNESS, "usb-c"),
                   _usb(32, 6, PCB_THICKNESS, "micro-b")])
    jack = _box(29, 19, PCB_THICKNESS, 14, 9, 10.5)
    jack -= Pos(36, 19, PCB_THICKNESS + 5.25) * Rot(0, 90, 0) * Cylinder(3, 12)
    black.append(jack)
    silver.append(Pos(31, 19, PCB_THICKNESS + 5.25) * Rot(0, 90, 0) * Cylinder(0.9, 7))
    for y in (2.5, 11):
        black.append(Pos(19.5, y, PCB_THICKNESS + 3.5) * Cylinder(3.3, 7))
        silver.append(Pos(19.5, y, PCB_THICKNESS + 7.1) * Cylinder(3.2, 0.2))
    black.append(_box(26, -1, PCB_THICKNESS, 6.5, 5, 2))
    silver.append(_box(26, -1, PCB_THICKNESS + 2, 3, 4, 0.2))
    # 2x3 I2C and 2x3 voltage output headers; three-position voltage jumper.
    for cx, cy, nx, ny in ((15, 22, 3, 2), (15, -22, 3, 2), (23, -14, 1, 3)):
        black.append(_box(cx, cy, PCB_THICKNESS, nx * PIN_PITCH, ny * PIN_PITCH, 2.5))
        for i in range(nx):
            for j in range(ny):
                gold.append(_box(cx + (i - (nx - 1) / 2) * PIN_PITCH,
                                 cy + (j - (ny - 1) / 2) * PIN_PITCH, PCB_THICKNESS, 0.64, 0.64, 8.5))
    black.append(_box(23, -12.73, PCB_THICKNESS + 2.5, 2.2, 4.7, 3))
    for x, y in ((26, -8), (29, -8), (24, 6)):
        white.append(_box(x, y, PCB_THICKNESS, 2.8, 1.4, 0.8))
    red = [_box(29, -23, PCB_THICKNESS, 2, 1.5, 1)]
    # Solder joints on the underside; never lower than -0.9 mm.
    for x, y in header_points(SOCKET_CENTER_X):
        silver.append(Pos(x, y, -0.45) * Cylinder(0.8, 0.9))
    return Compound(children=sum([_finish([pcb], "pcb_black"), _finish(black, "electronics_black"),
                             _finish(silver, "electronics_silver"), _finish(gold, "electronics_gold"),
                             _finish(white, "electronics_white"), _finish(red, "electronics_red")], []),
                    label="esp32_expansion_30pin")


@lru_cache(maxsize=1)
def mounting_registration():
    """Minimax *proper* rigid fit with board components facing outboard (+world X).

    Board +X maps to -world Z and +Y to +world Y. Enumerate all hole assignments;
    do not reflect the finished PCB to force a fit. No scale or hole edits.
    Return in-plane angle in mount Z/Y coordinates, translation, offsets, order.
    """
    import numpy as np
    from scipy.optimize import minimize
    from models.electronics_mounts import UNO_HOLE_POINTS

    board = np.array(EXPANSION_HOLE_POINTS) * [-1, 1]
    targets = np.array(UNO_HOLE_POINTS)
    best = None
    for order in permutations(range(4)):
        target = targets[list(order)]

        def residual(p):
            c, s = cos(p[0]), sin(p[0])
            return np.linalg.norm(board @ np.array([[c, s], [-s, c]]) + p[1:3] - target, axis=1)

        for start in (0, np.pi):
            result = minimize(lambda p: p[3], [start, 0, 0, 25], method="SLSQP",
                              constraints={"type": "ineq", "fun": lambda p: p[3] - residual(p)},
                              options={"ftol": 1e-10, "maxiter": 500})
            if result.success and (best is None or result.x[3] < best[0]):
                best = (float(result.x[3]), float(result.x[0]),
                        tuple(float(v) for v in result.x[1:3]),
                        tuple(float(v) for v in residual(result.x)), order)
    if best is None:
        raise ValueError("Board registration failed")
    _, angle, offset, errors, order = best
    angle = (angle * 180 / np.pi + 180) % 360 - 180
    return float(angle), offset, errors, order


def registered_hole_points():
    """Photographed holes in the existing mount's local (Z offset, Y) datum."""
    angle, offset, _, _ = mounting_registration()
    a = angle * 3.141592653589793 / 180
    return tuple((-x * cos(a) - y * sin(a) + offset[0],
                  -x * sin(a) + y * cos(a) + offset[1])
                 for x, y in EXPANSION_HOLE_POINTS)


def board_mount_location(turntable_z=0.0):
    """Approved placement on the boss seating plane, with components facing outward."""
    from models import azimuth_turntable_shoulder_cleat as mount
    angle, offset, _, _ = mounting_registration()
    face = (mount.CLEVIS_CLEAR_GAP / 2 + mount.ELBOW_MOTOR_RELIEF_BACK_SKIN
            + mount.ESP32_STANDOFF_HEIGHT - 0.2)
    return (Pos(face, offset[1], turntable_z + mount.ARDUINO_BOARD_CENTER_Z + offset[0])
            * Rot(0, 90, 0) * Rot(0, 0, -angle))


def install_reference(board, location, label):
    """Consume a reference and place its leaves without copying its parent tree.

    build123d moved() copies anytree parents too. These fresh local-coordinate
    leaves must be detached before placement, just like the purchased motors.
    """
    leaves = tuple(board.children)
    for leaf in leaves:
        leaf.parent = None
    return Compound(children=[leaf.moved(location) for leaf in leaves], label=label)


def build_model():
    return Compound(children=[build_expansion(),
                              install_reference(build_devkit(), Pos(SOCKET_CENTER_X, 0, DEVKIT_SEATED_Z),
                                                "seated_esp32_devkit_30pin")],
                    label="esp32_seated_board_pair")
