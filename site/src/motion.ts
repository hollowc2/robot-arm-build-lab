export function advanceMotion(
  position: number,
  velocity: number,
  target: number,
  maxSpeed: number,
  acceleration: number,
  seconds: number,
  circular = false,
): [number, number] {
  const distance = circular ? ((target - position + 540) % 360) - 180 : target - position;
  if (Math.abs(distance) < 0.001 && Math.abs(velocity) < 0.01) return [target, 0];

  const desiredVelocity = Math.sign(distance) * Math.min(maxSpeed, Math.sqrt(2 * acceleration * Math.abs(distance)));
  const velocityChange = Math.max(-acceleration * seconds, Math.min(acceleration * seconds, desiredVelocity - velocity));
  const nextVelocity = velocity + velocityChange;
  const nextPosition = position + nextVelocity * seconds;

  if (distance && Math.sign(distance - nextVelocity * seconds) !== Math.sign(distance)) return [target, 0];
  return [circular ? (nextPosition + 360) % 360 : nextPosition, nextVelocity];
}
