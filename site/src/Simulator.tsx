import React, { useEffect, useRef, useState } from "react";
import * as CANNON from "cannon-es";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { RoomEnvironment } from "three/examples/jsm/environments/RoomEnvironment.js";
import { STLLoader } from "three/examples/jsm/loaders/STLLoader.js";
import { toCreasedNormals } from "three/examples/jsm/utils/BufferGeometryUtils.js";
import { jawAngle, jawPivotX, jawPivotY, linkagePose, releaseTravel } from "./gripper";
import { wristPosition as wristJointPosition, wristMeshOffset } from "./assembly";
import { graspTravel, type GraspShape, type JawSurface } from "./grasp";
import {
  applyJointRotations,
  clampJoint,
  createArmModel,
  elbowPosition,
  gripPointPosition,
  homePose,
  jointDelta,
  jointLimits,
  jointNames,
  shoulderPosition,
  type JointAngles,
  type JointName,
} from "./arm";
import { brickColors, brickHeight, buildPresets, footprint, studHeight, studPitch, type BuildPreset } from "./bricks";
import { followLine, planBuild, type BuildPlan, type PlannedBrick } from "./buildPlan";
import { ArmDriver, BuildSequencer, type BuildStatus } from "./buildRunner";
import { brickGeometry, brickMaterial, ghostMaterial } from "./brickMesh";
import { SimClock, speedRange } from "./simClock";
import {
  disposeObject,
  generatedBase,
  guardWheelZoom,
  pageBackground,
  prefersReducedMotion,
  radialGlowTexture,
  watchVisibility,
} from "./shared";

type Mode = "loading" | "autopilot" | "manual";
type BuildView = {
  status: BuildStatus;
  paused: boolean;
  current: number;
  total: number;
  placed: number;
  stage: string | null;
  failure: string | null;
};
type Actions = {
  takeManual: () => void;
  start: () => void;
  togglePause: () => void;
  reset: () => void;
  selectPreset: (id: string) => void;
  setSpeed: (speed: number) => void;
};

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
const defaultPreset = "house";
const brickMass = 0.03;
// How close a released brick must be to its studs to click into place.
const snapDistance = 2;
const snapAngle = THREE.MathUtils.degToRad(3);
const noActions: Actions = {
  takeManual: () => undefined,
  start: () => undefined,
  togglePause: () => undefined,
  reset: () => undefined,
  selectPreset: () => undefined,
  setSpeed: () => undefined,
};

const formatSpeed = (speed: number) => `${Number(speed.toFixed(2))}×`;

export type TitleBlockFact = [label: string, value: string];

