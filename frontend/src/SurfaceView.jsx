import React, { useRef, useEffect, useCallback } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';

/**
 * Interactive 3D surface viewer using Three.js.
 * Props:
 *   meshData: { width, height, z_data (b64 float32), colors (b64 uint8 RGB),
 *               z_min, z_max, z_scale, x_range, y_range }
 */
export default function SurfaceView({ meshData }) {
  const containerRef = useRef(null);
  const threeRef = useRef(null); // { renderer, scene, camera, controls, mesh }

  // Decode base64 to typed arrays
  const decode = useCallback((b64, ArrayType) => {
    const bin = atob(b64);
    const bytes = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
    return new ArrayType(bytes.buffer);
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
      controls.dispose();
      renderer.dispose();
      if (container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement);
      }
      threeRef.current = null;
    };
  }, []);

  // Update mesh when data changes
  useEffect(() => {
    if (!threeRef.current || !meshData) return;

    const { scene, camera, controls } = threeRef.current;
    const { width: nx, height: ny, z_data, colors, z_min, z_max, z_scale, x_range, y_range } = meshData;

    // Decode arrays
    const zArr = decode(z_data, Float32Array);
    const colArr = decode(colors, Uint8Array);

    // Remove old mesh
    if (threeRef.current.mesh) {
      scene.remove(threeRef.current.mesh);
      threeRef.current.mesh.geometry.dispose();
      threeRef.current.mesh.material.dispose();
    }

    // Build geometry
    const geom = new THREE.BufferGeometry();
    const positions = new Float32Array(nx * ny * 3);
    const colorAttr = new Float32Array(nx * ny * 3);

    // Normalize coordinates to roughly [-0.5, 0.5] for good camera framing
    const zRange = z_max - z_min || 1;

    for (let iy = 0; iy < ny; iy++) {
      for (let ix = 0; ix < nx; ix++) {
        const idx = iy * nx + ix;
        const px = ix / (nx - 1) - 0.5;  // [-0.5, 0.5]
        const py = iy / (ny - 1) - 0.5;
        const pz = ((zArr[idx] - z_min) / zRange - 0.5) * z_scale;

        positions[idx * 3] = px;
        positions[idx * 3 + 1] = pz; // height on Y axis
        positions[idx * 3 + 2] = py;

        colorAttr[idx * 3] = colArr[idx * 3] / 255;
        colorAttr[idx * 3 + 1] = colArr[idx * 3 + 1] / 255;
        colorAttr[idx * 3 + 2] = colArr[idx * 3 + 2] / 255;
      }
    }

    geom.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    geom.setAttribute('color', new THREE.BufferAttribute(colorAttr, 3));

    // Build index (triangles from grid)
    const indices = [];
    for (let iy = 0; iy < ny - 1; iy++) {
      for (let ix = 0; ix < nx - 1; ix++) {
        const a = iy * nx + ix;
        const b = a + 1;
        const c = a + nx;
        const d = c + 1;
        indices.push(a, c, b);
        indices.push(b, c, d);
      }
    }
    geom.setIndex(indices);
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
    controls.update();
  }, [meshData, decode]);

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
