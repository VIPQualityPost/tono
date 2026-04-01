import test from 'node:test';
import assert from 'node:assert/strict';

import {
  beginTrackedNodeRequest,
  isTrackedNodeRequestCurrent,
  resolveLoadNodeChannelPath,
} from '../src/loadNodeOutputs.ts';

test('resolveLoadNodeChannelPath can resolve a new ImageDemo node from its explicit selection before mount', () => {
  const resolvedPath = resolveLoadNodeChannelPath({
    explicitPath: 'APL_Figure4.ibw',
    className: '',
    widgetValues: {},
  });

  assert.equal(resolvedPath, 'APL_Figure4.ibw');
});

test('resolveLoadNodeChannelPath falls back to the current widget value for load nodes', () => {
  assert.equal(resolveLoadNodeChannelPath({
    className: 'Image',
    widgetValues: { filename: 'scan.ibw' },
  }), 'scan.ibw');

  assert.equal(resolveLoadNodeChannelPath({
    className: 'ImageDemo',
    widgetValues: { name: 'demo.ibw' },
  }), 'demo.ibw');
});

test('tracked load-node requests ignore stale async responses', () => {
  const requestVersions = new Map();

  const first = beginTrackedNodeRequest(requestVersions, '42');
  const second = beginTrackedNodeRequest(requestVersions, '42');

  assert.equal(isTrackedNodeRequestCurrent(requestVersions, '42', first), false);
  assert.equal(isTrackedNodeRequestCurrent(requestVersions, '42', second), true);
});
