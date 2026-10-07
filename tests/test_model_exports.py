from build123d import Box, Cylinder, export_stl

from scripts.export_models import export_printed_mesh


def test_empty_printed_group_removes_obsolete_mesh(tmp_path):
    destination = tmp_path / "simulator_wrist_hardware.stl"
    export_printed_mesh([Box(1, 2, 3)], destination)
    assert destination.stat().st_size > 84
    export_printed_mesh([], destination)
    assert not destination.exists()
    export_printed_mesh([], destination)


def test_simulator_mesh_remeshes_cached_print_geometry(tmp_path):
    part = Cylinder(20, 30)
    printable = tmp_path / "print.stl"
    web = tmp_path / "simulator_link.stl"
    export_stl(part, printable, tolerance=0.001, angular_tolerance=0.1)
    print_bytes = printable.read_bytes()

    export_printed_mesh([part], web)

    assert web.stat().st_size < printable.stat().st_size
    assert printable.read_bytes() == print_bytes
