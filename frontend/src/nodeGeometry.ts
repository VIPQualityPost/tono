import {
  getHandleType,
  getInputName,
  getOutputSlot,
  encodeProxyHandleRef,
  parseGroupProxyHandle,
} from './connectionUtils';

export const GROUP_PADDING_X = 24;
export const GROUP_PADDING_Y = 24;
export const GROUP_HEADER_HEIGHT = 36;
export const GROUP_WORKSPACE_INSET = 12;
export const GROUP_MIN_WIDTH = 260;
export const GROUP_MIN_HEIGHT = 180;

export function getNodeDimension(node: any, axis: string): number {
  if (axis === 'width') return node.measured?.width || node.style?.width || node.width || 200;
  return node.measured?.height || node.style?.height || node.height || 120;
}

export function applyNodeSize(node: any, width: any, height: any) {
  const nextWidth = Math.round(Number(width) || 0);
  const nextHeight = Math.round(Number(height) || 0);
  return {
    ...node,
    width: nextWidth,
    height: nextHeight,
    style: { ...(node.style || {}), width: nextWidth, height: nextHeight },
  };
}

export function getNodeAbsolutePosition(node: any, nodeMap: Map<string, any>): { x: number; y: number } {
  if (node?.positionAbsolute) {
    return {
      x: Number(node.positionAbsolute.x) || 0,
      y: Number(node.positionAbsolute.y) || 0,
    };
  }
  const local = {
    x: Number(node?.position?.x) || 0,
    y: Number(node?.position?.y) || 0,
  };
  if (!node?.parentId) return local;
  const parent = nodeMap.get(String(node.parentId));
  if (!parent) return local;
  const parentPos = getNodeAbsolutePosition(parent, nodeMap);
  return { x: parentPos.x + local.x, y: parentPos.y + local.y };
}

export function collectGroupDescendantIds(nodes: any[], groupId: any) {
  const allNodes = Array.isArray(nodes) ? nodes : [];
  const result = new Set<string>();
  let changed = true;
  while (changed) {
    changed = false;
    for (const node of allNodes) {
      const parentId = node?.parentId ? String(node.parentId) : null;
      const nodeId = String(node?.id);
      if (!parentId) continue;
      if ((parentId === String(groupId) || result.has(parentId)) && !result.has(nodeId)) {
        result.add(nodeId);
        changed = true;
      }
    }
  }
  return result;
}

export function getGroupMembers(nodes: any[], groupId: any) {
  const descendants = collectGroupDescendantIds(nodes, groupId);
  return Array.from(descendants);
}

export function getGroupDisplayBounds(nodes: any[], selectedIds: any[]) {
  const nodeMap = new Map<string, any>((nodes || []).map((node: any) => [String(node.id), node]));
  let minX = Infinity;
  let minY = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;

  for (const id of selectedIds) {
    const node = nodeMap.get(String(id));
    if (!node) continue;
    const pos = getNodeAbsolutePosition(node, nodeMap);
    const width = Number(getNodeDimension(node, 'width')) || 200;
    const height = Number(getNodeDimension(node, 'height')) || 120;
    minX = Math.min(minX, pos.x);
    minY = Math.min(minY, pos.y);
    maxX = Math.max(maxX, pos.x + width);
    maxY = Math.max(maxY, pos.y + height);
  }

  if (!Number.isFinite(minX) || !Number.isFinite(minY) || !Number.isFinite(maxX) || !Number.isFinite(maxY)) {
    return null;
  }

  return { minX, minY, maxX, maxY };
}

export function getGroupWorkspaceBounds(groupNode: any, nodeMap: Map<string, any>) {
  const pos = getNodeAbsolutePosition(groupNode, nodeMap);
  const width = Number(getNodeDimension(groupNode, 'width')) || 200;
  const height = Number(getNodeDimension(groupNode, 'height')) || 120;
  return {
    left: pos.x + GROUP_WORKSPACE_INSET,
    top: pos.y + GROUP_HEADER_HEIGHT + GROUP_WORKSPACE_INSET,
    right: pos.x + width - GROUP_WORKSPACE_INSET,
    bottom: pos.y + height - GROUP_WORKSPACE_INSET,
  };
}

