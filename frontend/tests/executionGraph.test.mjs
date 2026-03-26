import test from 'node:test';
import assert from 'node:assert/strict';

import {
  serializeExecutionGraph,
  getAutoRunnableNodes,
  hasBlockingAutoRunInput,
} from '../src/executionGraph.js';

test('serializeExecutionGraph excludes isolated nodes from the backend prompt', () => {
  const nodes = [
    {
      id: '1',
      data: {
        className: 'Image',
        definition: {
          input: { required: { filename: ['FILE_PICKER', {}] }, optional: {} },
          manual_trigger: false,
        },
        widgetValues: { filename: 'scan.gwy' },
      },
    },
    {
      id: '2',
      data: {
        className: 'PreviewImage',
        definition: {
          input: { required: { field: ['DATA_FIELD', {}] }, optional: {} },
          manual_trigger: false,
        },
        widgetValues: {},
      },
    },
    {
      id: '3',
      data: {
        className: 'Image',
        definition: {
          input: { required: { filename: ['FILE_PICKER', {}] }, optional: {} },
          manual_trigger: false,
        },
        widgetValues: {},
      },
    },
  ];
  const edges = [
    {
      source: '1',
      sourceHandle: 'output::0::DATA_FIELD',
      target: '2',
      targetHandle: 'input::field::DATA_FIELD',
    },
  ];

  const prompt = serializeExecutionGraph(nodes, edges);

  assert.deepEqual(prompt, {
    '1': {
      class_type: 'Image',
      inputs: { filename: 'scan.gwy' },
    },
    '2': {
      class_type: 'PreviewImage',
      inputs: { field: ['1', 0] },
    },
  });
  assert.equal('3' in prompt, false);
});

test('serializeExecutionGraph includes isolated preview-load nodes alongside connected subgraphs', () => {
  const nodes = [
    {
      id: '1',
      data: {
        className: 'Image',
        definition: {
          input: { required: { filename: ['FILE_PICKER', {}] }, optional: {} },
          manual_trigger: false,
        },
        widgetValues: { filename: 'first.gwy' },
      },
    },
    {
      id: '2',
      data: {
        className: 'PreviewImage',
        definition: {
          input: { required: { field: ['DATA_FIELD', {}] }, optional: {} },
          manual_trigger: false,
        },
        widgetValues: {},
      },
    },
    {
      id: '3',
      data: {
        className: 'ImageDemo',
        definition: {
          input: { required: { name: [['demo.npy'], {}] }, optional: {} },
          manual_trigger: false,
        },
        widgetValues: { name: 'demo.npy' },
      },
    },
    {
      id: '4',
      data: {
        className: 'Image',
        definition: {
          input: { required: { filename: ['FILE_PICKER', {}] }, optional: {} },
          manual_trigger: false,
        },
        widgetValues: { filename: '' },
      },
    },
  ];
  const edges = [
    {
      source: '1',
      sourceHandle: 'output::0::DATA_FIELD',
      target: '2',
      targetHandle: 'input::field::DATA_FIELD',
    },
  ];

  const prompt = serializeExecutionGraph(nodes, edges);

  assert.deepEqual(prompt, {
    '1': {
      class_type: 'Image',
      inputs: { filename: 'first.gwy' },
    },
    '2': {
      class_type: 'PreviewImage',
      inputs: { field: ['1', 0] },
    },
    '3': {
      class_type: 'ImageDemo',
      inputs: { name: 'demo.npy' },
    },
  });
  assert.equal('4' in prompt, false);
});

test('serializeExecutionGraph allows a singleton Image graph so previews can run', () => {
  const nodes = [
    {
      id: '1',
      data: {
        className: 'Image',
        definition: {
          input: { required: { filename: ['FILE_PICKER', {}] }, optional: {} },
          manual_trigger: false,
        },
        widgetValues: { filename: 'scan.gwy' },
      },
    },
  ];

  const prompt = serializeExecutionGraph(nodes, []);

  assert.deepEqual(prompt, {
    '1': {
      class_type: 'Image',
      inputs: { filename: 'scan.gwy' },
    },
  });
});

