// One scaled clock drives the arm, gripper, bricks, physics and the build sequence. Simulated
// time advances in fixed steps, so a build follows exactly the same trajectory at any speed;
// speed only changes how many steps run per displayed frame.
export const simStep = 1 / 120;
export const speedRange = { min: 0.5, max: 4, step: 0.25, initial: 1 };
// Longest real frame we try to catch up on (a background tab, a GC pause). Anything beyond is
// dropped rather than replayed in a burst.
const maxFrameSeconds = 0.1;

export class SimClock {
  speed = speedRange.initial;
  paused = false;
  // Simulated seconds since the clock was created.
  elapsed = 0;
  private accumulator = 0;

  setSpeed(speed: number) {
    this.speed = Math.max(speedRange.min, Math.min(speedRange.max, speed));
  }

  // Runs the fixed steps owed for this frame and returns how far the clock sits between the last
  // two steps (0-1), for interpolating what is drawn.
  advance(realSeconds: number, tick: (seconds: number) => void) {
    if (!this.paused) this.accumulator += Math.min(Math.max(realSeconds, 0), maxFrameSeconds) * this.speed;
    const maxSteps = Math.ceil((maxFrameSeconds * speedRange.max) / simStep);
    let steps = 0;
    while (this.accumulator >= simStep && steps < maxSteps) {
      tick(simStep);
      this.accumulator -= simStep;
      this.elapsed += simStep;
      steps += 1;
    }
    if (steps === maxSteps) this.accumulator = Math.min(this.accumulator, simStep);
    return this.accumulator / simStep;
  }

  // Forget any partial step, e.g. after a reset, so nothing interpolates across the jump.
  settle() {
    this.accumulator = 0;
  }
}
