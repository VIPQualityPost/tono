import React, { useContext, useRef, useCallback, useState, useEffect, memo, lazy, Suspense } from 'react';
import { Handle, NodeResizeControl, Position, useStore } from '@xyflow/react';
import { marked } from 'marked';
import LinePlotOverlay from './LinePlotOverlay';

marked.use({ breaks: true, gfm: true });

const SurfaceView = lazy(() => import('./SurfaceView'));
const CrossSectionOverlay = lazy(() => import('./CrossSectionOverlay'));
const CropBoxOverlay = lazy(() => import('./CropBoxOverlay'));
const MaskPaintOverlay = lazy(() => import('./MaskPaintOverlay'));
const MarkupOverlay = lazy(() => import('./MarkupOverlay'));
const AngleMeasureOverlay = lazy(() => import('./AngleMeasureOverlay'));
const ThresholdHistogram = lazy(() => import('./ThresholdHistogram'));

import TextNoteNode from './TextNoteNode';

import {
  getSpecTypeAndOptions, isDataSocketSpec, SOCKET_WIDGET_TYPES, TYPE_COLORS, CAT_COLORS,
} from './constants';
import { getGroupMinimumSize } from './groupSizing.js';
import { buildCombinedInputNameByWidgetName, formatUiLabel } from './nodeWidgetLayout.js';
import { applySIPrefix, formatNumericCell, formatTableRowCell, getTableColumns, parseNumberWithUnit } from './valueFormatting.js';

// ── Context (provided by App) ─────────────────────────────────────────

export const NodeContext = React.createContext(null);

function parseProxyHandle(handleId) {
  const text = String(handleId || '');
  if (!text.startsWith('group-proxy::')) return null;
  const parts = text.split('::');
  if (parts.length < 5) return null;
  return {
    direction: parts[1],
    nodeId: parts[2],
    type: parts[3],
    realHandle: decodeURIComponent(parts.slice(4).join('::')),
  };
}

function GroupNode({ id, data }) {
  const ctx = useContext(NodeContext);
  const proxyInputs = Array.isArray(data.proxyInputs) ? data.proxyInputs : [];
  const proxyOutputs = Array.isArray(data.proxyOutputs) ? data.proxyOutputs : [];
  const childCount = Number(data.childCount) || 0;
  const collapsed = !!data.collapsed;
  const maxRows = Math.max(proxyInputs.length, proxyOutputs.length, collapsed ? 1 : 0);
  const [isEditingLabel, setIsEditingLabel] = useState(false);
  const [draftLabel, setDraftLabel] = useState(String(data.label || 'group'));
  const labelInputRef = useRef(null);
  const selected = useStore(
    useCallback(
      (s) => {
        const node = s.nodeLookup?.get(id) || s.nodes?.find((candidate) => candidate.id === id);
        return !!node?.selected;
      },
      [id],
    ),
  );
  const groupMinSize = useStore(
    useCallback(
      (s) => getGroupMinimumSize(
        (s.nodes || []).filter((candidate) => String(candidate.parentId || '') === String(id)),
      ),
      [id],
    ),
  );
  const displayLabel = String(data.label || 'group');
  const labelFieldSize = Math.max(2, Math.min(40, String(draftLabel || displayLabel || 'group').length));

  useEffect(() => {
    if (!isEditingLabel) {
      setDraftLabel(displayLabel);
    }
  }, [displayLabel, isEditingLabel]);

  useEffect(() => {
    if (!isEditingLabel) return;
    labelInputRef.current?.focus();
    labelInputRef.current?.select();
  }, [isEditingLabel]);

  const commitLabel = useCallback(() => {
    const nextLabel = String(draftLabel || '').trim() || 'group';
    setIsEditingLabel(false);
    setDraftLabel(nextLabel);
    if (nextLabel !== displayLabel) {
      ctx.onRenameGroup?.(id, nextLabel);
    }
  }, [ctx, displayLabel, draftLabel, id]);

  const cancelLabelEdit = useCallback(() => {
    setDraftLabel(displayLabel);
    setIsEditingLabel(false);
  }, [displayLabel]);

  return (
    <>
      {!collapsed && selected && (
        <NodeResizeControl
          position="bottom-right"
          className="node-resize-handle"
          minWidth={groupMinSize.width}
          minHeight={groupMinSize.height}
          onResizeEnd={(_event, params) => ctx.onResizeGroup?.(id, params)}
        />
      )}
      <div className={`custom-node group-node ${collapsed ? 'group-node-collapsed' : 'group-node-expanded'}`}>
        <div className="node-title drag-handle group-node-title">
        <button
          type="button"
          className="group-toggle group-toggle-collapse nodrag"
          onClick={() => ctx.onToggleGroupCollapse?.(id)}
          title={collapsed ? 'expand group' : 'collapse group'}
        >
          {collapsed ? '▸' : '▾'}
        </button>
        <div className="group-title-slot">
          {isEditingLabel ? (
            <input
              ref={labelInputRef}
              className="group-title-input nodrag"
              type="text"
              value={draftLabel}
              size={labelFieldSize}
              onChange={(event) => setDraftLabel(event.target.value)}
              onBlur={commitLabel}
              onClick={(event) => event.stopPropagation()}
              onPointerDown={(event) => event.stopPropagation()}
              onKeyDown={(event) => {
                if (event.key === 'Enter') {
                  event.preventDefault();
                  commitLabel();
                } else if (event.key === 'Escape') {
                  event.preventDefault();
                  cancelLabelEdit();
                }
              }}
            />
          ) : (
            <button
              type="button"
              className="group-title-button nodrag"
              title="rename group"
              onClick={(event) => {
                event.stopPropagation();
                setDraftLabel(displayLabel);
                setIsEditingLabel(true);
              }}
            >
              {displayLabel}
            </button>
          )}
        </div>
        <div className="group-node-actions">
          <button
            type="button"
            className="group-toggle nodrag"
            onClick={() => ctx.onUngroup?.(id)}
            title="ungroup"
          >
            ungroup
          </button>
        </div>
      </div>

      <div className="node-body drag-handle">
        {collapsed ? (
          <>
            {Array.from({ length: maxRows }, (_, index) => {
              const input = proxyInputs[index];
              const output = proxyOutputs[index];
              return (
                <div className="io-row" key={`group-io-${index}`}>
                  <div className="io-left">
                    {input && (
                      <>
                        <Handle
                          type="target"
                          position={Position.Left}
                          id={input.handleId}
                          className="typed-handle"
                          style={{ background: TYPE_COLORS[input.type] || 'var(--fallback-type)' }}
                        />
                        <span className="io-label">{formatUiLabel(input.label || input.name)}</span>
                      </>
                    )}
                  </div>
                  <div className="io-right">
                    {output && (
                      <>
                        <span className="io-label">{formatUiLabel(output.label || output.name)}</span>
                        <Handle
                          type="source"
                          position={Position.Right}
                          id={output.handleId}
                          className="typed-handle"
                          style={{ background: TYPE_COLORS[output.type] || 'var(--fallback-type)' }}
                        />
                      </>
                    )}
                  </div>
                </div>
              );
            })}
            <div className="group-node-summary">{childCount} nodes</div>
          </>
        ) : (
          <div className="group-node-workspace">
            <div className="group-node-workspace-label">workflow group</div>
            <div className="group-node-summary">{childCount} nodes</div>
          </div>
        )}
      </div>
      </div>
    </>
  );
}

class PreviewBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error) {
    console.error('[tono] preview render failed', error);
  }

  componentDidUpdate(prevProps) {
    if (prevProps.resetKey !== this.props.resetKey && this.state.hasError) {
      this.setState({ hasError: false });
    }
  }

  render() {
    if (!this.state.hasError) {
      return this.props.children;
    }

    if (this.props.fallbackImage) {
      return (
        <div className="node-preview">
          <img src={this.props.fallbackImage} alt="preview fallback" draggable={false} />
        </div>
      );
    }

    return (
      <div className="node-preview" style={{ color: 'var(--text-secondary)', padding: 8 }}>
        Preview unavailable.
      </div>
    );
  }
}

// ── SI prefix helpers ─────────────────────────────────────────────────

const _SI_PREFIXES = [
  { prefix: 'T', factor: 1e12 },
  { prefix: 'G', factor: 1e9 },
  { prefix: 'M', factor: 1e6 },
  { prefix: 'k', factor: 1e3 },
  { prefix: '',  factor: 1 },
  { prefix: 'm', factor: 1e-3 },
  { prefix: 'μ', factor: 1e-6 },
  { prefix: 'n', factor: 1e-9 },
  { prefix: 'p', factor: 1e-12 },
  { prefix: 'f', factor: 1e-15 },
];

