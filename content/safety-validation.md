# Safety Validation Checklist

Status values are `not tested`, `pass`, or `fail`. A failure blocks child-facing operation until corrected and retested.

## Before Full Prints

- Record caliper measurements for 608 and 625 bearings, shafts, motor shafts, pulley bores, boards, switches, and connectors.
- Print bearing-pocket, shaft-bore, M3 captive-head, switch-mount, 3.5 mm vent, and 3 mm moving-clearance coupons.
- Replace drill bits used as shafts with dimensioned smooth steel shafts for the final build.
- Record filament, nozzle, layer height, wall count, infill, orientation, and measured coupon error.

## Mechanical

- Verify each guard clears its belt, pulley, shaft, and motor throughout the complete commanded joint range.
- Verify no opening admits a 5 mm probe into a moving transmission or live electrical terminal.
- Verify guard fasteners remain captive and guard removal does not loosen structural or belt-tension hardware.
- Verify hard stops act beyond software travel but before cable damage, collision, or joint over-rotation.
- Run unloaded and 100 g endurance cycles; record motor, driver, bearing, and enclosure temperatures.

## Electrical and Controls

- Confirm the normally-closed E-stop removes motor power through external rated switching hardware.
- Confirm opening any guard interlock disables all motor drivers.
- Confirm a disconnected limit, E-stop, or guard wire is detected as an open/fault condition.
- Confirm startup, reset, E-stop recovery, guard opening, and communication loss all require re-homing.
- Confirm unexpected limit activation and ESP32 heartbeat loss stop motion and disable drivers.
- Confirm StepStick current limits and demonstration-mode speed/acceleration values are recorded.

## Sign-Off

- Adult operator:
- Date:
- Firmware revision:
- CAD revision:
- Mechanical result:
- Electrical result:
- 100 g endurance result:
- Remaining restrictions:
