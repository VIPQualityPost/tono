import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';

function clampFraction(value) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return 0;
  return Math.max(0, Math.min(1, numeric));
}

function sanitizeColor(color, fallback = '#ffd54f') {
  if (typeof color !== 'string') return fallback;
  const value = color.trim();
  return /^#[0-9a-fA-F]{6}$/.test(value) ? value.toLowerCase() : fallback;
}

function sanitizeShape(shape, fallbackShape, fallbackColor, fallbackWidth) {
  if (!shape || typeof shape !== 'object') return null;
  const kind = ['line', 'rectangle', 'circle', 'arrow'].includes(shape.kind) ? shape.kind : fallbackShape;
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
    color: sanitizeColor(shape.color, fallbackColor),
  };
}

function parseMarkupShapes(markupShapes, fallbackShape, fallbackColor, fallbackWidth) {
  if (Array.isArray(markupShapes)) {
    return markupShapes
      .map((shape) => sanitizeShape(shape, fallbackShape, fallbackColor, fallbackWidth))
      .filter(Boolean);
  }

  if (typeof markupShapes !== 'string' || !markupShapes.trim()) return [];

  try {
    const parsed = JSON.parse(markupShapes);
    if (!Array.isArray(parsed)) return [];
    return parsed
      .map((shape) => sanitizeShape(shape, fallbackShape, fallbackColor, fallbackWidth))
      .filter(Boolean);
  } catch {
    return [];
  }
}

function arrowPoints(shape, imageWidth, imageHeight) {
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
  const overlap = Math.max(1, strokeWidth * 0.75);
  const shaftX = x2 - ux * Math.max(0, headLength - overlap);
  const shaftY = y2 - uy * Math.max(0, headLength - overlap);
  const headBaseX = x2 - ux * headLength;
  const headBaseY = y2 - uy * headLength;
  const px = -uy;
  const py = ux;
  const leftX = headBaseX + px * headWidth * 0.5;
  const leftY = headBaseY + py * headWidth * 0.5;
  const rightX = headBaseX - px * headWidth * 0.5;
  const rightY = headBaseY - py * headWidth * 0.5;
  return {
    line: `${x1},${y1} ${shaftX},${shaftY}`,
    head: `${x2},${y2} ${leftX},${leftY} ${rightX},${rightY}`,
  };
}

function ShapeElement({ shape, imageWidth, imageHeight }) {
  const x1 = shape.x1 * imageWidth;
  const y1 = shape.y1 * imageHeight;
  const x2 = shape.x2 * imageWidth;
  const y2 = shape.y2 * imageHeight;
  const left = Math.min(x1, x2);
  const top = Math.min(y1, y2);
  const width = Math.abs(x2 - x1);
  const height = Math.abs(y2 - y1);
  const strokeWidth = Math.max(1, shape.width);
  const common = {
    fill: 'none',
    stroke: shape.color,
    strokeWidth,
    strokeLinecap: 'round',
    strokeLinejoin: 'round',
    vectorEffect: 'non-scaling-stroke',
  };

  if (shape.kind === 'line') {
    return <line x1={x1} y1={y1} x2={x2} y2={y2} {...common} />;
  }

  if (shape.kind === 'rectangle') {
    return <rect x={left} y={top} width={width} height={height} {...common} />;
  }

  if (shape.kind === 'circle') {
    return (
      <ellipse
        cx={left + width / 2}
        cy={top + height / 2}
        rx={width / 2}
        ry={height / 2}
        {...common}
      />
    );
  }

  const arrow = arrowPoints(shape, imageWidth, imageHeight);
  return (
    <>
      <polyline points={arrow.line} {...common} />
      <polygon
        points={arrow.head}
        fill={shape.color}
      />
    </>
  );
}

