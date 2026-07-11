# Guarded Child-Facing Architecture

The arm targets supervised demonstrations with payloads up to 100 g. Electronics remain stationary in a ventilated base enclosure. Base, shoulder, elbow, wrist, and gripper transmissions receive separate tool-removable guards secured with captive M3 hardware.

The mechanical assembly stays available for service and fit inspection. The guarded assembly adds the enclosure, cable-entry protection, base service-loop guard, and transmission guards without making those parts structural.

The Uno R4 is the motion and safety authority. The ESP32 is optional UI transport. Normally-closed limits and guard circuits fail open, and a latching external E-stop removes motor power independently of firmware.

The geared base remains the default until physical comparison. The spare HTD 342-3M belt candidate uses 18T/108T pulleys for the same 6:1 reduction. The more obvious 20T/120T pair cannot fit the available belt.
