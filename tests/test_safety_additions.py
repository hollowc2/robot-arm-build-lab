from __future__ import annotations

import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


def test_342_3m_base_candidate_preserves_ratio_and_belt_length() -> None:
    from models import belt_base_candidate
    from models.common import HTD_342_3M_PITCH_LENGTH, open_belt_pitch_length

    assert belt_base_candidate.REDUCTION_RATIO == pytest.approx(6.0)
    assert open_belt_pitch_length(
        belt_base_candidate.DRIVER_TEETH,
        belt_base_candidate.DRIVEN_TEETH,
        belt_base_candidate.BELT_CENTER_DISTANCE,
    ) == pytest.approx(HTD_342_3M_PITCH_LENGTH)
    assert belt_base_candidate.TENSION_TRAVEL >= 6.0
    assert belt_base_candidate.PLATE_X <= 256.0
    assert belt_base_candidate.PLATE_Y <= 256.0


def test_impossible_20t_120t_pair_is_rejected_for_342_belt() -> None:
    from models.common import HTD_342_3M_PITCH_LENGTH, solve_open_belt_center_distance

    with pytest.raises(ValueError, match="too short"):
        solve_open_belt_center_distance(20, 120, HTD_342_3M_PITCH_LENGTH)


def test_guard_and_enclosure_safety_parameters() -> None:
    from models import electronics_enclosure, safety_guards

    assert safety_guards.WALL_THICKNESS >= 2.4
    assert safety_guards.MOVING_CLEARANCE >= 3.0
    assert safety_guards.FINGER_EXCLUSION_OPENING < 5.0
    assert electronics_enclosure.WALL >= 2.4
    assert electronics_enclosure.VENT_WIDTH < 5.0


def test_guarded_assembly_contains_required_protection() -> None:
    from models.guarded_assembly import build_model

    assembly = build_model()
    labels = {child.label for child in assembly.children}
    assert {
        "electronics_enclosure",
        "base_drive_guard",
        "shoulder_belt_guard",
        "elbow_belt_guard",
        "wrist_belt_guard",
        "gripper_linkage_guard",
        "base_cable_entry_strain_relief_guide",
        "base_azimuth_service_loop_guard",
    }.issubset(labels)

    children = {child.label: child for child in assembly.children}
    for belt_label, guard_label in (
        ("shoulder_16T_to_80T_HTD3M_open_belt_visual", "shoulder_belt_guard"),
        ("elbow_16T_to_60T_HTD3M_open_belt_visual", "elbow_belt_guard"),
        ("wrist_20T_to_32T_HTD3M_open_belt_visual", "wrist_belt_guard"),
    ):
        belt = children[belt_label].bounding_box()
        guard = children[guard_label].bounding_box()
        assert guard.min.X < belt.min.X < belt.max.X < guard.max.X
        assert guard.min.Y < belt.min.Y < belt.max.Y < guard.max.Y
        assert guard.min.Z < belt.min.Z < belt.max.Z < guard.max.Z


def test_safety_controller_host_state_machine(tmp_path: Path) -> None:
    executable = tmp_path / "safety-controller-test"
    subprocess.run(
        [
            "g++",
            "-std=c++17",
            "-Ifirmware/include",
            "firmware/src/safety_controller.cpp",
            "firmware/test/test_safety_controller.cpp",
            "-o",
            str(executable),
        ],
        cwd=ROOT,
        check=True,
    )
    subprocess.run([str(executable)], check=True)
    subprocess.run(
        [
            "g++",
            "-std=c++17",
            "-Ifirmware/test",
            "-Ifirmware/include",
            "-fsyntax-only",
            "firmware/src/main.cpp",
        ],
        cwd=ROOT,
        check=True,
    )
