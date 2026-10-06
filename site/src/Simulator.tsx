import React, { useEffect, useRef, useState } from "react";
import * as CANNON from "cannon-es";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { RoomEnvironment } from "three/examples/jsm/environments/RoomEnvironment.js";
import { STLLoader } from "three/examples/jsm/loaders/STLLoader.js";
import { toCreasedNormals } from "three/examples/jsm/utils/BufferGeometryUtils.js";
import { jawAngle, jawPivotX, jawPivotY, linkagePose, releaseTravel } from "./gripper";
import { advanceMotion } from "./motion";
import { wristPosition as wristJointPosition, wristMeshOffset } from "./assembly";
import { graspTravel, type GraspShape, type JawSurface } from "./grasp";
import {
  disposeObject,
  generatedBase,
  guardWheelZoom,
  pageBackground,
  prefersReducedMotion,
  radialGlowTexture,
  watchVisibility,
} from "./shared";

type JointAngles = {
  base: number;
  shoulder: number;
  elbow: number;
  wrist: number;
  gripper: number;
};
type JointName = keyof JointAngles;
type Mode = "loading" | "autopilot" | "manual";

const homePose: JointAngles = { base: 0, shoulder: 0, elbow: 0, wrist: 0, gripper: 0 };
const jointLimits: Record<JointName, [number, number]> = {
  base: [0, 360],
  shoulder: [-130, 130],
  elbow: [-135, 135],
  wrist: [-150, 18],
  gripper: [0, 40],
};
// Real hardware will vary; keep these two limits per joint easy to calibrate.
const jointMotion: Record<JointName, { maxSpeed: number; acceleration: number }> = {
  base: { maxSpeed: 90, acceleration: 180 },
  shoulder: { maxSpeed: 70, acceleration: 140 },
  elbow: { maxSpeed: 80, acceleration: 160 },
  wrist: { maxSpeed: 100, acceleration: 200 },
  gripper: { maxSpeed: 16, acceleration: 32 },
};
const jointNames = Object.keys(homePose) as JointName[];
const jointControls: { name: JointName; id: string; label: string; unit: string }[] = [
  { name: "base", id: "J1", label: "Base", unit: "°" },
  { name: "shoulder", id: "J2", label: "Shoulder", unit: "°" },
  { name: "elbow", id: "J3", label: "Elbow", unit: "°" },
  { name: "wrist", id: "J4", label: "Wrist", unit: "°" },
  { name: "gripper", id: "J5", label: "Grip", unit: " mm" },
];
const meshCount = 35;
const palette = {
  arm: "#e2743f",
  frame: "#4a535b",
  hardware: "#9aa5ad",
  pulley: "#e7b84b",
  gripper: "#5fb3a9",
};
// Purchased-part finishes exported beside each rigid link as `${link}_${finish}.stl`.
type Finish = "motor_case" | "motor_stack" | "motor_connector" | "steel";
const nema17Finishes: Finish[] = ["motor_case", "motor_stack", "motor_connector", "steel"];

function clampJoint(name: JointName, value: number) {
  const [min, max] = jointLimits[name];
  return Math.max(min, Math.min(max, value));
}

export type TitleBlockFact = [label: string, value: string];

