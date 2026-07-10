from __future__ import annotations

from functools import lru_cache
from math import atan2, cos, hypot, pi, sin, tan
from typing import Any, Callable

from build123d import (
    Align,
    Box,
    BuildPart,
    BuildSketch,
    Circle,
    Cylinder,
    Location,
    Locations,
    Mode,
    Part,
    Polygon,
    Rectangle,
    Shape,
    Solid,
    Compound,
    add,
    extrude,
)

try:
    from models.common import (
        BASE_GEAR_BOLT_CIRCLE,
        BEARING_625_OD,
        M3_CLEARANCE,
        M3_TAP_HOLE,
        NEMA17_SHAFT,
        ELBOW_PULLEY_BOLT_CIRCLE,
        SHOULDER_PULLEY_BOLT_CIRCLE,
        ELBOW_BELT_CENTER_DISTANCE,
        WRIST_PULLEY_BOLT_CIRCLE,
        WRIST_DRIVER_TEETH,
        WRIST_DRIVEN_TEETH,
        SHOULDER_BELT_CENTER_DISTANCE,
        WRIST_BELT_CENTER_DISTANCE,
        assert_printable_extent,
        circle_points,
        export_model,
    )
except ModuleNotFoundError:
    from common import (
        BASE_GEAR_BOLT_CIRCLE,
        BEARING_625_OD,
        M3_CLEARANCE,
        M3_TAP_HOLE,
        NEMA17_SHAFT,
        ELBOW_PULLEY_BOLT_CIRCLE,
        SHOULDER_PULLEY_BOLT_CIRCLE,
        ELBOW_BELT_CENTER_DISTANCE,
        WRIST_PULLEY_BOLT_CIRCLE,
        WRIST_DRIVER_TEETH,
        WRIST_DRIVEN_TEETH,
        SHOULDER_BELT_CENTER_DISTANCE,
        WRIST_BELT_CENTER_DISTANCE,
        assert_printable_extent,
        circle_points,
        export_model,
    )

# Override center distance to match the HTD 342-3M belt specification
ELBOW_BELT_CENTER_DISTANCE = 113.35

GEAR_MODULE = 1.0
GEAR_PRESSURE_ANGLE = 20.0
GEAR_HELIX_ANGLE = 30.0
GEAR_THICKNESS = 12.0
BASE_GEAR_CENTER_BORE = 48.0
BASE_GEAR_BOLT_START_ANGLE = 30.0
BASE_GEAR_M3_COUNTERBORE_DIAMETER = 6.8
BASE_GEAR_M3_COUNTERBORE_DEPTH = 2.0
HTD_3M_PITCH = 3.0
BELT_WIDTH = 8.0
FLANGE_HEIGHT = 1.5
PULLEY_TOTAL_HEIGHT = BELT_WIDTH + 2 * FLANGE_HEIGHT
HTD_3M_PITCH_LINE_OFFSET = 0.381
HTD_3M_TOOTH_DEPTH = 1.14
HTD_PROFILE_SAMPLES_PER_TOOTH = 12
HTD_BELT_VISUAL_THICKNESS = 1.8
HTD_BELT_VISUAL_TOOTH_HEIGHT = 0.45
HTD_BELT_VISUAL_TOOTH_WIDTH = 1.0
WRIST_KEYED_ADAPTER_OD = 14.0
WRIST_KEYED_ADAPTER_LENGTH = 18.0
WRIST_KEYED_ADAPTER_FLANGE_OD = 18.0
WRIST_KEYED_ADAPTER_FLANGE_THICKNESS = 3.0
WRIST_PULLEY_M3_COUNTERBORE_DIAMETER = 6.8
WRIST_PULLEY_M3_COUNTERBORE_DEPTH = 2.0

D_SHAFT_DIAMETER = NEMA17_SHAFT
D_SHAFT_FLAT_TO_ROUND = 4.5
D_SHAFT_FLAT_FROM_CENTER = D_SHAFT_FLAT_TO_ROUND - D_SHAFT_DIAMETER / 2


def _gear_dedendum(teeth: int) -> float:
    pitch_radius = teeth * GEAR_MODULE / 2
    pressure_angle_rad = GEAR_PRESSURE_ANGLE * pi / 180
    return max(1.25 * GEAR_MODULE, pitch_radius * (1 - cos(pressure_angle_rad)) + 0.15)


def _shape_from_candidate(candidate: Any) -> Shape | None:
    if isinstance(candidate, Shape):
        return candidate
    for attr_name in ("part", "solid", "compound", "wrapped"):
        candidate_attr = getattr(candidate, attr_name, None)
        if isinstance(candidate_attr, Shape):
            return candidate_attr
    return None


def _first_constructed(factory: Callable[..., Any], attempts: tuple[dict[str, Any], ...]) -> Shape | None:
    for kwargs in attempts:
        try:
            shape = _shape_from_candidate(factory(**kwargs))
        except Exception:
            continue
        if shape is not None:
            return shape
    return None


