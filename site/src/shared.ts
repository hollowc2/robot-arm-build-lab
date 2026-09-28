import { useEffect, useState } from "react";
import * as THREE from "three";
import type { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";

export type BoundingBox = {
  min: [number, number, number];
  max: [number, number, number];
  size: [number, number, number];
};

export type CatalogPart = {
  name: string;
  title: string;
  module: string;
  source: string;
  category: string;
  status: string;
  printReady: boolean;
  material?: string;
  printOrientation?: string;
  volumeMm3: number;
  bbox: BoundingBox;
  webModel: string;
};

export type Catalog = {
  project: string;
  generatedAt: string;
  parts: CatalogPart[];
};

export type ProgressFeed = {
  generatedAt: string;
  commits: { sha: string; date: string; subject: string }[];
  note: string;
};

export const generatedBase = `${import.meta.env.BASE_URL}generated`;
export const repoUrl = "https://github.com/hollowc2/robot-arm-build-lab";
export const pageBackground = "#0b0d0f";

export function useJson<T>(path: string) {
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

export function modelUrl(path: string) {
  return `${import.meta.env.BASE_URL}${path}`;
}

export function formatSize(size: [number, number, number]) {
  return size.map((value) => Math.round(value)).join(" × ");
}

export function prefersReducedMotion() {
  return window.matchMedia?.("(prefers-reduced-motion: reduce)").matches ?? false;
}

// Page scroll wins over the viewer: the wheel only zooms while Ctrl/Cmd is held
// (trackpad pinch sends ctrlKey too). Touch pinch always zooms.
export function guardWheelZoom(element: HTMLElement, controls: OrbitControls) {
  const onWheel = (event: WheelEvent) => {
    controls.enableZoom = event.ctrlKey || event.metaKey;
  };
  const onPointer = () => {
    controls.enableZoom = true;
  };
  element.addEventListener("wheel", onWheel, { capture: true, passive: true });
  element.addEventListener("pointerdown", onPointer, { capture: true });
  return () => {
    element.removeEventListener("wheel", onWheel, { capture: true });
    element.removeEventListener("pointerdown", onPointer, { capture: true });
  };
}

// Skip rendering while the canvas is scrolled out of view.
export function watchVisibility(element: HTMLElement, onChange: (visible: boolean) => void) {
  const observer = new IntersectionObserver(([entry]) => onChange(entry.isIntersecting), { rootMargin: "120px" });
  observer.observe(element);
  return () => observer.disconnect();
}

export function disposeObject(object: THREE.Object3D) {
  object.traverse((child) => {
    if (child instanceof THREE.Mesh || child instanceof THREE.LineSegments) {
      child.geometry.dispose();
      const materials = Array.isArray(child.material) ? child.material : [child.material];
      materials.forEach((material: THREE.Material & { map?: THREE.Texture | null }) => {
        material.map?.dispose();
        material.dispose();
      });
    }
  });
}

export function radialGlowTexture(inner: string, outer: string) {
  const canvas = document.createElement("canvas");
  canvas.width = canvas.height = 256;
  const context = canvas.getContext("2d")!;
  const gradient = context.createRadialGradient(128, 128, 0, 128, 128, 128);
  gradient.addColorStop(0, inner);
  gradient.addColorStop(1, outer);
  context.fillStyle = gradient;
  context.fillRect(0, 0, 256, 256);
  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  return texture;
}
