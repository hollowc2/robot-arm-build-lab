from build123d import Box

from scripts.export_models import export_printed_mesh


def test_empty_printed_group_removes_obsolete_mesh(tmp_path):
    destination = tmp_path / "simulator_wrist_hardware.stl"
    export_printed_mesh([Box(1, 2, 3)], destination)
    assert destination.stat().st_size > 84
    export_printed_mesh([], destination)
    assert not destination.exists()
    export_printed_mesh([], destination)
