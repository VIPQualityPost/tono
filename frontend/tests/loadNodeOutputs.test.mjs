import test from 'node:test';
import assert from 'node:assert/strict';

import {
  beginTrackedNodeRequest,
  buildLoadNodeOutputs,
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

const CHANNELS = [
  { name: 'HeightTrace', type: 'DATA_FIELD' },
  { name: 'DeflectionTrace', type: 'DATA_FIELD' },
  { name: 'ZSensorTrace', type: 'DATA_FIELD' },
];

test('buildLoadNodeOutputs exposes ImageDemo channels directly (no path slot)', () => {
  const { output, outputName } = buildLoadNodeOutputs('ImageDemo', CHANNELS);

  assert.deepEqual(output, ['DATA_FIELD', 'DATA_FIELD', 'DATA_FIELD']);
  assert.deepEqual(outputName, ['HeightTrace', 'DeflectionTrace', 'ZSensorTrace']);
  // Slot k must resolve to channel k — a leading path slot would shift
  // every connection onto the next channel's data.
  assert.equal(outputName[0], 'HeightTrace');
  assert.equal(outputName[1], 'DeflectionTrace');
  assert.equal(outputName[2], 'ZSensorTrace');
});

test('buildLoadNodeOutputs prepends the path output for Image', () => {
  const { output, outputName } = buildLoadNodeOutputs('Image', CHANNELS);

  assert.deepEqual(output, ['FILE_PATH', 'DATA_FIELD', 'DATA_FIELD', 'DATA_FIELD']);
  assert.deepEqual(outputName, ['path', 'HeightTrace', 'DeflectionTrace', 'ZSensorTrace']);
});

test('buildLoadNodeOutputs defaults a missing selection to a single field', () => {
  assert.deepEqual(buildLoadNodeOutputs('ImageDemo', []), { output: [], outputName: [] });
  assert.deepEqual(buildLoadNodeOutputs('ImageDemo', [{ name: '', type: '' }]), {
    output: ['DATA_FIELD'],
    outputName: ['field'],
  });
  assert.deepEqual(buildLoadNodeOutputs('Image', [{ name: '', type: '' }]), {
    output: ['FILE_PATH', 'DATA_FIELD'],
    outputName: ['path', 'field'],
  });
});
