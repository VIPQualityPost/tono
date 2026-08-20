import React, { useEffect, useRef, useState, useCallback } from 'react';
import { CANVAS_COLORS } from './constants';
import { clampFraction, pointerToFraction } from './overlayUtils';

interface StrokePoint {
  x: number;
  y: number;
}

interface Stroke {
  size: number;
  points: StrokePoint[];
}

interface DrawStrokeStyles {
  strokeStyle?: string;
  fillStyle?: string;
}

function sanitizeStroke(stroke: any, fallbackPenSize: number): Stroke | null {
  if (!stroke || typeof stroke !== 'object' || !Array.isArray(stroke.points) || stroke.points.length === 0) {
    return null;
  }

  const size = Math.max(1, Math.round(Number(stroke.size) || fallbackPenSize || 1));
  const points = stroke.points
    .map((point: any) => {
      if (!point || typeof point !== 'object') return null;
      return {
        x: Number(clampFraction(point.x).toFixed(4)),
        y: Number(clampFraction(point.y).toFixed(4)),
      };
    })
    .filter(Boolean) as StrokePoint[];

  if (points.length === 0) return null;
  return { size, points };
}

function parseMaskPaths(maskPaths: any, fallbackPenSize: number): Stroke[] {
  if (Array.isArray(maskPaths)) {
    return maskPaths.map((stroke: any) => sanitizeStroke(stroke, fallbackPenSize)).filter(Boolean) as Stroke[];
  }
  if (typeof maskPaths !== 'string' || !maskPaths.trim()) return [];

  try {
    const parsed = JSON.parse(maskPaths);
    if (!Array.isArray(parsed)) return [];
    return parsed.map((stroke: any) => sanitizeStroke(stroke, fallbackPenSize)).filter(Boolean) as Stroke[];
  } catch {
    return [];
  }
}

