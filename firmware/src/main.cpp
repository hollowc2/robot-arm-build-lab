#include <Arduino.h>
#include "safety_controller.h"

namespace pins {
constexpr int kEmergencyStop = 2;
constexpr int kGuardChain = 3;
constexpr int kLimits[] = {4, 5, 6, 7};
constexpr int kDriverEnable = 8;  // StepStick enable is active low.
constexpr int kServo = 9;
constexpr int kStep[] = {10, 12, A0};
constexpr int kDirection[] = {11, 13, A1};
constexpr int kWristCoils[] = {A2, A3, A4, A5};
}  // namespace pins

constexpr unsigned long kHeartbeatTimeoutMs = 500;
constexpr unsigned long kHomeStepIntervalUs = 2500;
constexpr long kMaximumHomeSteps = 12000;
constexpr int kBackoffSteps = 120;
SafetyController safety;
unsigned long last_heartbeat_ms = 0;
unsigned long last_home_step_us = 0;
int home_axis = -1;
long home_steps = 0;
int backoff_remaining = 0;
int wrist_phase = 0;

void disableWrist() {
  for (int pin : pins::kWristCoils) digitalWrite(pin, LOW);
}

void stepWrist(int direction) {
  static constexpr bool phases[4][4] = {
      {true, false, false, true},
      {true, true, false, false},
      {false, true, true, false},
      {false, false, true, true},
  };
  wrist_phase = (wrist_phase + direction + 4) % 4;
  for (int index = 0; index < 4; ++index) {
    digitalWrite(pins::kWristCoils[index], phases[wrist_phase][index]);
  }
}

void pulseHomeAxis(int axis, bool backoff) {
  const int direction = backoff ? HIGH : LOW;
  if (axis < 3) {
    digitalWrite(pins::kDirection[axis], direction);
    digitalWrite(pins::kStep[axis], HIGH);
    delayMicroseconds(3);
    digitalWrite(pins::kStep[axis], LOW);
  } else {
    stepWrist(backoff ? 1 : -1);
  }
}

void beginHoming() {
  home_axis = 0;
  home_steps = 0;
  backoff_remaining = 0;
  last_home_step_us = micros();
}

void serviceHoming() {
  if (safety.state() != SafetyState::Homing || home_axis < 0) return;
  if (micros() - last_home_step_us < kHomeStepIntervalUs) return;
  last_home_step_us = micros();

  if (backoff_remaining > 0) {
    pulseHomeAxis(home_axis, true);
    --backoff_remaining;
    if (backoff_remaining == 0) {
      if (digitalRead(pins::kLimits[home_axis]) == HIGH) {
        safety.setHomingFailed();
        disableWrist();
        return;
      }
      ++home_axis;
      home_steps = 0;
      if (home_axis == 4) {
        home_axis = -1;
        disableWrist();
        safety.setHomingComplete();
      }
    }
    return;
  }

  if (digitalRead(pins::kLimits[home_axis]) == HIGH) {
    backoff_remaining = kBackoffSteps;
    return;
  }
  pulseHomeAxis(home_axis, false);
  if (++home_steps > kMaximumHomeSteps) {
    home_axis = -1;
    disableWrist();
    safety.setHomingFailed();
  }
}

SafetyInputs readSafetyInputs() {
  bool any_limit_open = false;
  for (int pin : pins::kLimits) any_limit_open |= digitalRead(pin) == HIGH;
  return {
      digitalRead(pins::kEmergencyStop) == LOW,
      digitalRead(pins::kGuardChain) == LOW,
      millis() - last_heartbeat_ms <= kHeartbeatTimeoutMs,
      any_limit_open,
  };
}

void setup() {
  pinMode(pins::kEmergencyStop, INPUT_PULLUP);
  pinMode(pins::kGuardChain, INPUT_PULLUP);
  for (int pin : pins::kLimits) pinMode(pin, INPUT_PULLUP);
  pinMode(pins::kDriverEnable, OUTPUT);
  for (int pin : pins::kStep) pinMode(pin, OUTPUT);
  for (int pin : pins::kDirection) pinMode(pin, OUTPUT);
  for (int pin : pins::kWristCoils) pinMode(pin, OUTPUT);
  digitalWrite(pins::kDriverEnable, HIGH);
  Serial.begin(115200);
  Serial1.begin(115200);
}

void loop() {
  while (Serial1.available()) {
    const char command = static_cast<char>(Serial1.read());
    if (command == 'H') last_heartbeat_ms = millis();
    if (command == 'R') safety.reset(readSafetyInputs());
    if (command == 'Z' && safety.requestHoming()) beginHoming();
  }
  safety.update(readSafetyInputs());
  serviceHoming();
  digitalWrite(pins::kDriverEnable, safety.driversEnabled() ? LOW : HIGH);
  if (!safety.driversEnabled()) disableWrist();
}
