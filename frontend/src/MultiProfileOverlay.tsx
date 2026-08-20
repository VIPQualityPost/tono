import React, { useRef, useState, useCallback, useEffect } from 'react';
import { clamp, pointerToFraction } from './overlayUtils';

export const CAPTURE_SELECTOR = '.multiprofile-overlay';

interface MultiProfileOverlayProps {
  image: string;
  row: number;
  direction: 'horizontal' | 'vertical';
  maxIndex: number;
  nodeId: string;
  onWidgetChange: (nodeId: string, name: string, value: unknown) => void;
}

export default function MultiProfileOverlay({
  image, row, direction, maxIndex,
  nodeId, onWidgetChange,
}: MultiProfileOverlayProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [draftRow, setDraftRow] = useState<number | null>(null);
  const draggingRef = useRef(false);
  const pendingCommitRef = useRef<number | null>(null);

  useEffect(() => {
    if (pendingCommitRef.current !== null && row !== pendingCommitRef.current) {
      // The backend clamped/rounded the committed row, so the emitted value
      // never equals the draft; accept any fresh backend row as ground truth
      // so the stale draft cannot linger forever.
      pendingCommitRef.current = null;
      setDraftRow(null);
    } else if (pendingCommitRef.current !== null && row === pendingCommitRef.current) {
      pendingCommitRef.current = null;
      setDraftRow(null);
    }
  }, [row]);

  const displayRow = draftRow ?? row;

  const fractionFromEvent = useCallback((e: React.PointerEvent<Element>): number => {
    if (!containerRef.current) return 0;
    const { fx, fy } = pointerToFraction(e, containerRef.current);
    return direction === 'horizontal' ? fy : fx;
  }, [direction]);

  const fractionToIndex = useCallback((frac: number): number => {
    return clamp(Math.round(frac * maxIndex), 0, maxIndex);
  }, [maxIndex]);

  const onPointerDown = useCallback((e: React.PointerEvent<Element>) => {
    e.stopPropagation();
    e.preventDefault();
    (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
    draggingRef.current = true;
    setDraftRow(fractionToIndex(fractionFromEvent(e)));
  }, [fractionFromEvent, fractionToIndex]);

  const onPointerMove = useCallback((e: React.PointerEvent<Element>) => {
    if (!draggingRef.current) return;
    setDraftRow(fractionToIndex(fractionFromEvent(e)));
  }, [fractionFromEvent, fractionToIndex]);

  const onPointerUp = useCallback(() => {
    if (draggingRef.current && draftRow !== null) {
      pendingCommitRef.current = draftRow;
      onWidgetChange(nodeId, 'row', draftRow);
    }
    draggingRef.current = false;
  }, [draftRow, nodeId, onWidgetChange]);

  const fracPos = maxIndex > 0 ? displayRow / maxIndex : 0;
  const linePct = clamp(fracPos * 100, 0, 100);

  const lineStyle: React.CSSProperties = direction === 'horizontal'
    ? { left: 0, right: 0, top: `${linePct}%`, height: 0 }
    : { top: 0, bottom: 0, left: `${linePct}%`, width: 0 };

  const cursorClass = direction === 'horizontal' ? 'cursor-row' : 'cursor-col';

  return (
    <div
      ref={containerRef}
      className={`nodrag nowheel multiprofile-overlay ${cursorClass}`}
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={onPointerUp}
      onLostPointerCapture={onPointerUp}
    >
      <img src={image} alt="A blended with B" draggable={false} className="multiprofile-image" />
      <div className={`multiprofile-line multiprofile-line-${direction}`} style={lineStyle} />
      <div className="multiprofile-readout">
        {direction === 'horizontal' ? 'row' : 'col'} {displayRow}
      </div>
    </div>
  );
}
