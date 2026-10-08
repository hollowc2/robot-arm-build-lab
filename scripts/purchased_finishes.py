"""Material names shared by reference and installed purchased hardware exports."""

PURCHASED_FINISHES = {
    **{name: name for name in ("pcb_black", "electronics_black", "electronics_silver",
                               "electronics_gold", "electronics_white", "electronics_red")},
    "nema17_end_bells": "motor_case",
    "nema17_stator_stack": "motor_stack",
    "nema17_steel_shaft_and_screws": "steel",
    "nema17_jst_connector": "motor_connector",
    "byj48_can": "byj_can",
    "byj48_brass_shaft": "brass",
    "byj48_blue_terminal": "byj_blue",
    "sg90_blue_case": "servo_blue",
    "sg90_nylon_spline": "nylon",
    "sg90_side_label": "servo_label",
    **{f"motor_wire_{color}": f"wire_{color}" for color in ("blue", "pink", "yellow", "orange", "red", "brown")},
}
