import React from 'react';

// ── Clamping ─────────────────────────────────────────────────────────

export function clamp(value: number, min: number, max: number) {
  return Math.max(min, Math.min(max, value));
}

export function clampFraction(value: number | unknown): number {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return 0;
  return Math.max(0, Math.min(1, numeric));
}

// ── Color validation ─────────────────────────────────────────────────

const HEX_COLOR_RE = /^#[0-9a-fA-F]{6}$/;

export function sanitizeHexColor(color: unknown, fallback: string = '#ff9800'): string {
  if (typeof color !== 'string') return fallback;
  const value = color.trim();
  return HEX_COLOR_RE.test(value) ? value.toLowerCase() : fallback;
}

// ── Pointer coordinate extraction ────────────────────────────────────

export function pointerToFraction(
  event: React.PointerEvent<Element>,
  container: HTMLElement,
): { fx: number; fy: number } {
  const rect = container.getBoundingClientRect();
  return {
    fx: clampFraction((event.clientX - rect.left) / rect.width),
    fy: clampFraction((event.clientY - rect.top) / rect.height),
  };
}

// ── Chart helpers ────────────────────────────────────────────────────

export function trimZeros(text: string) {
  return text.replace(/(?:\.0+|(\.\d+?)0+)$/, '$1');
}

export function formatTick(value: number) {
  const abs = Math.abs(value);
  if (abs === 0) return '0';
  if (abs >= 1e4 || abs < 1e-3) return value.toExponential(1).replace('e+', 'e');
  if (abs >= 100) return trimZeros(value.toFixed(0));
  if (abs >= 10) return trimZeros(value.toFixed(1));
  if (abs >= 1) return trimZeros(value.toFixed(2));
  return trimZeros(value.toFixed(3));
}

export function makeTicks(min: number, max: number, count = 5) {
  if (!Number.isFinite(min) || !Number.isFinite(max) || min === max) return [min];
  return Array.from({ length: count }, (_: unknown, i: number) => min + (max - min) * i / (count - 1));
}

export function getExtent(values: number[], fallbackMin = 0, fallbackMax = 1) {
  if (!Array.isArray(values) || !values.length) return [fallbackMin, fallbackMax];
  let min = Infinity, max = -Infinity;
  for (const v of values) {
    if (Number.isFinite(v)) {
      if (v < min) min = v;
      if (v > max) max = v;
    }
  }
  return (Number.isFinite(min) && Number.isFinite(max)) ? [min, max] : [fallbackMin, fallbackMax];
}
