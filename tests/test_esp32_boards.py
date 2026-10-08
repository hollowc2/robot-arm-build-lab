import pytest
from build123d import Cylinder, Pos

from models import esp32_boards as boards
from models.electronics_mounts import UNO_HOLE_POINTS


@pytest.fixture(scope="module")
def expansion():
    return boards.build_expansion()


@pytest.fixture(scope="module")
def devkit():
    return boards.build_devkit()


def test_expansion_photo_dimensions_and_nonrectangular_holes(expansion):
    pcb = next(p for p in expansion.children if p.label == "pcb_black")
    assert pcb.bounding_box().size.X == pytest.approx(68.6)
    assert pcb.bounding_box().size.Y == pytest.approx(53.4)
    assert pcb.bounding_box().size.Z == pytest.approx(1.6)
    a, b, c, d = boards.EXPANSION_HOLE_POINTS
    assert a[0] - b[0] == pytest.approx(52.52)
    assert d[0] - c[0] == pytest.approx(50.81)
    assert a[1] - d[1] == pytest.approx(48.39)
    assert b[1] - c[1] == pytest.approx(27.96)
    for x, y in boards.EXPANSION_HOLE_POINTS:
        assert (pcb & (Pos(x, y, 0.8) * Cylinder(1.699, 1.6))) is None
        assert (pcb & (Pos(x + 1.9, y, 0.8) * Cylinder(0.1, 1.6))).volume > 0


def test_devkit_has_thirty_aligned_pins_and_seats_above_carrier(devkit, expansion):
    pcb = next(p for p in devkit.children if p.label == "pcb_black")
    assert tuple(pcb.bounding_box().size) == pytest.approx((53, 28.2, 1.6))
    pins = [p for p in devkit.children if p.label == "electronics_gold" and p.bounding_box().min.Z < 0]
    assert len(pins) == 30
    centers = sorted((p.bounding_box().center().X, p.bounding_box().center().Y) for p in pins)
    for actual, expected in zip(centers, sorted(boards.header_points()), strict=True):
        assert actual == pytest.approx(expected)
    for side in (-1, 1):
        row = sorted(x for x, y in centers if y * side > 0)
        assert [b - a for a, b in zip(row, row[1:])] == pytest.approx([2.54] * 14)
    assert boards.DEVKIT_SEATED_Z == pytest.approx(12.6)
    seated = [p.moved(Pos(boards.SOCKET_CENTER_X, 0, boards.DEVKIT_SEATED_Z)) for p in devkit.children]
    # Pin tips lie inside real socket cavities, clear of socket plastic.
    for child in seated:
        if child.label == "electronics_gold" and child.bounding_box().min.Z < boards.DEVKIT_SEATED_Z:
            assert child.bounding_box().min.Z == pytest.approx(boards.PCB_THICKNESS + boards.SOCKET_HEIGHT - boards.PIN_INSERTION)
            for socket in expansion.children:
                if socket.label == "electronics_black":
                    overlap = child & socket
                    assert overlap is None or overlap.volume < 1e-7


def test_purchased_models_are_valid_labeled_component_leaves(expansion, devkit):
    for model in (expansion, devkit):
        assert model.is_valid
        assert model.volume > 0
        assert {p.label for p in model.children} == set(boards.FINISH_COLORS)
        assert all(p.volume > 0 for p in model.children)


def test_clone_dimensions_and_usb_variant_are_configurable():
    model = boards.build_devkit(boards.DevkitSpec(length=52, width=28.5, usb_variant="usb-c"))
    pcb = next(p for p in model.children if p.label == "pcb_black")
    assert pcb.bounding_box().size.X == pytest.approx(52)
    assert pcb.bounding_box().size.Y == pytest.approx(28.5)
    with pytest.raises(ValueError):
        boards.DevkitSpec(usb_variant="unknown")
    with pytest.raises(ValueError):
        boards.DevkitSpec(width=20)