def _herringbone_half_twist_degrees(teeth: int) -> float:
    pitch_radius = teeth * GEAR_MODULE / 2
    half_thickness = GEAR_THICKNESS / 2
    return half_thickness * tan(GEAR_HELIX_ANGLE * pi / 180) / pitch_radius * 180 / pi


def _bd_spur_gear_plan(teeth: int) -> Any:
    try:
        from bd_warehouse.gear import SpurGearPlan
    except Exception as exc:
        raise RuntimeError("bd_warehouse.gear.SpurGearPlan is required to generate herringbone gears") from exc

    return SpurGearPlan(
        module=GEAR_MODULE,
        tooth_count=teeth,
        pressure_angle=GEAR_PRESSURE_ANGLE,
        dedendum=_gear_dedendum(teeth),
        root_fillet=0.15,
    )


def _herringbone_tooth_face(
    *,
    root_radius: float,
    outer_radius: float,
    center_angle_deg: float,
    tooth_pitch_deg: float,
) -> Shape:
    root_half_angle = 0.28 * tooth_pitch_deg
    outer_half_angle = 0.19 * tooth_pitch_deg
    points = []

    for radius, angle_deg in (
        (root_radius, center_angle_deg - root_half_angle),
        (outer_radius, center_angle_deg - outer_half_angle),
        (outer_radius, center_angle_deg + outer_half_angle),
        (root_radius, center_angle_deg + root_half_angle),
    ):
        angle_rad = angle_deg * pi / 180
        points.append((radius * cos(angle_rad), radius * sin(angle_rad)))

    with BuildSketch() as tooth:
        Polygon(points)
    return tooth.sketch.faces()[0]


def _build_herringbone_tooth_half(
    teeth: int,
    *,
    root_radius: float,
    outer_radius: float,
    center_angle_deg: float,
    tooth_pitch_deg: float,
    direction: int,
) -> Part:
    face = _herringbone_tooth_face(
        root_radius=root_radius,
        outer_radius=outer_radius,
        center_angle_deg=center_angle_deg,
        tooth_pitch_deg=tooth_pitch_deg,
    )
    twist_deg = direction * _herringbone_half_twist_degrees(teeth)
    half_height = direction * GEAR_THICKNESS / 2
    solid = Solid.extrude_linear_with_rotation(
        face,
        center=(0, 0, 0),
        normal=(0, 0, half_height),
        angle=twist_deg,
    )
    return Part() + solid


def _build_bd_herringbone_compound(
    teeth: int,
    *,
    label: str,
    add_cut_features: Callable[[float], None],
) -> Compound:
    gear_plan = _bd_spur_gear_plan(teeth)
    root_radius = gear_plan.root_radius
    tooth_root_radius = max(root_radius - 0.05, 0.01)
    outer_radius = gear_plan.addendum_radius
    tooth_pitch_deg = 360 / teeth

    with BuildPart() as root:
        Cylinder(radius=root_radius, height=GEAR_THICKNESS)
        add_cut_features(GEAR_THICKNESS)

    teeth_parts = []
    for tooth_index in range(teeth):
        center_angle_deg = tooth_index * tooth_pitch_deg
        for direction in (1, -1):
            teeth_parts.append(
                _build_herringbone_tooth_half(
                    teeth,
                    root_radius=tooth_root_radius,
                    outer_radius=outer_radius,
                    center_angle_deg=center_angle_deg,
                    tooth_pitch_deg=tooth_pitch_deg,
                    direction=direction,
                )
            )

    return Compound(children=[root.part, *teeth_parts], label=label)


def _bd_timing_pulley(teeth: int) -> Shape | None:
    timing_modules = (
        "bd_warehouse.timing_belts",
        "bd_warehouse.timing_belt",
        "bd_warehouse.pulley",
        "bd_warehouse.pulleys",
    )
    for module_name in timing_modules:
        try:
            module = __import__(module_name, fromlist=["HTD_3M_profile", "TimingPulley"])
            HTD_3M_profile = getattr(module, "HTD_3M_profile")
            TimingPulley = getattr(module, "TimingPulley")
            break
        except Exception:
            continue
    else:
        return None

    try:
        profile = HTD_3M_profile()
    except Exception:
        profile = HTD_3M_profile

    attempts = (
        {
            "profile": profile,
            "tooth_count": teeth,
            "belt_width": BELT_WIDTH,
            "flange_height": FLANGE_HEIGHT,
        },
        {
            "profile": profile,
            "teeth": teeth,
            "belt_width": BELT_WIDTH,
            "flange_height": FLANGE_HEIGHT,
        },
        {
            "belt_profile": profile,
            "tooth_count": teeth,
            "width": BELT_WIDTH,
            "flange_height": FLANGE_HEIGHT,
        },
        {
            "profile": profile,
            "tooth_count": teeth,
            "width": BELT_WIDTH,
        },
    )
    return _first_constructed(TimingPulley, attempts)


