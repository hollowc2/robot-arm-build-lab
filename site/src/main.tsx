import React, { useEffect, useMemo, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { STLLoader } from "three/examples/jsm/loaders/STLLoader.js";
import { advanceMotion } from "./motion";
import "./styles.css";

type BoundingBox = {
  min: [number, number, number];
  max: [number, number, number];
  size: [number, number, number];
};

type CatalogPart = {
  name: string;
  title: string;
  module: string;
  source: string;
  category: string;
  status: string;
  printReady: boolean;
  volumeMm3: number;
  bbox: BoundingBox;
  webModel: string;
};

type Catalog = {
  project: string;
  generatedAt: string;
  parts: CatalogPart[];
};

type ViewerPart = {
  name: string;
  bbox: BoundingBox;
  status: string;
};

type ViewerModel = {
  name: string;
  format: string;
  units: string;
  parts: ViewerPart[];
};

type ProgressFeed = {
  generatedAt: string;
  commits: { sha: string; date: string; subject: string }[];
  pullRequests: { number: number; title: string; url: string; state: string }[];
  issues: { number: number; title: string; url: string; state: string }[];
  note: string;
};

type ViewerTarget = {
  id: string;
  title: string;
  subtitle: string;
  url: string | null;
  bbox: BoundingBox | null;
};

type ViewerState = "loading" | "stl" | "fallback" | "error";

const generatedBase = `${import.meta.env.BASE_URL}generated`;

const buildLogModules = import.meta.glob("../../content/build-log/*.md", {
  query: "?raw",
  import: "default",
  eager: true,
});

const designDecisionModules = import.meta.glob("../../content/design-decisions/*.md", {
  query: "?raw",
  import: "default",
  eager: true,
});

function parseNote(raw: unknown, path: string) {
  const text = String(raw);
  const title = text.match(/^#\s+(.+)$/m)?.[1] ?? path.split("/").pop() ?? "Note";
  const body = text.replace(/^#\s+.+$/m, "").trim();
  return { title, body, path };
}

function useJson<T>(path: string) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    fetch(path)
      .then((response) => {
        if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
        return response.json() as Promise<T>;
      })
      .then((payload) => active && setData(payload))
      .catch((fetchError: Error) => active && setError(fetchError.message));
    return () => {
      active = false;
    };
  }, [path]);

  return { data, error };
}

function modelUrl(path: string | null) {
  if (!path) return null;
  return `${import.meta.env.BASE_URL}${path}`;
}

function formatName(name: string) {
  return name.replaceAll("_", " ");
}

function createFallbackAssembly(model: ViewerModel) {
  const group = new THREE.Group();
  model.parts.forEach((part, index) => {
    const geometry = new THREE.BoxGeometry(
      Math.max(part.bbox.size[0], 0.5),
      Math.max(part.bbox.size[1], 0.5),
      Math.max(part.bbox.size[2], 0.5),
    );
    const material = new THREE.MeshStandardMaterial({
      color: new THREE.Color().setHSL((index * 0.11) % 1, 0.42, part.status === "active" ? 0.52 : 0.67),
      roughness: 0.7,
      metalness: 0.05,
      transparent: part.status !== "active",
      opacity: part.status === "active" ? 0.9 : 0.42,
    });
    const mesh = new THREE.Mesh(geometry, material);
    mesh.position.set(
      (part.bbox.min[0] + part.bbox.max[0]) / 2,
      (part.bbox.min[1] + part.bbox.max[1]) / 2,
      (part.bbox.min[2] + part.bbox.max[2]) / 2,
    );
    group.add(mesh);
  });
  return group;
}

function createFallbackBox(target: ViewerTarget) {
  const size = target.bbox?.size ?? [80, 80, 80];
  const group = new THREE.Group();
  const geometry = new THREE.BoxGeometry(Math.max(size[0], 1), Math.max(size[1], 1), Math.max(size[2], 1));
  const material = new THREE.MeshStandardMaterial({
    color: "#587b8f",
    roughness: 0.72,
    metalness: 0.04,
    transparent: true,
    opacity: 0.68,
  });
  group.add(new THREE.Mesh(geometry, material));
  return group;
}

