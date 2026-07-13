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
            children_by_label = {child.label: child for child in children}
            gripper_children = {child.label: child for child in children_by_label["sg90_parallel_gripper"].children}
            export_model(model, entry.name)
            simulator_parts = {
                "simulator_base_fixed": (
                    "geared_base_stator", "base_nema17_stepper_motor",
                    "base_driver_20T_module1_herringbone_5mm_round_shaft",
                ),
                "simulator_base_yaw": (
                    "base_driven_120T_module1_herringbone_48mm_bore_6xM3_60BC",
                    "base_azimuth_8mm_shaft", "installed_bearing_01_608-2RS_bearing",
                    "installed_bearing_02_608-2RS_bearing", "azimuth_turntable_shoulder_cleat",
                    "shoulder_nema17_stepper_motor", "shoulder_pivot_8mm_shaft",
                    "installed_bearing_03_608-2RS_bearing", "installed_bearing_04_608-2RS_bearing",
                ),
                "simulator_upper_arm": (
                    "bicep_arm_link", "shoulder_pivot_8mm_spacer", "elbow_nema17_stepper_motor",
                    "elbow_pivot_5mm_shaft", "installed_bearing_05_625-2RS_bearing",
                    "installed_bearing_06_625-2RS_bearing",
                ),
                "simulator_forearm": (
                    "forearm_link", "wrist_28BYJ-48_stepper_motor", "wrist_pivot_5mm_shaft",
                    "installed_bearing_07_625-2RS_bearing", "installed_bearing_08_625-2RS_bearing",
                ),
                "simulator_wrist_hardware": (
                    "installed_bearing_09_625-2RS_bearing", "installed_bearing_10_625-2RS_bearing",
                    "installed_sg90_micro_servo_1", "installed_sg90_micro_servo_2",
                ),
                "simulator_shoulder_driver": ("shoulder_driver_16T_HTD3M_5mm_D_shaft",),
                "simulator_shoulder_belt": ("shoulder_16T_to_80T_HTD3M_open_belt_visual",),
                "simulator_shoulder_driven": ("shoulder_80T_HTD3M_8p5_4xM3_25BC",),
                "simulator_elbow_driver": ("elbow_driver_16T_HTD3M_5mm_round_shaft",),
                "simulator_elbow_belt": ("elbow_16T_to_60T_HTD3M_open_belt_visual",),
                "simulator_elbow_driven": ("elbow_60T_HTD3M_16p15_4xM3_25BC",),
                "simulator_wrist_driver": (
                    "wrist_keyed_28byj_shaft_to_pulley_adapter", "wrist_driver_20T_HTD3M_5mm_D_shaft",
                ),
                "simulator_wrist_belt": ("wrist_20T_to_32T_HTD3M_open_belt_visual",),
                "simulator_wrist_driven": ("wrist_32T_HTD3M_16p15_4xM3_20BC",),
            }
            fastener_groups = {
                "simulator_base_yaw": ("installed_M3_fastener_base_gear_",),
                "simulator_upper_arm": ("installed_M3_fastener_shoulder_pulley_",),
                "simulator_forearm": ("installed_M3_fastener_elbow_pulley_",),
                "simulator_wrist_hardware": (
                    "installed_M3_fastener_servo_", "installed_M3_fastener_jaw_",
                    "installed_M3_fastener_wrist_pulley_",
                ),
            }
            for name, labels in simulator_parts.items():
                prefixes = fastener_groups.get(name, ())
                parts = [children_by_label[label] for label in labels]
                parts.extend(child for child in children if child.label.startswith(prefixes))
                export_stl(Compound(children=parts), OUT_DIR / f"{name}.stl")

            for name, labels in {
                "simulator_gripper_base": ("sg90_gripper_base",),
                "simulator_gripper_left": (
                    "left_sg90_gripper_jaw", "left_sg90_servo_horn_adapter", "left_sg90_gripper_pushrod",
                ),
                "simulator_gripper_right": (
                    "right_sg90_gripper_jaw", "right_sg90_servo_horn_adapter", "right_sg90_gripper_pushrod",
                ),
            }.items():
                export_stl(Compound(children=[gripper_children[label] for label in labels]), OUT_DIR / f"{name}.stl")
        else:
            export_model(model, entry.name)


if __name__ == "__main__":
    main()
