from __future__ import annotations

from build123d import Align, Compound, Cylinder, Location, Pos, Rot

try:
    from models.common import (
        BASE_GEAR_BOLT_CIRCLE,
        BYJ48_EAR_SPACING,
        ELBOW_PULLEY_BOLT_CIRCLE,
        NEMA17_HOLE_SPACING,
        SHOULDER_PULLEY_BOLT_CIRCLE,
        WRIST_PULLEY_BOLT_CIRCLE,
        circle_points,
        export_model,
    )
except ModuleNotFoundError:
    from common import (
        BASE_GEAR_BOLT_CIRCLE,
        BYJ48_EAR_SPACING,
        ELBOW_PULLEY_BOLT_CIRCLE,
        NEMA17_HOLE_SPACING,
        SHOULDER_PULLEY_BOLT_CIRCLE,
        WRIST_PULLEY_BOLT_CIRCLE,
        circle_points,
        export_model,
    )


AZIMUTH_TURNTABLE_Z = 28.0
PULLEY_SIDE_CLEARANCE = 0.75
WRIST_STACK_CLEARANCE = 1.0
M3_SCREW_LENGTHS = (6.0, 8.0, 10.0, 12.0, 14.0, 16.0, 18.0, 20.0, 25.0, 30.0, 40.0)
NEMA17_THREAD_DEPTH = 4.5


def nema17_mount_screw_placements(
    motor_location: Location, mount, hole_spacing: float
) -> list[tuple[float, Location]]:
    """Size and place the four M3 screws that clamp a NEMA17 through its printed mount.

    Each hole is probed with an annulus just outside the clearance hole, so the
    bolt head lands on the plate face, counterbore floor, or flush recess the
    printed part actually provides.
    """
    probe_length = 40.0
    half = hole_spacing / 2
    placements = []
    for x in (-half, half):
        for y in (-half, half):
            local = Location((x, y, 0))
            probe = Cylinder(2.6, probe_length, align=(Align.CENTER, Align.CENTER, Align.MIN))
            probe -= Cylinder(1.9, probe_length, align=(Align.CENTER, Align.CENTER, Align.MIN))
            contact = mount & probe.moved(motor_location * local)
            if contact.volume <= 0:
                raise ValueError("NEMA17 mount screw probe found no printed material.")
            seat = contact.moved(motor_location.inverse()).bounding_box().max.Z
            length = max(length for length in M3_SCREW_LENGTHS if length <= seat + NEMA17_THREAD_DEPTH)
            # The screw model's head is on local -Z; flip it so the head sits on the seat.
            placements.append(
                (length, motor_location * Location((x, y, seat - length / 2)) * Rot(180, 0, 0))
            )
    return placements


