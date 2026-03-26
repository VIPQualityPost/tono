import test from 'node:test';
import assert from 'node:assert/strict';

import { hydrateWorkflowState } from '../src/workflowHydration.js';
import { serializeWorkflowState } from '../src/workflowSerialization.js';

test('serializeWorkflowState keeps only stable workflow fields needed for reload', () => {
  const nodes = [
    {
      id: '1',
      type: 'custom',
      position: { x: 100, y: 200 },
      dragHandle: '.node-header',
      selected: true,
      width: 320,
      data: {
        label: 'Demo Label',
        className: 'DemoNode',
        widgetValues: { threshold: 0.42, mode: 'fast' },
        definition: { input: { required: { threshold: ['FLOAT', { default: 0.5 }] } } },
        previewImage: 'data:image/png;base64,abc',
        tableRows: [{ a: 1 }],
        meshData: { vertices: [1, 2, 3] },
        overlay: { active: true },
      },
    },
    {
      id: '2',
      position: { x: 10, y: 20 },
      data: {
        className: 'NoLabelNode',
      },
    },
  ];

  const edges = [
    {
      id: 'e1-2',
      source: '1',
      sourceHandle: 'output::0::IMAGE',
      target: '2',
      targetHandle: 'input::image::IMAGE',
      style: { stroke: '#fff', strokeWidth: 2 },
      selected: true,
      animated: true,
    },
  ];

  const serialized = serializeWorkflowState(nodes, edges);

  assert.deepEqual(serialized, {
    version: 1,
    nodes: [
      {
        id: '1',
        type: 'custom',
        position: { x: 100, y: 200 },
        dragHandle: '.node-header',
        data: {
          label: 'Demo Label',
          className: 'DemoNode',
          widgetValues: { threshold: 0.42, mode: 'fast' },
          output: [],
          output_name: [],
        },
      },
      {
        id: '2',
        type: 'custom',
        position: { x: 10, y: 20 },
        dragHandle: '.drag-handle',
        data: {
          label: 'NoLabelNode',
          className: 'NoLabelNode',
          widgetValues: {},
          output: [],
          output_name: [],
        },
      },
    ],
    edges: [
      {
        id: 'e1-2',
        source: '1',
        sourceHandle: 'output::0::IMAGE',
        target: '2',
        targetHandle: 'input::image::IMAGE',
        style: { stroke: '#fff', strokeWidth: 2 },
      },
    ],
  });

  assert.equal('definition' in serialized.nodes[0].data, false);
  assert.equal('previewImage' in serialized.nodes[0].data, false);
  assert.equal('selected' in serialized.edges[0], false);
});

test('hydrateWorkflowState clears shared path widgets while restoring saved dynamic outputs', () => {
  const saved = {
    version: 1,
    nodes: [
      {
        id: '12',
        position: { x: 40, y: 80 },
        data: {
          className: 'Image',
          widgetValues: { filename: 'scan.ibw', colormap: 'viridis' },
          output: ['DATA_FIELD', 'DATA_FIELD'],
          output_name: ['Height', 'Phase'],
          previewImage: 'stale',
        },
      },
    ],
    edges: [
      {
        id: 'e12-3',
        source: '12',
        sourceHandle: 'output::1::DATA_FIELD',
        target: '3',
        targetHandle: 'input::field::DATA_FIELD',
      },
    ],
  };

  const defs = {
    Image: {
      category: 'io',
      input: { required: { filename: ['FILE_PICKER', {}], colormap: [['viridis', 'gray'], {}] } },
      output: ['DATA_FIELD'],
      output_name: ['field'],
      manual_trigger: false,
    },
  };

  const hydrated = hydrateWorkflowState(saved, defs);

  assert.equal(hydrated.nextNodeId, 13);
  assert.deepEqual(hydrated.edges, saved.edges);
  assert.equal(hydrated.nodes[0].type, 'custom');
  assert.equal(hydrated.nodes[0].dragHandle, '.drag-handle');
  assert.equal(hydrated.nodes[0].data.label, 'Image');
  assert.equal(hydrated.nodes[0].data.previewImage, null);
  assert.equal(hydrated.nodes[0].data.widgetValues.filename, '');
  assert.equal(hydrated.nodes[0].data.widgetValues.colormap, 'viridis');
  assert.deepEqual(hydrated.nodes[0].data.definition.output, ['DATA_FIELD', 'DATA_FIELD']);
  assert.deepEqual(hydrated.nodes[0].data.definition.output_name, ['Height', 'Phase']);
  assert.deepEqual(hydrated.nodes[0].data.definition.input, defs.Image.input);
});

test('serializeWorkflowState and hydrateWorkflowState clear path-like widgets but preserve other metadata', () => {
  const nodes = [
    {
      id: '7',
      position: { x: 10, y: 20 },
      data: {
        label: 'Image',
        className: 'Image',
        widgetValues: { filename: 'scan.gwy', colormap: 'gray' },
        definition: {
          category: 'io',
          input: { required: { filename: ['FILE_PICKER', {}], colormap: [['gray', 'viridis'], {}] } },
          output: ['DATA_FIELD', 'DATA_FIELD', 'DATA_FIELD'],
          output_name: ['Topography', 'Error', 'Mask'],
        },
        previewImage: 'data:image/png;base64,stale',
      },
    },
  ];
  const edges = [
    {
      id: 'e7-9',
      source: '7',
      sourceHandle: 'output::2::DATA_FIELD',
      target: '9',
      targetHandle: 'input::field::DATA_FIELD',
    },
  ];
  const defs = {
    Image: {
      category: 'io',
      input: { required: { filename: ['FILE_PICKER', {}], colormap: [['gray', 'viridis'], {}] } },
      output: ['DATA_FIELD'],
      output_name: ['field'],
    },
  };

  const serialized = serializeWorkflowState(nodes, edges);
  const hydrated = hydrateWorkflowState(serialized, defs);

  assert.deepEqual(hydrated.nodes[0].data.widgetValues, { filename: '', colormap: 'gray' });
  assert.deepEqual(hydrated.nodes[0].data.definition.output, ['DATA_FIELD', 'DATA_FIELD', 'DATA_FIELD']);
  assert.deepEqual(hydrated.nodes[0].data.definition.output_name, ['Topography', 'Error', 'Mask']);
  assert.deepEqual(hydrated.edges, edges);
});

test('hydrateWorkflowState clears saved folder selections on shared workflows', () => {
  const saved = {
    version: 1,
    nodes: [
      {
        id: '21',
        position: { x: 0, y: 0 },
        data: {
          className: 'Folder',
          widgetValues: { folder: '/Users/alice/Desktop/shared-dataset' },
          output: ['PATH', 'PATH'],
          output_name: ['scan1.png', 'scan2.png'],
        },
      },
    ],
    edges: [],
  };

  const defs = {
    Folder: {
      category: 'io',
      input: { required: { folder: ['FOLDER_PICKER', {}] } },
      output: ['PATH'],
      output_name: ['path'],
    },
  };

  const hydrated = hydrateWorkflowState(saved, defs);

  assert.equal(hydrated.nodes[0].data.widgetValues.folder, '');
  assert.deepEqual(hydrated.nodes[0].data.definition.output, ['PATH', 'PATH']);
  assert.deepEqual(hydrated.nodes[0].data.definition.output_name, ['scan1.png', 'scan2.png']);
});
