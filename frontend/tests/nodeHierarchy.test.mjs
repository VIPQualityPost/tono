import test from 'node:test';
import assert from 'node:assert/strict';

import { sortNodesForParentOrder } from '../src/nodeHierarchy.js';
import { hydrateWorkflowState } from '../src/workflowHydration.js';
import { instantiateNodeClipboardPayload, NODE_CLIPBOARD_KIND } from '../src/nodeClipboard.js';

test('sortNodesForParentOrder places parents before descendants', () => {
  const nodes = [
    { id: '2', parentId: '1', position: { x: 80, y: 60 }, data: { className: 'Preview' } },
    { id: '3', position: { x: 300, y: 20 }, data: { className: 'Image' } },
    { id: '1', className: 'group-shell', position: { x: 0, y: 0 }, data: { className: 'Group' } },
    { id: '4', parentId: '2', position: { x: 30, y: 24 }, data: { className: 'Save' } },
  ];

  const ordered = sortNodesForParentOrder(nodes);

  assert.deepEqual(ordered.map((node) => node.id), ['1', '2', '3', '4']);
});

test('hydrateWorkflowState reorders group parents ahead of children', () => {
  const saved = {
    nodes: [
      {
        id: '11',
        type: 'custom',
        position: { x: 48, y: 72 },
        parentId: '10',
        extent: 'parent',
        data: {
          label: 'preview',
          className: 'Preview',
          widgetValues: {},
        },
      },
      {
        id: '10',
        type: 'custom',
        className: 'group-shell',
        position: { x: 12, y: 24 },
        style: { width: 320, height: 220 },
        data: {
          label: 'group',
          className: 'Group',
          widgetValues: {},
        },
      },
    ],
    edges: [],
  };

  const hydrated = hydrateWorkflowState(saved, {});

  assert.deepEqual(hydrated.nodes.map((node) => node.id), ['10', '11']);
  assert.equal(hydrated.nodes[1].parentId, '10');
});

test('instantiateNodeClipboardPayload remaps parent ids before sorting grouped nodes', () => {
  const payload = {
    kind: NODE_CLIPBOARD_KIND,
    version: 1,
    nodes: [
      {
        id: 'child',
        type: 'custom',
        position: { x: 48, y: 72 },
        parentId: 'group',
        extent: 'parent',
        data: {
          label: 'preview',
          className: 'Preview',
          widgetValues: {},
        },
      },
      {
        id: 'group',
        type: 'custom',
        className: 'group-shell',
        position: { x: 12, y: 24 },
        style: { width: 320, height: 220 },
        data: {
          label: 'group',
          className: 'Group',
          widgetValues: {},
        },
      },
    ],
    edges: [],
  };

  const instantiated = instantiateNodeClipboardPayload(payload, {}, 20);

  assert.deepEqual(instantiated.nodes.map((node) => node.id), ['21', '20']);
  assert.equal(instantiated.nodes[1].parentId, '21');
  assert.equal(instantiated.nextNodeId, 22);
});