def test_photo_pattern_does_not_silently_claim_nominal_m3_fit():
    angle, offset, residual, order = boards.mounting_registration()
    assert angle == pytest.approx(-8.063306, abs=1e-5)
    assert max(residual) == pytest.approx(2.553347, abs=1e-6)
    assert max(residual) > (boards.MOUNT_HOLE_DIAMETER - 3) / 2
    assert len(UNO_HOLE_POINTS) == len(residual) == 4
    assert order == (3, 2, 1, 0)
    for point, index, error in zip(boards.registered_hole_points(), order, residual):
        assert sum((a - b)**2 for a, b in zip(point, UNO_HOLE_POINTS[index]))**0.5 == pytest.approx(error)


def test_installed_board_screws_seat_and_match_approved_bosses(master_assembly):
    from models import azimuth_turntable_shoulder_cleat as mount
    from models.master_assembly import AZIMUTH_TURNTABLE_Z

    children = {p.label: p for p in master_assembly.children}
    installed = children["installed_esp32_expansion_30pin"]
    location = boards.board_mount_location(AZIMUTH_TURNTABLE_Z)
    pcb = next(p for p in installed.children if p.label == "pcb_black")
    assert pcb.bounding_box().min.X == pytest.approx(location.position.X)
    assert pcb.bounding_box().max.X == pytest.approx(location.position.X + boards.PCB_THICKNESS)
    assert installed.bounding_box().min.X >= location.position.X - 0.9 - 1e-6
    for i, (y, z) in enumerate(mount.ESP32_STANDOFF_POINTS_YZ, 1):
        screw = children[f"installed_M3_fastener_esp32_{i}"]
        bb = screw.bounding_box()
        assert bb.center().Y == pytest.approx(y)
        assert bb.center().Z == pytest.approx(AZIMUTH_TURNTABLE_Z + z)
        assert bb.max.X == pytest.approx(pcb.bounding_box().max.X + 3)
        assert bb.min.X == pytest.approx(pcb.bounding_box().max.X - 6)
        assert (screw & pcb) is None or (screw & pcb).volume < 1e-7
        # The boss pilot remains empty on the axis; a surrounding annulus finds material.
        probe = Pos(location.position.X - 2, y, AZIMUTH_TURNTABLE_Z + z) * Cylinder(1.249, 3.5, rotation=(0, 90, 0))
        overlap = children["azimuth_turntable_shoulder_cleat"] & probe
        assert overlap is None or overlap.volume < 1e-7


def test_mounted_boards_clear_structure_and_sampled_shoulder_motion(master_assembly):
    import re
    from pathlib import Path
    from build123d import Compound, Rot
    from models.master_assembly import AZIMUTH_TURNTABLE_Z
    from models import azimuth_turntable_shoulder_cleat as mount

    children = {p.label: p for p in master_assembly.children}
    electronics = Compound([children["installed_esp32_expansion_30pin"],
                            children["installed_esp32_devkit_30pin"]])
    for name in ("azimuth_turntable_shoulder_cleat", "shoulder_nema17_stepper_motor",
                 "shoulder_16T_to_80T_HTD3M_open_belt_visual", "shoulder_driver_16T_HTD3M_5mm_D_shaft"):
        overlap = electronics & children[name]
        assert overlap is None or sum(s.volume for s in overlap.solids()) < 1e-6, f"Electronics intersect {name}"
    source = (Path(__file__).resolve().parents[1] / "site/src/arm.ts").read_text()
    match = re.search(r"shoulder: \[(-?\d+), (-?\d+)\]", source)
    lower, upper = map(int, match.groups())
    pivot = AZIMUTH_TURNTABLE_Z + mount.PIVOT_Z
    for angle in sorted({lower, upper, *range(lower, upper + 1, 5)}):
        move = Pos(0, 0, pivot) * Rot(-angle, 0, 0) * Pos(0, 0, -pivot)
        for name in ("bicep_arm_link", "elbow_nema17_stepper_motor", "shoulder_80T_HTD3M_8p5_4xM3_25BC"):
            clearance = electronics.distance_to(children[name].moved(move))
            assert clearance >= 1.0, f"Shoulder {angle}°: {name} is {clearance:.3f} mm from boards"
