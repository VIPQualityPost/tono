import React, { useRef, useState, useCallback } from 'react';
import { pointerToFraction } from './overlayUtils';

export const CAPTURE_SELECTOR = '.crop-overlay';

interface CropBoxOverlayProps {
  image: string;
  x1: number;
  y1: number;
  x2: number;
  y2: number;
  aLocked: boolean;
  bLocked: boolean;
  nodeId: string;
  onWidgetChange: (nodeId: string, name: string, value: unknown) => void;
  square?: boolean;
  xreal?: number;
  yreal?: number;
}

function snapPhysicalSquare(
  anchorX: number, anchorY: number,
  moverX: number, moverY: number,
  xreal: number, yreal: number,
) {
  const dx = moverX - anchorX;
  const dy = moverY - anchorY;
  const ax = xreal > 0 ? xreal : 1;
  const ay = yreal > 0 ? yreal : 1;
  const shortPhys = Math.min(Math.abs(dx) * ax, Math.abs(dy) * ay);
  const sx = dx >= 0 ? 1 : -1;
  const sy = dy >= 0 ? 1 : -1;
  return {
    x: anchorX + sx * (shortPhys / ax),
    y: anchorY + sy * (shortPhys / ay),
  };
}

export default function CropBoxOverlay({
  image, x1, y1, x2, y2,
  aLocked, bLocked,
  nodeId, onWidgetChange,
  square = false,
  xreal = 1,
  yreal = 1,
}: CropBoxOverlayProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [dragging, setDragging] = useState<string | null>(null);
  const panStartRef = useRef<{ fx: number; fy: number; x1: number; y1: number; x2: number; y2: number } | null>(null);

  const getCoords = useCallback((e: React.PointerEvent<Element>) => {
    return pointerToFraction(e, containerRef.current!);
  }, []);

  const onPointerDown = useCallback((point: string) => (e: React.PointerEvent<Element>) => {
    if (point === 'p1' && aLocked) return;
    if (point === 'p2' && bLocked) return;
    if (point === 'rect' && (aLocked || bLocked)) return;
    e.stopPropagation();
    e.preventDefault();
    (e.target as HTMLElement).setPointerCapture(e.pointerId);
    if (point === 'rect') {
      const { fx, fy } = getCoords(e);
      panStartRef.current = { fx, fy, x1, y1, x2, y2 };
    }
    setDragging(point);
  }, [aLocked, bLocked, getCoords, x1, y1, x2, y2]);

  const onPointerMove = useCallback((e: React.PointerEvent<Element>) => {
    if (!dragging || !containerRef.current) return;
    const { fx, fy } = getCoords(e);

    if (dragging === 'rect') {
      const start = panStartRef.current;
      if (!start) return;
      const left = Math.min(start.x1, start.x2);
      const right = Math.max(start.x1, start.x2);
      const top = Math.min(start.y1, start.y2);
      const bottom = Math.max(start.y1, start.y2);
      let dx = fx - start.fx;
      let dy = fy - start.fy;
      dx = Math.max(-left, Math.min(1 - right, dx));
      dy = Math.max(-top, Math.min(1 - bottom, dy));
      const nx1 = parseFloat((start.x1 + dx).toFixed(3));
      const ny1 = parseFloat((start.y1 + dy).toFixed(3));
      const nx2 = parseFloat((start.x2 + dx).toFixed(3));
      const ny2 = parseFloat((start.y2 + dy).toFixed(3));
      onWidgetChange(nodeId, 'x1', nx1);
      onWidgetChange(nodeId, 'y1', ny1);
      onWidgetChange(nodeId, 'x2', nx2);
      onWidgetChange(nodeId, 'y2', ny2);
      return;
    }

    let vx = fx;
    let vy = fy;
    if (square) {
      const anchorX = dragging === 'p2' ? x1 : x2;
      const anchorY = dragging === 'p2' ? y1 : y2;
      const snapped = snapPhysicalSquare(anchorX, anchorY, fx, fy, xreal, yreal);
      vx = snapped.x;
      vy = snapped.y;
    }
    const vxR = parseFloat(vx.toFixed(3));
    const vyR = parseFloat(vy.toFixed(3));
    if (dragging === 'p1') {
      onWidgetChange(nodeId, 'x1', vxR);
      onWidgetChange(nodeId, 'y1', vyR);
    } else {
      onWidgetChange(nodeId, 'x2', vxR);
      onWidgetChange(nodeId, 'y2', vyR);
    }
  }, [dragging, getCoords, nodeId, onWidgetChange, square, xreal, yreal, x1, y1, x2, y2]);

  const onPointerUp = useCallback(() => {
    setDragging(null);
    panStartRef.current = null;
  }, []);

  const left = Math.min(x1, x2);
  const right = Math.max(x1, x2);
  const top = Math.min(y1, y2);
  const bottom = Math.max(y1, y2);

  return (
    <div
      ref={containerRef}
      className="nodrag nowheel crop-overlay"
      onPointerMove={onPointerMove}
      onPointerUp={onPointerUp}
      onLostPointerCapture={onPointerUp}
    >
      <img src={image} alt="crop source" draggable={false} className="crop-image" />

      <div className="crop-dim" style={{ left: 0, top: 0, width: '100%', height: `${top * 100}%` }} />
      <div className="crop-dim" style={{ left: 0, top: `${top * 100}%`, width: `${left * 100}%`, height: `${(bottom - top) * 100}%` }} />
      <div className="crop-dim" style={{ left: `${right * 100}%`, top: `${top * 100}%`, width: `${(1 - right) * 100}%`, height: `${(bottom - top) * 100}%` }} />
      <div className="crop-dim" style={{ left: 0, top: `${bottom * 100}%`, width: '100%', height: `${(1 - bottom) * 100}%` }} />

      <div
        className={`crop-rect ${aLocked || bLocked ? 'crop-rect-locked' : ''}`}
        style={{
          left: `${left * 100}%`,
          top: `${top * 100}%`,
          width: `${(right - left) * 100}%`,
          height: `${(bottom - top) * 100}%`,
        }}
        onPointerDown={onPointerDown('rect')}
      />

      <div
        className={`crop-marker ${aLocked ? 'crop-marker-locked' : ''}`}
        style={{ left: `${x1 * 100}%`, top: `${y1 * 100}%` }}
        onPointerDown={onPointerDown('p1')}
      />
      <div
        className={`crop-marker ${bLocked ? 'crop-marker-locked' : ''}`}
        style={{ left: `${x2 * 100}%`, top: `${y2 * 100}%` }}
        onPointerDown={onPointerDown('p2')}
      />
    </div>
  );
}
