import React, { useRef, useEffect, useCallback, useState } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';

const VIEW3D_DIAGNOSTICS_STORAGE_KEY = 'tono:view3d-diagnostics';
const DEFAULT_CAMERA_STATE = {
  // A diagonal home view avoids edge-on framing when one lateral axis is much smaller.
  azimuth: Math.PI / 4,
  polar: 1.1,
  distance: 1.8,
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

function formatNumber(value, digits = 2) {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric.toFixed(digits) : 'n/a';
}

function formatVector3(value, digits = 2) {
  if (!value) return 'n/a';
  return `${formatNumber(value.x, digits)}, ${formatNumber(value.y, digits)}, ${formatNumber(value.z, digits)}`;
}

function areView3dDiagnosticsEnabled() {
  if (typeof window === 'undefined') return false;
  try {
    return window.localStorage?.getItem(VIEW3D_DIAGNOSTICS_STORAGE_KEY) === '1';
  } catch {
    return false;
  }
}

function buildGeometrySignature(meshData) {
  if (!meshData) return '';
  const positionSource = String(meshData.positions || meshData.z_data || '');
  const indexSource = String(meshData.indices || '');
  return [
    meshData.width,
    meshData.height,
    meshData.z_scale,
    meshData.make_solid ? 1 : 0,
    meshData.surface_extent_x,
    meshData.surface_extent_y,
    positionSource.length,
    positionSource.slice(0, 24),
    positionSource.slice(-24),
    indexSource.length,
    indexSource.slice(0, 24),
    indexSource.slice(-24),
  ].join('|');
}

/**
 * Interactive 3D surface viewer using Three.js.
 * Props:
 *   meshData: { width, height, z_data (b64 float32), colors (b64 uint8 RGB),
 *               z_min, z_max, z_scale, x_range, y_range }
 */
export default function SurfaceView({ meshData, nodeId, widgetValues, runtimeValues, onRuntimeValuesChange }) {
  const [showDiagnostics] = useState(() => areView3dDiagnosticsEnabled());
  const containerRef = useRef(null);
  const threeRef = useRef(null); // { renderer, scene, camera, controls, mesh }
  const meshCenterRef = useRef(new THREE.Vector3());
  const fitDistanceRef = useRef(DEFAULT_CAMERA_STATE.distance);
  const lastGeometrySignatureRef = useRef('');
  const syncTimerRef = useRef(null);
  const lastSnapshotRef = useRef('');
  const isInsideRef = useRef(false);
  const pointerEnteredAtRef = useRef(0);
  const lastWheelAtRef = useRef(0);
  const gestureStartedInsideRef = useRef(false);
  const [diagnostics, setDiagnostics] = useState({
    status: meshData ? 'initializing' : 'waiting for mesh',
    webgl: 'pending',
    canvas: 'n/a',
    mesh: meshData ? 'pending' : 'none',
    bounds: 'n/a',
    camera: 'n/a',
    target: 'n/a',
    render: 'n/a',
    error: '',
  });

  const updateDiagnostics = useCallback((patch) => {
    if (!showDiagnostics) return;
    setDiagnostics((prev) => ({ ...prev, ...patch }));
  }, [showDiagnostics]);

  // Decode base64 to typed arrays
  const decode = useCallback((b64, ArrayType) => {
    const bin = atob(b64);
    const bytes = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
    return new ArrayType(bytes.buffer);
  }, []);

  const captureViewportSnapshot = useCallback(() => {
    const canvas = threeRef.current?.renderer?.domElement;
    if (!canvas) return null;
    try {
      return canvas.toDataURL('image/png');
    } catch (error) {
      console.warn('[tono] Failed to capture View3D viewport snapshot', error);
      updateDiagnostics({
        status: 'snapshot error',
        error: error?.message || String(error),
      });
      return null;
    }
  }, [updateDiagnostics]);

  const syncViewportState = useCallback((scheduleRun = false) => {
    const state = threeRef.current;
    if (!state) return;
    const { controls, camera, renderer } = state;
    const snapshot = captureViewportSnapshot();
    updateDiagnostics({
      camera: `dist ${formatNumber(controls.getDistance())} az ${formatNumber(controls.getAzimuthalAngle())} pol ${formatNumber(controls.getPolarAngle())}`,
      target: formatVector3(controls.target),
      canvas: `${renderer.domElement.width}x${renderer.domElement.height} px`,
      render: `calls ${renderer.info.render.calls} tris ${renderer.info.render.triangles} geo ${renderer.info.memory.geometries}`,
    });
    if (!nodeId || !onRuntimeValuesChange) return;
    const patch = {};
    if (snapshot && snapshot !== lastSnapshotRef.current) patch.viewport_snapshot = snapshot;
    if (Object.keys(patch).length > 0) {
      onRuntimeValuesChange(nodeId, patch, { scheduleRun });
      if (snapshot) {
        lastSnapshotRef.current = snapshot;
      }
    }
  }, [captureViewportSnapshot, nodeId, onRuntimeValuesChange, updateDiagnostics]);

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
    const target = meshCenterRef.current.clone();
    const distance = THREE.MathUtils.clamp(
      getFiniteNumber(cameraState.distance, fitDistanceRef.current, DEFAULT_CAMERA_STATE.distance),
      controls.minDistance,
      controls.maxDistance,
    );
    const spherical = new THREE.Spherical(
      distance,
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
    camera.lookAt(target);
    controls.update();
  }, []);

  const resetCamera = useCallback(() => {
    applyCameraState({
      azimuth: DEFAULT_CAMERA_STATE.azimuth,
      polar: DEFAULT_CAMERA_STATE.polar,
    });
    scheduleViewportSync(0, true);
  }, [applyCameraState, scheduleViewportSync]);

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
    updateDiagnostics({
      status: meshData ? 'renderer ready' : 'waiting for mesh',
      webgl: `${renderer.capabilities.isWebGL2 ? 'webgl2' : 'webgl1'} / ${renderer.capabilities.precision}`,
      canvas: `${renderer.domElement.width}x${renderer.domElement.height} px`,
      render: `calls ${renderer.info.render.calls} tris ${renderer.info.render.triangles} geo ${renderer.info.memory.geometries}`,
      error: '',
    });

    const handleContextLost = (event) => {
      event.preventDefault();
      updateDiagnostics({
        status: 'webgl context lost',
        error: 'WebGL context lost',
      });
    };
    const handleContextRestored = () => {
      updateDiagnostics({
        status: 'webgl context restored',
        error: '',
      });
    };
    renderer.domElement.addEventListener('webglcontextlost', handleContextLost, false);
    renderer.domElement.addEventListener('webglcontextrestored', handleContextRestored, false);

    const scene = new THREE.Scene();

    const camera = new THREE.PerspectiveCamera(45, 1, 0.01, 1000);
    camera.position.set(1.2, 0.8, 1.2);

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.1;
    controls.enablePan = false;
    controls.enableZoom = true;
    controls.zoomSpeed = 2.2;
    controls.minDistance = 0.3;
    controls.maxDistance = 10;
    controls.mouseButtons = {
      LEFT: THREE.MOUSE.ROTATE,
      MIDDLE: THREE.MOUSE.DOLLY,
      RIGHT: THREE.MOUSE.DOLLY,
    };
    controls.touches = {
      ONE: THREE.TOUCH.ROTATE,
      TWO: THREE.TOUCH.DOLLY_ROTATE,
    };
    renderer.domElement.style.touchAction = 'none';
    const handleControlsEnd = () => scheduleViewportSync(120, true);
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
    applyCameraState({
      azimuth: DEFAULT_CAMERA_STATE.azimuth,
      polar: DEFAULT_CAMERA_STATE.polar,
    });

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
      updateDiagnostics({
        canvas: `${r.domElement.width}x${r.domElement.height} px`,
      });
    });
    ro.observe(container);

    return () => {
      ro.disconnect();
      cancelAnimationFrame(animId);
      if (syncTimerRef.current) clearTimeout(syncTimerRef.current);
      controls.removeEventListener('end', handleControlsEnd);
      renderer.domElement.removeEventListener('webglcontextlost', handleContextLost, false);
      renderer.domElement.removeEventListener('webglcontextrestored', handleContextRestored, false);
      controls.dispose();
      renderer.dispose();
      if (container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement);
      }
      threeRef.current = null;
    };
  }, [scheduleViewportSync, updateDiagnostics]);

  useEffect(() => {
    if (meshData) {
      updateDiagnostics({
        status: 'mesh payload received',
        mesh: `${meshData.width}x${meshData.height} payload`,
        error: '',
      });
      return;
    }
    updateDiagnostics({
      status: threeRef.current ? 'waiting for mesh' : 'initializing',
      mesh: 'none',
      bounds: 'n/a',
    });
  }, [meshData, updateDiagnostics]);

  // Update mesh when data changes
  useEffect(() => {
    if (!threeRef.current || !meshData) return;
    try {
      const { scene, controls, renderer } = threeRef.current;
      const geometrySignature = buildGeometrySignature(meshData);
      const geometryChanged = geometrySignature !== lastGeometrySignatureRef.current;
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
      const sphere = bounds.isEmpty()
        ? new THREE.Sphere(center.clone(), 0.5)
        : bounds.getBoundingSphere(new THREE.Sphere());
      const radius = Math.max(Number(sphere.radius) || 0, 0.125);
      const fovRadians = THREE.MathUtils.degToRad(threeRef.current.camera.fov || 45);
      const fitDistance = Math.max(
        DEFAULT_CAMERA_STATE.distance,
        (radius / Math.sin(Math.max(fovRadians / 2, 0.01))) * 1.15,
      );
      meshCenterRef.current.copy(center);
      controls.minDistance = Math.max(0.1, maxDimension * 0.35);
      controls.maxDistance = Math.max(10, fitDistance * 8);
      fitDistanceRef.current = Math.min(
        controls.maxDistance,
        Math.max(controls.minDistance, fitDistance),
      );
      const { camera } = threeRef.current;
      camera.near = Math.max(0.01, fitDistanceRef.current / 100);
      camera.far = Math.max(1000, fitDistanceRef.current * 20);
      camera.updateProjectionMatrix();
      updateDiagnostics({
        status: 'mesh built',
        mesh: `${nx}x${ny} / verts ${positionsArray.length / 3} / idx ${geom.index?.count || 0}`,
        bounds: `center ${formatVector3(center)} size ${formatVector3(size)}`,
        camera: `fit ${formatNumber(fitDistanceRef.current)} near ${formatNumber(camera.near, 3)} far ${formatNumber(camera.far, 1)}`,
        render: `calls ${renderer.info.render.calls} tris ${renderer.info.render.triangles} geo ${renderer.info.memory.geometries}`,
        error: '',
      });
      if (geometryChanged) {
        applyCameraState({
          azimuth: DEFAULT_CAMERA_STATE.azimuth,
          polar: DEFAULT_CAMERA_STATE.polar,
        });
        lastGeometrySignatureRef.current = geometrySignature;
      }
      scheduleViewportSync(0, false);
    } catch (error) {
      console.error('[tono] View3D mesh build failed', error);
      updateDiagnostics({
        status: 'mesh build error',
        error: error?.message || String(error),
      });
    }
  }, [applyCameraState, decode, meshData, scheduleViewportSync, updateDiagnostics]);

  // Gesture-aware wheel handling: only capture scroll when it started inside the view.
  // Uses capture phase to disable OrbitControls zoom before it fires when gesture started outside.
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const onEnter = () => {
      isInsideRef.current = true;
      pointerEnteredAtRef.current = Date.now();
    };
    const onLeave = () => {
      isInsideRef.current = false;
    };

    // Capture phase: fires before OrbitControls on renderer.domElement
    const onWheelCapture = () => {
      const now = Date.now();
      const msSinceLastWheel = now - lastWheelAtRef.current;
      const msSinceEnter = now - pointerEnteredAtRef.current;
      lastWheelAtRef.current = now;

      if (msSinceLastWheel > 300) {
        gestureStartedInsideRef.current = isInsideRef.current && msSinceEnter > 100;
      }

      // Gesture started outside — disable OrbitControls zoom so it doesn't intercept
      if (!gestureStartedInsideRef.current && threeRef.current) {
        threeRef.current.controls.enableZoom = false;
      }
    };

    // Bubble phase: fires after OrbitControls has already run (or skipped due to enableZoom=false)
    const onWheelBubble = (e) => {
      if (threeRef.current) {
        threeRef.current.controls.enableZoom = true;
      }
      if (gestureStartedInsideRef.current) {
        e.stopPropagation(); // prevent React Flow from panning when interacting with the 3D view
      }
      // else: let event propagate to React Flow so canvas panning continues
    };

    container.addEventListener('wheel', onWheelCapture, { capture: true, passive: true });
    container.addEventListener('wheel', onWheelBubble, { passive: false });
    container.addEventListener('pointerenter', onEnter);
    container.addEventListener('pointerleave', onLeave);

    return () => {
      container.removeEventListener('wheel', onWheelCapture, { capture: true });
      container.removeEventListener('wheel', onWheelBubble);
      container.removeEventListener('pointerenter', onEnter);
      container.removeEventListener('pointerleave', onLeave);
    };
  }, []);

  const onContextMenu = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  return (
    <div className="surface-view-shell">
      <div
        ref={containerRef}
        className="nodrag surface-view-container"
        onContextMenu={onContextMenu}
      />
      {showDiagnostics ? (
        <div className="surface-view-diagnostics">
          <div>{`status: ${diagnostics.status}`}</div>
          <div>{`webgl: ${diagnostics.webgl}`}</div>
          <div>{`canvas: ${diagnostics.canvas}`}</div>
          <div>{`mesh: ${diagnostics.mesh}`}</div>
          <div>{`bounds: ${diagnostics.bounds}`}</div>
          <div>{`camera: ${diagnostics.camera}`}</div>
          <div>{`target: ${diagnostics.target}`}</div>
          <div>{`render: ${diagnostics.render}`}</div>
          {diagnostics.error ? <div>{`error: ${diagnostics.error}`}</div> : null}
        </div>
      ) : null}
      <button
        type="button"
        className="surface-view-home nodrag"
        title="Reset 3D view"
        onPointerDown={(e) => e.stopPropagation()}
        onClick={(e) => {
          e.stopPropagation();
          resetCamera();
        }}
      >
        Home
      </button>
    </div>
  );
}
