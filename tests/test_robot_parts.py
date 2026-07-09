import importlib
from math import pi

import pytest


PART_MODULES = [
    "models.geared_base_stator",
    "models.azimuth_turntable_shoulder_cleat",
    "models.bicep_arm_link",
    "models.forearm_link",
    "models.electronics_mounts",
    "models.wire_management",
    "models.joint_shafts",
    "models.sg90_gripper_base",
    "models.byj48_stepper_motor",
    "models.nema17_stepper_motor",
    "models.transmission_components",
    "models.wrist_keyed_shaft_adapter",
    "models.master_assembly",
]


def test_robot_part_models_have_volume() -> None:
    for module_name in PART_MODULES:
        module = importlib.import_module(module_name)
        model = module.build_model()
        assert model.volume > 0, module_name


def test_master_assembly_has_all_major_children() -> None:
    from models.master_assembly import build_model

    assembly = build_model()

    assert len(assembly.children) == 26
    assert assembly.volume > 0


def test_master_assembly_arm_pulley_planes_match_motor_layout() -> None:
    from models.master_assembly import build_model

    assembly = build_model()
    children = list(assembly.children)
    children_by_label = {child.label: child for child in children}

    shoulder_driver = children_by_label["shoulder_driver_16T_HTD3M_5mm_D_shaft"]
    shoulder_driven = children_by_label["shoulder_80T_HTD3M_8p5_4xM3_25BC"]
    shoulder_belt = children_by_label["shoulder_16T_to_80T_HTD3M_open_belt_visual"]
    elbow_driver = children_by_label["elbow_driver_16T_HTD3M_5mm_round_shaft"]
    elbow_driven = children_by_label["elbow_60T_HTD3M_16p15_4xM3_25BC"]
    elbow_belt = children_by_label["elbow_16T_to_60T_HTD3M_open_belt_visual"]
    wrist_driver = children_by_label["wrist_driver_20T_HTD3M_5mm_D_shaft"]
    wrist_adapter = children_by_label["wrist_keyed_28byj_shaft_to_pulley_adapter"]
    wrist_driven = children_by_label["wrist_48T_HTD3M_16p15_4xM3_20BC"]
    wrist_belt = children_by_label["wrist_20T_to_48T_HTD3M_open_belt_visual"]
    elbow_motor = children_by_label["elbow_nema17_stepper_motor"]

    def center_x(part) -> float:
        bbox = part.bounding_box()
        return (bbox.min.X + bbox.max.X) / 2

    shoulder_x = center_x(shoulder_driven)
    elbow_x = center_x(elbow_driven)

    assert shoulder_x < 0
    assert center_x(shoulder_driver) == pytest.approx(shoulder_x)
    assert center_x(shoulder_belt) == pytest.approx(shoulder_x)
    assert elbow_x < 0
    assert center_x(elbow_driver) == pytest.approx(elbow_x)
    assert center_x(elbow_belt) == pytest.approx(elbow_x)
    assert elbow_motor.bounding_box().min.X < elbow_x < elbow_motor.bounding_box().max.X
    assert elbow_motor.bounding_box().max.X > 0
    assert center_x(wrist_driver) == pytest.approx(center_x(wrist_driven))
    assert center_x(wrist_adapter) == pytest.approx(center_x(wrist_driver))
    assert center_x(wrist_belt) == pytest.approx(center_x(wrist_driven))
    assert shoulder_driver.label.endswith("D_shaft")
    assert elbow_driver.label.endswith("round_shaft")
    assert wrist_driver.label.endswith("D_shaft")


