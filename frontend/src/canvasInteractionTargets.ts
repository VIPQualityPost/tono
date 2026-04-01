const EXCLUDED_CANVAS_TARGETS = '.context-menu, .react-flow__node, .react-flow__edge, .react-flow__controls, .react-flow__minimap, .surface-view-container';
const CANVAS_AREA_TARGETS = '.react-flow, .react-flow__renderer, .react-flow__viewport, .react-flow__pane, .react-flow__background, .react-flow__selectionpane';

function getTargetElement(target: EventTarget | null): Element | null {
  if (!target) return null;
  if (typeof (target as Element).closest === 'function') return target as Element;
  const parent = (target as Node).parentElement;
  if (parent && typeof parent.closest === 'function') {
    return parent;
  }
  return null;
}

function supportsClosest(target: EventTarget | null): boolean {
  return !!getTargetElement(target);
}

function matchesClosest(target: EventTarget | null, selector: string): boolean {
  const element = getTargetElement(target);
  return !!element && element.closest(selector) !== null;
}

export function isEditableInteractionTarget(target: EventTarget | null): boolean {
  if (!supportsClosest(target)) return false;
  if (matchesClosest(target, 'input, textarea, select')) return true;
  return matchesClosest(target, '[contenteditable="true"]');
}

export function canStartCanvasRightDragZoomTarget(target: EventTarget | null): boolean {
  if (!supportsClosest(target)) return false;
  if (isEditableInteractionTarget(target)) return false;
  if (matchesClosest(target, EXCLUDED_CANVAS_TARGETS)) {
    return false;
  }
  return matchesClosest(target, CANVAS_AREA_TARGETS);
}

export function canOpenCanvasContextMenuTarget(target: EventTarget | null): boolean {
  if (!supportsClosest(target)) return false;
  if (isEditableInteractionTarget(target)) return false;
  if (matchesClosest(target, EXCLUDED_CANVAS_TARGETS)) {
    return false;
  }
  return matchesClosest(target, CANVAS_AREA_TARGETS);
}

export function isSecondaryCanvasContextEvent(event: MouseEvent | null): boolean {
  if (!event || typeof event.button !== 'number') return false;
  return event.button === 2 || (event.button === 0 && !!event.ctrlKey);
}