export function Simulator({ children, facts }: { children: React.ReactNode; facts: TitleBlockFact[] }) {
  const mountRef = useRef<HTMLDivElement | null>(null);
  const readoutRefs = useRef<Partial<Record<JointName, HTMLSpanElement | null>>>({});
  const tipRef = useRef<HTMLSpanElement | null>(null);
  const jointsRef = useRef({ ...homePose });
  const targetsRef = useRef({ ...homePose });
  const velocitiesRef = useRef({ ...homePose });
  const actionsRef = useRef<Record<"takeManual" | "toggleAutopilot" | "resetBlocks", () => void>>({
    takeManual: () => undefined,
    toggleAutopilot: () => undefined,
    resetBlocks: () => undefined,
  });
  const [targets, setTargets] = useState({ ...homePose });
  const [loaded, setLoaded] = useState(0);
  const [mode, setMode] = useState<Mode>("loading");
  const [demoLabel, setDemoLabel] = useState<string | null>(null);
  const [heldName, setHeldName] = useState<string | null>(null);
  const [reach, setReach] = useState<number | null>(null);

  useEffect(() => {
    if (!mountRef.current) return undefined;
    const mount = mountRef.current;
    let frame = 0;
    let disposed = false;
    let visible = true;
    let loadedCount = 0;
    let autopilot = !prefersReducedMotion();
    setLoaded(0);
    setMode("loading");

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(pageBackground);
    scene.fog = new THREE.Fog(pageBackground, 1700, 3400);
    const camera = new THREE.PerspectiveCamera(32, 1, 1, 6000);
    camera.up.set(0, 0, 1);
    camera.position.set(700, -720, 560);
    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    mount.appendChild(renderer.domElement);
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.target.set(0, 0, 270);
    controls.enableDamping = true;
    controls.dampingFactor = 0.08;
    controls.enablePan = false;
    controls.minDistance = 320;
    controls.maxDistance = 2600;
    controls.maxPolarAngle = Math.PI * 0.53;
    const stopWheelGuard = guardWheelZoom(mount, controls);
    const stopWatching = watchVisibility(mount, (isVisible) => {
      visible = isVisible;
    });

    scene.add(new THREE.HemisphereLight("#fff3e6", "#15181b", 1.7));
    // Metals need something to reflect. Only the purchased-part finishes use it, so the
    // printed plastic keeps its existing lighting.
    const pmrem = new THREE.PMREMGenerator(renderer);
    const reflections = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
    pmrem.dispose();
    const finishes: Record<Finish, THREE.MeshStandardMaterial> = {
      // Black anodized aluminium end bells.
      motor_case: new THREE.MeshStandardMaterial({ color: "#1c1e21", roughness: 0.42, metalness: 0.6, envMap: reflections, envMapIntensity: 0.7 }),
      // Laminated silicon-steel stator stack.
      motor_stack: new THREE.MeshStandardMaterial({ color: "#aeb3b8", roughness: 0.36, metalness: 0.9, envMap: reflections }),
      // White JST-PH connector housing.
      motor_connector: new THREE.MeshStandardMaterial({ color: "#eee8d8", roughness: 0.6, metalness: 0 }),
      // Polished steel shafts and fasteners.
      steel: new THREE.MeshStandardMaterial({ color: "#eef1f4", roughness: 0.16, metalness: 1, envMap: reflections, envMapIntensity: 1.2 }),
    };
    const key = new THREE.DirectionalLight("#ffffff", 2.6);
    key.position.set(320, -420, 900);
    key.castShadow = true;
    key.shadow.mapSize.set(2048, 2048);
    Object.assign(key.shadow.camera, { left: -620, right: 620, top: 620, bottom: -620, near: 200, far: 2000 });
    key.shadow.bias = -0.0006;
    key.shadow.normalBias = 1.2;
    scene.add(key);
    const rim = new THREE.DirectionalLight("#86b4ff", 1.5);
    rim.position.set(-640, 560, 380);
    scene.add(rim);

    const glow = new THREE.Mesh(
      new THREE.CircleGeometry(900, 96),
      new THREE.MeshBasicMaterial({ map: radialGlowTexture("#1b1f23", pageBackground), depthWrite: false }),
    );
    glow.position.z = -1.2;
    scene.add(glow);
    const grid = new THREE.GridHelper(3000, 100, "#2a3036", "#1a1e22");
    grid.rotation.x = Math.PI / 2;
    grid.position.z = -0.6;
    scene.add(grid);
    const shadowFloor = new THREE.Mesh(new THREE.PlaneGeometry(2400, 2400), new THREE.ShadowMaterial({ opacity: 0.42 }));
    shadowFloor.receiveShadow = true;
    shadowFloor.position.z = -0.2;
    scene.add(shadowFloor);

    const world = new CANNON.World({ gravity: new CANNON.Vec3(0, 0, -981) });
    world.allowSleep = true;
    world.broadphase = new CANNON.SAPBroadphase(world);
    world.defaultContactMaterial.friction = 0.55;
    world.defaultContactMaterial.restitution = 0.18;
    // Resolve the extra simultaneous contacts in a stack without accumulating sideways drift.
    (world.solver as CANNON.GSSolver).iterations = 40;
    world.addBody(new CANNON.Body({ mass: 0, shape: new CANNON.Plane() }));

    const robotRoot = new THREE.Group();
    scene.add(robotRoot);
    const jawSurfaces: JawSurface[] = [];
    const base = new THREE.Group();
    const shoulder = new THREE.Group();
    const elbow = new THREE.Group();
    const wrist = new THREE.Group();
    const leftJaw = new THREE.Group();
    const rightJaw = new THREE.Group();
    const jawLinks = ([-1, 1] as const).map((side) => {
      const jaw = side < 0 ? leftJaw : rightJaw;
      jaw.position.set(side * jawPivotX, jawPivotY, 0);
      const horn = new THREE.Group();
      horn.position.set(side * jawPivotX, 49.5, 0);
      const rod = new THREE.Group();
      wrist.add(horn, rod);
      return { side, jaw, horn, rod };
    });
    shoulder.position.set(0, 0, 162.03);
    elbow.position.set(0, 0, 175.35);
    wrist.position.set(...wristJointPosition);
    robotRoot.add(base);
    base.add(shoulder);
    shoulder.add(elbow);
    elbow.add(wrist);
    wrist.add(leftJaw, rightJaw);
    const gripPoint = new THREE.Object3D();
    gripPoint.position.set(0, 124, 14);
    wrist.add(gripPoint);

    const demoBase = new THREE.Group();
    const demoShoulder = new THREE.Group();
    const demoElbow = new THREE.Group();
    const demoWrist = new THREE.Group();
    const demoGrip = new THREE.Object3D();
    demoShoulder.position.copy(shoulder.position);
    demoElbow.position.copy(elbow.position);
    demoWrist.position.copy(wrist.position);
    demoGrip.position.copy(gripPoint.position);
    demoBase.add(demoShoulder);
    demoShoulder.add(demoElbow);
    demoElbow.add(demoWrist);
    demoWrist.add(demoGrip);

    const movingMeshes: THREE.Mesh[] = [];
    const loader = new STLLoader();
    const loadGeometry = (name: string, onLoad: (geometry: THREE.BufferGeometry) => void) => {
      loader.load(`${generatedBase}/models/${name}.stl`, (raw) => {
        if (disposed) {
          raw.dispose();
          return;
        }
        const geometry = toCreasedNormals(raw, Math.PI / 6);
        raw.dispose();
        geometry.computeBoundingBox();
        onLoad(geometry);
        loadedCount += 1;
        setLoaded(loadedCount);
        if (loadedCount === meshCount) {
          setMode(autopilot ? "autopilot" : "manual");
          updateReach();
          if (autopilot) startDemo();
        }
      });
    };
    const addMesh = (mesh: THREE.Mesh, parent: THREE.Object3D) => {
      mesh.castShadow = true;
      parent.add(mesh);
      if (parent !== robotRoot && parent !== base) movingMeshes.push(mesh);
      if (parent === leftJaw || parent === rightJaw) jawSurfaces.push({ geometry: mesh.geometry, side: parent === leftJaw ? -1 : 1 });
    };
    const load = (name: string, parent: THREE.Object3D, offset: [number, number, number], material: string | THREE.Material = palette.arm) => {
      loadGeometry(name, (geometry) => {
        const mesh = new THREE.Mesh(geometry, typeof material === "string"
          ? new THREE.MeshStandardMaterial({ color: material, roughness: 0.56, metalness: 0.06 })
          : material);
        mesh.position.set(...offset);
        addMesh(mesh, parent);
      });
    };
    const loadFinishes = (name: string, parent: THREE.Object3D, offset: [number, number, number], kinds: Finish[]) => {
      kinds.forEach((kind) => load(`${name}_${kind}`, parent, offset, finishes[kind]));
    };
    const loadPulley = (name: string, parent: THREE.Object3D, offset: [number, number, number]) => {
      const pivot = new THREE.Group();
      parent.add(pivot);
      loadGeometry(name, (geometry) => {
        const center = geometry.boundingBox!.getCenter(new THREE.Vector3());
        pivot.position.copy(center).add(new THREE.Vector3(...offset));
        const mesh = new THREE.Mesh(geometry, new THREE.MeshStandardMaterial({ color: palette.pulley, roughness: 0.45, metalness: 0.2 }));
        mesh.position.copy(center).multiplyScalar(-1);
        mesh.castShadow = true;
        pivot.add(mesh);
        if (parent !== base) movingMeshes.push(mesh);
      });
      return pivot;
    };
    const belt = (name: string, parent: THREE.Object3D, offset: [number, number, number]) => {
      const phase = { value: 0 };
      load(name, parent, offset, new THREE.ShaderMaterial({
        uniforms: { phase, beltColor: { value: new THREE.Color("#0a0a0a") } },
        vertexShader: "varying vec3 p; void main(){p=position;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0);}",
        fragmentShader: "uniform float phase;uniform vec3 beltColor;varying vec3 p;void main(){float stripe=step(.5,fract((p.y+p.z)/6.0+phase));gl_FragColor=vec4(beltColor+stripe*.05,1.0);}",
      }));
      return phase;
    };
    loadGeometry("simulator_base_fixed", (geometry) => {
      // The assembly origin is above the feet. Move the entire mechanism and IK model
      // together so the lowest grey support rests on the same z=0 floor as the props.
      robotRoot.position.z = -geometry.boundingBox!.min.z;
      demoBase.position.z = robotRoot.position.z;
      addMesh(new THREE.Mesh(geometry, new THREE.MeshStandardMaterial({ color: palette.frame, roughness: 0.56, metalness: 0.06 })), robotRoot);
    });
    loadFinishes("simulator_base_fixed", robotRoot, [0, 0, 0], nema17Finishes);
    load("simulator_base_yaw", base, [0, 0, 0]);
    loadFinishes("simulator_base_yaw", base, [0, 0, 0], nema17Finishes);
    load("simulator_upper_arm", shoulder, [0, 0, -162.03]);
    loadFinishes("simulator_upper_arm", shoulder, [0, 0, -162.03], nema17Finishes);
    load("simulator_forearm", elbow, [0, 0, -337.38]);
    loadFinishes("simulator_forearm", elbow, [0, 0, -337.38], ["steel"]);
    load("simulator_wrist_hardware", wrist, wristMeshOffset, palette.hardware);
    loadFinishes("simulator_wrist_hardware", wrist, wristMeshOffset, ["steel"]);
    load("simulator_gripper_base", wrist, [0, 0, 0], palette.gripper);
    jawLinks.forEach(({ side, jaw, horn, rod }) => {
      const name = side < 0 ? "left" : "right";
      load(`simulator_gripper_${name}`, jaw, [-side * jawPivotX, -jawPivotY, 0], palette.gripper);
      load(`simulator_gripper_${name}_horn`, horn, [-side * jawPivotX, -49.5, 0], palette.gripper);
      load(`simulator_gripper_${name}_rod`, rod, [-side * 17.5, -65, 0], palette.gripper);
    });
    const shoulderDriver = loadPulley("simulator_shoulder_driver", base, [0, 0, 0]);
    loadPulley("simulator_shoulder_driven", shoulder, [0, 0, -162.03]);
    const shoulderBelt = belt("simulator_shoulder_belt", base, [0, 0, 0]);
    const elbowDriver = loadPulley("simulator_elbow_driver", shoulder, [0, 0, -162.03]);
    loadPulley("simulator_elbow_driven", elbow, [0, 0, -337.38]);
    const elbowBelt = belt("simulator_elbow_belt", shoulder, [0, 0, -162.03]);
    const wristDriver = loadPulley("simulator_wrist_driver", elbow, [0, 0, -337.38]);
    loadPulley("simulator_wrist_driven", wrist, wristMeshOffset);
    const wristBelt = belt("simulator_wrist_belt", elbow, [0, 0, -337.38]);

    const robotColliders: { marker: THREE.Object3D; body: CANNON.Body }[] = [];
    const addRobotCollider = (parent: THREE.Object3D, position: [number, number, number], shape: CANNON.Shape) => {
      const marker = new THREE.Object3D();
      marker.position.set(...position);
      parent.add(marker);
      const body = new CANNON.Body({ mass: 0, type: CANNON.Body.KINEMATIC, shape });
      body.collisionFilterGroup = 2;
      world.addBody(body);
      robotColliders.push({ marker, body });
    };
    addRobotCollider(robotRoot, [0, 0, 70], new CANNON.Cylinder(65, 65, 140, 16));
    addRobotCollider(shoulder, [0, 0, 88], new CANNON.Box(new CANNON.Vec3(28, 24, 88)));
    addRobotCollider(elbow, [0, 0, 84], new CANNON.Box(new CANNON.Vec3(24, 22, 84)));
    addRobotCollider(wrist, [0, 28, 4], new CANNON.Box(new CANNON.Vec3(20, 38, 17)));
    addRobotCollider(leftJaw, [3.8, 54, 14.5], new CANNON.Box(new CANNON.Vec3(1.2, 7, 4)));
    addRobotCollider(rightJaw, [-3.8, 54, 14.5], new CANNON.Box(new CANNON.Vec3(1.2, 7, 4)));

    type PhysicsProp = {
      name: string;
      mesh: THREE.Mesh;
      body: CANNON.Body;
      mass: number;
      start: [number, number, number];
      graspShape: GraspShape;
    };
    const props: PhysicsProp[] = [];
    const addProp = (
      name: string,
      geometry: THREE.BufferGeometry,
      shape: CANNON.Shape,
      start: [number, number, number],
      color: string,
      mass = 0.06,
    ) => {
      const mesh = new THREE.Mesh(geometry, new THREE.MeshStandardMaterial({ color, roughness: 0.5, metalness: 0.02 }));
      mesh.castShadow = true;
      scene.add(mesh);
      const body = new CANNON.Body({ mass, shape, position: new CANNON.Vec3(...start) });
      body.linearDamping = 0.08;
      body.angularDamping = 0.12;
      // The world is in millimetres, so the default 0.1 unit/s sleep threshold never trips and a
      // resting stack slowly jitters apart. Let settled props sleep instead.
      body.allowSleep = true;
      body.sleepSpeedLimit = 3;
      body.sleepTimeLimit = 0.5;
      world.addBody(body);
      const graspShape: GraspShape = shape instanceof CANNON.Box
        ? { halfExtents: new THREE.Vector3(shape.halfExtents.x, shape.halfExtents.y, shape.halfExtents.z) }
        : { radius: (shape as CANNON.Sphere).radius };
      props.push({ name, mesh, body, mass, start, graspShape });
    };
    const cubeShape = new CANNON.Box(new CANNON.Vec3(12, 11, 11));
    addProp("orange block", new THREE.BoxGeometry(24, 22, 22), cubeShape, [90, 145, 11], "#f28c5a");
    addProp("blue block", new THREE.BoxGeometry(24, 22, 22), cubeShape, [-85, 150, 11], "#4ea5d9");
    addProp("yellow block", new THREE.BoxGeometry(24, 22, 22), cubeShape, [135, 70, 11], "#f4d35e");
    addProp("green block", new THREE.BoxGeometry(24, 22, 22), cubeShape, [-130, 75, 11], "#70c1b3");
    addProp("red ball", new THREE.SphereGeometry(9, 24, 16), new CANNON.Sphere(9), [150, -40, 9], "#ee6055", 0.04);

    let held: PhysicsProp | null = null;
    let heldTravel = 0;
    const heldPosition = new THREE.Vector3();
    const heldQuaternion = new THREE.Quaternion();
    const localPosition = new THREE.Vector3();
    const localQuaternion = new THREE.Quaternion();
    const inverseWrist = new THREE.Quaternion();
    const wristPosition = new THREE.Vector3();
    const carriedPosition = new THREE.Vector3();
    const carriedQuaternion = new THREE.Quaternion();
    const gripPosition = new THREE.Vector3();
    const previousGripPosition = new THREE.Vector3();
    const gripQuaternion = new THREE.Quaternion();
    const gripVelocity = new THREE.Vector3();
    const markerPosition = new THREE.Vector3();
    const markerQuaternion = new THREE.Quaternion();
    const floorBounds = new THREE.Box3();
    type DemoStep = { label: string; target: JointAngles; pause: number; settledAt?: number };
    let demo: { steps: DemoStep[]; index: number } | null = null;
    let demoSteps: DemoStep[] | null = null;
    let finishedAt = 0;
    const release = () => {
      if (!held) return;
      held.body.collisionFilterMask = -1;
      held.body.type = CANNON.Body.DYNAMIC;
      held.body.mass = held.mass;
      held.body.updateMassProperties();
      held.body.velocity.set(gripVelocity.x, gripVelocity.y, gripVelocity.z);
      held.body.wakeUp();
      held = null;
      setHeldName(null);
    };
    const resetObjects = () => {
      demo = null;
      release();
      props.forEach((prop) => {
        prop.body.type = CANNON.Body.DYNAMIC;
        prop.body.mass = prop.mass;
        prop.body.updateMassProperties();
        prop.body.position.set(...prop.start);
        prop.body.quaternion.set(0, 0, 0, 1);
        prop.body.velocity.setZero();
        prop.body.angularVelocity.setZero();
        prop.body.wakeUp();
      });
    };
    let motionBlocked = false;
    let stepSeconds = 0;

    const normalizeBase = (value: number) => (value % 360 + 360) % 360;
    const probePosition = new THREE.Vector3();
    const probeJoint = new THREE.Vector3();
    const probe = (pose: JointAngles) => {
      demoBase.rotation.z = THREE.MathUtils.degToRad(-pose.base);
      demoShoulder.rotation.x = THREE.MathUtils.degToRad(-pose.shoulder);
      demoElbow.rotation.x = THREE.MathUtils.degToRad(pose.elbow);
      demoWrist.rotation.x = THREE.MathUtils.degToRad(-pose.wrist);
      demoBase.updateMatrixWorld(true);
      return probePosition.setFromMatrixPosition(demoGrip.matrixWorld);
    };
    // Position error plus two soft preferences: the gripper points straight down, and the
    // elbow and wrist housings stay well clear of the table.
    const demoCost = (pose: JointAngles, target: THREE.Vector3) => {
      const error = probe(pose).distanceToSquared(target);
      const tilt = ((-pose.shoulder + pose.elbow - pose.wrist + 90 + 540) % 360) - 180;
      const elbowClearance = Math.max(0, 90 - probeJoint.setFromMatrixPosition(demoElbow.matrixWorld).z);
      const wristClearance = Math.max(0, 90 - probeJoint.setFromMatrixPosition(demoWrist.matrixWorld).z);
      return { error, cost: error + 2 * tilt ** 2 + elbowClearance ** 2 + wristClearance ** 2 };
    };
    // Seed from the previous pose and, among accurate solutions, prefer the one with the least
    // joint travel so consecutive steps stay on the same elbow branch instead of flipping.
    const solveDemoPose = (target: THREE.Vector3, gripper: number, previous: JointAngles) => {
      const base = normalizeBase(THREE.MathUtils.radToDeg(Math.atan2(target.x, target.y)));
      const solutions: { pose: JointAngles; error: number; cost: number; travel: number }[] = [];
      for (const seed of [[previous.shoulder, previous.elbow, previous.wrist], [45, -110, -48], [30, -130, -66], [-125, 125, -100]]) {
        let candidate: JointAngles = { base, shoulder: seed[0], elbow: seed[1], wrist: seed[2], gripper };
        for (const step of [24, 8, 2, 0.5]) {
          for (let round = 0; round < 12; round += 1) {
            for (const joint of ["base", "shoulder", "elbow", "wrist"] as const) {
              let best = candidate;
              let bestCost = demoCost(candidate, target).cost;
              for (const delta of [-step, step]) {
                const value = joint === "base" ? normalizeBase(candidate[joint] + delta) : clampJoint(joint, candidate[joint] + delta);
                const next = { ...candidate, [joint]: value };
                const { cost } = demoCost(next, target);
                if (cost < bestCost) {
                  best = next;
                  bestCost = cost;
                }
              }
              candidate = best;
            }
          }
        }
        const travel = (["shoulder", "elbow", "wrist"] as const)
          .reduce((sum, joint) => sum + Math.abs(candidate[joint] - previous[joint]), 0);
        solutions.push({ pose: candidate, ...demoCost(candidate, target), travel });
      }
      const accurate = solutions.filter((solution) => solution.error < 4);
      const rank = (solution: (typeof solutions)[number]) => (accurate.length ? solution.cost + 0.1 * solution.travel : solution.cost);
      return (accurate.length ? accurate : solutions).reduce((best, solution) => (rank(solution) < rank(best) ? solution : best)).pose;
    };

    const updateReach = () => {
      let maxReach = 0;
      for (let s = -130; s <= 130; s += 5) {
        for (let e = -135; e <= 135; e += 5) {
          for (let w = -150; w <= 18; w += 12) {
            const tip = probe({ base: 0, shoulder: s, elbow: e, wrist: w, gripper: 0 });
            if (tip.z >= 0) maxReach = Math.max(maxReach, Math.hypot(tip.x, tip.y));
          }
        }
      }

      const reachRing = new THREE.Group();
      reachRing.add(new THREE.Mesh(
        new THREE.RingGeometry(maxReach - 1.2, maxReach + 1.2, 180),
        new THREE.MeshBasicMaterial({ color: "#ff7a45", transparent: true, opacity: 0.55, depthWrite: false }),
      ));
      const tickPoints: number[] = [];
      for (let degrees = 0; degrees < 360; degrees += 10) {
        const angle = THREE.MathUtils.degToRad(degrees);
        const length = degrees % 90 === 0 ? 34 : degrees % 30 === 0 ? 18 : 9;
        tickPoints.push(
          Math.cos(angle) * maxReach, Math.sin(angle) * maxReach, 0,
          Math.cos(angle) * (maxReach - length), Math.sin(angle) * (maxReach - length), 0,
        );
      }
      const ticks = new THREE.BufferGeometry();
      ticks.setAttribute("position", new THREE.Float32BufferAttribute(tickPoints, 3));
      reachRing.add(new THREE.LineSegments(ticks, new THREE.LineBasicMaterial({ color: "#ff7a45", transparent: true, opacity: 0.45 })));
      reachRing.position.z = 0.4;
      scene.add(reachRing);
      setReach(Math.round(maxReach / 10) * 10);
    };

    const atTarget = (pose: JointAngles, target: JointAngles) => jointNames.every((name) => {
      const difference = name === "base"
        ? Math.abs(((pose.base - target.base + 540) % 360) - 180)
        : Math.abs(pose[name] - (name === "gripper" && held ? Math.max(target[name], heldTravel) : target[name]));
      return difference < 1.2;
    });
    const stack: [number, number] = [0, 150];
    const buildDemoSteps = () => {
      const blocks = props.filter((prop) => prop.name.endsWith("block"));
      const steps: DemoStep[] = [
        { label: "Opening the gripper", target: { ...homePose, gripper: 40 }, pause: 500 },
      ];
      const makeDemoStep = (label: string, point: [number, number, number], gripper: number, pause = 220): DemoStep => ({
        label,
        target: solveDemoPose(new THREE.Vector3(...point), gripper, steps.at(-1)!.target),
        pause,
      });
      blocks.forEach((block, index) => {
        const [x, y] = block.start;
        // Preserve the pickup offset and release each block a few millimetres above its layer.
        const height = 20 + index * 22;
        steps.push(makeDemoStep(`Reaching for the ${block.name}`, [x, y, 88], 40));
        steps.push(makeDemoStep(`Lowering onto the ${block.name}`, [x, y, 18], 40));
        steps.push(makeDemoStep(`Gripping the ${block.name}`, [x, y, 18], 0, 650));
        steps.push(makeDemoStep(`Lifting the ${block.name}`, [x, y, 88], 0));
        steps.push(makeDemoStep(`Carrying the ${block.name} over`, [stack[0], stack[1], height + 70], 0));
        steps.push(makeDemoStep(`Placing the ${block.name}`, [stack[0], stack[1], height], 0, 280));
        steps.push(makeDemoStep(`Releasing the ${block.name}`, [stack[0], stack[1], height], 40, 900));
        // Lift straight off before moving on; sliding sideways would drag the open jaws through the stack.
        steps.push(makeDemoStep("Backing away", [stack[0], stack[1], height + 70], 40, 120));
      });
      const ball = props.find((prop) => prop.name === "red ball")!;
      const [ballX, ballY] = ball.start;
      steps.push(makeDemoStep("Reaching for the red ball", [ballX, ballY, 88], 40));
      steps.push(makeDemoStep("Lowering onto the red ball", [ballX, ballY, 18], 40));
      steps.push(makeDemoStep("Gripping the red ball", [ballX, ballY, 18], 0, 650));
      steps.push(makeDemoStep("Lifting the red ball", [ballX, ballY, 170], 0));
      steps.push(makeDemoStep("Carrying the red ball over", [stack[0], stack[1], 170], 0));
      // Keep the ball and finger tips clear of the completed stack before releasing.
      steps.push(makeDemoStep("Balancing the red ball", [stack[0], stack[1], 110], 0, 300));
      steps.push(makeDemoStep("Letting go", [stack[0], stack[1], 110], 40, 1400));
      steps.push(makeDemoStep("Backing away", [stack[0], stack[1], 220], 40, 400));
      return steps;
    };
    const describeStack = () => {
      const onStack = (prop: PhysicsProp) => Math.hypot(prop.body.position.x - stack[0], prop.body.position.y - stack[1]) < 15;
      const blocks = props.filter((prop) => prop.name.endsWith("block"));
      const ball = props.find((prop) => prop.name === "red ball")!;
      if (!blocks.every(onStack)) return "The stack toppled, trying again";
      return onStack(ball) && ball.body.position.z > 80 ? "Four blocks stacked, ball balanced" : "Four blocks stacked, the ball rolled off";
    };
    const setTargetPose = (pose: JointAngles) => {
      targetsRef.current = { ...pose };
      setTargets({ ...pose });
    };
    const startDemo = () => {
      resetObjects();
      demoSteps ??= buildDemoSteps();
      demo = { steps: demoSteps.map((step) => ({ ...step, settledAt: undefined })), index: 0 };
      stepSeconds = 0;
      finishedAt = 0;
      setTargetPose(demo.steps[0].target);
      setDemoLabel(demo.steps[0].label);
    };
    const takeManual = () => {
      if (!autopilot && !demo) return;
      autopilot = false;
      demo = null;
      finishedAt = 0;
      setDemoLabel(null);
      if (loadedCount === meshCount) setMode("manual");
    };
    actionsRef.current = {
      takeManual,
      toggleAutopilot: () => {
        if (autopilot) {
          takeManual();
          const pose = jointsRef.current;
          setTargetPose({ ...pose, base: Math.round(pose.base) % 360, shoulder: Math.round(pose.shoulder), elbow: Math.round(pose.elbow), wrist: Math.round(pose.wrist), gripper: Math.round(pose.gripper) });
        } else {
          autopilot = true;
          setMode("autopilot");
          startDemo();
        }
      },
      resetBlocks: () => (autopilot ? startDemo() : resetObjects()),
    };

    const applyPose = (pose: JointAngles) => {
      base.rotation.z = THREE.MathUtils.degToRad(-pose.base);
      shoulder.rotation.x = THREE.MathUtils.degToRad(-pose.shoulder);
      elbow.rotation.x = THREE.MathUtils.degToRad(pose.elbow);
      wrist.rotation.x = THREE.MathUtils.degToRad(-pose.wrist);
      shoulderDriver.rotation.x = THREE.MathUtils.degToRad(-pose.shoulder * 5);
      elbowDriver.rotation.x = THREE.MathUtils.degToRad(pose.elbow * 3.75);
      wristDriver.rotation.x = THREE.MathUtils.degToRad(-pose.wrist * 1.6);
      shoulderBelt.value = -pose.shoulder * 16 / 360;
      elbowBelt.value = pose.elbow * 16 / 360;
      wristBelt.value = -pose.wrist * 20 / 360;
      jawLinks.forEach(({ side, jaw, horn, rod }) => {
        jaw.rotation.z = jawAngle(pose.gripper, side);
        const linkage = linkagePose(pose.gripper, side);
        horn.rotation.z = linkage.hornAngle;
        rod.position.copy(linkage.hornEnd);
        rod.rotation.z = linkage.rodAngle;
      });
      scene.updateMatrixWorld(true);
    };

    const shownReadouts: Partial<Record<JointName | "tip", string>> = {};
    let lastTipUpdate = 0;
    const writeReadouts = (pose: JointAngles, time: number) => {
      jointControls.forEach(({ name, unit }) => {
        const node = readoutRefs.current[name];
        const text = `${Math.round(name === "base" ? pose.base % 360 : pose[name])}${unit}`;
        if (node && shownReadouts[name] !== text) {
          node.textContent = text;
          shownReadouts[name] = text;
        }
      });
      if (tipRef.current && time - lastTipUpdate > 90) {
        lastTipUpdate = time;
        const text = `x ${Math.round(gripPosition.x)}  y ${Math.round(gripPosition.y)}  z ${Math.round(gripPosition.z)}`;
        if (shownReadouts.tip !== text) {
          tipRef.current.textContent = text;
          shownReadouts.tip = text;
        }
      }
    };

    const resize = () => {
      const width = mount.clientWidth;
      const height = mount.clientHeight;
      if (!width || !height) return;
      renderer.setSize(width, height);
      camera.aspect = width / height;
      // On wide screens the controls sit on the left, so slide the arm into the open space.
      const shift = width >= 1000 ? Math.min(250, width * 0.16) : 0;
      if (shift) camera.setViewOffset(width, height, -shift, 0, width, height);
      else camera.clearViewOffset();
      const distance = width / height < 0.9 ? 1500 : 1600;
      camera.position.sub(controls.target).setLength(distance).add(controls.target);
      camera.updateProjectionMatrix();
    };
    const resizeObserver = new ResizeObserver(resize);
    resizeObserver.observe(mount);
    resize();

    let lastTime = performance.now();
    let lastGamepadUpdate = 0;
    const render = (time = performance.now()) => {
      frame = requestAnimationFrame(render);
      const elapsed = Math.min((time - lastTime) / 1000, 0.05);
      lastTime = time;
      if (!visible) return;
      const gamepad = navigator.getGamepads?.().find((pad) => pad?.connected);
      if (gamepad) {
        const axis = (index: number) => Math.abs(gamepad.axes[index] ?? 0) > 0.12 ? gamepad.axes[index] : 0;
        const trigger = (gamepad.buttons[7]?.value ?? 0) - (gamepad.buttons[6]?.value ?? 0);
        const homePressed = gamepad.buttons[0]?.pressed ?? false;
        if ([0, 1, 2, 3].some((index) => axis(index) !== 0) || Math.abs(trigger) > 0.05 || homePressed) {
          takeManual();
          const next = targetsRef.current;
          next.base = (next.base + axis(0) * 100 * elapsed + 360) % 360;
          next.shoulder = clampJoint("shoulder", next.shoulder - axis(1) * 80 * elapsed);
          next.wrist = clampJoint("wrist", next.wrist + axis(2) * 80 * elapsed);
          next.elbow = clampJoint("elbow", next.elbow - axis(3) * 80 * elapsed);
          next.gripper = clampJoint("gripper", next.gripper + trigger * 18 * elapsed);
          if (homePressed) Object.assign(next, homePose);
          if (time - lastGamepadUpdate > 100) {
            setTargets({ ...next });
            lastGamepadUpdate = time;
          }
        }
      }
      const pose = jointsRef.current;
      const velocities = velocitiesRef.current;
      const previousPose = { ...pose };
      jointNames.forEach((name) => {
        [pose[name], velocities[name]] = advanceMotion(
          pose[name], velocities[name], targetsRef.current[name],
          jointMotion[name].maxSpeed, jointMotion[name].acceleration, elapsed, name === "base",
        );
      });
      applyPose(pose);
      const hitFloor = movingMeshes.some((mesh) => {
        if (!mesh.geometry.boundingBox) return false;
        return floorBounds.copy(mesh.geometry.boundingBox).applyMatrix4(mesh.matrixWorld).min.z < 0;
      });
      if (hitFloor) {
        Object.assign(pose, previousPose);
        Object.assign(velocities, homePose);
        targetsRef.current = { ...previousPose };
        if (!motionBlocked) setTargets({ ...previousPose });
        motionBlocked = true;
        applyPose(pose);
      } else motionBlocked = false;

      gripPoint.getWorldPosition(gripPosition);
      gripPoint.getWorldQuaternion(gripQuaternion);
      gripVelocity.copy(gripPosition).sub(previousGripPosition).divideScalar(Math.max(elapsed, 1 / 120));
      previousGripPosition.copy(gripPosition);
      wrist.getWorldPosition(wristPosition);
      inverseWrist.copy(gripQuaternion).invert();
      if (held && pose.gripper >= releaseTravel(heldTravel, jointLimits.gripper[1])) release();
      if (!held && targetsRef.current.gripper < previousPose.gripper && pose.gripper < previousPose.gripper) {
        for (const prop of props) {
          if (prop.body.type !== CANNON.Body.DYNAMIC) continue;
          localPosition.set(prop.body.position.x, prop.body.position.y, prop.body.position.z)
            .sub(wristPosition).applyQuaternion(inverseWrist);
          // Require the solid to be inside the mouth; proximity alone is not a grasp.
          if (Math.abs(localPosition.x) > 6 || Math.abs(localPosition.y - 124) > 18 || Math.abs(localPosition.z - 14) > 10) continue;
          localQuaternion.set(prop.body.quaternion.x, prop.body.quaternion.y, prop.body.quaternion.z, prop.body.quaternion.w)
            .premultiply(inverseWrist);
          const contact = graspTravel(jawSurfaces, localPosition, localQuaternion, prop.graspShape, jointLimits.gripper[1]);
          if (contact === null || pose.gripper > contact || targetsRef.current.gripper > contact) continue;
          held = prop;
          heldTravel = contact;
          heldPosition.copy(localPosition);
          heldQuaternion.copy(localQuaternion);
          held.body.type = CANNON.Body.KINEMATIC;
          held.body.mass = 0;
          held.body.collisionFilterMask = 1; // The carried solid must not collide with its own fingers.
          held.body.updateMassProperties();
          held.body.angularVelocity.setZero();
          held.body.wakeUp();
          setHeldName(held.name);
          break;
        }
      }
      if (held) {
        if (pose.gripper < heldTravel) {
          pose.gripper = heldTravel;
          velocities.gripper = 0;
          applyPose(pose);
        }
        carriedPosition.copy(heldPosition).applyQuaternion(gripQuaternion).add(wristPosition);
        carriedQuaternion.copy(gripQuaternion).multiply(heldQuaternion);
        held.body.position.set(carriedPosition.x, carriedPosition.y, carriedPosition.z);
        held.body.quaternion.set(carriedQuaternion.x, carriedQuaternion.y, carriedQuaternion.z, carriedQuaternion.w);
        held.body.velocity.set(gripVelocity.x, gripVelocity.y, gripVelocity.z);
      }
      robotColliders.forEach(({ marker, body }) => {
        marker.getWorldPosition(markerPosition);
        marker.getWorldQuaternion(markerQuaternion);
        body.position.set(markerPosition.x, markerPosition.y, markerPosition.z);
        body.quaternion.set(markerQuaternion.x, markerQuaternion.y, markerQuaternion.z, markerQuaternion.w);
        body.updateAABB();
      });
      // The arm's colliders are moved by position, not velocity, so contact alone never wakes a
      // sleeping prop. Wake anything the arm reaches into.
      props.forEach(({ body }) => {
        if (body.sleepState !== CANNON.Body.SLEEPING) return;
        body.updateAABB();
        if (robotColliders.some((collider) => collider.body.aabb.overlaps(body.aabb))) body.wakeUp();
      });
      world.step(1 / 60, elapsed, 5);
      if (held) {
        held.body.position.set(carriedPosition.x, carriedPosition.y, carriedPosition.z);
        held.body.quaternion.set(carriedQuaternion.x, carriedQuaternion.y, carriedQuaternion.z, carriedQuaternion.w);
      }
      props.forEach(({ mesh, body }) => {
        mesh.position.set(body.position.x, body.position.y, body.position.z);
        mesh.quaternion.set(body.quaternion.x, body.quaternion.y, body.quaternion.z, body.quaternion.w);
      });
      // Safety net: if the floor guard ever parks the arm short of a step, start over rather than hang.
      // Counted in simulated seconds so slow devices running in slow motion don't trip it.
      if (demo) stepSeconds += elapsed;
      if (demo && stepSeconds > 12) {
        startDemo();
      } else if (demo) {
        const step = demo.steps[demo.index];
        if (atTarget(pose, step.target)) {
          if (step.settledAt === undefined) step.settledAt = time;
          if (time - step.settledAt >= step.pause) {
            demo.index += 1;
            if (demo.index === demo.steps.length) {
              demo = null;
              finishedAt = time;
              setDemoLabel(describeStack());
            } else {
              const next = demo.steps[demo.index];
              stepSeconds = 0;
              setTargetPose(next.target);
              setDemoLabel(next.label);
            }
          }
        } else step.settledAt = undefined;
      } else if (autopilot && finishedAt && time - finishedAt > 4500 && atTarget(pose, targetsRef.current)) {
        startDemo();
      }
      writeReadouts(pose, time);
      controls.update();
      renderer.render(scene, camera);
    };
    render();

    return () => {
      disposed = true;
      cancelAnimationFrame(frame);
      resizeObserver.disconnect();
      stopWheelGuard();
      stopWatching();
      controls.dispose();
      actionsRef.current = { takeManual: () => undefined, toggleAutopilot: () => undefined, resetBlocks: () => undefined };
      disposeObject(scene);
      reflections.dispose();
      renderer.dispose();
      mount.removeChild(renderer.domElement);
    };
  }, []);

  const setJoint = (name: JointName, value: number) => {
    actionsRef.current.takeManual();
    const next = { ...targetsRef.current, [name]: clampJoint(name, value) };
    targetsRef.current = next;
    setTargets(next);
  };
  const goHome = () => {
    actionsRef.current.takeManual();
    targetsRef.current = { ...homePose };
    setTargets({ ...homePose });
  };

  const ready = loaded === meshCount;
  const status = !ready
    ? `Loading CAD meshes ${loaded}/${meshCount}`
    : mode === "autopilot"
      ? demoLabel ?? "Autopilot"
      : heldName
        ? `Holding the ${heldName}`
        : "Manual control";

  return (
    <section className="hero" id="simulator" data-meshes={loaded} data-mode={mode} data-held={heldName ?? ""}>
      <div className="hero-stage" ref={mountRef} aria-label="Interactive robot arm simulator" />
      {!ready && (
        <div className="hero-loader" aria-hidden="true">
          <span style={{ "--progress": `${(loaded / meshCount) * 100}%` } as React.CSSProperties} />
        </div>
      )}
      <div className="hero-rail">
        <div className="hero-copy">{children}</div>
        <div className="dock ticks" role="group" aria-label="Simulator controls">
          <div className="dock-status" aria-live="polite">
            <span className={`dot dot-${mode}`} />
            <span className="dock-mode">{mode === "autopilot" ? "Autopilot" : mode === "manual" ? "Manual" : "Boot"}</span>
            <span className="dock-message">{status}</span>
          </div>
          <div className="joint-list">
            {jointControls.map(({ name, id, label, unit }) => {
              const [min, max] = jointLimits[name];
              const value = Math.round(targets[name]);
              return (
                <label className="joint" key={name}>
                  <span className="joint-id">{id}</span>
                  <span className="joint-name">{label}</span>
                  <span className="joint-readout" ref={(node) => { readoutRefs.current[name] = node; }} />
                  <input
                    aria-label={label}
                    aria-valuetext={`${value}${unit}`}
                    type="range"
                    min={min}
                    max={max}
                    value={value}
                    style={{ "--fill": `${((value - min) / (max - min)) * 100}%` } as React.CSSProperties}
                    onChange={(event) => setJoint(name, Number(event.target.value))}
                  />
                </label>
              );
            })}
          </div>
          <div className="dock-tip">
            <span>Tip</span>
            <span ref={tipRef} />
            <span>mm</span>
          </div>
          <div className="dock-actions">
            <button className="button button-primary" type="button" disabled={!ready} onClick={() => actionsRef.current.toggleAutopilot()}>
              {mode === "autopilot" ? "Pause autopilot" : "Run autopilot"}
            </button>
            <button className="button" type="button" onClick={goHome}>Home</button>
            <button className="button" type="button" onClick={() => actionsRef.current.resetBlocks()}>Reset blocks</button>
          </div>
          <p className="dock-hint">
            <span className="hint-pointer">Drag to orbit · Ctrl + scroll to zoom · Gamepad ready</span>
            <span className="hint-touch">Drag to orbit · pinch to zoom</span>
          </p>
        </div>
      </div>
      <dl className="title-block">
        {[...facts.slice(0, 2), ["Reach", reach ? `≈ ${reach} mm` : "…"] as TitleBlockFact, ...facts.slice(2)].map(([label, value]) => (
          <div key={label}>
            <dt>{label}</dt>
            <dd>{value}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}
