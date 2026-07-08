import React, { useEffect, useMemo, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import * as THREE from "three";
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

function statusColor(name: string) {
  const palette = ["#d76f45", "#4f8f86", "#c5a84f", "#6f86c8", "#8f6d58", "#5f9f68"];
  let hash = 0;
  for (const char of name) hash = (hash + char.charCodeAt(0)) % palette.length;
  return palette[hash];
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

function ModelViewer({ model }: { model: ViewerModel | null }) {
  const mountRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!mountRef.current || !model) return undefined;

    const mount = mountRef.current;
    const scene = new THREE.Scene();
    scene.background = new THREE.Color("#f7f4ee");

    const camera = new THREE.PerspectiveCamera(35, mount.clientWidth / mount.clientHeight, 1, 2000);
    camera.position.set(250, -340, 240);

    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(mount.clientWidth, mount.clientHeight);
    mount.appendChild(renderer.domElement);

    const group = new THREE.Group();
    const materialByName = new Map<string, THREE.MeshStandardMaterial>();
    model.parts.forEach((part) => {
      const [width, depth, height] = part.bbox.size;
      const geometry = new THREE.BoxGeometry(Math.max(width, 0.5), Math.max(depth, 0.5), Math.max(height, 0.5));
      const material = new THREE.MeshStandardMaterial({
        color: statusColor(part.name),
        roughness: 0.66,
        metalness: 0.08,
        transparent: part.status !== "active",
        opacity: part.status === "active" ? 0.88 : 0.46,
      });
      materialByName.set(part.name, material);
      const mesh = new THREE.Mesh(geometry, material);
      mesh.position.set(
        (part.bbox.min[0] + part.bbox.max[0]) / 2,
        (part.bbox.min[1] + part.bbox.max[1]) / 2,
        (part.bbox.min[2] + part.bbox.max[2]) / 2,
      );
      group.add(mesh);
    });

    const box = new THREE.Box3().setFromObject(group);
    const center = box.getCenter(new THREE.Vector3());
    group.position.sub(center);
    scene.add(group);

    const ambient = new THREE.HemisphereLight("#ffffff", "#b9aa93", 2.1);
    const key = new THREE.DirectionalLight("#ffffff", 2.5);
    key.position.set(150, -220, 360);
    scene.add(ambient, key);
    scene.add(new THREE.GridHelper(360, 12, "#b9aa93", "#ddd4c7"));

    let frame = 0;
    const render = () => {
      frame = window.requestAnimationFrame(render);
      group.rotation.z += 0.003;
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
      window.cancelAnimationFrame(frame);
      window.removeEventListener("resize", resize);
      renderer.dispose();
      mount.removeChild(renderer.domElement);
      materialByName.forEach((material) => material.dispose());
      group.traverse((object) => {
        if (object instanceof THREE.Mesh) object.geometry.dispose();
      });
    };
  }, [model]);

  return <div className="viewer" ref={mountRef} aria-label="Current robot assembly viewer" />;
}

function App() {
  const { data: catalog, error: catalogError } = useJson<Catalog>(`${generatedBase}/catalog.json`);
  const { data: viewerModel, error: viewerError } = useJson<ViewerModel>(`${generatedBase}/viewer-model.json`);
  const { data: progress } = useJson<ProgressFeed>(`${generatedBase}/progress.json`);
  const [hiddenParts, setHiddenParts] = useState<Set<string>>(new Set());

  const buildNotes = useMemo(
    () => Object.entries(buildLogModules).map(([path, raw]) => parseNote(raw, path)).sort((a, b) => b.path.localeCompare(a.path)),
    [],
  );
  const decisions = useMemo(
    () => Object.entries(designDecisionModules).map(([path, raw]) => parseNote(raw, path)).sort((a, b) => b.path.localeCompare(a.path)),
    [],
  );

  const visibleViewerModel = useMemo(() => {
    if (!viewerModel) return null;
    return { ...viewerModel, parts: viewerModel.parts.filter((part) => !hiddenParts.has(part.name)) };
  }, [hiddenParts, viewerModel]);

  const printableCount = catalog?.parts.filter((part) => part.printReady).length ?? 0;
  const generatedAt = catalog ? new Date(catalog.generatedAt).toLocaleString() : "pending";

  return (
    <main>
      <section className="hero">
        <div className="hero-copy">
          <p className="eyebrow">Public workshop dashboard</p>
          <h1>Billy Bitcoin's Robot Arm Build Lab</h1>
          <div className="status-grid" aria-label="Current build status">
            <div>
              <span>Build status</span>
              <strong>Active CAD prototype</strong>
            </div>
            <div>
              <span>Latest milestone</span>
              <strong>Dashboard monorepo scaffold</strong>
            </div>
            <div>
              <span>Generated</span>
              <strong>{generatedAt}</strong>
            </div>
          </div>
          <div className="questions">
            <span>Active design questions</span>
            <ul>
              <li>Shoulder stack belt and bearing spacing after first print.</li>
              <li>Wire service loop clearance through base rotation.</li>
              <li>Wrist motor mass and end-effector stiffness.</li>
            </ul>
          </div>
        </div>
        <ModelViewer model={visibleViewerModel} />
        {(catalogError || viewerError) && <p className="data-warning">Generated metadata is missing: {catalogError || viewerError}</p>}
      </section>

      <section className="section two-column">
        <div>
          <div className="section-heading">
            <p className="eyebrow">Current Model</p>
            <h2>Assembly Layers</h2>
          </div>
          <div className="toggle-grid">
            {viewerModel?.parts.slice(0, 18).map((part) => (
              <button
                className={hiddenParts.has(part.name) ? "part-toggle is-muted" : "part-toggle"}
                key={part.name}
                type="button"
                onClick={() =>
                  setHiddenParts((current) => {
                    const next = new Set(current);
                    if (next.has(part.name)) next.delete(part.name);
                    else next.add(part.name);
                    return next;
                  })
                }
              >
                <span style={{ backgroundColor: statusColor(part.name) }} />
                {part.name.replaceAll("_", " ")}
              </button>
            ))}
          </div>
        </div>
        <div>
          <div className="section-heading">
            <p className="eyebrow">Design Pipeline</p>
            <h2>Idea to Physical Test</h2>
          </div>
          <ol className="pipeline">
            <li>Voice or design note</li>
            <li>LLM-assisted prompt and code branch</li>
            <li>Python build123d source</li>
            <li>CI-rendered preview and printable artifact</li>
            <li>Human review, merge, print, and fit test</li>
          </ol>
        </div>
      </section>

      <section className="section">
        <div className="section-heading">
          <p className="eyebrow">Parts Board</p>
          <h2>{catalog?.parts.length ?? 0} source models, {printableCount} print-ready candidates</h2>
        </div>
        <div className="parts-board">
          {catalog?.parts.map((part) => (
            <article className="part-card" key={part.name}>
              <div>
                <h3>{part.title}</h3>
                <p>{part.source}</p>
              </div>
              <dl>
                <div><dt>Status</dt><dd>{part.status}</dd></div>
                <div><dt>Category</dt><dd>{part.category}</dd></div>
                <div><dt>Size</dt><dd>{part.bbox.size.map((value) => `${value.toFixed(1)}`).join(" x ")} mm</dd></div>
                <div><dt>Print</dt><dd>{part.printReady ? "ready for review" : "reference"}</dd></div>
              </dl>
            </article>
          ))}
        </div>
      </section>

      <section className="section two-column">
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
