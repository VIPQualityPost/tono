import test from 'node:test';
import assert from 'node:assert/strict';

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
