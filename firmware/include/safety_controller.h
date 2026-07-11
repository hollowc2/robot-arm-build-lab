#pragma once

#include <cstdint>

enum class SafetyState : std::uint8_t {
  BootDisabled,
  Homing,
  Ready,
  Moving,
  Fault,
  EmergencyStop,
};

enum class FaultCode : std::uint8_t {
  None,
  GuardOpen,
  UnexpectedLimit,
  CommunicationTimeout,
  HomingFailed,
};

struct SafetyInputs {
  bool emergency_stop_ok;
  bool guards_closed;
  bool communication_ok;
  bool any_limit_open;
};

class SafetyController {
 public:
  SafetyController();

  void update(const SafetyInputs& inputs);
  bool requestHoming();
  bool setHomingComplete();
  bool setHomingFailed();
  bool requestMotion();
  void setMotionComplete();
  bool reset(const SafetyInputs& inputs);

  SafetyState state() const { return state_; }
  FaultCode fault() const { return fault_; }
  bool driversEnabled() const;
  bool requiresHoming() const { return requires_homing_; }

 private:
  void enterFault(FaultCode fault);

  SafetyState state_;
  FaultCode fault_;
  bool requires_homing_;
};
