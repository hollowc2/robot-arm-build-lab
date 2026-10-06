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

type Limits = { maxSpeed: number; acceleration: number };

// A coordinated move drives every joint from one shared progress value, so the joints start and
// arrive together and the arm follows a straight line in joint space. Short vertical moves then
// stay vertical, which matters when a brick slides down beside its neighbours.
export type JointMove<K extends string> = {
  from: Record<K, number>;
  delta: Record<K, number>;
  progress: number;
  velocity: number;
  limits: Limits;
};

export function planJointMove<K extends string>(
  from: Record<K, number>,
  to: Record<K, number>,
  limits: Record<K, Limits>,
  circular: readonly K[] = [],
): JointMove<K> {
  const joints = Object.keys(to) as K[];
  const delta = {} as Record<K, number>;
  let maxSpeed = Infinity;
  let acceleration = Infinity;
  for (const joint of joints) {
    delta[joint] = circular.includes(joint) ? ((to[joint] - from[joint] + 540) % 360) - 180 : to[joint] - from[joint];
    const distance = Math.abs(delta[joint]);
    if (distance < 1e-9) continue;
    // The slowest joint, scaled by how far it has to go, sets the pace for everyone.
    maxSpeed = Math.min(maxSpeed, limits[joint].maxSpeed / distance);
    acceleration = Math.min(acceleration, limits[joint].acceleration / distance);
  }
  const still = !Number.isFinite(maxSpeed);
  return {
    from: { ...from },
    delta,
    progress: still ? 1 : 0,
    velocity: 0,
    limits: still ? { maxSpeed: 1, acceleration: 1 } : { maxSpeed, acceleration },
  };
}

export function stepJointMove<K extends string>(
  move: JointMove<K>,
  seconds: number,
  pose: Record<K, number>,
  velocities: Record<K, number>,
  circular: readonly K[] = [],
) {
  [move.progress, move.velocity] = advanceMotion(move.progress, move.velocity, 1, move.limits.maxSpeed, move.limits.acceleration, seconds);
  for (const joint of Object.keys(move.delta) as K[]) {
    const value = move.from[joint] + move.delta[joint] * move.progress;
    pose[joint] = circular.includes(joint) ? (value % 360 + 360) % 360 : value;
    velocities[joint] = move.delta[joint] * move.velocity;
  }
  return move.progress === 1;
}
