import React, { useEffect, useMemo, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { STLLoader } from "three/examples/jsm/loaders/STLLoader.js";
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

  const selectedPart = catalog?.parts.find((part) => part.name === selectedId) ?? null;
  const selectedTarget = selectedId === "assembly"
    ? assemblyTarget
    : selectedPart && {
        id: selectedPart.name,
        title: selectedPart.title,
        subtitle: `${selectedPart.status} / ${selectedPart.category}`,
        url: selectedPart.webModel,
        bbox: selectedPart.bbox,
      };

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
    <App />
  </React.StrictMode>,
);
