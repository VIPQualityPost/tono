import { sortNodesForParentOrder } from './nodeHierarchy.ts';
import type { TonoNode, TonoEdge, NodeData, NodeDefsRegistry } from './types.ts';

export const NODE_CLIPBOARD_KIND = 'tono/node-selection';
export const NODE_CLIPBOARD_MIME = 'application/x-tono-node-selection';

interface ClipboardNodeData {
  label: string;
  className: string;
  widgetValues: Record<string, unknown>;
  runtimeValues: Record<string, unknown>;
  extraData: Record<string, unknown>;
}

interface ClipboardNode {
  id: string;
  type: string;
  position: { x: number; y: number };
  width?: number;
  height?: number;
  className?: string;
  parentId?: string;
  extent?: unknown;
  hidden?: boolean;
  style?: unknown;
  dragHandle?: string;
  data: ClipboardNodeData;
  [key: string]: unknown;
}

interface ClipboardEdge {
  source: string;
  sourceHandle?: string | null;
  target: string;
  targetHandle?: string | null;
  style?: unknown;
  hidden?: boolean;
  data?: unknown;
  [key: string]: unknown;
}

interface ClipboardPayload {
  kind: string;
  version: number;
  nodes: ClipboardNode[];
  edges: ClipboardEdge[];
}

