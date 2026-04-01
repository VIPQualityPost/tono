import test from 'node:test';
import assert from 'node:assert/strict';

import {
  MARKUP_DEFAULT_COLOR,
  MARKUP_DEFAULT_SHAPE,
  getArrowGeometry,
  getMarkupPreviewStrokeWidth,
  sanitizeMarkupColor,
  sanitizeMarkupShape,
} from '../src/markupShapeGeometry.ts';

test('markup defaults use arrow and red', () => {
  assert.equal(MARKUP_DEFAULT_SHAPE, 'arrow');
  assert.equal(MARKUP_DEFAULT_COLOR, '#ff0000');
  assert.equal(sanitizeMarkupColor(undefined), '#ff0000');
});

test('sanitizeMarkupShape falls back to arrow and red', () => {
  assert.deepEqual(
    sanitizeMarkupShape(
      {
        kind: 'triangle',
        x1: 0.1,
        y1: 0.2,
        x2: 0.9,
        y2: 0.8,
        width: 5,
        color: 'not-a-color',
      },
      MARKUP_DEFAULT_SHAPE,
      MARKUP_DEFAULT_COLOR,
      3,
    ),
    {
      kind: 'arrow',
      x1: 0.1,
      y1: 0.2,
      x2: 0.9,
      y2: 0.8,
      width: 5,
      color: '#ff0000',
    },
  );
});

test('getArrowGeometry keeps the shaft at the head base with no rounded overlap', () => {
  const arrow = getArrowGeometry(
    {
      x1: 0,
      y1: 0,
      x2: 1,
      y2: 0,
      width: 4,
    },
    100,
    100,
  );

  assert.equal(arrow.line, '0,0 84,0');
  assert.equal(arrow.head, '100,0 84,6 84,-6');
});

test('getMarkupPreviewStrokeWidth matches backend preview scaling', () => {
  assert.equal(getMarkupPreviewStrokeWidth(10, 256, 256), 10);
  assert.equal(getMarkupPreviewStrokeWidth(10, 1024, 768), 20);
});