def _fallback_herringbone_profile_points(
    *, teeth: int, root_radius: float, outer_radius: float
) -> list[tuple[float, float]]:
    tooth_pitch = 2 * pi / teeth
    points = []

    for index in range(teeth):
        center_angle = index * tooth_pitch
        for angle, radius in (
            (center_angle - tooth_pitch / 2, root_radius),
            (center_angle, outer_radius),
        ):
            points.append((radius * cos(angle), radius * sin(angle)))

    return points


def _fallback_herringbone_half(
    *,
    teeth: int,
    height: float,
    z_offset: float,
    angle_offset: float,
    ring_inner_radius: float | None = None,
) -> Part:
    pitch_radius = teeth * GEAR_MODULE / 2
    outer_radius = (teeth + 2) * GEAR_MODULE / 2
    root_radius = max(pitch_radius - 1.25 * GEAR_MODULE, GEAR_MODULE)

    with BuildPart() as half:
        with BuildSketch() as profile:
            Polygon(
                _fallback_herringbone_profile_points(
                    teeth=teeth,
                    root_radius=root_radius,
                    outer_radius=outer_radius,
                )
            )
        extrude(profile.sketch, amount=height / 2, both=True)
        if ring_inner_radius is not None:
            Cylinder(radius=ring_inner_radius, height=height + 2, mode=Mode.SUBTRACT)

    return half.part.moved(Location((0, 0, z_offset), (0, 0, angle_offset)))


def _add_fallback_herringbone_blank(teeth: int) -> None:
    pitch_radius = teeth * GEAR_MODULE / 2
    root_radius = max(pitch_radius - 1.25 * GEAR_MODULE, GEAR_MODULE)
    Cylinder(radius=root_radius, height=GEAR_THICKNESS)


def _add_fallback_herringbone_teeth(teeth: int) -> None:
    pitch_radius = teeth * GEAR_MODULE / 2
    root_radius = max(pitch_radius - 1.25 * GEAR_MODULE, GEAR_MODULE)
    ring_inner_radius = max(root_radius - 0.35, 0.01)

    add(
        _fallback_herringbone_half(
            teeth=teeth,
            height=GEAR_THICKNESS / 2,
            z_offset=GEAR_THICKNESS / 4,
            angle_offset=0.0,
            ring_inner_radius=ring_inner_radius,
        )
    )
    add(
        _fallback_herringbone_half(
            teeth=teeth,
            height=GEAR_THICKNESS / 2,
            z_offset=-GEAR_THICKNESS / 4,
            angle_offset=180 / teeth,
            ring_inner_radius=ring_inner_radius,
        )
    )


def _htd_pitch_radius(teeth: int) -> float:
    return teeth * HTD_3M_PITCH / (2 * pi)


def _add_fallback_pulley_blank(teeth: int) -> None:
    pitch_radius = _htd_pitch_radius(teeth)
    outer_radius = pitch_radius - HTD_3M_PITCH_LINE_OFFSET
    root_radius = outer_radius - HTD_3M_TOOTH_DEPTH
    flange_radius = outer_radius + 1.6
    total_samples = teeth * HTD_PROFILE_SAMPLES_PER_TOOTH
    points = []

    for sample in range(total_samples):
        angle = 2 * pi * sample / total_samples
        tooth_phase = angle * teeth
        tooth_blend = 0.5 + 0.5 * cos(tooth_phase)
        radius = root_radius + HTD_3M_TOOTH_DEPTH * tooth_blend
        points.append((radius * cos(angle), radius * sin(angle)))

    with BuildSketch() as blank:
        Polygon(points)
    extrude(blank.sketch, amount=BELT_WIDTH / 2, both=True)

    with Locations(Location((0, 0, BELT_WIDTH / 2 + FLANGE_HEIGHT / 2))):
        Cylinder(radius=flange_radius, height=FLANGE_HEIGHT)
    with Locations(Location((0, 0, -BELT_WIDTH / 2 - FLANGE_HEIGHT / 2))):
        Cylinder(radius=flange_radius, height=FLANGE_HEIGHT)


def _add_center_hole(diameter: float, height: float) -> None:
    Cylinder(radius=diameter / 2, height=height + 2, mode=Mode.SUBTRACT)


def _add_center_hole_2d(diameter: float) -> None:
    Circle(radius=diameter / 2, mode=Mode.SUBTRACT)