// Map of suffix characters → multiplier (accept both 'u' and 'μ' for micro)
const _SI_PARSE_MAP = { T:1e12, G:1e9, M:1e6, k:1e3, m:1e-3, u:1e-6, μ:1e-6, n:1e-9, p:1e-12, f:1e-15 };

function formatSI(v, prec) {
  if (!Number.isFinite(v)) return String(v);
  if (v === 0) return prec != null ? `0.${'0'.repeat(prec)}` : '0';
  const abs = Math.abs(v);
  // Pick the largest SI prefix whose factor is ≤ |v| (gives value in [1, 1000))
  let chosen = _SI_PREFIXES[_SI_PREFIXES.length - 1];
  for (const p of _SI_PREFIXES) {
    if (abs >= p.factor * (1 - 1e-10)) { chosen = p; break; }
  }
  const scaled = v / chosen.factor;
  return (prec != null ? scaled.toFixed(prec) : String(scaled)) + chosen.prefix;
}

// Parse a string that may carry an SI suffix (e.g. "20n", "1.5μ", "500p")
// Falls back to standard parseFloat for plain numbers and scientific notation.
function parseSI(text) {
  const t = (text || '').trim();
  if (!t) return NaN;
  const lastChar = t.slice(-1);
  const factor = _SI_PARSE_MAP[lastChar];
  if (factor != null) {
    const num = parseFloat(t.slice(0, -1));
    if (!isNaN(num)) return num * factor;
  }
  return parseFloat(t);
}

// ── Draggable number input ────────────────────────────────────────────

function DraggableNumber({ value, step, min, max, precision, onChange }) {
  const [editing, setEditing] = useState(false);
  const [editText, setEditText] = useState('');
  const dragState = useRef(null);
  const elRef = useRef(null);

  const display = precision != null ? formatSI(Number(value), precision) : String(value);

  const clamp = useCallback((v) => {
    if (min != null && v < min) v = min;
    if (max != null && v > max) v = max;
    return v;
  }, [min, max]);

  const onPointerDown = useCallback((e) => {
    if (editing) return;
    e.preventDefault();
    dragState.current = { startX: e.clientX, startVal: Number(value) };
    elRef.current?.setPointerCapture(e.pointerId);
  }, [editing, value]);

  const onPointerMove = useCallback((e) => {
    if (!dragState.current) return;
    const dx = e.clientX - dragState.current.startX;
    const delta = dx * (step || 0.01);
    const raw = dragState.current.startVal + delta;
    const rounded = precision != null ? raw : Math.round(raw);
    onChange(clamp(rounded));
  }, [step, precision, clamp, onChange]);

  const onPointerUp = useCallback((e) => {
    if (!dragState.current) return;
    const dx = Math.abs(e.clientX - dragState.current.startX);
    dragState.current = null;
    // If barely moved, enter text-edit mode
    if (dx < 3) {
      setEditText(display);
      setEditing(true);
    }
  }, [display]);

  const onWheel = useCallback((e) => {
    if (editing) return;
    e.preventDefault();

    const baseStep = Number(step) || 1;
    const multiplier = e.shiftKey ? 10 : 1;
    const delta = (e.deltaY < 0 ? 1 : -1) * baseStep * multiplier;
    const startVal = Number(value);
    const raw = (Number.isFinite(startVal) ? startVal : 0) + delta;
    const rounded = precision != null ? raw : Math.round(raw);
    onChange(clamp(rounded));
  }, [editing, step, value, precision, onChange, clamp]);

  const commitEdit = useCallback(() => {
    setEditing(false);
    const parsed = parseSI(editText);
    if (!isNaN(parsed)) onChange(clamp(precision != null ? parsed : Math.round(parsed)));
  }, [editText, precision, clamp, onChange]);

  if (editing) {
    return (
      <input
        className="nodrag drag-number-edit"
        type="text"
        autoFocus
        value={editText}
        onChange={(e) => setEditText(e.target.value)}
        onBlur={commitEdit}
        onKeyDown={(e) => { if (e.key === 'Enter') commitEdit(); if (e.key === 'Escape') setEditing(false); }}
      />
    );
  }

  return (
    <div
      ref={elRef}
      className="nodrag drag-number"
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={onPointerUp}
      onWheel={onWheel}
    >
      <span className="drag-number-val">{display}</span>
    </div>
  );
}

// ── Collapsible section ───────────────────────────────────────────────

function CollapsibleSection({ title, defaultOpen, children }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="collapsible">
      <button
        className="nodrag collapsible-toggle"
        onClick={() => setOpen((o) => !o)}
      >
        <span className="collapsible-arrow">{open ? '▾' : '▸'}</span>
        {title}
      </button>
      {open && children}
    </div>
  );
}

function LayerGalleryPreview({ overlay }) {
  const layers = Array.isArray(overlay?.layers) ? overlay.layers : [];
  const [index, setIndex] = useState(0);

  // Reset to 0 only when the layer names change (different file/channels loaded),
  // not on every graph re-run which produces a new overlay object reference.
  const layerNamesKey = layers.map((l) => l.name ?? '').join('\0');
  const prevLayerNamesKeyRef = useRef(layerNamesKey);
  useEffect(() => {
    if (layerNamesKey !== prevLayerNamesKeyRef.current) {
      prevLayerNamesKeyRef.current = layerNamesKey;
      setIndex(0);
    }
  }, [layerNamesKey]);

  useEffect(() => {
    if (layers.length === 0) {
      setIndex(0);
      return;
    }
    if (index >= layers.length) {
      setIndex(layers.length - 1);
    }
  }, [index, layers.length]);

  if (layers.length === 0) return null;

  const active = layers[index] || layers[0];

  return (
    <div className="layer-gallery">
      <div className="layer-gallery-toolbar">
        <button
          className="layer-gallery-btn nodrag"
          onClick={() => setIndex((current) => (current - 1 + layers.length) % layers.length)}
        >
          {'<'}
        </button>
        <div className="layer-gallery-name" title={active.name || `Layer ${index + 1}`}>
          {active.name || `Layer ${index + 1}`}
        </div>
        <button
          className="layer-gallery-btn nodrag"
          onClick={() => setIndex((current) => (current + 1) % layers.length)}
        >
          {'>'}
        </button>
      </div>
      <div className="layer-gallery-count">
        {index + 1} / {layers.length}
      </div>
      <div className="node-preview">
        <img src={active.image} alt={active.name || `layer ${index + 1}`} draggable={false} />
      </div>
    </div>
  );
}

function getMeasurementChoices(rows) {
  const names = [];
  for (const row of rows || []) {
    const quantity = row?.quantity;
    if (typeof quantity === 'string' && quantity && !names.includes(quantity)) {
      names.push(quantity);
    }
  }
  return names;
}

function formatScalarValue(value) {
  if (value == null || Number.isNaN(Number(value))) return '—';
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return String(numeric);
  const abs = Math.abs(numeric);
  if (abs === 0) return '0';
  if ((abs > 0 && abs < 1e-3) || abs >= 1e5) return numeric.toExponential(4);
  return numeric.toFixed(abs >= 100 ? 2 : 4).replace(/\.?0+$/, '');
}

function getScalarPayload(scalarValue) {
  if (typeof scalarValue === 'number') {
    return Number.isFinite(scalarValue) ? { value: scalarValue, unit: '' } : null;
  }
  if (!scalarValue || typeof scalarValue !== 'object') return null;
  const raw = scalarValue.value;
  if (typeof raw === 'string') {
    return { valueText: raw, unitText: typeof scalarValue.unit === 'string' ? scalarValue.unit : '' };
  }
  const numeric = Number(raw);
  if (!Number.isFinite(numeric)) return null;
  return {
    value: numeric,
    unit: typeof scalarValue.unit === 'string' ? scalarValue.unit : '',
  };
}

function formatScalarDisplay(scalarValue) {
  const payload = getScalarPayload(scalarValue);
  if (!payload) return null;
  if ('valueText' in payload) return payload;

  if (payload.unit) {
    const prefixed = applySIPrefix(payload.value, payload.unit);
    if (prefixed.unitText !== payload.unit || prefixed.valueText !== formatNumericCell(payload.value)) {
      return {
        valueText: prefixed.valueText,
        unitText: prefixed.unitText,
      };
    }
    return {
      valueText: formatScalarValue(payload.value),
      unitText: payload.unit,
    };
  }

  return {
    valueText: formatScalarValue(payload.value),
    unitText: '',
  };
}

