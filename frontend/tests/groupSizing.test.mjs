import test from 'node:test';
import assert from 'node:assert/strict';

import { getGroupMinimumSize } from '../src/groupSizing.js';

test('getGroupMinimumSize keeps the base minimum for empty groups', () => {
  assert.deepEqual(getGroupMinimumSize([]), { width: 260, height: 180 });
});

test('getGroupMinimumSize grows to fit child bounds plus padding', () => {
  const nodes = [
    {
      position: { x: 24, y: 60 },
      style: { width: 180, height: 100 },
    },
    {
      position: { x: 260, y: 150 },
      style: { width: 220, height: 140 },
    },
  ];

  assert.deepEqual(getGroupMinimumSize(nodes), {
    width: 504,
    height: 314,
  });
});