def _add_d_shaft_hole(height: float) -> None:
    _add_center_hole(D_SHAFT_DIAMETER, height)

    filler_depth = max(D_SHAFT_DIAMETER / 2 - D_SHAFT_FLAT_FROM_CENTER, 0.01)
    filler_center_x = D_SHAFT_FLAT_FROM_CENTER + filler_depth / 2
    with Locations(Location((filler_center_x, 0, 0))):
        Box(
            filler_depth,
            D_SHAFT_DIAMETER + 1.0,
            height,
            align=(Align.CENTER, Align.CENTER, Align.CENTER),
        )


def _add_d_shaft_hole_2d() -> None:
    _add_center_hole_2d(D_SHAFT_DIAMETER)

    filler_depth = max(D_SHAFT_DIAMETER / 2 - D_SHAFT_FLAT_FROM_CENTER, 0.01)
    filler_center_x = D_SHAFT_FLAT_FROM_CENTER + filler_depth / 2
    with Locations(Location((filler_center_x, 0))):
        Rectangle(
            filler_depth,
            D_SHAFT_DIAMETER + 1.0,
            align=(Align.CENTER, Align.CENTER),
            mode=Mode.ADD,
        )


def _add_bolt_circle(
    count: int,
    bolt_circle: float,
    height: float,
    start_angle: float = 0.0,
    *,
    hole_diameter: float = M3_CLEARANCE,
) -> None:
    for x, y in circle_points(count, bolt_circle, start_angle=start_angle):
        with Locations(Location((x, y, 0))):
            Cylinder(radius=hole_diameter / 2, height=height + 2, mode=Mode.SUBTRACT)


def _add_bottom_counterbore_bolt_circle(
    count: int,
    bolt_circle: float,
    height: float,
    start_angle: float = 0.0,
    *,
    hole_diameter: float = M3_CLEARANCE,
    head_diameter: float = BASE_GEAR_M3_COUNTERBORE_DIAMETER,
    counterbore_depth: float = BASE_GEAR_M3_COUNTERBORE_DEPTH,
) -> None:
    _add_bolt_circle(count, bolt_circle, height, start_angle, hole_diameter=hole_diameter)

    counterbore_z = -height / 2 + counterbore_depth / 2
    for x, y in circle_points(count, bolt_circle, start_angle=start_angle):
        with Locations(Location((x, y, counterbore_z))):
            Cylinder(
                radius=head_diameter / 2,
                height=counterbore_depth,
                mode=Mode.SUBTRACT,
            )


def _add_bolt_circle_2d(count: int, bolt_circle: float, start_angle: float = 0.0) -> None:
    for x, y in circle_points(count, bolt_circle, start_angle=start_angle):
        with Locations(Location((x, y))):
            Circle(radius=M3_CLEARANCE / 2, mode=Mode.SUBTRACT)


def _finalize(part: Part, label: str) -> Part:
    part.label = label
    size = part.bounding_box().size
    assert_printable_extent((size.X, size.Y, size.Z))
    return part


@lru_cache(maxsize=None)
def build_base_driven_gear() -> Part:
    def add_cut_features(height: float) -> None:
        _add_center_hole(BASE_GEAR_CENTER_BORE, height)
        _add_bottom_counterbore_bolt_circle(
            6,
            BASE_GEAR_BOLT_CIRCLE,
            height,
            start_angle=BASE_GEAR_BOLT_START_ANGLE,
        )

    gear = _build_bd_herringbone_compound(
        120,
        label="base_driven_120T_module1_herringbone_48mm_bore_6xM3_60BC",
        add_cut_features=add_cut_features,
    )
    return _finalize(gear, "base_driven_120T_module1_herringbone_48mm_bore_6xM3_60BC")


@lru_cache(maxsize=None)
def build_base_driver_pinion() -> Part:
    def add_cut_features(height: float) -> None:
        _add_center_hole(NEMA17_SHAFT, height)

    pinion = _build_bd_herringbone_compound(
        20,
        label="base_driver_20T_module1_herringbone_5mm_round_shaft",
        add_cut_features=add_cut_features,
    )
    return _finalize(pinion, "base_driver_20T_module1_herringbone_5mm_round_shaft")


def build_shoulder_driver_pulley() -> Part:
    return _build_motor_pulley(
        teeth=16,
        label="shoulder_driver_16T_HTD3M_5mm_D_shaft",
        keyed=True,
    )


def build_elbow_driver_pulley() -> Part:
    return _build_motor_pulley(
        teeth=16,
        label="elbow_driver_16T_HTD3M_5mm_round_shaft",
        keyed=False,
    )


def build_wrist_driver_pulley() -> Part:
    return _build_motor_pulley(
        teeth=WRIST_DRIVER_TEETH,
        label=f"wrist_driver_{WRIST_DRIVER_TEETH}T_HTD3M_5mm_D_shaft",
        keyed=True,
    )