function drawStroke(ctx: CanvasRenderingContext2D, stroke: Stroke, width: number, height: number, imageWidth: number, imageHeight: number, styles: DrawStrokeStyles = {}) {
  if (!stroke || !Array.isArray(stroke.points) || stroke.points.length === 0) return;

  const scaleX = imageWidth > 0 ? width / imageWidth : 1;
  const scaleY = imageHeight > 0 ? height / imageHeight : 1;
  const brushScale = Math.max(0.5, Math.min(scaleX, scaleY));
  const lineWidth = Math.max(1, stroke.size * brushScale);

  ctx.save();
  ctx.lineCap = 'round';
  ctx.lineJoin = 'round';
  ctx.strokeStyle = styles.strokeStyle || CANVAS_COLORS.maskStroke;
  ctx.fillStyle = styles.fillStyle || CANVAS_COLORS.maskStroke;
  ctx.lineWidth = lineWidth;

  const points = stroke.points.map((point) => ({
    x: clampFraction(point.x) * width,
    y: clampFraction(point.y) * height,
  }));

  if (points.length === 1) {
    const radius = lineWidth / 2;
    ctx.beginPath();
    ctx.arc(points[0].x, points[0].y, radius, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();
    return;
  }

  ctx.beginPath();
  ctx.moveTo(points[0].x, points[0].y);
  for (let i = 1; i < points.length; i += 1) {
    ctx.lineTo(points[i].x, points[i].y);
  }
  ctx.stroke();

  for (const point of points) {
    ctx.beginPath();
    ctx.arc(point.x, point.y, lineWidth / 2, 0, Math.PI * 2);
    ctx.fill();
  }

  ctx.restore();
}

interface MaskPaintOverlayProps {
  image: string;
  imageWidth: number;
  imageHeight: number;
  penSize: number;
  maskPaths: any;
  nodeId: string;
  onWidgetChange: (nodeId: string, name: string, value: unknown) => void;
}

export default function MaskPaintOverlay({
  image,
  imageWidth,
  imageHeight,
  penSize,
  maskPaths,
  nodeId,
  onWidgetChange,
}: MaskPaintOverlayProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const strokesRef = useRef<Stroke[]>([]);
  const draftStrokeRef = useRef<Stroke | null>(null);
  const [strokes, setStrokes] = useState<Stroke[]>(() => parseMaskPaths(maskPaths, penSize));
  const [draftStroke, setDraftStroke] = useState<Stroke | null>(null);
  const [drawing, setDrawing] = useState(false);
  const [cursorPoint, setCursorPoint] = useState<StrokePoint | null>(null);

  useEffect(() => {
    const parsed = parseMaskPaths(maskPaths, penSize);
    strokesRef.current = parsed;
    setStrokes(parsed);
    setDraftStroke(null);
    setDrawing(false);
  }, [maskPaths, penSize]);

  useEffect(() => {
    strokesRef.current = strokes;
  }, [strokes]);

  useEffect(() => {
    draftStrokeRef.current = draftStroke;
  }, [draftStroke]);

  const redrawCanvas = useCallback((committedStrokes: Stroke[], activeStroke: Stroke | null) => {
    const canvas = canvasRef.current;
    const container = containerRef.current;
    if (!canvas || !container) return;

    const rect = container.getBoundingClientRect();
    const cssWidth = Math.max(1, Math.round(rect.width));
    const cssHeight = Math.max(1, Math.round(rect.height));
    const dpr = Math.max(1, window.devicePixelRatio || 1);

    if (canvas.width !== Math.round(cssWidth * dpr) || canvas.height !== Math.round(cssHeight * dpr)) {
      canvas.width = Math.round(cssWidth * dpr);
      canvas.height = Math.round(cssHeight * dpr);
      canvas.style.width = `${cssWidth}px`;
      canvas.style.height = `${cssHeight}px`;
    }

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    const maskCanvas = document.createElement('canvas');
    maskCanvas.width = canvas.width;
    maskCanvas.height = canvas.height;
    const maskCtx = maskCanvas.getContext('2d');
    if (!maskCtx) return;

    maskCtx.setTransform(1, 0, 0, 1, 0, 0);
    maskCtx.clearRect(0, 0, maskCanvas.width, maskCanvas.height);
    maskCtx.scale(dpr, dpr);

    const drawMaskStroke = (stroke: Stroke) => drawStroke(
      maskCtx,
      stroke,
      cssWidth,
      cssHeight,
      imageWidth,
      imageHeight,
      { strokeStyle: CANVAS_COLORS.maskStroke, fillStyle: CANVAS_COLORS.maskStroke },
    );

    for (const stroke of committedStrokes) {
      drawMaskStroke(stroke);
    }
    if (activeStroke) {
      drawMaskStroke(activeStroke);
    }

    ctx.drawImage(maskCanvas, 0, 0);
    ctx.globalCompositeOperation = 'source-in';
    ctx.fillStyle = CANVAS_COLORS.maskOverlay;
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.globalCompositeOperation = 'source-over';
  }, [imageHeight, imageWidth]);

  useEffect(() => {
    redrawCanvas(strokes, draftStroke);
  }, [draftStroke, redrawCanvas, strokes]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container || typeof ResizeObserver === 'undefined') return undefined;

    const observer = new ResizeObserver(() => {
      redrawCanvas(strokesRef.current, draftStroke);
    });
    observer.observe(container);
    return () => observer.disconnect();
  }, [draftStroke, redrawCanvas]);

  const getPoint = useCallback((event: React.PointerEvent<Element>): StrokePoint | null => {
    if (!containerRef.current) return null;
    const { fx, fy } = pointerToFraction(event, containerRef.current);
    return { x: fx, y: fy };
  }, []);

  const getBrushDisplaySize = useCallback(() => {
    const rect = containerRef.current?.getBoundingClientRect();
    if (!rect) return Math.max(1, Math.round(Number(penSize) || 1));
    const scaleX = imageWidth > 0 ? rect.width / imageWidth : 1;
    const scaleY = imageHeight > 0 ? rect.height / imageHeight : 1;
    const brushScale = Math.max(0.5, Math.min(scaleX, scaleY));
    return Math.max(1, (Math.max(1, Math.round(Number(penSize) || 1)) * brushScale));
  }, [imageHeight, imageWidth, penSize]);

  const appendPoint = useCallback((stroke: Stroke | null, point: StrokePoint | null): Stroke | null => {
    if (!stroke || !point) return stroke;
    const lastPoint = stroke.points[stroke.points.length - 1];
    if (lastPoint && Math.abs(lastPoint.x - point.x) < 0.001 && Math.abs(lastPoint.y - point.y) < 0.001) {
      return stroke;
    }
    return {
      ...stroke,
      points: [...stroke.points, point],
    };
  }, []);

  const commitStroke = useCallback((stroke: Stroke | null) => {
    const normalizedStroke = sanitizeStroke(stroke, penSize);
    setDraftStroke(null);
    setDrawing(false);
    if (!normalizedStroke || !nodeId || !onWidgetChange) return;

    const nextStrokes = [...strokesRef.current, normalizedStroke];
    strokesRef.current = nextStrokes;
    setStrokes(nextStrokes);
    onWidgetChange(nodeId, 'mask_paths', JSON.stringify(nextStrokes));
  }, [nodeId, onWidgetChange, penSize]);

  const handlePointerDown = useCallback((event: React.PointerEvent<Element>) => {
    if ((event.target as HTMLElement).closest('button')) return;
    const point = getPoint(event);
    if (!point) return;

    event.preventDefault();
    event.stopPropagation();
    event.currentTarget.setPointerCapture(event.pointerId);
    setCursorPoint(point);
    setDrawing(true);
    setDraftStroke({
      size: Math.max(1, Math.round(Number(penSize) || 1)),
      points: [point],
    });
  }, [getPoint, penSize]);

  const handlePointerMove = useCallback((event: React.PointerEvent<Element>) => {
    const point = getPoint(event);
    if (!point) return;
    setCursorPoint(point);
    if (!drawing) return;

    setDraftStroke((current) => appendPoint(current, point));
  }, [appendPoint, drawing, getPoint]);

  const handlePointerUp = useCallback(() => {
    if (!drawing) return;
    commitStroke(draftStrokeRef.current);
  }, [commitStroke, drawing]);

  const handlePointerCancel = useCallback(() => {
    // Interrupted stroke (pointer capture lost to a gesture): drop the draft
    // so the next interaction starts clean instead of committing a stale
    // partial stroke.
    if (!drawing) return;
    setDrawing(false);
    draftStrokeRef.current = null;
    setDraftStroke(null);
  }, [drawing]);

  const handlePointerLeave = useCallback(() => {
    if (!drawing) {
      setCursorPoint(null);
    }
  }, [drawing]);

  return (
    <div
      ref={containerRef}
      className={`nodrag nowheel mask-paint-overlay${drawing ? ' mask-paint-overlay-drawing' : ''}`}
      onPointerDown={handlePointerDown}
      onPointerMove={handlePointerMove}
      onPointerUp={handlePointerUp}
      onLostPointerCapture={handlePointerUp}
      onPointerCancel={handlePointerCancel}
      onPointerLeave={handlePointerLeave}
    >
      <img
        src={image}
        alt="mask source"
        draggable={false}
        className="mask-paint-image"
        onLoad={() => redrawCanvas(strokesRef.current, draftStroke)}
      />
      <canvas ref={canvasRef} className="mask-paint-canvas" />
      {cursorPoint && (
        <div
          className="mask-paint-cursor"
          style={{
            left: `${cursorPoint.x * 100}%`,
            top: `${cursorPoint.y * 100}%`,
            width: `${getBrushDisplaySize()}px`,
            height: `${getBrushDisplaySize()}px`,
          }}
        />
      )}
    </div>
  );
}
