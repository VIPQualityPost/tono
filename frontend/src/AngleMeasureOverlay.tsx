import React, { useRef, useState, useCallback } from 'react';

export const CAPTURE_SELECTOR = '.angle-overlay';

import {
  getAngleLabelBasePosition,
  getAngleLabelPosition,
  measureAngleDegrees,
  moveAngleWidget,
  round3,
} from './angleMeasureGeometry';
import { clampFraction as clamp01, sanitizeHexColor, pointerToFraction } from './overlayUtils';

function hexToRgb(value: string) {
  const color = sanitizeHexColor(value);
  return {
    r: parseInt(color.slice(1, 3), 16),
    g: parseInt(color.slice(3, 5), 16),
    b: parseInt(color.slice(5, 7), 16),
  };
}

function mixColor(baseColor: string, mixWith: string, weight: number) {
  const alpha = Math.max(0, Math.min(1, Number(weight) || 0));
  const base = hexToRgb(baseColor);
  const target = hexToRgb(mixWith);
  const r = Math.round((base.r * (1 - alpha)) + (target.r * alpha));
  const g = Math.round((base.g * (1 - alpha)) + (target.g * alpha));
  const b = Math.round((base.b * (1 - alpha)) + (target.b * alpha));
  return `rgb(${r}, ${g}, ${b})`;
}

function formatAngle(value: number) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return '0.0 deg';
  return `${numeric.toFixed(1)} deg`;
}

function buildAngleArcPath(x1: number, y1: number, xm: number, ym: number, x2: number, y2: number) {
  const va = { x: x1 - xm, y: y1 - ym };
  const vb = { x: x2 - xm, y: y2 - ym };
  const lenA = Math.hypot(va.x, va.y);
  const lenB = Math.hypot(vb.x, vb.y);
  if (lenA <= 1e-6 || lenB <= 1e-6) return '';

  const radius = Math.min(0.12, 0.38 * Math.min(lenA, lenB));
  const start = { x: xm + (va.x / lenA) * radius, y: ym + (va.y / lenA) * radius };
  const end = { x: xm + (vb.x / lenB) * radius, y: ym + (vb.y / lenB) * radius };
  const cross = (va.x * vb.y) - (va.y * vb.x);

  return [
    `M ${start.x * 100} ${start.y * 100}`,
    `A ${radius * 100} ${radius * 100} 0 0 ${cross >= 0 ? 1 : 0} ${end.x * 100} ${end.y * 100}`,
  ].join(' ');
}

interface AngleMeasureOverlayProps {
  image: string;
  x1: number;
  y1: number;
  xm: number;
  ym: number;
  x2: number;
  y2: number;
  labelDx: number;
  labelDy: number;
  angleDeg: number;
  color: string;
  strokeWidth: number;
  nodeId: string;
  onWidgetChange: (nodeId: string, name: string, value: unknown) => void;
}

interface AngleDragState {
  handle: string;
  start?: { fx: number; fy: number };
  points?: { x1: number; y1: number; xm: number; ym: number; x2: number; y2: number };
}

