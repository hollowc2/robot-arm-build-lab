from __future__ import annotations

from build123d import (
    Align,
    Box,
    BuildPart,
    Compound,
    Cylinder,
    Kind,
    Location,
    Locations,
    Mode,
    Part,
    Plane,
    Pos,
    Rectangle,
    Sketch,
    chamfer,
    extrude,
    offset,
)

try:
    from models.common import M3_CLEARANCE, NEMA17_BODY, NEMA17_HOLE_SPACING, NEMA17_PILOT, NEMA17_SHAFT, export_model
except ModuleNotFoundError:
    from common import M3_CLEARANCE, NEMA17_BODY, NEMA17_HOLE_SPACING, NEMA17_PILOT, NEMA17_SHAFT, export_model


PART_NAME = "nema17_stepper_motor"

# A 40 mm 17HS4401-style motor: black anodized end bells clamp a laminated
# silicon-steel stator stack, and the rear bell carries a JST-PH socket.
BODY_DEPTH = 40.0
FRONT_CAP_DEPTH = 8.5
REAR_CAP_DEPTH_BODY = 8.5
FRONT_BOSS_HEIGHT = 2.0
SHAFT_LENGTH = 22.0
# Reserved behind the body for the plug, wiring, and rear screw heads.
REAR_CAP_DEPTH = 4.0
MOUNT_HOLE_DEPTH = 4.5

CAP_CORNER_CHAMFER = 3.0
STACK_CORNER_CHAMFER = 4.5
STACK_INSET = 0.15
LAMINATION_PITCH = 2.0
LAMINATION_GROOVE_DEPTH = 0.25
LAMINATION_GROOVE_WIDTH = 0.4

REAR_SCREW_HEAD_DIAMETER = 5.0
REAR_SCREW_HEAD_HEIGHT = 0.8
CONNECTOR_WIDTH_X = 15.0
CONNECTOR_HEIGHT_Z = 5.6
CONNECTOR_DEPTH_Y = 5.0

# Child labels let the simulator give each purchased material its own finish.
CASE_LABEL = "nema17_end_bells"
STACK_LABEL = "nema17_stator_stack"
STEEL_LABEL = "nema17_steel_shaft_and_screws"
CONNECTOR_LABEL = "nema17_jst_connector"


def _hole_points(z: float) -> tuple[tuple[float, float, float], ...]:
    half = NEMA17_HOLE_SPACING / 2
    return tuple((x, y, z) for x in (-half, half) for y in (-half, half))


def _profile(size: float, corner: float) -> Sketch:
    return chamfer(Rectangle(size, size).vertices(), length=corner)


def _build_case() -> Part:
    rear_z = -BODY_DEPTH
    connector_z = rear_z + REAR_CAP_DEPTH_BODY / 2
    bell = _profile(NEMA17_BODY, CAP_CORNER_CHAMFER)
    case = extrude(Plane.XY.offset(-FRONT_CAP_DEPTH) * bell, amount=FRONT_CAP_DEPTH)
    case += extrude(Plane.XY.offset(rear_z) * bell, amount=REAR_CAP_DEPTH_BODY)
    case += Cylinder(NEMA17_PILOT / 2, FRONT_BOSS_HEIGHT, align=(Align.CENTER, Align.CENTER, Align.MIN))
    for point in _hole_points(-MOUNT_HOLE_DEPTH / 2):
        case -= Pos(*point) * Cylinder(M3_CLEARANCE / 2, MOUNT_HOLE_DEPTH + 0.2)
    # Pocket in the rear bell for the flush JST-PH connector housing.
    case -= Pos(0, -NEMA17_BODY / 2, connector_z) * Box(
        CONNECTOR_WIDTH_X, 2 * CONNECTOR_DEPTH_Y, CONNECTOR_HEIGHT_Z
    )
    case.label = CASE_LABEL
    return case


def _build_stator_stack() -> Part:
    stack_size = NEMA17_BODY - 2 * STACK_INSET
    stack_bottom = -BODY_DEPTH + REAR_CAP_DEPTH_BODY
    stack_depth = BODY_DEPTH - FRONT_CAP_DEPTH - REAR_CAP_DEPTH_BODY
    outline = _profile(stack_size, STACK_CORNER_CHAMFER)
    stack = extrude(Plane.XY.offset(stack_bottom) * outline, amount=stack_depth)
    # Shallow grooves read as the stamped lamination layers.
    groove = Rectangle(stack_size + 2, stack_size + 2) - offset(
        outline, amount=-LAMINATION_GROOVE_DEPTH, kind=Kind.INTERSECTION
    )
    groove_count = int(stack_depth // LAMINATION_PITCH)
    first = stack_bottom + (stack_depth - (groove_count - 1) * LAMINATION_PITCH) / 2
    for index in range(groove_count):
        z = first + index * LAMINATION_PITCH - LAMINATION_GROOVE_WIDTH / 2
        stack -= extrude(Plane.XY.offset(z) * groove, amount=LAMINATION_GROOVE_WIDTH)
    stack.label = STACK_LABEL
    return stack


def _build_steel() -> Part:
    with BuildPart() as steel:
        Cylinder(NEMA17_SHAFT / 2, SHAFT_LENGTH, align=(Align.CENTER, Align.CENTER, Align.MIN))
        # Four long screws pull the end bells together from the rear face.
        with Locations(*_hole_points(-BODY_DEPTH)):
            Cylinder(
                REAR_SCREW_HEAD_DIAMETER / 2,
                REAR_SCREW_HEAD_HEIGHT,
                align=(Align.CENTER, Align.CENTER, Align.MAX),
            )
    steel.part.label = STEEL_LABEL
    return steel.part


def _build_connector() -> Part:
    connector_z = -BODY_DEPTH + REAR_CAP_DEPTH_BODY / 2
    with BuildPart() as connector:
        with Locations((0, -NEMA17_BODY / 2, connector_z)):
            Box(
                CONNECTOR_WIDTH_X,
                CONNECTOR_DEPTH_Y,
                CONNECTOR_HEIGHT_Z,
                align=(Align.CENTER, Align.MIN, Align.CENTER),
            )
            # Open socket face for the 6-pin plug.
            Box(
                CONNECTOR_WIDTH_X - 2.0,
                2.4,
                CONNECTOR_HEIGHT_Z - 2.0,
                align=(Align.CENTER, Align.MIN, Align.CENTER),
                mode=Mode.SUBTRACT,
            )
    connector.part.label = CONNECTOR_LABEL
    return connector.part


def build_parts() -> tuple[Part, ...]:
    """The motor's separately finished pieces in local motor coordinates.

    Coordinate contract:
    - The front mounting face is on local Z=0.
    - The motor body extends along local -Z.
    - The shaft and pilot boss extend along local +Z.
    - The connector faces local -Y.
    """
    return (_build_case(), _build_stator_stack(), _build_steel(), _build_connector())


def build_installed(location: Location, label: str) -> Compound:
    """Place a motor while keeping its labeled finish children in world coordinates."""
    return Compound(children=[part.moved(location) for part in build_parts()], label=label)


def build_model() -> Compound:
    return Compound(children=list(build_parts()), label=PART_NAME)


def main() -> None:
    model = build_model()
    export_model(model, PART_NAME)

    try:
        from ocp_vscode import show
    except ImportError:
        return

    show(model)


if __name__ == "__main__":
    main()
