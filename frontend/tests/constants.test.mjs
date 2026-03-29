import test from 'node:test';
import assert from 'node:assert/strict';

import {
  DATA_TYPES,
  getAcceptedSocketTypes,
  isDataSocketSpec,
  socketSpecAcceptsType,
} from '../src/constants.js';

test('intrinsic socket compatibility still allows INT to connect to FLOAT sockets', () => {
  assert.equal(socketSpecAcceptsType('INT', 'FLOAT'), true);
  assert.equal(socketSpecAcceptsType('FLOAT', 'INT'), true);
});

test('retired save alias types are no longer first-class socket types', () => {
  assert.equal(DATA_TYPES.has('SAVE_VALUE'), false);
  assert.equal(DATA_TYPES.has('SAVE_LAYER'), false);
});

test('accepted_types extend canonical socket compatibility without reintroducing alias types', () => {
  const spec = ['RECORD_TABLE', { accepted_types: ['DATA_TABLE'] }];

  assert.equal(isDataSocketSpec(spec), true);
  assert.deepEqual(
    Array.from(getAcceptedSocketTypes(spec)).sort(),
    ['RECORD_TABLE', 'DATA_TABLE'],
  );
  assert.equal(socketSpecAcceptsType('DATA_TABLE', spec), true);
  assert.equal(socketSpecAcceptsType('LINE', spec), false);
});
