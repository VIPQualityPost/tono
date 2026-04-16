import React, { useRef, useState, useCallback } from 'react';
import { clampFraction, pointerToFraction } from './overlayUtils';

export const CAPTURE_SELECTOR = '.radial-overlay';

interface RadialProfileOverlayProps {
  image: string;
  cx: number;
  cy: number;
  ex: number;
  ey: number;
  nodeId: string;
  onWidgetChange: (nodeId: string, name: string, value: unknown) => void;
}

type DragHandle = 'center' | 'a' | 'b';

interface DragState {
  handle: DragHandle;
  start: { fx: number; fy: number };
  points: { cx: number; cy: number; ex: number; ey: number };
}

const round3 = (v: number) => parseFloat(v.toFixed(3));

export default function RadialProfileOverlay({
  image, cx, cy, ex, ey,
  nodeId, onWidgetChange,
}: RadialProfileOverlayProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [dragging, setDragging] = useState<DragState | null>(null);

  const getCoords = useCallback((e: React.PointerEvent<Element>) => {
    return pointerToFraction(e, containerRef.current!);
  }, []);

  const updateWidgets = useCallback((updates: Record<string, number>) => {
    for (const [name, value] of Object.entries(updates)) {
      onWidgetChange(nodeId, name, value);
    }
  }, [nodeId, onWidgetChange]);

  const onPointerDown = useCallback((handle: DragHandle) => (e: React.PointerEvent<Element>) => {
    e.stopPropagation();
    e.preventDefault();
    (e.target as HTMLElement).setPointerCapture(e.pointerId);
    const start = getCoords(e);
    setDragging({ handle, start, points: { cx, cy, ex, ey } });
  }, [cx, cy, ex, ey, getCoords]);

  const onPointerMove = useCallback((e: React.PointerEvent<Element>) => {
    if (!dragging || !containerRef.current) return;
    const { fx, fy } = getCoords(e);
    const pts = dragging.points;

    if (dragging.handle === 'center') {
      const dx = fx - dragging.start.fx;
      const dy = fy - dragging.start.fy;
      updateWidgets({
        cx: round3(clampFraction(pts.cx + dx)),
        cy: round3(clampFraction(pts.cy + dy)),
        ex: round3(clampFraction(pts.ex + dx)),
        ey: round3(clampFraction(pts.ey + dy)),
      });
    } else if (dragging.handle === 'a') {
      updateWidgets({ ex: round3(fx), ey: round3(fy) });
    } else {
      updateWidgets({
        ex: round3(clampFraction(2 * pts.cx - fx)),
        ey: round3(clampFraction(2 * pts.cy - fy)),
      });
    }
  }, [dragging, getCoords, updateWidgets]);

  const onPointerUp = useCallback(() => {
    setDragging(null);
  }, []);

  const bx = 2 * cx - ex;
  const by = 2 * cy - ey;

  const rxFrac = Math.abs(ex - cx);
  const ryFrac = Math.abs(ey - cy);

  return (
    <div
      ref={containerRef}
      className="nodrag nowheel radial-overlay"
      onPointerMove={onPointerMove}
      onPointerUp={onPointerUp}
      onLostPointerCapture={onPointerUp}
    >
      <img src={image} alt="field" draggable={false} className="radial-image" />

      <svg className="radial-svg" viewBox="0 0 100 100" preserveAspectRatio="none">
        <ellipse
          cx={cx * 100} cy={cy * 100}
          rx={rxFrac * 100} ry={ryFrac * 100}
          className="radial-circle"
        />
        <line
          x1={ex * 100} y1={ey * 100}
          x2={bx * 100} y2={by * 100}
          className="radial-diameter"
        />
      </svg>

      <div
        className="radial-marker radial-marker-end"
        style={{ left: `${ex * 100}%`, top: `${ey * 100}%` }}
        onPointerDown={onPointerDown('a')}
      />
      <div
        className="radial-marker radial-marker-end"
        style={{ left: `${bx * 100}%`, top: `${by * 100}%` }}
        onPointerDown={onPointerDown('b')}
      />
      <div
        className="radial-marker radial-marker-center"
        style={{ left: `${cx * 100}%`, top: `${cy * 100}%` }}
        onPointerDown={onPointerDown('center')}
      />
    </div>
  );
}