def build_wrist_keyed_shaft_adapter() -> Part:
    """Build a printed keyed extension for the short 28BYJ wrist motor shaft."""
    with BuildPart() as adapter:
        Cylinder(
            radius=WRIST_KEYED_ADAPTER_OD / 2,
            height=WRIST_KEYED_ADAPTER_LENGTH,
        )
        with Locations(
            Location(
                (
                    0,
                    0,
                    WRIST_KEYED_ADAPTER_LENGTH / 2
                    - WRIST_KEYED_ADAPTER_FLANGE_THICKNESS / 2,
                )
            )
        ):
            Cylinder(
                radius=WRIST_KEYED_ADAPTER_FLANGE_OD / 2,
                height=WRIST_KEYED_ADAPTER_FLANGE_THICKNESS,
            )

        _add_d_shaft_hole(WRIST_KEYED_ADAPTER_LENGTH)

        for z_offset in (-4.0, 4.0):
            with Locations(Location((0, 0, z_offset), (90, 0, 0))):
                Cylinder(
                    radius=M3_TAP_HOLE / 2,
                    height=WRIST_KEYED_ADAPTER_OD + 2.0,
                    mode=Mode.SUBTRACT,
                )

    return _finalize(adapter.part, "wrist_keyed_28byj_shaft_to_pulley_adapter")


def build_shoulder_pulley() -> Part:
    return _build_pulley(
        teeth=80,
        center_hole=8.5,
        bolt_circle=SHOULDER_PULLEY_BOLT_CIRCLE,
        label="shoulder_80T_HTD3M_8p5_4xM3_25BC",
        bolt_hole_diameter=M3_TAP_HOLE,
    )


def build_elbow_pulley() -> Part:
    return _build_pulley(
        teeth=60,
        center_hole=BEARING_625_OD,
        bolt_circle=ELBOW_PULLEY_BOLT_CIRCLE,
        label="elbow_60T_HTD3M_16p15_4xM3_25BC",
        bolt_hole_diameter=M3_TAP_HOLE,
    )


def build_wrist_pulley() -> Part:
    return _build_pulley(
        teeth=WRIST_DRIVEN_TEETH,
        center_hole=BEARING_625_OD,
        bolt_circle=WRIST_PULLEY_BOLT_CIRCLE,
        label=f"wrist_{WRIST_DRIVEN_TEETH}T_HTD3M_16p15_4xM3_20BC",
        bottom_counterbore=True,
        counterbore_diameter=WRIST_PULLEY_M3_COUNTERBORE_DIAMETER,
        counterbore_depth=WRIST_PULLEY_M3_COUNTERBORE_DEPTH,
    )


def _build_pulley(
    *,
    teeth: int,
    center_hole: float,
    bolt_circle: float,
    label: str,
    bolt_hole_diameter: float = M3_CLEARANCE,
    bottom_counterbore: bool = False,
    counterbore_diameter: float = BASE_GEAR_M3_COUNTERBORE_DIAMETER,
    counterbore_depth: float = BASE_GEAR_M3_COUNTERBORE_DEPTH,
) -> Part:
    with BuildPart() as pulley:
        blank = _bd_timing_pulley(teeth)
        if blank is not None:
            add(blank)
            pitch_radius = teeth * HTD_3M_PITCH / (2 * pi)
            flange_radius = pitch_radius + 2.35
            with Locations(Location((0, 0, BELT_WIDTH / 2 + FLANGE_HEIGHT / 2))):
                Cylinder(radius=flange_radius, height=FLANGE_HEIGHT)
            with Locations(Location((0, 0, -BELT_WIDTH / 2 - FLANGE_HEIGHT / 2))):
                Cylinder(radius=flange_radius, height=FLANGE_HEIGHT)
        else:
            _add_fallback_pulley_blank(teeth)

        _add_center_hole(center_hole, PULLEY_TOTAL_HEIGHT)
        if bottom_counterbore:
            _add_bottom_counterbore_bolt_circle(
                4,
                bolt_circle,
                PULLEY_TOTAL_HEIGHT,
                start_angle=45.0,
                hole_diameter=bolt_hole_diameter,
                head_diameter=counterbore_diameter,
                counterbore_depth=counterbore_depth,
            )
        else:
            _add_bolt_circle(
                4,
                bolt_circle,
                PULLEY_TOTAL_HEIGHT,
                start_angle=45.0,
                hole_diameter=bolt_hole_diameter,
            )

    return _finalize(pulley.part, label)


def _build_motor_pulley(*, teeth: int, label: str, keyed: bool) -> Part:
    with BuildPart() as pulley:
        blank = _bd_timing_pulley(teeth)
        if blank is not None:
            add(blank)
            pitch_radius = teeth * HTD_3M_PITCH / (2 * pi)
            flange_radius = pitch_radius + 2.35
            with Locations(Location((0, 0, BELT_WIDTH / 2 + FLANGE_HEIGHT / 2))):
                Cylinder(radius=flange_radius, height=FLANGE_HEIGHT)
            with Locations(Location((0, 0, -BELT_WIDTH / 2 - FLANGE_HEIGHT / 2))):
                Cylinder(radius=flange_radius, height=FLANGE_HEIGHT)
        else:
            _add_fallback_pulley_blank(teeth)

        if keyed:
            _add_d_shaft_hole(PULLEY_TOTAL_HEIGHT)
        else:
            _add_center_hole(NEMA17_SHAFT, PULLEY_TOTAL_HEIGHT)

    return _finalize(pulley.part, label)


