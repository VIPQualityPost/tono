import React, { useEffect, useRef, useState, useCallback } from 'react';
import { getAxisScale } from './valueFormatting';

const ASPECT_RATIO = 3.2 / 2.2;
const MARGINS = { top: 18, right: 16, bottom: 34, left: 56 };

function clamp(v, min, max) { return Math.max(min, Math.min(max, v)); }
function round4(v) { return parseFloat(v.toFixed(4)); }
function trimZeros(t) { return t.replace(/(?:\.0+|(\.\d+?)0+)$/, '$1'); }

function formatTick(value) {
  const abs = Math.abs(value);
  if (abs === 0) return '0';
  if (abs >= 1e4 || abs < 1e-3) return value.toExponential(1).replace('e+', 'e');
  if (abs >= 100) return trimZeros(value.toFixed(0));
  if (abs >= 10) return trimZeros(value.toFixed(1));
  if (abs >= 1) return trimZeros(value.toFixed(2));
  return trimZeros(value.toFixed(3));
}

function makeTicks(min, max, count = 5) {
  if (!Number.isFinite(min) || !Number.isFinite(max) || min === max) return [min];
  return Array.from({ length: count }, (_, i) => min + (max - min) * i / (count - 1));
}

function getExtent(values, fallbackMin = 0, fallbackMax = 1) {
  if (!Array.isArray(values) || !values.length) return [fallbackMin, fallbackMax];
  let min = Infinity, max = -Infinity;
  for (const v of values) { if (Number.isFinite(v)) { if (v < min) min = v; if (v > max) max = v; } }
  return (Number.isFinite(min) && Number.isFinite(max)) ? [min, max] : [fallbackMin, fallbackMax];
}

