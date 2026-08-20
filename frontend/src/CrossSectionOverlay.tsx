import React, { useRef, useState, useCallback } from 'react';
import { pointerToFraction } from './overlayUtils';

export const CAPTURE_SELECTOR = '.cs-overlay';

/**
 * Image preview with two endpoint markers for cross-section line control.
 * Markers are draggable when unlocked (no COORD input connected),
 * and fixed when locked (COORD input provides the position).
 *
 * Marker positions are driven by widget values (immediate React state),
 * not by backend overlay coords, so they move instantly during drag.
 */

interface CrossSectionOverlayProps {
  image: string;
  x1: number;
  y1: number;
  x2: number;
  y2: number;
  aLocked: boolean;
  bLocked: boolean;
  nodeId: string;
  onWidgetChange: (nodeId: string, name: string, value: unknown) => void;
  showLine?: boolean;
}

export default function CrossSectionOverlay({
  image, x1, y1, x2, y2,
  aLocked, bLocked,
  nodeId, onWidgetChange,
  showLine = true,
}: CrossSectionOverlayProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [dragging, setDragging] = useState<string | null>(null); // 'p1' or 'p2'

  const getCoords = useCallback((e: React.PointerEvent<Element>) => {
    return pointerToFraction(e, containerRef.current!);
  }, []);

  const onPointerDown = useCallback((point: string) => (e: React.PointerEvent<Element>) => {
    const locked = (point === 'p1' && aLocked) || (point === 'p2' && bLocked);
    if (locked) {
      // Inert, not transparent: grabbing a locked marker must not pan the
      // canvas underneath.
      e.stopPropagation();
      e.preventDefault();
      return;
    }
    e.stopPropagation();
    e.preventDefault();
    (e.target as HTMLElement).setPointerCapture(e.pointerId);
    setDragging(point);
  }, [aLocked, bLocked]);

  const onPointerMove = useCallback((e: React.PointerEvent<Element>) => {
    if (!dragging || !containerRef.current) return;
    const { fx, fy } = getCoords(e);
    const vx = parseFloat(fx.toFixed(3));
    const vy = parseFloat(fy.toFixed(3));
    if (dragging === 'p1') {
      onWidgetChange(nodeId, 'x1', vx);
      onWidgetChange(nodeId, 'y1', vy);
    } else {
      onWidgetChange(nodeId, 'x2', vx);
      onWidgetChange(nodeId, 'y2', vy);
    }
  }, [dragging, nodeId, onWidgetChange, getCoords]);

  const onPointerUp = useCallback(() => {
    setDragging(null);
  }, []);

  return (
    <div
      ref={containerRef}
      className="nodrag nowheel cs-overlay"
      onPointerMove={onPointerMove}
      onPointerUp={onPointerUp}
      onLostPointerCapture={onPointerUp}
    >
      <img src={image} alt="field" draggable={false} className="cs-image" />

      {/* Line connecting the two markers */}
      {showLine && (
        <svg className="cs-svg">
          <line
            x1={`${x1 * 100}%`} y1={`${y1 * 100}%`}
            x2={`${x2 * 100}%`} y2={`${y2 * 100}%`}
            stroke="var(--marker)" strokeWidth="2" strokeDasharray="6 3"
          />
        </svg>
      )}

      {/* Endpoint markers — locked markers get a different style */}
      <div
        className={`cs-marker ${aLocked ? 'cs-marker-locked' : ''}`}
        style={{ left: `${x1 * 100}%`, top: `${y1 * 100}%` }}
        onPointerDown={onPointerDown('p1')}
      >A</div>
      <div
        className={`cs-marker ${bLocked ? 'cs-marker-locked' : ''}`}
        style={{ left: `${x2 * 100}%`, top: `${y2 * 100}%` }}
        onPointerDown={onPointerDown('p2')}
      >B</div>
    </div>
  );
}