def _build_belt_run(
    *,
    start: tuple[float, float],
    end: tuple[float, float],
    tooth_normal: tuple[float, float],
    label: str,
    include_body: bool = True,
) -> Part:
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    length = hypot(dx, dy)
    angle = atan2(dy, dx)
    center = ((start[0] + end[0]) / 2, (start[1] + end[1]) / 2)

    with BuildPart() as run:
        if include_body:
            with Locations(Location((center[0], center[1], 0), (0, 0, angle * 180 / pi))):
                Box(
                    length,
                    HTD_BELT_VISUAL_THICKNESS,
                    BELT_WIDTH,
                    align=(Align.CENTER, Align.CENTER, Align.CENTER),
                )

        tooth_count = max(int(length / HTD_3M_PITCH), 1)
        step_x = dx / length if length else 1.0
        step_y = dy / length if length else 0.0
        tooth_offset = HTD_BELT_VISUAL_THICKNESS / 2 + HTD_BELT_VISUAL_TOOTH_HEIGHT / 2
        for index in range(tooth_count):
            along = (index + 0.5) * length / tooth_count
            x = start[0] + step_x * along + tooth_normal[0] * tooth_offset
            y = start[1] + step_y * along + tooth_normal[1] * tooth_offset
            with Locations(Location((x, y, 0), (0, 0, angle * 180 / pi))):
                Box(
                    HTD_BELT_VISUAL_TOOTH_WIDTH,
                    HTD_BELT_VISUAL_TOOTH_HEIGHT,
                    BELT_WIDTH + 0.05,
                    align=(Align.CENTER, Align.CENTER, Align.CENTER),
                )

    run.part.label = label
    return run.part


def _arc_points(
    *,
    center: tuple[float, float],
    radius: float,
    start_angle: float,
    end_angle: float,
    contains_angle: float,
) -> list[tuple[float, float]]:
    delta = _arc_delta(start_angle=start_angle, end_angle=end_angle, contains_angle=contains_angle)
    steps = max(int(abs(delta) / (pi / 36)), 8)

    return [
        (
            center[0] + radius * cos(start_angle + delta * step / steps),
            center[1] + radius * sin(start_angle + delta * step / steps),
        )
        for step in range(steps + 1)
    ]


def _arc_delta(*, start_angle: float, end_angle: float, contains_angle: float) -> float:
    full_turn = 2 * pi
    ccw_delta = (end_angle - start_angle) % full_turn
    contains_delta = (contains_angle - start_angle) % full_turn
    return ccw_delta if contains_delta <= ccw_delta else ccw_delta - full_turn


def _build_belt_arc_teeth(
    *,
    center: tuple[float, float],
    radius: float,
    start_angle: float,
    end_angle: float,
    contains_angle: float,
    label: str,
) -> Part:
    delta = _arc_delta(start_angle=start_angle, end_angle=end_angle, contains_angle=contains_angle)
    arc_length = abs(delta) * radius
    tooth_count = max(int(arc_length / HTD_3M_PITCH), 1)
    tooth_radius = max(radius - HTD_BELT_VISUAL_THICKNESS / 2 - HTD_BELT_VISUAL_TOOTH_HEIGHT / 2, 0.01)

    with BuildPart() as teeth:
        for index in range(tooth_count):
            angle = start_angle + delta * (index + 0.5) / tooth_count
            x = center[0] + tooth_radius * cos(angle)
            y = center[1] + tooth_radius * sin(angle)
            tangent_angle = angle + (pi / 2 if delta >= 0 else -pi / 2)
            with Locations(Location((x, y, 0), (0, 0, tangent_angle * 180 / pi))):
                Box(
                    HTD_BELT_VISUAL_TOOTH_WIDTH,
                    HTD_BELT_VISUAL_TOOTH_HEIGHT,
                    BELT_WIDTH + 0.05,
                    align=(Align.CENTER, Align.CENTER, Align.CENTER),
                )

    teeth.part.label = label
    return teeth.part


