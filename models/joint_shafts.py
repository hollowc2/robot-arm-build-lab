from __future__ import annotations

from build123d import Align, BuildPart, Compound, Cylinder, Location, Mode, Part

try:
    from models.common import BEARING_608_ID, BEARING_625_ID, assert_printable_extent, export_model
except ModuleNotFoundError:
    from common import BEARING_608_ID, BEARING_625_ID, assert_printable_extent, export_model


MODEL_NAME = "joint_shafts"

BASE_SHAFT_DIAMETER = BEARING_608_ID
BASE_SHAFT_LENGTH = 42.0

SHOULDER_SHAFT_DIAMETER = BEARING_608_ID
SHOULDER_SHAFT_LENGTH = 75.0
SHOULDER_PIVOT_SPACER_ID = SHOULDER_SHAFT_DIAMETER + 0.5
SHOULDER_PIVOT_SPACER_OD = 20.0
SHOULDER_PIVOT_SPACER_LENGTH = 11.0

ELBOW_SHAFT_DIAMETER = BEARING_625_ID
ELBOW_SHAFT_LENGTH = 52.0

WRIST_SHAFT_DIAMETER = BEARING_625_ID
WRIST_SHAFT_LENGTH = 52.0


def _build_shaft(*, diameter: float, length: float, axis: str, label: str) -> Part:
    with BuildPart() as shaft:
        rotation = (0, 90, 0) if axis == "x" else (0, 0, 0)
        Cylinder(
            diameter / 2,
            length,
            rotation=rotation,
            align=(Align.CENTER, Align.CENTER, Align.CENTER),
        )

    shaft.part.label = label
    size = shaft.part.bounding_box().size
    assert_printable_extent((size.X, size.Y, size.Z))
    return shaft.part


def build_base_azimuth_shaft() -> Part:
    return _build_shaft(
        diameter=BASE_SHAFT_DIAMETER,
        length=BASE_SHAFT_LENGTH,
        axis="z",
        label="base_azimuth_8mm_shaft",
    )


def build_shoulder_pivot_shaft() -> Part:
    return _build_shaft(
        diameter=SHOULDER_SHAFT_DIAMETER,
        length=SHOULDER_SHAFT_LENGTH,
        axis="x",
        label="shoulder_pivot_8mm_shaft",
    )


def build_shoulder_pivot_spacer() -> Part:
    with BuildPart() as spacer:
        Cylinder(
            SHOULDER_PIVOT_SPACER_OD / 2,
            SHOULDER_PIVOT_SPACER_LENGTH,
            rotation=(0, 90, 0),
            align=(Align.CENTER, Align.CENTER, Align.CENTER),
        )
        Cylinder(
            SHOULDER_PIVOT_SPACER_ID / 2,
            SHOULDER_PIVOT_SPACER_LENGTH + 2.0,
            rotation=(0, 90, 0),
            align=(Align.CENTER, Align.CENTER, Align.CENTER),
            mode=Mode.SUBTRACT,
        )

    spacer.part.label = "shoulder_pivot_8mm_spacer"
    size = spacer.part.bounding_box().size
    assert_printable_extent((size.X, size.Y, size.Z))
    return spacer.part


def build_elbow_pivot_shaft() -> Part:
    return _build_shaft(
        diameter=ELBOW_SHAFT_DIAMETER,
        length=ELBOW_SHAFT_LENGTH,
        axis="x",
        label="elbow_pivot_5mm_shaft",
    )


def build_wrist_pivot_shaft() -> Part:
    return _build_shaft(
        diameter=WRIST_SHAFT_DIAMETER,
        length=WRIST_SHAFT_LENGTH,
        axis="x",
        label="wrist_pivot_5mm_shaft",
    )


def build_model() -> Compound:
    shafts = Compound(
        children=[
            build_base_azimuth_shaft().moved(Location((-70, 0, 0))),
            build_shoulder_pivot_shaft().moved(Location((-25, 0, 0))),
            build_shoulder_pivot_spacer().moved(Location((20, 0, 0))),
            build_elbow_pivot_shaft().moved(Location((55, 0, 0))),
            build_wrist_pivot_shaft().moved(Location((105, 0, 0))),
        ],
        label=MODEL_NAME,
    )
    size = shafts.bounding_box().size
    assert_printable_extent((size.X, size.Y, size.Z))
    return shafts


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
