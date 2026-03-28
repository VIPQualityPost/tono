import test from 'node:test';
import assert from 'node:assert/strict';

import {
  buildNodeClipboardPayload,
  buildNodeClipboardPayloadForIds,
  instantiateNodeClipboardPayload,
  NODE_CLIPBOARD_KIND,
  parseNodeClipboardPayload,
} from '../src/nodeClipboard.js';

test('buildNodeClipboardPayload keeps only selected nodes and internal edges', () => {
  const nodes = [
    {
      id: '1',
      selected: true,
      type: 'custom',
      position: { x: 10, y: 20 },
      data: {
        label: 'Image',
        className: 'Image',
        widgetValues: { filename: 'scan.ibw' },
        runtimeValues: { layerIndex: 2 },
      },
    },
    {
      id: '2',
      selected: true,
      position: { x: 100, y: 200 },
      data: {
        label: 'Preview',
        className: 'Preview',
        widgetValues: { mode: 'auto' },
      },
    },
    {
      id: '3',
      selected: false,
      position: { x: 500, y: 600 },
      data: {
        label: 'Save',
        className: 'Save',
      },
    },
  ];

  const edges = [
    {
      id: 'e1-2',
      source: '1',
      sourceHandle: 'output::0::DATA_FIELD',
      target: '2',
      targetHandle: 'input::field::DATA_FIELD',
      style: { stroke: '#fff', strokeWidth: 2 },
    },
    {
      id: 'e2-3',
      source: '2',
      sourceHandle: 'output::0::IMAGE',
      target: '3',
      targetHandle: 'input::value::SAVE_VALUE',
    },
  ];

  const payload = buildNodeClipboardPayload(nodes, edges);

  assert.equal(payload.kind, NODE_CLIPBOARD_KIND);
  assert.equal(payload.nodes.length, 2);
  assert.deepEqual(payload.nodes.map((node) => node.id), ['1', '2']);
  assert.equal(payload.edges.length, 1);
  assert.deepEqual(payload.edges[0], {
    source: '1',
    sourceHandle: 'output::0::DATA_FIELD',
    target: '2',
    targetHandle: 'input::field::DATA_FIELD',
    style: { stroke: '#fff', strokeWidth: 2 },
  });

  const reparsed = parseNodeClipboardPayload(JSON.stringify(payload));
  assert.deepEqual(reparsed, payload);
});

test('instantiateNodeClipboardPayload remaps ids, offsets positions, and hydrates node shells', () => {
  const payload = {
    kind: NODE_CLIPBOARD_KIND,
    version: 1,
    nodes: [
      {
        id: '1',
        position: { x: 10, y: 20 },
        data: {
          label: 'Image',
          className: 'Image',
          widgetValues: { filename: 'scan.ibw', colormap: 'viridis' },
          runtimeValues: { layerIndex: 1 },
        },
      },
      {
        id: '2',
        position: { x: 100, y: 200 },
        data: {
          label: 'Preview',
          className: 'Preview',
          widgetValues: { colormap: 'gray' },
        },
      },
    ],
    edges: [
      {
        source: '1',
        sourceHandle: 'output::0::DATA_FIELD',
        target: '2',
        targetHandle: 'input::field::DATA_FIELD',
        style: { stroke: '#abc', strokeWidth: 2 },
      },
    ],
  };

  const defs = {
    Image: { output: ['DATA_FIELD'], output_name: ['field'] },
    Preview: { output: ['IMAGE'], output_name: ['preview'] },
  };

  const instantiated = instantiateNodeClipboardPayload(payload, defs, 12, { x: 32, y: 48 });

  assert.equal(instantiated.nextNodeId, 14);
  assert.deepEqual(instantiated.nodes.map((node) => node.id), ['12', '13']);
  assert.deepEqual(instantiated.nodes.map((node) => node.position), [
    { x: 42, y: 68 },
    { x: 132, y: 248 },
  ]);
  assert.equal(instantiated.nodes[0].selected, true);
  assert.deepEqual(instantiated.nodes[0].data.widgetValues, { filename: 'scan.ibw', colormap: 'viridis' });
  assert.deepEqual(instantiated.nodes[0].data.runtimeValues, { layerIndex: 1 });
  assert.equal(instantiated.nodes[0].data.previewImage, null);
  assert.deepEqual(instantiated.nodes[0].data.definition, defs.Image);

  assert.deepEqual(instantiated.edges, [
    {
      id: 'e12-13-0',
      source: '12',
      sourceHandle: 'output::0::DATA_FIELD',
      target: '13',
      targetHandle: 'input::field::DATA_FIELD',
      selected: false,
      style: { stroke: '#abc', strokeWidth: 2 },
    },
  ]);
});

test('buildNodeClipboardPayloadForIds can include upstream external edges for duplicated nodes', () => {
  const nodes = [
    { id: '1', position: { x: 0, y: 0 }, data: { className: 'Image' } },
    { id: '2', position: { x: 100, y: 0 }, data: { className: 'Preview' } },
    { id: '3', position: { x: 200, y: 0 }, data: { className: 'Save' } },
  ];

  const edges = [
    {
      source: '1',
      sourceHandle: 'output::0::DATA_FIELD',
      target: '2',
      targetHandle: 'input::field::DATA_FIELD',
    },
    {
      source: '2',
      sourceHandle: 'output::0::IMAGE',
      target: '3',
      targetHandle: 'input::value::SAVE_VALUE',
    },
  ];

  const payload = buildNodeClipboardPayloadForIds(nodes, edges, ['2'], {
    includeIncomingExternalEdges: true,
  });

  assert.equal(payload.nodes.length, 1);
  assert.deepEqual(payload.edges, [
    {
      source: '1',
      sourceHandle: 'output::0::DATA_FIELD',
      target: '2',
      targetHandle: 'input::field::DATA_FIELD',
    },
  ]);
});