export default function MarkupOverlay({
  image,
  shape,
  strokeColor,
  strokeWidth,
  markupShapes,
  nodeId,
  onWidgetChange,
}) {
  const containerRef = useRef(null);
  const imageRef = useRef(null);
  const shapesRef = useRef([]);
  const [draftShape, setDraftShape] = useState(null);
  const [drawing, setDrawing] = useState(false);
  const [imageSize, setImageSize] = useState({ width: 1, height: 1 });

  const normalizedShape = useMemo(
    () => (['line', 'rectangle', 'circle', 'arrow'].includes(shape) ? shape : 'line'),
    [shape],
  );
  const normalizedColor = useMemo(() => sanitizeColor(strokeColor, '#ffd54f'), [strokeColor]);
  const normalizedWidth = useMemo(
    () => Math.max(1, Math.min(64, Math.round(Number(strokeWidth) || 3))),
    [strokeWidth],
  );

  const committedShapes = useMemo(
    () => parseMarkupShapes(markupShapes, normalizedShape, normalizedColor, normalizedWidth),
    [markupShapes, normalizedShape, normalizedColor, normalizedWidth],
  );

  useEffect(() => {
    shapesRef.current = committedShapes;
  }, [committedShapes]);

  useEffect(() => {
    const img = imageRef.current;
    if (!img) return;
    const updateImageSize = () => {
      const width = Math.max(1, img.naturalWidth || img.width || 1);
      const height = Math.max(1, img.naturalHeight || img.height || 1);
      setImageSize({ width, height });
    };

    updateImageSize();
    if (!img.complete) {
      img.addEventListener('load', updateImageSize);
      return () => img.removeEventListener('load', updateImageSize);
    }
    return undefined;
  }, [image]);

  const getPoint = useCallback((event) => {
    const rect = containerRef.current?.getBoundingClientRect();
    if (!rect) return null;
    return {
      x: Number(clampFraction((event.clientX - rect.left) / rect.width).toFixed(4)),
      y: Number(clampFraction((event.clientY - rect.top) / rect.height).toFixed(4)),
    };
  }, []);

  const commitShapes = useCallback((nextShapes) => {
    if (!nodeId || !onWidgetChange) return;
    onWidgetChange(nodeId, 'markup_shapes', JSON.stringify(nextShapes));
  }, [nodeId, onWidgetChange]);

  const handlePointerDown = useCallback((event) => {
    if (!onWidgetChange || event.target.closest('button')) return;
    const point = getPoint(event);
    if (!point) return;
    event.preventDefault();
    event.stopPropagation();
    event.currentTarget.setPointerCapture(event.pointerId);
    setDrawing(true);
    setDraftShape({
      kind: normalizedShape,
      color: normalizedColor,
      width: normalizedWidth,
      x1: point.x,
      y1: point.y,
      x2: point.x,
      y2: point.y,
    });
  }, [getPoint, normalizedColor, normalizedShape, normalizedWidth, onWidgetChange]);

  const handlePointerMove = useCallback((event) => {
    if (!drawing) return;
    const point = getPoint(event);
    if (!point) return;
    setDraftShape((current) => (current ? { ...current, x2: point.x, y2: point.y } : current));
  }, [drawing, getPoint]);

  const finishDrawing = useCallback(() => {
    if (!draftShape) {
      setDrawing(false);
      return;
    }
    const nextShape = sanitizeShape(draftShape, normalizedShape, normalizedColor, normalizedWidth);
    setDraftShape(null);
    setDrawing(false);
    if (!nextShape) return;
    commitShapes([...shapesRef.current, nextShape]);
  }, [commitShapes, draftShape, normalizedColor, normalizedShape, normalizedWidth]);

  const undoLast = useCallback(() => {
    if (shapesRef.current.length === 0) return;
    commitShapes(shapesRef.current.slice(0, -1));
  }, [commitShapes]);

  const clearAll = useCallback(() => {
    commitShapes([]);
  }, [commitShapes]);

  const renderedShapes = draftShape ? [...committedShapes, draftShape] : committedShapes;

  return (
    <div
      ref={containerRef}
      className={`nodrag nowheel markup-overlay${drawing ? ' markup-overlay-drawing' : ''}`}
      onPointerDown={handlePointerDown}
      onPointerMove={handlePointerMove}
      onPointerUp={finishDrawing}
      onPointerCancel={finishDrawing}
      onLostPointerCapture={finishDrawing}
    >
      <img ref={imageRef} src={image} alt="markup source" draggable={false} className="markup-image" />
      <svg
        className="markup-svg"
        viewBox={`0 0 ${imageSize.width} ${imageSize.height}`}
        preserveAspectRatio="none"
      >
        {renderedShapes.map((item, index) => (
          <ShapeElement
            key={`${item.kind}-${index}`}
            shape={item}
            imageWidth={imageSize.width}
            imageHeight={imageSize.height}
          />
        ))}
      </svg>
      <div className="markup-toolbar">
        <button className="markup-tool-btn" type="button" onClick={undoLast} disabled={committedShapes.length === 0}>
          Undo
        </button>
        <button className="markup-tool-btn" type="button" onClick={clearAll} disabled={committedShapes.length === 0}>
          Clear
        </button>
      </div>
    </div>
  );
}
