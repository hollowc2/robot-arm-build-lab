from __future__ import annotations

from build123d import Align, Axis, Box, BuildPart, Cylinder, Locations, Mode, Part, chamfer

try:
    from models.common import M3_CLEARANCE, NEMA17_BODY, NEMA17_HOLE_SPACING, NEMA17_PILOT, NEMA17_SHAFT, export_model
except ModuleNotFoundError:
    from common import M3_CLEARANCE, NEMA17_BODY, NEMA17_HOLE_SPACING, NEMA17_PILOT, NEMA17_SHAFT, export_model


PART_NAME = "nema17_stepper_motor"

BODY_DEPTH = 40.0
FRONT_BOSS_HEIGHT = 2.0
SHAFT_LENGTH = 22.0
REAR_CAP_DEPTH = 4.0
MOUNT_HOLE_DEPTH = 4.5


def build_model() -> Part:
    """Build a lightweight NEMA 17 motor envelope.

    Coordinate contract:
    - The front mounting face is on local Z=0.
    - The motor body extends along local -Z.
    - The shaft and pilot boss extend along local +Z.
    """

    with BuildPart() as motor:
        with Locations((0, 0, -BODY_DEPTH / 2)):
            Box(
                NEMA17_BODY,
                NEMA17_BODY,
                BODY_DEPTH,
                align=(Align.CENTER, Align.CENTER, Align.CENTER),
            )

        with Locations((0, 0, -BODY_DEPTH - REAR_CAP_DEPTH / 2)):
            Box(
                NEMA17_BODY - 3.0,
                NEMA17_BODY - 3.0,
                REAR_CAP_DEPTH,
                align=(Align.CENTER, Align.CENTER, Align.CENTER),
            )

        Cylinder(
            NEMA17_PILOT / 2,
            FRONT_BOSS_HEIGHT,
            align=(Align.CENTER, Align.CENTER, Align.MIN),
        )
        Cylinder(
            NEMA17_SHAFT / 2,
            SHAFT_LENGTH,
            align=(Align.CENTER, Align.CENTER, Align.MIN),
        )

        half_spacing = NEMA17_HOLE_SPACING / 2
        with Locations(
            (-half_spacing, -half_spacing, -MOUNT_HOLE_DEPTH / 2),
            (-half_spacing, half_spacing, -MOUNT_HOLE_DEPTH / 2),
            (half_spacing, -half_spacing, -MOUNT_HOLE_DEPTH / 2),
            (half_spacing, half_spacing, -MOUNT_HOLE_DEPTH / 2),
        ):
            Cylinder(
                M3_CLEARANCE / 2,
                MOUNT_HOLE_DEPTH + 0.2,
                align=(Align.CENTER, Align.CENTER, Align.CENTER),
                mode=Mode.SUBTRACT,
            )

        chamfer(motor.part.edges().filter_by(Axis.Z), length=0.7)

    motor.part.label = PART_NAME
    return motor.part


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
