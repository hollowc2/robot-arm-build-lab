"""Simple, dimensionally useful purchased-hardware models for assembly previews."""

from __future__ import annotations

from build123d import Align, BuildPart, Cylinder, Mode, Part

try:
    from models.common import (
        BEARING_608_ID, BEARING_608_OD, BEARING_608_WIDTH,
        BEARING_625_ID, BEARING_625_OD, BEARING_625_WIDTH,
        M3_NUT_DEPTH, M3_NUT_FLATS, SG90_BODY_X, SG90_BODY_Y, SG90_HEIGHT,
    )
except ModuleNotFoundError:
    from common import (
        BEARING_608_ID, BEARING_608_OD, BEARING_608_WIDTH,
        BEARING_625_ID, BEARING_625_OD, BEARING_625_WIDTH,
        M3_NUT_DEPTH, M3_NUT_FLATS, SG90_BODY_X, SG90_BODY_Y, SG90_HEIGHT,
    )


def _bearing(*, outside: float, bore: float, width: float, axis: str, label: str) -> Part:
    """A shielded radial bearing, centered on its mounting axis."""
    rotation = (0, 90, 0) if axis == "x" else (0, 0, 0)
    with BuildPart() as model:
        Cylinder(outside / 2, width, rotation=rotation, align=(Align.CENTER,) * 3)
        Cylinder(bore / 2, width + 0.2, rotation=rotation, align=(Align.CENTER,) * 3, mode=Mode.SUBTRACT)
    model.part.label = label
    return model.part


def build_608_bearing(axis: str = "x") -> Part:
    return _bearing(outside=BEARING_608_OD, bore=BEARING_608_ID, width=BEARING_608_WIDTH, axis=axis, label="608-2RS_bearing")


def build_625_bearing(axis: str = "x") -> Part:
    return _bearing(outside=BEARING_625_OD, bore=BEARING_625_ID, width=BEARING_625_WIDTH, axis=axis, label="625-2RS_bearing")


def build_sg90_servo() -> Part:
    """Installed SG90 envelope: case, mounting ears, output boss and spline."""
    with BuildPart() as model:
        # The gripper pockets use X=12.2 and Y=23.0 at the deck plane.
        from build123d import Box, Locations
        Box(SG90_BODY_Y, SG90_BODY_X, SG90_HEIGHT, align=(Align.CENTER, Align.CENTER, Align.MAX))
        Box(SG90_BODY_Y + 3.0, SG90_BODY_X + 9.0, 2.0, align=(Align.CENTER, Align.CENTER, Align.MAX))
        with Locations((0, 6.5, 3.0)):
            Cylinder(5.8, 3.0, align=(Align.CENTER, Align.CENTER, Align.MIN))
            Cylinder(2.4, 5.0, align=(Align.CENTER, Align.CENTER, Align.MIN))
    model.part.label = "SG90_micro_servo"
    return model.part


def build_m3_socket_screw(length: float, axis: str = "x") -> Part:
    """M3 socket-head cap screw, centered on its overall length."""
    rotation = (0, 90, 0) if axis == "x" else (0, 0, 0)
    with BuildPart() as model:
        Cylinder(1.5, length, rotation=rotation, align=(Align.CENTER,) * 3)
        # 5.5 mm diameter x 3 mm high socket-cap head.
        head_center = -(length / 2 + 1.5)
        if axis == "x":
            from build123d import Locations
            with Locations((head_center, 0, 0)):
                Cylinder(2.75, 3.0, rotation=rotation, align=(Align.CENTER,) * 3)
        else:
            from build123d import Locations
            with Locations((0, 0, head_center)):
                Cylinder(2.75, 3.0, rotation=rotation, align=(Align.CENTER,) * 3)
    model.part.label = f"M3_socket_cap_screw_{length:g}mm"
    return model.part


def build_m3_nut(axis: str = "x") -> Part:
    rotation = (0, 90, 0) if axis == "x" else (0, 0, 0)
    with BuildPart() as model:
        # Cylindrical envelope keeps this reference model lightweight; its across-flats
        # diameter remains conservative for collision checks.
        Cylinder(M3_NUT_FLATS / 2, M3_NUT_DEPTH, rotation=rotation, align=(Align.CENTER,) * 3)
        Cylinder(1.6, M3_NUT_DEPTH + 0.2, rotation=rotation, align=(Align.CENTER,) * 3, mode=Mode.SUBTRACT)
    model.part.label = "M3_hex_nut"
    return model.part


def build_model() -> Part:
    """Representative purchased hardware for the catalog preview."""
    return build_608_bearing()