def test_bicep_motor_mount_is_compact_and_motor_side_facing() -> None:
    from models import bicep_arm_link

    model = bicep_arm_link.build_model()
    bbox = model.bounding_box()

    assert bbox.size.Y == pytest.approx(bicep_arm_link.MOTOR_PLATE_WIDTH_Y)
    assert bbox.size.X == pytest.approx(bicep_arm_link.ELBOW_CLEVIS_TOTAL_X)
    assert bicep_arm_link.MOTOR_PLATE_WIDTH_Y == pytest.approx(54.0)
    assert bicep_arm_link.MOTOR_PLATE_HEIGHT_Z == pytest.approx(54.0)
    assert (
        bicep_arm_link.MOTOR_PLATE_CENTER_X
        + bicep_arm_link.MOTOR_PLATE_X_THICKNESS / 2
        == pytest.approx(bicep_arm_link.MOTOR_PLATE_OUTER_X)
    )
    assert bicep_arm_link.MOTOR_FACE_X == pytest.approx(
        bicep_arm_link.MOTOR_PLATE_OUTER_X - bicep_arm_link.MOTOR_FACE_INSET_X
    )
    assert bicep_arm_link.MOTOR_SLOT_TRAVEL == pytest.approx(4.0)
    assert bicep_arm_link.M3_CLEARANCE < bicep_arm_link.MOTOR_COUNTERBORE_DIAMETER
    assert bicep_arm_link.MOTOR_COUNTERBORE_DIAMETER > bicep_arm_link.M3_COUNTERBORE
    assert bicep_arm_link.MOTOR_COUNTERBORE_SLOT_TRAVEL > bicep_arm_link.MOTOR_SLOT_TRAVEL
    assert bicep_arm_link.MOTOR_PLATE_BACK_X < bicep_arm_link.MOTOR_FACE_X
    assert bicep_arm_link.MOTOR_COUNTERBORE_FACE_X == pytest.approx(
        -bicep_arm_link.LINK_X_THICKNESS / 2
    )
    assert bicep_arm_link.MOTOR_COUNTERBORE_FACE_X < bicep_arm_link.MOTOR_PLATE_BACK_X
    assert bicep_arm_link.MOTOR_COUNTERBORE_DEPTH > bicep_arm_link.M3_COUNTERBORE_DEPTH
    assert (
        bicep_arm_link.MOTOR_COUNTERBORE_FACE_X + bicep_arm_link.MOTOR_COUNTERBORE_DEPTH
        > bicep_arm_link.MOTOR_PLATE_BACK_X
    )
    assert (
        bicep_arm_link.MOTOR_COUNTERBORE_FACE_X + bicep_arm_link.MOTOR_COUNTERBORE_DEPTH
        < bicep_arm_link.MOTOR_FACE_X
    )


def test_bicep_has_negative_x_pulley_side_clearance_planes() -> None:
    from models import bicep_arm_link, forearm_link
    from models.master_assembly import PULLEY_SIDE_CLEARANCE
    from models.transmission_components import BELT_WIDTH, PULLEY_TOTAL_HEIGHT

    elbow_stack_side_clearance = (
        bicep_arm_link.ELBOW_CLEVIS_GAP_X
        - forearm_link.BOTTOM_HUB_THICKNESS
        - PULLEY_TOTAL_HEIGHT
        - PULLEY_SIDE_CLEARANCE
    ) / 2
    elbow_pulley_x = (
        -bicep_arm_link.ELBOW_CLEVIS_GAP_X / 2
        + elbow_stack_side_clearance
        + PULLEY_TOTAL_HEIGHT / 2
    )
    belt_inner_face_x = elbow_pulley_x + BELT_WIDTH / 2
    belt_outer_face_x = elbow_pulley_x - BELT_WIDTH / 2

    shoulder_pulley_x = -(
        bicep_arm_link.LINK_X_THICKNESS / 2 + PULLEY_TOTAL_HEIGHT / 2 + PULLEY_SIDE_CLEARANCE
    )
    shoulder_inner_face_x = shoulder_pulley_x + PULLEY_TOTAL_HEIGHT / 2

    assert (
        bicep_arm_link.ELBOW_BELT_CHANNEL_FACE_X - belt_inner_face_x
        >= bicep_arm_link.PULLEY_CHANNEL_CLEARANCE_X
    )
    assert (
        belt_outer_face_x - bicep_arm_link.ELBOW_BELT_CHANNEL_OUTER_X
        >= bicep_arm_link.PULLEY_CHANNEL_CLEARANCE_X
    )
    assert (
        bicep_arm_link.ELBOW_BELT_CHANNEL_Y_AT_MOTOR
        - bicep_arm_link.ELBOW_BELT_CHANNEL_WIDTH_Y / 2
        > 0
    )
    assert bicep_arm_link.ELBOW_BELT_CHANNEL_WIDTH_Y < bicep_arm_link.ELBOW_BELT_CHANNEL_Y_AT_CLEVIS
    assert bicep_arm_link.ELBOW_BELT_CHANNEL_Z_MIN > bicep_arm_link.MOTOR_SHAFT_Z
    assert (
        bicep_arm_link.ELBOW_BELT_CHANNEL_Z_MAX
        > bicep_arm_link.TOP_PIVOT_Z - bicep_arm_link.ELBOW_CLEVIS_CLEARANCE_Z / 2
    )
    assert (
        bicep_arm_link.SHOULDER_PULLEY_FLAT_FACE_X - shoulder_inner_face_x
        >= bicep_arm_link.SHOULDER_PULLEY_EXTRA_CLEARANCE_X
    )


