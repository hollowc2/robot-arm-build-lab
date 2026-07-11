# Uno R4 Motion Safety Supervisor

The Uno R4 owns motor enable, homing, limit handling, and fault state. The ESP32 may send user commands but cannot directly enable a motor driver. Normally-closed E-stop, guard, and limit circuits read LOW when healthy and HIGH when open or disconnected.

The E-stop must also interrupt 12 V motor power through rated external hardware. Firmware disable is secondary protection, not the primary E-stop path.

`main.cpp` implements slow, sequential, bounded homing for the three StepStick-driven NEMA 17 axes and the four-coil 28BYJ-48 wrist. Each axis approaches its normally-closed switch, backs off, and faults if the switch remains open or the maximum approach step count is exceeded. General point-to-point motion remains disabled until measured joint travel, direction, and steps-per-degree values are recorded.

Run the host safety-state test with:

```bash
g++ -std=c++17 -Ifirmware/include firmware/src/safety_controller.cpp firmware/test/test_safety_controller.cpp -o /tmp/robot-arm-safety-test
/tmp/robot-arm-safety-test
```