function disposeObject(object: THREE.Object3D) {
  object.traverse((child) => {
    if (child instanceof THREE.Mesh) {
      child.geometry.dispose();
      const materials = Array.isArray(child.material) ? child.material : [child.material];
      materials.forEach((material) => material.dispose());
    }
  });
}

function ModelViewer({
  target,
  assembly,
  wireframe,
  onState,
}: {
  target: ViewerTarget | null;
  assembly: ViewerModel | null;
  wireframe: boolean;
  onState: (state: ViewerState) => void;
}) {
  const mountRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!mountRef.current || !target) return undefined;

    let cancelled = false;
    let activeObject: THREE.Object3D | null = null;
    let frame = 0;
    const mount = mountRef.current;
    const scene = new THREE.Scene();
    scene.background = new THREE.Color("#101418");

    const camera = new THREE.PerspectiveCamera(38, mount.clientWidth / mount.clientHeight, 0.1, 5000);
    camera.position.set(210, -320, 190);

    const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(mount.clientWidth, mount.clientHeight);
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    mount.appendChild(renderer.domElement);

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.08;
    controls.target.set(0, 0, 0);

    const grid = new THREE.GridHelper(360, 18, "#52616f", "#2b333b");
    grid.rotation.x = Math.PI / 2;
    scene.add(grid);
    scene.add(new THREE.AxesHelper(70));
    scene.add(new THREE.HemisphereLight("#ffffff", "#44515e", 2.4));
    const key = new THREE.DirectionalLight("#ffffff", 2.8);
    key.position.set(220, -260, 340);
    scene.add(key);

    const frameObject = (object: THREE.Object3D) => {
      const box = new THREE.Box3().setFromObject(object);
      const center = box.getCenter(new THREE.Vector3());
      const size = box.getSize(new THREE.Vector3());
      object.position.sub(center);
      const maxAxis = Math.max(size.x, size.y, size.z, 20);
      camera.position.set(maxAxis * 1.25, -maxAxis * 1.75, maxAxis * 1.15);
      camera.near = Math.max(maxAxis / 800, 0.1);
      camera.far = maxAxis * 12;
      camera.updateProjectionMatrix();
      controls.target.set(0, 0, 0);
      controls.update();
    };

    const applyWireframe = (object: THREE.Object3D) => {
      object.traverse((child) => {
        if (child instanceof THREE.Mesh) {
          const materials = Array.isArray(child.material) ? child.material : [child.material];
          materials.forEach((material) => {
            if ("wireframe" in material) material.wireframe = wireframe;
          });
        }
      });
    };

    const showObject = (object: THREE.Object3D, state: ViewerState) => {
      if (cancelled) {
        disposeObject(object);
        return;
      }
      activeObject = object;
      applyWireframe(activeObject);
      frameObject(activeObject);
      scene.add(activeObject);
      onState(state);
    };

    onState("loading");
    const url = modelUrl(target.url);
    if (url) {
      new STLLoader().load(
        url,
        (geometry) => {
          geometry.computeVertexNormals();
          const material = new THREE.MeshStandardMaterial({
            color: target.id === "assembly" ? "#d47a4c" : "#60a5a1",
            roughness: 0.62,
            metalness: 0.12,
          });
          showObject(new THREE.Mesh(geometry, material), "stl");
        },
        undefined,
        () => {
          const fallback = target.id === "assembly" && assembly ? createFallbackAssembly(assembly) : createFallbackBox(target);
          showObject(fallback, "fallback");
        },
      );
    } else {
      const fallback = target.id === "assembly" && assembly ? createFallbackAssembly(assembly) : createFallbackBox(target);
      showObject(fallback, "fallback");
    }

    const render = () => {
      frame = window.requestAnimationFrame(render);
      controls.update();
      renderer.render(scene, camera);
    };
    render();

    const resize = () => {
      const width = mount.clientWidth;
      const height = mount.clientHeight;
      camera.aspect = width / height;
      camera.updateProjectionMatrix();
      renderer.setSize(width, height);
    };
    window.addEventListener("resize", resize);

    return () => {
      cancelled = true;
      window.cancelAnimationFrame(frame);
      window.removeEventListener("resize", resize);
      controls.dispose();
      if (activeObject) disposeObject(activeObject);
      renderer.dispose();
      mount.removeChild(renderer.domElement);
    };
  }, [assembly, onState, target, wireframe]);

  return <div className="viewer" ref={mountRef} aria-label="STL model viewer" />;
}