def test_elbow_clevis_sandwiches_forearm_hub_and_60t_pulley() -> None:
    from models import bicep_arm_link, forearm_link
    from models.master_assembly import PULLEY_SIDE_CLEARANCE, build_model
    from models.transmission_components import PULLEY_TOTAL_HEIGHT

    assembly = build_model()
    children = list(assembly.children)
    children_by_label = {child.label: child for child in children}

    elbow_driven = children_by_label["elbow_60T_HTD3M_16p15_4xM3_25BC"]
    forearm = children_by_label["forearm_link"]

    side_clearance = (
        bicep_arm_link.ELBOW_CLEVIS_GAP_X
        - forearm_link.BOTTOM_HUB_THICKNESS
        - PULLEY_TOTAL_HEIGHT
        - PULLEY_SIDE_CLEARANCE
    ) / 2
    expected_elbow_pulley_x = (
        -bicep_arm_link.ELBOW_CLEVIS_GAP_X / 2
        + side_clearance
        + PULLEY_TOTAL_HEIGHT / 2
    )
    expected_forearm_x = (
        expected_elbow_pulley_x
        + PULLEY_TOTAL_HEIGHT / 2
        + PULLEY_SIDE_CLEARANCE
        + forearm_link.BOTTOM_HUB_THICKNESS / 2
    )

    def center_x(part) -> float:
        bbox = part.bounding_box()
        return (bbox.min.X + bbox.max.X) / 2

    elbow_bbox = elbow_driven.bounding_box()
    assert side_clearance >= PULLEY_SIDE_CLEARANCE
    assert elbow_bbox.min.X > -bicep_arm_link.ELBOW_CLEVIS_GAP_X / 2
    assert elbow_bbox.max.X < bicep_arm_link.ELBOW_CLEVIS_GAP_X / 2
    assert center_x(elbow_driven) == pytest.approx(expected_elbow_pulley_x)
    assert center_x(forearm) == pytest.approx(expected_forearm_x)


def test_master_assembly_includes_all_joint_shafts() -> None:
    from models.master_assembly import build_model

    assembly = build_model()
    labels = {child.label for child in assembly.children}

    assert "base_azimuth_8mm_shaft" in labels
    assert "shoulder_pivot_8mm_shaft" in labels
    assert "shoulder_pivot_8mm_spacer" in labels
    assert "elbow_pivot_5mm_shaft" in labels
    assert "wrist_pivot_5mm_shaft" in labels


def test_shoulder_spacer_fills_azimuth_clevis_stack() -> None:
    from models import azimuth_turntable_shoulder_cleat, bicep_arm_link, joint_shafts
    from models.master_assembly import PULLEY_SIDE_CLEARANCE, build_model
    from models.transmission_components import PULLEY_TOTAL_HEIGHT

    assembly = build_model()
    children_by_label = {child.label: child for child in assembly.children}
    spacer = children_by_label["shoulder_pivot_8mm_spacer"]

    stack_width = (
        PULLEY_TOTAL_HEIGHT
        + bicep_arm_link.LINK_X_THICKNESS
        + joint_shafts.SHOULDER_PIVOT_SPACER_LENGTH
        + 4 * PULLEY_SIDE_CLEARANCE
    )

    assert stack_width == pytest.approx(azimuth_turntable_shoulder_cleat.CLEVIS_CLEAR_GAP)
    assert spacer.bounding_box().size.X == pytest.approx(joint_shafts.SHOULDER_PIVOT_SPACER_LENGTH)
    assert spacer.bounding_box().min.X == pytest.approx(
        bicep_arm_link.LINK_X_THICKNESS / 2 + PULLEY_SIDE_CLEARANCE
    )


def test_master_assembly_includes_single_wrist_motor() -> None:
    from models import bicep_arm_link, forearm_link
    from models.master_assembly import PULLEY_SIDE_CLEARANCE, build_model
    from models.transmission_components import PULLEY_TOTAL_HEIGHT

    assembly = build_model()
    children_by_label = {child.label: child for child in assembly.children}

    wrist_motor = children_by_label["wrist_28BYJ-48_stepper_motor"]

    wrist_bbox = wrist_motor.bounding_box()
    wrist_center_x = (wrist_bbox.min.X + wrist_bbox.max.X) / 2

    forearm_x = (
        -bicep_arm_link.ELBOW_CLEVIS_GAP_X / 2
        + (
            bicep_arm_link.ELBOW_CLEVIS_GAP_X
            - forearm_link.BOTTOM_HUB_THICKNESS
            - PULLEY_TOTAL_HEIGHT
            - PULLEY_SIDE_CLEARANCE
        )
        / 2
        + PULLEY_TOTAL_HEIGHT
        + PULLEY_SIDE_CLEARANCE
        + forearm_link.BOTTOM_HUB_THICKNESS / 2
    )

    assert wrist_center_x < forearm_x - forearm_link.LINK_THICKNESS_X / 2


