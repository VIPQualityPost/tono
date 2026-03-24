import React, {
  useState, useCallback, useEffect, useRef, useMemo,
} from 'react';
import {
  ReactFlow, Background, Controls, MiniMap,
  useNodesState, useEdgesState, addEdge, useReactFlow,
  ReactFlowProvider, getNodesBounds, getViewportForBounds,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

import CustomNode, { NodeContext } from './CustomNode';
import FileBrowser from './FileBrowser';
import * as api from './api';
import { toBlob } from 'html-to-image';
import { embedWorkflow, extractWorkflow } from './pngMetadata';
import { serializeWorkflowState } from './workflowSerialization';

// ── Constants ─────────────────────────────────────────────────────────

const DATA_TYPES = new Set(['DATA_FIELD', 'IMAGE', 'LINE', 'TABLE', 'COORD']);

const TYPE_COLORS = {
  DATA_FIELD: '#ff002f',
  IMAGE:      '#00ff08a0',
  LINE:       '#ffbe5c',
  TABLE:      '#35e2fd',
  COORD:      '#e91ed1',
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

function blobToDataUrl(blob) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onloadend = () => resolve(reader.result);
    reader.onerror = () => reject(reader.error || new Error('Failed to read file'));
    reader.readAsDataURL(blob);
  });
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
    const dataUrl = img.currentSrc || img.src;
    if (!dataUrl || !img.parentNode) continue;
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

function serializeGraph(nodes, edges) {
  const prompt = {};

  for (const node of nodes) {
    const { className, definition, widgetValues } = node.data;
    if (!definition) continue;

    const inputs = {};

    // Widget (scalar) values
    const required = definition.input.required || {};
    for (const [name, spec] of Object.entries(required)) {
      const [type] = Array.isArray(spec) ? spec : [spec];
      if (DATA_TYPES.has(type)) continue; // socket, handled via edges
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
  // Group by category, optionally filtering to compatible nodes
  const categories = {};
  for (const [className, def] of Object.entries(nodeDefs)) {
    // If filtering: only show nodes with a matching input or output
    if (filterType && filterDirection) {
      if (filterDirection === 'source') {
        // Dragged from an output — show nodes that have a matching INPUT
        const req = def.input.required || {};
        const opt = def.input.optional || {};
        const allInputs = { ...req, ...opt };
        const hasMatch = Object.values(allInputs).some((spec) => {
          const [type] = Array.isArray(spec) ? spec : [spec];
          return type === filterType;
        });
        if (!hasMatch) continue;
      } else {
        // Dragged from an input — show nodes that have a matching OUTPUT
        if (!def.output.includes(filterType)) continue;
      }
    }

    const cat = def.category || 'uncategorized';
    if (!categories[cat]) categories[cat] = [];
    categories[cat].push({ className, def });
  }

  if (Object.keys(categories).length === 0) {
    return (
      <div className="context-menu" style={{ left: x, top: y }} onClick={(e) => e.stopPropagation()}>
        <div className="context-item" style={{ color: '#64748b' }}>No compatible nodes</div>
      </div>
    );
  }

  return (
    <div
      className="context-menu"
      style={{ left: x, top: y }}
      onClick={(e) => e.stopPropagation()}
    >
      {Object.entries(categories).map(([cat, items]) => (
        <div key={cat}>
          <div className="context-category">{cat}</div>
          {items.map(({ className, def }) => (
            <div
              key={className}
              className="context-item"
              onClick={() => { onAdd(className, def); onClose(); }}
            >
              {def.display_name || className}
            </div>
          ))}
        </div>
      ))}
    </div>
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
        case 'mesh3d':
          updateNodeData(msg.data.node_id, { meshData: msg.data.mesh });
          break;
        case 'overlay':
          updateNodeData(msg.data.node_id, { overlay: msg.data.overlay });
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
    return srcType === tgtType;
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
        },
      };
    }));
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

  const contextValue = useMemo(() => ({
    onWidgetChange,
    openFileBrowser,
  }), [onWidgetChange, openFileBrowser]);

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
      },
    };

    setNodes((ns) => [...ns, newNode]);

    // Auto-connect if this was triggered by dropping a connection on blank space
    if (contextMenu.pendingHandleId) {
      const filterType = contextMenu.filterType;

      if (contextMenu.pendingHandleType === 'source') {
        // Dragged from an output → connect to the first matching input on the new node
        const allInputs = { ...(def.input.required || {}), ...(def.input.optional || {}) };
        const inputName = Object.entries(allInputs).find(([, spec]) => {
          const [type] = Array.isArray(spec) ? spec : [spec];
          return type === filterType;
        })?.[0];
        if (inputName) {
          const targetHandle = `input::${inputName}::${filterType}`;
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
        const outputIdx = def.output.indexOf(filterType);
        if (outputIdx !== -1) {
          const sourceHandle = `output::${outputIdx}::${filterType}`;
          const color = TYPE_COLORS[filterType] || '#999';
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

    // Don't run if any node has unconnected required data inputs
    for (const node of currentNodes) {
      const def = node.data?.definition;
      if (!def) continue;
      const required = def.input.required || {};
      for (const [name, spec] of Object.entries(required)) {
        const [type] = Array.isArray(spec) ? spec : [spec];
        if (!DATA_TYPES.has(type)) continue;
        const hasEdge = currentEdges.some(
          (e) => e.target === node.id && getInputName(e.targetHandle) === name
        );
        if (!hasEdge) return; // incomplete graph, skip auto-run
      }
    }

    const prompt = serializeGraph(currentNodes, currentEdges);
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
    const loadedNodes = data.nodes || [];
    const loadedEdges = data.edges || [];
    const defs = nodeDefsRef.current;
    const hydrated = loadedNodes.map((n) => ({
      ...n,
      type: n.type || 'custom',
      dragHandle: n.dragHandle || '.drag-handle',
      data: {
        ...n.data,
        label: n.data?.label || n.data?.className || 'Node',
        widgetValues: n.data?.widgetValues || {},
        definition: defs[n.data.className] || n.data.definition,
        previewImage: null, tableRows: null, meshData: null, overlay: null,
      },
    }));
    setNodes(hydrated);
    setEdges(loadedEdges);
    const maxId = Math.max(0, ...loadedNodes.map((n) => parseInt(n.id, 10) || 0));
    nextIdRef.current = maxId + 1;
  }, [setNodes, setEdges]);

  const getWorkflowBlob = useCallback(async () => {
    const viewportEl = document.querySelector('.react-flow__viewport');
    if (!viewportEl) throw new Error('Flow element not found');

    const allNodes = reactFlow.getNodes();
    if (allNodes.length === 0) throw new Error('No nodes to capture');

    const bounds = getNodesBounds(allNodes);
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

      if (window.pywebview?.api?.save_workflow_png) {
        const dataUrl = await blobToDataUrl(finalBlob);
        const savedPath = await window.pywebview.api.save_workflow_png(dataUrl, 'workflow.png');
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
        <div className="flow-container" onMouseDown={(e) => {
          if (!e.target.closest('.context-menu')) setContextMenu(null);
        }} onDrop={onDropFile} onDragOver={onDragOver}>
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
                  analysis: '#4a148c', grains: '#bf360c', display: '#212121',
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
