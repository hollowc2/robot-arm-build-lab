from __future__ import annotations

from build123d import Align, Box, BuildPart, Compound, Cylinder, Location, Locations, Mode, Part

try:
    from models.common import M3_CLEARANCE, M3_COUNTERBORE, assert_printable_extent
except ModuleNotFoundError:
    from common import M3_CLEARANCE, M3_COUNTERBORE, assert_printable_extent


MODEL_NAME = "safety_guards"
WALL_THICKNESS = 2.4
MOVING_CLEARANCE = 3.0
FINGER_EXCLUSION_OPENING = 4.0
CAPTIVE_HEAD_CLEARANCE = M3_COUNTERBORE + 0.4
BASE_GUARD_OUTER_DIAMETER = 156.0
BASE_GUARD_INNER_DIAMETER = 146.0


def _finalize(part: Part, label: str) -> Part:
    part.label = label
    size = part.bounding_box().size
    assert_printable_extent((size.X, size.Y, size.Z))
    return part


def _captive_mount_tab(x: float, y: float, z: float, tab_depth: float) -> None:
    with Locations((x, y, z)):
        Box(12.0, tab_depth, WALL_THICKNESS, align=(Align.CENTER, Align.CENTER, Align.CENTER))
        Cylinder(M3_CLEARANCE / 2, WALL_THICKNESS + 0.8, mode=Mode.SUBTRACT)
        with Locations((0, 0, WALL_THICKNESS / 2 - 0.8)):
            Cylinder(CAPTIVE_HEAD_CLEARANCE / 2, 1.8, mode=Mode.SUBTRACT)


def build_belt_guard(*, label: str, length: float, width: float) -> Part:
    """Build a three-sided removable guard with a structure-facing open back."""
    depth = 11.0 + 2 * MOVING_CLEARANCE
    outer_length = length + 2 * (WALL_THICKNESS + MOVING_CLEARANCE)
    outer_width = width + 2 * (WALL_THICKNESS + MOVING_CLEARANCE)
    with BuildPart() as guard:
        Box(depth, outer_width, outer_length, align=(Align.CENTER, Align.CENTER, Align.CENTER))
        with Locations((-WALL_THICKNESS / 2, 0, 0)):
            Box(
                depth,
                outer_width - 2 * WALL_THICKNESS,
                outer_length - 2 * WALL_THICKNESS,
                align=(Align.CENTER, Align.CENTER, Align.CENTER),
                mode=Mode.SUBTRACT,
            )
        # Open the structure-facing side while retaining the front and perimeter walls.
        with Locations((depth / 2, 0, 0)):
            Box(
                depth,
                outer_width - 2 * WALL_THICKNESS,
                outer_length - 2 * WALL_THICKNESS,
                align=(Align.CENTER, Align.CENTER, Align.CENTER),
                mode=Mode.SUBTRACT,
            )
        for y in (-outer_width / 2 - 4.0, outer_width / 2 + 4.0):
            for z in (-outer_length / 2 + 10.0, outer_length / 2 - 10.0):
                _captive_mount_tab(0, y, z, 10.0)
    return _finalize(guard.part, label)


def build_shoulder_belt_guard() -> Part:
    return build_belt_guard(label="shoulder_belt_guard", length=170.0, width=92.0)


def build_elbow_belt_guard() -> Part:
    return build_belt_guard(label="elbow_belt_guard", length=170.0, width=72.0)


def build_wrist_belt_guard() -> Part:
    return build_belt_guard(label="wrist_belt_guard", length=145.0, width=48.0)


def build_base_drive_guard() -> Part:
    """Build the stationary annular skirt that blocks access to the base drive."""
    height = 22.0
    with BuildPart() as guard:
        Cylinder(BASE_GUARD_OUTER_DIAMETER / 2, height, align=(Align.CENTER, Align.CENTER, Align.MIN))
        Cylinder(BASE_GUARD_INNER_DIAMETER / 2, height + 0.4, align=(Align.CENTER, Align.CENTER, Align.MIN), mode=Mode.SUBTRACT)
        for angle_location in ((0, -76), (0, 76), (-76, 0), (76, 0)):
            with Locations((angle_location[0], angle_location[1], 0)):
                Box(14.0, 14.0, WALL_THICKNESS, align=(Align.CENTER, Align.CENTER, Align.MIN))
                Cylinder(M3_CLEARANCE / 2, WALL_THICKNESS + 0.4, mode=Mode.SUBTRACT)
                Cylinder(CAPTIVE_HEAD_CLEARANCE / 2, 1.8, mode=Mode.SUBTRACT)
    return _finalize(guard.part, "base_drive_guard")


def build_gripper_linkage_guard() -> Part:
    """Build a shallow linkage shield; the jaw working area remains intentionally open."""
    with BuildPart() as guard:
        Box(52.0, 58.0, WALL_THICKNESS, align=(Align.CENTER, Align.CENTER, Align.MIN))
        for x in (-21.0, 21.0):
            for y in (-24.0, 24.0):
                with Locations((x, y, 0)):
                    Cylinder(M3_CLEARANCE / 2, WALL_THICKNESS + 0.4, mode=Mode.SUBTRACT)
                    Cylinder(CAPTIVE_HEAD_CLEARANCE / 2, 1.8, mode=Mode.SUBTRACT)
    return _finalize(guard.part, "gripper_linkage_guard")


def build_model() -> Compound:
    parts = [
        build_base_drive_guard().moved(Location((-82.0, -82.0, 0))),
        build_shoulder_belt_guard().moved(Location((88.0, -64.0, 75.0), (0, 90, 0))),
        build_elbow_belt_guard().moved(Location((88.0, 42.0, 82.5), (0, 90, 0))),
        build_wrist_belt_guard().moved(Location((-82.0, 72.0, 74.0), (0, 90, 0))),
        build_gripper_linkage_guard().moved(Location((72.0, -74.0, 0))),
    ]
    return Compound(children=parts, label=MODEL_NAME)
