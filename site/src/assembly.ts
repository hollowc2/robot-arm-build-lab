// Installed CAD coordinates from master_assembly.py and forearm_link.py (mm).
// Keep the wrist group and assembly-space meshes on the same shaft axis.
export const elbowPivotZ = 337.38;
export const wristPivotZ = elbowPivotZ + 61 + 132.87553391244688;
export const wristPosition: [number, number, number] = [0, 0, wristPivotZ - elbowPivotZ];
export const wristMeshOffset: [number, number, number] = [0, 0, -wristPivotZ];