def test_forearm_has_single_pulley_side_wrist_motor_mount() -> None:
    from models import forearm_link

    model = forearm_link.build_model()
    bbox = model.bounding_box()
    mount_face_center_x = forearm_link.WRIST_MOTOR_SIDE_SIGN * (
        forearm_link.LINK_THICKNESS_X / 2 + forearm_link.MOTOR_FACE_THICKNESS_X / 2
    )

    assert forearm_link.WRIST_MOTOR_SIDE_SIGN == -1
    assert mount_face_center_x < -forearm_link.LINK_THICKNESS_X / 2
    assert bbox.size.Y == pytest.approx(forearm_link.MOTOR_FACE_WIDTH_Y)
    assert forearm_link.MOTOR_MOUNT_BOTTOM_Z == pytest.approx(
        forearm_link.BOTTOM_HUB_RADIUS + forearm_link.MOTOR_MOUNT_ELBOW_END_CLEARANCE_Z
    )
    assert forearm_link.MOTOR_SHAFT_Z == pytest.approx(
        forearm_link.MOTOR_MOUNT_BOTTOM_Z + forearm_link.MOTOR_FACE_HEIGHT_Z / 2
    )
    assert forearm_link.TOP_WRIST_PIVOT_Z - forearm_link.MOTOR_SHAFT_Z == pytest.approx(
        forearm_link.WRIST_BELT_CENTER_DISTANCE
    )


def test_forearm_elbow_hub_has_pulley_side_m3_countersinks() -> None:
    from models import forearm_link

    assert forearm_link.ELBOW_BOLT_HEAD_SIDE_SIGN == -1
    assert forearm_link.ELBOW_M3_COUNTERSINK_DIAMETER > forearm_link.M3_CLEARANCE
    assert 0 < forearm_link.ELBOW_M3_COUNTERSINK_DEPTH < forearm_link.BOTTOM_HUB_THICKNESS / 2


def test_base_120t_gear_has_bottom_m3_countersinks_for_turntable() -> None:
    from models import azimuth_turntable_shoulder_cleat, transmission_components
    from models.common import BASE_GEAR_BOLT_CIRCLE, M3_CLEARANCE, circle_points

    gear = transmission_components.build_base_driven_gear()
    bbox = gear.bounding_box()

    assert bbox.size.Z == pytest.approx(transmission_components.GEAR_THICKNESS)
    assert transmission_components.BASE_GEAR_M3_COUNTERSINK_DIAMETER > M3_CLEARANCE
    assert (
        0
        < transmission_components.BASE_GEAR_M3_COUNTERSINK_DEPTH
        < transmission_components.GEAR_THICKNESS / 2
    )
    assert circle_points(
        6,
        BASE_GEAR_BOLT_CIRCLE,
        start_angle=transmission_components.BASE_GEAR_BOLT_START_ANGLE,
    ) == pytest.approx(circle_points(6, BASE_GEAR_BOLT_CIRCLE, start_angle=30.0))
    assert azimuth_turntable_shoulder_cleat.BASE_GEAR_BOLT_CIRCLE == pytest.approx(
        BASE_GEAR_BOLT_CIRCLE
    )


def test_master_assembly_excludes_electronics_and_wire_guides() -> None:
    from models.master_assembly import build_model

    assembly = build_model()
    labels = {child.label for child in assembly.children}

    assert "arduino_uno_r4_minima_tray" not in labels
    assert "base_nema17_driver_board_tray" not in labels
    assert "shoulder_nema17_driver_board_tray" not in labels
    assert "elbow_nema17_driver_board_tray" not in labels
    assert "wrist_28byj_uln2003_board_tray" not in labels
    assert "base_cable_entry_strain_relief_guide" not in labels
    assert "base_azimuth_service_loop_guard" not in labels
    assert "shoulder_service_loop_anchor" not in labels
    assert "elbow_service_loop_anchor" not in labels
    assert "wrist_service_loop_anchor" not in labels
    assert "bicep_harness_channel_marker" not in labels
    assert "forearm_harness_channel_marker" not in labels


def test_motor_shafts_clear_lower_pulley_envelopes() -> None:
    from models import bicep_arm_link, forearm_link
    from models.transmission_components import HTD_3M_PITCH

    shoulder_80t_flange_radius = 80 * HTD_3M_PITCH / (2 * pi) + 2.35
    elbow_60t_flange_radius = 60 * HTD_3M_PITCH / (2 * pi) + 2.35

    assert bicep_arm_link.MOTOR_SHAFT_Z - shoulder_80t_flange_radius >= 5.0
    assert forearm_link.MOTOR_SHAFT_Z - elbow_60t_flange_radius >= 5.0
