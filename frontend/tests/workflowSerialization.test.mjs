import test from 'node:test';
import assert from 'node:assert/strict';

import { hydrateWorkflowState } from '../src/workflowHydration.ts';
import { serializeWorkflowState } from '../src/workflowSerialization.ts';

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
        width: 320,
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

test('hydrateWorkflowState clears shared path widgets and uses registry definitions', () => {
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
  // The saved edge targets node '3', which is not in the payload — hydration
  // must drop dangling edges instead of rendering phantom connections.
  assert.deepEqual(hydrated.edges, []);
  assert.equal(hydrated.nodes[0].type, 'custom');
  assert.equal(hydrated.nodes[0].dragHandle, '.drag-handle');
  assert.equal(hydrated.nodes[0].data.label, 'Image');
  assert.equal(hydrated.nodes[0].data.previewImage, null);
  assert.equal(hydrated.nodes[0].data.widgetValues.filename, '');
  assert.equal(hydrated.nodes[0].data.widgetValues.colormap, 'viridis');
  assert.deepEqual(hydrated.nodes[0].data.definition.output, ['DATA_FIELD']);
  assert.deepEqual(hydrated.nodes[0].data.definition.output_name, ['field']);
  assert.deepEqual(hydrated.nodes[0].data.definition.input, defs.Image.input);
});

test('serializeWorkflowState and hydrateWorkflowState clear path-like widgets without restoring saved outputs', () => {
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
  assert.deepEqual(hydrated.nodes[0].data.definition.output, ['DATA_FIELD']);
  assert.deepEqual(hydrated.nodes[0].data.definition.output_name, ['field']);
  // Edge e7-9 points at node '9', which is not in the payload — pruned.
  assert.deepEqual(hydrated.edges, []);
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
  assert.deepEqual(hydrated.nodes[0].data.definition.output, ['PATH']);
  assert.deepEqual(hydrated.nodes[0].data.definition.output_name, ['path']);
});

test('View3D runtime viewport state is not persisted or rehydrated with workflows', () => {
  const nodes = [
    {
      id: '41',
      type: 'custom',
      position: { x: 10, y: 20 },
      data: {
        label: '3D View',
        className: 'View3D',
        widgetValues: { z_scale: 1 },
        runtimeValues: {
          camera_azimuth: 0.42,
          camera_polar: 1.2,
          camera_distance: 2.5,
          camera_target_x: 0.1,
          camera_target_y: 0.2,
          camera_target_z: 0.3,
          viewport_snapshot: 'data:image/png;base64,abc',
        },
      },
    },
  ];

  const serialized = serializeWorkflowState(nodes, []);

  assert.equal('runtimeValues' in serialized.nodes[0].data, false);

  const hydrated = hydrateWorkflowState(serialized, {
    View3D: { output: ['MESH_MODEL', 'IMAGE'], output_name: ['mesh', 'viewport'] },
  });

  assert.deepEqual(hydrated.nodes[0].data.runtimeValues, {});
});

test('workflow serialization preserves wrapper class names for group shells', () => {
  const nodes = [
    {
      id: '31',
      type: 'custom',
      className: 'group-shell',
      position: { x: 5, y: 15 },
      style: { width: 420, height: 260 },
      data: {
        label: 'group',
        className: 'Group',
        widgetValues: {},
      },
    },
  ];

  const serialized = serializeWorkflowState(nodes, []);
  const hydrated = hydrateWorkflowState(serialized, {});

  assert.equal(serialized.nodes[0].className, 'group-shell');
  assert.equal(hydrated.nodes[0].className, 'group-shell');
});
