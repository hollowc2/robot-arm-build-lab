from __future__ import annotations

from build123d import Align, Box, BuildPart, Cylinder, Locations, Mode, Part

try:
    from models.common import (
        BYJ48_BODY,
        BYJ48_EAR_SPACING,
        BYJ48_MOUNT_HOLE,
        BYJ48_SHAFT_ACROSS_FLATS,
        BYJ48_SHAFT_DIAMETER,
        export_model,
    )
except ModuleNotFoundError:
    from common import (
        BYJ48_BODY,
        BYJ48_EAR_SPACING,
        BYJ48_MOUNT_HOLE,
        BYJ48_SHAFT_ACROSS_FLATS,
        BYJ48_SHAFT_DIAMETER,
        export_model,
    )


PART_NAME = "28BYJ-48_stepper_motor"

BODY_DEPTH = 19.0
MOUNT_PLATE_THICKNESS = 1.6
MOUNT_EAR_WIDTH = 7.0
MOUNT_EAR_LENGTH = 10.0
FRONT_BOSS_DIAMETER = 9.0
FRONT_BOSS_HEIGHT = 1.5
SHAFT_LENGTH = 10.0
MOUNT_HOLE_DEPTH = 3.0


def build_model() -> Part:
    """Build a lightweight 28BYJ-48 motor envelope.

    Coordinate contract:
    - The front mounting face is on local Z=0.
    - The motor body extends along local -Z.
    - The shaft and front boss extend along local +Z.
    """

    with BuildPart() as motor:
        with Locations((0, 0, -BODY_DEPTH / 2)):
            Cylinder(
                BYJ48_BODY / 2,
                BODY_DEPTH,
                align=(Align.CENTER, Align.CENTER, Align.CENTER),
            )

        with Locations((0, 0, -MOUNT_PLATE_THICKNESS / 2)):
            Box(
                BYJ48_BODY,
                MOUNT_PLATE_THICKNESS,
                MOUNT_PLATE_THICKNESS,
                align=(Align.CENTER, Align.CENTER, Align.CENTER),
            )

        for y in (-BYJ48_EAR_SPACING / 2, BYJ48_EAR_SPACING / 2):
            with Locations((0, y, -MOUNT_PLATE_THICKNESS / 2)):
                Box(
                    MOUNT_EAR_LENGTH,
                    MOUNT_EAR_WIDTH,
                    MOUNT_PLATE_THICKNESS,
                    align=(Align.CENTER, Align.CENTER, Align.CENTER),
                )
            with Locations((0, y, -MOUNT_HOLE_DEPTH / 2)):
                Cylinder(
                    BYJ48_MOUNT_HOLE / 2,
                    MOUNT_HOLE_DEPTH + 0.2,
                    align=(Align.CENTER, Align.CENTER, Align.CENTER),
                    mode=Mode.SUBTRACT,
                )

        Cylinder(
            FRONT_BOSS_DIAMETER / 2,
            FRONT_BOSS_HEIGHT,
            align=(Align.CENTER, Align.CENTER, Align.MIN),
        )
        Cylinder(
            BYJ48_SHAFT_DIAMETER / 2,
            SHAFT_LENGTH,
            align=(Align.CENTER, Align.CENTER, Align.MIN),
        )
        shaft_flat_cut_depth = (
            BYJ48_SHAFT_DIAMETER - BYJ48_SHAFT_ACROSS_FLATS
        ) / 2 + 0.5
        shaft_flat_cut_x = (
            BYJ48_SHAFT_ACROSS_FLATS / 2 + shaft_flat_cut_depth / 2
        )
        for side in (-1.0, 1.0):
            with Locations((side * shaft_flat_cut_x, 0, SHAFT_LENGTH / 2)):
                Box(
                    shaft_flat_cut_depth,
                    BYJ48_SHAFT_DIAMETER + 1.0,
                    SHAFT_LENGTH + 0.2,
                    align=(Align.CENTER, Align.CENTER, Align.CENTER),
                    mode=Mode.SUBTRACT,
                )

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
