from __future__ import annotations

import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]




def test_impossible_20t_120t_pair_is_rejected_for_342_belt() -> None:
    from models.common import HTD_342_3M_PITCH_LENGTH, solve_open_belt_center_distance

    with pytest.raises(ValueError, match="too short"):
        solve_open_belt_center_distance(20, 120, HTD_342_3M_PITCH_LENGTH)


def test_electronics_enclosure_safety_parameters() -> None:
    from models import electronics_enclosure

    assert electronics_enclosure.WALL >= 2.4
    assert electronics_enclosure.VENT_WIDTH < 5.0


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
