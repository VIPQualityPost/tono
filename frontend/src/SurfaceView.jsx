import React, { useRef, useEffect, useCallback } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';

const DEFAULT_CAMERA_STATE = {
  azimuth: 0.0,
  polar: 1.1,
  distance: 1.8,
  targetX: 0.0,
  targetY: 0.0,
  targetZ: 0.0,
};

function getFiniteNumber(...values) {
  for (const value of values) {
    const numeric = Number(value);
    if (Number.isFinite(numeric)) {
      return numeric;
    }
  }
  return null;
}

function getCameraState(meshData, widgetValues, runtimeValues, fallbackTarget = null) {
  return {
    azimuth: getFiniteNumber(
      runtimeValues?.camera_azimuth,
      widgetValues?.camera_azimuth,
      meshData?.camera_azimuth,
      DEFAULT_CAMERA_STATE.azimuth,
    ),
    polar: getFiniteNumber(
      runtimeValues?.camera_polar,
      widgetValues?.camera_polar,
      meshData?.camera_polar,
      DEFAULT_CAMERA_STATE.polar,
    ),
    distance: getFiniteNumber(
      runtimeValues?.camera_distance,
      widgetValues?.camera_distance,
      meshData?.camera_distance,
      DEFAULT_CAMERA_STATE.distance,
    ),
    targetX: getFiniteNumber(
      runtimeValues?.camera_target_x,
      widgetValues?.camera_target_x,
      meshData?.camera_target_x,
      fallbackTarget?.x,
      DEFAULT_CAMERA_STATE.targetX,
    ),
    targetY: getFiniteNumber(
      runtimeValues?.camera_target_y,
      widgetValues?.camera_target_y,
      meshData?.camera_target_y,
      fallbackTarget?.y,
      DEFAULT_CAMERA_STATE.targetY,
    ),
    targetZ: getFiniteNumber(
      runtimeValues?.camera_target_z,
      widgetValues?.camera_target_z,
      meshData?.camera_target_z,
      fallbackTarget?.z,
      DEFAULT_CAMERA_STATE.targetZ,
    ),
  };
}

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
  const lastCameraStateRef = useRef({
    azimuth: null,
    polar: null,
    distance: null,
    targetX: null,
    targetY: null,
    targetZ: null,
  });

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
    const cameraState = {
      azimuth: Number(controls.getAzimuthalAngle().toFixed(4)),
      polar: Number(controls.getPolarAngle().toFixed(4)),
      distance: Number(controls.getDistance().toFixed(4)),
      targetX: Number(controls.target.x.toFixed(4)),
      targetY: Number(controls.target.y.toFixed(4)),
      targetZ: Number(controls.target.z.toFixed(4)),
    };
    const snapshot = renderer.domElement.toDataURL('image/png');
    const previous = lastCameraStateRef.current;
    const patch = {};
    if (previous.azimuth !== cameraState.azimuth) patch.camera_azimuth = cameraState.azimuth;
    if (previous.polar !== cameraState.polar) patch.camera_polar = cameraState.polar;
    if (previous.distance !== cameraState.distance) patch.camera_distance = cameraState.distance;
    if (previous.targetX !== cameraState.targetX) patch.camera_target_x = cameraState.targetX;
    if (previous.targetY !== cameraState.targetY) patch.camera_target_y = cameraState.targetY;
    if (previous.targetZ !== cameraState.targetZ) patch.camera_target_z = cameraState.targetZ;
    if (snapshot !== lastSnapshotRef.current) patch.viewport_snapshot = snapshot;
    if (Object.keys(patch).length > 0) {
      onRuntimeValuesChange(nodeId, patch, { scheduleRun });
      lastCameraStateRef.current = cameraState;
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

  const applyCameraState = useCallback((cameraState = {}) => {
    const state = threeRef.current;
    if (!state) return;
    const { camera, controls } = state;
    const target = new THREE.Vector3(
      getFiniteNumber(cameraState.targetX, controls.target.x, DEFAULT_CAMERA_STATE.targetX),
      getFiniteNumber(cameraState.targetY, controls.target.y, DEFAULT_CAMERA_STATE.targetY),
      getFiniteNumber(cameraState.targetZ, controls.target.z, DEFAULT_CAMERA_STATE.targetZ),
    );
    const spherical = new THREE.Spherical(
      Math.max(0.3, getFiniteNumber(cameraState.distance, DEFAULT_CAMERA_STATE.distance)),
      THREE.MathUtils.clamp(
        getFiniteNumber(cameraState.polar, DEFAULT_CAMERA_STATE.polar),
        0.01,
        Math.PI - 0.01,
      ),
      getFiniteNumber(cameraState.azimuth, DEFAULT_CAMERA_STATE.azimuth),
    );
    const offset = new THREE.Vector3().setFromSpherical(spherical);
    controls.target.copy(target);
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
    controls.enablePan = true;
    controls.enableZoom = true;
    controls.screenSpacePanning = true;
    controls.panSpeed = 1.0;
    controls.zoomSpeed = 2.2;
    controls.minDistance = 0.3;
    controls.maxDistance = 10;
    controls.mouseButtons = {
      LEFT: THREE.MOUSE.ROTATE,
      MIDDLE: THREE.MOUSE.PAN,
      RIGHT: THREE.MOUSE.DOLLY,
    };
    controls.touches = {
      ONE: THREE.TOUCH.ROTATE,
      TWO: THREE.TOUCH.DOLLY_PAN,
    };
    if ('zoomToCursor' in controls) {
      controls.zoomToCursor = true;
    }
    renderer.domElement.style.touchAction = 'none';
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
    applyCameraState(getCameraState(meshData, widgetValues, runtimeValues));

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
  }, [applyCameraState, meshData, runtimeValues, scheduleViewportSync, widgetValues]);

  // Update mesh when data changes
  useEffect(() => {
    if (!threeRef.current || !meshData) return;

    const { scene, controls } = threeRef.current;
    const {
      width: nx, height: ny, z_data, colors, z_min, z_max, z_scale,
      positions, indices, vertex_colors,
      surface_extent_x, surface_extent_y,
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
    const surfaceExtentX = getFiniteNumber(surface_extent_x, 1.0);
    const surfaceExtentY = getFiniteNumber(surface_extent_y, 1.0);

    if (!posArr) {
      const zRange = z_max - z_min || 1;
      for (let iy = 0; iy < ny; iy++) {
        for (let ix = 0; ix < nx; ix++) {
          const idx = iy * nx + ix;
          const px = (ix / Math.max(nx - 1, 1) - 0.5) * surfaceExtentX;
          const py = (iy / Math.max(ny - 1, 1) - 0.5) * surfaceExtentY;
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

    const bounds = new THREE.Box3().setFromObject(mesh);
    const center = bounds.isEmpty() ? new THREE.Vector3() : bounds.getCenter(new THREE.Vector3());
    const size = bounds.isEmpty() ? new THREE.Vector3(1, 1, 1) : bounds.getSize(new THREE.Vector3());
    const maxDimension = Math.max(size.x, size.y, size.z, 0.25);
    controls.minDistance = Math.max(0.1, maxDimension * 0.35);
    controls.maxDistance = Math.max(10, maxDimension * 14);
    applyCameraState(getCameraState(meshData, widgetValues, runtimeValues, center));
    scheduleViewportSync(0, false);
  }, [meshData, decode, applyCameraState, runtimeValues, scheduleViewportSync, widgetValues]);

  // Prevent scroll events from propagating to React Flow
  const onWheel = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const onContextMenu = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  return (
    <div
      ref={containerRef}
      className="nodrag nowheel surface-view-container"
      onWheelCapture={onWheel}
      onContextMenu={onContextMenu}
    />
  );
}
