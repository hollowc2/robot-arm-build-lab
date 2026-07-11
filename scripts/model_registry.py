from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelEntry:
    module: str
    name: str
    title: str
    category: str
    status: str
    print_ready: bool
    material: str = "PETG"
    print_orientation: str = "largest flat face down"
    hardware: tuple[str, ...] = ()
    guard_dependencies: tuple[str, ...] = ()
    validation: str = "cad-only"


MODEL_REGISTRY: tuple[ModelEntry, ...] = (
    ModelEntry("models.geared_base_stator", "geared_base_stator", "Geared Base Stator", "base", "prototype", True),
    ModelEntry("models.azimuth_turntable_shoulder_cleat", "azimuth_turntable_shoulder_cleat", "Azimuth Turntable Shoulder Cleat", "base", "prototype", True),
    ModelEntry("models.bicep_arm_link", "bicep_arm_link", "Bicep Arm Link", "arm", "prototype", True),
    ModelEntry("models.forearm_link", "forearm_link", "Forearm Link", "arm", "prototype", True),
    ModelEntry("models.electronics_mounts", "electronics_mounts", "Electronics Mounts", "electronics", "draft", True),
    ModelEntry("models.wire_management", "wire_management", "Wire Management", "electronics", "draft", True),
    ModelEntry("models.joint_shafts", "joint_shafts", "Joint Shafts", "hardware", "reference", False),
    ModelEntry("models.sg90_gripper_base", "sg90_gripper_base", "SG90 Gripper Base", "end effector", "draft", True),
    ModelEntry("models.sg90_parallel_gripper", "sg90_parallel_gripper", "SG90 Parallel Gripper", "end effector", "prototype", True),
    ModelEntry("models.byj48_stepper_motor", "byj48_stepper_motor", "28BYJ-48 Stepper Motor", "reference", "reference", False),
    ModelEntry("models.nema17_stepper_motor", "nema17_stepper_motor", "NEMA 17 Stepper Motor", "reference", "reference", False),
    ModelEntry("models.transmission_components", "transmission_components", "Transmission Components", "drive", "prototype", True),
    ModelEntry("models.belt_base_candidate", "belt_base_candidate", "342-3M Belt Base Candidate", "base", "comparison", True, hardware=("HTD 342-3M-8 belt", "608 bearings", "NEMA 17", "M3 hardware")),
    ModelEntry("models.safety_guards", "safety_guards", "Transmission Safety Guards", "safety", "prototype", True, hardware=("captive M3 screws",), validation="fit-test-required"),
    ModelEntry("models.electronics_enclosure", "electronics_enclosure", "Electronics Enclosure", "safety", "prototype", True, hardware=("M3 screws", "guard interlock switch"), validation="fit-test-required"),
    ModelEntry("models.wrist_keyed_shaft_adapter", "wrist_keyed_28byj_shaft_to_pulley_adapter", "Wrist Keyed Shaft Adapter", "drive", "prototype", True),
    ModelEntry("models.master_assembly", "robot_arm_master_assembly", "Robot Arm Master Assembly", "assembly", "active", False),
    ModelEntry("models.guarded_assembly", "robot_arm_guarded_assembly", "Guarded Robot Arm Assembly", "assembly", "prototype", False, guard_dependencies=("base_drive_guard", "shoulder_belt_guard", "elbow_belt_guard", "wrist_belt_guard", "gripper_linkage_guard", "electronics_enclosure"), validation="full-sweep-required"),
)


REQUIRED_EXPORT_NAMES = tuple(entry.name for entry in MODEL_REGISTRY)
