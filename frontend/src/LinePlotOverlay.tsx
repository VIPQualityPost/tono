import React, { useEffect, useRef, useState, useCallback } from 'react';
import { getAxisScale } from './valueFormatting';
import { clamp, formatTick, makeTicks, getExtent } from './overlayUtils';

export const CAPTURE_SELECTOR = '.lineplot-overlay';

const ASPECT_RATIO = 3.2 / 2.2;
const MARGINS = { top: 18, right: 16, bottom: 34, left: 56 };

// Hardcoded marker colors so SVG elements render correctly in canvas exports,
// where CSS custom properties (var(--marker) etc.) are not resolved.
const MARKER_FILL = '#ffd700';
const MARKER_STROKE = '#ffffff';
const MARKER_LOCKED_COLOR = '#e91e63';
const MARKER_LABEL_FILL = '#0f172a';

function round3(v: number) {
  return parseFloat(v.toFixed(3));
}

interface LinePlotOverlayProps {
  overlay: any;
  x1: number;
  x2: number;
  aLocked: boolean;
  bLocked: boolean;
  nodeId: string;
  onWidgetChange: (nodeId: string, name: string, value: unknown) => void;
  interactive?: boolean;
}

export default function LinePlotOverlay({
  overlay,
  x1,
  x2,
  aLocked,
  bLocked,
  nodeId,
  onWidgetChange,
  interactive = true,
}: LinePlotOverlayProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [dragging, setDragging] = useState<string | null>(null);
  const [size, setSize] = useState({ width: 0, height: 0 });

  useEffect(() => {
    if (!containerRef.current) return undefined;
    const updateSize = () => {
      if (!containerRef.current) return;
      setSize({
        width: Math.max(1, Math.round(containerRef.current.clientWidth || 320)),
        height: Math.max(1, Math.round(containerRef.current.clientHeight || (containerRef.current.clientWidth / ASPECT_RATIO) || 220)),
      });
    };

    updateSize();

    if (typeof ResizeObserver === 'function') {
      const observer = new ResizeObserver((entries) => {
        const entry = entries[0];
        if (!entry) return;
        const { width, height } = entry.contentRect;
        setSize({
          width: Math.max(1, Math.round(width)),
          height: Math.max(1, Math.round(height)),
        });
      });
      observer.observe(containerRef.current);
      return () => observer.disconnect();
    }

    window.addEventListener('resize', updateSize);
    return () => window.removeEventListener('resize', updateSize);
  }, []);

  const xValues: number[] = Array.isArray(overlay?.x_axis) && overlay.x_axis.length === overlay.line?.length
    ? overlay.x_axis
    : overlay?.line?.map((_: unknown, i: number) => i) || [];
  const yValues: number[] = Array.isArray(overlay?.line) ? overlay.line : [];

  const width = size.width || 320;
  const height = size.height || Math.round(width / ASPECT_RATIO);
  const plotLeft = MARGINS.left;
  const plotTop = MARGINS.top;
  const plotWidth = Math.max(1, width - MARGINS.left - MARGINS.right);
  const plotHeight = Math.max(1, height - MARGINS.top - MARGINS.bottom);

  const [xMin, xMax] = getExtent(xValues, 0, 1);
  const [yMinRaw, yMaxRaw] = getExtent(yValues, 0, 1);
  const yPad = yMinRaw === yMaxRaw ? 1 : (yMaxRaw - yMinRaw) * 0.08;
  const yMin = yMinRaw - yPad;
  const yMax = yMaxRaw + yPad;

  const scaleX = useCallback((value: number) => {
    if (xMax === xMin) return plotLeft + plotWidth / 2;
    return plotLeft + ((value - xMin) / (xMax - xMin)) * plotWidth;
  }, [plotLeft, plotWidth, xMin, xMax]);

  const scaleY = useCallback((value: number) => {
    if (yMax === yMin) return plotTop + plotHeight / 2;
    return plotTop + (1 - ((value - yMin) / (yMax - yMin))) * plotHeight;
  }, [plotTop, plotHeight, yMin, yMax]);

  const pickCursorPoint = useCallback((fraction: number) => {
    if (!xValues.length || !yValues.length) {
      return {
        x: plotLeft,
        y: plotTop + plotHeight / 2,
        yFraction: 0.5,
      };
    }

    const frac = clamp(fraction ?? 0.5, 0, 1);
    const targetX = xMin + frac * (xMax - xMin || 1);

    let idx = 0;
    let best = Infinity;
    for (let i = 0; i < xValues.length; i += 1) {
      const dist = Math.abs(xValues[i] - targetX);
      if (dist < best) {
        best = dist;
        idx = i;
      }
    }

    const x = xValues[idx];
    const y = yValues[idx];
    const yFraction = yMax === yMin ? 0.5 : clamp((y - yMin) / (yMax - yMin), 0, 1);
    return {
      x: scaleX(x),
      y: scaleY(y),
      yFraction,
    };
  }, [plotLeft, plotTop, plotHeight, scaleX, scaleY, xValues, yValues, xMin, xMax, yMin, yMax]);

  const cursorA = pickCursorPoint(x1 ?? overlay?.x1 ?? 0.25);
  const cursorB = pickCursorPoint(x2 ?? overlay?.x2 ?? 0.75);

  const path = yValues.map((y: number, i: number) => `${i === 0 ? 'M' : 'L'} ${scaleX(xValues[i])} ${scaleY(y)}`).join(' ');
  const xTickCount = Math.max(2, Math.min(5, Math.floor(plotWidth / 70)));
  const yTickCount = Math.max(2, Math.min(5, Math.floor(plotHeight / 40)));
  const xTicks = makeTicks(xMin, xMax, xTickCount);
  const yTicks = makeTicks(yMin, yMax, yTickCount);
  const xRepresentative = Math.max(Math.abs(xMin), Math.abs(xMax));
  const { scale: xScale, unitLabel: xUnitLabel } = getAxisScale(xRepresentative, overlay?.x_unit);
  const plotStroke = clamp(plotWidth / 240, 1.4, 2.6);
  const gridStroke = clamp(plotWidth / 900, 0.6, 1.1);
  const cursorStroke = clamp(plotWidth / 220, 1.4, 2.2);
  const measureStroke = clamp(plotWidth / 180, 1.6, 2.8);
  const markerRadius = clamp(plotWidth / 42, 5.5, 9);
  const markerLabelSize = clamp(plotWidth / 34, 8, 11);

  const updateCursor = useCallback((point: string, event: React.PointerEvent<Element>) => {
    if (!interactive || !onWidgetChange || !nodeId) return;
    if (!containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    const xFrac = clamp((event.clientX - rect.left - plotLeft) / plotWidth, 0, 1);
    const sample = pickCursorPoint(xFrac);
    if (point === 'p1') {
      onWidgetChange(nodeId, 'x1', round3(xFrac));
      onWidgetChange(nodeId, 'y1', round3(sample.yFraction));
    } else {
      onWidgetChange(nodeId, 'x2', round3(xFrac));
      onWidgetChange(nodeId, 'y2', round3(sample.yFraction));
    }
  }, [interactive, nodeId, onWidgetChange, pickCursorPoint, plotLeft, plotWidth]);

  const onPointerDown = useCallback((point: string) => (event: React.PointerEvent<Element>) => {
    if (!interactive) return;
    if ((point === 'p1' && aLocked) || (point === 'p2' && bLocked)) return;
    event.preventDefault();
    event.stopPropagation();
    event.currentTarget.setPointerCapture(event.pointerId);
    setDragging(point);
  }, [interactive, aLocked, bLocked]);

  const onPointerMove = useCallback((event: React.PointerEvent<Element>) => {
    if (!dragging) return;
    updateCursor(dragging, event);
  }, [dragging, updateCursor]);

  const onPointerUp = useCallback(() => {
    setDragging(null);
  }, []);

  return (
    <div
      ref={containerRef}
      className="nodrag nowheel lineplot-overlay"
      onPointerMove={onPointerMove}
      onPointerUp={onPointerUp}
      onLostPointerCapture={onPointerUp}
    >
      <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} className="lineplot-svg">
        <rect x="0" y="0" width={width} height={height} fill="var(--bg-deep)" />

        {xTicks.map((tick) => {
          const x = scaleX(tick);
          return (
            <g key={`x-${tick}`}>
              <line x1={x} y1={plotTop} x2={x} y2={plotTop + plotHeight} stroke="var(--border-default)" strokeWidth={gridStroke} opacity="0.45" />
              <text x={x} y={height - 10} textAnchor="middle" fontSize="11" fill="var(--text-secondary)">
                {formatTick(tick / xScale)}
              </text>
            </g>
          );
        })}
        {xUnitLabel && (
          <text x={plotLeft + plotWidth} y={height - 1} textAnchor="end" fontSize="10" fill="var(--text-muted)">{xUnitLabel}</text>
        )}

        {yTicks.map((tick) => {
          const y = scaleY(tick);
          return (
            <g key={`y-${tick}`}>
              <line x1={plotLeft} y1={y} x2={plotLeft + plotWidth} y2={y} stroke="var(--border-default)" strokeWidth={gridStroke} opacity="0.45" />
              <text x={plotLeft - 10} y={y + 4} textAnchor="end" fontSize="11" fill="var(--text-secondary)">
                {formatTick(tick)}
              </text>
            </g>
          );
        })}

        <rect x={plotLeft} y={plotTop} width={plotWidth} height={plotHeight} fill="none" stroke="var(--border-default)" strokeWidth={gridStroke + 0.3} />
        <path d={path} fill="none" stroke="var(--plot-line)" strokeWidth={plotStroke} strokeLinecap="round" strokeLinejoin="round" />

        {interactive && (
          <>
            <line x1={cursorA.x} y1={plotTop} x2={cursorA.x} y2={plotTop + plotHeight} stroke="var(--marker)" strokeWidth={cursorStroke} strokeDasharray="10 6" opacity="0.95" />
            <line x1={cursorB.x} y1={plotTop} x2={cursorB.x} y2={plotTop + plotHeight} stroke="var(--marker)" strokeWidth={cursorStroke} strokeDasharray="10 6" opacity="0.95" />

            <g onPointerDown={onPointerDown('p1')}>
              <circle
                cx={cursorA.x}
                cy={cursorA.y}
                r={markerRadius}
                className={`lineplot-marker ${aLocked ? 'lineplot-marker-locked' : ''}`}
                fill={aLocked ? MARKER_LOCKED_COLOR : MARKER_FILL}
                stroke={aLocked ? MARKER_LOCKED_COLOR : MARKER_STROKE}
              />
              <text
                x={cursorA.x}
                y={cursorA.y}
                textAnchor="middle"
                dominantBaseline="middle"
                fontSize={markerLabelSize}
                className="lineplot-marker-label"
                fill={MARKER_LABEL_FILL}
                pointerEvents="none"
              >
                A
              </text>
            </g>
            <g onPointerDown={onPointerDown('p2')}>
              <circle
                cx={cursorB.x}
                cy={cursorB.y}
                r={markerRadius}
                className={`lineplot-marker ${bLocked ? 'lineplot-marker-locked' : ''}`}
                fill={bLocked ? MARKER_LOCKED_COLOR : MARKER_FILL}
                stroke={bLocked ? MARKER_LOCKED_COLOR : MARKER_STROKE}
              />
              <text
                x={cursorB.x}
                y={cursorB.y}
                textAnchor="middle"
                dominantBaseline="middle"
                fontSize={markerLabelSize}
                className="lineplot-marker-label"
                fill={MARKER_LABEL_FILL}
                pointerEvents="none"
              >
                B
              </text>
            </g>
          </>
        )}
      </svg>
    </div>
  );
}
