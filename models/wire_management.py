from __future__ import annotations

from build123d import Align, Box, BuildPart, Compound, Cylinder, Location, Locations, Mode, Part

try:
    from models.common import M3_CLEARANCE, assert_printable_extent, export_model
except ModuleNotFoundError:
    from common import M3_CLEARANCE, assert_printable_extent, export_model


MODEL_NAME = "wire_management"

GUIDE_THICKNESS = 3.0
WALL_THICKNESS = 2.4
ZIP_TIE_WIDTH = 4.2
ZIP_TIE_LENGTH = 16.0
CABLE_BUNDLE_DIAMETER = 10.0


def _assert_part_printable(part: Part) -> None:
    size = part.bounding_box().size
    assert_printable_extent((size.X, size.Y, size.Z))


def _set_label(part: Part, label: str) -> Part:
    part.label = label
    _assert_part_printable(part)
    return part


def _zip_tie_slot(length: float = ZIP_TIE_LENGTH, width: float = ZIP_TIE_WIDTH, height: float = GUIDE_THICKNESS + 1.0) -> None:
    straight = max(0.0, length - width)
    with Locations((0, -straight / 2, 0), (0, straight / 2, 0)):
        Cylinder(width / 2, height, align=(Align.CENTER, Align.CENTER, Align.CENTER), mode=Mode.SUBTRACT)
    Box(width, straight, height, align=(Align.CENTER, Align.CENTER, Align.CENTER), mode=Mode.SUBTRACT)


def _mount_hole(height: float = GUIDE_THICKNESS + 1.0) -> None:
    Cylinder(M3_CLEARANCE / 2, height, align=(Align.CENTER, Align.CENTER, Align.CENTER), mode=Mode.SUBTRACT)


def _build_anchor(label: str, loop_radius: float, base_length: float, base_width: float, height: float) -> Part:
    """Build one printable service-loop anchor with a raised open saddle."""
    with BuildPart() as anchor:
        Box(base_width, base_length, GUIDE_THICKNESS, align=(Align.CENTER, Align.CENTER, Align.MIN))

        for y in (-base_length / 2 + 9.0, base_length / 2 - 9.0):
            with Locations((0, y, GUIDE_THICKNESS / 2)):
                _zip_tie_slot()

        for x in (-base_width / 2 + 7.0, base_width / 2 - 7.0):
            with Locations((x, 0, GUIDE_THICKNESS / 2)):
                _mount_hole()

        post_y = base_length / 2 - 10.0
        for x in (-loop_radius, loop_radius):
            with Locations((x, post_y, GUIDE_THICKNESS)):
                Cylinder(WALL_THICKNESS / 2, height, align=(Align.CENTER, Align.CENTER, Align.MIN))

        with Locations((0, post_y, GUIDE_THICKNESS + height)):
            Cylinder(
                loop_radius + WALL_THICKNESS / 2,
                WALL_THICKNESS,
                rotation=(0, 90, 0),
                align=(Align.CENTER, Align.CENTER, Align.CENTER),
            )
            Cylinder(
                loop_radius - WALL_THICKNESS / 2,
                WALL_THICKNESS + 0.4,
                rotation=(0, 90, 0),
                align=(Align.CENTER, Align.CENTER, Align.CENTER),
                mode=Mode.SUBTRACT,
            )
            Box(
                (loop_radius + WALL_THICKNESS) * 2,
                WALL_THICKNESS + 0.8,
                loop_radius + WALL_THICKNESS,
                align=(Align.CENTER, Align.CENTER, Align.MAX),
                mode=Mode.SUBTRACT,
            )

    return _set_label(anchor.part, label)


def build_base_cable_entry_strain_relief_guide() -> Part:
    """Cable entry guide with a rounded bundle gate, tie-down slots, and M3 mount holes."""
    length = 68.0
    width = 36.0
    gate_radius = CABLE_BUNDLE_DIAMETER / 2 + WALL_THICKNESS

    with BuildPart() as guide:
        Box(width, length, GUIDE_THICKNESS, align=(Align.CENTER, Align.CENTER, Align.MIN))

        with Locations((0, -length / 2 + 12.0, GUIDE_THICKNESS / 2)):
            _zip_tie_slot(length=18.0)
        with Locations((0, length / 2 - 12.0, GUIDE_THICKNESS / 2)):
            _zip_tie_slot(length=18.0)

        for x in (-width / 2 + 7.0, width / 2 - 7.0):
            with Locations((x, 0, GUIDE_THICKNESS / 2)):
                _mount_hole()

        for x in (-gate_radius, gate_radius):
            with Locations((x, 0, GUIDE_THICKNESS)):
                Cylinder(WALL_THICKNESS / 2, 15.0, align=(Align.CENTER, Align.CENTER, Align.MIN))

        with Locations((0, 0, GUIDE_THICKNESS + 15.0)):
            Cylinder(
                gate_radius + WALL_THICKNESS / 2,
                WALL_THICKNESS,
                rotation=(0, 90, 0),
                align=(Align.CENTER, Align.CENTER, Align.CENTER),
            )
            Cylinder(
                CABLE_BUNDLE_DIAMETER / 2,
                WALL_THICKNESS + 0.4,
                rotation=(0, 90, 0),
                align=(Align.CENTER, Align.CENTER, Align.CENTER),
                mode=Mode.SUBTRACT,
            )
            Box(
                (gate_radius + WALL_THICKNESS) * 2,
                WALL_THICKNESS + 0.8,
                gate_radius + WALL_THICKNESS,
                align=(Align.CENTER, Align.CENTER, Align.MAX),
                mode=Mode.SUBTRACT,
            )

    return _set_label(guide.part, "base_cable_entry_strain_relief_guide")