type JointAngles = {
  base: number;
  shoulder: number;
  elbow: number;
  wrist: number;
  gripper: number;
};

const homePose: JointAngles = { base: 0, shoulder: 0, elbow: 0, wrist: 0, gripper: 0 };
const jointLimits: Record<keyof JointAngles, [number, number]> = {
  base: [0, 360],
  shoulder: [-130, 130],
  elbow: [-135, 135],
  wrist: [-150, 18],
  gripper: [0, 24],
};
// Real hardware will vary; keep these two limits per joint easy to calibrate.
const jointMotion: Record<keyof JointAngles, { maxSpeed: number; acceleration: number }> = {
  base: { maxSpeed: 90, acceleration: 180 },
  shoulder: { maxSpeed: 70, acceleration: 140 },
  elbow: { maxSpeed: 80, acceleration: 160 },
  wrist: { maxSpeed: 100, acceleration: 200 },
  gripper: { maxSpeed: 16, acceleration: 32 },
};
const jointNames = Object.keys(homePose) as (keyof JointAngles)[];

function clampJoint(name: keyof JointAngles, value: number) {
  const [min, max] = jointLimits[name];
  return Math.max(min, Math.min(max, value));
}

function RobotSimulator() {
  const mountRef = useRef<HTMLDivElement | null>(null);
  const jointsRef = useRef({ ...homePose });
  const targetsRef = useRef({ ...homePose });
  const velocitiesRef = useRef({ ...homePose });
  const [joints, setJoints] = useState({ ...homePose });
  const [loaded, setLoaded] = useState(0);

  useEffect(() => {
    if (!mountRef.current) return undefined;
    const mount = mountRef.current;
    let frame = 0;
    const scene = new THREE.Scene();
    scene.background = new THREE.Color("#101418");
    const camera = new THREE.PerspectiveCamera(34, mount.clientWidth / mount.clientHeight, 0.1, 3000);
    camera.up.set(0, 0, 1);
    camera.position.set(650, -650, 560);
    camera.lookAt(0, 0, 260);
    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(mount.clientWidth, mount.clientHeight);
    mount.appendChild(renderer.domElement);
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.target.set(0, 0, 260);
    controls.enableDamping = true;
    controls.dampingFactor = 0.08;
    controls.minDistance = 280;
    controls.maxDistance = 1800;
    scene.add(new THREE.HemisphereLight("#ffffff", "#44515e", 2.5));
    const light = new THREE.DirectionalLight("#ffffff", 3);
    light.position.set(200, -250, 400);
    scene.add(light);
    const grid = new THREE.GridHelper(900, 30, "#52616f", "#2b333b");
    grid.rotation.x = Math.PI / 2;
    scene.add(grid);

    const base = new THREE.Group();
    const shoulder = new THREE.Group();
    const elbow = new THREE.Group();
    const wrist = new THREE.Group();
    const leftJaw = new THREE.Group();
    const rightJaw = new THREE.Group();
    shoulder.position.set(0, 0, 162.03);
    elbow.position.set(0, 0, 175.35);
    wrist.position.set(-6, 0, 167.33);
    scene.add(base);
    base.add(shoulder);
    shoulder.add(elbow);
    elbow.add(wrist);
    wrist.add(leftJaw, rightJaw);

    const load = (name: string, parent: THREE.Object3D, offset: [number, number, number], material: string | THREE.Material = "#d47a4c") => {
      new STLLoader().load(`${generatedBase}/models/${name}.stl`, (geometry) => {
        geometry.computeVertexNormals();
        const mesh = new THREE.Mesh(geometry, typeof material === "string"
          ? new THREE.MeshStandardMaterial({ color: material, roughness: 0.62, metalness: 0.12 })
          : material);
        mesh.position.set(...offset);
        parent.add(mesh);
        setLoaded((count) => count + 1);
      });
    };
    const loadPulley = (name: string, parent: THREE.Object3D, offset: [number, number, number]) => {
      const pivot = new THREE.Group();
      new STLLoader().load(`${generatedBase}/models/${name}.stl`, (geometry) => {
        geometry.computeVertexNormals();
        geometry.computeBoundingBox();
        const center = geometry.boundingBox!.getCenter(new THREE.Vector3());
        pivot.position.copy(center).add(new THREE.Vector3(...offset));
        const mesh = new THREE.Mesh(geometry, new THREE.MeshStandardMaterial({ color: "#e7b84b", roughness: 0.5, metalness: 0.2 }));
        mesh.position.copy(center).multiplyScalar(-1);
        pivot.add(mesh);
        parent.add(pivot);
        setLoaded((count) => count + 1);
      });
      return pivot;
    };
    const belt = (name: string, parent: THREE.Object3D, offset: [number, number, number]) => {
      const phase = { value: 0 };
      load(name, parent, offset, new THREE.ShaderMaterial({
        uniforms: { phase, beltColor: { value: new THREE.Color("#050505") } },
        vertexShader: "varying vec3 p; void main(){p=position;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0);}",
        fragmentShader: "uniform float phase;uniform vec3 beltColor;varying vec3 p;void main(){float stripe=step(.5,fract((p.y+p.z)/6.0+phase));gl_FragColor=vec4(beltColor+stripe*.04,1.0);}",
      }));
      return phase;
    };
    load("simulator_base_fixed", scene, [0, 0, 0], "#677985");
    load("simulator_base_yaw", base, [0, 0, 0]);
    load("simulator_upper_arm", shoulder, [0, 0, -162.03]);
    load("simulator_forearm", elbow, [0, 0, -337.38]);
    load("simulator_wrist_hardware", wrist, [6, 0, -504.71], "#8f9da6");
    load("simulator_gripper_base", wrist, [0, 0, 0], "#60a5a1");
    load("simulator_gripper_left", leftJaw, [0, 0, 0], "#60a5a1");
    load("simulator_gripper_right", rightJaw, [0, 0, 0], "#60a5a1");
    const shoulderDriver = loadPulley("simulator_shoulder_driver", base, [0, 0, 0]);
    loadPulley("simulator_shoulder_driven", shoulder, [0, 0, -162.03]);
    const shoulderBelt = belt("simulator_shoulder_belt", base, [0, 0, 0]);
    const elbowDriver = loadPulley("simulator_elbow_driver", shoulder, [0, 0, -162.03]);
    loadPulley("simulator_elbow_driven", elbow, [0, 0, -337.38]);
    const elbowBelt = belt("simulator_elbow_belt", shoulder, [0, 0, -162.03]);
    const wristDriver = loadPulley("simulator_wrist_driver", elbow, [0, 0, -337.38]);
    loadPulley("simulator_wrist_driven", wrist, [6, 0, -504.71]);
    const wristBelt = belt("simulator_wrist_belt", elbow, [0, 0, -337.38]);

    let lastTime = performance.now();
    let lastGamepadUpdate = 0;
    const render = (time = performance.now()) => {
      frame = requestAnimationFrame(render);
      const elapsed = Math.min((time - lastTime) / 1000, 0.05);
      const gamepad = navigator.getGamepads?.().find((pad) => pad?.connected);
      if (gamepad) {
        const axis = (index: number) => Math.abs(gamepad.axes[index] ?? 0) > 0.12 ? gamepad.axes[index] : 0;
        const targets = targetsRef.current;
        targets.base = (targets.base + axis(0) * 100 * elapsed + 360) % 360;
        targets.shoulder = clampJoint("shoulder", targets.shoulder - axis(1) * 80 * elapsed);
        targets.wrist = clampJoint("wrist", targets.wrist + axis(2) * 80 * elapsed);
        targets.elbow = clampJoint("elbow", targets.elbow - axis(3) * 80 * elapsed);
        targets.gripper = clampJoint("gripper", targets.gripper + ((gamepad.buttons[7]?.value ?? 0) - (gamepad.buttons[6]?.value ?? 0)) * 18 * elapsed);
        if (gamepad.buttons[0]?.pressed) Object.assign(targets, homePose);
        if (time - lastGamepadUpdate > 100) {
          setJoints({ ...targets });
          lastGamepadUpdate = time;
        }
      }
      lastTime = time;
      const pose = jointsRef.current;
      const velocities = velocitiesRef.current;
      jointNames.forEach((name) => {
        [pose[name], velocities[name]] = advanceMotion(
          pose[name], velocities[name], targetsRef.current[name],
          jointMotion[name].maxSpeed, jointMotion[name].acceleration, elapsed, name === "base",
        );
      });
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
      leftJaw.position.x = -pose.gripper / 2;
      rightJaw.position.x = pose.gripper / 2;
      controls.update();
      renderer.render(scene, camera);
    };
    render();
    const resize = () => {
      camera.aspect = mount.clientWidth / mount.clientHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(mount.clientWidth, mount.clientHeight);
    };
    window.addEventListener("resize", resize);
    return () => {
      cancelAnimationFrame(frame);
      window.removeEventListener("resize", resize);
      controls.dispose();
      scene.traverse((child) => {
        if (child instanceof THREE.Mesh) {
          child.geometry.dispose();
          (Array.isArray(child.material) ? child.material : [child.material]).forEach((material) => material.dispose());
        }
      });
      renderer.dispose();
      mount.removeChild(renderer.domElement);
    };
  }, []);

  const setJoint = (name: keyof JointAngles, value: number) => {
    const next = { ...targetsRef.current, [name]: clampJoint(name, value) };
    targetsRef.current = next;
    setJoints(next);
  };
  const nudge = (name: keyof JointAngles, amount: number) => {
    const value = targetsRef.current[name] + amount;
    setJoint(name, name === "base" ? (value + 360) % 360 : value);
  };

  return (
    <main className="simulator-page">
      <header className="simulator-header">
        <div><p className="eyebrow">Robot Arm Build Lab</p><h1>Master Assembly Simulator</h1></div>
        <a href={import.meta.env.BASE_URL}>Back to model explorer</a>
      </header>
      <div className="simulator-layout">
        <div className="simulator-view" ref={mountRef} aria-label="Articulated robot arm simulator" />
        <div className="simulator-controls">
          <p>{loaded}/17 CAD and drivetrain meshes loaded</p>
          {([
            ["base", "Base yaw", 0, 360, "°"],
            ["shoulder", "Shoulder", -130, 130, "°"],
            ["elbow", "Elbow", -135, 135, "°"],
            ["wrist", "Wrist pitch", -150, 18, "°"],
            ["gripper", "Gripper opening", 0, 24, " mm"],
          ] as const).map(([name, label, min, max, unit]) => (
            <label key={name}>
              <span>{label}<strong>{joints[name]}{unit}</strong></span>
              <input aria-label={label} type="range" min={min} max={max} value={joints[name]} onChange={(event) => setJoint(name, Number(event.target.value))} />
            </label>
          ))}
          <div className="controller-pads">
            <div className="d-pad" aria-label="Base and shoulder controls">
              <button type="button" aria-label="Shoulder forward" onClick={() => nudge("shoulder", 5)}>▲</button>
              <button type="button" aria-label="Base left" onClick={() => nudge("base", -5)}>◀</button>
              <span>L</span>
              <button type="button" aria-label="Base right" onClick={() => nudge("base", 5)}>▶</button>
              <button type="button" aria-label="Shoulder back" onClick={() => nudge("shoulder", -5)}>▼</button>
            </div>
            <div className="d-pad" aria-label="Elbow and wrist controls">
              <button type="button" aria-label="Elbow forward" onClick={() => nudge("elbow", 5)}>▲</button>
              <button type="button" aria-label="Wrist back" onClick={() => nudge("wrist", -5)}>◀</button>
              <span>R</span>
              <button type="button" aria-label="Wrist forward" onClick={() => nudge("wrist", 5)}>▶</button>
              <button type="button" aria-label="Elbow back" onClick={() => nudge("elbow", -5)}>▼</button>
            </div>
          </div>
          <div className="gripper-buttons">
            <button type="button" onClick={() => nudge("gripper", -2)}>Close</button>
            <button type="button" onClick={() => nudge("gripper", 2)}>Open</button>
          </div>
          <button type="button" onClick={() => { targetsRef.current = { ...homePose }; setJoints({ ...homePose }); }}>Home all joints</button>
          <small>Drag to orbit, scroll to zoom. Xbox: left stick = base/shoulder, right stick = wrist/elbow, triggers = gripper, A = home.</small>
        </div>
      </div>
    </main>
  );
}

