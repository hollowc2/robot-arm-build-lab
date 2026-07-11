from __future__ import annotations

from build123d import Compound

try:
    from models.common import export_model
    from models.master_assembly import build_guarded_model
except ModuleNotFoundError:
    from common import export_model
    from master_assembly import build_guarded_model


MODEL_NAME = "robot_arm_guarded_assembly"


def build_model() -> Compound:
    model = build_guarded_model()
    model.label = MODEL_NAME
    return model


def main() -> None:
    export_model(build_model(), MODEL_NAME)


if __name__ == "__main__":
    main()