def build_base_azimuth_service_loop_guard() -> Part:
    """Low-profile C guard that keeps the base service loop outside the azimuth shaft path."""
    outer_radius = 42.0
    inner_radius = 28.0
    height = 10.0

    with BuildPart() as guard:
        Cylinder(outer_radius, height, align=(Align.CENTER, Align.CENTER, Align.MIN))
        Cylinder(inner_radius, height + 0.4, align=(Align.CENTER, Align.CENTER, Align.MIN), mode=Mode.SUBTRACT)
        Box(
            outer_radius * 2.2,
            outer_radius,
            height + 0.6,
            align=(Align.CENTER, Align.MIN, Align.CENTER),
            mode=Mode.SUBTRACT,
        )

        for x in (-24.0, 24.0):
            with Locations((x, 26.0, height / 2)):
                _mount_hole(height=height + 1.0)

        with Locations((0, 36.0, height / 2)):
            _zip_tie_slot(length=20.0, height=height + 1.0)

    return _set_label(guard.part, "base_azimuth_service_loop_guard")


def build_shoulder_service_loop_anchor() -> Part:
    return _build_anchor("shoulder_service_loop_anchor", loop_radius=9.0, base_length=48.0, base_width=28.0, height=18.0)


def build_elbow_service_loop_anchor() -> Part:
    return _build_anchor("elbow_service_loop_anchor", loop_radius=8.0, base_length=42.0, base_width=26.0, height=16.0)


def build_wrist_service_loop_anchor() -> Part:
    return _build_anchor("wrist_service_loop_anchor", loop_radius=6.0, base_length=34.0, base_width=22.0, height=13.0)


def build_bicep_harness_channel_marker() -> Part:
    with BuildPart() as marker:
        Box(4.0, 86.0, 2.0, align=(Align.CENTER, Align.CENTER, Align.MIN))
        for y in (-32.0, 0.0, 32.0):
            with Locations((0, y, 2.0)):
                Box(16.0, 2.0, 3.0, align=(Align.CENTER, Align.CENTER, Align.MIN))

    return _set_label(marker.part, "bicep_harness_channel_marker")


def build_forearm_harness_channel_marker() -> Part:
    with BuildPart() as marker:
        Box(4.0, 112.0, 2.0, align=(Align.CENTER, Align.CENTER, Align.MIN))
        for y in (-44.0, -14.0, 16.0, 46.0):
            with Locations((0, y, 2.0)):
                Box(14.0, 2.0, 3.0, align=(Align.CENTER, Align.CENTER, Align.MIN))

    return _set_label(marker.part, "forearm_harness_channel_marker")


def build_zip_tie_slot_marker_pair() -> Compound:
    markers: list[Part] = []
    for index, x in enumerate((-10.0, 10.0), start=1):
        with BuildPart() as marker:
            Box(12.0, 24.0, 2.0, align=(Align.CENTER, Align.CENTER, Align.MIN))
            with Locations((0, 0, 1.0)):
                _zip_tie_slot(length=16.0, width=4.2, height=3.0)
        markers.append(_set_label(marker.part.moved(Location((x, 0, 0))), f"zip_tie_slot_marker_{index}"))

    pair = Compound(children=markers, label="zip_tie_slot_marker_pair")
    size = pair.bounding_box().size
    assert_printable_extent((size.X, size.Y, size.Z))
    return pair


def build_model() -> Compound:
    children = [
        build_base_cable_entry_strain_relief_guide().moved(Location((-80.0, -55.0, 0.0))),
        build_base_azimuth_service_loop_guard().moved(Location((20.0, -55.0, 0.0))),
        build_shoulder_service_loop_anchor().moved(Location((-82.0, 25.0, 0.0))),
        build_elbow_service_loop_anchor().moved(Location((-42.0, 25.0, 0.0))),
        build_wrist_service_loop_anchor().moved(Location((-5.0, 25.0, 0.0))),
        build_bicep_harness_channel_marker().moved(Location((35.0, 25.0, 0.0))),
        build_forearm_harness_channel_marker().moved(Location((55.0, 25.0, 0.0))),
        build_zip_tie_slot_marker_pair().moved(Location((88.0, 25.0, 0.0))),
    ]

    model = Compound(children=children, label=MODEL_NAME)
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