export default function AngleMeasureOverlay({
  image,
  x1,
  y1,
  xm,
  ym,
  x2,
  y2,
  labelDx,
  labelDy,
  angleDeg,
  color,
  strokeWidth,
  nodeId,
  onWidgetChange,
}: AngleMeasureOverlayProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [dragging, setDragging] = useState<AngleDragState | null>(null);
  const resolvedColor = sanitizeHexColor(color, '#ff9800');
  const resolvedStrokeWidth = Math.max(0.35, Math.min(6, Number(strokeWidth) || 1.35));
  const resolvedArcColor = mixColor(resolvedColor, '#ffffff', 0.42);
  const resolvedMidColor = mixColor(resolvedColor, '#ffffff', 0.72);
  const resolvedBadgeTextColor = mixColor(resolvedColor, '#ffffff', 0.72);
  const resolvedBadgeBorderColor = mixColor(resolvedColor, '#ffffff', 0.32);

  const getCoords = useCallback((event: React.PointerEvent<Element>) => {
    return pointerToFraction(event, containerRef.current!);
  }, []);

  const updateWidgets = useCallback((updates: Record<string, unknown>) => {
    Object.entries(updates).forEach(([name, value]) => {
      onWidgetChange(nodeId, name, value);
    });
  }, [nodeId, onWidgetChange]);

  const onPointerDown = useCallback((handle: string) => (event: React.PointerEvent<Element>) => {
    event.stopPropagation();
    event.preventDefault();
    event.currentTarget.setPointerCapture(event.pointerId);

    if (handle === 'mid') {
      const start = getCoords(event);
      setDragging({
        handle,
        start,
        points: { x1, y1, xm, ym, x2, y2 },
      });
      return;
    }

    setDragging({ handle });
  }, [getCoords, x1, y1, xm, ym, x2, y2]);

  const onPointerMove = useCallback((event: React.PointerEvent<Element>) => {
    if (!dragging || !containerRef.current) return;
    const { fx, fy } = getCoords(event);

    if (dragging.handle === 'mid') {
      updateWidgets(moveAngleWidget(
        dragging.points!,
        fx - dragging.start!.fx,
        fy - dragging.start!.fy,
      ));
      return;
    }

    if (dragging.handle === 'p1') {
      updateWidgets({ x1: round3(fx), y1: round3(fy) });
    } else if (dragging.handle === 'p2') {
      updateWidgets({ x2: round3(fx), y2: round3(fy) });
    } else if (dragging.handle === 'label') {
      const base = getAngleLabelBasePosition(x1, y1, xm, ym, x2, y2);
      updateWidgets({
        label_dx: round3(fx - base.x),
        label_dy: round3(fy - base.y),
      });
    }
  }, [dragging, getCoords, updateWidgets, x1, y1, xm, ym, x2, y2]);

  const onPointerUp = useCallback(() => {
    setDragging(null);
  }, []);

  const displayedAngle = Number.isFinite(Number(angleDeg))
    ? Number(angleDeg)
    : measureAngleDegrees(x1, y1, xm, ym, x2, y2);
  const arcPath = buildAngleArcPath(x1, y1, xm, ym, x2, y2);
  const labelPosition = getAngleLabelPosition({ x1, y1, xm, ym, x2, y2 }, labelDx, labelDy);

  return (
    <div
      ref={containerRef}
      className="nodrag nowheel angle-overlay"
      style={{
        '--angle-line-color': resolvedColor,
        '--angle-arc-color': resolvedArcColor,
        '--angle-end-handle-color': resolvedColor,
        '--angle-mid-handle-color': resolvedMidColor,
        '--angle-badge-text-color': resolvedBadgeTextColor,
        '--angle-badge-border-color': resolvedBadgeBorderColor,
        '--angle-stroke-width': `${resolvedStrokeWidth}`,
      } as React.CSSProperties}
      onPointerMove={onPointerMove}
      onPointerUp={onPointerUp}
      onLostPointerCapture={onPointerUp}
    >
      <img src={image} alt="angle source" draggable={false} className="angle-image" />
      <svg className="angle-svg" viewBox="0 0 100 100" preserveAspectRatio="none">
        <line className="angle-line" x1={x1 * 100} y1={y1 * 100} x2={xm * 100} y2={ym * 100} />
        <line className="angle-line" x1={xm * 100} y1={ym * 100} x2={x2 * 100} y2={y2 * 100} />
        {arcPath && <path className="angle-arc" d={arcPath} />}
      </svg>

      <div
        className="angle-badge"
        style={{ left: `${labelPosition.x * 100}%`, top: `${labelPosition.y * 100}%` }}
        onPointerDown={onPointerDown('label')}
      >
        {formatAngle(displayedAngle)}
      </div>

      <div
        className="angle-handle angle-handle-end"
        style={{ left: `${x1 * 100}%`, top: `${y1 * 100}%` }}
        onPointerDown={onPointerDown('p1')}
      >
        A
      </div>
      <div
        className="angle-handle angle-handle-mid"
        style={{ left: `${xm * 100}%`, top: `${ym * 100}%` }}
        onPointerDown={onPointerDown('mid')}
      >
        V
      </div>
      <div
        className="angle-handle angle-handle-end"
        style={{ left: `${x2 * 100}%`, top: `${y2 * 100}%` }}
        onPointerDown={onPointerDown('p2')}
      >
        B
      </div>
    </div>
  );
}