export function getNodeCenter(node: any, nodeMap: Map<string, any>) {
  const pos = getNodeAbsolutePosition(node, nodeMap);
  const width = Number(getNodeDimension(node, 'width')) || 200;
  const height = Number(getNodeDimension(node, 'height')) || 120;
  return {
    x: pos.x + width / 2,
    y: pos.y + height / 2,
  };
}

export function getNodeRect(node: any, nodeMap: Map<string, any>) {
  const pos = getNodeAbsolutePosition(node, nodeMap);
  const width = Number(getNodeDimension(node, 'width')) || 200;
  const height = Number(getNodeDimension(node, 'height')) || 120;
  return {
    left: pos.x,
    top: pos.y,
    right: pos.x + width,
    bottom: pos.y + height,
  };
}

export function getAbsoluteRectForNodePosition(node: any, absolutePosition: { x: number; y: number }) {
  const width = Number(getNodeDimension(node, 'width')) || 200;
  const height = Number(getNodeDimension(node, 'height')) || 120;
  return {
    left: absolutePosition.x,
    top: absolutePosition.y,
    right: absolutePosition.x + width,
    bottom: absolutePosition.y + height,
  };
}

export function rectContainsPoint(rect: { left: number; right: number; top: number; bottom: number }, point: { x: number; y: number }) {
  return point.x >= rect.left
    && point.x <= rect.right
    && point.y >= rect.top
    && point.y <= rect.bottom;
}

export function rectContainsRect(outerRect: { left: number; right: number; top: number; bottom: number }, innerRect: { left: number; right: number; top: number; bottom: number }) {
  return innerRect.left >= outerRect.left
    && innerRect.top >= outerRect.top
    && innerRect.right <= outerRect.right
    && innerRect.bottom <= outerRect.bottom;
}

export function findExpandedGroupDropTarget(nodes: any[], draggedNodeIds: any[], anchorNodeId: any, anchorPoint: { x: number; y: number } | null = null) {
  const nodeMap = new Map<string, any>((nodes || []).map((node: any) => [String(node.id), node]));
  const anchorNode = nodeMap.get(String(anchorNodeId));
  if (!anchorNode) return null;

  const draggedIdSet = new Set((draggedNodeIds || []).map((id: any) => String(id)));
  const anchorCenter = anchorPoint && Number.isFinite(anchorPoint.x) && Number.isFinite(anchorPoint.y)
    ? anchorPoint
    : getNodeCenter(anchorNode, nodeMap);

  return (nodes || [])
    .filter((node: any) => (
      node?.data?.className === 'Group'
      && !node?.data?.collapsed
      && !draggedIdSet.has(String(node.id))
    ))
    .map((node: any) => {
      const rect = getGroupWorkspaceBounds(node, nodeMap);
      return {
        node,
        rect,
        area: Math.max(1, rect.right - rect.left) * Math.max(1, rect.bottom - rect.top),
      };
    })
    .filter(({ rect }: { rect: any }) => rectContainsPoint(rect, anchorCenter))
    .sort((a: any, b: any) => a.area - b.area)[0]?.node || null;
}

export function getInputLabelForNode(node: any, inputName: string) {
  const inputs = {
    ...(node?.data?.definition?.input?.required || {}),
    ...(node?.data?.definition?.input?.optional || {}),
  };
  const spec = inputs[inputName];
  if (!spec) return inputName;
  const [, opts] = Array.isArray(spec) ? spec : [spec, {}];
  return opts?.label || inputName;
}