test('instantiateNodeClipboardPayload can keep external upstream sources when duplicating nodes', () => {
  const payload = {
    kind: NODE_CLIPBOARD_KIND,
    version: 1,
    nodes: [
      {
        id: '2',
        position: { x: 100, y: 0 },
        data: {
          label: 'Preview',
          className: 'Preview',
          widgetValues: { colormap: 'viridis' },
        },
      },
    ],
    edges: [
      {
        source: '1',
        sourceHandle: 'output::0::DATA_FIELD',
        target: '2',
        targetHandle: 'input::field::DATA_FIELD',
      },
    ],
  };

  const defs = {
    Preview: { output: ['IMAGE'], output_name: ['preview'] },
  };

  const instantiated = instantiateNodeClipboardPayload(
    payload,
    defs,
    7,
    { x: 50, y: 25 },
    { keepExternalSources: true },
  );

  assert.deepEqual(instantiated.nodes.map((node) => node.id), ['7']);
  assert.deepEqual(instantiated.edges, [
    {
      id: 'e1-7-0',
      source: '1',
      sourceHandle: 'output::0::DATA_FIELD',
      target: '7',
      targetHandle: 'input::field::DATA_FIELD',
      selected: false,
    },
  ]);
});

test('clipboard payload deep-copies local widget and runtime fields', () => {
  const nodes = [
    {
      id: '9',
      selected: true,
      position: { x: 0, y: 0 },
      data: {
        label: 'Markup',
        className: 'Markup',
        widgetValues: {
          stroke_width: 3,
          markup_shapes: [
            { kind: 'line', points: [0.1, 0.2, 0.3, 0.4] },
          ],
        },
        runtimeValues: {
          camera: { azimuth: 15, polar: 60 },
        },
      },
    },
  ];

  const payload = buildNodeClipboardPayload(nodes, []);

  nodes[0].data.widgetValues.markup_shapes[0].points[0] = 0.9;
  nodes[0].data.runtimeValues.camera.azimuth = 90;

  assert.equal(payload.nodes[0].data.widgetValues.markup_shapes[0].points[0], 0.1);
  assert.equal(payload.nodes[0].data.runtimeValues.camera.azimuth, 15);
});

test('clipboard payload preserves wrapper class names for group shells', () => {
  const payload = buildNodeClipboardPayloadForIds(
    [
      {
        id: '50',
        type: 'custom',
        className: 'group-shell',
        position: { x: 0, y: 0 },
        data: {
          label: 'group',
          className: 'Group',
          widgetValues: {},
        },
      },
    ],
    [],
    ['50'],
  );

  const instantiated = instantiateNodeClipboardPayload(payload, {}, 80);

  assert.equal(payload.nodes[0].className, 'group-shell');
  assert.equal(instantiated.nodes[0].className, 'group-shell');
});

test('instantiateNodeClipboardPayload remaps collapsed group proxy metadata to cloned child ids', () => {
  const payload = {
    kind: NODE_CLIPBOARD_KIND,
    version: 1,
    nodes: [
      {
        id: '10',
        type: 'custom',
        className: 'group-shell',
        position: { x: 40, y: 50 },
        style: { width: 320, height: 220 },
        data: {
          label: 'group',
          className: 'Group',
          widgetValues: {},
          extraData: {
            collapsed: true,
            childCount: 1,
            proxyInputs: [
              {
                key: '2::input::field::DATA_FIELD',
                type: 'DATA_FIELD',
                label: 'field',
                handleId: 'group-proxy::in::2::DATA_FIELD::input%3A%3Afield%3A%3ADATA_FIELD',
              },
            ],
          },
        },
      },
      {
        id: '2',
        type: 'custom',
        parentId: '10',
        extent: 'parent',
        hidden: true,
        position: { x: 24, y: 48 },
        data: {
          label: 'preview',
          className: 'Preview',
          widgetValues: {},
        },
      },
    ],
    edges: [
      {
        source: '1',
        sourceHandle: 'output::0::DATA_FIELD',
        target: '10',
        targetHandle: 'group-proxy::in::2::DATA_FIELD::input%3A%3Afield%3A%3ADATA_FIELD',
        data: {
          groupProxyOwner: '10',
          groupProxyOriginal: {
            target: '2',
            targetHandle: 'input::field::DATA_FIELD',
          },
        },
      },
    ],
  };

  const instantiated = instantiateNodeClipboardPayload(
    payload,
    {},
    20,
    { x: 0, y: 0 },
    { keepExternalSources: true },
  );

  assert.equal(instantiated.nextNodeId, 22);
  assert.deepEqual(instantiated.nodes.map((node) => node.id), ['20', '21']);
  assert.deepEqual(instantiated.edges, [
    {
      id: 'e1-20-0',
      source: '1',
      sourceHandle: 'output::0::DATA_FIELD',
      target: '20',
      targetHandle: 'group-proxy::in::21::DATA_FIELD::input%3A%3Afield%3A%3ADATA_FIELD',
      selected: false,
      data: {
        groupProxyOwner: '20',
        groupProxyOriginal: {
          target: '21',
          targetHandle: 'input::field::DATA_FIELD',
        },
      },
    },
  ]);

  assert.deepEqual(instantiated.nodes[0].data.proxyInputs, [
    {
      key: '21::input::field::DATA_FIELD',
      type: 'DATA_FIELD',
      label: 'field',
      handleId: 'group-proxy::in::21::DATA_FIELD::input%3A%3Afield%3A%3ADATA_FIELD',
    },
  ]);
});
