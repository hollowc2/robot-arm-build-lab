from __future__ import annotations

import importlib
import sys
from pathlib import Path

try:
    from scripts.model_registry import MODEL_REGISTRY
except ModuleNotFoundError:
    from model_registry import MODEL_REGISTRY


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> None:
    from build123d import Compound, export_stl
    from models.common import OUT_DIR, export_model

    requested = set(sys.argv[1:])
    for entry in MODEL_REGISTRY:
        if requested and entry.name not in requested:
            continue
        module = importlib.import_module(entry.module)
        build_for_export = getattr(module, "build_printable_model", module.build_model)
        model = build_for_export()
        if entry.name == "robot_arm_master_assembly":
            children = tuple(model.children)
            gripper_children = tuple(children[32].children)
            export_model(model, entry.name)
            link_ranges = {
                "simulator_base_fixed": (0, 1, 3),
                "simulator_base_yaw": (2, *range(4, 9), *range(11, 14)),
                "simulator_upper_arm": (14, 15, 16, *range(20, 23)),
                "simulator_forearm": (23, 25, *range(29, 32)),
                "simulator_wrist_hardware": tuple(range(33, 47)),
            }
            for name, indexes in link_ranges.items():
                export_stl(Compound(children=[children[index] for index in indexes]), OUT_DIR / f"{name}.stl")

            drivetrain_ranges = {
                "simulator_shoulder_driver": (9,),
                "simulator_shoulder_belt": (10,),
                "simulator_shoulder_driven": (19,),
                "simulator_elbow_driver": (17,),
                "simulator_elbow_belt": (18,),
                "simulator_elbow_driven": (24,),
                "simulator_wrist_driver": (26, 27),
                "simulator_wrist_belt": (28,),
                "simulator_wrist_driven": (47,),
            }
            for name, indexes in drivetrain_ranges.items():
                export_stl(Compound(children=[children[index] for index in indexes]), OUT_DIR / f"{name}.stl")

            for name, indexes in {
                "simulator_gripper_base": (0,),
                "simulator_gripper_left": (1, 2, 3),
                "simulator_gripper_right": (4, 5, 6),
            }.items():
                export_stl(Compound(children=[gripper_children[index] for index in indexes]), OUT_DIR / f"{name}.stl")
        else:
            export_model(model, entry.name)


if __name__ == "__main__":
    main()