export default function ThresholdHistogram({ overlay, threshold, thresholdConnected, nodeId, onWidgetChange }) {
  const containerRef = useRef(null);
  const [dragging, setDragging] = useState(false);
  const [size, setSize] = useState({ width: 0 });

  useEffect(() => {
    if (!containerRef.current) return undefined;
    const update = () => {
      if (!containerRef.current) return;
      setSize({ width: Math.max(1, Math.round(containerRef.current.clientWidth || 320)) });
    };
    update();
    if (typeof ResizeObserver === 'function') {
      const ro = new ResizeObserver((entries) => {
        const e = entries[0];
        if (e) setSize({ width: Math.max(1, Math.round(e.contentRect.width)) });
      });
      ro.observe(containerRef.current);
      return () => ro.disconnect();
    }
    window.addEventListener('resize', update);
    return () => window.removeEventListener('resize', update);
  }, []);

  const xValues = Array.isArray(overlay?.x_axis) && overlay.x_axis.length === overlay.line?.length
    ? overlay.x_axis : overlay?.line?.map((_, i) => i) || [];
  const yValues = Array.isArray(overlay?.line) ? overlay.line : [];
  const method = overlay?.method ?? 'absolute';
  const locked = (overlay?.locked ?? false) || !!thresholdConnected;
  const xMin = overlay?.x_min ?? 0;
  const xMax = overlay?.x_max ?? 1;

  const width = size.width || 320;
  const height = Math.round(width / ASPECT_RATIO);
  const plotLeft = MARGINS.left;
  const plotTop = MARGINS.top;
  const plotWidth = Math.max(1, width - MARGINS.left - MARGINS.right);
  const plotHeight = Math.max(1, height - MARGINS.top - MARGINS.bottom);

  const [xExtMin, xExtMax] = getExtent(xValues, 0, 1);
  const [yMinRaw, yMaxRaw] = getExtent(yValues, 0, 1);
  const yPad = yMinRaw === yMaxRaw ? 1 : (yMaxRaw - yMinRaw) * 0.08;
  const yMin = yMinRaw - yPad;
  const yMax = yMaxRaw + yPad;

  const scaleX = useCallback((v) => {
    if (xExtMax === xExtMin) return plotLeft + plotWidth / 2;
    return plotLeft + (v - xExtMin) / (xExtMax - xExtMin) * plotWidth;
  }, [plotLeft, plotWidth, xExtMin, xExtMax]);

  const scaleY = useCallback((v) => {
    if (yMax === yMin) return plotTop + plotHeight / 2;
    return plotTop + (1 - (v - yMin) / (yMax - yMin)) * plotHeight;
  }, [plotTop, plotHeight, yMin, yMax]);

  // Compute marker x-fraction from current threshold widget value
  const markerFrac = (() => {
    if (locked) return clamp(overlay?.threshold_frac ?? 0.5, 0, 1);
    const t = threshold ?? 0;
    if (method === 'relative') return clamp(t, 0, 1);
    return (xMax === xMin) ? 0.5 : clamp((t - xMin) / (xMax - xMin), 0, 1);
  })();

  const markerX = plotLeft + markerFrac * plotWidth;

  // Snap marker circle to histogram line height
  const markerY = (() => {
    if (!xValues.length || !yValues.length) return plotTop + plotHeight / 2;
    const targetX = xExtMin + markerFrac * (xExtMax - xExtMin);
    let best = 0, bestDist = Infinity;
    for (let i = 0; i < xValues.length; i++) {
      const d = Math.abs(xValues[i] - targetX);
      if (d < bestDist) { bestDist = d; best = i; }
    }
    return scaleY(yValues[best]);
  })();

  const handleDrag = useCallback((e) => {
    if (!onWidgetChange || !nodeId || locked || !containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    const frac = clamp((e.clientX - rect.left - plotLeft) / plotWidth, 0, 1);
    // Relative threshold is a 0-1 fraction — round to 4 dp is fine.
    // Absolute threshold is in SI units (could be nm/m scale) — keep full float precision.
    const newThreshold = method === 'relative'
      ? round4(frac)
      : xMin + frac * (xMax - xMin);
    onWidgetChange(nodeId, 'threshold', newThreshold);
  }, [onWidgetChange, nodeId, locked, plotLeft, plotWidth, method, xMin, xMax]);

  const onPointerDown = useCallback((e) => {
    if (locked) return;
    e.preventDefault();
    e.stopPropagation();
    e.currentTarget.setPointerCapture(e.pointerId);
    setDragging(true);
  }, [locked]);

  const onPointerMove = useCallback((e) => {
    if (dragging) handleDrag(e);
  }, [dragging, handleDrag]);

  const onPointerUp = useCallback(() => setDragging(false), []);

  const path = yValues.map((y, i) => `${i === 0 ? 'M' : 'L'} ${scaleX(xValues[i])} ${scaleY(y)}`).join(' ');
  const xTickCount = Math.max(2, Math.min(5, Math.floor(plotWidth / 70)));
  const yTickCount = Math.max(2, Math.min(5, Math.floor(plotHeight / 40)));
  const xTicks = makeTicks(xExtMin, xExtMax, xTickCount);
  const yTicks = makeTicks(yMin, yMax, yTickCount);
  const xRepresentative = Math.max(Math.abs(xExtMin), Math.abs(xExtMax));
  const { scale: xScale, unitLabel: xUnitLabel } = getAxisScale(xRepresentative, overlay?.x_unit);
  const plotStroke = clamp(plotWidth / 240, 1.4, 2.6);
  const gridStroke = clamp(plotWidth / 900, 0.6, 1.1);
  const cursorStroke = clamp(plotWidth / 220, 1.4, 2.2);
  const markerRadius = clamp(plotWidth / 42, 5.5, 9);
  const markerLabelSize = clamp(plotWidth / 34, 8, 11);

  return (
    <div
      ref={containerRef}
      className="nodrag nowheel lineplot-overlay"
      onPointerMove={onPointerMove}
      onPointerUp={onPointerUp}
      onLostPointerCapture={onPointerUp}
    >
      {locked && (
        <div style={{ fontSize: 10, color: 'var(--danger-locked)', padding: '0 4px 3px', textAlign: 'right', letterSpacing: '0.04em' }}>
          {thresholdConnected ? 'Locked — driven by socket' : 'Locked — Otsu auto-threshold'}
        </div>
      )}
      <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} className="lineplot-svg">
        <rect x="0" y="0" width={width} height={height} fill="var(--bg-deep)" />

        {xTicks.map((tick) => {
          const x = scaleX(tick);
          return (
            <g key={`x-${tick}`}>
              <line x1={x} y1={plotTop} x2={x} y2={plotTop + plotHeight} stroke="var(--border-default)" strokeWidth={gridStroke} opacity="0.45" />
              <text x={x} y={height - 10} textAnchor="middle" fontSize="11" fill="var(--text-secondary)">{formatTick(tick / xScale)}</text>
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
              <text x={plotLeft - 10} y={y + 4} textAnchor="end" fontSize="11" fill="var(--text-secondary)">{formatTick(tick)}</text>
            </g>
          );
        })}

        <rect x={plotLeft} y={plotTop} width={plotWidth} height={plotHeight} fill="none" stroke="var(--border-default)" strokeWidth={gridStroke + 0.3} />
        <path d={path} fill="none" stroke="var(--plot-line)" strokeWidth={plotStroke} strokeLinecap="round" strokeLinejoin="round" />

        {/* Threshold marker line */}
        <line
          x1={markerX} y1={plotTop} x2={markerX} y2={plotTop + plotHeight}
          stroke="var(--marker)" strokeWidth={cursorStroke} strokeDasharray="10 6" opacity="0.95"
        />

        {/* Threshold marker circle */}
        <g onPointerDown={onPointerDown} style={{ cursor: locked ? 'default' : 'ew-resize' }}>
          <circle
            cx={markerX}
            cy={markerY}
            r={markerRadius}
            className={`lineplot-marker ${locked ? 'lineplot-marker-locked' : ''}`}
          />
          <text
            x={markerX}
            y={markerY}
            textAnchor="middle"
            dominantBaseline="middle"
            fontSize={markerLabelSize}
            className="lineplot-marker-label"
            pointerEvents="none"
          >
            T
          </text>
        </g>
      </svg>
    </div>
  );
}
