import React, {
  useState, useCallback, useEffect, useRef, useMemo,
} from 'react';
import {
  ReactFlow, Background, Controls, MiniMap,
  useNodesState, useEdgesState, addEdge, useReactFlow,
  ReactFlowProvider, getViewportForBounds,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

import CustomNode, { NodeContext } from './CustomNode';
import FileBrowser from './FileBrowser';
import * as api from './api';
import { toBlob } from 'html-to-image';
import { embedWorkflow, extractWorkflow } from './pngMetadata';
import { hydrateWorkflowState } from './workflowHydration';
import { serializeWorkflowState } from './workflowSerialization';

// ── Constants ─────────────────────────────────────────────────────────

const DATA_TYPES = new Set([
  'DATA_FIELD', 'IMAGE', 'LINE', 'MEASURE_TABLE', 'RECORD_TABLE', 'ANY_TABLE',
  'COORD', 'STATS_SOURCE', 'VALUE_SOURCE',
]);

const SOCKET_COMPATIBILITY = {
  STATS_SOURCE: new Set(['DATA_FIELD', 'IMAGE', 'LINE', 'RECORD_TABLE']),
  ANY_TABLE: new Set(['MEASURE_TABLE', 'RECORD_TABLE']),
  VALUE_SOURCE: new Set(['FLOAT', 'MEASURE_TABLE']),
};

const TYPE_COLORS = {
  DATA_FIELD: '#ff002f',
  IMAGE:      '#00ff08a0',
  LINE:       '#ffbe5c',
  MEASURE_TABLE:'#35e2fd',
  RECORD_TABLE:'#fbbf24',
  ANY_TABLE:  '#67e8f9',
  COORD:      '#e91ed1',
  FLOAT:      '#7dd3fc',
  STATS_SOURCE:'#c084fc',
  VALUE_SOURCE:'#60a5fa',
};

const NODE_TYPES = { custom: CustomNode };

// ── Handle ID helpers ─────────────────────────────────────────────────

function getHandleType(handleId) {
  return handleId.split('::')[2];
}

function getInputName(handleId) {
  return handleId.split('::')[1];
}

function getOutputSlot(handleId) {
  return parseInt(handleId.split('::')[1], 10);
}

function socketTypesCompatible(sourceType, targetType) {
  if (sourceType === targetType) return true;
  const accepted = SOCKET_COMPATIBILITY[targetType];
  return !!accepted?.has(sourceType);
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

// ── Graph serialisation → backend prompt format ───────────────────────

function serializeGraph(nodes, edges, { excludeManualTrigger = false } = {}) {
  const prompt = {};

  for (const node of nodes) {
    const { className, definition, widgetValues } = node.data;
    if (!definition) continue;
    if (excludeManualTrigger && definition.manual_trigger) continue;

    const inputs = {};

    // Widget (scalar) values
    const required = definition.input.required || {};
    for (const [name, spec] of Object.entries(required)) {
      const [type] = Array.isArray(spec) ? spec : [spec];
      if (DATA_TYPES.has(type)) continue; // socket, handled via edges
      if (type === 'BUTTON') continue; // UI-only widget, not a backend input
      if (widgetValues[name] !== undefined) {
        inputs[name] = widgetValues[name];
      }
    }

    // Connected (socket) inputs from edges
    const incoming = edges.filter((e) => e.target === node.id);
    for (const edge of incoming) {
      const inputName = getInputName(edge.targetHandle);
      const outputSlot = getOutputSlot(edge.sourceHandle);
      inputs[inputName] = [edge.source, outputSlot];
    }

    prompt[node.id] = { class_type: className, inputs };
  }

  return prompt;
}

// ── Context menu component ────────────────────────────────────────────

function ContextMenu({ x, y, nodeDefs, onAdd, onClose, filterType, filterDirection }) {
  const [openCat, setOpenCat] = useState(null);
  const [search, setSearch] = useState('');
  const menuRef = useRef(null);
  const [menuPos, setMenuPos] = useState({ x, y });
  const subMenuRef = useRef(null);
  const [subPos, setSubPos] = useState({ x: 0, y: 0 });
  const catRowRefs = useRef({});

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
            const [type] = Array.isArray(spec) ? spec : [spec];
            return socketTypesCompatible(filterType, type);
          });
          if (!hasMatch) continue;
        } else {
          if (!def.output.some((type) => socketTypesCompatible(type, filterType))) continue;
        }
      }
      const cat = def.category || 'uncategorized';
      if (!cats[cat]) cats[cat] = [];
      cats[cat].push({ className, def });
    }
    return cats;
  }, [nodeDefs, filterType, filterDirection]);

  // Flat filtered list for search
  const searchResults = useMemo(() => {
    if (!search.trim()) return null;
    const q = search.toLowerCase();
    const results = [];
    for (const items of Object.values(categories)) {
      for (const { className, def } of items) {
        const name = (def.display_name || className).toLowerCase();
        if (name.includes(q)) results.push({ className, def });
      }
    }
    return results;
  }, [search, categories]);

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

  if (Object.keys(categories).length === 0) {
    return (
      <div className="context-menu" ref={menuRef} style={{ left: menuPos.x, top: menuPos.y }} onClick={(e) => e.stopPropagation()}>
        <div className="context-item" style={{ color: '#64748b' }}>No compatible nodes</div>
      </div>
    );
  }

  const catNames = Object.keys(categories).sort();

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
            autoFocus
          />
        </div>

        {searchResults ? (
          <div className="ctx-list">
            {searchResults.length === 0 ? (
              <div className="context-item" style={{ color: '#64748b' }}>No matches</div>
            ) : (
              searchResults.map(({ className, def }) => (
                <div
                  key={className}
                  className="context-item"
                  onClick={() => { onAdd(className, def); onClose(); }}
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
      {openCat && categories[openCat] && (
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
          {categories[openCat].map(({ className, def }) => (
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
  const [fileBrowserCb, setFileBrowserCb] = useState(null);

  const nodeDefsRef = useRef({});
  const nextIdRef = useRef(1);
  const autoRunTimer = useRef(null);
  const autoRunRef = useRef(null);
  const reactFlow = useReactFlow();

  // ── Load node definitions ───────────────────────────────────────────

  useEffect(() => {
    api.getNodes().then((defs) => {
      nodeDefsRef.current = defs;
      setStatus({ text: `Loaded ${Object.keys(defs).length} nodes.`, level: 'info' });
    }).catch((err) => {
      setStatus({ text: 'Failed to load nodes: ' + err.message, level: 'error' });
    });
  }, []);

  // ── WebSocket ───────────────────────────────────────────────────────

  const updateNodeData = useCallback((nodeId, patch) => {
    setNodes((ns) => ns.map((n) =>
      n.id !== nodeId ? n : { ...n, data: { ...n.data, ...patch } }
    ));
  }, [setNodes]);

  useEffect(() => {
    api.setMessageHandler((msg) => {
      console.log('[argonode] WS:', msg.type, msg.data?.node_id || msg.data?.node || '');
      switch (msg.type) {
        case 'execution_start':
          setNodes((ns) => ns.map((n) => ({
            ...n,
            data: { ...n.data, processingTimeMs: null },
          })));
          setStatus({ text: 'Running workflow…', level: 'info' });
          break;
        case 'executing':
          setStatus({ text: `Executing node ${msg.data.node}…`, level: 'info' });
          break;
        case 'execution_complete':
          setStatus({ text: 'Done.', level: 'info' });
          break;
        case 'execution_error':
          setStatus({ text: 'Error: ' + msg.data.message, level: 'error' });
          console.error('[argonode] execution error', msg.data);
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
          updateNodeData(msg.data.node_id, { overlay: msg.data.overlay });
          break;
        case 'node_warning':
          updateNodeData(msg.data.node_id, { warning: msg.data.message });
          break;
      }
    });
    api.initWS();
    return () => api.closeWS();
  }, [updateNodeData]);

  // ── Connection handling ─────────────────────────────────────────────

  const isValidConnection = useCallback((connection) => {
    const srcType = getHandleType(connection.sourceHandle);
    const tgtType = getHandleType(connection.targetHandle);
    return socketTypesCompatible(srcType, tgtType);
  }, []);

  const onConnect = useCallback((params) => {
    const type = getHandleType(params.sourceHandle);
    const color = TYPE_COLORS[type] || '#999';

    setEdges((eds) => {
      // Enforce single connection per input handle
      const filtered = eds.filter(
        (e) => !(e.target === params.target && e.targetHandle === params.targetHandle)
      );
      return addEdge(
        { ...params, style: { stroke: color, strokeWidth: 2 } },
        filtered
      );
    });
    scheduleAutoRun();
  }, [setEdges]);

  // ── Drop-on-blank: open filtered context menu ──────────────────────

  const onConnectEnd = useCallback((event, connectionState) => {
    // If the connection was completed (dropped on a valid handle), do nothing
    if (connectionState.isValid) return;

    const fromHandle = connectionState.fromHandle;
    if (!fromHandle || !fromHandle.id) return;

    const { clientX, clientY } = 'changedTouches' in event ? event.changedTouches[0] : event;
    const handleType = getHandleType(fromHandle.id);

    setContextMenu({
      x: clientX,
      y: clientY,
      filterType: handleType,
      filterDirection: fromHandle.type,
      pendingNodeId: fromHandle.nodeId,
      pendingHandleId: fromHandle.id,
      pendingHandleType: fromHandle.type,
    });
  }, []);

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

    // If this is a filename/name change on a LoadFile/LoadDemo node, fetch channels
    if ((name === 'filename' || name === 'name') && value) {
      const node = reactFlow.getNode(nodeId);
      if (node && (node.data.className === 'LoadFile' || node.data.className === 'LoadDemo')) {
        api.getChannels(value).then((channels) => {
          setNodes((prev) => prev.map((n) => {
            if (n.id !== nodeId) return n;
            return {
              ...n,
              data: {
                ...n.data,
                definition: {
                  ...n.data.definition,
                  output: channels.map((c) => c.type),
                  output_name: channels.map((c) => c.name),
                },
              },
            };
          }));
          reactFlow.updateNodeInternals(nodeId);
        });
      }
    }

    scheduleAutoRun();
  }, [setNodes]); // scheduleAutoRun is stable (no deps)

  // ── File browser ────────────────────────────────────────────────────

  const openFileBrowser = useCallback((callback) => {
    // Use native file picker when running inside pywebview (desktop app)
    if (window.pywebview?.api?.open_file_dialog) {
      window.pywebview.api.open_file_dialog().then((path) => {
        if (path) callback(path);
      });
      return;
    }
    setFileBrowserCb(() => callback);
  }, []);

  // ── Node context value (stable) ─────────────────────────────────────

  const onManualTrigger = useCallback((nodeId) => {
    const currentNodes = reactFlow.getNodes();
    const currentEdges = reactFlow.getEdges();
    // Include ALL nodes (no excludeManualTrigger) so the save node is in the prompt
    const prompt = serializeGraph(currentNodes, currentEdges);
    if (!prompt || Object.keys(prompt).length === 0) return;
    setStatus({ text: 'Saving…', level: 'info' });
    api.runPrompt(prompt).catch((err) => {
      setStatus({ text: 'Save failed: ' + err.message, level: 'error' });
    });
  }, [reactFlow]);

  const contextValue = useMemo(() => ({
    onWidgetChange,
    openFileBrowser,
    onManualTrigger,
  }), [onWidgetChange, openFileBrowser, onManualTrigger]);

  // ── Add node from context menu ──────────────────────────────────────

  const addNode = useCallback((className, def) => {
    if (!contextMenu) return;
    const position = reactFlow.screenToFlowPosition({
      x: contextMenu.x,
      y: contextMenu.y,
    });

    // Build default widget values
    const widgetValues = {};
    const required = def.input.required || {};
    for (const [name, spec] of Object.entries(required)) {
      const [type, opts] = Array.isArray(spec) ? spec : [spec, {}];
      if (DATA_TYPES.has(type)) continue;
      if (type === 'BUTTON') continue;
      if (Array.isArray(type)) {
        widgetValues[name] = type[0]; // combo default = first option
      } else {
        widgetValues[name] = opts?.default ?? '';
      }
    }

    const newNodeId = String(nextIdRef.current++);
    const newNode = {
      id: newNodeId,
      type: 'custom',
      position,
      dragHandle: '.drag-handle',
      data: {
        label: def.display_name || className,
        className,
        definition: def,
        widgetValues,
        previewImage: null,
        tableRows: null,
        meshData: null,
        overlay: null,
        scalarValue: null,
        processingTimeMs: null,
      },
    };

    setNodes((ns) => [...ns, newNode]);

    // For LoadFile/LoadDemo, auto-fetch channels for the default value
    if (className === 'LoadDemo' && widgetValues.name) {
      api.getChannels(widgetValues.name).then((channels) => {
        setNodes((prev) => prev.map((n) => {
          if (n.id !== newNodeId) return n;
          return {
            ...n,
            data: {
              ...n.data,
              definition: {
                ...n.data.definition,
                output: channels.map((c) => c.type),
                output_name: channels.map((c) => c.name),
              },
            },
          };
        }));
        reactFlow.updateNodeInternals(newNodeId);
      });
    }

    // Auto-connect if this was triggered by dropping a connection on blank space
    if (contextMenu.pendingHandleId) {
      const filterType = contextMenu.filterType;

      if (contextMenu.pendingHandleType === 'source') {
        // Dragged from an output → connect to the first matching input on the new node
        const allInputs = { ...(def.input.required || {}), ...(def.input.optional || {}) };
        const inputName = Object.entries(allInputs).find(([, spec]) => {
          const [type] = Array.isArray(spec) ? spec : [spec];
          return socketTypesCompatible(filterType, type);
        })?.[0];
        if (inputName) {
          const targetType = (() => {
            const spec = allInputs[inputName];
            const [type] = Array.isArray(spec) ? spec : [spec];
            return type;
          })();
          const targetHandle = `input::${inputName}::${targetType}`;
          const color = TYPE_COLORS[filterType] || '#999';
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
        const outputIdx = def.output.findIndex((type) => socketTypesCompatible(type, filterType));
        if (outputIdx !== -1) {
          const outputType = def.output[outputIdx];
          const sourceHandle = `output::${outputIdx}::${outputType}`;
          const color = TYPE_COLORS[outputType] || '#999';
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
  }, [contextMenu, reactFlow, setNodes, setEdges]);

  // ── Toolbar actions ─────────────────────────────────────────────────

  const runWorkflow = useCallback(async () => {
    // Read current state via functional ref to avoid stale closure
    const currentNodes = reactFlow.getNodes();
    const currentEdges = reactFlow.getEdges();
    const prompt = serializeGraph(currentNodes, currentEdges);

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

    // Don't run if any non-manual node has unconnected required data inputs
    // or any FILE_PICKER widget is empty
    for (const node of currentNodes) {
      const def = node.data?.definition;
      if (!def || def.manual_trigger) continue; // skip manual-trigger nodes
      const required = def.input.required || {};
      for (const [name, spec] of Object.entries(required)) {
        const [type] = Array.isArray(spec) ? spec : [spec];
        if (type === 'FILE_PICKER') {
          if (!node.data.widgetValues?.[name]) return; // no file selected, skip
          continue;
        }
        if (!DATA_TYPES.has(type)) continue;
        const hasEdge = currentEdges.some(
          (e) => e.target === node.id && getInputName(e.targetHandle) === name
        );
        if (!hasEdge) return; // incomplete graph, skip auto-run
      }
    }

    const prompt = serializeGraph(currentNodes, currentEdges, { excludeManualTrigger: true });
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

  const clearGraph = useCallback(() => {
    setNodes([]);
    setEdges([]);
    nextIdRef.current = 1;
    setStatus({ text: 'Graph cleared.', level: 'info' });
  }, [setNodes, setEdges]);

  const applyWorkflowData = useCallback((data) => {
    const hydrated = hydrateWorkflowState(data, nodeDefsRef.current);
    setNodes(hydrated.nodes);
    setEdges(hydrated.edges);
    nextIdRef.current = hydrated.nextNodeId;
  }, [setNodes, setEdges]);

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

    const blob = await captureViewportBlob(viewportEl, {
      backgroundColor: '#1a1a1a',
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

  // ── Context menu ────────────────────────────────────────────────────

  const onPaneContextMenu = useCallback((event) => {
    event.preventDefault();
    setContextMenu({ x: event.clientX, y: event.clientY });
  }, []);

  useEffect(() => {
    if (!contextMenu) return undefined;

    const handlePointerDown = (event) => {
      if (event.target.closest('.context-menu')) return;
      setContextMenu(null);
    };

    window.addEventListener('pointerdown', handlePointerDown, true);
    return () => window.removeEventListener('pointerdown', handlePointerDown, true);
  }, [contextMenu]);

  // ── Render ──────────────────────────────────────────────────────────

  return (
    <NodeContext.Provider value={contextValue}>
      <div className="app-container">
        {/* Toolbar */}
        <div id="toolbar">
          <span id="app-title">argonode</span>

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
          </div>

          <div className={`status-bar ${status.level}`}>{status.text}</div>
        </div>

        {/* React Flow canvas */}
        <div className="flow-container" onDrop={onDropFile} onDragOver={onDragOver}>
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onConnectEnd={onConnectEnd}
            isValidConnection={isValidConnection}
            nodeTypes={NODE_TYPES}
            onPaneContextMenu={onPaneContextMenu}
            colorMode="dark"
            deleteKeyCode={['Backspace', 'Delete']}
            defaultEdgeOptions={{ type: 'default' }}
          >
            <Background />
            <Controls />
            <MiniMap
              nodeColor={(n) => {
                const cat = n.data?.definition?.category;
                const colors = {
                  io: '#37474f', filters: '#1a237e', level: '#1b5e20',
                  analysis: '#4a148c', particles: '#bf360c', display: '#212121',
                };
                return colors[cat] || '#333';
              }}
            />
          </ReactFlow>

          {contextMenu && (
            <ContextMenu
              x={contextMenu.x}
              y={contextMenu.y}
              nodeDefs={nodeDefsRef.current}
              onAdd={addNode}
              onClose={() => setContextMenu(null)}
              filterType={contextMenu.filterType}
              filterDirection={contextMenu.filterDirection}
            />
          )}
        </div>

        {/* File browser modal */}
        {fileBrowserCb && (
          <FileBrowser
            onSelect={(path) => { fileBrowserCb(path); setFileBrowserCb(null); }}
            onClose={() => setFileBrowserCb(null)}
          />
        )}
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
