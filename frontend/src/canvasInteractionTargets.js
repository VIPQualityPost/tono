const EXCLUDED_CANVAS_TARGETS = '.context-menu, .react-flow__node, .react-flow__edge, .react-flow__controls, .react-flow__minimap, .surface-view-container';
const CANVAS_AREA_TARGETS = '.react-flow, .react-flow__renderer, .react-flow__viewport, .react-flow__pane, .react-flow__background, .react-flow__selectionpane';

function getTargetElement(target) {
  if (!target) return null;
  if (typeof target.closest === 'function') return target;
  if (target.parentElement && typeof target.parentElement.closest === 'function') {
    return target.parentElement;
  }
  return null;
}

function supportsClosest(target) {
  return !!getTargetElement(target);
}

function matchesClosest(target, selector) {
  const element = getTargetElement(target);
  return !!element && element.closest(selector) !== null;
}

export function isEditableInteractionTarget(target) {
  if (!supportsClosest(target)) return false;
  if (matchesClosest(target, 'input, textarea, select')) return true;
  return matchesClosest(target, '[contenteditable="true"]');
}

export function canStartCanvasRightDragZoomTarget(target) {
  if (!supportsClosest(target)) return false;
  if (isEditableInteractionTarget(target)) return false;
  if (matchesClosest(target, EXCLUDED_CANVAS_TARGETS)) {
    return false;
  }
  return matchesClosest(target, CANVAS_AREA_TARGETS);
}

export function canOpenCanvasContextMenuTarget(target) {
  if (!supportsClosest(target)) return false;
  if (isEditableInteractionTarget(target)) return false;
  if (matchesClosest(target, EXCLUDED_CANVAS_TARGETS)) {
    return false;
  }
  return matchesClosest(target, CANVAS_AREA_TARGETS);
}

export function isSecondaryCanvasContextEvent(event) {
  if (!event || typeof event.button !== 'number') return false;
  return event.button === 2 || (event.button === 0 && !!event.ctrlKey);
}