def build_model(configuration: str = "mechanical") -> Compound:
    if configuration not in {"mechanical", "service"}:
        raise ValueError("configuration must be mechanical or service")
    try:
        from models import azimuth_turntable_shoulder_cleat as turntable_model
        from models import bicep_arm_link as bicep_model
        from models import forearm_link as forearm_model
        from models import geared_base_stator as stator_model
        from models.joint_shafts import (
            SHOULDER_PIVOT_SPACER_LENGTH,
            build_base_azimuth_shaft,
            build_elbow_pivot_shaft,
            build_shoulder_pivot_spacer,
            build_shoulder_pivot_shaft,
            build_wrist_pivot_shaft,
        )
        from models.geared_base_stator import build_model as build_stator
        from models.hardware import (
            build_608_bearing,
            build_625_bearing,
            build_m3_socket_screw,
            build_sg90_installed,
        )
        from models.byj48_stepper_motor import MOUNT_PLATE_THICKNESS, build_installed as build_byj48
        from models.nema17_stepper_motor import build_installed as build_nema17
        from models.electronics_mounts import (
            build_28byj_uln_board_tray,
            build_nema17_driver_board_tray,
        )
        from models import sg90_gripper_base as gripper_base_model
        from models import sg90_parallel_gripper as gripper_model
        from models.sg90_parallel_gripper import build_model as build_gripper
        from models.transmission_components import (
            PULLEY_TOTAL_HEIGHT,
            WRIST_PULLEY_M3_COUNTERBORE_DEPTH,
            build_base_driven_gear,
            build_base_driver_pinion,
            build_elbow_htd_belt,
            build_elbow_driver_pulley,
            build_elbow_pulley,
            build_shoulder_htd_belt,
            build_shoulder_driver_pulley,
            build_shoulder_pulley,
            build_wrist_driver_pulley,
            build_wrist_htd_belt,
            build_wrist_pulley,
            BASE_GEAR_BOLT_START_ANGLE,
        )
        from models.wire_management import (
            build_base_azimuth_service_loop_guard,
            build_base_cable_entry_strain_relief_guide,
        )
    except ModuleNotFoundError:
        import azimuth_turntable_shoulder_cleat as turntable_model
        import bicep_arm_link as bicep_model
        import forearm_link as forearm_model
        import geared_base_stator as stator_model
        from joint_shafts import (
            SHOULDER_PIVOT_SPACER_LENGTH,
            build_base_azimuth_shaft,
            build_elbow_pivot_shaft,
            build_shoulder_pivot_spacer,
            build_shoulder_pivot_shaft,
            build_wrist_pivot_shaft,
        )
        from geared_base_stator import build_model as build_stator
        from hardware import (
            build_608_bearing,
            build_625_bearing,
            build_m3_socket_screw,
            build_sg90_installed,
        )
        from byj48_stepper_motor import MOUNT_PLATE_THICKNESS, build_installed as build_byj48
        from nema17_stepper_motor import build_installed as build_nema17
        from electronics_mounts import (
            build_28byj_uln_board_tray,
            build_nema17_driver_board_tray,
        )
        import sg90_gripper_base as gripper_base_model
        import sg90_parallel_gripper as gripper_model
        from sg90_parallel_gripper import build_model as build_gripper
        from transmission_components import (
            PULLEY_TOTAL_HEIGHT,
            WRIST_PULLEY_M3_COUNTERBORE_DEPTH,
            build_base_driven_gear,
            build_base_driver_pinion,
            build_elbow_htd_belt,
            build_elbow_driver_pulley,
            build_elbow_pulley,
            build_shoulder_htd_belt,
            build_shoulder_driver_pulley,
            build_shoulder_pulley,
            build_wrist_driver_pulley,
            build_wrist_htd_belt,
            build_wrist_pulley,
            BASE_GEAR_BOLT_START_ANGLE,
        )
        from wire_management import (
            build_base_azimuth_service_loop_guard,
            build_base_cable_entry_strain_relief_guide,
        )

    shoulder_pivot_z = AZIMUTH_TURNTABLE_Z + turntable_model.PIVOT_Z
    elbow_pivot_z = shoulder_pivot_z + bicep_model.TOP_PIVOT_Z
    wrist_pivot_z = elbow_pivot_z + forearm_model.TOP_WRIST_PIVOT_Z

    shoulder_pulley_x = -(
        bicep_model.LINK_X_THICKNESS / 2
        + PULLEY_TOTAL_HEIGHT / 2
        + PULLEY_SIDE_CLEARANCE
    )
    shoulder_stack_width = (
        PULLEY_TOTAL_HEIGHT
        + bicep_model.LINK_X_THICKNESS
        + SHOULDER_PIVOT_SPACER_LENGTH
        + 4 * PULLEY_SIDE_CLEARANCE
    )
    if abs(shoulder_stack_width - turntable_model.CLEVIS_CLEAR_GAP) > 1e-9:
        raise ValueError(
            "Shoulder pulley, link, spacer, and side clearances must fill the azimuth clevis gap."
        )
    shoulder_spacer_x = (
        bicep_model.LINK_X_THICKNESS / 2
        + PULLEY_SIDE_CLEARANCE
        + SHOULDER_PIVOT_SPACER_LENGTH / 2
    )
    elbow_stack_side_clearance = (
        bicep_model.ELBOW_CLEVIS_GAP_X
        - forearm_model.BOTTOM_HUB_THICKNESS
        - PULLEY_TOTAL_HEIGHT
        - PULLEY_SIDE_CLEARANCE
    ) / 2
    if elbow_stack_side_clearance < PULLEY_SIDE_CLEARANCE:
        raise ValueError(
            "Elbow clevis gap must fit the forearm hub, 60T pulley, and side clearances."
        )
    elbow_pulley_x = (
        -bicep_model.ELBOW_CLEVIS_GAP_X / 2
        + elbow_stack_side_clearance
        + PULLEY_TOTAL_HEIGHT / 2
    )
    forearm_x = (
        elbow_pulley_x
        + PULLEY_TOTAL_HEIGHT / 2
        + PULLEY_SIDE_CLEARANCE
        + forearm_model.BOTTOM_HUB_THICKNESS / 2
    )
    wrist_pulley_x = (
        forearm_x
        + forearm_model.WRIST_ASSEMBLY_OFFSET_X
        - (
            forearm_model.LINK_THICKNESS_X / 2
            + forearm_model.MOTOR_FACE_THICKNESS_X
            - PULLEY_TOTAL_HEIGHT / 2
        )
    )
    wrist_gripper_x = (
        wrist_pulley_x
        + PULLEY_TOTAL_HEIGHT / 2
        + WRIST_STACK_CLEARANCE
        + gripper_base_model.CLEVIS_TONGUE_WIDTH / 2
    )
    wrist_stack_min_x = wrist_pulley_x - PULLEY_TOTAL_HEIGHT / 2
    wrist_stack_max_x = wrist_gripper_x + gripper_base_model.CLEVIS_TONGUE_WIDTH / 2
    wrist_clevis_min_x = forearm_x - forearm_model.CLEVIS_GAP_X / 2
    wrist_clevis_max_x = forearm_x + forearm_model.CLEVIS_GAP_X / 2
    wrist_clevis_min_x += forearm_model.WRIST_CLEVIS_GAP_CENTER_X
    wrist_clevis_max_x += forearm_model.WRIST_CLEVIS_GAP_CENTER_X
    if (
        wrist_stack_min_x < wrist_clevis_min_x + WRIST_STACK_CLEARANCE
        or wrist_stack_max_x > wrist_clevis_max_x - WRIST_STACK_CLEARANCE
    ):
        raise ValueError(
            "Wrist clevis gap must fit the driven pulley, gripper tongue, and side clearances."
        )
    if abs(wrist_gripper_x) > 1e-9:
        raise ValueError(
            "Wrist offset must keep the gripper centered over the robot base."
        )

    stator = build_stator()
    stator.label = "geared_base_stator"
    base_gear_z = AZIMUTH_TURNTABLE_Z - 7.0
    base_gear = build_base_driven_gear().moved(Pos(0, 0, base_gear_z))
    base_pinion = build_base_driver_pinion().moved(
        Pos(stator_model.BASE_GEAR_CENTER_DISTANCE, 0, base_gear_z)
    )
    base_shaft_center_z = (AZIMUTH_TURNTABLE_Z + turntable_model.PLATE_THICKNESS) / 2
    base_shaft = build_base_azimuth_shaft().moved(Pos(0, 0, base_shaft_center_z))
    turntable = turntable_model.build_model().moved(Pos(0, 0, AZIMUTH_TURNTABLE_Z))
    turntable.label = "azimuth_turntable_shoulder_cleat"
    bicep = bicep_model.build_model().moved(Pos(0, 0, shoulder_pivot_z))
    bicep.label = "bicep_arm_link"
    forearm = forearm_model.build_model().moved(Pos(forearm_x, 0, elbow_pivot_z))
    forearm.label = "forearm_link"
    gripper = build_gripper().moved(
        Pos(wrist_gripper_x, 0, wrist_pivot_z) * Rot(0, 0, 0)
    )
    gripper.label = gripper_model.MODEL_NAME
    shoulder_shaft = build_shoulder_pivot_shaft().moved(Pos(0, 0, shoulder_pivot_z))
    elbow_shaft = build_elbow_pivot_shaft().moved(Pos(0, 0, elbow_pivot_z))
    # Keep the trimmed shaft centered on the laterally offset wrist clevis.
    wrist_shaft = build_wrist_pivot_shaft().moved(
        Pos(forearm_x + forearm_model.WRIST_CLEVIS_GAP_CENTER_X, 0, wrist_pivot_z)
    )

    # Purchased hardware: bearing positions match the pockets cut into each joint.
    base_bearings = [
        build_608_bearing(axis="z").moved(Pos(0, 0, z)) for z in (30.5, 23.5)
    ]
    shoulder_bearings = [
        build_608_bearing().moved(Pos(x, 0, shoulder_pivot_z)) for x in (-30.0, 30.0)
    ]
    elbow_bearing_x = bicep_model.ELBOW_CLEVIS_GAP_X / 2 + (5.0 + 0.25) / 2
    elbow_bearings = [
        build_625_bearing().moved(Pos(x, 0, elbow_pivot_z))
        for x in (-elbow_bearing_x, elbow_bearing_x)
    ]
    wrist_bearings = [
        build_625_bearing().moved(Pos(forearm_x + x, 0, wrist_pivot_z))
        for x in (
            forearm_model.WRIST_CLEVIS_GAP_CENTER_X
            - forearm_model.CLEVIS_GAP_X / 2
            - forearm_model.CLEVIS_EAR_THICKNESS_X
            + 2.5,
            forearm_model.WRIST_CLEVIS_GAP_CENTER_X
            + forearm_model.CLEVIS_GAP_X / 2
            + forearm_model.CLEVIS_EAR_THICKNESS_X
            - 2.5,
        )
    ]
    sg90_servos = [
        build_sg90_installed(
            Pos(
                wrist_gripper_x + x,
                gripper_base_model.SERVO_CENTER_Y,
                wrist_pivot_z + gripper_base_model.SERVO_FLANGE_TOP_Z,
            ),
            "SG90_micro_servo",
        )
        for x in (-gripper_base_model.SERVO_CENTER_X, gripper_base_model.SERVO_CENTER_X)
    ]
    for index, part in enumerate(
        (
            *base_bearings,
            *shoulder_bearings,
            *elbow_bearings,
            *wrist_bearings,
        ),
        1,
    ):
        part.label = f"installed_bearing_{index:02d}_{part.label}"
    for index, part in enumerate(sg90_servos, 1):
        part.label = f"installed_sg90_micro_servo_{index}"

    # Visible fasteners at the gripper: four servo tabs, two jaw pivots, and wrist pulley bolts.
    # Tab screws drive up from under the servo flanges; jaw screws drive down into the posts.
    servo_tab_screw_length = 6.0
    servo_fasteners = [
        build_m3_socket_screw(servo_tab_screw_length, axis="z").moved(
            Pos(
                wrist_gripper_x + x,
                y,
                wrist_pivot_z
                + gripper_base_model.SERVO_FLANGE_TOP_Z
                - 2.0
                + servo_tab_screw_length / 2,
            )
        )
        for x in (-gripper_base_model.SERVO_CENTER_X, gripper_base_model.SERVO_CENTER_X)
        for y in (
            gripper_base_model.SERVO_CENTER_Y - 16.0,
            gripper_base_model.SERVO_CENTER_Y + 16.0,
        )
    ]
    jaw_screw_length = 10.0
    jaw_fasteners = [
        build_m3_socket_screw(jaw_screw_length, axis="z").moved(
            Pos(
                wrist_gripper_x + x,
                gripper_base_model.GRIPPER_POST_Y,
                wrist_pivot_z
                + gripper_model.JAW_Z_CENTER
                + gripper_model.JAW_THICKNESS / 2
                - jaw_screw_length / 2,
            )
            * Rot(180, 0, 0)
        )
        for x in (-gripper_base_model.SERVO_CENTER_X, gripper_base_model.SERVO_CENTER_X)
    ]
    # Wrist screws seat in the 32T pulley's counterbores and thread into the
    # gripper tongue, stopping short of the forearm's far wrist ear.
    wrist_screw_seat_x = (
        wrist_pulley_x - PULLEY_TOTAL_HEIGHT / 2 + WRIST_PULLEY_M3_COUNTERBORE_DEPTH
    )
    wrist_screw_length = max(
        length
        for length in M3_SCREW_LENGTHS
        if length
        <= wrist_gripper_x
        + gripper_base_model.CLEVIS_TONGUE_WIDTH / 2
        - 1.0
        - wrist_screw_seat_x
    )
    wrist_pulley_fasteners = [
        build_m3_socket_screw(wrist_screw_length).moved(
            Pos(wrist_screw_seat_x + wrist_screw_length / 2, y, wrist_pivot_z + z)
        )
        for y, z in circle_points(4, WRIST_PULLEY_BOLT_CIRCLE, start_angle=45.0)
    ]
    # The remaining defined driveline bolt circles use the same M3 preview hardware.
    base_gear_fasteners = [
        build_m3_socket_screw(16.0, axis="z").moved(Pos(x, y, base_gear_z))
        for x, y in circle_points(
            6, BASE_GEAR_BOLT_CIRCLE, start_angle=BASE_GEAR_BOLT_START_ANGLE
        )
    ]
    # Like the elbow, the shoulder screws drive from the bicep's counterbores
    # into the 80T pulley, clear of the left shoulder bearing.
    shoulder_screw_seat_x = bicep_model.SHOULDER_M3_SCREW_SEAT_X
    shoulder_screw_length = max(
        length
        for length in M3_SCREW_LENGTHS
        if length
        <= shoulder_screw_seat_x - (shoulder_pulley_x - PULLEY_TOTAL_HEIGHT / 2) - 1.0
    )
    shoulder_pulley_fasteners = [
        build_m3_socket_screw(shoulder_screw_length).moved(
            Pos(shoulder_screw_seat_x - shoulder_screw_length / 2, y, shoulder_pivot_z + z)
            * Rot(0, 0, 180)
        )
        for y, z in circle_points(4, SHOULDER_PULLEY_BOLT_CIRCLE, start_angle=45.0)
    ]
    # The elbow screws drive from the forearm hub's counterbores into the 60T
    # pulley's thread pilots, so their heads stay hidden inside the bicep clevis.
    elbow_screw_seat_x = (
        forearm_x
        + forearm_model.ELBOW_BOLT_HEAD_SIDE_SIGN
        * (forearm_model.BOTTOM_HUB_THICKNESS / 2 - forearm_model.ELBOW_M3_COUNTERBORE_DEPTH)
    )
    elbow_pulley_far_face_x = elbow_pulley_x - PULLEY_TOTAL_HEIGHT / 2
    elbow_screw_length = max(
        length
        for length in M3_SCREW_LENGTHS
        if length <= elbow_screw_seat_x - elbow_pulley_far_face_x - 1.0
    )
    elbow_pulley_fasteners = [
        build_m3_socket_screw(elbow_screw_length).moved(
            Pos(elbow_screw_seat_x - elbow_screw_length / 2, y, elbow_pivot_z + z)
            * Rot(0, 0, 180)
        )
        for y, z in circle_points(4, ELBOW_PULLEY_BOLT_CIRCLE, start_angle=45.0)
    ]
    base_motor_location = Pos(
        stator_model.BASE_GEAR_CENTER_DISTANCE,
        0,
        stator_model.BASE_MOTOR_FACE_Z,
    )
    base_motor = build_nema17(base_motor_location, "base_nema17_stepper_motor")
    shoulder_motor_location = (
        Pos(
            turntable_model.LEFT_OUTER_X,
            0,
            AZIMUTH_TURNTABLE_Z + turntable_model.MOTOR_SHAFT_Z,
        )
        * Rot(0, 90, 0)
    )
    shoulder_motor = build_nema17(shoulder_motor_location, "shoulder_nema17_stepper_motor")
    elbow_motor_location = (
        Pos(
            bicep_model.MOTOR_FACE_X,
            0,
            shoulder_pivot_z + bicep_model.MOTOR_SHAFT_Z,
        )
        * Rot(0, -90, 0)
    )
    elbow_motor = build_nema17(elbow_motor_location, "elbow_nema17_stepper_motor")
    base_motor_fasteners, shoulder_motor_fasteners, elbow_motor_fasteners = (
        [
            build_m3_socket_screw(length, axis="z").moved(location)
            for length, location in nema17_mount_screw_placements(
                motor_location, mount, NEMA17_HOLE_SPACING
            )
        ]
        for motor_location, mount in (
            (base_motor_location, stator),
            (shoulder_motor_location, turntable),
            (elbow_motor_location, bicep),
        )
    )
    for group, fasteners in (
        ("base_motor", base_motor_fasteners),
        ("shoulder_motor", shoulder_motor_fasteners),
        ("elbow_motor", elbow_motor_fasteners),
        ("base_gear", base_gear_fasteners),
        ("shoulder_pulley", shoulder_pulley_fasteners),
        ("elbow_pulley", elbow_pulley_fasteners),
        ("servo", servo_fasteners),
        ("jaw", jaw_fasteners),
        ("wrist_pulley", wrist_pulley_fasteners),
    ):
        for index, part in enumerate(fasteners, 1):
            part.label = f"installed_M3_fastener_{group}_{index:02d}"

    shoulder_pulley = build_shoulder_pulley().moved(
        Pos(shoulder_pulley_x, 0, shoulder_pivot_z) * Rot(0, 90, 0)
    )
    elbow_pulley = build_elbow_pulley().moved(
        Pos(elbow_pulley_x, 0, elbow_pivot_z) * Rot(0, 90, 0)
    )
    wrist_pulley = build_wrist_pulley().moved(
        Pos(wrist_pulley_x, 0, wrist_pivot_z) * Rot(0, 90, 0)
    )
    shoulder_spacer = build_shoulder_pivot_spacer().moved(
        Pos(shoulder_spacer_x, 0, shoulder_pivot_z)
    )

    wrist_motor_face_x = (
        forearm_model.LINK_THICKNESS_X / 2 + forearm_model.MOTOR_FACE_THICKNESS_X
    )
    wrist_motor_location = (
        Pos(
            forearm_x
            + forearm_model.WRIST_ASSEMBLY_OFFSET_X
            - wrist_motor_face_x
            - forearm_model.MOTOR_EAR_STANDOFF_X,
            0,
            elbow_pivot_z + forearm_model.MOTOR_SHAFT_Z,
        )
        * Rot(0, 90, 0)
    )
    wrist_motor = build_byj48(
        wrist_motor_location,
        "wrist_28BYJ-48_stepper_motor",
    )
    wrist_motor.label = "wrist_28BYJ-48_stepper_motor"
    # Short screws tap directly into blind pilots in the printed ear pads.
    wrist_motor_fasteners = []
    length = forearm_model.MOTOR_MOUNT_SCREW_LENGTH
    for index, y in enumerate((-BYJ48_EAR_SPACING / 2, BYJ48_EAR_SPACING / 2), 1):
        screw = build_m3_socket_screw(length, axis="z").moved(
            wrist_motor_location * Pos(0, y, -MOUNT_PLATE_THICKNESS + length / 2)
        )
        screw.label = f"installed_M3_fastener_wrist_motor_{index:02d}"
        wrist_motor_fasteners.append(screw)
    shoulder_driver_pulley = build_shoulder_driver_pulley().moved(
        Pos(
            shoulder_pulley_x,
            0,
            AZIMUTH_TURNTABLE_Z + turntable_model.MOTOR_SHAFT_Z,
        )
        * Rot(0, 90, 0)
    )
    elbow_driver_pulley = build_elbow_driver_pulley().moved(
        Pos(
            elbow_pulley_x,
            0,
            shoulder_pivot_z + bicep_model.MOTOR_SHAFT_Z,
        )
        * Rot(0, 90, 0)
    )
    wrist_driver_pulley = build_wrist_driver_pulley().moved(
        Pos(
            wrist_pulley_x,
            0,
            elbow_pivot_z + forearm_model.MOTOR_SHAFT_Z,
        )
        * Rot(0, 90, 0)
    )
    shoulder_belt = build_shoulder_htd_belt().moved(
        Pos(
            shoulder_pulley_x,
            0,
            AZIMUTH_TURNTABLE_Z + turntable_model.MOTOR_SHAFT_Z,
        )
        * Rot(0, 90, 90)
    )
    elbow_belt = build_elbow_htd_belt().moved(
        Pos(
            elbow_pulley_x,
            0,
            shoulder_pivot_z + bicep_model.MOTOR_SHAFT_Z,
        )
        * Rot(0, 90, 90)
    )
    wrist_belt = build_wrist_htd_belt().moved(
        Pos(
            wrist_pulley_x,
            0,
            elbow_pivot_z + forearm_model.MOTOR_SHAFT_Z,
        )
        * Rot(0, 90, 90)
    )
    # Keep each motor driver on the same structural stage as its motor.  The
    # elbow and wrist carriers stand on edge outside the motor envelope so
    # their thin attachment ears can fasten directly to the adjacent wall.
    base_driver_tray = build_nema17_driver_board_tray().moved(
        Pos(stator_model.BASE_GEAR_CENTER_DISTANCE, -18, stator_model.BASE_THICKNESS)
    )
    base_driver_tray.label = "base_nema17_driver_board_tray"
    # The shoulder carrier lies flat on the left clevis wall beside the motor
    # flange, its ears screwed into pilots the turntable provides.
    shoulder_driver_tray = build_nema17_driver_board_tray(
        attachment_side=turntable_model.SHOULDER_DRIVER_TRAY_ATTACHMENT_SIDE
    ).moved(
        Pos(0, 0, AZIMUTH_TURNTABLE_Z) * turntable_model.SHOULDER_DRIVER_TRAY_LOCATION
    )
    shoulder_driver_tray.label = "shoulder_nema17_driver_board_tray"
    elbow_driver_tray = build_nema17_driver_board_tray(attachment_side="right")
    elbow_driver_tray = elbow_driver_tray.moved(
        Pos(
            bicep_model.MOTOR_PLATE_CENTER_X - elbow_driver_tray.bounding_box().max.X,
            -bicep_model.MOTOR_PLATE_WIDTH_Y / 2,
            shoulder_pivot_z + bicep_model.MOTOR_SHAFT_Z,
        )
        * Rot(90, 0, 0)
    )
    elbow_driver_tray.label = "elbow_nema17_driver_board_tray"
    wrist_driver_tray = build_28byj_uln_board_tray(attachment_side="right")
    wrist_driver_tab_x = (
        forearm_x
        + forearm_model.WRIST_ASSEMBLY_OFFSET_X
        - (
            forearm_model.LINK_THICKNESS_X / 2
            + forearm_model.MOTOR_FACE_THICKNESS_X / 2
        )
    )
    wrist_driver_tray = wrist_driver_tray.moved(
        Pos(
            wrist_driver_tab_x - wrist_driver_tray.bounding_box().max.X,
            -forearm_model.MOTOR_FACE_WIDTH_Y / 2,
            elbow_pivot_z + forearm_model.MOTOR_SHAFT_Z,
        )
        * Rot(90, 0, 0)
    )
    wrist_driver_tray.label = "wrist_28byj_uln2003_board_tray"

    from models.esp32_boards import (
        PCB_THICKNESS, SOCKET_CENTER_X, DEVKIT_SEATED_Z,
        build_expansion, build_devkit, board_mount_location,
    )
    electronics_location = board_mount_location(AZIMUTH_TURNTABLE_Z)
    esp32_expansion = Compound(children=[part.moved(electronics_location)
                                         for part in build_expansion().children])
    esp32_expansion.label = "installed_esp32_expansion_30pin"
    esp32_devkit = Compound(children=[
        part.moved(electronics_location * Pos(SOCKET_CENTER_X, 0, DEVKIT_SEATED_Z))
        for part in build_devkit().children
    ])
    esp32_devkit.label = "installed_esp32_devkit_30pin"
    # M3 × 6 screws seat on the PCB top. 4.4 mm engagement reaches the
    # existing blind printed pilot depth without breaking through the wall.
    electronics_fasteners = []
    for index, (y, z) in enumerate(turntable_model.ESP32_STANDOFF_POINTS_YZ, 1):
        screw = build_m3_socket_screw(6, axis="z").moved(
            Pos(electronics_location.position.X + PCB_THICKNESS - 3,
                y, AZIMUTH_TURNTABLE_Z + z) * Rot(0, -90, 0)
        )
        screw.label = f"installed_M3_fastener_esp32_{index}"
        electronics_fasteners.append(screw)

    # Wire-management parts are disabled in the main assembly preview.
    # base_cable_guide = build_base_cable_entry_strain_relief_guide().moved(
    #     Pos(0, -98, stator_model.BASE_THICKNESS)
    # )
    # base_service_loop_guard = build_base_azimuth_service_loop_guard().moved(
    #     Pos(0, 0, stator_model.BASE_THICKNESS + stator_model.THRUST_RING_HEIGHT + 0.4)
    # )
    # shoulder_loop_anchor = build_shoulder_service_loop_anchor().moved(
    #     Pos(
    #         turntable_model.RIGHT_OUTER_X + 18,
    #         30,
    #         shoulder_pivot_z - 42,
    #     )
    #     * Rot(0, 0, 90)
    # )
    # elbow_loop_anchor = build_elbow_service_loop_anchor().moved(
    #     Pos(
    #         bicep_model.ELBOW_CLEVIS_TOTAL_X / 2 + 16,
    #         28,
    #         elbow_pivot_z - 34,
    #     )
    #     * Rot(0, 0, 90)
    # )
    # wrist_loop_anchor = build_wrist_service_loop_anchor().moved(
    #     Pos(
    #         forearm_x + forearm_model.CLEVIS_GAP_X / 2 + forearm_model.CLEVIS_EAR_THICKNESS_X + 14,
    #         24,
    #         wrist_pivot_z - 26,
    #     )
    #     * Rot(0, 0, 90)
    # )
    # bicep_wire_channel = build_bicep_harness_channel_marker().moved(
    #     Pos(bicep_model.LINK_X_THICKNESS / 2 + 4, 0, shoulder_pivot_z + 92)
    #     * Rot(90, 0, 0)
    # )
    # forearm_wire_channel = build_forearm_harness_channel_marker().moved(
    #     Pos(forearm_x, 0, elbow_pivot_z + 88) * Rot(90, 0, 0)
    # )

    children = [
        stator,
        base_motor,
        *base_motor_fasteners,
        base_driver_tray,
        base_gear,
        base_pinion,
        base_shaft,
        *base_bearings,
        *base_gear_fasteners,
        turntable,
        esp32_expansion,
        esp32_devkit,
        *electronics_fasteners,
        shoulder_motor,
        *shoulder_motor_fasteners,
        shoulder_driver_tray,
        shoulder_driver_pulley,
        shoulder_belt,
        shoulder_shaft,
        *shoulder_bearings,
        *shoulder_pulley_fasteners,
        bicep,
        shoulder_spacer,
        elbow_motor,
        *elbow_motor_fasteners,
        elbow_driver_tray,
        elbow_driver_pulley,
        elbow_belt,
        shoulder_pulley,
        elbow_shaft,
        *elbow_bearings,
        *elbow_pulley_fasteners,
        forearm,
        elbow_pulley,
        wrist_motor,
        *wrist_motor_fasteners,
        wrist_driver_tray,
        wrist_driver_pulley,
        wrist_belt,
        wrist_shaft,
        *wrist_bearings,
        gripper,
        *sg90_servos,
        *servo_fasteners,
        *jaw_fasteners,
        *wrist_pulley_fasteners,
        wrist_pulley,
    ]

    if configuration == "service":
        base_cable_guide = build_base_cable_entry_strain_relief_guide().moved(
            Pos(0, -98, stator_model.BASE_THICKNESS)
        )
        base_service_loop_guard = build_base_azimuth_service_loop_guard().moved(
            Pos(
                0,
                0,
                stator_model.BASE_THICKNESS + stator_model.THRUST_RING_HEIGHT + 0.4,
            )
        )
        children.extend((base_cable_guide, base_service_loop_guard))

    label = (
        "robot_arm_master_assembly"
        if configuration == "mechanical"
        else f"robot_arm_{configuration}_assembly"
    )
    return Compound(children=children, label=label)


def main() -> None:
    assembly = build_model()
    export_model(assembly, "robot_arm_master_assembly")

    try:
        from ocp_vscode import show
    except ModuleNotFoundError:
        show = None

    if show is not None:
        show(assembly)


if __name__ == "__main__":
    main()
