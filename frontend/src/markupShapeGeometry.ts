import { clampFraction, sanitizeHexColor } from './overlayUtils.ts';

export const MARKUP_DEFAULT_SHAPE = 'arrow';
export const MARKUP_DEFAULT_COLOR = '#ff0000';
export const MARKUP_PREVIEW_REFERENCE_DIM = 512;

export interface MarkupShape {
  kind: string;
  x1: number;
  y1: number;
  x2: number;
  y2: number;
  width: number;
  color: string;
}

export function sanitizeMarkupColor(color: unknown, fallback: string = MARKUP_DEFAULT_COLOR): string {
  return sanitizeHexColor(color, fallback);
}

export function sanitizeMarkupShape(
  shape: Partial<MarkupShape> | null | undefined,
  fallbackShape: string = MARKUP_DEFAULT_SHAPE,
  fallbackColor: string = MARKUP_DEFAULT_COLOR,
  fallbackWidth: number = 3,
): MarkupShape | null {
  if (!shape || typeof shape !== 'object') return null;
  const kind = (shape.kind && ['line', 'rectangle', 'circle', 'arrow'].includes(shape.kind)) ? shape.kind : fallbackShape;
  const x1 = clampFraction(shape.x1);
  const y1 = clampFraction(shape.y1);
  const x2 = clampFraction(shape.x2);
  const y2 = clampFraction(shape.y2);
  const width = Math.max(1, Math.min(64, Math.round(Number(shape.width) || fallbackWidth || 1)));
  return {
    kind,
    x1: Number(x1.toFixed(4)),
    y1: Number(y1.toFixed(4)),
    x2: Number(x2.toFixed(4)),
    y2: Number(y2.toFixed(4)),
    width,
    color: sanitizeMarkupColor(shape.color, fallbackColor),
  };
}

export function parseMarkupShapes(
  markupShapes: unknown,
  fallbackShape: string = MARKUP_DEFAULT_SHAPE,
  fallbackColor: string = MARKUP_DEFAULT_COLOR,
  fallbackWidth: number = 3,
): MarkupShape[] {
  if (Array.isArray(markupShapes)) {
    return markupShapes
      .map((shape) => sanitizeMarkupShape(shape, fallbackShape, fallbackColor, fallbackWidth))
      .filter((s): s is MarkupShape => s != null);
  }

  if (typeof markupShapes !== 'string' || !markupShapes.trim()) return [];

  try {
    const parsed = JSON.parse(markupShapes);
    if (!Array.isArray(parsed)) return [];
    return parsed
      .map((shape) => sanitizeMarkupShape(shape, fallbackShape, fallbackColor, fallbackWidth))
      .filter((s): s is MarkupShape => s != null);
  } catch {
    return [];
  }
}

export function getArrowGeometry(shape: MarkupShape, imageWidth: number, imageHeight: number) {
  const x1 = shape.x1 * imageWidth;
  const y1 = shape.y1 * imageHeight;
  const x2 = shape.x2 * imageWidth;
  const y2 = shape.y2 * imageHeight;
  const dx = x2 - x1;
  const dy = y2 - y1;
  const length = Math.hypot(dx, dy) || 1;
  const ux = dx / length;
  const uy = dy / length;
  const strokeWidth = Math.max(1, shape.width);
  const headLength = Math.max(10, strokeWidth * 4);
  const headWidth = Math.max(8, strokeWidth * 3);
  const shaftX = x2 - ux * headLength;
  const shaftY = y2 - uy * headLength;
  const px = -uy;
  const py = ux;
  const leftX = shaftX + px * headWidth * 0.5;
  const leftY = shaftY + py * headWidth * 0.5;
  const rightX = shaftX - px * headWidth * 0.5;
  const rightY = shaftY - py * headWidth * 0.5;
  return {
    line: `${x1},${y1} ${shaftX},${shaftY}`,
    head: `${x2},${y2} ${leftX},${leftY} ${rightX},${rightY}`,
  };
}

export function getMarkupPreviewStrokeWidth(width: number, imageWidth: number, imageHeight: number) {
  const normalizedWidth = Math.max(1, Math.round(Number(width) || 1));
  const longestDim = Math.max(1, Number(imageWidth) || 0, Number(imageHeight) || 0);
  const scale = Math.max(1, longestDim / MARKUP_PREVIEW_REFERENCE_DIM);
  return Math.max(1, Math.round(normalizedWidth * scale));
}
