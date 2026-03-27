import test from 'node:test';
import assert from 'node:assert/strict';

import { SOCKET_COMPATIBILITY } from '../src/constants.js';

test('SAVE_VALUE accepts ANNOTATION_SOURCE inputs', () => {
  assert.equal(SOCKET_COMPATIBILITY.SAVE_VALUE.has('ANNOTATION_SOURCE'), true);
});
