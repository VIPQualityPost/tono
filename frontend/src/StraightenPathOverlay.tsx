import React, { useRef, useState, useCallback, useEffect } from 'react';
import { clampFraction, pointerToFraction } from './overlayUtils';

export const CAPTURE_SELECTOR = '.straighten-overlay';

interface Point { x: number; y: number; }

interface StraightenPathOverlayProps {
  image: string;
  points: Point[];
  thickness: number;
  xres: number;
  yres: number;
  nodeId: string;
  onWidgetChange: (nodeId: string, name: string, value: unknown) => void;
}

const round3 = (v: number) => parseFloat(v.toFixed(3));

function pointsToStrings(points: Point[]) {
  return {
    points_x: points.map(p => round3(p.x)).join(', '),
    points_y: points.map(p => round3(p.y)).join(', '),
  };
}

// Solve a 1-D natural cubic spline (matches scipy.interpolate.CubicSpline with
// bc_type="natural") and return a function that evaluates it at any t.
function naturalCubicSpline(t: number[], y: number[]): (tq: number) => number {
  const n = t.length;
  if (n < 2) return () => y[0] ?? 0;
  if (n === 2) {
    return (tq) => y[0] + (y[1] - y[0]) * (tq - t[0]) / (t[1] - t[0]);
  }
  const h = new Array(n - 1);
  for (let i = 0; i < n - 1; i++) h[i] = t[i + 1] - t[i];

  // Tridiagonal system for second derivatives M[1..n-2] (M[0] = M[n-1] = 0).
  const a = new Array(n).fill(0);
  const b = new Array(n).fill(0);
  const c = new Array(n).fill(0);
  const d = new Array(n).fill(0);
  for (let i = 1; i < n - 1; i++) {
    a[i] = h[i - 1];
    b[i] = 2 * (h[i - 1] + h[i]);
    c[i] = h[i];
    d[i] = 6 * ((y[i + 1] - y[i]) / h[i] - (y[i] - y[i - 1]) / h[i - 1]);
  }
  for (let i = 2; i < n - 1; i++) {
    const w = a[i] / b[i - 1];
    b[i] -= w * c[i - 1];
    d[i] -= w * d[i - 1];
  }
  const M = new Array(n).fill(0);
  if (n >= 3) {
    M[n - 2] = d[n - 2] / b[n - 2];
    for (let i = n - 3; i >= 1; i--) {
      M[i] = (d[i] - c[i] * M[i + 1]) / b[i];
    }
  }

  return (tq) => {
    let i = 0;
    while (i < n - 2 && tq > t[i + 1]) i++;
    const dx = h[i];
    const A = (t[i + 1] - tq) / dx;
    const B = (tq - t[i]) / dx;
    return A * y[i] + B * y[i + 1]
      + ((A ** 3 - A) * M[i] + (B ** 3 - B) * M[i + 1]) * (dx * dx) / 6;
  };
}

const CURVE_SAMPLES_PER_SEGMENT = 24;

function buildCurvePath(points: Point[]): string {
  if (points.length === 0) return '';
  if (points.length === 1) return `M ${points[0].x * 100} ${points[0].y * 100}`;
  if (points.length === 2) {
    return `M ${points[0].x * 100} ${points[0].y * 100} L ${points[1].x * 100} ${points[1].y * 100}`;
  }
  const n = points.length;
  const t = Array.from({ length: n }, (_, i) => i / (n - 1));
  const xs = points.map(p => p.x);
  const ys = points.map(p => p.y);
  const fx = naturalCubicSpline(t, xs);
  const fy = naturalCubicSpline(t, ys);

  const total = (n - 1) * CURVE_SAMPLES_PER_SEGMENT;
  const segs: string[] = [`M ${points[0].x * 100} ${points[0].y * 100}`];
  for (let i = 1; i <= total; i++) {
    const tq = i / total;
    segs.push(`L ${fx(tq) * 100} ${fy(tq) * 100}`);
  }
  return segs.join(' ');
}