def _build_belt_loop_body(
    *,
    driver_center: tuple[float, float],
    driven_center: tuple[float, float],
    driver_radius: float,
    driven_radius: float,
    plus_normal: tuple[float, float],
    minus_normal: tuple[float, float],
    label: str,
) -> Part:
    half_thickness = HTD_BELT_VISUAL_THICKNESS / 2
    plus_angle = atan2(plus_normal[1], plus_normal[0])
    minus_angle = atan2(minus_normal[1], minus_normal[0])
    driver_away_angle = atan2(driver_center[1] - driven_center[1], driver_center[0] - driven_center[0])
    driven_away_angle = atan2(driven_center[1] - driver_center[1], driven_center[0] - driver_center[0])

    def point(center: tuple[float, float], radius: float, normal: tuple[float, float]) -> tuple[float, float]:
        return (center[0] + radius * normal[0], center[1] + radius * normal[1])

    def loop_points(radius_offset: float) -> list[tuple[float, float]]:
        driver_loop_radius = max(driver_radius + radius_offset, 0.01)
        driven_loop_radius = max(driven_radius + radius_offset, 0.01)
        points = [
            point(driver_center, driver_loop_radius, plus_normal),
            point(driven_center, driven_loop_radius, plus_normal),
        ]
        points.extend(
            _arc_points(
                center=driven_center,
                radius=driven_loop_radius,
                start_angle=plus_angle,
                end_angle=minus_angle,
                contains_angle=driven_away_angle,
            )[1:]
        )
        points.append(point(driver_center, driver_loop_radius, minus_normal))
        points.extend(
            _arc_points(
                center=driver_center,
                radius=driver_loop_radius,
                start_angle=minus_angle,
                end_angle=plus_angle,
                contains_angle=driver_away_angle,
            )[1:]
        )
        return points

    with BuildPart() as belt_body:
        with BuildSketch() as belt_profile:
            Polygon(loop_points(half_thickness))
            Polygon(loop_points(-half_thickness), mode=Mode.SUBTRACT)
        extrude(belt_profile.sketch, amount=BELT_WIDTH / 2, both=True)

    belt_body.part.label = label
    return belt_body.part


def build_htd3m_open_belt(
    *,
    driver_teeth: int,
    driven_teeth: int,
    center_distance: float | None = None,
    driver_center: tuple[float, float] = (0.0, 0.0),
    driven_center: tuple[float, float] | None = None,
    label: str = "HTD3M_open_belt_visual",
) -> Compound:
    """Build a visual HTD 3M open belt in local XY with belt width on local Z."""
    if driven_center is None:
        if center_distance is None:
            raise ValueError("center_distance or driven_center is required")
        driven_center = (driver_center[0], driver_center[1] + center_distance)

    dx = driven_center[0] - driver_center[0]
    dy = driven_center[1] - driver_center[1]
    distance = hypot(dx, dy)
    if distance <= 0:
        raise ValueError("pulley centers must be distinct")

    driver_radius = _htd_pitch_radius(driver_teeth)
    driven_radius = _htd_pitch_radius(driven_teeth)
    if abs(driver_radius - driven_radius) >= distance:
        raise ValueError("pulley center distance is too short for an open belt visual")

    unit = (dx / distance, dy / distance)
    normal = (-unit[1], unit[0])
    tangent_bias = (driver_radius - driven_radius) / distance
    tangent_span = (1 - tangent_bias * tangent_bias) ** 0.5

    line_normals = {
        side: (
            tangent_bias * unit[0] + side * tangent_span * normal[0],
            tangent_bias * unit[1] + side * tangent_span * normal[1],
        )
        for side in (1.0, -1.0)
    }
    plus_angle = atan2(line_normals[1.0][1], line_normals[1.0][0])
    minus_angle = atan2(line_normals[-1.0][1], line_normals[-1.0][0])
    driver_away_angle = atan2(driver_center[1] - driven_center[1], driver_center[0] - driven_center[0])
    driven_away_angle = atan2(driven_center[1] - driver_center[1], driven_center[0] - driver_center[0])
    children: list[Part] = [
        _build_belt_loop_body(
            driver_center=driver_center,
            driven_center=driven_center,
            driver_radius=driver_radius,
            driven_radius=driven_radius,
            plus_normal=line_normals[1.0],
            minus_normal=line_normals[-1.0],
            label=f"{label}_closed_loop_body",
        ),
        _build_belt_arc_teeth(
            center=driven_center,
            radius=driven_radius,
            start_angle=plus_angle,
            end_angle=minus_angle,
            contains_angle=driven_away_angle,
            label=f"{label}_driven_wrap_teeth",
        ),
        _build_belt_arc_teeth(
            center=driver_center,
            radius=driver_radius,
            start_angle=minus_angle,
            end_angle=plus_angle,
            contains_angle=driver_away_angle,
            label=f"{label}_driver_wrap_teeth",
        ),
    ]

    for side, side_name in ((1.0, "forward"), (-1.0, "return")):
        line_normal = line_normals[side]
        start = (
            driver_center[0] + driver_radius * line_normal[0],
            driver_center[1] + driver_radius * line_normal[1],
        )
        end = (
            driven_center[0] + driven_radius * line_normal[0],
            driven_center[1] + driven_radius * line_normal[1],
        )
        children.append(
            _build_belt_run(
                start=start,
                end=end,
                tooth_normal=(-line_normal[0], -line_normal[1]),
                label=f"{label}_{side_name}_toothed_run",
                include_body=False,
            )
        )

    belt = Compound(children=children, label=label)
    size = belt.bounding_box().size
    assert_printable_extent((size.X, size.Y, size.Z))
    return belt