function formatProcessingTime(value) {
  const ms = Number(value);
  if (!Number.isFinite(ms) || ms < 0) return null;
  if (ms < 1) return `${ms.toFixed(2)} ms`;
  if (ms < 10) return `${ms.toFixed(1)} ms`;
  if (ms < 1000) return `${Math.round(ms)} ms`;
  if (ms < 10000) return `${(ms / 1000).toFixed(2)} s`;
  return `${(ms / 1000).toFixed(1)} s`;
}

function getSourceTypeForInput(store, nodeId, inputName) {
  const targetHandle = `input::${inputName}::`;
  const edge = store.edges?.find((e) => e.target === nodeId && e.targetHandle?.startsWith(targetHandle));
  if (!edge?.sourceHandle) return null;
  const proxy = parseProxyHandle(edge.sourceHandle);
  if (proxy) return proxy.type || null;
  const parts = edge.sourceHandle.split('::');
  return parts[2] || null;
}

function getSourceNodeForInput(store, nodeId, inputName) {
  const targetHandle = `input::${inputName}::`;
  const edge = store.edges?.find((e) => e.target === nodeId && e.targetHandle?.startsWith(targetHandle));
  if (!edge) return null;
  return store.nodeLookup?.get(edge.source) || store.nodes?.find((n) => n.id === edge.source) || null;
}

function getConnectedOutputInfo(store, nodeId, inputName) {
  const targetHandle = `input::${inputName}::`;
  const edge = store.edges?.find((e) => e.target === nodeId && e.targetHandle?.startsWith(targetHandle));
  if (!edge?.sourceHandle) return null;
  const proxy = parseProxyHandle(edge.sourceHandle);
  const sourceNodeId = proxy?.nodeId || edge.source;
  const sourceHandle = proxy?.realHandle || edge.sourceHandle;
  const sourceNode = store.nodeLookup?.get(sourceNodeId) || store.nodes?.find((n) => n.id === sourceNodeId) || null;
  const slot = Number.parseInt(sourceHandle.split('::')[1], 10);
  if (!sourceNode || !Number.isInteger(slot)) return null;
  return {
    path: sourceNode.data?.definition?.output_paths?.[slot] || null,
    name: sourceNode.data?.definition?.output_name?.[slot] || null,
  };
}

/**
 * Resolve live COORDPAIR values by walking edges back to upstream Coordinate
 * nodes' widget values.  Returns [x1, y1, x2, y2] (a flat array for stable
 * equality comparison) or null if the chain can't be fully resolved.
 *
 * Uses store.nodes (the reactive array) rather than nodeLookup so that
 * upstream widgetValues changes trigger re-renders.
 */
function resolveLiveCoordPair(store, nodeId, coordPairInputName) {
  const nodes = store.nodes;
  const edges = store.edges;
  if (!nodes || !edges) return null;

  const findNode = (nid) => nodes.find((n) => n.id === nid);

  // 1. Find the edge feeding this node's COORDPAIR input
  const cpEdge = edges.find(
    (e) => e.target === nodeId && e.targetHandle?.startsWith(`input::${coordPairInputName}::`)
  );
  if (!cpEdge) return null;

  const cpNode = findNode(cpEdge.source);
  if (!cpNode) return null;

  // If the source node is a CoordinatePair, walk one more level to Coordinate nodes
  if (cpNode.data?.className === 'CoordinatePair') {
    const resolveCoord = (inputName) => {
      const edge = edges.find(
        (e) => e.target === cpNode.id && e.targetHandle?.startsWith(`input::${inputName}::`)
      );
      if (!edge) return null;
      const srcNode = findNode(edge.source);
      if (!srcNode?.data?.widgetValues) return null;
      const x = srcNode.data.widgetValues.x;
      const y = srcNode.data.widgetValues.y;
      return (x != null && y != null) ? [x, y] : null;
    };
    const a = resolveCoord('a');
    const b = resolveCoord('b');
    if (!a || !b) return null;
    return [a[0], a[1], b[0], b[1]];
  }

  // If the source is a node with x1/y1/x2/y2 widgets (e.g. another CrossSection output)
  const wv = cpNode.data?.widgetValues;
  if (wv && wv.x1 != null && wv.y1 != null && wv.x2 != null && wv.y2 != null) {
    return [wv.x1, wv.y1, wv.x2, wv.y2];
  }

  return null;
}

function getBasename(value) {
  if (typeof value !== 'string') return '';
  const trimmed = value.trim();
  if (!trimmed) return '';
  const normalized = trimmed.replace(/\\/g, '/').replace(/\/+$/, '');
  const parts = normalized.split('/');
  return parts[parts.length - 1] || '';
}

function getWidgetSourceInputName(opts) {
  return opts?.source_type_input
    || opts?.choices_from_table_input
    || opts?.choices_from_measure_input
    || Object.keys(opts?.show_when_source_type || {})[0];
}

function widgetVisibleForSourceType(widget, sourceType) {
  const rules = widget?.opts?.show_when_source_type;
  if (!rules || typeof rules !== 'object') return true;
  const inputName = Object.keys(rules)[0];
  const allowed = Array.isArray(rules[inputName]) ? rules[inputName] : [];
  if (allowed.length === 0) return true;
  return allowed.includes(sourceType);
}

function widgetVisibleForWidgetValues(widget, widgetValues) {
  const rules = widget?.opts?.show_when_widget_value;
  if (!rules || typeof rules !== 'object') return true;

  for (const [widgetName, allowedValues] of Object.entries(rules)) {
    const allowed = Array.isArray(allowedValues) ? allowedValues.map(String) : [];
    if (allowed.length === 0) continue;
    if (!allowed.includes(String(widgetValues?.[widgetName] ?? ''))) {
      return false;
    }
  }

  return true;
}

function widgetHiddenByConnectedInput(widget, connectedInputs) {
  const raw = widget?.opts?.hide_when_input_connected;
  if (!raw || !connectedInputs) return false;
  const inputs = Array.isArray(raw) ? raw : [raw];
  return inputs.some((inputName) => connectedInputs.has(String(inputName)));
}

function widgetVisibleForInputVisibility(widget, visibleInputs) {
  const raw = widget?.opts?.show_when_input_visible;
  if (!raw) return true;
  const inputs = Array.isArray(raw) ? raw : [raw];
  return inputs.some((inputName) => visibleInputs?.has(String(inputName)));
}

function getWidgetInlineInputName(widget) {
  const raw = widget?.opts?.inline_with_input;
  if (!raw) return null;
  return String(Array.isArray(raw) ? raw[0] : raw);
}

const DEFAULT_COLORMAP_STOPS = [
  { position: 0, color: '#440154' },
  { position: 1, color: '#fde725' },
];

function normalizeHexColor(color, fallback = '#000000') {
  if (typeof color !== 'string') return fallback;
  let text = color.trim();
  if (text.startsWith('#') && text.length === 4) {
    text = `#${text.slice(1).split('').map((ch) => `${ch}${ch}`).join('')}`;
  }
  if (/^#[0-9a-fA-F]{6}$/.test(text)) {
    return text.toLowerCase();
  }
  return fallback;
}

function parseColorMapStops(raw) {
  let parsed = raw;
  if (typeof raw === 'string') {
    try {
      parsed = JSON.parse(raw);
    } catch {
      parsed = DEFAULT_COLORMAP_STOPS;
    }
  }

  if (!Array.isArray(parsed)) {
    parsed = DEFAULT_COLORMAP_STOPS;
  }

  const stops = parsed
    .map((stop) => {
      const position = Number(stop?.position);
      return {
        position: Number.isFinite(position) ? Math.max(0, Math.min(1, position)) : 0,
        color: normalizeHexColor(stop?.color, '#000000'),
      };
    })
    .sort((a, b) => a.position - b.position);

  if (stops.length < 2) {
    return DEFAULT_COLORMAP_STOPS.map((stop) => ({ ...stop }));
  }

  stops[0].position = 0;
  stops[stops.length - 1].position = 1;
  return stops;
}

function serializeColorMapStops(stops) {
  return JSON.stringify(stops.map((stop, index) => ({
    position: index === 0 ? 0 : index === stops.length - 1 ? 1 : Number(stop.position.toFixed(4)),
    color: normalizeHexColor(stop.color, '#000000'),
  })));
}

