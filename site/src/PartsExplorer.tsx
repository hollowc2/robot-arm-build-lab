import { useEffect, useMemo, useRef, useState } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { STLLoader } from "three/examples/jsm/loaders/STLLoader.js";
import { toCreasedNormals } from "three/examples/jsm/utils/BufferGeometryUtils.js";
import {
  type CatalogPart,
  disposeObject,
  formatSize,
  guardWheelZoom,
  modelUrl,
  pageBackground,
  prefersReducedMotion,
  repoUrl,
  watchVisibility,
} from "./shared";

type ViewerState = "idle" | "loading" | "stl" | "error";

const categoryOrder = ["base", "arm", "drive", "end effector", "electronics", "safety", "hardware", "reference"];

function PartViewer({ part }: { part: CatalogPart }) {
  const mountRef = useRef<HTMLDivElement | null>(null);
  const showRef = useRef<(part: CatalogPart) => void>(() => undefined);
  const [state, setState] = useState<ViewerState>("idle");

  useEffect(() => {
    if (!mountRef.current) return undefined;
    const mount = mountRef.current;
    let animation = 0;
    let disposed = false;
    let visible = false;
    let pending: CatalogPart | null = null;
    let request = 0;
    let current: THREE.Object3D | null = null;

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(pageBackground);
    const camera = new THREE.PerspectiveCamera(30, 1, 0.5, 5000);
    camera.up.set(0, 0, 1);
    const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    mount.appendChild(renderer.domElement);
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.08;
    controls.enablePan = false;
    controls.autoRotate = !prefersReducedMotion();
    controls.autoRotateSpeed = 1.1;
    controls.addEventListener("start", () => {
      controls.autoRotate = false;
    });
    const stopWheelGuard = guardWheelZoom(mount, controls);
    scene.add(new THREE.HemisphereLight("#fff3e6", "#15181b", 1.8));
    const key = new THREE.DirectionalLight("#ffffff", 2.4);
    key.position.set(1, -1.3, 2);
    camera.add(key);
    scene.add(camera);
    const rim = new THREE.DirectionalLight("#86b4ff", 1.2);
    rim.position.set(-2, 2, 1);
    scene.add(rim);

    let fitRadius = 0;
    const frame = () => {
      if (!fitRadius) return;
      const halfFov = THREE.MathUtils.degToRad(camera.fov / 2);
      const narrowestHalfFov = Math.min(halfFov, Math.atan(Math.tan(halfFov) * camera.aspect));
      const distance = (fitRadius / Math.sin(narrowestHalfFov)) * 1.15;
      camera.position.sub(controls.target).setLength(distance).add(controls.target);
      camera.near = distance / 100;
      camera.far = distance * 20;
      camera.updateProjectionMatrix();
      controls.minDistance = fitRadius * 1.2;
      controls.maxDistance = distance * 3;
      controls.update();
    };

    const loader = new STLLoader();
    const show = (target: CatalogPart) => {
      if (!visible) {
        pending = target;
        return;
      }
      const id = ++request;
      setState("loading");
      loader.load(
        modelUrl(target.webModel),
        (raw) => {
          if (disposed || id !== request) {
            raw.dispose();
            return;
          }
          const geometry = toCreasedNormals(raw, Math.PI / 6);
          raw.dispose();
          geometry.computeBoundingBox();
          const box = geometry.boundingBox!;
          const center = box.getCenter(new THREE.Vector3());
          geometry.translate(-center.x, -center.y, -box.min.z);
          const size = box.getSize(new THREE.Vector3());

          const group = new THREE.Group();
          const reference = target.category === "reference" || target.category === "hardware";
          group.add(new THREE.Mesh(geometry, new THREE.MeshStandardMaterial({
            color: reference ? "#9aa5ad" : "#e2743f",
            roughness: reference ? 0.4 : 0.56,
            metalness: reference ? 0.35 : 0.06,
          })));
          const span = Math.max(60, Math.ceil((Math.max(size.x, size.y) * 1.7) / 20) * 20);
          const grid = new THREE.GridHelper(span, span / 10, "#343b42", "#20252a");
          grid.rotation.x = Math.PI / 2;
          group.add(grid);

          if (current) {
            scene.remove(current);
            disposeObject(current);
          }
          current = group;
          scene.add(group);

          fitRadius = Math.max(size.length() / 2, 12);
          controls.target.set(0, 0, size.z / 2);
          camera.position.copy(controls.target).add(new THREE.Vector3(1, -1.25, 0.75));
          frame();
          setState("stl");
        },
        undefined,
        () => {
          if (!disposed && id === request) setState("error");
        },
      );
    };
    showRef.current = show;
    const stopWatching = watchVisibility(mount, (isVisible) => {
      visible = isVisible;
      if (visible && pending) {
        const next = pending;
        pending = null;
        show(next);
      }
    });

    const resize = () => {
      const width = mount.clientWidth;
      const height = mount.clientHeight;
      if (!width || !height) return;
      renderer.setSize(width, height);
      camera.aspect = width / height;
      camera.updateProjectionMatrix();
      frame();
    };
    const resizeObserver = new ResizeObserver(resize);
    resizeObserver.observe(mount);
    resize();

    const render = () => {
      animation = requestAnimationFrame(render);
      if (!visible) return;
      controls.update();
      renderer.render(scene, camera);
    };
    render();

    return () => {
      disposed = true;
      showRef.current = () => undefined;
      cancelAnimationFrame(animation);
      resizeObserver.disconnect();
      stopWheelGuard();
      stopWatching();
      controls.dispose();
      disposeObject(scene);
      renderer.dispose();
      mount.removeChild(renderer.domElement);
    };
  }, []);

  useEffect(() => {
    showRef.current(part);
  }, [part]);

  return (
    <div className="part-stage" data-state={state}>
      <div className="part-canvas" ref={mountRef} aria-label={`3D view of ${part.title}`} />
      {state === "loading" && <span className="stage-note">Loading STL…</span>}
      {state === "error" && <span className="stage-note">STL not exported yet</span>}
      <span className="stage-scale">Grid 10 mm</span>
    </div>
  );
}

