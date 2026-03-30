import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';

export const CAPTURE_SELECTOR = '.markup-overlay';
import {
  getArrowGeometry,
  MARKUP_DEFAULT_COLOR,
  MARKUP_DEFAULT_SHAPE,
  getMarkupPreviewStrokeWidth,
  parseMarkupShapes,
  sanitizeMarkupColor,
  sanitizeMarkupShape,
} from './markupShapeGeometry.js';

function clampFraction(value) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return 0;
  return Math.max(0, Math.min(1, numeric));
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
  const strokeWidth = getMarkupPreviewStrokeWidth(shape.width, imageWidth, imageHeight);
  const renderShape = { ...shape, width: strokeWidth };
  const common = {
    fill: 'none',
    stroke: shape.color,
    strokeWidth,
    strokeLinecap: shape.kind === 'arrow' ? 'square' : 'round',
    strokeLinejoin: 'round',
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

  const arrow = getArrowGeometry(renderShape, imageWidth, imageHeight);
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
    () => (['line', 'rectangle', 'circle', 'arrow'].includes(shape) ? shape : MARKUP_DEFAULT_SHAPE),
    [shape],
  );
  const normalizedColor = useMemo(
    () => sanitizeMarkupColor(strokeColor, MARKUP_DEFAULT_COLOR),
    [strokeColor],
  );
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
    const nextShape = sanitizeMarkupShape(draftShape, normalizedShape, normalizedColor, normalizedWidth);
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
