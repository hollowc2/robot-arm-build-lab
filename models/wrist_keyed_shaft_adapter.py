from __future__ import annotations

try:
    from models.common import export_model
    from models.transmission_components import build_wrist_keyed_shaft_adapter
except ModuleNotFoundError:
    from common import export_model
    from transmission_components import build_wrist_keyed_shaft_adapter


PART_NAME = "wrist_keyed_28byj_shaft_to_pulley_adapter"


def build_model():
    return build_wrist_keyed_shaft_adapter()


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