export function getOutputLabelForNode(node: any, slot: number, handleId: string): string {
  const outputNames = node?.data?.definition?.output_name || [];
  const outputTypes = node?.data?.definition?.output || [];
  if (Number.isInteger(slot) && outputNames[slot]) return outputNames[slot];
  const proxy = parseGroupProxyHandle(handleId);
  return proxy?.realHandle ? getOutputLabelForNode(node, getOutputSlot(proxy.realHandle), proxy.realHandle) : outputTypes[slot] || 'output';
}

export function buildGroupProxyData(groupId: string, nodes: any[], edges: any[]) {
  const nodeMap = new Map<string, any>((nodes || []).map((node: any) => [String(node.id), node]));
  const memberIds = new Set(getGroupMembers(nodes, groupId));
  const proxyInputs: { key: string; type: string; label: string; handleId: string }[] = [];
  const proxyOutputs: { key: string; type: string; label: string; handleId: string }[] = [];
  const seenInputs = new Set();
  const seenOutputs = new Set();

  for (const edge of edges || []) {
    const original = (edge?.data?.groupProxyOriginal || {}) as Record<string, any>;
    const sourceId = String(original.source || edge.source);
    const targetId = String(original.target || edge.target);
    const sourceHandle = original.sourceHandle || edge.sourceHandle;
    const targetHandle = original.targetHandle || edge.targetHandle;
    const sourceInside = memberIds.has(sourceId);
    const targetInside = memberIds.has(targetId);

    if (!sourceInside && targetInside) {
      const key = `${targetId}::${targetHandle}`;
      if (seenInputs.has(key)) continue;
      seenInputs.add(key);
      proxyInputs.push({
        key,
        type: getHandleType(targetHandle),
        label: getInputLabelForNode(nodeMap.get(targetId), getInputName(targetHandle)),
        handleId: `group-proxy::in::${targetId}::${getHandleType(targetHandle)}::${encodeProxyHandleRef(targetHandle)}`,
      });
    }

    if (sourceInside && !targetInside) {
      const key = `${sourceId}::${sourceHandle}`;
      if (seenOutputs.has(key)) continue;
      seenOutputs.add(key);
      proxyOutputs.push({
        key,
        type: getHandleType(sourceHandle),
        label: getOutputLabelForNode(nodeMap.get(sourceId), getOutputSlot(sourceHandle), sourceHandle),
        handleId: `group-proxy::out::${sourceId}::${getHandleType(sourceHandle)}::${encodeProxyHandleRef(sourceHandle)}`,
      });
    }
  }

  return { proxyInputs, proxyOutputs, childCount: memberIds.size };
}

export function sameStringArray(a: any[] = [], b: any[] = []) {
  if (a === b) return true;
  if (!Array.isArray(a) || !Array.isArray(b) || a.length !== b.length) return false;
  return a.every((item, index) => item === b[index]);
}

export function getRenderedNodeBounds(nodes: any[]) {
  let minX = Infinity;
  let minY = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;
  let found = false;

  for (const node of nodes) {
    const selectorId = typeof CSS !== 'undefined' && typeof CSS.escape === 'function'
      ? CSS.escape(String(node.id))
      : String(node.id);
    const el = document.querySelector(`.react-flow__node[data-id="${selectorId}"]`) as HTMLElement | null;
    const width = el?.offsetWidth || node.measured?.width || node.width || 0;
    const height = el?.offsetHeight || node.measured?.height || node.height || 0;
    const x = node.positionAbsolute?.x ?? node.position?.x ?? 0;
    const y = node.positionAbsolute?.y ?? node.position?.y ?? 0;

    if (!Number.isFinite(width) || !Number.isFinite(height) || width <= 0 || height <= 0) {
      continue;
    }

    minX = Math.min(minX, x);
    minY = Math.min(minY, y);
    maxX = Math.max(maxX, x + width);
    maxY = Math.max(maxY, y + height);
    found = true;
  }

  if (!found) {
    return null;
  }

  return {
    x: minX,
    y: minY,
    width: Math.max(1, maxX - minX),
    height: Math.max(1, maxY - minY),
  };
}
