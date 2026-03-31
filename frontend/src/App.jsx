import React, {
  useState, useCallback, useEffect, useRef, useMemo,
} from 'react';
import {
  ReactFlow, Background, Controls, MiniMap,
  useNodesState, useEdgesState, addEdge, useReactFlow,
  ReactFlowProvider, getViewportForBounds, PanOnScrollMode, SelectionMode,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

import CustomNode, { NodeContext } from './CustomNode';
import * as api from './api';
import { pickNativeDirectorySelection, pickNativeFileSelection } from './nativePicker';
import { toBlob } from 'html-to-image';
import { embedWorkflow, extractWorkflow } from './pngMetadata';
import { captureViewportBlob as captureWorkflowViewportBlob } from './workflowCapture';
import { hydrateWorkflowState } from './workflowHydration';
import { serializeWorkflowState } from './workflowSerialization';
import { sortNodesForParentOrder } from './nodeHierarchy.js';
import {
  buildNodeClipboardPayload,
  buildNodeClipboardPayloadForIds,
  instantiateNodeClipboardPayload,
  NODE_CLIPBOARD_MIME,
  parseNodeClipboardPayload,
} from './nodeClipboard';
import { loadDefaultWorkflowAsset } from './defaultWorkflow';
import {
  serializeExecutionGraph,
  getAutoRunnableNodes,
  hasBlockingAutoRunInput,
} from './executionGraph';
import {
  beginTrackedNodeRequest,
  isTrackedNodeRequestCurrent,
  resolveLoadNodeChannelPath,
} from './loadNodeOutputs.js';
import { buildDefaultWidgetValues } from './nodeWidgetDefaults.js';
import {
  getHandleType,
  getInputName,
  getOutputSlot,
  encodeProxyHandleRef,
  parseGroupProxyHandle,
  getConnectionHandleType,
  getResolvedHandleRef,
  getNodeInputSpecForHandle,
  outputTypeCanConnectToTarget,
  resolveOutputTypeForTarget,
  checkConnectionValid,
} from './connectionUtils.js';

import {
  getSpecTypeAndOptions,
  socketSpecAcceptsType,
  TYPE_COLORS,
  CAT_COLORS,
  CANVAS_COLORS,
} from './constants';

const NODE_TYPES = { custom: CustomNode };

const GROUP_PADDING_X = 24;
const GROUP_PADDING_Y = 24;
const GROUP_HEADER_HEIGHT = 36;
const GROUP_WORKSPACE_INSET = 12;
const GROUP_MIN_WIDTH = 260;
const GROUP_MIN_HEIGHT = 180;
const CANVAS_MIN_ZOOM = 0.2;
const CANVAS_MAX_ZOOM = 4;
const CANVAS_RIGHT_DRAG_ZOOM_SENSITIVITY = 0.0065;
const CANVAS_RIGHT_DRAG_ZOOM_THRESHOLD = 5;

function getNodeDimension(node, axis) {
  if (axis === 'width') return node.measured?.width || node.style?.width || node.width || 200;
  return node.measured?.height || node.style?.height || node.height || 120;
}

function applyNodeSize(node, width, height) {
  const nextWidth = Math.round(Number(width) || 0);
  const nextHeight = Math.round(Number(height) || 0);
  return {
    ...node,
    width: nextWidth,
    height: nextHeight,
    style: { ...(node.style || {}), width: nextWidth, height: nextHeight },
  };
}

function getNodeAbsolutePosition(node, nodeMap) {
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

function collectGroupDescendantIds(nodes, groupId) {
  const allNodes = Array.isArray(nodes) ? nodes : [];
  const result = new Set();
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

function getGroupMembers(nodes, groupId) {
  const descendants = collectGroupDescendantIds(nodes, groupId);
  return Array.from(descendants);
}

function getGroupDisplayBounds(nodes, selectedIds) {
  const nodeMap = new Map((nodes || []).map((node) => [String(node.id), node]));
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

function getGroupWorkspaceBounds(groupNode, nodeMap) {
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

function getNodeCenter(node, nodeMap) {
  const pos = getNodeAbsolutePosition(node, nodeMap);
  const width = Number(getNodeDimension(node, 'width')) || 200;
  const height = Number(getNodeDimension(node, 'height')) || 120;
  return {
    x: pos.x + width / 2,
    y: pos.y + height / 2,
  };
}

function getNodeRect(node, nodeMap) {
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

function getAbsoluteRectForNodePosition(node, absolutePosition) {
  const width = Number(getNodeDimension(node, 'width')) || 200;
  const height = Number(getNodeDimension(node, 'height')) || 120;
  return {
    left: absolutePosition.x,
    top: absolutePosition.y,
    right: absolutePosition.x + width,
    bottom: absolutePosition.y + height,
  };
}

function rectContainsPoint(rect, point) {
  return point.x >= rect.left
    && point.x <= rect.right
    && point.y >= rect.top
    && point.y <= rect.bottom;
}

function rectContainsRect(outerRect, innerRect) {
  return innerRect.left >= outerRect.left
    && innerRect.top >= outerRect.top
    && innerRect.right <= outerRect.right
    && innerRect.bottom <= outerRect.bottom;
}

function getEventClientPosition(event) {
  if (!event) return null;
  const point = 'changedTouches' in event && event.changedTouches?.[0]
    ? event.changedTouches[0]
    : ('touches' in event && event.touches?.[0] ? event.touches[0] : event);
  if (!Number.isFinite(point?.clientX) || !Number.isFinite(point?.clientY)) return null;
  return { x: point.clientX, y: point.clientY };
}

function getEventFlowPosition(event, reactFlow) {
  const clientPosition = getEventClientPosition(event);
  if (!clientPosition || typeof reactFlow?.screenToFlowPosition !== 'function') return null;
  return reactFlow.screenToFlowPosition(clientPosition);
}

function getDragIntent(event, reactFlow, dragState) {
  if (!dragState?.pointerOffset || !dragState?.anchorStartAbsolute) return null;
  const pointerFlowPos = getEventFlowPosition(event, reactFlow);
  if (!pointerFlowPos) return null;

  const anchorAbsolute = {
    x: pointerFlowPos.x - dragState.pointerOffset.x,
    y: pointerFlowPos.y - dragState.pointerOffset.y,
  };
  const delta = {
    x: anchorAbsolute.x - (Number(dragState.anchorStartAbsolute.x) || 0),
    y: anchorAbsolute.y - (Number(dragState.anchorStartAbsolute.y) || 0),
  };
  const absolutePositions = new Map(
    Object.entries(dragState.absolutePositions || {}).map(([id, pos]) => [
      id,
      {
        x: (Number(pos?.x) || 0) + delta.x,
        y: (Number(pos?.y) || 0) + delta.y,
      },
    ]),
  );

  return {
    pointerFlowPos,
    anchorAbsolute,
    absolutePositions,
  };
}

function findExpandedGroupDropTarget(nodes, draggedNodeIds, anchorNodeId, anchorPoint = null) {
  const nodeMap = new Map((nodes || []).map((node) => [String(node.id), node]));
  const anchorNode = nodeMap.get(String(anchorNodeId));
  if (!anchorNode) return null;

  const draggedIdSet = new Set((draggedNodeIds || []).map((id) => String(id)));
  const anchorCenter = anchorPoint && Number.isFinite(anchorPoint.x) && Number.isFinite(anchorPoint.y)
    ? anchorPoint
    : getNodeCenter(anchorNode, nodeMap);

  return (nodes || [])
    .filter((node) => (
      node?.data?.className === 'Group'
      && !node?.data?.collapsed
      && !draggedIdSet.has(String(node.id))
    ))
    .map((node) => {
      const rect = getGroupWorkspaceBounds(node, nodeMap);
      return {
        node,
        rect,
        area: Math.max(1, rect.right - rect.left) * Math.max(1, rect.bottom - rect.top),
      };
    })
    .filter(({ rect }) => rectContainsPoint(rect, anchorCenter))
    .sort((a, b) => a.area - b.area)[0]?.node || null;
}

function getInputLabelForNode(node, inputName) {
  const inputs = {
    ...(node?.data?.definition?.input?.required || {}),
    ...(node?.data?.definition?.input?.optional || {}),
  };
  const spec = inputs[inputName];
  if (!spec) return inputName;
  const [, opts] = Array.isArray(spec) ? spec : [spec, {}];
  return opts?.label || inputName;
}

function getOutputLabelForNode(node, slot, handleId) {
  const outputNames = node?.data?.definition?.output_name || [];
  const outputTypes = node?.data?.definition?.output || [];
  if (Number.isInteger(slot) && outputNames[slot]) return outputNames[slot];
  const proxy = parseGroupProxyHandle(handleId);
  return proxy?.realHandle ? getOutputLabelForNode(node, getOutputSlot(proxy.realHandle), proxy.realHandle) : outputTypes[slot] || 'output';
}

function buildGroupProxyData(groupId, nodes, edges) {
  const nodeMap = new Map((nodes || []).map((node) => [String(node.id), node]));
  const memberIds = new Set(getGroupMembers(nodes, groupId));
  const proxyInputs = [];
  const proxyOutputs = [];
  const seenInputs = new Set();
  const seenOutputs = new Set();

  for (const edge of edges || []) {
    const original = edge?.data?.groupProxyOriginal || {};
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

function sameStringArray(a = [], b = []) {
  if (a === b) return true;
  if (!Array.isArray(a) || !Array.isArray(b) || a.length !== b.length) return false;
  return a.every((item, index) => item === b[index]);
}

function isEditableTarget(target) {
  if (!target || !(target instanceof Element)) return false;
  if (target.closest('input, textarea, select')) return true;
  return target.closest('[contenteditable="true"]') !== null;
}

function clampNumber(value, min, max) {
  return Math.min(max, Math.max(min, value));
}

function canStartCanvasRightDragZoom(target) {
  if (!target || !(target instanceof Element)) return false;
  if (isEditableTarget(target)) return false;
  if (target.closest('.context-menu, .react-flow__node, .react-flow__edge, .react-flow__controls, .react-flow__minimap, .surface-view-container')) {
    return false;
  }
  return target.closest('.react-flow__pane, .react-flow__background') !== null;
}

function compareMenuNodes(a, b) {
  const orderA = Number.isFinite(a?.menu_order)
    ? a.menu_order
    : Number.isFinite(a?.def?.menu_order)
      ? a.def.menu_order
      : Number.MAX_SAFE_INTEGER;
  const orderB = Number.isFinite(b?.menu_order)
    ? b.menu_order
    : Number.isFinite(b?.def?.menu_order)
      ? b.def.menu_order
      : Number.MAX_SAFE_INTEGER;
  if (orderA !== orderB) return orderA - orderB;

  const nameA = (a?.def?.display_name || a?.className || '').toLowerCase();
  const nameB = (b?.def?.display_name || b?.className || '').toLowerCase();
  return nameA.localeCompare(nameB);
}

function compareMenuCategories(a, b) {
  const orderA = Number.isFinite(a?.order) ? a.order : Number.MAX_SAFE_INTEGER;
  const orderB = Number.isFinite(b?.order) ? b.order : Number.MAX_SAFE_INTEGER;
  if (orderA !== orderB) return orderA - orderB;
  return String(a?.name || '').localeCompare(String(b?.name || ''));
}

function getRenderedNodeBounds(nodes) {
  let minX = Infinity;
  let minY = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;
  let found = false;

  for (const node of nodes) {
    const selectorId = typeof CSS !== 'undefined' && typeof CSS.escape === 'function'
      ? CSS.escape(String(node.id))
      : String(node.id);
    const el = document.querySelector(`.react-flow__node[data-id="${selectorId}"]`);
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

async function waitForImageElement(img) {
  if (img.complete && img.naturalWidth > 0) return;
  if (typeof img.decode === 'function') {
    try {
      await img.decode();
      return;
    } catch {
      // Fall back to load/error listeners below.
    }
  }
  await new Promise((resolve) => {
    const done = () => {
      img.removeEventListener('load', done);
      img.removeEventListener('error', done);
      resolve();
    };
    img.addEventListener('load', done, { once: true });
    img.addEventListener('error', done, { once: true });
  });
}

async function getCaptureImageDataUrl(img) {
  const src = img.currentSrc || img.src;
  if (!src) return null;
  if (!src.startsWith('data:')) return src;

  const rect = img.getBoundingClientRect();
  const width = Math.max(1, Math.round(img.clientWidth || rect.width));
  const height = Math.max(1, Math.round(img.clientHeight || rect.height));
  const scale = Math.min(2, window.devicePixelRatio || 1);

  const canvas = document.createElement('canvas');
  canvas.width = Math.max(1, Math.round(width * scale));
  canvas.height = Math.max(1, Math.round(height * scale));

  const ctx = canvas.getContext('2d');
  if (!ctx) return src;

  try {
    ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
    return canvas.toDataURL('image/png');
  } catch {
    return src;
  }
}

function createCapturePlaceholder(el, dataUrl) {
  const rect = el.getBoundingClientRect();
  const style = window.getComputedStyle(el);
  const placeholder = document.createElement('div');

  placeholder.style.display = style.display === 'inline' ? 'inline-block' : style.display;
  placeholder.style.width = `${el.clientWidth || rect.width}px`;
  placeholder.style.height = `${el.clientHeight || rect.height}px`;
  placeholder.style.maxWidth = style.maxWidth;
  placeholder.style.maxHeight = style.maxHeight;
  placeholder.style.minWidth = style.minWidth;
  placeholder.style.minHeight = style.minHeight;
  placeholder.style.borderRadius = style.borderRadius;
  placeholder.style.backgroundImage = `url("${dataUrl}")`;
  placeholder.style.backgroundRepeat = 'no-repeat';
  placeholder.style.backgroundPosition = 'center';
  placeholder.style.backgroundSize = el.tagName === 'CANVAS' ? '100% 100%' : 'contain';
  placeholder.style.flexShrink = style.flexShrink;

  return placeholder;
}

async function captureViewportBlob(viewportEl, options) {
  const restorers = [];
  const images = Array.from(viewportEl.querySelectorAll('img'));
  await Promise.all(images.map(waitForImageElement));

  for (const img of images) {
    if (!img.parentNode) continue;
    const dataUrl = await getCaptureImageDataUrl(img);
    if (!dataUrl) continue;
    const placeholder = createCapturePlaceholder(img, dataUrl);
    img.parentNode.replaceChild(placeholder, img);
    restorers.push(() => {
      if (placeholder.parentNode) {
        placeholder.parentNode.replaceChild(img, placeholder);
      }
    });
  }

  const canvases = Array.from(viewportEl.querySelectorAll('canvas'));
  for (const canvas of canvases) {
    if (!canvas.parentNode) continue;
    let dataUrl = 'data:,';
    try {
      dataUrl = canvas.toDataURL('image/png');
    } catch {
      dataUrl = 'data:,';
    }
    if (dataUrl === 'data:,') continue;

    const placeholder = createCapturePlaceholder(canvas, dataUrl);
    canvas.parentNode.replaceChild(placeholder, canvas);
    restorers.push(() => {
      if (placeholder.parentNode) {
        placeholder.parentNode.replaceChild(canvas, placeholder);
      }
    });
  }

  await new Promise((resolve) => requestAnimationFrame(() => resolve()));
  await new Promise((resolve) => requestAnimationFrame(() => resolve()));

  try {
    return await toBlob(viewportEl, options);
  } finally {
    restorers.reverse().forEach((restore) => restore());
  }
}

// ── Context menu component ────────────────────────────────────────────

function ContextMenu({
  x,
  y,
  nodeDefs,
  onAdd,
  onClose,
  filterType,
  filterSpec = null,
  filterDirection,
  selectedNodeCount = 0,
  onCreateGroup = null,
}) {
  const [openCat, setOpenCat] = useState(null);
  const [search, setSearch] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const menuRef = useRef(null);
  const [menuPos, setMenuPos] = useState({ x, y });
  const subMenuRef = useRef(null);
  const [subPos, setSubPos] = useState({ x: 0, y: 0 });
  const catRowRefs = useRef({});
  const selectedItemRef = useRef(null);

  // Group by category, optionally filtering to compatible nodes
  const categories = useMemo(() => {
    const cats = {};
    for (const [className, def] of Object.entries(nodeDefs)) {
      if (filterType && filterDirection) {
        if (filterDirection === 'source') {
          const req = def.input.required || {};
          const opt = def.input.optional || {};
          const allInputs = { ...req, ...opt };
          const hasMatch = Object.values(allInputs).some((spec) => {
            return socketSpecAcceptsType(filterType, spec);
          });
          if (!hasMatch) continue;
        } else {
          const hasMatch = def.output.some((type, idx) =>
            outputTypeCanConnectToTarget(type, filterSpec || filterType, def.output_accepted_types?.[idx] || [])
          );
          if (!hasMatch) continue;
        }
      }
      const menuCategories = Array.isArray(def.menu_categories) && def.menu_categories.length > 0
        ? def.menu_categories
        : [{
            category: def.category || 'uncategorized',
            category_order: def.category_order,
            menu_order: def.menu_order,
          }];

      for (const menuCategory of menuCategories) {
        const cat = menuCategory?.category || def.category || 'uncategorized';
        if (!cats[cat]) {
          cats[cat] = {
            name: cat,
            order: Number.isFinite(menuCategory?.category_order)
              ? menuCategory.category_order
              : Number.MAX_SAFE_INTEGER,
            items: [],
          };
        }
        cats[cat].order = Math.min(
          cats[cat].order,
          Number.isFinite(menuCategory?.category_order)
            ? menuCategory.category_order
            : Number.MAX_SAFE_INTEGER,
        );
        cats[cat].items.push({
          className,
          def,
          menu_order: Number.isFinite(menuCategory?.menu_order) ? menuCategory.menu_order : def.menu_order,
        });
      }
    }
    return Object.values(cats)
      .map((category) => ({
        ...category,
        items: [...category.items].sort(compareMenuNodes),
      }))
      .sort(compareMenuCategories);
  }, [nodeDefs, filterDirection, filterSpec, filterType]);

  // Flat filtered list for search
  const searchResults = useMemo(() => {
    if (!search.trim()) return null;
    const q = search.toLowerCase();
    const results = [];
    const seen = new Set();
    for (const category of categories) {
      for (const { className, def } of category.items) {
        if (seen.has(className)) continue;
        const name = (def.display_name || className).toLowerCase();
        if (name.includes(q)) {
          results.push({ className, def });
          seen.add(className);
        }
      }
    }
    return results;
  }, [search, categories]);

  // Reset selection to top whenever results change
  useEffect(() => {
    setSelectedIndex(0);
  }, [searchResults]);

  // Scroll selected item into view
  useEffect(() => {
    selectedItemRef.current?.scrollIntoView({ block: 'nearest' });
  }, [selectedIndex]);

  const handleSearchKeyDown = useCallback((e) => {
    if (!searchResults || searchResults.length === 0) return;
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex((i) => Math.min(i + 1, searchResults.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex((i) => Math.max(i - 1, 0));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      const item = searchResults[selectedIndex];
      if (item) { onAdd(item.className, item.def); onClose(); }
    }
  }, [searchResults, selectedIndex, onAdd, onClose]);

  // Clamp main menu position to viewport on mount
  useEffect(() => {
    const el = menuRef.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    const vw = window.innerWidth;
    const vh = window.innerHeight;
    let nx = x, ny = y;
    if (x + rect.width > vw) nx = vw - rect.width - 8;
    if (y + rect.height > vh) ny = vh - rect.height - 8;
    if (nx < 4) nx = 4;
    if (ny < 4) ny = 4;
    setMenuPos({ x: nx, y: ny });
  }, [x, y]);

  // Position submenu next to the hovered category row, clamped to viewport
  useEffect(() => {
    if (!openCat) return;
    const rowEl = catRowRefs.current[openCat];
    const subEl = subMenuRef.current;
    if (!rowEl || !subEl) return;

    const rowRect = rowEl.getBoundingClientRect();
    const menuRect = menuRef.current.getBoundingClientRect();
    const subRect = subEl.getBoundingClientRect();
    const vw = window.innerWidth;
    const vh = window.innerHeight;

    // Horizontal: prefer right side, fall back to left
    let sx = menuRect.right - 1;
    if (sx + subRect.width > vw - 8) {
      sx = menuRect.left - subRect.width + 1;
    }
    if (sx < 4) sx = 4;

    // Vertical: align top with hovered row, clamp to viewport
    let sy = rowRect.top;
    if (sy + subRect.height > vh - 8) {
      sy = vh - subRect.height - 8;
    }
    if (sy < 4) sy = 4;

    setSubPos({ x: sx, y: sy });
  }, [openCat]);

  const handleCatEnter = useCallback((cat) => {
    setOpenCat(cat);
  }, []);

  if (categories.length === 0) {
    return (
      <div className="context-menu" ref={menuRef} style={{ left: menuPos.x, top: menuPos.y }} onClick={(e) => e.stopPropagation()}>
        <div className="context-item" style={{ color: 'var(--text-muted)' }}>No compatible nodes</div>
      </div>
    );
  }

  const catNames = categories.map((category) => category.name);
  const categoryMap = Object.fromEntries(categories.map((category) => [category.name, category.items]));

  return (
    <>
      <div
        className="context-menu ctx-root"
        ref={menuRef}
        style={{ left: menuPos.x, top: menuPos.y }}
        onClick={(e) => e.stopPropagation()}
        onMouseLeave={(e) => {
          // Close submenu only if mouse didn't move into the submenu
          const related = e.relatedTarget;
          if (subMenuRef.current && subMenuRef.current.contains(related)) return;
          setOpenCat(null);
        }}
      >
        <div className="ctx-title">Add Node</div>
        <div className="ctx-search-row">
          <input
            className="ctx-search"
            type="text"
            placeholder="Search…"
            value={search}
            onChange={(e) => { setSearch(e.target.value); setOpenCat(null); }}
            onKeyDown={handleSearchKeyDown}
            autoFocus
          />
        </div>

        {!filterType && selectedNodeCount > 1 && typeof onCreateGroup === 'function' && (
          <div
            className="context-item"
            onClick={() => { onCreateGroup(); onClose(); }}
          >
            create group
          </div>
        )}

        {searchResults ? (
          <div className="ctx-list">
            {searchResults.length === 0 ? (
              <div className="context-item" style={{ color: 'var(--text-muted)' }}>No matches</div>
            ) : (
              searchResults.map(({ className, def }, idx) => (
                <div
                  key={className}
                  ref={idx === selectedIndex ? selectedItemRef : null}
                  className={`context-item${idx === selectedIndex ? ' context-item--selected' : ''}`}
                  onClick={() => { onAdd(className, def); onClose(); }}
                  onMouseEnter={() => setSelectedIndex(idx)}
                >
                  {def.display_name || className}
                </div>
              ))
            )}
          </div>
        ) : (
          <div className="ctx-list">
            {catNames.map((cat) => (
              <div
                key={cat}
                ref={(el) => { catRowRefs.current[cat] = el; }}
                className={`ctx-cat-item${openCat === cat ? ' ctx-cat-active' : ''}`}
                onMouseEnter={() => handleCatEnter(cat)}
              >
                <span className="ctx-cat-label">{cat}</span>
                <span className="ctx-cat-arrow">▶</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Submenu rendered as a sibling, positioned at computed screen coords */}
      {openCat && categoryMap[openCat] && (
        <div
          className="context-menu ctx-submenu"
          ref={subMenuRef}
          style={{ left: subPos.x, top: subPos.y }}
          onClick={(e) => e.stopPropagation()}
          onMouseLeave={(e) => {
            const related = e.relatedTarget;
            if (menuRef.current && menuRef.current.contains(related)) return;
            setOpenCat(null);
          }}
        >
          {categoryMap[openCat].map(({ className, def }) => (
            <div
              key={className}
              className="context-item"
              onClick={() => { onAdd(className, def); onClose(); }}
            >
              {def.display_name || className}
            </div>
          ))}
        </div>
      )}
    </>
  );
}

// ── Main flow component (needs ReactFlowProvider ancestor) ────────────

function Flow() {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [status, setStatus] = useState({ text: 'Connecting…', level: 'info' });
  const [contextMenu, setContextMenu] = useState(null);
  const [isCanvasRightZooming, setIsCanvasRightZooming] = useState(false);
  const [executingNodeId, setExecutingNodeId] = useState(null);

  const flowContainerRef = useRef(null);
  const panTimerRef = useRef(null);
  const nodeDefsRef = useRef({});
  const nextIdRef = useRef(1);
  const autoRunTimer = useRef(null);
  const autoRunRef = useRef(null);
  const defaultWorkflowLoadAttemptedRef = useRef(false);
  const lastPastedClipboardTextRef = useRef('');
  const pasteRepeatCountRef = useRef(0);
  const duplicateDragRef = useRef(null);
  const dragStateRef = useRef(null);
  const activeDragNodeIdRef = useRef(null);
  const canvasRightZoomRef = useRef(null);
  const suppressPaneContextMenuUntilRef = useRef(0);
  const loadNodeOutputRequestVersionsRef = useRef(new Map());
  const reactFlow = useReactFlow();

  // ── WebSocket ───────────────────────────────────────────────────────

  const updateNodeData = useCallback((nodeId, patch) => {
    setNodes((ns) => ns.map((n) =>
      n.id !== nodeId ? n : { ...n, data: { ...n.data, ...patch } }
    ));
  }, [setNodes]);

  const refreshGroupNode = useCallback((groupId, explicitNodes = null, explicitEdges = null) => {
    const currentNodes = explicitNodes || reactFlow.getNodes();
    const currentEdges = explicitEdges || reactFlow.getEdges();
    const groupNode = currentNodes.find((node) => node.id === groupId && node.data?.className === 'Group');
    if (!groupNode) return;

    const { proxyInputs, proxyOutputs, childCount } = buildGroupProxyData(groupId, currentNodes, currentEdges);
    setNodes((prev) => prev.map((node) => (
      node.id !== groupId
        ? node
        : {
          ...node,
          className: 'group-shell',
          data: {
            ...node.data,
            proxyInputs,
            proxyOutputs,
            childCount,
          },
        }
    )));
    reactFlow.updateNodeInternals(groupId);
  }, [reactFlow, setNodes]);

  const toggleGroupCollapse = useCallback((groupId) => {
    const currentNodes = reactFlow.getNodes();
    const currentEdges = reactFlow.getEdges();
    const groupNode = currentNodes.find((node) => node.id === groupId && node.data?.className === 'Group');
    if (!groupNode) return;

    const memberIds = new Set(getGroupMembers(currentNodes, groupId));
    const collapsed = !groupNode.data?.collapsed;
    const proxyData = buildGroupProxyData(groupId, currentNodes, currentEdges);

    const nextNodes = currentNodes.map((node) => {
      if (memberIds.has(String(node.id))) {
        return { ...node, hidden: collapsed };
      }
      if (node.id !== groupId) return node;
      const expandedSize = groupNode.data?.expandedSize || {
        width: Number(groupNode.style?.width) || 320,
        height: Number(groupNode.style?.height) || 240,
      };
      const collapsedHeight = Math.max(74, 38 + Math.max(proxyData.proxyInputs.length, proxyData.proxyOutputs.length, 1) * 24 + 26);
      return {
        ...applyNodeSize(
          node,
          collapsed ? 260 : expandedSize.width,
          collapsed ? collapsedHeight : expandedSize.height,
        ),
        data: {
          ...node.data,
          collapsed,
          expandedSize,
          proxyInputs: proxyData.proxyInputs,
          proxyOutputs: proxyData.proxyOutputs,
          childCount: proxyData.childCount,
        },
      };
    });

    const nextEdges = currentEdges.map((edge) => {
      if (collapsed) {
        if (edge.data?.groupProxyOwner === groupId || edge.data?.groupInternalHiddenBy === groupId) {
          return edge;
        }
        const sourceInside = memberIds.has(String(edge.source));
        const targetInside = memberIds.has(String(edge.target));
        if (sourceInside && targetInside) {
          return {
            ...edge,
            hidden: true,
            data: { ...(edge.data || {}), groupInternalHiddenBy: groupId },
          };
        }
        if (!sourceInside && targetInside) {
          return {
            ...edge,
            target: groupId,
            targetHandle: `group-proxy::in::${edge.target}::${getHandleType(edge.targetHandle)}::${encodeProxyHandleRef(edge.targetHandle)}`,
            data: {
              ...(edge.data || {}),
              groupProxyOwner: groupId,
              groupProxyOriginal: {
                target: edge.target,
                targetHandle: edge.targetHandle,
              },
            },
          };
        }
        if (sourceInside && !targetInside) {
          return {
            ...edge,
            source: groupId,
            sourceHandle: `group-proxy::out::${edge.source}::${getHandleType(edge.sourceHandle)}::${encodeProxyHandleRef(edge.sourceHandle)}`,
            data: {
              ...(edge.data || {}),
              groupProxyOwner: groupId,
              groupProxyOriginal: {
                source: edge.source,
                sourceHandle: edge.sourceHandle,
              },
            },
          };
        }
        return edge;
      }

      if (edge.data?.groupInternalHiddenBy === groupId) {
        const nextData = { ...(edge.data || {}) };
        delete nextData.groupInternalHiddenBy;
        return {
          ...edge,
          hidden: false,
          data: Object.keys(nextData).length > 0 ? nextData : undefined,
        };
      }
      if (edge.data?.groupProxyOwner === groupId) {
        const nextData = { ...(edge.data || {}) };
        const original = nextData.groupProxyOriginal || {};
        delete nextData.groupProxyOwner;
        delete nextData.groupProxyOriginal;
        return {
          ...edge,
          source: original.source || edge.source,
          sourceHandle: original.sourceHandle || edge.sourceHandle,
          target: original.target || edge.target,
          targetHandle: original.targetHandle || edge.targetHandle,
          data: Object.keys(nextData).length > 0 ? nextData : undefined,
        };
      }
      return edge;
    });

    setNodes(nextNodes);
    setEdges(nextEdges);
    setTimeout(() => refreshGroupNode(groupId, nextNodes, nextEdges), 0);
  }, [reactFlow, refreshGroupNode, setEdges, setNodes]);

  const ungroupGroup = useCallback((groupId) => {
    const currentNodes = reactFlow.getNodes();
    const currentEdges = reactFlow.getEdges();
    const nodeMap = new Map(currentNodes.map((node) => [String(node.id), node]));
    const groupNode = nodeMap.get(String(groupId));
    if (!groupNode || groupNode.data?.className !== 'Group') return;

    const memberIds = new Set(getGroupMembers(currentNodes, groupId));
    const groupSelected = !!groupNode.selected;

    const nextNodes = currentNodes
      .filter((node) => String(node.id) !== String(groupId))
      .map((node) => {
        if (!memberIds.has(String(node.id))) return node;
        const absolute = getNodeAbsolutePosition(node, nodeMap);
        return {
          ...node,
          parentId: undefined,
          extent: undefined,
          hidden: false,
          selected: groupSelected,
          position: absolute,
        };
      });

    const nextEdges = currentEdges
      .map((edge) => {
        if (edge.data?.groupInternalHiddenBy === groupId) {
          const nextData = { ...(edge.data || {}) };
          delete nextData.groupInternalHiddenBy;
          return {
            ...edge,
            hidden: false,
            data: Object.keys(nextData).length > 0 ? nextData : undefined,
          };
        }
        if (edge.data?.groupProxyOwner === groupId) {
          const nextData = { ...(edge.data || {}) };
          const original = nextData.groupProxyOriginal || {};
          delete nextData.groupProxyOwner;
          delete nextData.groupProxyOriginal;
          return {
            ...edge,
            source: original.source || edge.source,
            sourceHandle: original.sourceHandle || edge.sourceHandle,
            target: original.target || edge.target,
            targetHandle: original.targetHandle || edge.targetHandle,
            hidden: false,
            data: Object.keys(nextData).length > 0 ? nextData : undefined,
          };
        }
        return edge;
      })
      .filter((edge) => String(edge.source) !== String(groupId) && String(edge.target) !== String(groupId));

    setNodes(nextNodes);
    setEdges(nextEdges);
    setTimeout(() => {
      reactFlow.getNodes()
        .filter((node) => node.data?.className === 'Group')
        .forEach((node) => refreshGroupNode(node.id, nextNodes, nextEdges));
    }, 0);
  }, [reactFlow, refreshGroupNode, setEdges, setNodes]);

  const createGroupFromSelection = useCallback(() => {
    const currentNodes = reactFlow.getNodes();
    const selectedNodes = currentNodes.filter((node) => node.selected && node.data?.className !== 'Group');
    if (selectedNodes.length < 2) return;

    const selectedIds = selectedNodes.map((node) => String(node.id));
    const bounds = getGroupDisplayBounds(currentNodes, selectedIds);
    if (!bounds) return;

    const groupId = String(nextIdRef.current++);
    const groupPosition = {
      x: bounds.minX - GROUP_PADDING_X,
      y: bounds.minY - (GROUP_HEADER_HEIGHT + GROUP_PADDING_Y),
    };
    const groupWidth = Math.max(
      GROUP_MIN_WIDTH,
      Math.round(bounds.maxX - bounds.minX + GROUP_PADDING_X * 2),
    );
    const groupHeight = Math.max(
      GROUP_MIN_HEIGHT,
      Math.round(bounds.maxY - bounds.minY + GROUP_HEADER_HEIGHT + GROUP_PADDING_Y * 2),
    );

    const groupNode = {
      id: groupId,
      type: 'custom',
      className: 'group-shell',
      position: groupPosition,
      width: groupWidth,
      height: groupHeight,
      dragHandle: '.drag-handle',
      style: { width: groupWidth, height: groupHeight },
      data: {
        label: 'group',
        className: 'Group',
        definition: null,
        widgetValues: {},
        runtimeValues: {},
        collapsed: false,
        expandedSize: { width: groupWidth, height: groupHeight },
        proxyInputs: [],
        proxyOutputs: [],
        childCount: selectedNodes.length,
        previewImage: null,
        tableRows: null,
        meshData: null,
        overlay: null,
        scalarValue: null,
        processingTimeMs: null,
        warning: null,
      },
      selected: true,
    };

    const nodeMap = new Map(currentNodes.map((node) => [String(node.id), node]));
    const nextNodes = [
      ...currentNodes.map((node) => {
        if (!selectedIds.includes(String(node.id))) {
          return { ...node, selected: false };
        }
        const absolute = getNodeAbsolutePosition(node, nodeMap);
        return {
          ...node,
          selected: false,
          parentId: groupId,
          extent: 'parent',
          hidden: false,
          position: {
            x: absolute.x - groupPosition.x,
            y: absolute.y - groupPosition.y,
          },
        };
      }),
      groupNode,
    ];

    const orderedNodes = sortNodesForParentOrder(nextNodes);
    setNodes(orderedNodes);
    setTimeout(() => refreshGroupNode(groupId, orderedNodes, reactFlow.getEdges()), 0);
  }, [reactFlow, refreshGroupNode, setNodes]);

  const setNodeOutputs = useCallback((nodeId, output, outputName, extraDefinitionPatch = {}) => {
    setNodes((prev) => prev.map((node) => {
      if (node.id !== nodeId) return node;
      const currentDefinition = node.data.definition || {};
      const nextDefinition = {
        ...currentDefinition,
        ...extraDefinitionPatch,
        output,
        output_name: outputName,
      };
      const sameOutputs = sameStringArray(currentDefinition.output, output);
      const sameNames = sameStringArray(currentDefinition.output_name, outputName);
      const sameOutputPaths = sameStringArray(currentDefinition.output_paths, nextDefinition.output_paths);
      if (sameOutputs && sameNames && sameOutputPaths) {
        return node;
      }
      return {
        ...node,
        data: {
          ...node.data,
          definition: nextDefinition,
        },
      };
    }));
    reactFlow.updateNodeInternals(nodeId);
  }, [reactFlow, setNodes]);

  const getResolvedPathInput = useCallback((nodeId) => {
    const edge = reactFlow.getEdges().find(
      (e) => e.target === nodeId && getInputName(e.targetHandle) === 'path'
    );
    if (!edge) return null;
    const original = edge.data?.groupProxyOriginal || {};
    const sourceId = original.source || edge.source;
    const sourceHandle = original.sourceHandle || edge.sourceHandle;
    const sourceNode = reactFlow.getNode(sourceId);
    const outputPaths = sourceNode?.data?.definition?.output_paths;
    const outputSlot = getOutputSlot(sourceHandle);
    if (Array.isArray(outputPaths) && typeof outputPaths[outputSlot] === 'string') {
      return outputPaths[outputSlot];
    }
    return null;
  }, [reactFlow]);

  const refreshLoadNodeOutputs = useCallback(async (nodeId, explicitPath = null) => {
    const node = reactFlow.getNode(nodeId);
    const resolvedPath = resolveLoadNodeChannelPath({
      explicitPath,
      resolvedPathInput: getResolvedPathInput(nodeId),
      className: node?.data?.className || '',
      widgetValues: node?.data?.widgetValues || {},
    });
    const requestVersion = beginTrackedNodeRequest(loadNodeOutputRequestVersionsRef.current, nodeId);

    if (!resolvedPath) {
      if (!isTrackedNodeRequestCurrent(loadNodeOutputRequestVersionsRef.current, nodeId, requestVersion)) {
        return;
      }
      setNodeOutputs(nodeId, ['FILE_PATH', 'DATA_FIELD'], ['path', 'field'], { output_paths: [] });
      return;
    }

    const channels = await api.getChannels(resolvedPath);
    if (!isTrackedNodeRequestCurrent(loadNodeOutputRequestVersionsRef.current, nodeId, requestVersion)) {
      return;
    }
    setNodeOutputs(
      nodeId,
      ['FILE_PATH', ...channels.map((channel) => channel.type)],
      ['path', ...channels.map((channel) => channel.name)],
      { output_paths: [] },
    );
  }, [getResolvedPathInput, reactFlow, setNodeOutputs]);

  const refreshFolderNodeOutputs = useCallback(async (nodeId, folderPath) => {
    const entries = folderPath ? await api.getFolderFiles(folderPath) : [];
    setNodeOutputs(
      nodeId,
      entries.map((entry) => entry.type),
      entries.map((entry) => entry.name),
      { output_paths: entries.map((entry) => entry.path) },
    );

    const downstreamPathEdges = reactFlow.getEdges().filter(
      (edge) => edge.source === nodeId && getInputName(edge.targetHandle) === 'path'
    );
    for (const edge of downstreamPathEdges) {
      const outputSlot = getOutputSlot(edge.sourceHandle);
      const resolvedPath = entries[outputSlot]?.path || null;
      await refreshLoadNodeOutputs(edge.target, resolvedPath);
    }
  }, [reactFlow, refreshLoadNodeOutputs, setNodeOutputs]);

  const refreshAnnotationNodeOutputs = useCallback((nodeId) => {
    const node = reactFlow.getNode(nodeId);
    if (!node) return;

    const inputEdge = reactFlow.getEdges().find(
      (edge) => edge.target === nodeId && getInputName(edge.targetHandle) === 'input'
    );
    const outputType = inputEdge ? getHandleType(inputEdge.sourceHandle) : 'ANNOTATION_SOURCE';
    setNodeOutputs(nodeId, [outputType], ['Output']);

    if (!inputEdge || outputType === 'ANNOTATION_SOURCE') return;

    setEdges((prev) => prev.filter((edge) => {
      if (edge.source !== nodeId) return true;
      const resolvedTarget = getResolvedHandleRef(edge.target, edge.targetHandle);
      const targetNode = reactFlow.getNode(resolvedTarget.nodeId);
      const targetSpec = getNodeInputSpecForHandle(targetNode, resolvedTarget.handleId) || resolvedTarget.type;
      return socketSpecAcceptsType(outputType, targetSpec);
    }));
  }, [reactFlow, setEdges, setNodeOutputs]);

  useEffect(() => {
    api.setMessageHandler((msg) => {
      console.log('[tono] WS:', msg.type, msg.data?.node_id || msg.data?.node || '');
      switch (msg.type) {
        case 'execution_start':
          setNodes((ns) => ns.map((n) => ({
            ...n,
            data: { ...n.data, processingTimeMs: null },
          })));
          setExecutingNodeId(null);
          setStatus({ text: 'Running workflow…', level: 'info' });
          break;
        case 'executing':
          setExecutingNodeId(String(msg.data.node));
          setStatus({ text: `Executing node ${msg.data.node}…`, level: 'info' });
          break;
        case 'execution_complete':
          setExecutingNodeId(null);
          setStatus({ text: 'Done.', level: 'info' });
          break;
        case 'execution_error':
          setExecutingNodeId(null);
          setStatus({ text: 'Error: ' + msg.data.message, level: 'error' });
          console.error('[tono] execution error', msg.data);
          break;
        case 'preview':
          updateNodeData(msg.data.node_id, { previewImage: msg.data.image });
          break;
        case 'table':
          updateNodeData(msg.data.node_id, { tableRows: msg.data.rows });
          break;
        case 'scalar':
          updateNodeData(msg.data.node_id, {
            scalarValue: {
              value: msg.data.value,
              unit: typeof msg.data.unit === 'string' ? msg.data.unit : '',
            },
          });
          break;
        case 'node_timing':
          updateNodeData(msg.data.node_id, { processingTimeMs: msg.data.elapsed_ms });
          break;
        case 'mesh3d':
          updateNodeData(msg.data.node_id, { meshData: msg.data.mesh });
          break;
        case 'overlay':
          updateNodeData(
            msg.data.node_id,
            msg.data.overlay?.kind === 'mask_paint' || msg.data.overlay?.kind === 'markup'
              ? { overlay: msg.data.overlay, previewImage: null }
              : { overlay: msg.data.overlay },
          );
          break;
        case 'node_warning':
          updateNodeData(msg.data.node_id, { warning: msg.data.message });
          break;
        case 'nodes_updated':
          api.getNodes().then((defs) => {
            nodeDefsRef.current = defs;
            setStatus({ text: `Plugin loaded — ${Object.keys(defs).length} nodes available.`, level: 'info' });
          }).catch(() => {});
          break;
      }
    });
    api.initWS();
    return () => api.closeWS();
  }, [updateNodeData]);

  // ── Connection handling ─────────────────────────────────────────────

  const isValidConnection = useCallback(
    (connection) => checkConnectionValid(connection, (id) => reactFlow.getNode(id)),
    [reactFlow],
  );

  const onConnect = useCallback((params) => {
    const sourceProxy = parseGroupProxyHandle(params.sourceHandle);
    const targetProxy = parseGroupProxyHandle(params.targetHandle);
    const type = getConnectionHandleType(params.sourceHandle);
    const color = TYPE_COLORS[type] || 'var(--fallback-type)';

    const edgePayload = {
      ...params,
      style: { stroke: color, strokeWidth: 2 },
    };
    const proxyOriginal = {};
    if (sourceProxy) {
      proxyOriginal.source = sourceProxy.nodeId;
      proxyOriginal.sourceHandle = sourceProxy.realHandle;
    }
    if (targetProxy) {
      proxyOriginal.target = targetProxy.nodeId;
      proxyOriginal.targetHandle = targetProxy.realHandle;
    }
    if (Object.keys(proxyOriginal).length > 0) {
      edgePayload.data = {
        ...(edgePayload.data || {}),
        groupProxyOwner: sourceProxy?.direction === 'out' ? params.source : params.target,
        groupProxyOriginal: proxyOriginal,
      };
    }

    setEdges((eds) => {
      // Enforce single connection per input handle
      const filtered = eds.filter(
        (e) => !(e.target === params.target && e.targetHandle === params.targetHandle)
      );
      return addEdge(edgePayload, filtered);
    });
    const effectiveTargetHandle = targetProxy?.realHandle || params.targetHandle;
    const effectiveTargetNode = targetProxy?.nodeId || params.target;
    if (getInputName(effectiveTargetHandle) === 'path') {
      setTimeout(() => {
        refreshLoadNodeOutputs(effectiveTargetNode);
      }, 0);
    }
    const targetNode = reactFlow.getNode(effectiveTargetNode);
    if (targetNode && (targetNode.data.className === 'Annotations' || targetNode.data.className === 'Markup')) {
      setTimeout(() => {
        refreshAnnotationNodeOutputs(effectiveTargetNode);
      }, 0);
    }
    if (sourceProxy) {
      setTimeout(() => refreshGroupNode(params.source), 0);
    }
    if (targetProxy) {
      setTimeout(() => refreshGroupNode(params.target), 0);
    }
    scheduleAutoRun();
  }, [reactFlow, refreshAnnotationNodeOutputs, refreshGroupNode, refreshLoadNodeOutputs, setEdges]); // scheduleAutoRun is stable (no deps)

  const handleEdgesChange = useCallback((changes) => {
    const currentEdges = reactFlow.getEdges();
    onEdgesChange(changes);

    const affectedPathTargets = new Set();
    const affectedAnnotationTargets = new Set();
    for (const change of changes) {
      if (change.type !== 'remove') continue;
      const removedEdge = currentEdges.find((edge) => edge.id === change.id);
      if (!removedEdge) continue;
      if (getInputName(removedEdge.targetHandle) === 'path') {
        affectedPathTargets.add(removedEdge.target);
      }
      if (getInputName(removedEdge.targetHandle) === 'input') {
        const targetNode = reactFlow.getNode(removedEdge.target);
        if (targetNode && (targetNode.data.className === 'Annotations' || targetNode.data.className === 'Markup')) {
          affectedAnnotationTargets.add(removedEdge.target);
        }
      }
    }

    if (affectedPathTargets.size > 0) {
      setTimeout(() => {
        affectedPathTargets.forEach((nodeId) => {
          refreshLoadNodeOutputs(nodeId);
        });
      }, 0);
    }
    if (affectedAnnotationTargets.size > 0) {
      setTimeout(() => {
        affectedAnnotationTargets.forEach((nodeId) => {
          refreshAnnotationNodeOutputs(nodeId);
        });
      }, 0);
    }
    setTimeout(() => {
      reactFlow.getNodes()
        .filter((node) => node.data?.className === 'Group')
        .forEach((node) => refreshGroupNode(node.id));
    }, 0);
  }, [onEdgesChange, reactFlow, refreshAnnotationNodeOutputs, refreshGroupNode, refreshLoadNodeOutputs]);

  const handleNodesChange = useCallback((changes) => {
    const currentNodes = reactFlow.getNodes();
    const selectedGroupIds = new Set(
      changes
        .filter((change) => change.type === 'select' && change.selected)
        .map((change) => String(change.id))
        .filter((id) => currentNodes.some((node) => String(node.id) === id && node.data?.className === 'Group')),
    );
    const removedIds = new Set(
      changes
        .filter((change) => change.type === 'remove')
        .map((change) => String(change.id)),
    );

    onNodesChange(changes);

    if (selectedGroupIds.size > 0) {
      const deselectedDescendantIds = new Set();
      selectedGroupIds.forEach((groupId) => {
        collectGroupDescendantIds(currentNodes, groupId).forEach((id) => deselectedDescendantIds.add(id));
      });

      if (deselectedDescendantIds.size > 0) {
        setNodes((existing) => existing.map((node) => (
          deselectedDescendantIds.has(String(node.id))
            ? { ...node, selected: false }
            : node
        )));
      }
    }

    if (removedIds.size === 0) return;

    const groupIds = currentNodes
      .filter((node) => removedIds.has(String(node.id)) && node.data?.className === 'Group')
      .map((node) => String(node.id));
    const removedWithDescendants = new Set(removedIds);
    for (const groupId of groupIds) {
      collectGroupDescendantIds(currentNodes, groupId).forEach((id) => removedWithDescendants.add(id));
    }

    if (groupIds.length > 0) {
      setNodes((existing) => existing.filter((node) => !removedWithDescendants.has(String(node.id))));
      setEdges((existing) => existing.filter((edge) => (
        !removedWithDescendants.has(String(edge.source))
        && !removedWithDescendants.has(String(edge.target))
      )));
    }

    setTimeout(() => {
      reactFlow.getNodes()
        .filter((node) => node.data?.className === 'Group')
        .forEach((node) => refreshGroupNode(node.id));
    }, 0);
  }, [onNodesChange, reactFlow, refreshGroupNode, setEdges, setNodes]);

  // ── Drop-on-blank: open filtered context menu ──────────────────────

  const onConnectEnd = useCallback((event, connectionState) => {
    // If the connection was completed (dropped on a valid handle), do nothing
    if (connectionState.isValid) return;

    const fromHandle = connectionState.fromHandle;
    if (!fromHandle || !fromHandle.id) return;

    const { clientX, clientY } = 'changedTouches' in event ? event.changedTouches[0] : event;
    const handleType = getConnectionHandleType(fromHandle.id);
    const resolvedFromHandle = getResolvedHandleRef(fromHandle.nodeId, fromHandle.id);
    const fromNode = reactFlow.getNode(resolvedFromHandle.nodeId);
    const filterSpec = fromHandle.type === 'target'
      ? (getNodeInputSpecForHandle(fromNode, resolvedFromHandle.handleId) || handleType)
      : handleType;

    setContextMenu({
      x: clientX,
      y: clientY,
      filterType: handleType,
      filterSpec,
      filterDirection: fromHandle.type,
      pendingNodeId: fromHandle.nodeId,
      pendingHandleId: fromHandle.id,
      pendingHandleType: fromHandle.type,
    });
  }, [reactFlow]);

  // ── Widget change callback ──────────────────────────────────────────

  const onWidgetChange = useCallback((nodeId, name, value) => {
    setNodes((ns) => ns.map((n) => {
      if (n.id !== nodeId) return n;
      return {
        ...n,
        data: {
          ...n.data,
          widgetValues: { ...n.data.widgetValues, [name]: value },
          // Clear warning when user changes a value
          warning: null,
        },
      };
    }));

    const node = reactFlow.getNode(nodeId);
    if (node && node.data.className === 'Folder' && name === 'folder') {
      refreshFolderNodeOutputs(nodeId, value);
    }

    if (node && (node.data.className === 'Image' || node.data.className === 'ImageDemo') && (name === 'filename' || name === 'name')) {
      refreshLoadNodeOutputs(nodeId, value);
    }

    scheduleAutoRun();
  }, [reactFlow, refreshFolderNodeOutputs, refreshLoadNodeOutputs, setNodes]); // scheduleAutoRun is stable (no deps)

  // ── File browser ────────────────────────────────────────────────────

  const uploadBrowserSelection = useCallback(async (selection, selectionMode) => {
    if (!selection) return null;

    if (selectionMode === 'folder') {
      const rootName = String(selection.rootName || '').trim();
      if (!rootName) {
        throw new Error('Selected folder is empty or could not be read.');
      }

      setStatus({
        text: `Importing folder "${rootName}" into this session…`,
        level: 'info',
      });

      const folder = await api.createUploadFolder(rootName);
      for (const entry of selection.entries || []) {
        await api.uploadFile(entry.file, { relativePath: entry.relativePath });
      }
      return folder.path;
    }

    const [entry] = selection.entries || [];
    if (!entry) return null;

    setStatus({
      text: `Uploading ${entry.file.name}…`,
      level: 'info',
    });

    const uploaded = await api.uploadFile(entry.file, { relativePath: entry.relativePath });
    return uploaded.path;
  }, []);

  const openFileBrowser = useCallback(async (callback, { selectionMode = 'file' } = {}) => {
    if (selectionMode === 'folder' && window.pywebview?.api?.open_folder_dialog) {
      window.pywebview.api.open_folder_dialog().then((path) => {
        if (path) callback(path);
      });
      return;
    }
    if (selectionMode === 'file' && window.pywebview?.api?.open_file_dialog) {
      window.pywebview.api.open_file_dialog().then((path) => {
        if (path) callback(path);
      });
      return;
    }

    try {
      const selection = selectionMode === 'folder'
        ? await pickNativeDirectorySelection()
        : await pickNativeFileSelection();
      if (!selection) return;

      const uploadedPath = await uploadBrowserSelection(selection, selectionMode);
      if (uploadedPath) callback(uploadedPath);
    } catch (error) {
      setStatus({
        text: `Browse failed: ${error.message || String(error)}`,
        level: 'error',
      });
    }
  }, [uploadBrowserSelection]);

  // ── Node context value (stable) ─────────────────────────────────────

  const onManualTrigger = useCallback((nodeId) => {
    const currentNodes = reactFlow.getNodes();
    const currentEdges = reactFlow.getEdges();
    // Include ALL nodes (no excludeManualTrigger) so the save node is in the prompt
    const prompt = serializeExecutionGraph(currentNodes, currentEdges);
    if (!prompt || Object.keys(prompt).length === 0) return;
    setStatus({ text: 'Saving…', level: 'info' });
    api.runPrompt(prompt).catch((err) => {
      setStatus({ text: 'Save failed: ' + err.message, level: 'error' });
    });
  }, [reactFlow]);

  // ── Add node from context menu ──────────────────────────────────────

  const addNode = useCallback((className, def) => {
    if (!contextMenu) return;
    const position = reactFlow.screenToFlowPosition({
      x: contextMenu.x,
      y: contextMenu.y,
    });

    const widgetValues = buildDefaultWidgetValues(def);

    const newNodeId = String(nextIdRef.current++);
    const isTextNote = className === 'TextNote';
    const newNode = {
      id: newNodeId,
      type: 'custom',
      position,
      dragHandle: '.drag-handle',
      ...(isTextNote ? { width: 300, height: 220, style: { width: 300, height: 220 } } : {}),
      data: {
        label: def.display_name || className,
        className,
        definition: def,
        widgetValues,
        runtimeValues: {},
        previewImage: null,
        tableRows: null,
        meshData: null,
        overlay: null,
        scalarValue: null,
        processingTimeMs: null,
      },
    };

    setNodes((ns) => [...ns, newNode]);

    // Initialize dynamic outputs for nodes that depend on the selected path/folder.
    setTimeout(() => {
      if (className === 'Folder' && widgetValues.folder) {
        refreshFolderNodeOutputs(newNodeId, widgetValues.folder);
      }

      // For Image/ImageDemo, auto-fetch channels for the default value.
      // Delay this until after the node exists in React Flow so the async
      // response cannot be dropped on creation.
      if (className === 'ImageDemo' && widgetValues.name) {
        refreshLoadNodeOutputs(newNodeId, widgetValues.name);
      }
      if (className === 'Image' && widgetValues.filename) {
        refreshLoadNodeOutputs(newNodeId, widgetValues.filename);
      }
    }, 0);

    // Auto-connect if this was triggered by dropping a connection on blank space
    if (contextMenu.pendingHandleId) {
      const filterType = contextMenu.filterType;
      const filterSpec = contextMenu.filterSpec || filterType;

      if (contextMenu.pendingHandleType === 'source') {
        // Dragged from an output → connect to the first matching input on the new node
        const allInputs = { ...(def.input.required || {}), ...(def.input.optional || {}) };
        const inputName = Object.entries(allInputs).find(([, spec]) => {
          return socketSpecAcceptsType(filterType, spec);
        })?.[0];
        if (inputName) {
          const targetType = (() => {
            const spec = allInputs[inputName];
            const [type] = getSpecTypeAndOptions(spec);
            return type;
          })();
          const targetHandle = `input::${inputName}::${targetType}`;
          const color = TYPE_COLORS[filterType] || 'var(--fallback-type)';
          setEdges((eds) => addEdge({
            source: contextMenu.pendingNodeId,
            sourceHandle: contextMenu.pendingHandleId,
            target: newNodeId,
            targetHandle,
            style: { stroke: color, strokeWidth: 2 },
          }, eds));
        }
      } else {
        // Dragged from an input → connect from the first matching output on the new node
        const outputIdx = def.output.findIndex((type, idx) =>
          outputTypeCanConnectToTarget(type, filterSpec, def.output_accepted_types?.[idx] || [])
        );
        if (outputIdx !== -1) {
          const outputType = resolveOutputTypeForTarget(def.output[outputIdx], filterSpec);
          const sourceHandle = `output::${outputIdx}::${outputType}`;
          const color = TYPE_COLORS[outputType] || 'var(--fallback-type)';
          setEdges((eds) => addEdge({
            source: newNodeId,
            sourceHandle,
            target: contextMenu.pendingNodeId,
            targetHandle: contextMenu.pendingHandleId,
            style: { stroke: color, strokeWidth: 2 },
          }, eds));
        }
      }
    }

    setContextMenu(null);
    scheduleAutoRun();
  }, [contextMenu, reactFlow, refreshFolderNodeOutputs, refreshLoadNodeOutputs, setNodes, setEdges]); // scheduleAutoRun is stable (no deps)

  // ── Toolbar actions ─────────────────────────────────────────────────

  const runWorkflow = useCallback(async () => {
    // Read current state via functional ref to avoid stale closure
    const currentNodes = reactFlow.getNodes();
    const currentEdges = reactFlow.getEdges();
    const prompt = serializeExecutionGraph(currentNodes, currentEdges);

    if (!prompt || Object.keys(prompt).length === 0) {
      setStatus({ text: 'Graph is empty — add some nodes first.', level: 'error' });
      return;
    }
    setStatus({ text: 'Running…', level: 'info' });
    try {
      await api.runPrompt(prompt);
    } catch (err) {
      setStatus({ text: 'Failed: ' + err.message, level: 'error' });
    }
  }, [reactFlow]);

  // Debounced auto-run via ref to avoid dependency chains
  autoRunRef.current = () => {
    const currentNodes = reactFlow.getNodes();
    const currentEdges = reactFlow.getEdges();
    const runnableNodes = getAutoRunnableNodes(currentNodes, currentEdges);

    // Don't run if any non-manual node has unconnected required data inputs
    // or any FILE_PICKER widget is empty
    for (const node of runnableNodes) {
      if (hasBlockingAutoRunInput(node, currentEdges)) return;
    }

    const prompt = serializeExecutionGraph(currentNodes, currentEdges, { excludeManualTrigger: true });
    if (!prompt || Object.keys(prompt).length === 0) return;
    setStatus({ text: 'Running…', level: 'info' });
    api.runPrompt(prompt).catch((err) => {
      setStatus({ text: 'Failed: ' + err.message, level: 'error' });
    });
  };

  const scheduleAutoRun = useCallback(() => {
    clearTimeout(autoRunTimer.current);
    autoRunTimer.current = setTimeout(() => autoRunRef.current?.(), 300);
  }, []);

  const onRuntimeValuesChange = useCallback((nodeId, patch, { scheduleRun = false } = {}) => {
    if (!patch || typeof patch !== 'object') return;

    setNodes((ns) => ns.map((n) => {
      if (n.id !== nodeId) return n;
      return {
        ...n,
        data: {
          ...n.data,
          runtimeValues: { ...(n.data.runtimeValues || {}), ...patch },
        },
      };
    }));

    if (scheduleRun) {
      scheduleAutoRun();
    }
  }, [setNodes, scheduleAutoRun]);

  const initializeDynamicNodes = useCallback((nodesToInitialize) => {
    setTimeout(() => {
      nodesToInitialize.forEach((node) => {
        if (node.data.className === 'Folder' && node.data.widgetValues?.folder) {
          refreshFolderNodeOutputs(node.id, node.data.widgetValues.folder);
        }
      });
      nodesToInitialize.forEach((node) => {
        if (node.data.className === 'Image' || node.data.className === 'ImageDemo') {
          refreshLoadNodeOutputs(node.id);
        }
      });
      nodesToInitialize.forEach((node) => {
        if (node.data.className === 'Annotations' || node.data.className === 'Markup') {
          refreshAnnotationNodeOutputs(node.id);
        }
      });
      nodesToInitialize.forEach((node) => {
        reactFlow.updateNodeInternals(node.id);
      });
    }, 0);
  }, [reactFlow, refreshAnnotationNodeOutputs, refreshFolderNodeOutputs, refreshLoadNodeOutputs]);

  const pasteClipboardSelection = useCallback((clipboardText) => {
    const payload = parseNodeClipboardPayload(clipboardText);
    if (!payload) return false;

    if (clipboardText === lastPastedClipboardTextRef.current) {
      pasteRepeatCountRef.current += 1;
    } else {
      lastPastedClipboardTextRef.current = clipboardText;
      pasteRepeatCountRef.current = 1;
    }

    const offsetAmount = 36 * pasteRepeatCountRef.current;
    const pasted = instantiateNodeClipboardPayload(
      payload,
      nodeDefsRef.current,
      nextIdRef.current,
      { x: offsetAmount, y: offsetAmount },
    );

    if (pasted.nodes.length === 0) return false;

    nextIdRef.current = pasted.nextNodeId;

    setNodes((existing) => sortNodesForParentOrder([
      ...existing.map((node) => ({ ...node, selected: false })),
      ...pasted.nodes,
    ]));
    setEdges((existing) => [
      ...existing.map((edge) => ({ ...edge, selected: false })),
      ...pasted.edges,
    ]);

    initializeDynamicNodes(pasted.nodes);

    setStatus({
      text: `Pasted ${pasted.nodes.length} node${pasted.nodes.length === 1 ? '' : 's'}.`,
      level: 'info',
    });
    scheduleAutoRun();
    return true;
  }, [
    initializeDynamicNodes,
    reactFlow,
    scheduleAutoRun,
    setEdges,
    setNodes,
  ]);

  const resizeGroup = useCallback((groupId, size) => {
    const nextWidth = Math.round(Number(size?.width) || 0);
    const nextHeight = Math.round(Number(size?.height) || 0);
    if (!nextWidth || !nextHeight) return;

    setNodes((existing) => existing.map((node) => {
      if (String(node.id) !== String(groupId) || node.data?.className !== 'Group') return node;

      const sameSize = Math.abs((Number(node.style?.width) || 0) - nextWidth) < 0.5
        && Math.abs((Number(node.style?.height) || 0) - nextHeight) < 0.5;
      if (sameSize) return node;

      return {
        ...applyNodeSize(node, nextWidth, nextHeight),
        data: {
          ...node.data,
          expandedSize: { width: nextWidth, height: nextHeight },
        },
      };
    }));

    setTimeout(() => reactFlow.updateNodeInternals(String(groupId)), 0);
  }, [reactFlow, setNodes]);

  const renameGroup = useCallback((groupId, label) => {
    const nextLabel = String(label || '').trim() || 'group';
    setNodes((existing) => existing.map((node) => {
      if (String(node.id) !== String(groupId) || node.data?.className !== 'Group') return node;
      if (String(node.data?.label || 'group') === nextLabel) return node;
      return {
        ...node,
        data: {
          ...node.data,
          label: nextLabel,
        },
      };
    }));
  }, [setNodes]);

  const contextValue = useMemo(() => ({
    onWidgetChange,
    onRuntimeValuesChange,
    openFileBrowser,
    onManualTrigger,
    onToggleGroupCollapse: toggleGroupCollapse,
    onResizeGroup: resizeGroup,
    onRenameGroup: renameGroup,
    onUngroup: ungroupGroup,
    executingNodeId,
  }), [onRuntimeValuesChange, onWidgetChange, openFileBrowser, onManualTrigger, renameGroup, resizeGroup, toggleGroupCollapse, ungroupGroup, executingNodeId]);

  const clearGraph = useCallback(() => {
    setNodes([]);
    setEdges([]);
    nextIdRef.current = 1;
    setStatus({ text: 'Graph cleared.', level: 'info' });
  }, [setNodes, setEdges]);

  const applyWorkflowData = useCallback((data) => {
    const hydrated = hydrateWorkflowState(data, nodeDefsRef.current);
    setNodes(sortNodesForParentOrder(hydrated.nodes));
    setEdges(hydrated.edges);
    nextIdRef.current = hydrated.nextNodeId;
    initializeDynamicNodes(hydrated.nodes);
  }, [initializeDynamicNodes, setNodes, setEdges]);

  const loadDefaultWorkflow = useCallback(async () => {
    if (defaultWorkflowLoadAttemptedRef.current) return;
    defaultWorkflowLoadAttemptedRef.current = true;

    const graphHasContent = () => {
      const currentNodes = reactFlow.getNodes();
      const currentEdges = reactFlow.getEdges();
      return currentNodes.length > 0 || currentEdges.length > 0;
    };

    if (graphHasContent()) return;

    try {
      const loaded = await loadDefaultWorkflowAsset();
      if (!loaded || graphHasContent()) return;

      applyWorkflowData(loaded.workflow);
      setStatus({ text: `Loaded default workflow from ${loaded.source}.`, level: 'info' });
      requestAnimationFrame(() => {
        requestAnimationFrame(() => scheduleAutoRun());
      });
    } catch (err) {
      setStatus({ text: 'Default workflow failed to load: ' + err.message, level: 'error' });
    }
  }, [applyWorkflowData, reactFlow, scheduleAutoRun]);

  // ── Load node definitions ───────────────────────────────────────────

  useEffect(() => {
    api.getNodes().then((defs) => {
      nodeDefsRef.current = defs;
      setStatus({ text: `Loaded ${Object.keys(defs).length} nodes.`, level: 'info' });
      loadDefaultWorkflow();
    }).catch((err) => {
      setStatus({ text: 'Failed to load nodes: ' + err.message, level: 'error' });
    });
  }, [loadDefaultWorkflow]);

  const getWorkflowBlob = useCallback(async () => {
    const viewportEl = document.querySelector('.react-flow__viewport');
    if (!viewportEl) throw new Error('Flow element not found');

    const allNodes = reactFlow.getNodes();
    if (allNodes.length === 0) throw new Error('No nodes to capture');

    const bounds = getRenderedNodeBounds(allNodes);
    if (!bounds) {
      throw new Error('Could not determine rendered node bounds');
    }
    const pad = 0.1; // 10% margin on each side
    const imageWidth = Math.ceil(bounds.width * (1 + pad * 2));
    const imageHeight = Math.ceil(bounds.height * (1 + pad * 2));
    const vp = getViewportForBounds(bounds, imageWidth, imageHeight, 0.5, 1, pad);

    const blob = await captureWorkflowViewportBlob(viewportEl, {
      backgroundColor: CANVAS_COLORS.bgDeep,
      width: imageWidth,
      height: imageHeight,
      style: {
        width: `${imageWidth}px`,
        height: `${imageHeight}px`,
        transform: `translate(${vp.x}px, ${vp.y}px) scale(${vp.zoom})`,
      },
    });
    if (!blob) throw new Error('Capture returned empty');

    const workflow = serializeWorkflowState(allNodes, reactFlow.getEdges());
    return embedWorkflow(blob, workflow);
  }, [reactFlow]);

  const saveWorkflow = useCallback(async () => {
    setStatus({ text: 'Saving…', level: 'info' });
    try {
      const finalBlob = await getWorkflowBlob();

      if (window.pywebview?.api?.choose_save_workflow_png_path) {
        const requestedPath = await window.pywebview.api.choose_save_workflow_png_path('workflow.png');
        if (!requestedPath) {
          setStatus({ text: 'Save cancelled.', level: 'info' });
          return;
        }
        const resp = await fetch(`/save-workflow-png?path=${encodeURIComponent(requestedPath)}`, {
          method: 'POST',
          headers: {
            'Content-Type': 'image/png',
          },
          body: finalBlob,
        });
        if (!resp.ok) {
          throw new Error(await resp.text() || `Save failed (${resp.status})`);
        }
        const { path: savedPath } = await resp.json();
        if (!savedPath) {
          setStatus({ text: 'Save cancelled.', level: 'info' });
          return;
        }
        setStatus({ text: `Workflow saved to ${savedPath}.`, level: 'info' });
        return;
      }

      if ('showSaveFilePicker' in window) {
        try {
          const handle = await window.showSaveFilePicker({
            suggestedName: 'workflow.png',
            types: [
              {
                description: 'PNG image',
                accept: { 'image/png': ['.png'] },
              },
            ],
          });
          const writable = await handle.createWritable();
          await writable.write(finalBlob);
          await writable.close();
          setStatus({ text: 'Workflow saved as workflow.png.', level: 'info' });
          return;
        } catch (err) {
          if (err?.name === 'AbortError') {
            setStatus({ text: 'Save cancelled.', level: 'info' });
            return;
          }
          throw err;
        }
      }

      // Final fallback: trigger a browser download and tell the user where it went.
      const resp = await fetch('/download?filename=workflow.png', {
        method: 'POST',
        body: finalBlob,
      });
      const dlBlob = await resp.blob();
      const a = document.createElement('a');
      a.href = URL.createObjectURL(dlBlob);
      a.download = 'workflow.png';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      setTimeout(() => URL.revokeObjectURL(a.href), 1000);

      setStatus({
        text: 'Workflow downloaded as workflow.png to your browser default downloads folder.',
        level: 'info',
      });
    } catch (err) {
      setStatus({ text: 'Save failed: ' + err.message, level: 'error' });
    }
  }, [getWorkflowBlob]);

  const copySnapshot = useCallback(() => {
    setStatus({ text: 'Copying snapshot…', level: 'info' });
    // Pass a Promise<Blob> to ClipboardItem so the clipboard.write() call
    // happens synchronously within the user gesture, avoiding permission errors.
    const blobPromise = getWorkflowBlob().catch((err) => {
      setStatus({ text: 'Snapshot failed: ' + err.message, level: 'error' });
      throw err;
    });
    navigator.clipboard.write([new ClipboardItem({ 'image/png': blobPromise })]).then(() => {
      setStatus({ text: 'Snapshot copied to clipboard.', level: 'info' });
    }).catch((err) => {
      setStatus({ text: 'Copy failed: ' + err.message, level: 'error' });
    });
  }, [getWorkflowBlob]);

  const loadWorkflow = useCallback(() => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.json,.png';
    input.onchange = async (e) => {
      const file = e.target.files[0];
      if (!file) return;
      try {
        let data;
        const lowerName = file.name.toLowerCase();
        if (lowerName.endsWith('.png') || file.type === 'image/png') {
          data = await extractWorkflow(file);
          if (!data) {
            setStatus({ text: 'No workflow data found in image.', level: 'error' });
            return;
          }
        } else {
          data = JSON.parse(await file.text());
        }
        applyWorkflowData(data);
        setStatus({ text: 'Workflow loaded.', level: 'info' });
      } catch {
        setStatus({ text: 'Invalid workflow file.', level: 'error' });
      }
    };
    input.click();
  }, [applyWorkflowData]);

  const uploadPlugin = useCallback(() => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.py';
    input.onchange = async (e) => {
      const file = e.target.files[0];
      if (!file) return;
      setStatus({ text: 'Uploading plugin…', level: 'info' });
      try {
        await api.uploadPlugin(file);
        // Node list refresh is handled by the nodes_updated WebSocket message.
      } catch (err) {
        setStatus({ text: err.message, level: 'error' });
      }
    };
    input.click();
  }, []);

  // ── Drag-and-drop workflow image loading ───────────────────────────

  const onDropFile = useCallback(async (event) => {
    const files = event.dataTransfer?.files;
    if (!files || files.length === 0) return;
    event.preventDefault();

    const file = files[0];
    const lowerName = file.name.toLowerCase();
    if (file.type !== 'image/png' && !lowerName.endsWith('.png')) return;

    try {
      const data = await extractWorkflow(file);
      if (!data) {
        setStatus({ text: 'No workflow data in this image.', level: 'error' });
        return;
      }
      applyWorkflowData(data);
      setStatus({ text: 'Workflow loaded from image.', level: 'info' });
    } catch (err) {
      setStatus({ text: 'Failed to load: ' + err.message, level: 'error' });
    }
  }, [applyWorkflowData]);

  const onDragOver = useCallback((event) => {
    if (event.dataTransfer?.types?.includes('Files')) {
      event.preventDefault();
      event.dataTransfer.dropEffect = 'copy';
    }
  }, []);

  const onNodeDragStart = useCallback((event, node) => {
    activeDragNodeIdRef.current = String(node.id);
    dragStateRef.current = null;

    if (!(event.ctrlKey || event.metaKey)) {
      duplicateDragRef.current = null;
      const currentNodes = reactFlow.getNodes();
      const draggedNodes = node.data?.className === 'Group'
        ? []
        : (
          node.selected
            ? currentNodes.filter((candidate) => candidate.selected && candidate.data?.className !== 'Group')
            : currentNodes.filter((candidate) => candidate.id === node.id)
        );
      const pointerFlowPos = getEventFlowPosition(event, reactFlow);
      if (draggedNodes.length > 0 && pointerFlowPos) {
        const nodeMap = new Map(currentNodes.map((candidate) => [String(candidate.id), candidate]));
        const absolutePositions = Object.fromEntries(
          draggedNodes.map((candidate) => [
            String(candidate.id),
            getNodeAbsolutePosition(candidate, nodeMap),
          ]),
        );
        const anchorAbsolute = absolutePositions[String(node.id)] || getNodeAbsolutePosition(node, nodeMap);
        dragStateRef.current = {
          anchorId: String(node.id),
          anchorStartAbsolute: anchorAbsolute,
          absolutePositions,
          releasedNodeIds: new Set(),
          touchedGroupIds: new Set(),
          pointerOffset: {
            x: pointerFlowPos.x - anchorAbsolute.x,
            y: pointerFlowPos.y - anchorAbsolute.y,
          },
        };
      }
      if (node.data?.className === 'Group') {
        const descendantIds = collectGroupDescendantIds(currentNodes, node.id);
        if (descendantIds.size > 0) {
          setNodes((existing) => existing.map((candidate) => (
            descendantIds.has(String(candidate.id))
              ? { ...candidate, selected: false }
              : candidate
          )));
        }
      }
      return;
    }

    const currentNodes = reactFlow.getNodes();
    const draggedNodes = node.selected
      ? currentNodes.filter((candidate) => candidate.selected)
      : currentNodes.filter((candidate) => candidate.id === node.id);
    if (draggedNodes.length === 0) return;

    const draggedIds = draggedNodes.map((candidate) => String(candidate.id));
    const payload = buildNodeClipboardPayloadForIds(
      currentNodes,
      reactFlow.getEdges(),
      draggedIds,
      { includeIncomingExternalEdges: true },
    );
    if (!payload) return;

    const duplicated = instantiateNodeClipboardPayload(
      payload,
      nodeDefsRef.current,
      nextIdRef.current,
      { x: 0, y: 0 },
      { keepExternalSources: true },
    );
    if (duplicated.nodes.length === 0) return;

    nextIdRef.current = duplicated.nextNodeId;

    const originPositions = Object.fromEntries(
      draggedNodes.map((candidate) => [
        String(candidate.id),
        {
          x: Number(candidate.position?.x) || 0,
          y: Number(candidate.position?.y) || 0,
        },
      ]),
    );
    const duplicateSourceById = Object.fromEntries(
      payload.nodes.map((candidate, index) => [duplicated.nodes[index]?.id, String(candidate.id)]).filter(([id]) => !!id),
    );

    duplicateDragRef.current = {
      anchorId: String(node.id),
      draggedIds,
      originPositions,
      duplicateSourceById,
    };

    setNodes((existing) => sortNodesForParentOrder([
      ...existing.map((candidate) => ({ ...candidate, selected: false })),
      ...duplicated.nodes,
    ]));
    setEdges((existing) => [
      ...existing.map((edge) => ({ ...edge, selected: false })),
      ...duplicated.edges,
    ]);

    initializeDynamicNodes(duplicated.nodes);
  }, [initializeDynamicNodes, reactFlow, setEdges, setNodes]);

  const onNodeDrag = useCallback((event, node) => {
    if (String(node.id) !== activeDragNodeIdRef.current) return;

    const duplicateState = duplicateDragRef.current;
    if (duplicateState) {
      const anchorId = duplicateState.anchorId || duplicateState.draggedIds[0];
      const anchorOrigin = duplicateState.originPositions[anchorId];
      if (!anchorOrigin) return;

      const offset = {
        x: (Number(node.position?.x) || 0) - anchorOrigin.x,
        y: (Number(node.position?.y) || 0) - anchorOrigin.y,
      };
      const draggedIdSet = new Set(duplicateState.draggedIds);

      setNodes((existing) => existing.map((candidate) => {
        const candidateId = String(candidate.id);
        const originalPosition = duplicateState.originPositions[candidateId];
        if (draggedIdSet.has(candidateId) && originalPosition) {
          return {
            ...candidate,
            selected: false,
            position: originalPosition,
          };
        }

        const sourceId = duplicateState.duplicateSourceById[candidateId];
        if (sourceId) {
          const sourceOrigin = duplicateState.originPositions[sourceId];
          if (!sourceOrigin) return candidate;
          return {
            ...candidate,
            selected: true,
            position: {
              x: sourceOrigin.x + offset.x,
              y: sourceOrigin.y + offset.y,
            },
          };
        }

        return candidate;
      }));
      return;
    }

    const dragState = dragStateRef.current;
    if (!dragState || node.data?.className === 'Group') return;

    const currentNodes = reactFlow.getNodes();
    const draggedNodes = node.selected
      ? currentNodes.filter((candidate) => candidate.selected && candidate.data?.className !== 'Group')
      : currentNodes.filter((candidate) => candidate.id === node.id);
    if (draggedNodes.length === 0) return;

    const dragIntent = getDragIntent(event, reactFlow, dragState);
    if (!dragIntent?.pointerFlowPos) return;

    const draggedIdSet = new Set(draggedNodes.map((candidate) => String(candidate.id)));
    const nodeMap = new Map(currentNodes.map((candidate) => [String(candidate.id), candidate]));
    const releasedNodeIds = dragState.releasedNodeIds instanceof Set
      ? new Set(dragState.releasedNodeIds)
      : new Set();
    const touchedGroupIds = dragState.touchedGroupIds instanceof Set
      ? new Set(dragState.touchedGroupIds)
      : new Set();

    let nextNodes = currentNodes;
    let changed = false;
    let structureChanged = false;

    nextNodes = nextNodes.map((candidate) => {
      const candidateId = String(candidate.id);
      if (!draggedIdSet.has(candidateId)) return candidate;

      const absolute = dragIntent.absolutePositions.get(candidateId)
        || getNodeAbsolutePosition(candidate, nodeMap);
      if (!absolute) return candidate;

      if (candidate.parentId) {
        const parentId = String(candidate.parentId);
        const parentNode = nodeMap.get(parentId);
        if (parentNode?.data?.className === 'Group') {
          const parentRect = getGroupWorkspaceBounds(parentNode, nodeMap);
          const parentAbsolute = getNodeAbsolutePosition(parentNode, nodeMap);
          const nextPosition = {
            x: absolute.x - parentAbsolute.x,
            y: absolute.y - parentAbsolute.y,
          };
          const candidateRect = getAbsoluteRectForNodePosition(candidate, absolute);
          const samePosition = Math.abs((Number(candidate.position?.x) || 0) - nextPosition.x) < 0.5
            && Math.abs((Number(candidate.position?.y) || 0) - nextPosition.y) < 0.5;

          if (!releasedNodeIds.has(candidateId) && !rectContainsRect(parentRect, candidateRect)) {
            releasedNodeIds.add(candidateId);
            changed = true;
            return {
              ...candidate,
              extent: undefined,
              hidden: false,
              position: nextPosition,
            };
          }

          if (releasedNodeIds.has(candidateId)) {
            if (!candidate.parentId && !candidate.extent && candidate.hidden !== true && samePosition) {
              return candidate;
            }

            changed = true;
            return {
              ...candidate,
              extent: undefined,
              hidden: false,
              position: nextPosition,
            };
          }
        }
      }

      if (!releasedNodeIds.has(candidateId)) return candidate;
      return candidate;
    });

    if (!changed) return;

    dragStateRef.current = {
      ...dragState,
      releasedNodeIds,
      touchedGroupIds,
    };

    setNodes(structureChanged ? sortNodesForParentOrder(nextNodes) : nextNodes);

    if (structureChanged) {
      setTimeout(() => {
        touchedGroupIds.forEach((groupId) => {
          if (groupId) refreshGroupNode(groupId, nextNodes, reactFlow.getEdges());
        });
      }, 0);
    }
  }, [reactFlow, refreshGroupNode, setNodes]);

  const onNodeDragStop = useCallback((event, node) => {
    if (String(node.id) !== activeDragNodeIdRef.current) return;
    activeDragNodeIdRef.current = null;

    const dragState = dragStateRef.current;
    dragStateRef.current = null;
    const duplicateState = duplicateDragRef.current;
    duplicateDragRef.current = null;
    if (duplicateState) {
      const anchorId = duplicateState.anchorId || duplicateState.draggedIds[0];
      const anchorOrigin = duplicateState.originPositions[anchorId];
      if (!anchorOrigin) return;

      const offset = {
        x: (Number(node.position?.x) || 0) - anchorOrigin.x,
        y: (Number(node.position?.y) || 0) - anchorOrigin.y,
      };
      const draggedIdSet = new Set(duplicateState.draggedIds);

      setNodes((existing) => existing.map((candidate) => {
        const candidateId = String(candidate.id);
        const originalPosition = duplicateState.originPositions[candidateId];
        if (draggedIdSet.has(candidateId) && originalPosition) {
          return {
            ...candidate,
            selected: false,
            position: originalPosition,
          };
        }

        const sourceId = duplicateState.duplicateSourceById[candidateId];
        if (sourceId) {
          const sourceOrigin = duplicateState.originPositions[sourceId];
          if (!sourceOrigin) return candidate;
          return {
            ...candidate,
            selected: true,
            position: {
              x: sourceOrigin.x + offset.x,
              y: sourceOrigin.y + offset.y,
            },
          };
        }

        return {
          ...candidate,
          selected: false,
        };
      }));

      setStatus({
        text: `Duplicated ${Object.keys(duplicateState.duplicateSourceById).length} node${Object.keys(duplicateState.duplicateSourceById).length === 1 ? '' : 's'}.`,
        level: 'info',
      });
      scheduleAutoRun();
      return;
    }

    const currentNodes = reactFlow.getNodes();
    const dragIntent = getDragIntent(event, reactFlow, dragState);
    const touchedGroupIds = dragState?.touchedGroupIds instanceof Set
      ? new Set(dragState.touchedGroupIds)
      : new Set();
    let nextNodes = currentNodes;
    let changed = false;

    const draggedNodes = node.data?.className === 'Group'
      ? []
      : (
        node.selected
          ? nextNodes.filter((candidate) => candidate.selected && candidate.data?.className !== 'Group')
          : nextNodes.filter((candidate) => candidate.id === node.id)
      );

    if (draggedNodes.length > 0) {
      const draggedIdSet = new Set(draggedNodes.map((candidate) => String(candidate.id)));
      const nodeMap = new Map(nextNodes.map((candidate) => [String(candidate.id), candidate]));
      const anchorNode = nodeMap.get(String(dragState?.anchorId || node.id));
      const intendedAnchorAbsolute = dragIntent?.absolutePositions.get(String(anchorNode?.id || node.id))
        || (anchorNode ? getNodeAbsolutePosition(anchorNode, nodeMap) : null);
      const intendedAnchorCenter = anchorNode && intendedAnchorAbsolute
        ? {
          x: intendedAnchorAbsolute.x + (Number(getNodeDimension(anchorNode, 'width')) || 200) / 2,
          y: intendedAnchorAbsolute.y + (Number(getNodeDimension(anchorNode, 'height')) || 120) / 2,
        }
        : null;
      const targetGroup = findExpandedGroupDropTarget(
        nextNodes,
        Array.from(draggedIdSet),
        node.id,
        intendedAnchorCenter,
      );
      if (targetGroup) {
        const targetRect = getGroupWorkspaceBounds(targetGroup, nodeMap);
        const targetAbs = getNodeAbsolutePosition(targetGroup, nodeMap);
        let joinedCount = 0;

        nextNodes = nextNodes.map((candidate) => {
          if (!draggedIdSet.has(String(candidate.id))) return candidate;

          const intendedAbsolute = dragIntent?.absolutePositions.get(String(candidate.id));
          const width = Number(getNodeDimension(candidate, 'width')) || 200;
          const height = Number(getNodeDimension(candidate, 'height')) || 120;
          const center = intendedAbsolute
            ? { x: intendedAbsolute.x + width / 2, y: intendedAbsolute.y + height / 2 }
            : getNodeCenter(candidate, nodeMap);
          if (!rectContainsPoint(targetRect, center)) return candidate;

          const absolute = intendedAbsolute || getNodeAbsolutePosition(candidate, nodeMap);
          const nextPosition = {
            x: absolute.x - targetAbs.x,
            y: absolute.y - targetAbs.y,
          };
          const alreadyInTarget = String(candidate.parentId || '') === String(targetGroup.id);
          const samePosition = Math.abs((Number(candidate.position?.x) || 0) - nextPosition.x) < 0.5
            && Math.abs((Number(candidate.position?.y) || 0) - nextPosition.y) < 0.5;
          if (alreadyInTarget && candidate.extent === 'parent' && samePosition) return candidate;

          if (candidate.parentId) {
            touchedGroupIds.add(String(candidate.parentId));
          }
          touchedGroupIds.add(String(targetGroup.id));
          joinedCount += 1;
          changed = true;
          return {
            ...candidate,
            parentId: String(targetGroup.id),
            extent: 'parent',
            hidden: false,
            position: nextPosition,
          };
        });

        if (joinedCount > 0) {
          setStatus({
            text: `Added ${joinedCount} node${joinedCount === 1 ? '' : 's'} to group.`,
            level: 'info',
          });
        }
      } else {
        let removedCount = 0;

        nextNodes = nextNodes.map((candidate) => {
          if (!draggedIdSet.has(String(candidate.id)) || !candidate.parentId) return candidate;

          const parentId = String(candidate.parentId);
          const parentNode = nodeMap.get(parentId);
          if (!parentNode || parentNode.data?.className !== 'Group') return candidate;
          const absolute = dragIntent?.absolutePositions.get(String(candidate.id))
            || getNodeAbsolutePosition(candidate, nodeMap);
          const parentWorkspaceRect = getGroupWorkspaceBounds(parentNode, nodeMap);
          const candidateRect = getAbsoluteRectForNodePosition(candidate, absolute);
          if (rectContainsRect(parentWorkspaceRect, candidateRect)) {
            if (candidate.extent === 'parent') return candidate;
            changed = true;
            return {
              ...candidate,
              extent: 'parent',
              hidden: false,
            };
          }

          touchedGroupIds.add(parentId);
          removedCount += 1;
          changed = true;
          return {
            ...candidate,
            parentId: undefined,
            extent: undefined,
            hidden: false,
            position: absolute,
          };
        });

        if (removedCount > 0) {
          setStatus({
            text: `Removed ${removedCount} node${removedCount === 1 ? '' : 's'} from group.`,
            level: 'info',
          });
        }
      }
    }

    if (!changed) {
      const releasedCount = dragState?.releasedNodeIds instanceof Set ? dragState.releasedNodeIds.size : 0;
      if (releasedCount > 0) {
        setStatus({
          text: `Removed ${releasedCount} node${releasedCount === 1 ? '' : 's'} from group.`,
          level: 'info',
        });
      }
      return;
    }

    setNodes(sortNodesForParentOrder(nextNodes));
    setTimeout(() => {
      touchedGroupIds.forEach((groupId) => {
        if (groupId) refreshGroupNode(groupId, nextNodes, reactFlow.getEdges());
      });
    }, 0);
  }, [reactFlow, refreshGroupNode, scheduleAutoRun, setNodes]);

  // ── Keyboard shortcut ───────────────────────────────────────────────

  useEffect(() => {
    const handler = (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
        e.preventDefault();
        runWorkflow();
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [runWorkflow]);

  useEffect(() => {
    const handleCopy = (event) => {
      if (isEditableTarget(event.target)) return;

      const payload = buildNodeClipboardPayload(reactFlow.getNodes(), reactFlow.getEdges());
      if (!payload) return;

      const serialized = JSON.stringify(payload);
      event.preventDefault();
      event.clipboardData?.setData(NODE_CLIPBOARD_MIME, serialized);
      event.clipboardData?.setData('text/plain', serialized);
      setStatus({
        text: `Copied ${payload.nodes.length} node${payload.nodes.length === 1 ? '' : 's'}.`,
        level: 'info',
      });
    };

    const handlePaste = (event) => {
      if (isEditableTarget(event.target)) return;

      const clipboardText = event.clipboardData?.getData(NODE_CLIPBOARD_MIME)
        || event.clipboardData?.getData('text/plain')
        || '';
      if (!clipboardText) return;

      const pasted = pasteClipboardSelection(clipboardText);
      if (pasted) {
        event.preventDefault();
      }
    };

    window.addEventListener('copy', handleCopy);
    window.addEventListener('paste', handlePaste);
    return () => {
      window.removeEventListener('copy', handleCopy);
      window.removeEventListener('paste', handlePaste);
    };
  }, [pasteClipboardSelection, reactFlow]);

  // ── Context menu ────────────────────────────────────────────────────

  const onPaneContextMenu = useCallback((event) => {
    event.preventDefault();
    if (performance.now() < suppressPaneContextMenuUntilRef.current) {
      suppressPaneContextMenuUntilRef.current = 0;
      return;
    }
    setContextMenu({ x: event.clientX, y: event.clientY });
  }, []);

  const onFlowContainerPointerDown = useCallback((event) => {
    if (event.button !== 2) return;
    if (!canStartCanvasRightDragZoom(event.target)) return;

    event.preventDefault();
    event.stopPropagation();
    setContextMenu(null);

    const viewport = reactFlow.getViewport();
    canvasRightZoomRef.current = {
      pointerId: event.pointerId,
      startY: event.clientY,
      startZoom: Number(viewport.zoom) || 1,
      moved: false,
    };
    setIsCanvasRightZooming(true);

    try {
      event.currentTarget.setPointerCapture?.(event.pointerId);
    } catch {
      // Ignore capture failures; global listeners still complete the interaction.
    }
  }, [reactFlow]);

  const onFlowContainerContextMenuCapture = useCallback((event) => {
    if (canvasRightZoomRef.current?.moved || performance.now() < suppressPaneContextMenuUntilRef.current) {
      event.preventDefault();
      event.stopPropagation();
    }
  }, []);

  const onFlowContainerWheel = useCallback(() => {
    const container = flowContainerRef.current;
    if (!container) return;
    container.classList.add('is-panning');
    clearTimeout(panTimerRef.current);
    panTimerRef.current = setTimeout(() => {
      container.classList.remove('is-panning');
    }, 150);
  }, []);

  useEffect(() => {
    const handlePointerMove = (event) => {
      const zoomState = canvasRightZoomRef.current;
      if (!zoomState || event.pointerId !== zoomState.pointerId) return;

      const deltaY = event.clientY - zoomState.startY;
      if (Math.abs(deltaY) < CANVAS_RIGHT_DRAG_ZOOM_THRESHOLD) return;

      event.preventDefault();
      zoomState.moved = true;

      const container = flowContainerRef.current;
      if (!container) return;
      const bounds = container.getBoundingClientRect();
      const localX = event.clientX - bounds.left;
      const localY = event.clientY - bounds.top;
      const currentViewport = reactFlow.getViewport();
      const flowX = (localX - currentViewport.x) / currentViewport.zoom;
      const flowY = (localY - currentViewport.y) / currentViewport.zoom;
      const nextZoom = clampNumber(
        zoomState.startZoom * Math.exp(-deltaY * CANVAS_RIGHT_DRAG_ZOOM_SENSITIVITY),
        CANVAS_MIN_ZOOM,
        CANVAS_MAX_ZOOM,
      );

      reactFlow.setViewport({
        x: localX - (flowX * nextZoom),
        y: localY - (flowY * nextZoom),
        zoom: nextZoom,
      }, { duration: 0 });
    };

    const finishPointerInteraction = (event) => {
      const zoomState = canvasRightZoomRef.current;
      if (!zoomState || event.pointerId !== zoomState.pointerId) return;

      if (zoomState.moved) {
        suppressPaneContextMenuUntilRef.current = performance.now() + 250;
      }
      canvasRightZoomRef.current = null;
      setIsCanvasRightZooming(false);

      const container = flowContainerRef.current;
      if (container?.hasPointerCapture?.(event.pointerId)) {
        try {
          container.releasePointerCapture(event.pointerId);
        } catch {
          // Ignore capture release errors.
        }
      }
    };

    window.addEventListener('pointermove', handlePointerMove, true);
    window.addEventListener('pointerup', finishPointerInteraction, true);
    window.addEventListener('pointercancel', finishPointerInteraction, true);
    return () => {
      window.removeEventListener('pointermove', handlePointerMove, true);
      window.removeEventListener('pointerup', finishPointerInteraction, true);
      window.removeEventListener('pointercancel', finishPointerInteraction, true);
    };
  }, [reactFlow]);

  useEffect(() => {
    if (!contextMenu) return undefined;

    const handlePointerDown = (event) => {
      if (event.target.closest('.context-menu')) return;
      setContextMenu(null);
    };

    window.addEventListener('pointerdown', handlePointerDown, true);
    return () => window.removeEventListener('pointerdown', handlePointerDown, true);
  }, [contextMenu]);

  const selectedNodeCount = nodes.filter((node) => node.selected).length;

  // ── Render ──────────────────────────────────────────────────────────

  return (
    <NodeContext.Provider value={contextValue}>
      <div className="app-container">
        {/* Toolbar */}
        <div id="toolbar">
          <span id="app-title">tono</span>

          <div className="toolbar-group">
            <button className="btn btn-primary" onClick={runWorkflow} title="Run workflow (Ctrl+Enter)">
              ▶ Run
            </button>
            <button className="btn" onClick={clearGraph} title="Clear graph">
              ✕ Clear
            </button>
          </div>

          <div className="toolbar-group">
            <button className="btn" onClick={saveWorkflow} title="Save workflow as PNG">
              ⤓ Save
            </button>
            <button className="btn" onClick={loadWorkflow} title="Load workflow (JSON or PNG)">
              ⤒ Load
            </button>
            <button className="btn" onClick={copySnapshot} title="Copy workflow screenshot to clipboard">
              ⎘ Snapshot
            </button>
            <button className="btn" onClick={uploadPlugin} title="Upload a plugin (.py)">
              ⊕ Plugin
            </button>
          </div>

          <div className={`status-bar ${status.level}`}>{status.text}</div>
        </div>

        {/* React Flow canvas */}
        <div
          ref={flowContainerRef}
          className={`flow-container${isCanvasRightZooming ? ' canvas-right-zooming' : ''}`}
          onDrop={onDropFile}
          onDragOver={onDragOver}
          onWheel={onFlowContainerWheel}
          onPointerDownCapture={onFlowContainerPointerDown}
          onContextMenuCapture={onFlowContainerContextMenuCapture}
        >
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={handleNodesChange}
            onEdgesChange={handleEdgesChange}
            onNodeDragStart={onNodeDragStart}
            onNodeDrag={onNodeDrag}
            onNodeDragStop={onNodeDragStop}
            onConnect={onConnect}
            onConnectEnd={onConnectEnd}
            isValidConnection={isValidConnection}
            nodeTypes={NODE_TYPES}
            onPaneContextMenu={onPaneContextMenu}
            colorMode="dark"
            panOnDrag={[1]}
            panOnScroll
            panOnScrollSpeed={1.5}
            panOnScrollMode={PanOnScrollMode.Free}
            zoomOnScroll={false}
            selectionOnDrag
            selectionMode={SelectionMode.Partial}
            multiSelectionKeyCode={['Shift']}
            deleteKeyCode={['Backspace', 'Delete']}
            defaultEdgeOptions={{ type: 'default' }}
          >
            <Background />
            <Controls />
            <MiniMap
              nodeColor={(n) => {
                const cat = n.data?.definition?.category;
                return CAT_COLORS[cat] || 'var(--fallback-cat)';
              }}
            />
          </ReactFlow>

          {contextMenu && (
            <ContextMenu
              x={contextMenu.x}
              y={contextMenu.y}
              nodeDefs={nodeDefsRef.current}
              onAdd={addNode}
              onCreateGroup={createGroupFromSelection}
              onClose={() => setContextMenu(null)}
              filterType={contextMenu.filterType}
              filterSpec={contextMenu.filterSpec}
              filterDirection={contextMenu.filterDirection}
              selectedNodeCount={selectedNodeCount}
            />
          )}
        </div>

      </div>
    </NodeContext.Provider>
  );
}

// ── App wrapper with ReactFlowProvider ────────────────────────────────

export default function App() {
  return (
    <ReactFlowProvider>
      <Flow />
    </ReactFlowProvider>
  );
}