export function PartsExplorer({ parts }: { parts: CatalogPart[] }) {
  const buildable = useMemo(() => parts.filter((part) => part.category !== "assembly"), [parts]);
  const assembly = parts.find((part) => part.category === "assembly");
  const [selectedName, setSelectedName] = useState<string | null>(null);
  const selected = buildable.find((part) => part.name === selectedName) ?? buildable[0];
  const groups = useMemo(() => {
    const byCategory = new Map<string, CatalogPart[]>();
    buildable.forEach((part) => byCategory.set(part.category, [...(byCategory.get(part.category) ?? []), part]));
    const rank = (category: string) => (categoryOrder.indexOf(category) + categoryOrder.length + 1) % (categoryOrder.length + 1);
    return [...byCategory.entries()].sort(([a], [b]) => rank(a) - rank(b));
  }, [buildable]);

  if (!selected) return null;

  return (
    <div className="parts">
      <div className="part-view ticks">
        <PartViewer part={selected} />
        <div className="part-meta">
          <div>
            <p className="part-kicker">{selected.category}</p>
            <h3>{selected.title}</h3>
          </div>
          <dl className="part-facts">
            <div><dt>Size</dt><dd>{formatSize(selected.bbox.size)} mm</dd></div>
            <div><dt>Material</dt><dd>{selected.printReady ? selected.material ?? "PETG" : "Off the shelf"}</dd></div>
            <div><dt>Status</dt><dd><span className={`badge badge-${selected.status}`}>{selected.status}</span></dd></div>
            {selected.printReady && selected.printOrientation && (
              <div><dt>Print</dt><dd>{selected.printOrientation}</dd></div>
            )}
          </dl>
          <div className="part-actions">
            <a className="button button-primary" href={modelUrl(selected.webModel)} download>Download STL</a>
            <a className="button" href={`${repoUrl}/blob/main/${selected.source}`} target="_blank" rel="noreferrer">View source ↗</a>
          </div>
        </div>
      </div>
      <div className="part-list">
        {groups.map(([category, members]) => (
          <div className="part-group" key={category}>
            <p className="part-group-label">{category}</p>
            {members.map((part) => (
              <button
                className="part-row"
                key={part.name}
                type="button"
                aria-pressed={part.name === selected.name}
                onClick={() => setSelectedName(part.name)}
              >
                <span className="part-row-title">{part.title}</span>
                <span className="part-row-size">{formatSize(part.bbox.size)}</span>
              </button>
            ))}
          </div>
        ))}
        {assembly && (
          <a className="part-assembly" href={modelUrl(assembly.webModel)} download>
            <span>Full assembly STL</span>
            <span>{formatSize(assembly.bbox.size)} mm · large download</span>
          </a>
        )}
      </div>
    </div>
  );
}
