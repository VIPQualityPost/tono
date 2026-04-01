import test from 'node:test';
import assert from 'node:assert/strict';

import {
  buildCombinedInputNameByWidgetName,
  getWidgetCombinedInputName,
} from '../src/nodeWidgetLayout.ts';

test('getWidgetCombinedInputName pairs same-label hide_when_input_connected widgets with their matching input', () => {
  const dataInputByName = new Map([
    ['colormap_map', { name: 'colormap_map', type: 'COLORMAP', label: 'colormap' }],
  ]);

  const combinedInputName = getWidgetCombinedInputName({
    name: 'colormap',
    opts: { hide_when_input_connected: 'colormap_map' },
  }, dataInputByName);

  assert.equal(combinedInputName, 'colormap_map');
});

test('getWidgetCombinedInputName leaves unrelated hidden inputs as standalone rows', () => {
  const dataInputByName = new Map([
    ['path', { name: 'path', type: 'FILE_PATH', label: 'path' }],
  ]);

  const combinedInputName = getWidgetCombinedInputName({
    name: 'filename',
    opts: { hide_when_input_connected: 'path' },
  }, dataInputByName);

  assert.equal(combinedInputName, null);
});

test('buildCombinedInputNameByWidgetName preserves explicit top_socket_input pairings', () => {
  const combinedInputNameByWidgetName = buildCombinedInputNameByWidgetName(
    [
      {
        name: 'directory',
        opts: {
          top_socket_input: 'directory',
          hide_when_input_connected: 'directory',
        },
      },
    ],
    [
      { name: 'directory', type: 'STRING', label: 'directory' },
    ],
  );

  assert.equal(combinedInputNameByWidgetName.get('directory'), 'directory');
});
