import React, { useRef, useState, useCallback, useEffect } from 'react';
import { pointerToFraction } from './overlayUtils';

export const CAPTURE_SELECTOR = '.perspective-overlay';

const CORNER_NAMES = ['top_left', 'top_right', 'bottom_left', 'bottom_right'] as const;
type CornerName = typeof CORNER_NAMES[number];

const CORNER_ANCHORS: Record<CornerName, { ax: number; ay: number }> = {
  top_left:     { ax: 0, ay: 0 },
  top_right:    { ax: 1, ay: 0 },
  bottom_left:  { ax: 0, ay: 1 },
  bottom_right: { ax: 1, ay: 1 },
};

interface Corner { x: number; y: number }

interface Props {
  image: string;
  correctedImage: string;
  corners: Corner[];
  nodeId: string;
  onWidgetChange: (nodeId: string, name: string, value: unknown) => void;
}

function cornerToPercent(corner: Corner, name: CornerName) {
  const anchor = CORNER_ANCHORS[name];
  return {
    left: (anchor.ax + corner.x) * 100,
    top:  (anchor.ay + corner.y) * 100,
  };
}

function cornersKey(c: Corner[]): string {
  return c.map((p) => `${p.x},${p.y}`).join(';');
}

export default function PerspectiveOverlay({
  image, correctedImage, corners, nodeId, onWidgetChange,
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const draggingRef = useRef<CornerName | null>(null);
  const [draft, setDraft] = useState<Corner[] | null>(null);
  const pendingCommitRef = useRef<string | null>(null);
  const [showCorrected, setShowCorrected] = useState(false);

  useEffect(() => {
    if (pendingCommitRef.current && cornersKey(corners) === pendingCommitRef.current) {
      pendingCommitRef.current = null;
      setDraft(null);
    }
  }, [corners]);

  const liveCorners = draft ?? corners;

  const onPointerDown = useCallback((corner: CornerName) => (e: React.PointerEvent<Element>) => {
    e.stopPropagation();
    e.preventDefault();
    (e.target as HTMLElement).setPointerCapture(e.pointerId);
    draggingRef.current = corner;
    setDraft([...liveCorners]);
  }, [liveCorners]);

  const onPointerMove = useCallback((e: React.PointerEvent<Element>) => {
    const name = draggingRef.current;
    if (!name || !containerRef.current) return;
    const { fx, fy } = pointerToFraction(e, containerRef.current);
    const anchor = CORNER_ANCHORS[name];
    const cx = Math.max(-1, Math.min(1, parseFloat((fx - anchor.ax).toFixed(3))));
    const cy = Math.max(-1, Math.min(1, parseFloat((fy - anchor.ay).toFixed(3))));
    const idx = CORNER_NAMES.indexOf(name);
    setDraft((prev) => {
      if (!prev) return prev;
      const next = [...prev];
      // Keep a minimum separation from the adjacent corners so the quad
      // cannot degenerate — the backend solves the homography with lstsq and
      // silently emits garbage when two corners coincide.
      const MIN_SEP = 0.02;
      const clampBetween = (v: number, lo: number, hi: number) => (
        hi >= lo ? Math.min(Math.max(v, lo), hi) : (lo + hi) / 2
      );
      const nextX = clampBetween(cx,
        Math.max(next[(idx + 1) % 4].x, next[(idx + 3) % 4].x) + MIN_SEP,
        Math.min(next[(idx + 1) % 4].x, next[(idx + 3) % 4].x) - MIN_SEP);
      const nextY = clampBetween(cy,
        Math.max(next[(idx + 1) % 4].y, next[(idx + 3) % 4].y) + MIN_SEP,
        Math.min(next[(idx + 1) % 4].y, next[(idx + 3) % 4].y) - MIN_SEP);
      next[idx] = { x: nextX, y: nextY };
      return next;
    });
  }, []);

  const onPointerUp = useCallback(() => {
    const name = draggingRef.current;
    if (!name || !draft) {
      draggingRef.current = null;
      return;
    }
    draggingRef.current = null;
    pendingCommitRef.current = cornersKey(draft);
    for (let i = 0; i < CORNER_NAMES.length; i++) {
      onWidgetChange(nodeId, `${CORNER_NAMES[i]}_x`, draft[i].x);
      onWidgetChange(nodeId, `${CORNER_NAMES[i]}_y`, draft[i].y);
    }
  }, [draft, nodeId, onWidgetChange]);

  const positions = CORNER_NAMES.map((name, i) => cornerToPercent(liveCorners[i] || { x: 0, y: 0 }, name));
  const quadPoints = `${positions[0].left},${positions[0].top} ${positions[1].left},${positions[1].top} ${positions[3].left},${positions[3].top} ${positions[2].left},${positions[2].top}`;

  return (
    <div className="perspective-overlay-wrap">
      <div className="perspective-tab-bar">
        <button
          className={`perspective-tab nodrag${!showCorrected ? ' active' : ''}`}
          onClick={() => setShowCorrected(false)}
        >
          Source
        </button>
        <button
          className={`perspective-tab nodrag${showCorrected ? ' active' : ''}`}
          onClick={() => setShowCorrected(true)}
        >
          Corrected
        </button>
      </div>

      {showCorrected ? (
        <div className="perspective-overlay perspective-corrected">
          <img src={correctedImage} alt="corrected" draggable={false} />
        </div>
      ) : (
        <div
          ref={containerRef}
          className="nodrag nowheel perspective-overlay"
          onPointerMove={onPointerMove}
          onPointerUp={onPointerUp}
          onLostPointerCapture={onPointerUp}
        >
          <img src={image} alt="source" draggable={false} />

          <svg className="perspective-quad" viewBox="0 0 100 100" preserveAspectRatio="none">
            <polygon
              points={quadPoints}
              fill="none"
              stroke="var(--selection, #3b82f6)"
              strokeWidth="0.4"
              strokeLinejoin="round"
            />
          </svg>

          {CORNER_NAMES.map((name, i) => (
            <div
              key={name}
              className={`perspective-handle${draggingRef.current === name ? ' dragging' : ''}`}
              style={{ left: `${positions[i].left}%`, top: `${positions[i].top}%` }}
              onPointerDown={onPointerDown(name)}
            />
          ))}
        </div>
      )}
    </div>
  );
}
