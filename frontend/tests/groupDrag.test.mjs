import test from 'node:test';
import assert from 'node:assert/strict';

import {
  GROUP_DRAG_RELEASE_DISTANCE,
  getPointDistanceOutsideRect,
  shouldReleaseFromGroup,
} from '../src/groupDrag.js';

test('getPointDistanceOutsideRect returns zero inside the rect', () => {
  const rect = { left: 10, top: 20, right: 110, bottom: 120 };
  assert.equal(getPointDistanceOutsideRect(rect, { x: 60, y: 70 }), 0);
});

test('shouldReleaseFromGroup waits for a small overshoot before releasing', () => {
  const rect = { left: 10, top: 20, right: 110, bottom: 120 };

  assert.equal(
    shouldReleaseFromGroup(rect, { x: 110 + GROUP_DRAG_RELEASE_DISTANCE - 1, y: 70 }),
    false,
  );
  assert.equal(
    shouldReleaseFromGroup(rect, { x: 110 + GROUP_DRAG_RELEASE_DISTANCE, y: 70 }),
    true,
  );
});
