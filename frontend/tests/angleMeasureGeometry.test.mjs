import test from 'node:test';
import assert from 'node:assert/strict';

import {
  getAngleLabelBasePosition,
  getAngleLabelPosition,
  measureAngleDegrees,
  moveAngleWidget,
} from '../src/angleMeasureGeometry.js';

test('measureAngleDegrees returns the included angle', () => {
  assert.equal(measureAngleDegrees(0, 1, 0, 0, 1, 0), 90);
  assert.ok(Math.abs(measureAngleDegrees(-1, 0, 0, 0, 1, 0) - 180) < 1e-9);
});

test('moveAngleWidget translates all points together', () => {
  const moved = moveAngleWidget(
    { x1: 0.2, y1: 0.7, xm: 0.5, ym: 0.5, x2: 0.8, y2: 0.3 },
    0.1,
    -0.2,
  );

  assert.deepEqual(moved, {
    x1: 0.3,
    y1: 0.5,
    xm: 0.6,
    ym: 0.3,
    x2: 0.9,
    y2: 0.1,
  });
});

test('moveAngleWidget clamps whole-widget drags to the image bounds', () => {
  const moved = moveAngleWidget(
    { x1: 0.2, y1: 0.7, xm: 0.5, ym: 0.5, x2: 0.8, y2: 0.3 },
    0.4,
    -0.5,
  );

  assert.deepEqual(moved, {
    x1: 0.4,
    y1: 0.4,
    xm: 0.7,
    ym: 0.2,
    x2: 1,
    y2: 0,
  });
});

test('getAngleLabelPosition follows the angle bisector and applies draggable offsets', () => {
  const base = getAngleLabelBasePosition(0.2, 0.5, 0.5, 0.5, 0.5, 0.2);
  assert.ok(base.x < 0.5);
  assert.ok(base.y < 0.5);

  const shifted = getAngleLabelPosition(
    { x1: 0.2, y1: 0.5, xm: 0.5, ym: 0.5, x2: 0.5, y2: 0.2 },
    -0.1,
    0.05,
  );
  assert.ok(Math.abs(shifted.x - (base.x - 0.1)) < 1e-9);
  assert.ok(Math.abs(shifted.y - (base.y + 0.05)) < 1e-9);
});
