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
import HelpPanelManager from './HelpPanelManager';
import ContextMenu from './ContextMenu';
import * as api from './api';
import { pickNativeDirectorySelection, pickNativeFileSelection } from './nativePicker';
import { embedWorkflow, extractWorkflow, sanitizeJson } from './pngMetadata';
import { captureViewportBlob as captureWorkflowViewportBlob } from './workflowCapture';
import tonoIconUrl from '../../resources/icon_1024.png';
import { hydrateWorkflowState } from './workflowHydration';
import useUndoRedo from './useUndoRedo';
import { packWorkflow, unpackWorkflow } from './workflowPacking';
import { serializeWorkflowState } from './workflowSerialization';
import { sortNodesForParentOrder } from './nodeHierarchy';
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
} from './loadNodeOutputs';
import { buildDefaultWidgetValues } from './nodeWidgetDefaults';
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
} from './connectionUtils';

import {
  getSpecTypeAndOptions,
  socketSpecAcceptsType,
  TYPE_COLORS,
  CAT_COLORS,
  CANVAS_COLORS,
} from './constants';

import {
  GROUP_PADDING_X,
  GROUP_PADDING_Y,
  GROUP_HEADER_HEIGHT,
  GROUP_MIN_WIDTH,
  GROUP_MIN_HEIGHT,
  getNodeSize,
  applyNodeSize,
  getNodeAbsolutePosition,
  collectGroupDescendantIds,
  getGroupMembers,
  getGroupDisplayBounds,
  getGroupWorkspaceBounds,
  getNodeCenter,
  getAbsoluteRectForNodePosition,
  rectContainsPoint,
  rectContainsRect,
  findExpandedGroupDropTarget,
  getRenderedNodeBounds,
  buildGroupProxyData,
  sameStringArray,
} from './nodeGeometry';

import {
  getEventFlowPosition,
  getDragIntent,
  isEditableTarget,
  clampNumber,
  canStartCanvasRightDragZoom,
} from './canvasEvents';

import type {
  NodeData,
  NodeDefinition,
  NodeDefsRegistry,
  InputSpec,
  TonoNode,
  TonoEdge,
  SerializedWorkflow,
  WsMessage,
} from './types';
import type { Node, Edge, NodeChange, EdgeChange, Connection, ReactFlowInstance } from '@xyflow/react';

declare global {
  interface Window {
    pywebview?: {
      api?: {
        open_folder_dialog?: () => Promise<string | null>;
        open_file_dialog?: () => Promise<string | null>;
        choose_save_workflow_png_path?: (filename: string) => Promise<string | null>;
      };
    };
    showSaveFilePicker?: (options?: any) => Promise<any>;
  }
}

const NODE_TYPES = { custom: CustomNode };

const CANVAS_MIN_ZOOM = 0.2;
const CANVAS_MAX_ZOOM = 4;
const CANVAS_RIGHT_DRAG_ZOOM_SENSITIVITY = 0.0065;
const CANVAS_RIGHT_DRAG_ZOOM_THRESHOLD = 5;

const DEBUG = false; // set to true for verbose logging

