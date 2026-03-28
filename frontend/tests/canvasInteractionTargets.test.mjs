import test from 'node:test';
import assert from 'node:assert/strict';

import {
  canOpenCanvasContextMenuTarget,
  canStartCanvasRightDragZoomTarget,
  isEditableInteractionTarget,
  isSecondaryCanvasContextEvent,
} from '../src/canvasInteractionTargets.js';

function makeTarget(activeSelectors = []) {
  const selectorSet = new Set(activeSelectors);
  return {
    closest(selector) {
      const parts = String(selector).split(',').map((part) => part.trim());
      return parts.some((part) => selectorSet.has(part)) ? {} : null;
    },
  };
}

test('editable canvas targets stay editable', () => {
  const inputTarget = makeTarget(['input']);
  assert.equal(isEditableInteractionTarget(inputTarget), true);
  assert.equal(canOpenCanvasContextMenuTarget(inputTarget), false);
  assert.equal(canStartCanvasRightDragZoomTarget(inputTarget), false);
});

test('empty pane targets allow the custom canvas context menu', () => {
  const paneTarget = makeTarget(['.react-flow__pane']);
  assert.equal(canOpenCanvasContextMenuTarget(paneTarget), true);
  assert.equal(canStartCanvasRightDragZoomTarget(paneTarget), true);
});

test('viewport-level targets also allow the custom canvas context menu', () => {
  const viewportTarget = makeTarget(['.react-flow__viewport']);
  assert.equal(canOpenCanvasContextMenuTarget(viewportTarget), true);
  assert.equal(canStartCanvasRightDragZoomTarget(viewportTarget), true);
});

test('node and surface-view targets do not open the canvas context menu', () => {
  assert.equal(canOpenCanvasContextMenuTarget(makeTarget(['.react-flow__node', '.react-flow__pane'])), false);
  assert.equal(canOpenCanvasContextMenuTarget(makeTarget(['.surface-view-container', '.react-flow__pane'])), false);
});

test('secondary canvas context detection includes macOS ctrl-click', () => {
  assert.equal(isSecondaryCanvasContextEvent({ button: 2, ctrlKey: false }), true);
  assert.equal(isSecondaryCanvasContextEvent({ button: 0, ctrlKey: true }), true);
  assert.equal(isSecondaryCanvasContextEvent({ button: 0, ctrlKey: false }), false);
});
