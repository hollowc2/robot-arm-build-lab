"""Simple, dimensionally useful purchased-hardware models for assembly previews."""

from __future__ import annotations

from build123d import Align, BuildPart, BuildSketch, Compound, Cylinder, Location, Mode, Part, Plane

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


def build_sg90_servo_parts() -> tuple[Part, ...]:
    """Blue case, nylon output spline, side labels and short three-wire lead.

    Preserve the gripper's deck at Z=0 and output axis at Y=6.5, Z=3..8.
    """
    from build123d import Box, Locations, Pos

    with BuildPart() as case:
        Box(SG90_BODY_Y, SG90_BODY_X, SG90_HEIGHT, align=(Align.CENTER, Align.CENTER, Align.MAX))
        # Shallow seams between the moulded gearbox lid, body and bottom cover.
        for z in (-5.0, -SG90_HEIGHT + 3.0):
            with Locations((0, 0, z)):
                Box(SG90_BODY_Y + 0.2, SG90_BODY_X + 0.2, 0.3, mode=Mode.SUBTRACT)
                Box(SG90_BODY_Y - 0.5, SG90_BODY_X - 0.5, 0.3)
        Box(SG90_BODY_Y + 3.0, SG90_BODY_X + 12.0, 2.0, align=(Align.CENTER, Align.CENTER, Align.MAX))
        for y in (-16.0, 16.0):
            with Locations((0, y, -1.0)):
                Cylinder(1.6, 2.4, mode=Mode.SUBTRACT)
        with Locations((0, 6.5, 0)):
            Cylinder(5.8, 6.0, align=(Align.CENTER, Align.CENTER, Align.MIN))
        with Locations((0, -2.0, 0)):
            Cylinder(3.1, 2.0, align=(Align.CENTER, Align.CENTER, Align.MIN))
    case.part.label = "sg90_blue_case"
    spline = Pos(0, 6.5, 6) * Cylinder(2.4, 2.0, align=(Align.CENTER, Align.CENTER, Align.MIN))
    # Bore for the horn retaining screw.
    spline -= Pos(0, 6.5, 7) * Cylinder(0.75, 2.2)
    spline.label = "sg90_nylon_spline"
    labels = [Pos(x, 0, -15.5) * Box(0.08, 18, 12) for x in (-SG90_BODY_Y / 2 - 0.04, SG90_BODY_Y / 2 + 0.04)]
    label = labels[0] + labels[1]
    label.label = "sg90_side_label"
    parts = [case.part, spline, label]
    for index, color in enumerate(("brown", "red", "orange")):
        wire = Pos((index - 1) * 1.4, -SG90_BODY_X / 2 - 6, -SG90_HEIGHT + 4) * Cylinder(
            0.55, 12, rotation=(90, 0, 0)
        )
        wire.label = f"motor_wire_{color}"
        parts.append(wire)
    return tuple(parts)


def build_sg90_servo() -> Compound:
    return Compound(children=list(build_sg90_servo_parts()), label="SG90_micro_servo")


def build_sg90_installed(location: Location, label: str) -> Compound:
    return Compound(children=[part.moved(location) for part in build_sg90_servo_parts()], label=label)


def build_m3_socket_screw(length: float, axis: str = "x") -> Part:
    """M3 socket-head cap screw (ISO 4762), centered on its shank length.

    The head sits on the negative side of the chosen axis.
    """
    from build123d import Axis, Locations, RegularPolygon, Rot, extrude, fillet

    with BuildPart() as model:
        Cylinder(1.5, length, align=(Align.CENTER,) * 3)
        # 5.5 mm diameter x 3 mm high head with a 2.5 mm hex socket.
        head_bottom = -length / 2
        with Locations((0, 0, head_bottom)):
            Cylinder(2.75, 3.0, align=(Align.CENTER, Align.CENTER, Align.MAX))
        crown = model.edges().filter_by(Axis.Z, reverse=True).sort_by(Axis.Z)[0]
        fillet(crown, radius=0.4)
        with BuildSketch(Plane.XY.offset(head_bottom - 3.0)):
            RegularPolygon(2.5 / 3**0.5, 6)
        extrude(amount=1.6, mode=Mode.SUBTRACT)
    part = model.part
    if axis == "x":
        part = part.moved(Rot(0, 90, 0))
    part.label = f"M3_socket_cap_screw_{length:g}mm"
    return part


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
