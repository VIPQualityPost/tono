import React, { useRef, useEffect, useCallback } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';

/**
 * Interactive 3D surface viewer using Three.js.
 * Props:
 *   meshData: { width, height, z_data (b64 float32), colors (b64 uint8 RGB),
 *               z_min, z_max, z_scale, x_range, y_range }
 */
export default function SurfaceView({ meshData, nodeId, widgetValues, runtimeValues, onRuntimeValuesChange }) {
  const containerRef = useRef(null);
  const threeRef = useRef(null); // { renderer, scene, camera, controls, mesh }
  const syncTimerRef = useRef(null);
  const lastSnapshotRef = useRef('');
  const lastAnglesRef = useRef({ azimuth: null, polar: null, distance: null });
  const hasSyncedInitialSnapshotRef = useRef(false);

  // Decode base64 to typed arrays
  const decode = useCallback((b64, ArrayType) => {
    const bin = atob(b64);
    const bytes = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
    return new ArrayType(bytes.buffer);
  }, []);

  const syncViewportState = useCallback((scheduleRun = false) => {
    const state = threeRef.current;
    if (!state || !nodeId || !onRuntimeValuesChange) return;
    const { renderer, controls } = state;
    const azimuth = Number(controls.getAzimuthalAngle().toFixed(4));
    const polar = Number(controls.getPolarAngle().toFixed(4));
    const distance = Number(controls.getDistance().toFixed(4));
    const snapshot = renderer.domElement.toDataURL('image/png');
    const previous = lastAnglesRef.current;
    const patch = {};
    if (previous.azimuth !== azimuth) patch.camera_azimuth = azimuth;
    if (previous.polar !== polar) patch.camera_polar = polar;
    if (previous.distance !== distance) patch.camera_distance = distance;
    if (snapshot !== lastSnapshotRef.current) patch.viewport_snapshot = snapshot;
    if (Object.keys(patch).length > 0) {
      onRuntimeValuesChange(nodeId, patch, { scheduleRun });
      lastAnglesRef.current = { azimuth, polar, distance };
      lastSnapshotRef.current = snapshot;
    }
  }, [nodeId, onRuntimeValuesChange]);

  const scheduleViewportSync = useCallback((delay = 120, scheduleRun = false) => {
    if (syncTimerRef.current) {
      clearTimeout(syncTimerRef.current);
    }
    syncTimerRef.current = setTimeout(() => {
      syncTimerRef.current = null;
      syncViewportState(scheduleRun);
    }, delay);
  }, [syncViewportState]);

  const applyCameraState = useCallback((azimuth, polar, distance) => {
    const state = threeRef.current;
    if (!state) return;
    const { camera, controls } = state;
    const target = controls.target.clone();
    const spherical = new THREE.Spherical(
      Math.max(0.3, Number.isFinite(distance) ? distance : 1.8),
      THREE.MathUtils.clamp(Number.isFinite(polar) ? polar : 1.1, 0.01, Math.PI - 0.01),
      Number.isFinite(azimuth) ? azimuth : 0.0,
    );
    const offset = new THREE.Vector3().setFromSpherical(spherical);
    camera.position.copy(target).add(offset);
    controls.update();
  }, []);

  // Initialize Three.js scene once
  useEffect(() => {
    const container = containerRef.current;
    if (!container || threeRef.current) return;

    const width = container.clientWidth;
    const height = width; // 1:1 aspect

    const renderer = new THREE.WebGLRenderer({
      antialias: true,
      alpha: false,
      preserveDrawingBuffer: true,
    });
    renderer.setSize(width, height);
    renderer.setPixelRatio(window.devicePixelRatio);
    renderer.setClearColor(0x0f172a);
    container.appendChild(renderer.domElement);

    const scene = new THREE.Scene();

    const camera = new THREE.PerspectiveCamera(45, 1, 0.01, 1000);
    camera.position.set(1.2, 0.8, 1.2);

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.1;
    controls.minDistance = 0.3;
    controls.maxDistance = 10;
    const handleControlsEnd = () => scheduleViewportSync(0, true);
    controls.addEventListener('end', handleControlsEnd);

    // Lighting
    const ambient = new THREE.AmbientLight(0xffffff, 0.4);
    scene.add(ambient);
    const dir = new THREE.DirectionalLight(0xffffff, 0.8);
    dir.position.set(1, 2, 1.5);
    scene.add(dir);
    const dir2 = new THREE.DirectionalLight(0xffffff, 0.3);
    dir2.position.set(-1, 0.5, -1);
    scene.add(dir2);

    // Animation loop
    let animId;
    const animate = () => {
      animId = requestAnimationFrame(animate);
      controls.update();
      renderer.render(scene, camera);
    };
    animate();

    threeRef.current = { renderer, scene, camera, controls, mesh: null, animId };
    applyCameraState(
      Number(runtimeValues?.camera_azimuth ?? widgetValues?.camera_azimuth),
      Number(runtimeValues?.camera_polar ?? widgetValues?.camera_polar),
      Number(runtimeValues?.camera_distance ?? widgetValues?.camera_distance),
    );

    // Resize observer to maintain 1:1 aspect when node width changes
    const ro = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (!entry || !threeRef.current) return;
      const w = entry.contentRect.width;
      if (w < 1) return;
      const { renderer: r, camera: c } = threeRef.current;
      r.setSize(w, w);
      c.aspect = 1;
      c.updateProjectionMatrix();
    });
    ro.observe(container);

    return () => {
      ro.disconnect();
      cancelAnimationFrame(animId);
      if (syncTimerRef.current) clearTimeout(syncTimerRef.current);
      controls.removeEventListener('end', handleControlsEnd);
      controls.dispose();
      renderer.dispose();
      if (container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement);
      }
      threeRef.current = null;
    };
  }, [applyCameraState, scheduleViewportSync]);

  // Update mesh when data changes
  useEffect(() => {
    if (!threeRef.current || !meshData) return;

    const { scene, camera, controls } = threeRef.current;
    const {
      width: nx, height: ny, z_data, colors, z_min, z_max, z_scale,
      positions, indices, vertex_colors, camera_azimuth, camera_polar, camera_distance,
    } = meshData;

    // Decode arrays
    const zArr = z_data ? decode(z_data, Float32Array) : null;
    const colArr = colors ? decode(colors, Uint8Array) : null;
    const posArr = positions ? decode(positions, Float32Array) : null;
    const indexArr = indices ? decode(indices, Uint32Array) : null;
    const vertexColorArr = vertex_colors ? decode(vertex_colors, Uint8Array) : null;

    // Remove old mesh
    if (threeRef.current.mesh) {
      scene.remove(threeRef.current.mesh);
      threeRef.current.mesh.geometry.dispose();
      threeRef.current.mesh.material.dispose();
    }

    // Build geometry
    const geom = new THREE.BufferGeometry();
    const positionsArray = posArr ?? new Float32Array(nx * ny * 3);
    const colorAttr = new Float32Array((vertexColorArr ? vertexColorArr.length : (nx * ny * 3)));

    if (!posArr) {
      const zRange = z_max - z_min || 1;
      for (let iy = 0; iy < ny; iy++) {
        for (let ix = 0; ix < nx; ix++) {
          const idx = iy * nx + ix;
          const px = ix / (nx - 1) - 0.5;
          const py = iy / (ny - 1) - 0.5;
          const pz = ((zArr[idx] - z_min) / zRange - 0.5) * z_scale;

          positionsArray[idx * 3] = px;
          positionsArray[idx * 3 + 1] = pz;
          positionsArray[idx * 3 + 2] = py;
        }
      }
    }

    const sourceColors = vertexColorArr ?? colArr;
    if (sourceColors) {
      for (let i = 0; i < sourceColors.length; i += 1) {
        colorAttr[i] = sourceColors[i] / 255;
      }
    }

    geom.setAttribute('position', new THREE.BufferAttribute(positionsArray, 3));
    geom.setAttribute('color', new THREE.BufferAttribute(colorAttr, 3));

    if (indexArr) {
      geom.setIndex(Array.from(indexArr));
    } else {
      const gridIndices = [];
      for (let iy = 0; iy < ny - 1; iy++) {
        for (let ix = 0; ix < nx - 1; ix++) {
          const a = iy * nx + ix;
          const b = a + 1;
          const c = a + nx;
          const d = c + 1;
          gridIndices.push(a, c, b);
          gridIndices.push(b, c, d);
        }
      }
      geom.setIndex(gridIndices);
    }
    geom.computeVertexNormals();

    const mat = new THREE.MeshPhongMaterial({
      vertexColors: true,
      side: THREE.DoubleSide,
      shininess: 30,
      flatShading: false,
    });

    const mesh = new THREE.Mesh(geom, mat);
    scene.add(mesh);
    threeRef.current.mesh = mesh;

    // Reset camera target to center of mesh
    controls.target.set(0, 0, 0);
    if (!hasSyncedInitialSnapshotRef.current) {
      applyCameraState(
        Number.isFinite(camera_azimuth) ? camera_azimuth : Number(runtimeValues?.camera_azimuth ?? widgetValues?.camera_azimuth),
        Number.isFinite(camera_polar) ? camera_polar : Number(runtimeValues?.camera_polar ?? widgetValues?.camera_polar),
        Number.isFinite(camera_distance) ? camera_distance : Number(runtimeValues?.camera_distance ?? widgetValues?.camera_distance),
      );
      hasSyncedInitialSnapshotRef.current = true;
    }
    scheduleViewportSync(0, false);
  }, [meshData, decode, applyCameraState, runtimeValues, scheduleViewportSync, widgetValues]);

  // Prevent scroll events from propagating to React Flow
  const onWheel = useCallback((e) => {
    e.stopPropagation();
  }, []);

  return (
    <div
      ref={containerRef}
      className="nodrag nowheel surface-view-container"
      onWheelCapture={onWheel}
    />
  );
}