function cloneValue<T>(value: T): T {
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

function clonePlainObject(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return {};
  return cloneValue(value as Record<string, unknown>) || {};
}

function encodeProxyHandleRef(handleId: string): string {
  return encodeURIComponent(String(handleId || ''));
}

function decodeProxyHandleRef(encoded: string): string {
  try {
    return decodeURIComponent(String(encoded || ''));
  } catch {
    return String(encoded || '');
  }
}

function parseGroupProxyHandle(handleId: string) {
  const text = String(handleId || '');
  if (!text.startsWith('group-proxy::')) return null;
  const parts = text.split('::');
  if (parts.length < 5) return null;
  return {
    direction: parts[1],
    nodeId: parts[2],
    type: parts[3],
    realHandle: decodeProxyHandleRef(parts.slice(4).join('::')),
  };
}

function hasOwn(obj: Record<string, unknown>, key: string): boolean {
  return Object.prototype.hasOwnProperty.call(obj, key);
}

function remapNodeId(value: string | null | undefined, idMap: Map<string, string>): string | null | undefined {
  if (value == null) return value;
  return idMap.get(String(value)) || String(value);
}

function remapGroupProxyHandle(handleId: string | null | undefined, idMap: Map<string, string>): string | null | undefined {
  if (!handleId) return handleId;
  const proxy = parseGroupProxyHandle(handleId);
  if (!proxy) return handleId;
  return `group-proxy::${proxy.direction}::${remapNodeId(proxy.nodeId, idMap)}::${proxy.type}::${encodeProxyHandleRef(proxy.realHandle)}`;
}

function remapGroupProxyDescriptors(items: unknown, idMap: Map<string, string>): unknown {
  if (!Array.isArray(items)) return items;
  return items.map((item: Record<string, unknown>) => {
    if (!item || typeof item !== 'object') return item;
    const nextItem = { ...item };
    if (typeof nextItem.key === 'string') {
      const separator = (nextItem.key as string).indexOf('::');
      if (separator !== -1) {
        const handleId = (nextItem.key as string).slice(separator + 2);
        nextItem.key = `${remapNodeId((nextItem.key as string).slice(0, separator), idMap)}::${remapGroupProxyHandle(handleId, idMap)}`;
      }
    }
    if (typeof nextItem.handleId === 'string') {
      nextItem.handleId = remapGroupProxyHandle(nextItem.handleId as string, idMap);
    }
    return nextItem;
  });
}

function remapClipboardExtraData(extraData: unknown, idMap: Map<string, string>): Record<string, unknown> {
  const nextExtraData = clonePlainObject(extraData);
  if (Array.isArray(nextExtraData.proxyInputs)) {
    nextExtraData.proxyInputs = remapGroupProxyDescriptors(nextExtraData.proxyInputs, idMap);
  }
  if (Array.isArray(nextExtraData.proxyOutputs)) {
    nextExtraData.proxyOutputs = remapGroupProxyDescriptors(nextExtraData.proxyOutputs, idMap);
  }
  return nextExtraData;
}

function remapClipboardEdgeData(data: unknown, idMap: Map<string, string>): unknown {
  if (!data || typeof data !== 'object' || Array.isArray(data)) return cloneValue(data);

  const nextData = cloneValue(data) as Record<string, unknown>;
  if (hasOwn(nextData, 'groupInternalHiddenBy')) {
    nextData.groupInternalHiddenBy = remapNodeId(nextData.groupInternalHiddenBy as string, idMap);
  }
  if (hasOwn(nextData, 'groupProxyOwner')) {
    nextData.groupProxyOwner = remapNodeId(nextData.groupProxyOwner as string, idMap);
  }

  const original = nextData.groupProxyOriginal;
  if (original && typeof original === 'object' && !Array.isArray(original)) {
    const orig = original as Record<string, unknown>;
    if (hasOwn(orig, 'source')) orig.source = remapNodeId(orig.source as string, idMap);
    if (hasOwn(orig, 'target')) orig.target = remapNodeId(orig.target as string, idMap);
    if (hasOwn(orig, 'sourceHandle')) {
      orig.sourceHandle = remapGroupProxyHandle(orig.sourceHandle as string, idMap);
    }
    if (hasOwn(orig, 'targetHandle')) {
      orig.targetHandle = remapGroupProxyHandle(orig.targetHandle as string, idMap);
    }
  }

  return nextData;
}

function collectSelectedNodeIds(nodes: TonoNode[], nodeIds: string[]): Set<string> {
  const selectedIdSet = new Set((Array.isArray(nodeIds) ? nodeIds : []).map((id: string) => String(id)));
  if (selectedIdSet.size === 0) return selectedIdSet;

  let changed = true;
  while (changed) {
    changed = false;
    for (const node of Array.isArray(nodes) ? nodes : []) {
      const parentId = node?.parentId ? String(node.parentId) : null;
      const nodeId = String(node?.id);
      if (parentId && selectedIdSet.has(parentId) && !selectedIdSet.has(nodeId)) {
        selectedIdSet.add(nodeId);
        changed = true;
      }
    }
  }
  return selectedIdSet;
}

function extractExtraData(data: NodeData): Record<string, unknown> {
  const source = data || {};
  return Object.fromEntries(
    Object.entries(source).filter(([key]) => ![
      'label',
      'className',
      'widgetValues',
      'runtimeValues',
      'definition',
      'previewImage',
      'tableRows',
      'meshData',
      'overlay',
      'scalarValue',
      'processingTimeMs',
      'warning',
    ].includes(key)),
  );
}

export function buildNodeClipboardPayloadForIds(
  nodes: TonoNode[],
  edges: TonoEdge[],
  nodeIds: string[],
  { includeIncomingExternalEdges = false } = {},
): ClipboardPayload | null {
  const selectedIdSet = collectSelectedNodeIds(nodes, nodeIds);
  const selectedNodes = Array.isArray(nodes)
    ? nodes.filter((node) => selectedIdSet.has(String(node.id)))
    : [];
  if (selectedNodes.length === 0) return null;

  const capturedEdges = Array.isArray(edges)
    ? edges.filter((edge) => (
      selectedIdSet.has(String(edge.target))
      && (
        selectedIdSet.has(String(edge.source))
        || (includeIncomingExternalEdges && !selectedIdSet.has(String(edge.source)))
      )
    ))
    : [];

  const snapDim = (v: number | undefined) => {
    const n = Math.round(Number(v));
    return Number.isFinite(n) && n > 0 ? n : undefined;
  };

  return {
    kind: NODE_CLIPBOARD_KIND,
    version: 1,
    nodes: selectedNodes.map((node) => {
      const width = snapDim(node.measured?.width ?? node.width);
      const height = snapDim(node.measured?.height ?? node.height);
      return {
      id: String(node.id),
      type: node.type || 'custom',
      position: {
        x: Number(node.position?.x) || 0,
        y: Number(node.position?.y) || 0,
      },
      ...(width != null ? { width } : {}),
      ...(height != null ? { height } : {}),
      ...(node.className ? { className: node.className } : {}),
      ...(node.parentId ? { parentId: String(node.parentId) } : {}),
      ...(node.extent ? { extent: node.extent } : {}),
      ...(node.hidden ? { hidden: true } : {}),
      ...(node.style ? { style: cloneValue(node.style) } : {}),
      dragHandle: node.dragHandle || '.drag-handle',
      data: {
        label: node.data?.label || node.data?.className || 'Node',
        className: node.data?.className || '',
        widgetValues: clonePlainObject(node.data?.widgetValues),
        runtimeValues: clonePlainObject(node.data?.runtimeValues),
        extraData: clonePlainObject(extractExtraData(node.data)),
      },
      };
    }),
    edges: capturedEdges.map((edge) => ({
      source: String(edge.source),
      sourceHandle: edge.sourceHandle,
      target: String(edge.target),
      targetHandle: edge.targetHandle,
      ...(edge.style ? { style: { ...edge.style } } : {}),
      ...(edge.hidden ? { hidden: true } : {}),
      ...(edge.data ? { data: cloneValue(edge.data) } : {}),
    })),
  };
}

export function buildNodeClipboardPayload(nodes: TonoNode[], edges: TonoEdge[]) {
  const selectedNodes = Array.isArray(nodes)
    ? nodes.filter((node) => node?.selected)
    : [];
  const selectedIds = selectedNodes.map((node) => String(node.id));
  const includeIncomingExternalEdges = selectedNodes.some((node) => node?.data?.className === 'Group');
  return buildNodeClipboardPayloadForIds(nodes, edges, selectedIds, { includeIncomingExternalEdges });
}

export function parseNodeClipboardPayload(text: string): ClipboardPayload | null {
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

export function instantiateNodeClipboardPayload(
  payload: ClipboardPayload | null,
  defs: NodeDefsRegistry = {},
  nextNodeId: number = 1,
  offset: { x: number; y: number } = { x: 40, y: 40 },
  { keepExternalSources = false } = {},
) {
  if (!payload || !Array.isArray(payload.nodes) || payload.nodes.length === 0) {
    return { nodes: [], edges: [], nextNodeId };
  }

  const idMap = new Map();
  let currentId = Number(nextNodeId) || 1;

  payload.nodes.forEach((node: ClipboardNode) => {
    idMap.set(String(node.id), String(currentId++));
  });

  const nodes = sortNodesForParentOrder(payload.nodes.map((node: ClipboardNode) => {
    const newId = idMap.get(String(node.id));
    const className = node.data?.className || '';
    const definition = className ? defs[className] || null : null;
    const extraData = remapClipboardExtraData(node.data?.extraData, idMap);

    return {
      id: newId,
      type: node.type || 'custom',
      className: node.className,
      position: {
        x: (Number(node.position?.x) || 0) + (Number(offset?.x) || 0),
        y: (Number(node.position?.y) || 0) + (Number(offset?.y) || 0),
      },
      ...(node.width != null ? { width: node.width } : {}),
      ...(node.height != null ? { height: node.height } : {}),
      ...(node.parentId ? { parentId: idMap.get(String(node.parentId)) || String(node.parentId) } : {}),
      ...(node.extent ? { extent: node.extent } : {}),
      ...(node.hidden ? { hidden: true } : {}),
      ...(node.style ? { style: cloneValue(node.style) } : {}),
      dragHandle: node.dragHandle || '.drag-handle',
      selected: true,
      data: {
        label: node.data?.label || className || 'Node',
        className,
        widgetValues: clonePlainObject(node.data?.widgetValues),
        runtimeValues: clonePlainObject(node.data?.runtimeValues),
        ...extraData,
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
  }));

  const edges = payload.edges
    .filter((edge: ClipboardEdge) => (
      idMap.has(String(edge.target))
      && (idMap.has(String(edge.source)) || keepExternalSources)
    ))
    .map((edge: ClipboardEdge, index: number) => {
      const source = idMap.get(String(edge.source)) || String(edge.source);
      const target = idMap.get(String(edge.target));
      return {
        id: `e${source}-${target}-${index}`,
        source,
        sourceHandle: remapGroupProxyHandle(edge.sourceHandle, idMap),
        target,
        targetHandle: remapGroupProxyHandle(edge.targetHandle, idMap),
        selected: false,
        ...(edge.style ? { style: { ...edge.style } } : {}),
        ...(edge.hidden ? { hidden: true } : {}),
        ...(edge.data ? { data: remapClipboardEdgeData(edge.data, idMap) } : {}),
      };
    });

  return {
    nodes,
    edges,
    nextNodeId: currentId,
  };
}
