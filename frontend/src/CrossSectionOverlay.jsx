import React, { useRef, useState, useCallback } from 'react';

/**
 * Image preview with two endpoint markers for cross-section line control.
 * Markers are draggable when unlocked (no COORD input connected),
 * and fixed when locked (COORD input provides the position).
 *
 * Marker positions are driven by widget values (immediate React state),
 * not by backend overlay coords, so they move instantly during drag.
 */
export default function CrossSectionOverlay({
  image, x1, y1, x2, y2,
  aLocked, bLocked,
  nodeId, onWidgetChange,
  showLine = true,
}) {
  const containerRef = useRef(null);
  const [dragging, setDragging] = useState(null); // 'p1' or 'p2'

  const getCoords = useCallback((e) => {
    const rect = containerRef.current.getBoundingClientRect();
    return {
      fx: Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width)),
      fy: Math.max(0, Math.min(1, (e.clientY - rect.top) / rect.height)),
    };
  }, []);

  const onPointerDown = useCallback((point) => (e) => {
    if (point === 'p1' && aLocked) return;
    if (point === 'p2' && bLocked) return;
    e.stopPropagation();
    e.preventDefault();
    e.target.setPointerCapture(e.pointerId);
    setDragging(point);
  }, [aLocked, bLocked]);

  const onPointerMove = useCallback((e) => {
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
            stroke="#ffd700" strokeWidth="2" strokeDasharray="6 3"
          />
        </svg>
      )}

      {/* Endpoint markers — locked markers get a different style */}
      <div
        className={`cs-marker ${aLocked ? 'cs-marker-locked' : ''}`}
        style={{ left: `${x1 * 100}%`, top: `${y1 * 100}%` }}
        onPointerDown={onPointerDown('p1')}
      />
      <div
        className={`cs-marker ${bLocked ? 'cs-marker-locked' : ''}`}
        style={{ left: `${x2 * 100}%`, top: `${y2 * 100}%` }}
        onPointerDown={onPointerDown('p2')}
      />
    </div>
  );
}
