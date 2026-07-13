from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from scripts.model_registry import MODEL_REGISTRY
except ModuleNotFoundError:
    from model_registry import MODEL_REGISTRY


ROOT = Path(__file__).resolve().parents[1]
GENERATED_DIR = ROOT / "site" / "public" / "generated"


VIEWER_PARTS = (
    ("electronics_enclosure", [-98, -94, -58], [98, 94, 3], "draft"),
    ("base_drive_guard", [-78, -78, 8], [78, 78, 30], "draft"),
    ("shoulder_belt_guard", [-27, -52, 62], [-10, 52, 171], "draft"),
    ("elbow_belt_guard", [-31, -42, 214], [-14, 42, 388], "draft"),
    ("wrist_belt_guard", [-29, -30, 390], [-12, 30, 548], "draft"),
    ("gripper_linkage_guard", [-10, 25, 505], [50, 83, 508], "draft"),
    ("geared_base_stator", [-82, -82, 0], [82, 82, 20], "active"),
    ("arduino_uno_r4_minima_tray", [-45, -132, 20], [45, -94, 28], "active"),
    ("base_nema17_driver_board_tray", [48, 42, 20], [92, 78, 28], "active"),
    ("base_cable_entry_strain_relief_guide", [-22, -112, 20], [22, -88, 42], "draft"),
    ("base_azimuth_service_loop_guard", [-58, -58, 24], [58, 58, 34], "draft"),
    ("base_nema17_stepper_motor", [48, -22, 20], [92, 22, 62], "active"),
    ("base_80T_drive_gear", [-42, -42, 20], [42, 42, 34], "active"),
    ("base_driver_pinion", [54, -16, 20], [86, 16, 34], "active"),
    ("base_azimuth_8mm_shaft", [-4, -4, 8], [4, 4, 50], "active"),
    ("azimuth_turntable_shoulder_cleat", [-48, -46, 28], [48, 46, 94], "active"),
    ("shoulder_nema17_stepper_motor", [-86, -22, 52], [-44, 22, 94], "active"),
    ("shoulder_nema17_driver_board_tray", [-86, -66, 54], [-42, -30, 62], "draft"),
    ("shoulder_service_loop_anchor", [40, 16, 36], [72, 44, 54], "draft"),
    ("shoulder_driver_16T_HTD3M_5mm_D_shaft", [-70, -12, 70], [-58, 12, 82], "active"),
    ("shoulder_16T_to_80T_HTD3M_open_belt_visual", [-76, -52, 70], [-54, 52, 82], "active"),
    ("shoulder_pivot_8mm_shaft", [-38, -4, 70], [38, 4, 78], "active"),
    ("bicep_arm_link", [-12, -23, 72], [34, 23, 176], "active"),
    ("bicep_elbow_belt_snap_cover", [-25.587, -34.155, 104], [-8.6, 34.155, 270.35], "draft"),
    ("bicep_harness_channel_marker", [0, -8, 130], [12, 8, 170], "draft"),
    ("shoulder_pivot_8mm_spacer", [8, -10, 70], [20, 10, 82], "active"),
    ("elbow_nema17_stepper_motor", [24, -22, 142], [66, 22, 184], "active"),
    ("elbow_nema17_driver_board_tray", [58, -50, 142], [102, -16, 150], "draft"),
    ("elbow_service_loop_anchor", [34, 12, 136], [66, 40, 154], "draft"),
    ("elbow_driver_16T_HTD3M_5mm_round_shaft", [-28, -12, 150], [-16, 12, 162], "active"),
    ("elbow_16T_to_60T_HTD3M_open_belt_visual", [-36, -48, 150], [-8, 48, 162], "active"),
    ("shoulder_80T_HTD3M_8p5_4xM3_25BC", [-72, -42, 70], [-58, 42, 84], "active"),
    ("elbow_pivot_5mm_shaft", [-28, -3, 150], [26, 3, 156], "active"),
    ("forearm_link", [-2, -20, 150], [28, 20, 252], "active"),
    ("forearm_harness_channel_marker", [4, -7, 198], [18, 7, 238], "draft"),
    ("elbow_60T_HTD3M_16p15_4xM3_25BC", [-34, -32, 150], [-20, 32, 164], "active"),
    ("wrist_28BYJ-48_stepper_motor", [-28, -18, 226], [8, 18, 256], "active"),
    ("wrist_28byj_uln2003_board_tray", [32, -48, 226], [70, -18, 234], "draft"),
    ("wrist_service_loop_anchor", [24, 10, 218], [54, 36, 236], "draft"),
    ("wrist_driver_20T_HTD3M_5mm_D_shaft", [-24, -14, 228], [-8, 14, 244], "active"),
    ("wrist_keyed_28byj_shaft_to_pulley_adapter", [-25, -9, 227], [-7, 9, 245], "active"),
    ("wrist_20T_to_32T_HTD3M_open_belt_visual", [-30, -36, 228], [-2, 36, 244], "active"),
    ("wrist_pivot_5mm_shaft", [4, -3, 246], [54, 3, 252], "active"),
    ("sg90_gripper_base", [14, -18, 246], [50, 18, 286], "active"),
    ("left_sg90_gripper_jaw", [12, 48, 260], [30, 136, 266], "active"),
    ("right_sg90_gripper_jaw", [34, 48, 260], [52, 136, 266], "active"),
    ("left_sg90_servo_horn_adapter", [13, 44, 254], [28, 68, 258], "active"),
    ("right_sg90_servo_horn_adapter", [36, 44, 254], [51, 68, 258], "active"),
    ("left_sg90_gripper_pushrod", [12, 62, 266], [30, 94, 271], "active"),
    ("right_sg90_gripper_pushrod", [34, 62, 266], [52, 94, 271], "active"),
    ("wrist_32T_HTD3M_16p15_4xM3_20BC", [-20, -19, 246], [-6, 19, 260], "active"),
)