function colorMapGradient(stops) {
  return `linear-gradient(90deg, ${stops.map((stop) => `${stop.color} ${Math.round(stop.position * 1000) / 10}%`).join(', ')})`;
}

function ColorMapStopsEditor({ nodeId, name, value, onChange }) {
  const stops = parseColorMapStops(value);

  const commitStops = useCallback((nextStops) => {
    const ordered = [...nextStops].sort((a, b) => a.position - b.position);
    if (ordered.length < 2) return;
    ordered[0] = { ...ordered[0], position: 0 };
    ordered[ordered.length - 1] = { ...ordered[ordered.length - 1], position: 1 };
    onChange(nodeId, name, serializeColorMapStops(ordered));
  }, [name, nodeId, onChange]);

  const updateStop = useCallback((index, patch) => {
    const next = stops.map((stop, stopIndex) => (stopIndex === index ? { ...stop, ...patch } : { ...stop }));
    if (index > 0 && index < next.length - 1) {
      const prev = next[index - 1].position + 0.001;
      const after = next[index + 1].position - 0.001;
      next[index].position = Math.max(prev, Math.min(after, next[index].position));
    }
    commitStops(next);
  }, [commitStops, stops]);

  const removeStop = useCallback((index) => {
    if (stops.length <= 2) return;
    commitStops(stops.filter((_, stopIndex) => stopIndex !== index));
  }, [commitStops, stops]);

  const addStop = useCallback(() => {
    let gapIndex = 0;
    let gapSize = -1;
    for (let i = 0; i < stops.length - 1; i += 1) {
      const gap = stops[i + 1].position - stops[i].position;
      if (gap > gapSize) {
        gapIndex = i;
        gapSize = gap;
      }
    }

    const left = stops[gapIndex];
    const right = stops[gapIndex + 1];
    const newStop = {
      position: Number((((left.position + right.position) / 2)).toFixed(4)),
      color: left.color,
    };
    const next = [...stops];
    next.splice(gapIndex + 1, 0, newStop);
    commitStops(next);
  }, [commitStops, stops]);

  return (
    <div className="colormap-editor">
      <div className="colormap-preview" style={{ backgroundImage: colorMapGradient(stops) }} />
      <div className="colormap-stop-list">
        {stops.map((stop, index) => {
          const isEndpoint = index === 0 || index === stops.length - 1;
          return (
            <div className="colormap-stop-row" key={`${index}-${stop.position}-${stop.color}`}>
              <span className="colormap-stop-label">{isEndpoint ? (index === 0 ? 'min' : 'max') : `stop ${index}`}</span>
              <input
                className="nodrag colormap-stop-color"
                type="color"
                value={normalizeHexColor(stop.color, '#000000')}
                onChange={(e) => updateStop(index, { color: e.target.value })}
              />
              {isEndpoint ? (
                <span className="colormap-stop-boundary">{index === 0 ? '0%' : '100%'}</span>
              ) : (
                <input
                  className="nodrag colormap-stop-position"
                  type="number"
                  min="0.001"
                  max="0.999"
                  step="0.01"
                  value={Number(stop.position.toFixed(4))}
                  onChange={(e) => updateStop(index, { position: Number(e.target.value) })}
                />
              )}
              <button
                className="nodrag colormap-stop-action"
                type="button"
                disabled={isEndpoint}
                onClick={() => removeStop(index)}
              >
                Remove
              </button>
            </div>
          );
        })}
      </div>
      <button className="nodrag widget-button colormap-add-stop" type="button" onClick={addStop}>
        Add Stop
      </button>
    </div>
  );
}

