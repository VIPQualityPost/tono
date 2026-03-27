export const NODE_CLIPBOARD_KIND = 'argonode/node-selection';
export const NODE_CLIPBOARD_MIME = 'application/x-argonode-node-selection';

function cloneValue(value) {
  if (value == null) return value;
  if (typeof structuredClone === 'function') {
    try {
      return structuredClone(value);
    } catch {
      // Fall through to JSON clone for simple plain data.
    }
  }
  return JSON.parse(JSON.stringify(value));
}

function clonePlainObject(value) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return {};
  return cloneValue(value) || {};
}

export function buildNodeClipboardPayload(nodes, edges) {
  const selectedNodes = Array.isArray(nodes) ? nodes.filter((node) => node?.selected) : [];
  if (selectedNodes.length === 0) return null;

  const selectedIds = new Set(selectedNodes.map((node) => String(node.id)));
  const internalEdges = Array.isArray(edges)
    ? edges.filter((edge) => selectedIds.has(String(edge.source)) && selectedIds.has(String(edge.target)))
    : [];

  return {
    kind: NODE_CLIPBOARD_KIND,
    version: 1,
    nodes: selectedNodes.map((node) => ({
      id: String(node.id),
      type: node.type || 'custom',
      position: {
        x: Number(node.position?.x) || 0,
        y: Number(node.position?.y) || 0,
      },
      dragHandle: node.dragHandle || '.drag-handle',
      data: {
        label: node.data?.label || node.data?.className || 'Node',
        className: node.data?.className || '',
        widgetValues: clonePlainObject(node.data?.widgetValues),
        runtimeValues: clonePlainObject(node.data?.runtimeValues),
      },
    })),
    edges: internalEdges.map((edge) => ({
      source: String(edge.source),
      sourceHandle: edge.sourceHandle,
      target: String(edge.target),
      targetHandle: edge.targetHandle,
      ...(edge.style ? { style: { ...edge.style } } : {}),
    })),
  };
}

export function parseNodeClipboardPayload(text) {
  if (typeof text !== 'string' || !text.trim()) return null;

  try {
    const parsed = JSON.parse(text);
    if (parsed?.kind !== NODE_CLIPBOARD_KIND) return null;
    if (!Array.isArray(parsed.nodes) || !Array.isArray(parsed.edges)) return null;
    return parsed;
  } catch {
    return null;
  }
}

export function instantiateNodeClipboardPayload(payload, defs = {}, nextNodeId = 1, offset = { x: 40, y: 40 }) {
  if (!payload || !Array.isArray(payload.nodes) || payload.nodes.length === 0) {
    return { nodes: [], edges: [], nextNodeId };
  }

  const idMap = new Map();
  let currentId = Number(nextNodeId) || 1;

  const nodes = payload.nodes.map((node) => {
    const newId = String(currentId++);
    idMap.set(String(node.id), newId);
    const className = node.data?.className || '';
    const definition = className ? defs[className] || null : null;

    return {
      id: newId,
      type: node.type || 'custom',
      position: {
        x: (Number(node.position?.x) || 0) + (Number(offset?.x) || 0),
        y: (Number(node.position?.y) || 0) + (Number(offset?.y) || 0),
      },
      dragHandle: node.dragHandle || '.drag-handle',
      selected: true,
      data: {
        label: node.data?.label || className || 'Node',
        className,
        widgetValues: clonePlainObject(node.data?.widgetValues),
        runtimeValues: clonePlainObject(node.data?.runtimeValues),
        definition,
        previewImage: null,
        tableRows: null,
        meshData: null,
        overlay: null,
        scalarValue: null,
        processingTimeMs: null,
        warning: null,
      },
    };
  });

  const edges = payload.edges
    .filter((edge) => idMap.has(String(edge.source)) && idMap.has(String(edge.target)))
    .map((edge, index) => ({
      id: `e${idMap.get(String(edge.source))}-${idMap.get(String(edge.target))}-${index}`,
      source: idMap.get(String(edge.source)),
      sourceHandle: edge.sourceHandle,
      target: idMap.get(String(edge.target)),
      targetHandle: edge.targetHandle,
      selected: false,
      ...(edge.style ? { style: { ...edge.style } } : {}),
    }));

  return {
    nodes,
    edges,
    nextNodeId: currentId,
  };
}
