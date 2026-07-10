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
    ModelEntry("models.wrist_keyed_shaft_adapter", "wrist_keyed_28byj_shaft_to_pulley_adapter", "Wrist Keyed Shaft Adapter", "drive", "prototype", True),
    ModelEntry("models.master_assembly", "robot_arm_master_assembly", "Robot Arm Master Assembly", "assembly", "active", False),
)


REQUIRED_EXPORT_NAMES = tuple(entry.name for entry in MODEL_REGISTRY)
