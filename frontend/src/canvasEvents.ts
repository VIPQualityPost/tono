import { getNodeCenter, getGroupWorkspaceBounds, rectContainsPoint } from './nodeGeometry';

export function getEventClientPosition(event: any) {
  if (!event) return null;
  const point = 'changedTouches' in event && event.changedTouches?.[0]
    ? event.changedTouches[0]
    : ('touches' in event && event.touches?.[0] ? event.touches[0] : event);
  if (!Number.isFinite(point?.clientX) || !Number.isFinite(point?.clientY)) return null;
  return { x: point.clientX, y: point.clientY };
}

export function getEventFlowPosition(event: any, reactFlow: any) {
  const clientPosition = getEventClientPosition(event);
  if (!clientPosition || typeof reactFlow?.screenToFlowPosition !== 'function') return null;
  return reactFlow.screenToFlowPosition(clientPosition);
}

export function getDragIntent(event: any, reactFlow: any, dragState: any) {
  if (!dragState?.pointerOffset || !dragState?.anchorStartAbsolute) return null;
  const pointerFlowPos = getEventFlowPosition(event, reactFlow);
  if (!pointerFlowPos) return null;

  const anchorAbsolute = {
    x: pointerFlowPos.x - dragState.pointerOffset.x,
    y: pointerFlowPos.y - dragState.pointerOffset.y,
  };
  const delta = {
    x: anchorAbsolute.x - (Number(dragState.anchorStartAbsolute.x) || 0),
    y: anchorAbsolute.y - (Number(dragState.anchorStartAbsolute.y) || 0),
  };
  const absolutePositions = new Map(
    Object.entries(dragState.absolutePositions || {}).map(([id, pos]: [string, any]) => [
      id,
      {
        x: (Number(pos?.x) || 0) + delta.x,
        y: (Number(pos?.y) || 0) + delta.y,
      },
    ]),
  );

  return {
    pointerFlowPos,
    anchorAbsolute,
    absolutePositions,
  };
}

export function isEditableTarget(target: any) {
  if (!target || !(target instanceof Element)) return false;
  if (target.closest('input, textarea, select')) return true;
  return target.closest('[contenteditable="true"]') !== null;
}

export function clampNumber(value: number, min: number, max: number) {
  return Math.min(max, Math.max(min, value));
}

export function canStartCanvasRightDragZoom(target: any) {
  if (!target || !(target instanceof Element)) return false;
  if (isEditableTarget(target)) return false;
  if (target.closest('.context-menu, .react-flow__node, .react-flow__edge, .react-flow__controls, .react-flow__minimap, .surface-view-container')) {
    return false;
  }
  return target.closest('.react-flow__pane, .react-flow__background') !== null;
}

export function compareMenuNodes(a: any, b: any) {
  const orderA = Number.isFinite(a?.menu_order)
    ? a.menu_order
    : Number.isFinite(a?.def?.menu_order)
      ? a.def.menu_order
      : Number.MAX_SAFE_INTEGER;
  const orderB = Number.isFinite(b?.menu_order)
    ? b.menu_order
    : Number.isFinite(b?.def?.menu_order)
      ? b.def.menu_order
      : Number.MAX_SAFE_INTEGER;
  if (orderA !== orderB) return orderA - orderB;

  const nameA = (a?.def?.display_name || a?.className || '').toLowerCase();
  const nameB = (b?.def?.display_name || b?.className || '').toLowerCase();
  return nameA.localeCompare(nameB);
}

export function compareMenuCategories(a: any, b: any) {
  const orderA = Number.isFinite(a?.order) ? a.order : Number.MAX_SAFE_INTEGER;
  const orderB = Number.isFinite(b?.order) ? b.order : Number.MAX_SAFE_INTEGER;
  if (orderA !== orderB) return orderA - orderB;
  return String(a?.name || '').localeCompare(String(b?.name || ''));
}
