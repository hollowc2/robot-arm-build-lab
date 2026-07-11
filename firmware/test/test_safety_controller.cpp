#include <cassert>
#include "safety_controller.h"

int main() {
  const SafetyInputs safe{true, true, true, false};
  SafetyController controller;
  assert(!controller.driversEnabled());
  assert(controller.requiresHoming());
  assert(!controller.requestMotion());
  assert(controller.requestHoming());
  assert(controller.driversEnabled());
  assert(controller.setHomingComplete());
  assert(controller.requestMotion());

  controller.update({true, false, true, false});
  assert(controller.state() == SafetyState::Fault);
  assert(controller.fault() == FaultCode::GuardOpen);
  assert(!controller.driversEnabled());
  assert(!controller.reset({true, false, true, false}));
  assert(controller.reset(safe));

  assert(controller.requestHoming());
  assert(controller.setHomingComplete());
  controller.update({false, true, true, false});
  assert(controller.state() == SafetyState::EmergencyStop);
  assert(!controller.driversEnabled());
  assert(controller.reset(safe));

  assert(controller.requestHoming());
  assert(controller.setHomingComplete());
  controller.update({true, true, false, false});
  assert(controller.fault() == FaultCode::CommunicationTimeout);
  assert(controller.reset(safe));
  assert(controller.requestHoming());
  assert(controller.setHomingComplete());
  controller.update({true, true, true, true});
  assert(controller.fault() == FaultCode::UnexpectedLimit);
}