def build_shoulder_htd_belt() -> Compound:
    return build_htd3m_open_belt(
        driver_teeth=16,
        driven_teeth=80,
        center_distance=SHOULDER_BELT_CENTER_DISTANCE,
        label="shoulder_16T_to_80T_HTD3M_open_belt_visual",
    )


def build_elbow_htd_belt() -> Compound:
    return build_htd3m_open_belt(
        driver_teeth=16,
        driven_teeth=60,
        center_distance=ELBOW_BELT_CENTER_DISTANCE,
        label="elbow_16T_to_60T_HTD3M_open_belt_visual",
    )


def build_wrist_htd_belt() -> Compound:
    return build_htd3m_open_belt(
        driver_teeth=WRIST_DRIVER_TEETH,
        driven_teeth=WRIST_DRIVEN_TEETH,
        center_distance=WRIST_BELT_CENTER_DISTANCE,
        label=f"wrist_{WRIST_DRIVER_TEETH}T_to_{WRIST_DRIVEN_TEETH}T_HTD3M_open_belt_visual",
    )


def _display_place(component: Shape, center_xy: tuple[float, float], rotation_z: float = 0.0) -> Shape:
    arranged = component.moved(Location((0, 0, 0), (0, 0, rotation_z))) if rotation_z else component
    bbox = arranged.bounding_box()
    center = (
        (bbox.min.X + bbox.max.X) / 2,
        (bbox.min.Y + bbox.max.Y) / 2,
        (bbox.min.Z + bbox.max.Z) / 2,
    )
    return arranged.moved(Location((center_xy[0] - center[0], center_xy[1] - center[1], -center[2])))


def build_model() -> Compound:
    """Group all transmission components into an aggregate layout for visual preview."""
    parts = (
        _display_place(build_base_driven_gear(), (-67.0, -16.0)),
        _display_place(build_base_driver_pinion(), (31.0, 62.0)),
        _display_place(build_shoulder_driver_pulley(), (31.0, 86.0)),
        _display_place(build_elbow_driver_pulley(), (31.0, 110.0)),
        _display_place(build_wrist_driver_pulley(), (-104.0, -104.0)),
        _display_place(build_wrist_keyed_shaft_adapter(), (-104.0, -80.0)),
        _display_place(build_shoulder_pulley(), (88.0, 88.6)),
        _display_place(build_elbow_pulley(), (29.3, 15.0)),
        _display_place(build_wrist_pulley(), (93.0, 15.0)),
        _display_place(build_shoulder_htd_belt(), (-57.2, 88.9), rotation_z=90.0),
        _display_place(build_elbow_htd_belt(), (63.0, -47.5), rotation_z=90.0),
        _display_place(build_wrist_htd_belt(), (55.5, -104.0), rotation_z=90.0),
    )
    # Rebuilt as a purely visual aggregate compound.
    # Individual parts continue to validate boundary constraints inside _finalize().
    return Compound(children=parts, label="transmission_components_arranged")

def main() -> None:
    components = {
        "base_driven_120T_herringbone_gear": build_base_driven_gear(),
        "base_driver_20T_herringbone_pinion": build_base_driver_pinion(),
        "shoulder_driver_16T_htd3m_pulley": build_shoulder_driver_pulley(),
        "elbow_driver_16T_htd3m_pulley": build_elbow_driver_pulley(),
        "wrist_driver_20T_htd3m_pulley": build_wrist_driver_pulley(),
        "wrist_keyed_28byj_shaft_to_pulley_adapter": build_wrist_keyed_shaft_adapter(),
        "shoulder_80T_htd3m_pulley": build_shoulder_pulley(),
        "elbow_60T_htd3m_pulley": build_elbow_pulley(),
        f"wrist_{WRIST_DRIVEN_TEETH}T_htd3m_pulley": build_wrist_pulley(),
        "shoulder_16T_to_80T_htd3m_belt_visual": build_shoulder_htd_belt(),
        "elbow_16T_to_60T_htd3m_belt_visual": build_elbow_htd_belt(),
        f"wrist_{WRIST_DRIVER_TEETH}T_to_{WRIST_DRIVEN_TEETH}T_htd3m_belt_visual": build_wrist_htd_belt(),
        "transmission_components": build_model(),
    }
    for name, component in components.items():
        export_model(component, name)

    try:
        from ocp_vscode import show
    except Exception:
        return
    show(components["transmission_components"])


if __name__ == "__main__":
    main()
