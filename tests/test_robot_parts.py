import importlib
from math import pi

import pytest


PART_MODULES = [
    "models.geared_base_stator",
    "models.azimuth_turntable_shoulder_cleat",
    "models.bicep_arm_link",
    "models.bicep_belt_cover",
    "models.forearm_link",
    "models.electronics_mounts",
    "models.wire_management",
    "models.joint_shafts",
    "models.sg90_gripper_base",
    "models.sg90_parallel_gripper",
    "models.byj48_stepper_motor",
    "models.nema17_stepper_motor",
    "models.transmission_components",
    "models.belt_base_candidate",
    "models.safety_guards",
    "models.electronics_enclosure",
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

    assert len(assembly.children) == 67
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
    wrist_driver = children_by_label["wrist_driver_20T_HTD3M_5mm_double_D_shaft"]
    wrist_adapter = children_by_label["wrist_keyed_28byj_shaft_to_pulley_adapter"]
    wrist_driven = children_by_label["wrist_32T_HTD3M_16p15_4xM3_20BC"]
    wrist_belt = children_by_label["wrist_20T_to_32T_HTD3M_open_belt_visual"]
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


def test_bicep_belt_cover_is_open_backed_and_has_two_snap_pairs() -> None:
    from models import bicep_belt_cover

    cover = bicep_belt_cover.build_model()
    bbox = cover.bounding_box()

    assert cover.label == "bicep_elbow_belt_snap_cover"
    assert bbox.min.Z == pytest.approx(bicep_belt_cover.COVER_BOTTOM_Z)
    assert bbox.max.Z == pytest.approx(bicep_belt_cover.COVER_TOP_Z)
    # Smooth lofting may bow a few tenths beyond the nominal section width.
    assert bbox.size.Y == pytest.approx(bicep_belt_cover.UPPER_OUTER_WIDTH_Y, abs=0.5)
    assert bicep_belt_cover.COVER_FRONT_X_UPPER < bicep_belt_cover.COVER_FRONT_X_LOWER
    assert bicep_belt_cover.COVER_REAR_X_UPPER < bicep_belt_cover.COVER_REAR_X_LOWER
    assert bicep_belt_cover.SNAP_HOOK_PROJECTION_X > bicep_belt_cover.SNAP_FIT_CLEARANCE
    assert bicep_belt_cover.SNAP_ARM_THICKNESS_X < bicep_belt_cover.WALL_THICKNESS


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
    local_forearm_bbox = forearm_link.build_model().bounding_box()
    local_forearm_center_x = (local_forearm_bbox.min.X + local_forearm_bbox.max.X) / 2
    assert side_clearance >= PULLEY_SIDE_CLEARANCE
    assert elbow_bbox.min.X > -bicep_arm_link.ELBOW_CLEVIS_GAP_X / 2
    assert elbow_bbox.max.X < bicep_arm_link.ELBOW_CLEVIS_GAP_X / 2
    assert center_x(elbow_driven) == pytest.approx(expected_elbow_pulley_x)
    assert center_x(forearm) == pytest.approx(expected_forearm_x + local_forearm_center_x)


def test_master_assembly_includes_all_joint_shafts() -> None:
    from models.master_assembly import build_model

    assembly = build_model()
    labels = {child.label for child in assembly.children}

    assert "base_azimuth_8mm_shaft" in labels
    assert "shoulder_pivot_8mm_shaft" in labels
    assert "shoulder_pivot_8mm_spacer" in labels
    assert "elbow_pivot_5mm_shaft" in labels
    assert "wrist_pivot_5mm_shaft" in labels


def test_master_assembly_shows_installed_joint_hardware_and_flush_shafts() -> None:
    from models import joint_shafts
    from models.master_assembly import build_model

    assembly = build_model()
    labels = [child.label for child in assembly.children]

    assert len([label for label in labels if label.startswith("installed_bearing_")]) == 10
    assert len([label for label in labels if label.startswith("installed_sg90_")]) == 2
    assert len([label for label in labels if label.startswith("installed_M3_fastener_")]) == 24
    assert joint_shafts.SHOULDER_SHAFT_LENGTH == pytest.approx(67.0)
    assert joint_shafts.ELBOW_SHAFT_LENGTH == pytest.approx(44.0)
    assert joint_shafts.WRIST_SHAFT_LENGTH == pytest.approx(41.0)


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
    assert forearm_link.LINK_HALF_WIDTH_Y == pytest.approx(forearm_link.MOTOR_FACE_WIDTH_Y / 2)
    assert forearm_link.MOTOR_SLOT_TRAVEL == pytest.approx(6.0)
    assert forearm_link.MOTOR_MOUNT_BOTTOM_Z == pytest.approx(
        forearm_link.BOTTOM_HUB_RADIUS + forearm_link.MOTOR_MOUNT_ELBOW_END_CLEARANCE_Z
    )
    assert forearm_link.MOTOR_SHAFT_Z == pytest.approx(
        forearm_link.MOTOR_MOUNT_BOTTOM_Z + forearm_link.MOTOR_FACE_HEIGHT_Z / 2
    )
    assert forearm_link.TOP_WRIST_PIVOT_Z - forearm_link.MOTOR_SHAFT_Z == pytest.approx(
        forearm_link.WRIST_BELT_CENTER_DISTANCE
    )
    assert forearm_link.WRIST_BELT_CHANNEL_OUTER_X < -forearm_link.LINK_THICKNESS_X / 2
    assert (
        forearm_link.WRIST_BELT_CHANNEL_OUTER_X + forearm_link.WRIST_BELT_CHANNEL_DEPTH_X
        < forearm_link.LINK_THICKNESS_X / 2
    )

    mount_face_center_x = forearm_link.WRIST_ASSEMBLY_OFFSET_X + mount_face_center_x
    upper_hole_y = forearm_link.BYJ48_EAR_SPACING / 2
    hole_edge_y = upper_hole_y + forearm_link.BYJ48_MOUNT_HOLE / 2 - 0.05
    assert not model.is_inside(
        (mount_face_center_x, hole_edge_y, forearm_link.MOTOR_SHAFT_Z),
        tolerance=1e-6,
    )


def test_forearm_wrist_drive_fits_htd_342_3m_belt() -> None:
    from models import forearm_link
    from models.common import (
        HTD_342_3M_PITCH_LENGTH,
        WRIST_DRIVER_TEETH,
        WRIST_DRIVEN_TEETH,
        open_belt_pitch_length,
    )

    nominal_pitch_length = open_belt_pitch_length(
        WRIST_DRIVER_TEETH,
        WRIST_DRIVEN_TEETH,
        forearm_link.WRIST_BELT_CENTER_DISTANCE,
    )
    half_slot_travel = forearm_link.MOTOR_SLOT_TRAVEL / 2
    slack_end_pitch_length = open_belt_pitch_length(
        WRIST_DRIVER_TEETH,
        WRIST_DRIVEN_TEETH,
        forearm_link.WRIST_BELT_CENTER_DISTANCE - half_slot_travel,
    )
    tension_end_pitch_length = open_belt_pitch_length(
        WRIST_DRIVER_TEETH,
        WRIST_DRIVEN_TEETH,
        forearm_link.WRIST_BELT_CENTER_DISTANCE + half_slot_travel,
    )

    assert nominal_pitch_length == pytest.approx(HTD_342_3M_PITCH_LENGTH)
    assert forearm_link.MOTOR_SLOT_TRAVEL == pytest.approx(6.0)
    assert slack_end_pitch_length < HTD_342_3M_PITCH_LENGTH
    assert tension_end_pitch_length > HTD_342_3M_PITCH_LENGTH


def test_wrist_belt_runs_outside_connected_bicep_style_clevis() -> None:
    from build123d import Pos, Rot
    from models import forearm_link
    from models.transmission_components import (
        HTD_BELT_VISUAL_THICKNESS,
        HTD_BELT_VISUAL_TOOTH_HEIGHT,
        build_wrist_htd_belt,
    )

    forearm = forearm_link.build_model()
    belt = build_wrist_htd_belt().moved(
        Pos(
            forearm_link.WRIST_BELT_CHANNEL_CENTER_X,
            0,
            forearm_link.MOTOR_SHAFT_Z,
        )
        * Rot(0, 90, 90)
    )

    assert all(forearm.intersect(solid) is None for solid in belt.solids())
    connected_web_z = (
        forearm_link.TOP_WRIST_PIVOT_Z
        - forearm_link.WRIST_CLEVIS_CLEARANCE_Z / 2
        - 5.0
    )
    assert len(forearm.solids()) == 1
    assert forearm.is_inside(
        (forearm_link.WRIST_BELT_CHANNEL_CENTER_X, 0, connected_web_z),
        tolerance=1e-6,
    )
    assert forearm.is_inside(
        (
            forearm_link.WRIST_OFFSET_EAR_OUTER_X + 4.0,
            0,
            forearm_link.WRIST_OFFSET_EAR_GUSSET_FULL_Z - 3.0,
        ),
        tolerance=1e-6,
    )
    assert forearm.is_inside(
        (
            forearm_link.WRIST_OFFSET_EAR_OUTER_X
            + forearm_link.CLEVIS_EAR_THICKNESS_X / 2,
            10.0,
            forearm_link.WRIST_CLEVIS_CLEARANCE_BOTTOM_Z + 1.0,
        ),
        tolerance=1e-6,
    )
    driven_pitch_radius = (
        forearm_link.WRIST_DRIVEN_TEETH * forearm_link.HTD_3M_PITCH / (2 * pi)
    )
    belt_inner_radius = (
        driven_pitch_radius
        - HTD_BELT_VISUAL_THICKNESS / 2
        - HTD_BELT_VISUAL_TOOTH_HEIGHT
    )
    assert belt_inner_radius > forearm_link.CLEVIS_WIDTH_Y / 2


def test_28byj_motor_and_uln_carrier_hole_patterns_match_reference_dimensions() -> None:
    from models import electronics_mounts
    from models.common import BYJ48_EAR_SPACING

    uln_x = [point[0] for point in electronics_mounts.ULN2003_HOLE_POINTS]
    uln_y = [point[1] for point in electronics_mounts.ULN2003_HOLE_POINTS]

    assert BYJ48_EAR_SPACING == pytest.approx(35.0)
    assert max(uln_x) - min(uln_x) == pytest.approx(29.5)
    assert max(uln_y) - min(uln_y) == pytest.approx(27.0)


def test_electronics_carriers_are_low_profile_with_external_attachment_ears() -> None:
    from models import electronics_mounts

    trays = (
        electronics_mounts.build_arduino_uno_r4_minima_tray(),
        electronics_mounts.build_nema17_driver_board_tray(),
        electronics_mounts.build_28byj_uln_board_tray(),
    )

    assert electronics_mounts.BASE_THICKNESS == pytest.approx(2.0)
    assert electronics_mounts.STANDOFF_HEIGHT == pytest.approx(2.0)
    assert all(tray.bounding_box().size.Z <= 4.0 for tray in trays)
    assert electronics_mounts.build_nema17_driver_board_tray().bounding_box().size.Y > (
        electronics_mounts.STEPSTICK_BOARD_Y + 2 * electronics_mounts.BOARD_CLEARANCE
    )


def test_forearm_elbow_hub_has_flush_pulley_side_m3_counterbores() -> None:
    from models import forearm_link
    from models.common import M3_COUNTERBORE_DEPTH

    assert forearm_link.ELBOW_BOLT_HEAD_SIDE_SIGN == -1
    assert forearm_link.ELBOW_M3_COUNTERBORE_DIAMETER > forearm_link.M3_CLEARANCE
    assert forearm_link.ELBOW_M3_COUNTERBORE_DEPTH == pytest.approx(M3_COUNTERBORE_DEPTH)
    assert forearm_link.ELBOW_M3_COUNTERBORE_DEPTH < forearm_link.BOTTOM_HUB_THICKNESS / 2


def test_elbow_pulley_uses_tight_m3_thread_pilots() -> None:
    from models import transmission_components
    from models.common import M3_TAP_HOLE

    assert 0 < transmission_components.ELBOW_PULLEY_M3_THREAD_PILOT < M3_TAP_HOLE


def test_forearm_wrist_clevis_clears_gripper_base_pivot_boss() -> None:
    from models import forearm_link, sg90_gripper_base

    model = forearm_link.build_model()
    bbox = model.bounding_box()

    assert forearm_link.CLEVIS_GAP_X == pytest.approx(29.0)
    assert forearm_link.WRIST_ASSEMBLY_OFFSET_X == pytest.approx(-13.875)
    assert forearm_link.WRIST_CLEVIS_GAP_CENTER_X == pytest.approx(-11.875)
    assert forearm_link.CLEVIS_GAP_X > sg90_gripper_base.CLEVIS_TONGUE_WIDTH
    assert sg90_gripper_base.DECK_ROOT_WIDTH < forearm_link.CLEVIS_GAP_X
    assert sg90_gripper_base.DECK_FLARE_FULL_Y > (
        sg90_gripper_base.WRIST_JOINT_ROTATION_CLEARANCE_RADIUS
    )
    assert forearm_link.WRIST_CLEVIS_CLEARANCE_Z > 2 * (
        sg90_gripper_base.WRIST_JOINT_ROTATION_CLEARANCE_RADIUS
        + sg90_gripper_base.PLATE_THICKNESS / 2
    )
    assert forearm_link.WRIST_HULL_WIDTH_Y > forearm_link.CLEVIS_WIDTH_Y
    assert forearm_link.WRIST_HULL_TRANSITION_START_Z < (
        forearm_link.TOP_WRIST_PIVOT_Z - forearm_link.CLEVIS_HEIGHT_Z / 2
    )
    assert bbox.max.Z - forearm_link.TOP_WRIST_PIVOT_Z == pytest.approx(
        forearm_link.CLEVIS_WIDTH_Y / 2
    )


def test_master_wrist_joint_stacks_pulley_and_gripper_with_clearance() -> None:
    from models import bicep_arm_link, forearm_link, sg90_gripper_base
    from models.master_assembly import PULLEY_SIDE_CLEARANCE, WRIST_STACK_CLEARANCE, build_model
    from models.transmission_components import PULLEY_TOTAL_HEIGHT

    assembly = build_model()
    children_by_label = {child.label: child for child in assembly.children}
    wrist_pulley = children_by_label["wrist_32T_HTD3M_16p15_4xM3_20BC"]
    gripper = children_by_label["sg90_parallel_gripper"]

    side_clearance = (
        bicep_arm_link.ELBOW_CLEVIS_GAP_X
        - forearm_link.BOTTOM_HUB_THICKNESS
        - PULLEY_TOTAL_HEIGHT
        - PULLEY_SIDE_CLEARANCE
    ) / 2
    elbow_pulley_x = (
        -bicep_arm_link.ELBOW_CLEVIS_GAP_X / 2
        + side_clearance
        + PULLEY_TOTAL_HEIGHT / 2
    )
    forearm_x = (
        elbow_pulley_x
        + PULLEY_TOTAL_HEIGHT / 2
        + PULLEY_SIDE_CLEARANCE
        + forearm_link.BOTTOM_HUB_THICKNESS / 2
    )
    wrist_pulley_x = forearm_x + forearm_link.WRIST_ASSEMBLY_OFFSET_X - (
        forearm_link.LINK_THICKNESS_X / 2
        + forearm_link.MOTOR_FACE_THICKNESS_X
        - PULLEY_TOTAL_HEIGHT / 2
    )
    expected_gripper_x = (
        wrist_pulley_x
        + PULLEY_TOTAL_HEIGHT / 2
        + WRIST_STACK_CLEARANCE
        + sg90_gripper_base.CLEVIS_TONGUE_WIDTH / 2
    )

    wrist_pulley_bbox = wrist_pulley.bounding_box()
    gripper_bbox = gripper.bounding_box()
    wrist_clevis_min_x = (
        forearm_x
        + forearm_link.WRIST_CLEVIS_GAP_CENTER_X
        - forearm_link.CLEVIS_GAP_X / 2
    )
    wrist_clevis_max_x = (
        forearm_x
        + forearm_link.WRIST_CLEVIS_GAP_CENTER_X
        + forearm_link.CLEVIS_GAP_X / 2
    )
    gripper_tongue_min_x = expected_gripper_x - sg90_gripper_base.CLEVIS_TONGUE_WIDTH / 2
    gripper_tongue_max_x = expected_gripper_x + sg90_gripper_base.CLEVIS_TONGUE_WIDTH / 2
    pulley_to_gripper_clearance = gripper_tongue_min_x - wrist_pulley_bbox.max.X
    pulley_side_clearance = wrist_pulley_bbox.min.X - wrist_clevis_min_x
    gripper_side_clearance = wrist_clevis_max_x - gripper_tongue_max_x

    assert pulley_to_gripper_clearance == pytest.approx(WRIST_STACK_CLEARANCE)
    assert 1.0 <= pulley_side_clearance <= 2.0
    assert 1.0 <= gripper_side_clearance <= 2.0
    assert (gripper_bbox.min.X + gripper_bbox.max.X) / 2 == pytest.approx(expected_gripper_x)
    assert expected_gripper_x == pytest.approx(0.0)


def test_sg90_parallel_gripper_has_mirrored_printable_linkage() -> None:
    from models import sg90_gripper_base, sg90_parallel_gripper
    from models.common import M3_CLEARANCE, M3_TAP_HOLE

    gripper = sg90_parallel_gripper.build_model()
    labels = {child.label for child in gripper.children}
    bbox = gripper.bounding_box()

    assert "sg90_gripper_base" in labels
    assert "left_sg90_gripper_jaw" in labels
    assert "right_sg90_gripper_jaw" in labels
    assert "left_sg90_servo_horn_adapter" in labels
    assert "right_sg90_servo_horn_adapter" in labels
    assert "left_sg90_gripper_pushrod" in labels
    assert "right_sg90_gripper_pushrod" in labels
    assert sg90_parallel_gripper.JAW_TIP_GAP == pytest.approx(13.0)
    assert sg90_parallel_gripper.JAW_PIVOT_CLEARANCE > sg90_gripper_base.GRIPPER_POST_DIAMETER
    assert sg90_parallel_gripper.JAW_RETAINING_SCREW_PILOT == pytest.approx(M3_TAP_HOLE)
    assert sg90_parallel_gripper.LINK_WIDTH > M3_CLEARANCE
    assert bbox.size.X <= sg90_gripper_base.OVERALL_WIDTH
    assert bbox.size.Y > sg90_gripper_base.OVERALL_LENGTH
    assert bbox.size.Z < 45.0


def test_sg90_parallel_gripper_print_plate_excludes_base() -> None:
    from models import sg90_parallel_gripper

    plate = sg90_parallel_gripper.build_printable_model()
    labels = {child.label for child in plate.children}

    assert "sg90_gripper_base" not in labels
    assert labels == {
        "left_sg90_gripper_jaw",
        "right_sg90_gripper_jaw",
        "left_sg90_servo_horn_adapter",
        "right_sg90_servo_horn_adapter",
        "left_sg90_gripper_pushrod",
        "right_sg90_gripper_pushrod",
    }
    assert all(child.bounding_box().min.Z == pytest.approx(0.0) for child in plate.children)
    boxes = [child.bounding_box() for child in plate.children]
    for index, first in enumerate(boxes):
        for second in boxes[index + 1 :]:
            x_gap = max(first.min.X - second.max.X, second.min.X - first.max.X)
            y_gap = max(first.min.Y - second.max.Y, second.min.Y - first.max.Y)
            assert max(x_gap, y_gap) >= sg90_parallel_gripper.PRINT_PART_CLEARANCE


def test_forearm_wrist_belt_has_installation_relief() -> None:
    from models import forearm_link

    assert forearm_link.WRIST_BELT_PULLEY_RELIEF_MARGIN >= 3.0
    assert forearm_link.WRIST_BELT_CHANNEL_DEPTH_X > forearm_link.WRIST_BELT_WIDTH
    assert forearm_link.WRIST_BELT_CHANNEL_OUTER_X < -forearm_link.LINK_THICKNESS_X / 2
    assert forearm_link.WRIST_PULLEY_RELIEF_DEPTH_X > forearm_link.WRIST_PULLEY_TOTAL_HEIGHT
    assert forearm_link.WRIST_PULLEY_RELIEF_CENTER_X == pytest.approx(
        forearm_link.WRIST_BELT_CHANNEL_CENTER_X
    )
    assert forearm_link.WRIST_BELT_CHANNEL_SLOT_WIDTH_YZ <= 5.0


def test_wrist_pulley_has_m3_counterbores_for_gripper_base() -> None:
    from models import transmission_components
    from models.common import M3_CLEARANCE

    pulley = transmission_components.build_wrist_pulley()
    bbox = pulley.bounding_box()

    assert bbox.size.Z == pytest.approx(transmission_components.PULLEY_TOTAL_HEIGHT)
    assert transmission_components.WRIST_PULLEY_M3_COUNTERBORE_DIAMETER > M3_CLEARANCE
    assert 0 < transmission_components.WRIST_PULLEY_M3_COUNTERBORE_DEPTH < (
        transmission_components.PULLEY_TOTAL_HEIGHT / 2
    )


def test_wrist_driver_and_motor_use_matching_double_d_shaft() -> None:
    from models import byj48_stepper_motor, transmission_components
    from models.common import BYJ48_SHAFT_ACROSS_FLATS, BYJ48_SHAFT_DIAMETER

    pulley = transmission_components.build_wrist_driver_pulley()
    motor = byj48_stepper_motor.build_model()
    just_beyond_flat = BYJ48_SHAFT_ACROSS_FLATS / 2 + 0.1
    near_round_edge = BYJ48_SHAFT_DIAMETER / 2 - 0.1

    assert not pulley.is_inside((0, 0, 0), tolerance=1e-6)
    assert pulley.is_inside((just_beyond_flat, 0, 0), tolerance=1e-6)
    assert pulley.is_inside((-just_beyond_flat, 0, 0), tolerance=1e-6)
    assert not pulley.is_inside((0, near_round_edge, 0), tolerance=1e-6)

    shaft_z = byj48_stepper_motor.SHAFT_LENGTH / 2
    assert not motor.is_inside(
        (just_beyond_flat, 0, shaft_z),
        tolerance=1e-6,
    )
    assert not motor.is_inside(
        (-just_beyond_flat, 0, shaft_z),
        tolerance=1e-6,
    )
    assert motor.is_inside((0, near_round_edge, shaft_z), tolerance=1e-6)


def test_base_120t_gear_has_bottom_m3_counterbores_for_turntable() -> None:
    from models import azimuth_turntable_shoulder_cleat, geared_base_stator, transmission_components
    from models.common import BASE_GEAR_BOLT_CIRCLE, M3_CLEARANCE, M3_TAP_HOLE, circle_points

    gear = transmission_components.build_base_driven_gear()
    bbox = gear.bounding_box()

    assert bbox.size.Z == pytest.approx(transmission_components.GEAR_THICKNESS)
    assert transmission_components.BASE_GEAR_CENTER_BORE > geared_base_stator.BEARING_BOSS_OD
    assert transmission_components.BASE_GEAR_CENTER_BORE < (
        BASE_GEAR_BOLT_CIRCLE - 2 * M3_CLEARANCE
    )
    assert transmission_components.BASE_GEAR_M3_COUNTERBORE_DIAMETER > M3_CLEARANCE
    assert (
        0
        < transmission_components.BASE_GEAR_M3_COUNTERBORE_DEPTH
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
    assert azimuth_turntable_shoulder_cleat.BASE_GEAR_THREAD_PILOT == pytest.approx(M3_TAP_HOLE)
    assert azimuth_turntable_shoulder_cleat.BASE_GEAR_THREAD_PILOT < M3_CLEARANCE
    assert (
        azimuth_turntable_shoulder_cleat.BASE_GEAR_THREAD_DEPTH
        < azimuth_turntable_shoulder_cleat.PLATE_THICKNESS
    )


def test_azimuth_turntable_uses_separate_center_shaft() -> None:
    from models import azimuth_turntable_shoulder_cleat, geared_base_stator
    from models.common import BEARING_608_ID

    turntable = azimuth_turntable_shoulder_cleat.build_model()
    bbox = turntable.bounding_box()

    assert bbox.min.Z == pytest.approx(0.0)
    assert azimuth_turntable_shoulder_cleat.CENTER_SHAFT_CLEARANCE > BEARING_608_ID
    assert azimuth_turntable_shoulder_cleat.CENTER_SHAFT_CLEARANCE == pytest.approx(8.5)
    assert (
        azimuth_turntable_shoulder_cleat.STATOR_BOSS_RELIEF_DIAMETER
        > geared_base_stator.BEARING_BOSS_OD
    )
    assert azimuth_turntable_shoulder_cleat.STATOR_BOSS_RELIEF_DEPTH == pytest.approx(7.0)
    assert (
        azimuth_turntable_shoulder_cleat.STATOR_BOSS_RELIEF_DEPTH
        < azimuth_turntable_shoulder_cleat.PLATE_THICKNESS
    )


def test_master_assembly_localizes_motor_drivers_and_excludes_loose_wire_guides() -> None:
    from models.master_assembly import build_model

    assembly = build_model()
    children_by_label = {child.label: child for child in assembly.children}
    labels = set(children_by_label)

    assert "arduino_uno_r4_minima_tray" not in labels
    assert "base_nema17_driver_board_tray" in labels
    assert "shoulder_nema17_driver_board_tray" in labels
    assert "elbow_nema17_driver_board_tray" in labels
    assert "wrist_28byj_uln2003_board_tray" in labels

    motor_driver_pairs = (
        ("base_nema17_stepper_motor", "base_nema17_driver_board_tray"),
        ("shoulder_nema17_stepper_motor", "shoulder_nema17_driver_board_tray"),
        ("elbow_nema17_stepper_motor", "elbow_nema17_driver_board_tray"),
        ("wrist_28BYJ-48_stepper_motor", "wrist_28byj_uln2003_board_tray"),
    )
    for motor_label, driver_label in motor_driver_pairs:
        motor_box = children_by_label[motor_label].bounding_box()
        driver_box = children_by_label[driver_label].bounding_box()
        x_gap = max(motor_box.min.X - driver_box.max.X, driver_box.min.X - motor_box.max.X, 0.0)
        y_gap = max(motor_box.min.Y - driver_box.max.Y, driver_box.min.Y - motor_box.max.Y, 0.0)
        z_gap = max(motor_box.min.Z - driver_box.max.Z, driver_box.min.Z - motor_box.max.Z, 0.0)
        assert (x_gap * x_gap + y_gap * y_gap + z_gap * z_gap) ** 0.5 <= 12.0

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