export function Simulator({ children, facts }: { children: React.ReactNode; facts: TitleBlockFact[] }) {
  const mountRef = useRef<HTMLDivElement | null>(null);
  const readoutRefs = useRef<Partial<Record<JointName, HTMLSpanElement | null>>>({});
  const tipRef = useRef<HTMLSpanElement | null>(null);
  const driverRef = useRef<ArmDriver | null>(null);
  driverRef.current ??= new ArmDriver();
  const actionsRef = useRef<Actions>(noActions);
  const [targets, setTargets] = useState({ ...homePose });
  const [loaded, setLoaded] = useState(0);
  const [mode, setMode] = useState<Mode>("loading");
  const [heldName, setHeldName] = useState<string | null>(null);
  const [reach, setReach] = useState<number | null>(null);
  const [presetId, setPresetId] = useState(defaultPreset);
  const [speed, setSpeed] = useState(speedRange.initial);
  const [tab, setTab] = useState<"build" | "joints">("build");
  const [view, setView] = useState<BuildView>({
    status: "idle", paused: false, current: 0, total: 0, placed: 0, stage: null, failure: null,
  });

  useEffect(() => {
    if (!mountRef.current) return undefined;
    const mount = mountRef.current;
    const driver = driverRef.current!;
    let frame = 0;
    let disposed = false;
    let visible = true;
    let loadedCount = 0;
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
    shoulder.position.set(...shoulderPosition);
    elbow.position.set(...elbowPosition);
    wrist.position.set(...wristJointPosition);
    robotRoot.add(base);
    base.add(shoulder);
    shoulder.add(elbow);
    elbow.add(wrist);
    wrist.add(leftJaw, rightJaw);
    const gripPoint = new THREE.Object3D();
    gripPoint.position.set(...gripPointPosition);
    wrist.add(gripPoint);
    // Mesh-free copy of the chain for inverse kinematics, reach and build planning.
    const arm = createArmModel();

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
        if (loadedCount === meshCount) onReady();
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
      // together so the lowest grey support rests on the same z=0 floor as the bricks.
      robotRoot.position.z = -geometry.boundingBox!.min.z;
      arm.setLift(robotRoot.position.z);
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

    // Bricks: one physics body and mesh each, plus a faint ghost marking where it will go.
    type SimBrick = {
      plan: PlannedBrick;
      mesh: THREE.Mesh;
      ghost: THREE.Mesh;
      body: CANNON.Body;
      graspShape: GraspShape;
      placed: boolean;
      // Body pose at the start of the latest fixed step, for interpolating what is drawn.
      previousPosition: THREE.Vector3;
      previousQuaternion: THREE.Quaternion;
      // CAD contact travel for the pose it last sat in the mouth, reused while nothing moves.
      contact?: { position: THREE.Vector3; quaternion: THREE.Quaternion; travel: number | null };
    };
    const brickGroup = new THREE.Group();
    scene.add(brickGroup);
    const brickGeometries = new Map<string, THREE.BufferGeometry>();
    const brickMaterials = new Map<string, THREE.Material>();
    const cached = <T,>(map: Map<string, T>, key: string, make: () => T) => {
      if (!map.has(key)) map.set(key, make());
      return map.get(key)!;
    };
    let bricks: SimBrick[] = [];
    const plans = new Map<string, BuildPlan>();
    let plan: BuildPlan | null = null;
    let sequencer: BuildSequencer | null = null;
    const clock = new SimClock();
    const lift = () => robotRoot.position.z;

    const toVec3 = (vector: CANNON.Vec3, out: THREE.Vector3) => out.set(vector.x, vector.y, vector.z);
    const toQuaternion = (quaternion: CANNON.Quaternion, out: THREE.Quaternion) => out.set(quaternion.x, quaternion.y, quaternion.z, quaternion.w);
    const setBodyPose = (body: CANNON.Body, position: THREE.Vector3, quaternion: THREE.Quaternion) => {
      body.position.set(position.x, position.y, position.z);
      body.quaternion.set(quaternion.x, quaternion.y, quaternion.z, quaternion.w);
    };
    const syncPrevious = (brick: SimBrick) => {
      toVec3(brick.body.position, brick.previousPosition);
      toQuaternion(brick.body.quaternion, brick.previousQuaternion);
    };
    const toSupply = (brick: SimBrick) => {
      brick.body.type = CANNON.Body.DYNAMIC;
      brick.body.mass = brickMass;
      brick.body.updateMassProperties();
      brick.body.collisionFilterMask = -1;
      setBodyPose(brick.body, brick.plan.supply.position, brick.plan.supply.quaternion);
      brick.body.velocity.setZero();
      brick.body.angularVelocity.setZero();
      brick.body.aabbNeedsUpdate = true;
      brick.body.wakeUp();
      brick.placed = false;
      brick.ghost.visible = true;
      syncPrevious(brick);
    };
    // Clutch power: once on its studs a brick is locked to the structure.
    const snapToStuds = (brick: SimBrick) => {
      brick.body.type = CANNON.Body.STATIC;
      brick.body.mass = 0;
      brick.body.updateMassProperties();
      brick.body.collisionFilterMask = -1;
      setBodyPose(brick.body, brick.plan.target.position, brick.plan.target.quaternion);
      brick.body.velocity.setZero();
      brick.body.angularVelocity.setZero();
      brick.body.aabbNeedsUpdate = true;
      brick.placed = true;
      brick.ghost.visible = false;
    };
    const createBricks = (next: BuildPlan) => {
      bricks.forEach((brick) => world.removeBody(brick.body));
      brickGroup.clear();
      bricks = next.bricks.map((planned) => {
        const geometry = cached(brickGeometries, `${planned.studs.u}x${planned.studs.v}`, () => brickGeometry(planned.size, planned.studs));
        const color = brickColors[planned.entry.color];
        const mesh = new THREE.Mesh(geometry, cached(brickMaterials, color, () => brickMaterial(color)));
        mesh.castShadow = true;
        mesh.receiveShadow = true;
        const ghost = new THREE.Mesh(geometry, cached(brickMaterials, `ghost ${color}`, () => ghostMaterial(color)));
        ghost.position.copy(planned.target.position);
        ghost.quaternion.copy(planned.target.quaternion);
        brickGroup.add(mesh, ghost);
        const half = planned.size.clone().multiplyScalar(0.5);
        const body = new CANNON.Body({ mass: brickMass, shape: new CANNON.Box(new CANNON.Vec3(half.x, half.y, half.z)) });
        body.linearDamping = 0.08;
        body.angularDamping = 0.12;
        // The world is in millimetres, so the default 0.1 unit/s sleep threshold never trips and
        // resting bricks slowly jitter. Let settled bricks sleep instead.
        body.allowSleep = true;
        body.sleepSpeedLimit = 3;
        body.sleepTimeLimit = 0.5;
        world.addBody(body);
        const brick: SimBrick = {
          plan: planned, mesh, ghost, body, graspShape: { halfExtents: half }, placed: false,
          previousPosition: new THREE.Vector3(), previousQuaternion: new THREE.Quaternion(),
        };
        toSupply(brick);
        return brick;
      });
    };
    const planFor = (id: string) => {
      if (!plans.has(id)) {
        const preset = buildPresets.find((entry) => entry.id === id) ?? buildPresets[0];
        const next = planBuild(preset, arm);
        if (next.problems.length) console.error(`Cannot build ${preset.name}:\n${next.problems.join("\n")}`);
        plans.set(id, next);
      }
      return plans.get(id)!;
    };

    let held: SimBrick | null = null;
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
    const bodyPosition = new THREE.Vector3();
    const bodyQuaternion = new THREE.Quaternion();
    const release = () => {
      if (!held) return;
      const brick = held;
      held = null;
      setHeldName(null);
      toVec3(brick.body.position, bodyPosition);
      toQuaternion(brick.body.quaternion, bodyQuaternion);
      if (bodyPosition.distanceTo(brick.plan.target.position) < snapDistance && bodyQuaternion.angleTo(brick.plan.target.quaternion) < snapAngle) {
        snapToStuds(brick);
        return;
      }
      brick.body.collisionFilterMask = -1;
      brick.body.type = CANNON.Body.DYNAMIC;
      brick.body.mass = brickMass;
      brick.body.updateMassProperties();
      brick.body.velocity.set(gripVelocity.x, gripVelocity.y, gripVelocity.z);
      brick.body.wakeUp();
    };
    // Let go of whatever is held without letting it fall or snap, ahead of a reset.
    const dropHeld = () => {
      held = null;
      setHeldName(null);
    };
    const resetBricks = () => {
      dropHeld();
      bricks.forEach(toSupply);
      clock.settle();
    };
    let motionBlocked = false;

    const updateReach = () => {
      let maxReach = 0;
      for (let s = -130; s <= 130; s += 5) {
        for (let e = -135; e <= 135; e += 5) {
          for (let w = -150; w <= 18; w += 12) {
            const tip = arm.probe({ base: 0, shoulder: s, elbow: e, wrist: w, gripper: 0 });
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

    // Push build state to React only when something visible changed.
    let shownView = "";
    let shownMode: Mode = "loading";
    const publish = () => {
      if (loadedCount < meshCount || !sequencer || !plan) return;
      const status = sequencer.status;
      const running = status === "running";
      const { current, total } = sequencer.progress();
      const next: BuildView = {
        status,
        paused: running && clock.paused,
        current,
        total,
        placed: bricks.filter((brick) => brick.placed).length,
        stage: running ? sequencer.step.label : null,
        failure: sequencer.failure,
      };
      const key = JSON.stringify(next);
      if (key !== shownView) {
        shownView = key;
        setView(next);
      }
      const nextMode: Mode = running ? "autopilot" : "manual";
      if (nextMode !== shownMode) {
        shownMode = nextMode;
        setMode(nextMode);
      }
    };
    const showTargets = () => setTargets({ ...driver.targets });

    const startBuild = () => {
      if (!plan || plan.problems.length || loadedCount < meshCount) return;
      if (sequencer?.status === "running") return;
      clock.paused = false;
      resetBricks();
      sequencer = new BuildSequencer(plan);
      const step = sequencer.start();
      driver.moveTo(step.target, followLine(step, lift()));
      showTargets();
      publish();
    };
    const resetBuild = () => {
      if (!plan) return;
      clock.paused = false;
      resetBricks();
      sequencer = new BuildSequencer(plan);
      driver.moveTo({ ...homePose });
      showTargets();
      publish();
    };
    const selectPreset = (id: string) => {
      if (loadedCount < meshCount) return;
      dropHeld();
      plan = planFor(id);
      createBricks(plan);
      setPresetId(plan.preset.id);
      resetBuild();
    };
    const takeManual = () => {
      sequencer?.stop();
      clock.paused = false;
      driver.track();
      publish();
    };
    actionsRef.current = {
      takeManual,
      start: startBuild,
      togglePause: () => {
        if (sequencer?.status !== "running") return;
        clock.paused = !clock.paused;
        publish();
      },
      reset: resetBuild,
      selectPreset,
      setSpeed: (value) => {
        clock.setSpeed(value);
        setSpeed(clock.speed);
      },
    };
    const onReady = () => {
      updateReach();
      selectPreset(defaultPreset);
      if (!prefersReducedMotion()) startBuild();
      publish();
    };

    const applyPose = (pose: JointAngles) => {
      applyJointRotations(pose, { base, shoulder, elbow, wrist });
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

    // One fixed simulation step: joints, grasp, physics and the build sequence all advance by
    // the same simulated `seconds`, whatever the speed setting.
    const pose = driver.pose;
    const previousPose = { ...pose };
    const tick = (seconds: number) => {
      Object.assign(previousPose, pose);
      bricks.forEach(syncPrevious);
      driver.step(seconds);
      applyPose(pose);
      const hitFloor = movingMeshes.some((mesh) => {
        if (!mesh.geometry.boundingBox) return false;
        return floorBounds.copy(mesh.geometry.boundingBox).applyMatrix4(mesh.matrixWorld).min.z < 0;
      });
      if (hitFloor) {
        Object.assign(pose, previousPose);
        driver.hold();
        if (sequencer?.status === "running") sequencer.fail("Stopped short of the table");
        if (!motionBlocked) showTargets();
        motionBlocked = true;
        applyPose(pose);
      } else motionBlocked = false;

      gripPoint.getWorldPosition(gripPosition);
      gripPoint.getWorldQuaternion(gripQuaternion);
      gripVelocity.copy(gripPosition).sub(previousGripPosition).divideScalar(seconds);
      previousGripPosition.copy(gripPosition);
      wrist.getWorldPosition(wristPosition);
      inverseWrist.copy(gripQuaternion).invert();
      if (held && pose.gripper >= releaseTravel(heldTravel, jointLimits.gripper[1])) release();
      if (!held && driver.targets.gripper < previousPose.gripper && pose.gripper < previousPose.gripper) {
        for (const brick of bricks) {
          if (brick.body.type !== CANNON.Body.DYNAMIC) continue;
          localPosition.set(brick.body.position.x, brick.body.position.y, brick.body.position.z)
            .sub(wristPosition).applyQuaternion(inverseWrist);
          // Require the solid to be inside the mouth; proximity alone is not a grasp.
          if (Math.abs(localPosition.x) > 6 || Math.abs(localPosition.y - 124) > 18 || Math.abs(localPosition.z - 14) > 10) continue;
          localQuaternion.set(brick.body.quaternion.x, brick.body.quaternion.y, brick.body.quaternion.z, brick.body.quaternion.w)
            .premultiply(inverseWrist);
          const known = brick.contact;
          const contact = known && known.position.distanceTo(localPosition) < 0.01 && known.quaternion.angleTo(localQuaternion) < 1e-4
            ? known.travel
            : graspTravel(jawSurfaces, localPosition, localQuaternion, brick.graspShape, jointLimits.gripper[1]);
          brick.contact = { position: localPosition.clone(), quaternion: localQuaternion.clone(), travel: contact };
          if (contact === null || pose.gripper > contact || driver.targets.gripper > contact) continue;
          held = brick;
          heldTravel = contact;
          heldPosition.copy(localPosition);
          heldQuaternion.copy(localQuaternion);
          held.body.type = CANNON.Body.KINEMATIC;
          held.body.mass = 0;
          held.body.collisionFilterMask = 1; // The carried solid must not collide with its own fingers.
          held.body.updateMassProperties();
          held.body.angularVelocity.setZero();
          held.body.wakeUp();
          setHeldName(held.plan.label);
          break;
        }
      }
      if (held) {
        if (pose.gripper < heldTravel) {
          pose.gripper = heldTravel;
          driver.velocities.gripper = 0;
          applyPose(pose);
        }
        carriedPosition.copy(heldPosition).applyQuaternion(gripQuaternion).add(wristPosition);
        carriedQuaternion.copy(gripQuaternion).multiply(heldQuaternion);
        setBodyPose(held.body, carriedPosition, carriedQuaternion);
        held.body.velocity.set(gripVelocity.x, gripVelocity.y, gripVelocity.z);
      }
      robotColliders.forEach(({ marker, body }) => {
        marker.getWorldPosition(markerPosition);
        marker.getWorldQuaternion(markerQuaternion);
        setBodyPose(body, markerPosition, markerQuaternion);
        body.updateAABB();
      });
      // The arm's colliders are moved by position, not velocity, so contact alone never wakes a
      // sleeping brick. Wake anything the arm reaches into.
      bricks.forEach(({ body }) => {
        if (body.sleepState !== CANNON.Body.SLEEPING) return;
        body.updateAABB();
        if (robotColliders.some((collider) => collider.body.aabb.overlaps(body.aabb))) body.wakeUp();
      });
      world.step(seconds);
      if (held) setBodyPose(held.body, carriedPosition, carriedQuaternion);

      if (sequencer) {
        const next = sequencer.update(seconds, driver.arrived(held ? heldTravel : null), held?.plan.index ?? null, (index) => bricks[index].placed);
        if (next) {
          driver.moveTo(next.target, followLine(next, lift()));
          showTargets();
        }
      }
    };

    const renderPose = { ...homePose };
    const drawnPosition = new THREE.Vector3();
    const drawnQuaternion = new THREE.Quaternion();
    let lastTime = performance.now();
    let lastGamepadUpdate = 0;
    const render = (time = performance.now()) => {
      frame = requestAnimationFrame(render);
      const elapsed = Math.min((time - lastTime) / 1000, 0.1);
      lastTime = time;
      if (!visible) return;
      const gamepad = navigator.getGamepads?.().find((pad) => pad?.connected);
      if (gamepad) {
        const axis = (index: number) => Math.abs(gamepad.axes[index] ?? 0) > 0.12 ? gamepad.axes[index] : 0;
        const trigger = (gamepad.buttons[7]?.value ?? 0) - (gamepad.buttons[6]?.value ?? 0);
        const homePressed = gamepad.buttons[0]?.pressed ?? false;
        if ([0, 1, 2, 3].some((index) => axis(index) !== 0) || Math.abs(trigger) > 0.05 || homePressed) {
          takeManual();
          const next = driver.targets;
          next.base = (next.base + axis(0) * 100 * elapsed + 360) % 360;
          next.shoulder = clampJoint("shoulder", next.shoulder - axis(1) * 80 * elapsed);
          next.wrist = clampJoint("wrist", next.wrist + axis(2) * 80 * elapsed);
          next.elbow = clampJoint("elbow", next.elbow - axis(3) * 80 * elapsed);
          next.gripper = clampJoint("gripper", next.gripper + trigger * 18 * elapsed);
          if (homePressed) Object.assign(next, homePose);
          if (time - lastGamepadUpdate > 100) {
            showTargets();
            lastGamepadUpdate = time;
          }
        }
      }
      const alpha = clock.advance(elapsed, tick);
      // Draw between the last two fixed steps so motion stays smooth at any display rate.
      jointNames.forEach((name) => {
        renderPose[name] = previousPose[name] + jointDelta(name, previousPose[name], pose[name]) * alpha;
      });
      applyPose(renderPose);
      bricks.forEach((brick) => {
        brick.mesh.position.lerpVectors(brick.previousPosition, toVec3(brick.body.position, drawnPosition), alpha);
        brick.mesh.quaternion.slerpQuaternions(brick.previousQuaternion, toQuaternion(brick.body.quaternion, drawnQuaternion), alpha);
      });
      publish();
      writeReadouts(renderPose, time);
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
      actionsRef.current = noActions;
      disposeObject(scene);
      brickGeometries.forEach((geometry) => geometry.dispose());
      brickMaterials.forEach((material) => material.dispose());
      reflections.dispose();
      renderer.dispose();
      mount.removeChild(renderer.domElement);
    };
  }, []);

  const setJoint = (name: JointName, value: number) => {
    actionsRef.current.takeManual();
    const driver = driverRef.current!;
    driver.targets = { ...driver.targets, [name]: clampJoint(name, value) };
    setTargets({ ...driver.targets });
  };
  const goHome = () => {
    actionsRef.current.takeManual();
    driverRef.current!.targets = { ...homePose };
    setTargets({ ...homePose });
  };

  const ready = loaded === meshCount;
  const preset = buildPresets.find((entry) => entry.id === presetId) ?? buildPresets[0];
  const running = view.status === "running";
  const total = view.total || preset.bricks.length;
  const [headline, detail] = !ready
    ? ["Loading", `${preset.name} · ${preset.bricks.length} bricks`]
    : running && view.paused
      ? [`Paused at brick ${view.current} of ${total}`, view.stage ?? ""]
      : running
        ? [`Placing brick ${view.current} of ${total}`, view.stage ?? ""]
        : view.status === "complete"
          ? [`${preset.name} complete`, `All ${total} bricks placed`]
          : view.status === "failed"
            ? ["Build halted", view.failure ?? ""]
            : view.status === "stopped"
              ? [`Stopped at brick ${view.current} of ${total}`, "Manual control took over · Start rebuilds"]
              : ["Ready to build", `${preset.name} · ${total} bricks`];
  const status = !ready
    ? `Loading CAD meshes ${loaded}/${meshCount}`
    : running
      ? (view.paused ? `Paused · ${view.stage ?? ""}` : view.stage ?? "Building")
      : heldName
        ? `Holding the ${heldName}`
        : view.status === "complete"
          ? `${preset.name} complete`
          : view.status === "idle"
            ? "Ready to build"
            : "Manual control";
  const modeLabel = !ready ? "Boot" : running ? (view.paused ? "Paused" : "Building") : view.status === "complete" ? "Done" : "Manual";
  const dot = !ready ? "loading" : running ? (view.paused ? "paused" : "autopilot") : "manual";
  const speedFill = ((speed - speedRange.min) / (speedRange.max - speedRange.min)) * 100;

  return (
    <section
      className="hero"
      id="simulator"
      data-meshes={loaded}
      data-mode={mode}
      data-held={heldName ?? ""}
      data-build={view.status}
      data-paused={view.paused}
      data-preset={presetId}
      data-placed={view.placed}
      data-stage={view.stage ?? ""}
      data-speed={speed}
    >
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
            <span className={`dot dot-${dot}`} />
            <span className="dock-mode">{modeLabel}</span>
            <span className="dock-message">{status}</span>
          </div>
          <div className="dock-tabs" role="tablist" aria-label="Control panel">
            {(["build", "joints"] as const).map((name) => (
              <button
                key={name}
                className="dock-tab"
                type="button"
                role="tab"
                id={`dock-tab-${name}`}
                aria-controls={`dock-panel-${name}`}
                aria-selected={tab === name}
                onClick={() => setTab(name)}
              >
                {name === "build" ? "Build" : "Joints"}
              </button>
            ))}
          </div>
          <div className="dock-panel" id="dock-panel-build" role="tabpanel" aria-labelledby="dock-tab-build" hidden={tab !== "build"}>
            <div className="preset-list" role="radiogroup" aria-label="Structure to build">
              {buildPresets.map((entry) => (
                <button
                  key={entry.id}
                  className="preset"
                  type="button"
                  role="radio"
                  aria-checked={presetId === entry.id}
                  disabled={!ready}
                  onClick={() => actionsRef.current.selectPreset(entry.id)}
                >
                  <PresetPreview preset={entry} />
                  <span className="preset-name">{entry.name}</span>
                  <span className="preset-count">{entry.bricks.length} bricks</span>
                </button>
              ))}
            </div>
            <div className="build-progress">
              <p className="build-headline">{headline}</p>
              <p className="build-detail">{detail}</p>
              <div
                className="build-bar"
                role="progressbar"
                aria-label="Bricks placed"
                aria-valuemin={0}
                aria-valuemax={total}
                aria-valuenow={view.placed}
                style={{ "--progress": `${(view.placed / total) * 100}%` } as React.CSSProperties}
              />
            </div>
            <div className="dock-actions build-actions">
              <button className="button button-primary" type="button" disabled={!ready || running} onClick={() => actionsRef.current.start()}>
                Start
              </button>
              <button className="button" type="button" disabled={!running} onClick={() => actionsRef.current.togglePause()}>
                {view.paused ? "Resume" : "Pause"}
              </button>
              <button className="button" type="button" disabled={!ready} onClick={() => actionsRef.current.reset()}>Reset</button>
            </div>
          </div>
          <div className="dock-panel" id="dock-panel-joints" role="tabpanel" aria-labelledby="dock-tab-joints" hidden={tab !== "joints"}>
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
              <button className="button" type="button" onClick={goHome}>Home</button>
            </div>
          </div>
          <label className="joint speed-control">
            <span className="joint-id">SPD</span>
            <span className="joint-name">Sim speed</span>
            <output className="joint-readout">{formatSpeed(speed)}</output>
            <input
              aria-label="Simulation speed"
              aria-valuetext={formatSpeed(speed)}
              type="range"
              min={speedRange.min}
              max={speedRange.max}
              step={speedRange.step}
              value={speed}
              style={{ "--fill": `${speedFill}%` } as React.CSSProperties}
              onChange={(event) => actionsRef.current.setSpeed(Number(event.target.value))}
            />
          </label>
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

// Front elevation drawn straight from the preset data, bottom course first.
function PresetPreview({ preset }: { preset: BuildPreset }) {
  const width = Math.max(...preset.bricks.map((entry) => entry.cell[0] + footprint(entry).u)) * studPitch;
  const layers = Math.max(...preset.bricks.map((entry) => entry.cell[2])) + 1;
  const height = layers * brickHeight + studHeight;
  return (
    <svg className="preset-preview" viewBox={`-1 -1 ${width + 2} ${height + 2}`} aria-hidden="true" preserveAspectRatio="xMidYMax meet">
      {preset.bricks.map((entry, index) => {
        const { u } = footprint(entry);
        const x = entry.cell[0] * studPitch;
        const y = height - (entry.cell[2] + 1) * brickHeight;
        const color = brickColors[entry.color];
        return (
          <g key={index} fill={color}>
            {Array.from({ length: u }, (_, stud) => (
              <rect key={stud} x={x + stud * studPitch + 2.5} y={y - studHeight} width={5} height={studHeight + 0.5} />
            ))}
            <rect x={x + 0.4} y={y} width={u * studPitch - 0.8} height={brickHeight - 0.4} rx={0.8} />
          </g>
        );
      })}
    </svg>
  );
}