def _bbox_payload(min_xyz: list[float], max_xyz: list[float]) -> dict[str, list[float]]:
    return {
        "min": [round(value, 3) for value in min_xyz],
        "max": [round(value, 3) for value in max_xyz],
        "size": [round(max_xyz[axis] - min_xyz[axis], 3) for axis in range(3)],
    }


def _bbox_from_boxes(boxes: list[dict[str, list[float]]]) -> dict[str, list[float]]:
    min_xyz = [min(box["min"][axis] for box in boxes) for axis in range(3)]
    max_xyz = [max(box["max"][axis] for box in boxes) for axis in range(3)]
    return {
        "min": [round(value, 3) for value in min_xyz],
        "max": [round(value, 3) for value in max_xyz],
        "size": [round(max_xyz[axis] - min_xyz[axis], 3) for axis in range(3)],
    }


def _volume_from_bbox(bbox: dict[str, list[float]]) -> float:
    size = bbox["size"]
    return round(size[0] * size[1] * size[2], 3)


def _viewer_children() -> list[dict[str, object]]:
    return [
        {
            "name": name,
            "bbox": _bbox_payload(min_xyz, max_xyz),
            "status": status,
            "volumeMm3": _volume_from_bbox(_bbox_payload(min_xyz, max_xyz)),
        }
        for name, min_xyz, max_xyz, status in VIEWER_PARTS
    ]


def _matching_children(entry_name: str, children: list[dict[str, object]]) -> list[dict[str, object]]:
    if entry_name == "safety_guards":
        return [child for child in children if "guard" in child["name"]]
    if entry_name == "electronics_enclosure":
        return [child for child in children if child["name"] == "electronics_enclosure"]
    if entry_name == "belt_base_candidate":
        return [child for child in children if child["name"] in {"geared_base_stator", "base_drive_guard"}]
    if entry_name == "electronics_mounts":
        return [child for child in children if "tray" in child["name"] or "board" in child["name"]]
    if entry_name == "wire_management":
        return [child for child in children if any(token in child["name"] for token in ("cable", "loop", "harness"))]
    if entry_name == "joint_shafts":
        return [child for child in children if "shaft" in child["name"] or "spacer" in child["name"]]
    if entry_name == "transmission_components":
        return [child for child in children if any(token in child["name"] for token in ("pulley", "belt", "gear", "pinion"))]
    if entry_name == "sg90_parallel_gripper":
        return [
            child
            for child in children
            if child["name"] == "sg90_gripper_base"
            or any(token in child["name"] for token in ("gripper_jaw", "servo_horn_adapter", "gripper_pushrod"))
        ]
    if entry_name == "byj48_stepper_motor":
        return [child for child in children if "28BYJ" in child["name"]]
    if entry_name == "nema17_stepper_motor":
        return [child for child in children if "nema17_stepper_motor" in child["name"]]
    return [child for child in children if child["name"] == entry_name]


def build_catalog() -> dict[str, Any]:
    generated_at = datetime.now(timezone.utc).isoformat()
    children = _viewer_children()

    parts: list[dict[str, Any]] = []

    for entry in MODEL_REGISTRY:
        if entry.name == "robot_arm_master_assembly":
            bbox = _bbox_from_boxes([child["bbox"] for child in children])
            volume = round(sum(float(child["volumeMm3"]) for child in children), 3)
        else:
            matches = _matching_children(entry.name, children)
            bbox = _bbox_from_boxes([match["bbox"] for match in matches])
            volume = round(sum(float(match["volumeMm3"]) for match in matches), 3)
        parts.append(
            {
                "name": entry.name,
                "title": entry.title,
                "module": entry.module,
                "source": f"{entry.module.replace('.', '/')}.py",
                "category": entry.category,
                "status": entry.status,
                "printReady": entry.print_ready,
                "material": entry.material,
                "printOrientation": entry.print_orientation,
                "hardware": list(entry.hardware),
                "guardDependencies": list(entry.guard_dependencies),
                "validation": entry.validation,
                "volumeMm3": volume,
                "bbox": bbox,
                "webModel": f"generated/models/{entry.name}.stl",
            }
        )

    return {
        "project": "Billy Bitcoin's Robot Arm Build Lab",
        "route": "/robot-arm/",
        "generatedAt": generated_at,
        "parts": parts,
    }


def build_viewer_model() -> dict[str, Any]:
    return {
        "name": "robot_arm_master_assembly",
        "format": "bbox-assembly-v1",
        "units": "mm",
        "parts": [
            {"name": child["name"], "bbox": child["bbox"], "status": child["status"]}
            for child in _viewer_children()
        ],
    }


def main() -> None:
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    (GENERATED_DIR / "catalog.json").write_text(json.dumps(build_catalog(), indent=2) + "\n")
    (GENERATED_DIR / "viewer-model.json").write_text(json.dumps(build_viewer_model(), indent=2) + "\n")


if __name__ == "__main__":
    main()
