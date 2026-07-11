#include "safety_controller.h"

SafetyController::SafetyController()
    : state_(SafetyState::BootDisabled), fault_(FaultCode::None), requires_homing_(true) {}

void SafetyController::enterFault(FaultCode fault) {
  state_ = SafetyState::Fault;
  fault_ = fault;
  requires_homing_ = true;
}

void SafetyController::update(const SafetyInputs& inputs) {
  if (!inputs.emergency_stop_ok) {
    state_ = SafetyState::EmergencyStop;
    fault_ = FaultCode::None;
    requires_homing_ = true;
    return;
  }
  if (!inputs.guards_closed) {
    enterFault(FaultCode::GuardOpen);
    return;
  }
  if ((state_ == SafetyState::Ready || state_ == SafetyState::Moving) &&
      !inputs.communication_ok) {
    enterFault(FaultCode::CommunicationTimeout);
    return;
  }
  if ((state_ == SafetyState::Ready || state_ == SafetyState::Moving) &&
      inputs.any_limit_open) {
    enterFault(FaultCode::UnexpectedLimit);
  }
}

bool SafetyController::requestHoming() {
  if (state_ != SafetyState::BootDisabled && state_ != SafetyState::Ready) return false;
  state_ = SafetyState::Homing;
  fault_ = FaultCode::None;
  return true;
}

bool SafetyController::setHomingComplete() {
  if (state_ != SafetyState::Homing) return false;
  state_ = SafetyState::Ready;
  requires_homing_ = false;
  return true;
}

bool SafetyController::setHomingFailed() {
  if (state_ != SafetyState::Homing) return false;
  enterFault(FaultCode::HomingFailed);
  return true;
}

bool SafetyController::requestMotion() {
  if (state_ != SafetyState::Ready || requires_homing_) return false;
  state_ = SafetyState::Moving;
  return true;
}

void SafetyController::setMotionComplete() {
  if (state_ == SafetyState::Moving) state_ = SafetyState::Ready;
}

bool SafetyController::reset(const SafetyInputs& inputs) {
  if (!inputs.emergency_stop_ok || !inputs.guards_closed) return false;
  state_ = SafetyState::BootDisabled;
  fault_ = FaultCode::None;
  requires_homing_ = true;
  return true;
}

bool SafetyController::driversEnabled() const {
  return state_ == SafetyState::Homing || state_ == SafetyState::Ready ||
         state_ == SafetyState::Moving;
}