function restoreGroupEdges(edges: any[], groupId: string) {
  return edges.map((edge: any) => {
    if ((edge.data as any)?.groupInternalHiddenBy === groupId) {
      const nextData: any = { ...(edge.data || {}) };
      delete nextData.groupInternalHiddenBy;
      return {
        ...edge,
        hidden: false,
        data: Object.keys(nextData).length > 0 ? nextData : undefined,
      };
    }
    if (edge.data?.groupProxyOwner === groupId) {
      const nextData: any = { ...(edge.data || {}) };
      const original = (nextData.groupProxyOriginal || {}) as Record<string, any>;
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
  });
}

// ── Main flow component (needs ReactFlowProvider ancestor) ────────────

function Flow() {
  const [nodes, setNodes, onNodesChange] = useNodesState<TonoNode>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<TonoEdge>([]);
  const [status, setStatus] = useState({ text: 'Connecting…', level: 'info' });
  const [contextMenu, setContextMenu] = useState<any>(null);
  const [isCanvasRightZooming, setIsCanvasRightZooming] = useState(false);
  const [executingNodeId, setExecutingNodeId] = useState<string | null>(null);
  const [helpTabs, setHelpTabs] = useState<{ label: string; type?: string; content: string | null }[]>([]);
  const [activeHelpTab, setActiveHelpTab] = useState<string | null>(null);
  const [updateInfo, setUpdateInfo] = useState<{ latest: string; url: string } | null>(null);
  const [menuOpen, setMenuOpen] = useState(false);
  const [menuClosing, setMenuClosing] = useState(false);
  const closeMenu = useCallback(() => {
    if (!menuOpen || menuClosing) return;
    setMenuClosing(true);
    setTimeout(() => { setMenuOpen(false); setMenuClosing(false); }, 150);
  }, [menuOpen, menuClosing]);

  const flowContainerRef = useRef<HTMLDivElement | null>(null);
  const panTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const nodeDefsRef = useRef<Record<string, any>>({});
  const nextIdRef = useRef(1);
  const autoRunTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const autoRunRef = useRef<(() => void) | null>(null);
  const pendingBrowserFilesRef = useRef<Map<string, File>>(new Map());
  const defaultWorkflowLoadAttemptedRef = useRef(false);
  const lastPastedClipboardTextRef = useRef('');
  const pasteRepeatCountRef = useRef(0);
  const duplicateDragRef = useRef<any>(null);
  const dragStateRef = useRef<any>(null);
  const activeDragNodeIdRef = useRef<string | null>(null);
  const canvasRightZoomRef = useRef<any>(null);
  const suppressPaneContextMenuUntilRef = useRef(0);
  const loadNodeOutputRequestVersionsRef = useRef(new Map<string, number>());
  const journalContentRef = useRef('');
  const pendingUndoSnapshotRef = useRef<{ nodes: TonoNode[]; edges: TonoEdge[]; nextId: number } | null>(null);
  const reactFlow = useReactFlow<TonoNode, TonoEdge>() as ReturnType<typeof useReactFlow<TonoNode, TonoEdge>> & { updateNodeInternals: (id: string) => void };
  const undoRedo = useUndoRedo();

  // ── Update check (native builds only) ──────────────────────────────
  useEffect(() => {
    if (!(window as any).pywebview) return;
    fetch('/check-update')
      .then((r) => r.ok ? r.json() : null)
      .then((data) => {
        if (data?.update_available && data.latest) {
          setUpdateInfo({ latest: data.latest, url: data.url });
        }
      })
      .catch(() => {});
  }, []);

  const scheduleAutoRun = useCallback(() => {
    if (autoRunTimer.current) clearTimeout(autoRunTimer.current);
    autoRunTimer.current = setTimeout(() => autoRunRef.current?.(), 300);
  }, []);

  // ── WebSocket ───────────────────────────────────────────────────────

  const updateNodeData = useCallback((nodeId: string, patch: Record<string, unknown>) => {
    setNodes((ns) => ns.map((n) =>
      n.id !== nodeId ? n : { ...n, data: { ...n.data, ...patch } }
    ));
  }, [setNodes]);

  const refreshGroupNode = useCallback((groupId: string, explicitNodes: any[] | null = null, explicitEdges: any[] | null = null) => {
    const currentNodes = explicitNodes || (reactFlow.getNodes() as TonoNode[]);
    const currentEdges = explicitEdges || (reactFlow.getEdges() as TonoEdge[]);
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
        } as unknown as TonoNode
    )));
    reactFlow.updateNodeInternals(groupId);
  }, [reactFlow, setNodes]);

  const refreshAllGroups = useCallback((explicitNodes: any[] | null = null, explicitEdges: any[] | null = null) => {
    setTimeout(() => {
      (reactFlow.getNodes() as TonoNode[])
        .filter((node) => node.data?.className === 'Group')
        .forEach((node) => refreshGroupNode(node.id, explicitNodes, explicitEdges));
    }, 0);
  }, [reactFlow, refreshGroupNode]);

  const toggleGroupCollapse = useCallback((groupId: string) => {
    const currentNodes = (reactFlow.getNodes() as TonoNode[]);
    const currentEdges = (reactFlow.getEdges() as TonoEdge[]);
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
        if (edge.data?.groupProxyOwner === groupId || (edge.data as any)?.groupInternalHiddenBy === groupId) {
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
            targetHandle: `group-proxy::in::${edge.target}::${getHandleType(edge.targetHandle || '')}::${encodeProxyHandleRef(edge.targetHandle || '')}`,
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
            sourceHandle: `group-proxy::out::${edge.source}::${getHandleType(edge.sourceHandle || '')}::${encodeProxyHandleRef(edge.sourceHandle || '')}`,
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

      return restoreGroupEdges([edge], groupId)[0];
    });

    setNodes(nextNodes as TonoNode[]);
    setEdges(nextEdges as TonoEdge[]);
    setTimeout(() => refreshGroupNode(groupId, nextNodes, nextEdges), 0);
  }, [reactFlow, refreshGroupNode, setEdges, setNodes]);

  const ungroupGroup = useCallback((groupId: string) => {
    const currentNodes = (reactFlow.getNodes() as TonoNode[]);
    const currentEdges = (reactFlow.getEdges() as TonoEdge[]);
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

    const nextEdges = restoreGroupEdges(currentEdges, groupId)
      .filter((edge: any) => String(edge.source) !== String(groupId) && String(edge.target) !== String(groupId));

    setNodes(nextNodes);
    setEdges(nextEdges);
    refreshAllGroups(nextNodes, nextEdges);
  }, [reactFlow, refreshAllGroups, setEdges, setNodes]);

  const createGroupFromSelection = useCallback(() => {
    const currentNodes = (reactFlow.getNodes() as TonoNode[]);
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

    const orderedNodes = sortNodesForParentOrder(nextNodes as any[]);
    setNodes(orderedNodes as TonoNode[]);
    setTimeout(() => refreshGroupNode(groupId, orderedNodes, (reactFlow.getEdges() as TonoEdge[])), 0);
  }, [reactFlow, refreshGroupNode, setNodes]);

  const setNodeOutputs = useCallback((nodeId: string, output: string[], outputName: string[], extraDefinitionPatch: Record<string, any> = {}) => {
    setNodes((prev) => prev.map((node) => {
      if (node.id !== nodeId) return node;
      const currentDefinition: any = node.data.definition || {};
      const nextDefinition: any = {
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

  const getResolvedPathInput = useCallback((nodeId: string) => {
    const edge = (reactFlow.getEdges() as TonoEdge[]).find(
      (e) => e.target === nodeId && getInputName(e.targetHandle || '') === 'path'
    );
    if (!edge) return null;
    const original = (edge.data?.groupProxyOriginal || {}) as Record<string, any>;
    const sourceId = original.source || edge.source;
    const sourceHandle = original.sourceHandle || edge.sourceHandle;
    const sourceNode = reactFlow.getNode(sourceId);
    const outputPaths = sourceNode?.data?.definition?.output_paths;
    const outputSlot = getOutputSlot(sourceHandle || '');
    if (Array.isArray(outputPaths) && typeof outputPaths[outputSlot] === 'string') {
      return outputPaths[outputSlot];
    }
    return null;
  }, [reactFlow]);

  const refreshLoadNodeOutputs = useCallback(async (nodeId: string, explicitPath: any = null) => {
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
      ['FILE_PATH', ...channels.map((channel: any) => channel.type)],
      ['path', ...channels.map((channel: any) => channel.name)],
      { output_paths: [] },
    );
  }, [getResolvedPathInput, reactFlow, setNodeOutputs]);

  const refreshFolderNodeOutputs = useCallback(async (nodeId: string, folderPath: any) => {
    let entries: any[] = [];

    if (folderPath) {
      // Check for pending browser files first (folder was picked but files not yet uploaded)
      const prefix = String(folderPath).endsWith('/') ? String(folderPath) : String(folderPath) + '/';
      const pendingEntries: any[] = [];
      for (const uri of pendingBrowserFilesRef.current.keys()) {
        if (uri.startsWith(prefix)) {
          const name = uri.slice(prefix.length);
          // Skip files in subdirectories for the top-level listing
          if (!name.includes('/')) {
            pendingEntries.push({ name, type: 'FILE_PATH', path: uri });
          }
        }
      }

      if (pendingEntries.length > 0) {
        // Build listing locally from pending files
        entries = [
          { name: 'directory', type: 'DIRECTORY', path: folderPath },
          ...pendingEntries.sort((a: any, b: any) => a.name.localeCompare(b.name)),
        ];
      } else {
        // Fall back to server (native builds, or files already uploaded)
        entries = await api.getFolderFiles(folderPath);
      }
    }

    setNodeOutputs(
      nodeId,
      entries.map((entry: any) => entry.type),
      entries.map((entry: any) => entry.name),
      { output_paths: entries.map((entry: any) => entry.path) },
    );

    const downstreamPathEdges = (reactFlow.getEdges() as TonoEdge[]).filter(
      (edge) => edge.source === nodeId && getInputName(edge.targetHandle || '') === 'path'
    );
    for (const edge of downstreamPathEdges) {
      const outputSlot = getOutputSlot(edge.sourceHandle || '');
      const resolvedPath = entries[outputSlot]?.path || null;
      await refreshLoadNodeOutputs(edge.target, resolvedPath);
    }
  }, [reactFlow, refreshLoadNodeOutputs, setNodeOutputs]);

  const refreshAnnotationNodeOutputs = useCallback((nodeId: string) => {
    const node = reactFlow.getNode(nodeId);
    if (!node) return;

    const inputEdge = (reactFlow.getEdges() as TonoEdge[]).find(
      (edge) => edge.target === nodeId && getInputName(edge.targetHandle || '') === 'input'
    );
    const outputType = inputEdge ? getHandleType(inputEdge.sourceHandle || '') : 'ANNOTATION_SOURCE';
    setNodeOutputs(nodeId, [outputType], ['Output']);

    if (!inputEdge || outputType === 'ANNOTATION_SOURCE') return;

    setEdges((prev) => prev.filter((edge) => {
      if (edge.source !== nodeId) return true;
      const resolvedTarget = getResolvedHandleRef(edge.target, edge.targetHandle || '');
      const targetNode = reactFlow.getNode(resolvedTarget.nodeId) as TonoNode | undefined;
      if (!targetNode) return true;
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
            data: { ...n.data, processingTimeMs: null, error: null },
          })));
          setExecutingNodeId(null);
          setStatus({ text: 'Running workflow…', level: 'info' });
          break;
        case 'executing':
          setExecutingNodeId(String(msg.data.node));
          updateNodeData(String(msg.data.node), { warning: null, error: null });
          setStatus({ text: `Executing node ${msg.data.node}…`, level: 'info' });
          break;
        case 'execution_complete':
          setExecutingNodeId(null);
          setStatus({ text: 'Done.', level: 'info' });
          break;
        case 'execution_error':
          setExecutingNodeId(null);
          if (msg.data.node_id) {
            updateNodeData(msg.data.node_id, { error: msg.data.message });
          }
          if (!msg.data.node_id) {
            setStatus({ text: 'Error: ' + msg.data.message, level: 'error' });
          }
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
        case 'file_download': {
          const dlToken = msg.data.token;
          const dlFilename = msg.data.filename || 'download';
          fetch(`/download-save/${encodeURIComponent(dlToken)}`)
            .then((r) => r.ok ? r.blob() : Promise.reject(new Error(`Download failed: ${r.status}`)))
            .then((blob) => {
              const url = URL.createObjectURL(blob);
              const a = document.createElement('a');
              a.href = url;
              a.download = dlFilename;
              document.body.appendChild(a);
              a.click();
              a.remove();
              URL.revokeObjectURL(url);
            })
            .catch((err) => setStatus({ text: String(err.message), level: 'error' }));
          break;
        }
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
    (connection: any) => checkConnectionValid(connection, (id: string) => reactFlow.getNode(id)),
    [reactFlow],
  );

  const onConnect = useCallback((params: any) => {
    const sourceProxy = parseGroupProxyHandle(params.sourceHandle);
    const targetProxy = parseGroupProxyHandle(params.targetHandle);
    const type = getConnectionHandleType(params.sourceHandle);
    const color = TYPE_COLORS[type] || 'var(--fallback-type)';

    const edgePayload: any = {
      ...params,
      style: { stroke: color, strokeWidth: 2 },
    };
    const proxyOriginal: Record<string, any> = {};
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

    undoRedo.pushSnapshot((reactFlow.getNodes() as TonoNode[]), (reactFlow.getEdges() as TonoEdge[]), nextIdRef.current);
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

  const handleEdgesChange = useCallback((changes: EdgeChange[]) => {
    if (changes.some((c: any) => c.type === 'remove')) {
      undoRedo.pushSnapshot((reactFlow.getNodes() as TonoNode[]), (reactFlow.getEdges() as TonoEdge[]), nextIdRef.current);
    }
    const currentEdges = (reactFlow.getEdges() as TonoEdge[]);
    onEdgesChange(changes);

    const affectedPathTargets = new Set<string>();
    const affectedAnnotationTargets = new Set<string>();
    for (const change of changes) {
      if (change.type !== 'remove') continue;
      const removedEdge = currentEdges.find((edge) => edge.id === change.id);
      if (!removedEdge) continue;
      if (getInputName(removedEdge.targetHandle || '') === 'path') {
        affectedPathTargets.add(removedEdge.target);
      }
      if (getInputName(removedEdge.targetHandle || '') === 'input') {
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
    refreshAllGroups();
  }, [onEdgesChange, reactFlow, refreshAllGroups, refreshAnnotationNodeOutputs, refreshLoadNodeOutputs]);

  const handleNodesChange = useCallback((changes: NodeChange[]) => {
    // Stash undo snapshot when a drag begins
    const isDragStart = changes.some((c: any) => c.type === 'position' && c.dragging);
    if (isDragStart && !pendingUndoSnapshotRef.current) {
      if (DEBUG) console.log('[undo] drag started, stashing snapshot');
      pendingUndoSnapshotRef.current = {
        nodes: structuredClone((reactFlow.getNodes() as TonoNode[])),
        edges: structuredClone((reactFlow.getEdges() as TonoEdge[])),
        nextId: nextIdRef.current,
      };
    }
    // Commit stashed snapshot when drag ends
    const isDragEnd = changes.some((c: any) => c.type === 'position' && c.dragging === false);
    if (isDragEnd && pendingUndoSnapshotRef.current) {
      if (DEBUG) console.log('[undo] drag ended, pushing snapshot');
      const s = pendingUndoSnapshotRef.current;
      undoRedo.pushSnapshot(s.nodes, s.edges, s.nextId);
      pendingUndoSnapshotRef.current = null;
    }

    const currentNodes = (reactFlow.getNodes() as TonoNode[]);
    const selectedGroupIds = new Set(
      (changes as any[])
        .filter((change: any) => change.type === 'select' && change.selected)
        .map((change: any) => String(change.id))
        .filter((id: string) => currentNodes.some((node) => String(node.id) === id && node.data?.className === 'Group')),
    );
    const removedIds = new Set(
      (changes as any[])
        .filter((change: any) => change.type === 'remove')
        .map((change: any) => String(change.id)),
    );

    if (removedIds.size > 0) {
      undoRedo.pushSnapshot((reactFlow.getNodes() as TonoNode[]), (reactFlow.getEdges() as TonoEdge[]), nextIdRef.current);
    }

    onNodesChange(changes as any);

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

    refreshAllGroups();
  }, [onNodesChange, reactFlow, refreshAllGroups, setEdges, setNodes]);

  // ── Drop-on-blank: open filtered context menu ──────────────────────

  const onConnectEnd = useCallback((event: any, connectionState: any) => {
    // If the connection was completed (dropped on a valid handle), do nothing
    if (connectionState.isValid) return;

    const fromHandle = connectionState.fromHandle;
    if (!fromHandle || !fromHandle.id) return;

    const { clientX, clientY } = 'changedTouches' in event ? event.changedTouches[0] : event;
    const handleType = getConnectionHandleType(fromHandle.id);
    const resolvedFromHandle = getResolvedHandleRef(fromHandle.nodeId, fromHandle.id);
    const fromNode = reactFlow.getNode(resolvedFromHandle.nodeId) as TonoNode | undefined;
    const filterSpec = fromHandle.type === 'target'
      ? (getNodeInputSpecForHandle(fromNode!, resolvedFromHandle.handleId) || handleType)
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

  const onWidgetChange = useCallback((nodeId: string, name: string, value: unknown) => {
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

  const uploadBrowserSelection = useCallback(async (selection: any, selectionMode: string) => {
    if (!selection) return null;

    if (selectionMode === 'folder') {
      const rootName = String(selection.rootName || '').trim();
      if (!rootName) {
        throw new Error('Selected folder is empty or could not be read.');
      }

      const folder = await api.createUploadFolder(rootName);
      const folderUri = folder.path; // e.g. "session://uploads/myfolder"

      // Store File objects for lazy upload — only uploaded when actually used
      for (const entry of selection.entries || []) {
        const fileUri = `session://uploads/${entry.relativePath}`;
        pendingBrowserFilesRef.current.set(fileUri, entry.file);
      }

      setStatus({
        text: `Folder "${rootName}" loaded (${(selection.entries || []).length} files).`,
        level: 'info',
      });

      return folderUri;
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

  const openFileBrowser = useCallback(async (callback: (path: string) => void, { selectionMode = 'file' } = {}) => {
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
    } catch (error: any) {
      setStatus({
        text: `Browse failed: ${error.message || String(error)}`,
        level: 'error',
      });
    }
  }, [uploadBrowserSelection]);

  // ── Lazy upload of pending browser files ─────────────────────────────

  const uploadPendingFiles = useCallback(async (prompt: Record<string, any>) => {
    const pending = pendingBrowserFilesRef.current;
    if (pending.size === 0) return;

    // Collect all string values from the prompt (folder paths and file paths)
    const promptValues = new Set<string>();
    for (const nodeData of Object.values(prompt)) {
      const inputs = (nodeData as any)?.inputs;
      if (!inputs || typeof inputs !== 'object') continue;
      for (const val of Object.values(inputs)) {
        if (typeof val === 'string') promptValues.add(val);
      }
    }

    // Upload files that are directly referenced OR inside a referenced folder
    const toUpload = new Set<string>();
    for (const uri of pending.keys()) {
      if (promptValues.has(uri)) {
        toUpload.add(uri);
        continue;
      }
      // Check if any prompt value is a folder prefix of this file
      for (const pv of promptValues) {
        const prefix = pv.endsWith('/') ? pv : pv + '/';
        if (uri.startsWith(prefix)) {
          toUpload.add(uri);
          break;
        }
      }
    }

    for (const uri of toUpload) {
      const file = pending.get(uri)!;
      const relativePath = uri.replace(/^session:\/\/uploads\//, '');
      await api.uploadFile(file, { relativePath });
      pending.delete(uri);
    }
  }, []);

  // ── Node context value (stable) ─────────────────────────────────────

  const onManualTrigger = useCallback(async (nodeId: string) => {
    const currentNodes = (reactFlow.getNodes() as TonoNode[]);
    const currentEdges = (reactFlow.getEdges() as TonoEdge[]);
    // Include ALL nodes (no excludeManualTrigger) so the save node is in the prompt
    const prompt = serializeExecutionGraph(currentNodes, currentEdges);
    if (!prompt || Object.keys(prompt).length === 0) return;
    setStatus({ text: 'Saving…', level: 'info' });
    try {
      await uploadPendingFiles(prompt);
      await api.runPrompt(prompt);
    } catch (err: any) {
      setStatus({ text: 'Save failed: ' + err.message, level: 'error' });
    }
  }, [reactFlow, uploadPendingFiles]);

  const openJournalTab = useCallback(() => {
    setHelpTabs((prev) => {
      if (prev.find((t) => t.label === 'Journal')) return prev;
      return [...prev, { label: 'Journal', type: 'journal', content: journalContentRef.current }];
    });
    setActiveHelpTab('Journal');
  }, []);

  // ── Add node from context menu ──────────────────────────────────────

  const addNode = useCallback((className: string, def: any) => {
    if (!contextMenu) return;
    if (className === 'TextNote') {
      openJournalTab();
      setContextMenu(null);
      return;
    }
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

    setNodes((ns) => [...ns, newNode as TonoNode]);

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
        const inputName = Object.entries(allInputs).find(([, spec]: [string, any]) => {
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
          } as any, eds));
        }
      } else {
        // Dragged from an input → connect from the first matching output on the new node
        const outputIdx = def.output.findIndex((type: string, idx: number) =>
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
          } as any, eds));
        }
      }
    }

    setContextMenu(null);
    scheduleAutoRun();
  }, [contextMenu, reactFlow, refreshFolderNodeOutputs, refreshLoadNodeOutputs, setNodes, setEdges]); // scheduleAutoRun stable; openJournalTab stable ([] deps)

  // ── Toolbar actions ─────────────────────────────────────────────────

  const runWorkflow = useCallback(async () => {
    // Read current state via functional ref to avoid stale closure
    const currentNodes = (reactFlow.getNodes() as TonoNode[]);
    const currentEdges = (reactFlow.getEdges() as TonoEdge[]);
    const prompt = serializeExecutionGraph(currentNodes, currentEdges);

    if (!prompt || Object.keys(prompt).length === 0) {
      setStatus({ text: 'Graph is empty — add some nodes first.', level: 'error' });
      return;
    }
    setStatus({ text: 'Running…', level: 'info' });
    try {
      await uploadPendingFiles(prompt);
      await api.runPrompt(prompt);
    } catch (err: any) {
      setStatus({ text: 'Failed: ' + err.message, level: 'error' });
    }
  }, [reactFlow, uploadPendingFiles]);

  // Debounced auto-run via ref to avoid dependency chains
  autoRunRef.current = () => {
    const currentNodes = (reactFlow.getNodes() as TonoNode[]);
    const currentEdges = (reactFlow.getEdges() as TonoEdge[]);
    const runnableNodes = getAutoRunnableNodes(currentNodes, currentEdges);

    // Don't run if any non-manual node has unconnected required data inputs
    // or any FILE_PICKER widget is empty
    for (const node of runnableNodes) {
      if (hasBlockingAutoRunInput(node, currentEdges)) return;
    }

    const prompt = serializeExecutionGraph(currentNodes, currentEdges, { excludeManualTrigger: true });
    if (!prompt || Object.keys(prompt).length === 0) return;
    setStatus({ text: 'Running…', level: 'info' });
    uploadPendingFiles(prompt).then(() => api.runPrompt(prompt)).catch((err) => {
      setStatus({ text: 'Failed: ' + err.message, level: 'error' });
    });
  };

  const onRuntimeValuesChange = useCallback((nodeId: string, patch: any, { scheduleRun = false } = {}) => {
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

  const initializeDynamicNodes = useCallback((nodesToInitialize: any[]) => {
    setTimeout(() => {
      nodesToInitialize.forEach((node: any) => {
        if (node.data.className === 'Folder' && node.data.widgetValues?.folder) {
          refreshFolderNodeOutputs(node.id, node.data.widgetValues.folder);
        }
      });
      nodesToInitialize.forEach((node: any) => {
        if (node.data.className === 'Image' || node.data.className === 'ImageDemo') {
          refreshLoadNodeOutputs(node.id);
        }
      });
      nodesToInitialize.forEach((node: any) => {
        if (node.data.className === 'Annotations' || node.data.className === 'Markup') {
          refreshAnnotationNodeOutputs(node.id);
        }
      });
      nodesToInitialize.forEach((node: any) => {
        reactFlow.updateNodeInternals(node.id);
      });
    }, 0);
  }, [reactFlow, refreshAnnotationNodeOutputs, refreshFolderNodeOutputs, refreshLoadNodeOutputs]);

  const pasteClipboardSelection = useCallback((clipboardText: string) => {
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
      ...existing.map((node) => ({ ...node, selected: false } as TonoNode)),
      ...pasted.nodes,
    ] as TonoNode[]));
    setEdges((existing) => [
      ...existing.map((edge) => ({ ...edge, selected: false } as TonoEdge)),
      ...pasted.edges,
    ] as TonoEdge[]);

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

  const resizeGroup = useCallback((groupId: string, size: any) => {
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

  const renameGroup = useCallback((groupId: string, label: string) => {
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

  const openHelp = useCallback(async (label: string) => {
    setHelpTabs((prev) => {
      if (prev.find((t) => t.label === label)) return prev;
      return [...prev, { label, content: null }];
    });
    setActiveHelpTab(label);
    const text = await api.getNodeDoc(label);
    setHelpTabs((prev) =>
      prev.map((t) =>
        t.label === label
          ? { ...t, content: text || '*No documentation available for this node.*' }
          : t,
      ),
    );
  }, []);

  const closeHelpTab = useCallback((label: string) => {
    setHelpTabs((prev) => {
      const next = prev.filter((t) => t.label !== label);
      setActiveHelpTab((cur) => {
        if (cur !== label) return cur;
        return next.length > 0 ? next[next.length - 1].label : null;
      });
      return next;
    });
  }, []);

  const updateTabContent = useCallback((label: string, content: string) => {
    if (label === 'Journal') journalContentRef.current = content;
    setHelpTabs((prev) => prev.map((t) => t.label === label ? { ...t, content } : t));
  }, []);

  const openDocByFilename = useCallback(async (filename: string) => {
    const title = filename.replace(/\.md$/i, '').replace(/[-_]/g, ' ').replace(/\b\w/g, (c: string) => c.toUpperCase());
    // If already open, just switch to it
    setHelpTabs((prev) => {
      if (prev.find((t) => t.label === title)) return prev;
      return [...prev, { label: title, content: null }];
    });
    setActiveHelpTab(title);
    try {
      const r = await fetch(`/help-docs/${encodeURIComponent(filename)}`);
      if (!r.ok) throw new Error('Not found');
      const doc = await r.json();
      setHelpTabs((prev) => prev.map((t) => t.label === title ? { ...t, content: doc.content } : t));
    } catch {
      setHelpTabs((prev) => prev.map((t) => t.label === title ? { ...t, content: `*Could not load ${filename}.*` } : t));
    }
  }, []);

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
    openHelp,
    getTableColumns: (_nodeId: string, _inputName: string): string[] => [],
    getMeasurementChoices: (_nodeId: string, _inputName: string): string[] => [],
  }), [onRuntimeValuesChange, onWidgetChange, openFileBrowser, onManualTrigger, renameGroup, resizeGroup, toggleGroupCollapse, ungroupGroup, executingNodeId, openHelp]);

  const clearGraph = useCallback(() => {
    setNodes([]);
    setEdges([]);
    nextIdRef.current = 1;
    setStatus({ text: 'Graph cleared.', level: 'info' });
  }, [setNodes, setEdges]);

  const applyWorkflowData = useCallback((data: any, { preservedPaths }: { preservedPaths?: Set<unknown> } = {}) => {
    const hydrated = hydrateWorkflowState(data, nodeDefsRef.current, { preservedPaths });
    setNodes(sortNodesForParentOrder(hydrated.nodes) as TonoNode[]);
    setEdges(hydrated.edges as TonoEdge[]);
    nextIdRef.current = hydrated.nextNodeId;
    journalContentRef.current = data.journalContent || '';
    if (journalContentRef.current) {
      setHelpTabs((prev) => {
        const existing = prev.find((t) => t.label === 'Journal');
        if (existing) return prev.map((t) => t.label === 'Journal' ? { ...t, content: journalContentRef.current } : t);
        return [...prev, { label: 'Journal', type: 'journal', content: journalContentRef.current }];
      });
      setActiveHelpTab('Journal');
    } else {
      setHelpTabs((prev) => prev.map((t) =>
        t.label === 'Journal' ? { ...t, content: '' } : t,
      ));
    }
    initializeDynamicNodes(hydrated.nodes);
  }, [initializeDynamicNodes, setNodes, setEdges]);

  const applyMaybePackedWorkflow = useCallback(async (data: any) => {
    if (data.packed && data.packedFiles) {
      setStatus({ text: 'Unpacking files…', level: 'info' });
      try {
        const { workflow, restoredPaths } = await unpackWorkflow(data);
        applyWorkflowData(workflow, { preservedPaths: restoredPaths });
        // Auto-run after packed workflow loads so all previews populate
        requestAnimationFrame(() => requestAnimationFrame(() => scheduleAutoRun()));
      } catch {
        // Unpack failed (e.g. stale session) — load the workflow without file restoration
        const { packedFiles: _, packed: __, ...cleanWorkflow } = data;
        applyWorkflowData(cleanWorkflow);
        setStatus({ text: 'Workflow loaded but packed files could not be restored. Re-browse your input files.', level: 'error' });
        return;
      }
    } else {
      applyWorkflowData(data);
    }
  }, [applyWorkflowData, scheduleAutoRun]);

  const loadDefaultWorkflow = useCallback(async () => {
    if (defaultWorkflowLoadAttemptedRef.current) return;
    defaultWorkflowLoadAttemptedRef.current = true;

    // Only auto-load the example workflow on first visit
    if (localStorage.getItem('tono_visited')) return;

    const graphHasContent = () => {
      const currentNodes = (reactFlow.getNodes() as TonoNode[]);
      const currentEdges = (reactFlow.getEdges() as TonoEdge[]);
      return currentNodes.length > 0 || currentEdges.length > 0;
    };

    if (graphHasContent()) return;

    try {
      const loaded = await loadDefaultWorkflowAsset();
      if (!loaded || graphHasContent()) return;

      await applyMaybePackedWorkflow(loaded.workflow);
      setStatus({ text: `Loaded default workflow from ${loaded.source}.`, level: 'info' });
      requestAnimationFrame(() => {
        requestAnimationFrame(() => scheduleAutoRun());
      });
    } catch (err: any) {
      setStatus({ text: 'Default workflow failed to load: ' + err.message, level: 'error' });
    }
  }, [applyMaybePackedWorkflow, reactFlow, scheduleAutoRun]);

  const loadExampleWorkflow = useCallback(async () => {
    try {
      const loaded = await loadDefaultWorkflowAsset();
      if (!loaded) {
        setStatus({ text: 'No example workflow found.', level: 'error' });
        return;
      }
      await applyMaybePackedWorkflow(loaded.workflow);
      setStatus({ text: 'Loaded example workflow.', level: 'info' });
    } catch (err: any) {
      setStatus({ text: 'Failed to load example workflow: ' + err.message, level: 'error' });
    }
  }, [applyMaybePackedWorkflow]);

  // ── Load node definitions ───────────────────────────────────────────

  useEffect(() => {
    api.getNodes().then((defs) => {
      nodeDefsRef.current = defs;
      setStatus({ text: `Loaded ${Object.keys(defs).length} nodes.`, level: 'info' });
      loadDefaultWorkflow();
    }).catch((err) => {
      setStatus({ text: 'Failed to load nodes: ' + err.message, level: 'error' });
    });

    // Load any .md files from frontend/public/ as help tabs
    const isFirstVisit = !localStorage.getItem('tono_visited');
    fetch('/help-docs')
      .then((r) => r.ok ? r.json() : [])
      .then((docs: any[]) => {
        if (!docs.length) return;
        const filtered = isFirstVisit ? docs : docs.filter((d: any) => d.title !== 'Getting Started');
        if (!filtered.length) return;
        setHelpTabs((prev) => {
          const existing = new Set(prev.map((t) => t.label));
          const newTabs = filtered.filter((d: any) => !existing.has(d.title)).map((d: any) => ({ label: d.title, content: d.content }));
          return newTabs.length ? [...prev, ...newTabs] : prev;
        });
        setActiveHelpTab((cur) => cur || filtered[0].title);
        localStorage.setItem('tono_visited', '1');
      })
      .catch(() => {});
  }, [loadDefaultWorkflow]);

  const stampLogoOnBlob = useCallback(async (blob: Blob) => {
    const [img, logo] = await Promise.all([blob, tonoIconUrl].map((src) => new Promise<HTMLImageElement>((resolve, reject) => {
      const el = new Image();
      el.onload = () => resolve(el);
      el.onerror = reject;
      el.src = typeof src === 'string' ? src : URL.createObjectURL(src);
    })));

    const canvas = document.createElement('canvas');
    canvas.width = img.naturalWidth;
    canvas.height = img.naturalHeight;
    const ctx = canvas.getContext('2d')!;
    ctx.drawImage(img, 0, 0);

    const margin = 16;
    const size = 64;
    if (img.naturalWidth >= size + margin * 2 && img.naturalHeight >= size + margin * 2) {
      const logoX = img.naturalWidth - size - margin;
      const logoY = img.naturalHeight - size - margin;
      const fontSize = Math.max(11, Math.round(size * 0.18));
      ctx.font = `500 ${fontSize}px system-ui, sans-serif`;
      ctx.fillStyle = 'rgba(255,255,255,0.7)';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'bottom';
      ctx.fillText('open with', logoX + size / 2, logoY - 6);
      ctx.drawImage(logo, logoX, logoY, size, size);
    }

    return new Promise<Blob | null>((resolve) => canvas.toBlob(resolve, 'image/png'));
  }, []);

  const captureWorkflowImage = useCallback(async () => {
    const viewportEl = document.querySelector('.react-flow__viewport') as HTMLElement | null;
    if (!viewportEl) throw new Error('Flow element not found');

    const allNodes = (reactFlow.getNodes() as TonoNode[]);
    if (allNodes.length === 0) throw new Error('No nodes to capture');

    const bounds = getRenderedNodeBounds(allNodes);
    if (!bounds) throw new Error('Could not determine rendered node bounds');
    const pad = 0.1;
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
    return await stampLogoOnBlob(blob) as Blob;
  }, [reactFlow]);

  const getWorkflowBlob = useCallback(async () => {
    const imageBlob = await captureWorkflowImage();
    const workflow = serializeWorkflowState(
      (reactFlow.getNodes() as TonoNode[]),
      (reactFlow.getEdges() as TonoEdge[]),
    ) as any;
    if (journalContentRef.current) workflow.journalContent = journalContentRef.current;
    return embedWorkflow(imageBlob, workflow);
  }, [reactFlow, captureWorkflowImage]);

  const saveBlobToFile = useCallback(async (blob: Blob, filename: string): Promise<string | null> => {
    if (window.pywebview?.api?.choose_save_workflow_png_path) {
      const requestedPath = await window.pywebview.api.choose_save_workflow_png_path(filename);
      if (!requestedPath) return null;
      const resp = await fetch(`/save-workflow-png?path=${encodeURIComponent(requestedPath)}`, {
        method: 'POST',
        headers: { 'Content-Type': 'image/png' },
        body: blob,
      });
      if (!resp.ok) throw new Error(await resp.text() || `Save failed (${resp.status})`);
      const { path: savedPath } = await resp.json();
      return savedPath || null;
    }

    if ('showSaveFilePicker' in window) {
      try {
        const handle = await window.showSaveFilePicker!({
          suggestedName: filename,
          types: [{ description: 'PNG image', accept: { 'image/png': ['.png'] } }],
        });
        const writable = await handle.createWritable();
        await writable.write(blob);
        await writable.close();
        return filename;
      } catch (err: any) {
        if (err?.name === 'AbortError') return null;
        throw err;
      }
    }

    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    setTimeout(() => URL.revokeObjectURL(a.href), 1000);
    return filename;
  }, []);

  const saveWorkflow = useCallback(async () => {
    setStatus({ text: 'Saving…', level: 'info' });
    try {
      const finalBlob = await getWorkflowBlob();
      const saved = await saveBlobToFile(finalBlob, 'workflow.png');
      if (!saved) {
        setStatus({ text: 'Save cancelled.', level: 'info' });
      } else {
        setStatus({ text: `Workflow saved to ${saved}.`, level: 'info' });
      }
    } catch (err: any) {
      setStatus({ text: 'Save failed: ' + err.message, level: 'error' });
    }
  }, [getWorkflowBlob, saveBlobToFile]);

  const savePackedWorkflow = useCallback(async () => {
    setStatus({ text: 'Packing files…', level: 'info' });
    try {
      const imageBlob = await captureWorkflowImage();
      const allNodes = (reactFlow.getNodes() as TonoNode[]);
      const workflow: any = serializeWorkflowState(allNodes, (reactFlow.getEdges() as TonoEdge[]));
      if (journalContentRef.current) workflow.journalContent = journalContentRef.current;

      const packed = await packWorkflow(workflow, nodeDefsRef.current, (done: number, total: number) => {
        setStatus({ text: `Packing files… (${done}/${total})`, level: 'info' });
      });
      const finalBlob = await embedWorkflow(imageBlob, packed as any);

      const saved = await saveBlobToFile(finalBlob, 'workflow-packed.png');
      if (!saved) {
        setStatus({ text: 'Save cancelled.', level: 'info' });
      } else {
        setStatus({ text: `Packed workflow saved to ${saved}.`, level: 'info' });
      }
    } catch (err: any) {
      setStatus({ text: 'Pack failed: ' + err.message, level: 'error' });
    }
  }, [reactFlow, captureWorkflowImage, saveBlobToFile]);

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
    input.onchange = async (e: Event) => {
      const file = (e.target as HTMLInputElement)?.files?.[0];
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
          data = sanitizeJson(JSON.parse(await file.text()));
        }
        await applyMaybePackedWorkflow(data);
        setStatus({ text: 'Workflow loaded.', level: 'info' });
      } catch (err: any) {
        setStatus({ text: 'Failed to load workflow: ' + (err?.message || 'unknown error'), level: 'error' });
      }
    };
    input.click();
  }, [applyMaybePackedWorkflow]);

  const uploadPlugin = useCallback(() => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.py';
    input.onchange = async (e: Event) => {
      const file = (e.target as HTMLInputElement)?.files?.[0];
      if (!file) return;
      setStatus({ text: 'Uploading plugin…', level: 'info' });
      try {
        await api.uploadPlugin(file);
        // Node list refresh is handled by the nodes_updated WebSocket message.
      } catch (err: any) {
        setStatus({ text: err.message, level: 'error' });
      }
    };
    input.click();
  }, []);

  // ── Drag-and-drop workflow image loading ───────────────────────────

  const onDropFile = useCallback(async (event: React.DragEvent) => {
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
      await applyMaybePackedWorkflow(data);
      setStatus({ text: 'Workflow loaded from image.', level: 'info' });
    } catch (err: any) {
      setStatus({ text: 'Failed to load: ' + err.message, level: 'error' });
    }
  }, [applyMaybePackedWorkflow]);

  const onDragOver = useCallback((event: React.DragEvent) => {
    if (event.dataTransfer?.types?.includes('Files')) {
      event.preventDefault();
      event.dataTransfer.dropEffect = 'copy';
    }
  }, []);

  const onNodeDragStart = useCallback((event: any, node: any) => {
    activeDragNodeIdRef.current = String(node.id);
    dragStateRef.current = null;
    if (!(event.ctrlKey || event.metaKey)) {
      duplicateDragRef.current = null;
      const currentNodes = (reactFlow.getNodes() as TonoNode[]);
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

    const currentNodes = (reactFlow.getNodes() as TonoNode[]);
    const draggedNodes = node.selected
      ? currentNodes.filter((candidate) => candidate.selected)
      : currentNodes.filter((candidate) => candidate.id === node.id);
    if (draggedNodes.length === 0) return;

    const draggedIds = draggedNodes.map((candidate) => String(candidate.id));
    const payload = buildNodeClipboardPayloadForIds(
      currentNodes,
      (reactFlow.getEdges() as TonoEdge[]),
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
      ...existing.map((candidate) => ({ ...candidate, selected: false } as TonoNode)),
      ...duplicated.nodes,
    ] as TonoNode[]));
    setEdges((existing) => [
      ...existing.map((edge) => ({ ...edge, selected: false } as TonoEdge)),
      ...duplicated.edges,
    ] as TonoEdge[]);

    initializeDynamicNodes(duplicated.nodes);
  }, [initializeDynamicNodes, reactFlow, setEdges, setNodes]);

  const onNodeDrag = useCallback((event: any, node: any) => {
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

    const currentNodes = (reactFlow.getNodes() as TonoNode[]);
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
    const structureChanged = false;

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
        touchedGroupIds.forEach((groupId: any) => {
          if (groupId) refreshGroupNode(groupId as string, nextNodes, (reactFlow.getEdges() as TonoEdge[]));
        });
      }, 0);
    }
  }, [reactFlow, refreshGroupNode, setNodes]);

  const onNodeDragStop = useCallback((event: any, node: any) => {
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

    const currentNodes = (reactFlow.getNodes() as TonoNode[]);
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
      const anchorSize = anchorNode ? getNodeSize(anchorNode) : null;
      const intendedAnchorCenter = anchorNode && intendedAnchorAbsolute && anchorSize
        ? {
          x: intendedAnchorAbsolute.x + anchorSize.width / 2,
          y: intendedAnchorAbsolute.y + anchorSize.height / 2,
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
          const { width, height } = getNodeSize(candidate);
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
      touchedGroupIds.forEach((groupId: any) => {
        if (groupId) refreshGroupNode(groupId as string, nextNodes, (reactFlow.getEdges() as TonoEdge[]));
      });
    }, 0);
  }, [reactFlow, refreshGroupNode, scheduleAutoRun, setNodes]);

  // ── Keyboard shortcut ───────────────────────────────────────────────

  // Close floating menu on outside click
  const floatingMenuRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!menuOpen) return;
    const handler = (e: MouseEvent) => {
      if (floatingMenuRef.current && !floatingMenuRef.current.contains(e.target as HTMLElement)) {
        closeMenu();
      }
    };
    document.addEventListener('pointerdown', handler);
    return () => document.removeEventListener('pointerdown', handler);
  }, [menuOpen]);

  // Auto-dismiss status toast after 5 seconds with close animation
  const [toastClosing, setToastClosing] = useState(false);
  useEffect(() => {
    if (!status.text) return;
    setToastClosing(false);
    const fadeTimer = setTimeout(() => setToastClosing(true), 4700);
    const removeTimer = setTimeout(() => { setToastClosing(false); setStatus({ text: '', level: 'info' }); }, 5000);
    return () => { clearTimeout(fadeTimer); clearTimeout(removeTimer); };
  }, [status]);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
        e.preventDefault();
        runWorkflow();
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [runWorkflow]);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (!(e.ctrlKey || e.metaKey) || e.key !== 'z') return;
      if (isEditableTarget(e.target)) return;
      e.preventDefault();
      if (e.shiftKey) {
        if (undoRedo.redo(setNodes as (n: TonoNode[]) => void, setEdges as (e: TonoEdge[]) => void, nextIdRef, () => (reactFlow.getNodes() as TonoNode[]), () => (reactFlow.getEdges() as TonoEdge[]))) {
          setStatus({ text: 'Redo.', level: 'info' });
        }
      } else {
        if (undoRedo.undo(setNodes as (n: TonoNode[]) => void, setEdges as (e: TonoEdge[]) => void, nextIdRef, () => (reactFlow.getNodes() as TonoNode[]), () => (reactFlow.getEdges() as TonoEdge[]))) {
          setStatus({ text: 'Undo.', level: 'info' });
        }
      }
    };
    window.addEventListener('keydown', handler, true);
    return () => window.removeEventListener('keydown', handler, true);
  }, [reactFlow, setNodes, setEdges, undoRedo]);

  useEffect(() => {
    const handleCopy = (event: ClipboardEvent) => {
      if (isEditableTarget(event.target)) return;

      const payload = buildNodeClipboardPayload((reactFlow.getNodes() as TonoNode[]), (reactFlow.getEdges() as TonoEdge[]));
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

    const handlePaste = (event: ClipboardEvent) => {
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

  const onPaneContextMenu = useCallback((event: any) => {
    event.preventDefault();
    if (performance.now() < suppressPaneContextMenuUntilRef.current) {
      suppressPaneContextMenuUntilRef.current = 0;
      return;
    }
    setContextMenu({ x: event.clientX, y: event.clientY });
  }, []);

  const onFlowContainerPointerDown = useCallback((event: React.PointerEvent) => {
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

  const onFlowContainerContextMenuCapture = useCallback((event: React.SyntheticEvent) => {
    if (canvasRightZoomRef.current?.moved || performance.now() < suppressPaneContextMenuUntilRef.current) {
      event.preventDefault();
      event.stopPropagation();
    }
  }, []);

  const onFlowContainerWheel = useCallback(() => {
    const container = flowContainerRef.current;
    if (!container) return;
    container.classList.add('is-panning');
    if (panTimerRef.current) clearTimeout(panTimerRef.current);
    panTimerRef.current = setTimeout(() => {
      container.classList.remove('is-panning');
    }, 150);
  }, []);

  useEffect(() => {
    const handlePointerMove = (event: PointerEvent) => {
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

    const finishPointerInteraction = (event: PointerEvent) => {
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

    const handlePointerDown = (event: PointerEvent) => {
      if ((event.target as Element)?.closest?.('.context-menu')) return;
      setContextMenu(null);
    };

    window.addEventListener('pointerdown', handlePointerDown, true);
    return () => window.removeEventListener('pointerdown', handlePointerDown, true);
  }, [contextMenu]);

  const selectedNodeCount = nodes.filter((node) => node.selected).length;

  // ── Render ──────────────────────────────────────────────────────────

  return (
    <NodeContext.Provider value={contextValue as any}>
      <div className="app-container">
        {/* Floating menu */}
        <div className="floating-menu" ref={floatingMenuRef}>
          <button className="floating-menu-toggle" onClick={() => menuOpen ? closeMenu() : setMenuOpen(true)} title="Menu">
            <img src="/favicon.svg" alt="tono" className="floating-menu-logo" />
          </button>
          {(menuOpen || menuClosing) && (
            <div className={`floating-menu-dropdown${menuClosing ? ' closing' : ''}`}>
              <button className="btn btn-primary" onClick={() => { runWorkflow(); closeMenu(); }} title="Run workflow (Ctrl+Enter)">
                ▶ Run
              </button>
              <button className="btn" onClick={() => { clearGraph(); closeMenu(); }} title="Clear graph">
                ✕ Clear
              </button>
              <hr className="floating-menu-divider" />
              <button className="btn" onClick={() => { saveWorkflow(); closeMenu(); }} title="Save workflow as PNG">
                ⤓ Save
              </button>
              <button className="btn" onClick={() => { savePackedWorkflow(); closeMenu(); }} title="Save packed workflow (with files)">
                ⊞ Pack
              </button>
              <button className="btn" onClick={() => { loadWorkflow(); closeMenu(); }} title="Load workflow (JSON or PNG)">
                ⤒ Load
              </button>
              <button className="btn" onClick={() => { copySnapshot(); closeMenu(); }} title="Copy workflow screenshot to clipboard">
                ⎘ Snapshot
              </button>
              {window.pywebview && (
                <button className="btn" onClick={() => { uploadPlugin(); closeMenu(); }} title="Upload a plugin (.py)">
                  ⊕ Plugin
                </button>
              )}
              <hr className="floating-menu-divider" />
              <button className="btn" onClick={() => { loadExampleWorkflow(); closeMenu(); }} title="Load example workflow">
                ◈ Example
              </button>
              <button className="btn" onClick={() => { openJournalTab(); closeMenu(); }} title="Open journal">
                ✎ Journal
              </button>
              <button className="btn" onClick={() => { openDocByFilename('getting-started.md'); closeMenu(); }} title="Getting started guide">
                ? Help
              </button>
              {updateInfo && (
                <>
                  <hr className="floating-menu-divider" />
                  <a className="btn floating-menu-update" href={updateInfo.url} target="_blank" rel="noopener noreferrer">
                    ↑ Update to {updateInfo.latest}
                  </a>
                </>
              )}
            </div>
          )}
        </div>

        {/* Status toast */}
        {(status.text || toastClosing) && (
          <div className={`status-toast ${status.level}${toastClosing ? ' closing' : ''}`}>{status.text}</div>
        )}

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
              nodeColor={(n: any) => {
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
      <HelpPanelManager
        tabs={helpTabs as any}
        activeTab={activeHelpTab as any}
        onTabSelect={setActiveHelpTab}
        onTabClose={closeHelpTab}
        onTabContentChange={updateTabContent}
        onOpenJournal={openJournalTab}
        onOpenDoc={openDocByFilename}
      />
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
