import React, { useRef, useState, useCallback } from 'react';

export default function CropBoxOverlay({
  image, x1, y1, x2, y2,
  aLocked, bLocked,
  nodeId, onWidgetChange,
}) {
  const containerRef = useRef(null);
  const [dragging, setDragging] = useState(null);

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
  }, [dragging, getCoords, nodeId, onWidgetChange]);

  const onPointerUp = useCallback(() => {
    setDragging(null);
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
        className="crop-rect"
        style={{
          left: `${left * 100}%`,
          top: `${top * 100}%`,
          width: `${(right - left) * 100}%`,
          height: `${(bottom - top) * 100}%`,
        }}
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