function NodeTable({ rows }) {
  const [query, setQuery] = useState('');
  const scrollRef = useRef(null);
  const isInsideRef = useRef(false);
  const pointerEnteredAtRef = useRef(0);
  const lastWheelAtRef = useRef(0);
  const gestureStartedInsideRef = useRef(false);

  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;

    const onEnter = () => {
      isInsideRef.current = true;
      pointerEnteredAtRef.current = Date.now();
    };
    const onLeave = () => {
      isInsideRef.current = false;
    };
    const onWheel = (e) => {
      const now = Date.now();
      const msSinceLastWheel = now - lastWheelAtRef.current;
      const msSinceEnter = now - pointerEnteredAtRef.current;
      lastWheelAtRef.current = now;

      if (msSinceLastWheel > 300) {
        // First event of a new gesture — only capture if pointer was already settled inside
        gestureStartedInsideRef.current = isInsideRef.current && msSinceEnter > 100;
      }

      if (gestureStartedInsideRef.current) {
        e.stopPropagation();
      }
    };

    el.addEventListener('wheel', onWheel, { passive: false });
    el.addEventListener('pointerenter', onEnter);
    el.addEventListener('pointerleave', onLeave);
    return () => {
      el.removeEventListener('wheel', onWheel);
      el.removeEventListener('pointerenter', onEnter);
      el.removeEventListener('pointerleave', onLeave);
    };
  }, []);

  const columns = getTableColumns(rows);
  if (columns.length === 0) return null;
  const lowerColumns = columns.map((column) => String(column).toLowerCase());
  const hasMeasurementLayout = (
    lowerColumns.length === 3
    && lowerColumns[0] === 'quantity'
    && lowerColumns[1] === 'value'
    && lowerColumns[2] === 'unit'
  );

  const getColumnClass = (column) => {
    const lower = String(column).toLowerCase();
    if (lower === 'value') return 'node-table-col-value';
    if (lower === 'unit') return 'node-table-col-unit';
    if (lower === 'quantity') return 'node-table-col-quantity';
    return '';
  };

  const filteredRows = query.trim()
    ? rows.filter((row) =>
        columns.some((col) => {
          const cell = formatTableRowCell(row, col);
          return String(cell).toLowerCase().includes(query.toLowerCase());
        })
      )
    : rows;

  return (
    <div className="node-table-wrap">
      {rows.length > 5 && (
        <div
          className="node-table-search"
          onPointerDown={(e) => e.stopPropagation()}
        >
          <input
            className="node-table-search-input nodrag"
            type="text"
            placeholder="Search…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </div>
      )}
      <div className="node-table-scroll" ref={scrollRef}>
        <table className="node-table-grid">
          {hasMeasurementLayout && (
            <colgroup>
              <col className="node-table-col-quantity" />
              <col className="node-table-col-value" />
              <col className="node-table-col-unit" />
            </colgroup>
          )}
          <thead>
            <tr>
              {columns.map((column) => (
                <th key={column} scope="col" className={getColumnClass(column)}>{column}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {filteredRows.map((row, rowIndex) => (
              <tr key={row.id ?? row.quantity ?? rowIndex}>
                {columns.map((column) => {
                  const value = row?.[column];
                  const displayValue = formatTableRowCell(row, column);
                  return (
                    <td
                      key={`${rowIndex}-${column}`}
                      className={[
                        getColumnClass(column),
                        (typeof value === 'number' || (column === 'value' && typeof row?.value === 'number')) ? 'node-table-num' : '',
                      ].filter(Boolean).join(' ')}
                      title={displayValue}
                    >
                      {displayValue}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ── CustomNode component ──────────────────────────────────────────────

function CustomNode({ id, data }) {
  const ctx = useContext(NodeContext);
  const def = data.definition;
  const scalarDisplay = formatScalarDisplay(data.scalarValue);
  const processingTimeText = formatProcessingTime(data.processingTimeMs);
  const connectedPathInfo = useStore(
    useCallback((s) => getConnectedOutputInfo(s, id, 'path'), [id]),
  );

  // Find the COORDPAIR input name (if any) so we can resolve live upstream positions
  const coordPairInputName = React.useMemo(() => {
    if (!def) return null;
    const allInputs = { ...def.input.required, ...def.input.optional };
    for (const [name, spec] of Object.entries(allInputs)) {
      const type = Array.isArray(spec) ? spec[0] : spec;
      if (type === 'COORDPAIR') return name;
    }
    return null;
  }, [def]);

  // Returns [x1, y1, x2, y2] or null — flat array for cheap equality check
  const liveCoordPair = useStore(
    useCallback(
      (s) => coordPairInputName ? resolveLiveCoordPair(s, id, coordPairInputName) : null,
      [id, coordPairInputName],
    ),
    (a, b) => {
      if (a === b) return true;
      if (!a || !b) return false;
      return a[0] === b[0] && a[1] === b[1] && a[2] === b[2] && a[3] === b[3];
    },
  );

  // Parse inputs into data handles and widgets
  const required = def?.input?.required || {};
  const optional = def?.input?.optional || {};

  const dataInputs = [];
  const widgets = [];
  const visibleInputNames = new Set();

  const hiddenWidgets = new Set();

  for (const [name, spec] of Object.entries(required)) {
    const [type, opts] = getSpecTypeAndOptions(spec);
    if (isDataSocketSpec(spec)) {
      dataInputs.push({ name, type, label: formatUiLabel(opts?.label || name) });
      visibleInputNames.add(name);
    } else if (opts?.hidden) {
      hiddenWidgets.add(name);
    } else if (opts?.socket_only) {
      dataInputs.push({ name, type, label: formatUiLabel(opts?.label || name) });
      visibleInputNames.add(name);
    } else {
      widgets.push({ name, type, opts: opts || {}, socketType: SOCKET_WIDGET_TYPES.has(type) ? type : null });
    }
  }

  // For manual-trigger nodes (Save), show progressive optional inputs:
  // show field_N only if field_(N-1) is connected (or N==0).
  const isProgressive = def?.manual_trigger;
  const connectedInputs = useStore(
    useCallback(
      (s) => {
        const set = new Set();
        for (const e of s.edges) {
          if (e.target === id) {
            const parts = e.targetHandle?.split('::');
            if (parts) set.add(parts[1]);
          }
        }
        return set;
      },
      [id],
    ),
  );

  const connectedSourceTypes = useStore(
    useCallback(
      (s) => {
        const sourceTypes = {};
        const allInputs = { ...required, ...optional };
        for (const name of Object.keys(allInputs)) {
          sourceTypes[name] = getSourceTypeForInput(s, id, name);
        }
        return sourceTypes;
      },
      [id, required, optional],
    ),
  );

  if (data.className === 'Group') {
    return <GroupNode id={id} data={data} />;
  }
  if (data.className === 'TextNote') {
    return <TextNoteNode id={id} data={data} />;
  }

  for (const [name, spec] of Object.entries(optional)) {
    const [type, opts] = getSpecTypeAndOptions(spec);
    if (isProgressive && isDataSocketSpec(spec)) {
      // Progressive: show this slot only if it's the first or the previous is connected
      const match = name.match(/^field_(\d+)$/);
      if (match) {
        const idx = parseInt(match[1], 10);
        if (idx === 0 || (connectedInputs && connectedInputs.has(`field_${idx - 1}`))) {
          dataInputs.push({ name, type, label: formatUiLabel(opts?.label || name) });
          visibleInputNames.add(name);
        }
        continue;
      }
    }
    if (opts?.hidden) {
      hiddenWidgets.add(name);
    } else if (isDataSocketSpec(spec) || opts?.socket_only) {
      dataInputs.push({ name, type, label: formatUiLabel(opts?.label || name) });
      visibleInputNames.add(name);
    } else {
      widgets.push({ name, type, opts: opts || {}, socketType: SOCKET_WIDGET_TYPES.has(type) ? type : null });
    }
  }

  const dataInputByName = new Map(dataInputs.map((input) => [input.name, input]));

  const widgetsVisibleByDefinition = widgets.filter((w) => (
    widgetVisibleForSourceType(w, connectedSourceTypes?.[getWidgetSourceInputName(w.opts)])
    && widgetVisibleForWidgetValues(w, data.widgetValues)
    && widgetVisibleForInputVisibility(w, visibleInputNames)
  ));
  const combinedInputNameByWidgetName = buildCombinedInputNameByWidgetName(
    widgetsVisibleByDefinition,
    dataInputs,
  );
  const visibleWidgets = widgetsVisibleByDefinition.filter((widget) => (
    combinedInputNameByWidgetName.has(widget.name)
    || !widgetHiddenByConnectedInput(widget, connectedInputs)
  ));

  const combinedInputNames = new Set(combinedInputNameByWidgetName.values());
  const renderedDataInputs = dataInputs.filter((input) => !combinedInputNames.has(input.name));

  // Computed directly from React props so it updates reliably when tableRows changes.
  const nodeTableMeasurementChoices = getMeasurementChoices(data.tableRows || []);

  const inlineWidgetsByInput = new Map();
  const topWidgets = [];
  const standaloneWidgets = [];
  for (const widget of visibleWidgets) {
    const inlineInputName = getWidgetInlineInputName(widget);
    if (inlineInputName) {
      inlineWidgetsByInput.set(inlineInputName, widget);
    } else if (widget.opts?.placement === 'top') {
      topWidgets.push(widget);
    } else {
      standaloneWidgets.push(widget);
    }
  }

  const outputs = def.output.map((type, i) => ({
    name: formatUiLabel(def.output_name[i] || type),
    type,
    slot: i,
  }));

  const catColor = CAT_COLORS[def.category] || 'var(--fallback-cat)';
  const maxIORows = Math.max(renderedDataInputs.length, outputs.length);
  const hasInteractiveLineOverlay = data.overlay?.kind === 'line_plot' && hiddenWidgets.has('x1');
  const hasInteractiveOverlay = !!data.overlay && (
    hiddenWidgets.has('x1')
    || data.overlay.kind === 'mask_paint'
    || data.overlay.kind === 'markup'
    || data.overlay.kind === 'threshold_histogram'
  );
  const hidePreviewForInteractiveMask = data.overlay?.kind === 'mask_paint' || data.overlay?.kind === 'markup';
  const overlayTitle = data.overlay?.section_title
    || (data.overlay?.kind === 'mask_paint'
      ? 'Mask'
      : data.overlay?.kind === 'markup'
      ? 'Markup'
      : data.overlay?.kind === 'angle_measure'
      ? 'Angle'
      : data.overlay?.kind === 'crop_box'
      ? 'Crop'
      : data.overlay?.kind === 'cursor_points'
      ? 'Cursors'
      : data.overlay?.kind === 'line_plot'
        ? 'Line Plot'
      : 'Cross Section');
  const headerMeta = (() => {
    if (data.className === 'Folder') {
      return getBasename(data.widgetValues?.folder);
    }
    if (data.className === 'Image') {
      return getBasename(connectedPathInfo?.path || data.widgetValues?.filename);
    }
    if (data.className === 'ImageDemo') {
      return getBasename(data.widgetValues?.name);
    }
    return '';
  })();

  return (
    <>
      {ctx?.executingNodeId === id && <div className="node-executing-glow" aria-hidden="true" />}
    <div className={`custom-node${data.error ? ' node-error' : ''}`}>
      {/* Title */}
      <div className="node-title drag-handle" style={{ background: catColor }}>
        <div className="node-title-left">
          <span className="node-title-main">{data.label}</span>
          <button className="node-help-btn nodrag nopan" title="Documentation" onClick={(e) => { e.stopPropagation(); ctx?.openHelp(data.label); }}>?</button>
        </div>
        {headerMeta && <span className="node-title-meta" title={headerMeta}>{headerMeta}</span>}
      </div>

      <div className="node-body drag-handle">
        {topWidgets.length > 0 && (
          <div className="top-widget-section">
            {topWidgets.map((w) => {
              const combinedInputName = combinedInputNameByWidgetName.get(w.name) || null;
              const socketInput = combinedInputName ? dataInputByName.get(combinedInputName) : null;
              const socketType = w.socketType || socketInput?.type;
              const socketName = w.socketType ? w.name : socketInput?.name;
              return (
                <div className={`widget-row${socketType ? ' widget-row-socket' : ''}`} key={w.name}>
                  {socketType && socketName && (
                    <Handle
                      type="target"
                      position={Position.Left}
                      id={`input::${socketName}::${socketType}`}
                      className="typed-handle"
                      style={{ background: TYPE_COLORS[socketType] || 'var(--fallback-type)' }}
                    />
                  )}
                  {(
                    (w.socketType && connectedInputs?.has(w.name))
                    || (combinedInputName && connectedInputs?.has(combinedInputName))
                  ) ? (
                    <label>{formatUiLabel(w.opts?.label || w.name)}</label>
                  ) : (
                    <WidgetControl
                      widget={w}
                      nodeId={id}
                      value={data.widgetValues[w.name]}
                      widgetValues={data.widgetValues}
                      onChange={ctx.onWidgetChange}
                      openFileBrowser={ctx.openFileBrowser}
                      measurementChoices={nodeTableMeasurementChoices}
                    />
                  )}
                </div>
              );
            })}
          </div>
        )}

        {/* I/O rows — pair inputs[i] with outputs[i] */}
        {Array.from({ length: maxIORows }, (_, i) => {
          const inp = renderedDataInputs[i];
          const out = outputs[i];
          return (
            <div className="io-row" key={`io-${i}`}>
              <div className="io-left">
                {inp && (
                  <>
                    <Handle
                      type="target"
                      position={Position.Left}
                      id={`input::${inp.name}::${inp.type}`}
                      className="typed-handle"
                      style={{ background: TYPE_COLORS[inp.type] || 'var(--fallback-type)' }}
                    />
                    <span className="io-label">{inp.label || inp.name}</span>
                    {inlineWidgetsByInput.has(inp.name) && (
                      <div className="io-inline-widget">
                        <WidgetControl
                          widget={inlineWidgetsByInput.get(inp.name)}
                          nodeId={id}
                          value={data.widgetValues[inlineWidgetsByInput.get(inp.name).name]}
                          widgetValues={data.widgetValues}
                          onChange={ctx.onWidgetChange}
                          openFileBrowser={ctx.openFileBrowser}
                          hideLabel={true}
                        />
                      </div>
                    )}
                  </>
                )}
              </div>
              <div className="io-right">
                {out && (
                  <>
                    <span className="io-label">{out.name}</span>
                    <Handle
                      type="source"
                      position={Position.Right}
                      id={`output::${out.slot}::${out.type}`}
                      className="typed-handle"
                      style={{ background: TYPE_COLORS[out.type] || 'var(--fallback-type)' }}
                    />
                  </>
                )}
              </div>
            </div>
          );
        })}

        {/* Warning notification */}
        {data.warning && (
          <div className="node-warning">{data.warning}</div>
        )}

        {/* Error notification */}
        {data.error && (
          <div className="node-error-message">{data.error}</div>
        )}

        {scalarDisplay && !standaloneWidgets.some((w) => w.opts?.text_input) && (
          <div className="node-value-display">
            <div className="node-value-box">
              <span className="node-value-box-number">{scalarDisplay.valueText}</span>
              {scalarDisplay.unitText && (
                <span className="node-value-box-unit">{scalarDisplay.unitText}</span>
              )}
            </div>
          </div>
        )}

        {/* Widget rows */}
        {standaloneWidgets.map((w) => {
          const combinedInputName = combinedInputNameByWidgetName.get(w.name) || null;
          const socketInput = combinedInputName ? dataInputByName.get(combinedInputName) : null;
          const socketType = w.socketType || socketInput?.type;
          const socketName = w.socketType ? w.name : socketInput?.name;
          return (
            <div className={`widget-row${socketType ? ' widget-row-socket' : ''}`} key={w.name}>
              {socketType && socketName && (
                <Handle
                  type="target"
                  position={Position.Left}
                  id={`input::${socketName}::${socketType}`}
                  className="typed-handle"
                  style={{ background: TYPE_COLORS[socketType] || 'var(--fallback-type)' }}
                />
              )}
              {(w.socketType && connectedInputs?.has(w.name))
                || (combinedInputName && connectedInputs?.has(combinedInputName)) ? (
                <label>{formatUiLabel(w.opts?.label || w.name)}</label>
              ) : (
                <WidgetControl
                  widget={w}
                  nodeId={id}
                  value={data.widgetValues[w.name]}
                  widgetValues={data.widgetValues}
                  onChange={ctx.onWidgetChange}
                  openFileBrowser={ctx.openFileBrowser}
                  measurementChoices={nodeTableMeasurementChoices}
                />
              )}
            </div>
          );
        })}

        {/* Manual trigger button (Save) */}
        {def.manual_trigger && (
          <div className="widget-row">
            <button
              className="nodrag btn btn-primary"
              style={{ flex: 1 }}
              onClick={() => ctx.onManualTrigger?.(id)}
            >
              Save to Disk
            </button>
          </div>
        )}

        {/* Interactive 3D surface view */}
        {data.meshData && (
          <CollapsibleSection title="3D View" defaultOpen={true}>
            <Suspense fallback={<div className="node-preview" style={{color:'var(--text-muted)',padding:4}}>Loading 3D...</div>}>
              <SurfaceView
                meshData={data.meshData}
                nodeId={id}
                widgetValues={data.widgetValues}
                runtimeValues={data.runtimeValues}
                onRuntimeValuesChange={ctx.onRuntimeValuesChange}
              />
            </Suspense>
          </CollapsibleSection>
        )}

        {/* Threshold histogram — rendered before preview so it sits above the mask image */}
        {data.overlay?.kind === 'threshold_histogram' && (
          <CollapsibleSection title={overlayTitle} defaultOpen={true}>
            <Suspense fallback={<div className="node-preview" style={{color:'var(--text-muted)',padding:4}}>Loading...</div>}>
              <ThresholdHistogram
                overlay={data.overlay}
                threshold={data.widgetValues.threshold}
                thresholdConnected={connectedInputs?.has('threshold')}
                nodeId={id}
                onWidgetChange={ctx.onWidgetChange}
              />
            </Suspense>
          </CollapsibleSection>
        )}

        {/* Collapsible preview image */}
        {data.previewImage && !hidePreviewForInteractiveMask && (
          typeof data.previewImage === 'object' && data.previewImage.kind === 'panels'
            ? data.previewImage.panels.map((panel, pi) => (
              <CollapsibleSection key={pi} title={panel.title || 'Preview'} defaultOpen={true}>
                <PreviewBoundary
                  resetKey={JSON.stringify({ kind: panel.kind, title: panel.title, len: panel.line?.length })}
                  fallbackImage={panel.fallback_image ?? null}
                >
                  {panel.kind === 'line_plot' ? (
                    <LinePlotOverlay overlay={panel} interactive={false} />
                  ) : panel.kind === 'image' ? (
                    <div className="node-preview">
                      <img src={panel.image} alt={panel.title || 'preview'} draggable={false} />
                    </div>
                  ) : null}
                </PreviewBoundary>
              </CollapsibleSection>
            ))
            : !(hasInteractiveLineOverlay && typeof data.previewImage === 'object' && data.previewImage.kind === 'line_plot') && (
              <CollapsibleSection title="Preview" defaultOpen={true}>
                <PreviewBoundary
                  resetKey={typeof data.previewImage === 'string' ? data.previewImage : JSON.stringify({
                    kind: data.previewImage.kind,
                    len: data.previewImage.line?.length,
                    layers: data.previewImage.layers?.length,
                  })}
                  fallbackImage={typeof data.previewImage === 'object' ? data.previewImage.fallback_image : null}
                >
                  {typeof data.previewImage === 'string' ? (
                    <div className="node-preview">
                      <img src={data.previewImage} alt="preview" draggable={false} />
                    </div>
                  ) : data.previewImage.kind === 'layer_gallery' ? (
                    <LayerGalleryPreview overlay={data.previewImage} />
                  ) : data.previewImage.kind === 'line_plot' ? (
                    <LinePlotOverlay overlay={data.previewImage} interactive={false} />
                  ) : null}
                </PreviewBoundary>
              </CollapsibleSection>
            )
        )}

        {/* Interactive cross-section overlay */}
        {hasInteractiveOverlay && data.overlay?.kind !== 'threshold_histogram' && (
          <CollapsibleSection title={overlayTitle} defaultOpen={true}>
            <Suspense fallback={<div className="node-preview" style={{color:'var(--text-muted)',padding:4}}>Loading...</div>}>
              {data.overlay.kind === 'line_plot' ? (
                <LinePlotOverlay
                  overlay={data.overlay}
                  x1={data.overlay.a_locked ? (liveCoordPair?.[0] ?? data.overlay.x1) : (data.widgetValues.x1 ?? data.overlay.x1)}
                  x2={data.overlay.b_locked ? (liveCoordPair?.[2] ?? data.overlay.x2) : (data.widgetValues.x2 ?? data.overlay.x2)}
                  aLocked={data.overlay.a_locked}
                  bLocked={data.overlay.b_locked}
                  nodeId={id}
                  onWidgetChange={ctx.onWidgetChange}
                />
              ) : data.overlay.kind === 'crop_box' ? (
                <CropBoxOverlay
                  image={data.overlay.image}
                  x1={data.overlay.a_locked ? (liveCoordPair?.[0] ?? data.overlay.x1) : (data.widgetValues.x1 ?? data.overlay.x1)}
                  y1={data.overlay.a_locked ? (liveCoordPair?.[1] ?? data.overlay.y1) : (data.widgetValues.y1 ?? data.overlay.y1)}
                  x2={data.overlay.b_locked ? (liveCoordPair?.[2] ?? data.overlay.x2) : (data.widgetValues.x2 ?? data.overlay.x2)}
                  y2={data.overlay.b_locked ? (liveCoordPair?.[3] ?? data.overlay.y2) : (data.widgetValues.y2 ?? data.overlay.y2)}
                  aLocked={data.overlay.a_locked}
                  bLocked={data.overlay.b_locked}
                  nodeId={id}
                  onWidgetChange={ctx.onWidgetChange}
                />
              ) : data.overlay.kind === 'cursor_points' ? (
                <CrossSectionOverlay
                  image={data.overlay.image}
                  x1={data.overlay.a_locked ? (liveCoordPair?.[0] ?? data.overlay.x1) : (data.widgetValues.x1 ?? data.overlay.x1)}
                  y1={data.overlay.a_locked ? (liveCoordPair?.[1] ?? data.overlay.y1) : (data.widgetValues.y1 ?? data.overlay.y1)}
                  x2={data.overlay.b_locked ? (liveCoordPair?.[2] ?? data.overlay.x2) : (data.widgetValues.x2 ?? data.overlay.x2)}
                  y2={data.overlay.b_locked ? (liveCoordPair?.[3] ?? data.overlay.y2) : (data.widgetValues.y2 ?? data.overlay.y2)}
                  aLocked={data.overlay.a_locked}
                  bLocked={data.overlay.b_locked}
                  nodeId={id}
                  onWidgetChange={ctx.onWidgetChange}
                  showLine={false}
                />
              ) : data.overlay.kind === 'mask_paint' ? (
                <MaskPaintOverlay
                  image={data.overlay.image}
                  imageWidth={data.overlay.image_width}
                  imageHeight={data.overlay.image_height}
                  penSize={data.widgetValues.pen_size}
                  maskPaths={data.widgetValues.mask_paths}
                  nodeId={id}
                  onWidgetChange={ctx.onWidgetChange}
                />
              ) : data.overlay.kind === 'markup' ? (
                <MarkupOverlay
                  image={data.overlay.image}
                  shape={data.widgetValues.shape ?? data.overlay.shape}
                  strokeColor={data.widgetValues.stroke_color ?? data.overlay.stroke_color}
                  strokeWidth={data.widgetValues.stroke_width ?? data.overlay.stroke_width}
                  markupShapes={data.widgetValues.markup_shapes}
                  nodeId={id}
                  onWidgetChange={ctx.onWidgetChange}
                />
              ) : data.overlay.kind === 'threshold_histogram' ? (
                <ThresholdHistogram
                  overlay={data.overlay}
                  threshold={data.widgetValues.threshold}
                  nodeId={id}
                  onWidgetChange={ctx.onWidgetChange}
                />
              ) : data.overlay.kind === 'angle_measure' ? (
                <AngleMeasureOverlay
                  image={data.overlay.image}
                  x1={data.widgetValues.x1 ?? data.overlay.x1}
                  y1={data.widgetValues.y1 ?? data.overlay.y1}
                  xm={data.widgetValues.xm ?? data.overlay.xm}
                  ym={data.widgetValues.ym ?? data.overlay.ym}
                  x2={data.widgetValues.x2 ?? data.overlay.x2}
                  y2={data.widgetValues.y2 ?? data.overlay.y2}
                  labelDx={data.widgetValues.label_dx ?? data.overlay.label_dx ?? 0}
                  labelDy={data.widgetValues.label_dy ?? data.overlay.label_dy ?? 0}
                  angleDeg={data.overlay.angle_deg}
                  color={data.widgetValues.color ?? data.overlay.color ?? '#ff9800'}
                  strokeWidth={connectedInputs?.has('stroke_width')
                    ? (data.overlay.stroke_width ?? data.overlay.line_thickness ?? data.widgetValues.stroke_width ?? 1.35)
                    : (data.widgetValues.stroke_width ?? data.overlay.stroke_width ?? data.overlay.line_thickness ?? 1.35)}
                  nodeId={id}
                  onWidgetChange={ctx.onWidgetChange}
                />
              ) : (
                <CrossSectionOverlay
                  image={data.overlay.image}
                  x1={data.overlay.a_locked ? data.overlay.x1 : (data.widgetValues.x1 ?? data.overlay.x1)}
                  y1={data.overlay.a_locked ? data.overlay.y1 : (data.widgetValues.y1 ?? data.overlay.y1)}
                  x2={data.overlay.b_locked ? data.overlay.x2 : (data.widgetValues.x2 ?? data.overlay.x2)}
                  y2={data.overlay.b_locked ? data.overlay.y2 : (data.widgetValues.y2 ?? data.overlay.y2)}
                  aLocked={data.overlay.a_locked}
                  bLocked={data.overlay.b_locked}
                  nodeId={id}
                  onWidgetChange={ctx.onWidgetChange}
                />
              )}
            </Suspense>
          </CollapsibleSection>
        )}

        {/* Collapsible table data */}
        {data.tableRows && data.tableRows.length > 0 && (
          <CollapsibleSection title="Table" defaultOpen={false}>
            <NodeTable rows={data.tableRows} />
          </CollapsibleSection>
        )}
        {processingTimeText && (
          <div className="node-benchmark" title={`Processed in ${processingTimeText}`}>
            {processingTimeText}
          </div>
        )}
      </div>
    </div>
    </>
  );
}

// ── Editable value-box for text_input FLOAT widgets ──────────────────

function TextInputValueBox({ val, placeholder, nodeId, name, label, hideLabel, onChange }) {
  const [editing, setEditing] = useState(false);
  const parsed = parseNumberWithUnit(val);
  const display = parsed ? formatScalarDisplay({ value: parsed.numeric, unit: parsed.unit }) : null;

  return (
    <>
      {!hideLabel && <label>{label}</label>}
      <div
        className="node-value-box nodrag"
        style={{ cursor: editing ? 'text' : 'pointer' }}
        onClick={() => !editing && setEditing(true)}
      >
        {editing ? (
          <input
            autoFocus
            className="nodrag"
            type="text"
            value={val}
            placeholder={placeholder}
            onChange={(e) => onChange(nodeId, name, e.target.value)}
            onBlur={() => setEditing(false)}
            style={{
              background: 'transparent',
              border: 'none',
              outline: 'none',
              color: 'inherit',
              font: 'inherit',
              textAlign: 'center',
              width: '100%',
              padding: 0,
            }}
          />
        ) : display ? (
          <>
            <span className="node-value-box-number">{display.valueText}</span>
            {display.unitText && <span className="node-value-box-unit">{display.unitText}</span>}
          </>
        ) : (
          <span className="node-value-box-number" style={{ opacity: 0.4 }}>{placeholder || '0'}</span>
        )}
      </div>
    </>
  );
}

// ── Widget renderer ───────────────────────────────────────────────────

function WidgetControl({ widget, nodeId, value, widgetValues, onChange, openFileBrowser, hideLabel = false, measurementChoices }) {
  const { name, type, opts } = widget;
  const label = formatUiLabel(opts?.label || name);
  const val = value ?? opts?.default ?? '';
  const placeholder = opts?.placeholder || '';
  const dynamicSourceType = useStore(
    useCallback(
      (s) => {
        const inputName = getWidgetSourceInputName(opts);
        if (!inputName) return null;
        return getSourceTypeForInput(s, nodeId, inputName);
      },
      [nodeId, opts],
    ),
  );
  const dynamicTableColumns = useStore(
    useCallback(
      (s) => {
        const tableInputName = opts?.choices_from_table_input;
        if (!tableInputName) return [];
        const sourceType = getSourceTypeForInput(s, nodeId, tableInputName);
        if (sourceType !== 'DATA_TABLE') return [];
        const sourceNode = getSourceNodeForInput(s, nodeId, tableInputName);
        const rows = sourceNode?.data?.tableRows;
        return Array.isArray(rows) ? getTableColumns(rows) : [];
      },
      [nodeId, opts?.choices_from_table_input],
    ),
  );
  const dynamicMeasurementChoices = useStore(
    useCallback(
      (s) => {
        if (!opts?.choices_from_measure_input) return [];
        const node = s.nodeLookup?.get(nodeId) || s.nodes?.find((n) => n.id === nodeId);
        const rows = node?.data?.tableRows;
        return Array.isArray(rows) ? getMeasurementChoices(rows) : [];
      },
      [nodeId, opts?.choices_from_measure_input],
    ),
  );
  const dynamicTypeChoices = (() => {
    const byType = opts?.choices_by_source_type;
    if (!byType) return [];
    if (dynamicSourceType) {
      return Array.isArray(byType[dynamicSourceType]) ? byType[dynamicSourceType] : [];
    }
    const merged = [];
    for (const choices of Object.values(byType)) {
      if (!Array.isArray(choices)) continue;
      for (const choice of choices) {
        if (!merged.includes(choice)) merged.push(choice);
      }
    }
    return merged;
  })();

  useEffect(() => {
    if (!opts?.choices_from_table_input || dynamicTableColumns.length === 0) return;
    const current = String(val ?? '');
    if (dynamicTableColumns.includes(current)) return;
    const preferred = dynamicTableColumns.includes('value') ? 'value' : dynamicTableColumns[0];
    if (preferred != null) onChange(nodeId, name, preferred);
  }, [dynamicTableColumns, name, nodeId, onChange, opts?.choices_from_table_input, val]);

  useEffect(() => {
    if (!opts?.choices_from_measure_input || dynamicMeasurementChoices.length === 0) return;
    const current = String(val ?? '');
    if (dynamicMeasurementChoices.includes(current)) return;
    if (dynamicMeasurementChoices[0] != null) onChange(nodeId, name, dynamicMeasurementChoices[0]);
  }, [dynamicMeasurementChoices, name, nodeId, onChange, opts?.choices_from_measure_input, val]);

  useEffect(() => {
    if (dynamicTypeChoices.length === 0) return;
    const current = String(val ?? '');
    if (dynamicTypeChoices.includes(current)) return;
    onChange(nodeId, name, dynamicTypeChoices[0]);
  }, [dynamicTypeChoices, name, nodeId, onChange, val]);

  if (opts?.colormap_stops) {
    return (
      <>
        {!hideLabel && <label>{label}</label>}
        <ColorMapStopsEditor
          nodeId={nodeId}
          name={name}
          value={val}
          onChange={onChange}
        />
      </>
    );
  }

  // Combo / enum — type itself is the array of options
  if (Array.isArray(type)) {
    return (
      <>
        {!hideLabel && <label>{label}</label>}
        <select
          className="nodrag"
          value={val || type[0]}
          onChange={(e) => onChange(nodeId, name, e.target.value)}
        >
          {type.map((opt) => (
            <option key={opt} value={opt}>{opt}</option>
          ))}
        </select>
      </>
    );
  }

  if (type === 'STRING' && dynamicTypeChoices.length > 0) {
    const selected = dynamicTypeChoices.includes(String(val)) ? String(val) : dynamicTypeChoices[0];
    return (
      <>
        {!hideLabel && <label>{label}</label>}
        <select
          className="nodrag"
          value={selected}
          onChange={(e) => onChange(nodeId, name, e.target.value)}
        >
          {dynamicTypeChoices.map((choice) => (
            <option key={choice} value={choice}>{choice}</option>
          ))}
        </select>
      </>
    );
  }

  if (type === 'STRING' && opts?.choices_from_table_input && dynamicTableColumns.length > 0) {
    const selected = dynamicTableColumns.includes(String(val)) ? String(val) : dynamicTableColumns[0];
    return (
      <>
        {!hideLabel && <label>{label}</label>}
        <select
          className="nodrag"
          value={selected}
          onChange={(e) => onChange(nodeId, name, e.target.value)}
        >
          {dynamicTableColumns.map((column) => (
            <option key={column} value={column}>{column}</option>
          ))}
        </select>
      </>
    );
  }

  if (type === 'STRING' && opts?.choices_from_measure_input && dynamicMeasurementChoices.length > 0) {
    const selected = dynamicMeasurementChoices.includes(String(val)) ? String(val) : dynamicMeasurementChoices[0];
    return (
      <>
        {!hideLabel && <label>{label}</label>}
        <select
          className="nodrag"
          value={selected}
          onChange={(e) => onChange(nodeId, name, e.target.value)}
        >
          {dynamicMeasurementChoices.map((choice) => (
            <option key={choice} value={choice}>{choice}</option>
          ))}
        </select>
      </>
    );
  }

  if (type === 'FILE_PICKER' || type === 'FOLDER_PICKER') {
    const isFolderPicker = type === 'FOLDER_PICKER';
    return (
      <>
        {!hideLabel && <label>{label}</label>}
        <div className="file-picker-row">
          <input
            className="nodrag"
            type="text"
            value={val}
            onChange={(e) => onChange(nodeId, name, e.target.value)}
            placeholder={placeholder || (isFolderPicker ? 'Select folder…' : 'Select file…')}
          />
          <button
            className="nodrag browse-btn"
            onClick={() => openFileBrowser(
              (path) => onChange(nodeId, name, path),
              { selectionMode: isFolderPicker ? 'folder' : 'file' },
            )}
          >
            Browse
          </button>
        </div>
      </>
    );
  }

  if (type === 'STRING' && opts?.color_picker) {
    const normalized = typeof val === 'string' && /^#[0-9a-fA-F]{6}$/.test(val)
      ? val
      : '#ff0000';
    return (
      <>
        {!hideLabel && <label>{label}</label>}
        <input
          className="nodrag widget-color-input"
          type="color"
          value={normalized}
          onChange={(e) => onChange(nodeId, name, e.target.value)}
        />
      </>
    );
  }

  if (type === 'BUTTON') {
    const updates = opts?.set_widgets && typeof opts.set_widgets === 'object'
      ? Object.entries(opts.set_widgets)
      : [];

    return (
      <button
        className="nodrag widget-button"
        type="button"
        onClick={() => {
          for (const [targetName, targetValue] of updates) {
            onChange(nodeId, targetName, targetValue);
          }
        }}
      >
        {formatUiLabel(opts?.label || name)}
      </button>
    );
  }

  if (opts?.text_input) {
    return (
      <TextInputValueBox
        val={val}
        placeholder={placeholder || opts?.placeholder || ''}
        nodeId={nodeId}
        name={name}
        label={label}
        hideLabel={hideLabel || !!opts.hide_label}
        onChange={onChange}
      />
    );
  }

  if (type === 'FLOAT') {
    if (opts?.slider) {
      const rawMin = opts?.min_widget ? widgetValues?.[opts.min_widget] : opts?.min;
      const rawMax = opts?.max_widget ? widgetValues?.[opts.max_widget] : opts?.max;
      const parsedMin = Number(rawMin);
      const parsedMax = Number(rawMax);
      let sliderMin = Number.isFinite(parsedMin) ? parsedMin : 0;
      let sliderMax = Number.isFinite(parsedMax) ? parsedMax : 1;
      if (sliderMax < sliderMin) [sliderMin, sliderMax] = [sliderMax, sliderMin];
      const step = opts?.step ?? 0.01;
      const numericVal = Number(val);
      const clampedVal = Number.isFinite(numericVal)
        ? Math.min(sliderMax, Math.max(sliderMin, numericVal))
        : sliderMin;

      return (
        <>
          {!hideLabel && <label>{label}</label>}
          <div className="slider-control">
            <input
              className="nodrag slider-input"
              type="range"
              min={sliderMin}
              max={sliderMax}
              step={step}
              value={clampedVal}
              onChange={(e) => onChange(nodeId, name, parseFloat(e.target.value))}
            />
            <span className="slider-value">{clampedVal.toFixed(4)}</span>
          </div>
        </>
      );
    }

    return (
      <>
        {!hideLabel && <label>{label}</label>}
        <DraggableNumber
          value={val || 0}
          step={opts?.step ?? 0.01}
          min={opts?.min}
          max={opts?.max}
          precision={4}
          onChange={(v) => onChange(nodeId, name, v)}
        />
      </>
    );
  }

  if (type === 'INT') {
    return (
      <>
        {!hideLabel && <label>{label}</label>}
        <DraggableNumber
          value={val || 0}
          step={opts?.step ?? 1}
          min={opts?.min}
          max={opts?.max}
          precision={0}
          onChange={(v) => onChange(nodeId, name, v)}
        />
      </>
    );
  }

  if (type === 'BOOLEAN') {
    return (
      <>
        {!hideLabel && <label>{label}</label>}
        <input
          className="nodrag"
          type="checkbox"
          checked={!!val}
          onChange={(e) => onChange(nodeId, name, e.target.checked)}
        />
      </>
    );
  }

  // STRING and anything else
  return (
    <>
      {!hideLabel && <label>{label}</label>}
      <input
        className="nodrag"
        type="text"
        value={val}
        placeholder={placeholder}
        onChange={(e) => onChange(nodeId, name, e.target.value)}
      />
    </>
  );
}

export default memo(CustomNode);