function App() {
  const { data: catalog, error: catalogError } = useJson<Catalog>(`${generatedBase}/catalog.json`);
  const { data: viewerModel, error: viewerError } = useJson<ViewerModel>(`${generatedBase}/viewer-model.json`);
  const { data: progress } = useJson<ProgressFeed>(`${generatedBase}/progress.json`);
  const [selectedId, setSelectedId] = useState("assembly");
  const [wireframe, setWireframe] = useState(false);
  const [viewerState, setViewerState] = useState<ViewerState>("loading");

  const buildNotes = useMemo(
    () => Object.entries(buildLogModules).map(([path, raw]) => parseNote(raw, path)).sort((a, b) => b.path.localeCompare(a.path)),
    [],
  );
  const decisions = useMemo(
    () => Object.entries(designDecisionModules).map(([path, raw]) => parseNote(raw, path)).sort((a, b) => b.path.localeCompare(a.path)),
    [],
  );

  const assemblyTarget = useMemo<ViewerTarget | null>(() => {
    const assemblyPart = catalog?.parts.find((part) => part.name === "robot_arm_master_assembly");
    return {
      id: "assembly",
      title: "Robot Arm Master Assembly",
      subtitle: "Full exported STL",
      url: assemblyPart?.webModel ?? "generated/models/robot_arm_master_assembly.stl",
      bbox: assemblyPart?.bbox ?? null,
    };
  }, [catalog]);

  const selectedPart = useMemo(
    () => catalog?.parts.find((part) => part.name === selectedId) ?? null,
    [catalog, selectedId],
  );
  const selectedTarget = useMemo<ViewerTarget | null>(() => {
    if (selectedId === "assembly") return assemblyTarget;
    if (!selectedPart) return null;
    return {
      id: selectedPart.name,
      title: selectedPart.title,
      subtitle: `${selectedPart.status} / ${selectedPart.category}`,
      url: selectedPart.webModel,
      bbox: selectedPart.bbox,
    };
  }, [assemblyTarget, selectedId, selectedPart]);

  const printableCount = catalog?.parts.filter((part) => part.printReady).length ?? 0;
  const generatedAt = catalog ? new Date(catalog.generatedAt).toLocaleString() : "pending";
  const statusText = viewerState === "stl" ? "STL loaded" : viewerState === "fallback" ? "STL missing, showing generated bounds" : "Loading model";

  return (
    <main>
      <section className="workbench">
        <aside className="sidebar">
          <div className="brand-block">
            <p className="eyebrow">Robot Arm Build Lab</p>
            <h1>Billy Bitcoin's Robot Arm</h1>
          </div>

          <div className="metric-grid" aria-label="Current build status">
            <div>
              <span>Status</span>
              <strong>Active CAD prototype</strong>
            </div>
            <div>
              <span>Models</span>
              <strong>{catalog?.parts.length ?? 0}</strong>
            </div>
            <div>
              <span>Print candidates</span>
              <strong>{printableCount}</strong>
            </div>
            <div>
              <span>Generated</span>
              <strong>{generatedAt}</strong>
            </div>
          </div>

          <div className="panel">
            <div className="panel-heading">
              <h2>Model Files</h2>
              <span>{statusText}</span>
            </div>
            <div className="model-list">
              <button
                className={selectedId === "assembly" ? "model-row is-active" : "model-row"}
                type="button"
                onClick={() => setSelectedId("assembly")}
              >
                <strong>Full assembly</strong>
                <span>generated/models/robot_arm_master_assembly.stl</span>
              </button>
              {catalog?.parts
                .filter((part) => part.name !== "robot_arm_master_assembly")
                .map((part) => (
                  <button
                    className={selectedId === part.name ? "model-row is-active" : "model-row"}
                    key={part.name}
                    type="button"
                    onClick={() => setSelectedId(part.name)}
                  >
                    <strong>{part.title}</strong>
                    <span>{part.webModel}</span>
                  </button>
                ))}
            </div>
          </div>
        </aside>

        <section className="viewer-column">
          <header className="viewer-toolbar">
            <div>
              <p className="eyebrow">STL Viewer</p>
              <h2>{selectedTarget?.title ?? "Loading model"}</h2>
              <span>{selectedTarget?.subtitle ?? "Generated CAD asset"}</span>
            </div>
            <div className="viewer-actions">
              <a href={`${import.meta.env.BASE_URL}simulator/`}>Open Simulator</a>
              <label>
                <input type="checkbox" checked={wireframe} onChange={(event) => setWireframe(event.target.checked)} />
                Wireframe
              </label>
              {selectedTarget?.url && (
                <a href={modelUrl(selectedTarget.url) ?? "#"} download>
                  Download STL
                </a>
              )}
            </div>
          </header>

          <ModelViewer target={selectedTarget} assembly={viewerModel} wireframe={wireframe} onState={setViewerState} />
          {(catalogError || viewerError) && <p className="data-warning">Generated metadata is missing: {catalogError || viewerError}</p>}

          <div className="inspection-strip">
            <article>
              <span>Size</span>
              <strong>{selectedTarget?.bbox?.size.map((value) => value.toFixed(1)).join(" x ") ?? "unknown"} mm</strong>
            </article>
            <article>
              <span>Source</span>
              <strong>{selectedPart?.source ?? "models/master_assembly.py"}</strong>
            </article>
            <article>
              <span>Artifact</span>
              <strong>{selectedTarget?.url ?? "pending"}</strong>
            </article>
          </div>
        </section>
      </section>

      <section className="section split">
        <div>
          <div className="section-heading">
            <p className="eyebrow">Design Pipeline</p>
            <h2>Idea to Physical Test</h2>
          </div>
          <ol className="pipeline">
            <li>Voice or design note</li>
            <li>LLM-assisted prompt and code branch</li>
            <li>Python build123d source</li>
            <li>CI-rendered STL/STEP artifacts</li>
            <li>Review, merge, print, fit test</li>
          </ol>
        </div>
        <div>
          <div className="section-heading">
            <p className="eyebrow">Active Questions</p>
            <h2>Fit Checks</h2>
          </div>
          <ul className="question-list">
            <li>Shoulder stack belt and bearing spacing after first print.</li>
            <li>Wire service loop clearance through base rotation.</li>
            <li>Wrist motor mass and end-effector stiffness.</li>
          </ul>
        </div>
      </section>

      <section className="section">
        <div className="section-heading">
          <p className="eyebrow">Parts Board</p>
          <h2>{catalog?.parts.length ?? 0} source models, {printableCount} print-ready candidates</h2>
        </div>
        <div className="parts-table" role="table" aria-label="Generated part catalog">
          <div className="parts-header" role="row">
            <span>Name</span>
            <span>Status</span>
            <span>Size</span>
            <span>STL</span>
          </div>
          {catalog?.parts.map((part) => (
            <button className="parts-row" key={part.name} role="row" type="button" onClick={() => setSelectedId(part.name)}>
              <span>{part.title}</span>
              <span>{part.status}</span>
              <span>{part.bbox.size.map((value) => value.toFixed(1)).join(" x ")}</span>
              <span>{part.webModel.split("/").pop()}</span>
            </button>
          ))}
        </div>
      </section>

      <section className="section split">
        <div>
          <div className="section-heading">
            <p className="eyebrow">Build Log</p>
            <h2>Chronological Notes</h2>
          </div>
          <div className="note-list">
            {buildNotes.map((note) => (
              <article key={note.path}>
                <h3>{note.title}</h3>
                <p>{note.body}</p>
              </article>
            ))}
          </div>
        </div>
        <div>
          <div className="section-heading">
            <p className="eyebrow">Design Decisions</p>
            <h2>Public Rationale</h2>
          </div>
          <div className="note-list">
            {decisions.map((note) => (
              <article key={note.path}>
                <h3>{note.title}</h3>
                <p>{note.body}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="section">
        <div className="section-heading">
          <p className="eyebrow">Public Progress</p>
          <h2>Generated Feed</h2>
        </div>
        <div className="progress-feed">
          {(progress?.commits.length ? progress.commits : [{ sha: "local", date: "pending", subject: "No git commits generated yet." }]).map((commit) => (
            <article key={`${commit.sha}-${commit.subject}`}>
              <strong>{commit.sha}</strong>
              <span>{commit.date}</span>
              <p>{commit.subject}</p>
            </article>
          ))}
        </div>
      </section>
    </main>
  );
}

createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    {window.location.pathname.endsWith("/simulator/") ? <RobotSimulator /> : <App />}
  </React.StrictMode>,
);