test('serializeExecutionGraph allows a singleton ImageDemo graph so previews can run', () => {
  const nodes = [
    {
      id: '1',
      data: {
        className: 'ImageDemo',
        definition: {
          input: { required: { name: [['demo.npy'], {}] }, optional: {} },
          manual_trigger: false,
        },
        widgetValues: { name: 'demo.npy' },
      },
    },
  ];

  const prompt = serializeExecutionGraph(nodes, []);

  assert.deepEqual(prompt, {
    '1': {
      class_type: 'ImageDemo',
      inputs: { name: 'demo.npy' },
    },
  });
});

test('getAutoRunnableNodes ignores disconnected nodes when deciding what can auto-run', () => {
  const nodes = [
    { id: '1', data: { definition: {}, widgetValues: {} } },
    { id: '2', data: { definition: {}, widgetValues: {} } },
    { id: '3', data: { definition: {}, widgetValues: {} } },
  ];
  const edges = [
    {
      source: '1',
      sourceHandle: 'output::0::DATA_FIELD',
      target: '2',
      targetHandle: 'input::field::DATA_FIELD',
    },
  ];

  const runnable = getAutoRunnableNodes(nodes, edges);

  assert.deepEqual(runnable.map((node) => node.id), ['1', '2']);
});

test('getAutoRunnableNodes includes isolated preview-load nodes with selections', () => {
  const nodes = [
    { id: '1', data: { className: 'Image', definition: {}, widgetValues: { filename: 'first.gwy' } } },
    { id: '2', data: { className: 'PreviewImage', definition: {}, widgetValues: {} } },
    { id: '3', data: { className: 'ImageDemo', definition: {}, widgetValues: { name: 'demo.npy' } } },
    { id: '4', data: { className: 'Image', definition: {}, widgetValues: { filename: '' } } },
  ];
  const edges = [
    {
      source: '1',
      sourceHandle: 'output::0::DATA_FIELD',
      target: '2',
      targetHandle: 'input::field::DATA_FIELD',
    },
  ];

  const runnable = getAutoRunnableNodes(nodes, edges);

  assert.deepEqual(runnable.map((node) => node.id), ['1', '2', '3']);
});

test('getAutoRunnableNodes allows a singleton Image graph', () => {
  const nodes = [
    {
      id: '1',
      data: {
        className: 'Image',
        definition: {},
        widgetValues: { filename: 'scan.gwy' },
      },
    },
  ];

  const runnable = getAutoRunnableNodes(nodes, []);

  assert.deepEqual(runnable.map((node) => node.id), ['1']);
});

test('getAutoRunnableNodes allows a singleton ImageDemo graph', () => {
  const nodes = [
    {
      id: '1',
      data: {
        className: 'ImageDemo',
        definition: {},
        widgetValues: { name: 'demo.npy' },
      },
    },
  ];

  const runnable = getAutoRunnableNodes(nodes, []);

  assert.deepEqual(runnable.map((node) => node.id), ['1']);
});

test('hasBlockingAutoRunInput only blocks connected nodes with incomplete required inputs', () => {
  const node = {
    id: '2',
    data: {
      definition: {
        manual_trigger: false,
        input: {
          required: {
            field: ['DATA_FIELD', {}],
            filename: ['FILE_PICKER', {}],
          },
        },
      },
      widgetValues: { filename: '' },
    },
  };
  const completeEdges = [
    {
      source: '1',
      sourceHandle: 'output::0::DATA_FIELD',
      target: '2',
      targetHandle: 'input::field::DATA_FIELD',
    },
  ];

  assert.equal(hasBlockingAutoRunInput(node, completeEdges), true);
  assert.equal(
    hasBlockingAutoRunInput(
      {
        ...node,
        data: {
          ...node.data,
          widgetValues: { filename: 'scan.gwy' },
        },
      },
      completeEdges,
    ),
    false,
  );
});

test('hasBlockingAutoRunInput skips required file widgets when a connected socket overrides them', () => {
  const node = {
    id: '2',
    data: {
      definition: {
        manual_trigger: false,
        input: {
          required: {
            filename: ['FILE_PICKER', { hide_when_input_connected: 'path' }],
          },
          optional: {
            path: ['FILE_PATH', {}],
          },
        },
      },
      widgetValues: { filename: '' },
    },
  };
  const edges = [
    {
      source: '1',
      sourceHandle: 'output::0::FILE_PATH',
      target: '2',
      targetHandle: 'input::path::FILE_PATH',
    },
  ];

  assert.equal(hasBlockingAutoRunInput(node, edges), false);
});