function pointsKey(points: Point[]) {
  return points.map(p => `${round3(p.x)},${round3(p.y)}`).join('|');
}

export default function StraightenPathOverlay({
  image, points, thickness, xres, yres,
  nodeId, onWidgetChange,
}: StraightenPathOverlayProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [draft, setDraft] = useState<Point[] | null>(null);
  const draggingRef = useRef<number | null>(null);
  const pendingCommitRef = useRef<string | null>(null);

  useEffect(() => {
    if (pendingCommitRef.current !== null
        && pointsKey(points) === pendingCommitRef.current) {
      pendingCommitRef.current = null;
      setDraft(null);
    }
  }, [points]);

  const commit = useCallback((next: Point[]) => {
    pendingCommitRef.current = pointsKey(next);
    const { points_x, points_y } = pointsToStrings(next);
    onWidgetChange(nodeId, 'points_x', points_x);
    onWidgetChange(nodeId, 'points_y', points_y);
  }, [nodeId, onWidgetChange]);

  const displayPoints = draft ?? points;

  const onPointerDownMarker = useCallback((idx: number) => (e: React.PointerEvent<Element>) => {
    e.stopPropagation();
    e.preventDefault();
    if (e.shiftKey && displayPoints.length > 2) {
      const next = displayPoints.filter((_, i) => i !== idx);
      setDraft(next);
      commit(next);
      return;
    }
    (e.target as HTMLElement).setPointerCapture(e.pointerId);
    draggingRef.current = idx;
    setDraft(displayPoints);
  }, [displayPoints, commit]);

  const onPointerMove = useCallback((e: React.PointerEvent<Element>) => {
    const idx = draggingRef.current;
    if (idx === null || !containerRef.current) return;
    const { fx, fy } = pointerToFraction(e, containerRef.current);
    setDraft(prev => {
      const base = prev ?? points;
      return base.map((p, i) => i === idx
        ? { x: clampFraction(fx), y: clampFraction(fy) }
        : p);
    });
  }, [points]);

  const onPointerUp = useCallback(() => {
    if (draggingRef.current !== null && draft) {
      commit(draft);
    }
    draggingRef.current = null;
  }, [draft, commit]);

  const onDoubleClick = useCallback((e: React.MouseEvent<Element>) => {
    if (!containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    const fx = clampFraction((e.clientX - rect.left) / rect.width);
    const fy = clampFraction((e.clientY - rect.top) / rect.height);
    const next = [...displayPoints, { x: fx, y: fy }];
    setDraft(next);
    commit(next);
  }, [displayPoints, commit]);

  const curveD = buildCurvePath(displayPoints);

  const refRes = Math.max(xres, yres) || 1;
  const bandWidthPct = (thickness / refRes) * 100;

  return (
    <div
      ref={containerRef}
      className="nodrag nowheel straighten-overlay"
      onPointerMove={onPointerMove}
      onPointerUp={onPointerUp}
      onLostPointerCapture={onPointerUp}
      onDoubleClick={onDoubleClick}
    >
      <img src={image} alt="field" draggable={false} className="straighten-image" />

      <svg className="straighten-svg" viewBox="0 0 100 100" preserveAspectRatio="none">
        {curveD && bandWidthPct > 0 && (
          <path
            d={curveD}
            className="straighten-band"
            fill="none"
            strokeWidth={bandWidthPct}
            strokeLinejoin="round"
            strokeLinecap="round"
          />
        )}
        {curveD && (
          <path d={curveD} className="straighten-curve" fill="none" />
        )}
      </svg>

      {displayPoints.map((p, i) => (
        <div
          key={i}
          className="straighten-marker"
          style={{ left: `${p.x * 100}%`, top: `${p.y * 100}%` }}
          onPointerDown={onPointerDownMarker(i)}
          title="shift-click to remove"
        />
      ))}
    </div>
  );
}
