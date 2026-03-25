import React, { useContext, useRef, useCallback, useState, useEffect, memo, lazy, Suspense } from 'react';
import { Handle, Position, useStore } from '@xyflow/react';
import LinePlotOverlay from './LinePlotOverlay';

const SurfaceView = lazy(() => import('./SurfaceView'));
const CrossSectionOverlay = lazy(() => import('./CrossSectionOverlay'));
const CropBoxOverlay = lazy(() => import('./CropBoxOverlay'));

// ── Constants ─────────────────────────────────────────────────────────

const DATA_TYPES = new Set(['DATA_FIELD', 'IMAGE', 'LINE', 'TABLE', 'COORD', 'STATS_SOURCE']);
const SOCKET_WIDGET_TYPES = new Set(['FLOAT']);

const TYPE_COLORS = {
  DATA_FIELD: '#3a7abf',
  IMAGE:      '#4caf50',
  LINE:       '#ff9800',
  TABLE:      '#fdd835',
  COORD:      '#e91e63',
  FLOAT:      '#7dd3fc',
  STATS_SOURCE:'#c084fc',
};

const CAT_COLORS = {
  io:       '#37474f',
  filters:  '#1a237e',
  modify:   '#0f766e',
  level:    '#1b5e20',
  analysis: '#4a148c',
  particles:'#bf360c',
  display:  '#212121',
};

// ── Context (provided by App) ─────────────────────────────────────────

export const NodeContext = React.createContext(null);

class PreviewBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error) {
    console.error('[argonode] preview render failed', error);
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
      <div className="node-preview" style={{ color: '#94a3b8', padding: 8 }}>
        Preview unavailable.
      </div>
    );
  }
}

// ── Draggable number input ────────────────────────────────────────────

function DraggableNumber({ value, step, min, max, precision, onChange }) {
  const [editing, setEditing] = useState(false);
  const [editText, setEditText] = useState('');
  const dragState = useRef(null);
  const elRef = useRef(null);

  const display = precision != null ? Number(value).toFixed(precision) : String(value);

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
    const rounded = precision != null
      ? parseFloat(raw.toFixed(precision))
      : Math.round(raw);
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

  const commitEdit = useCallback(() => {
    setEditing(false);
    const parsed = parseFloat(editText);
    if (!isNaN(parsed)) onChange(clamp(precision != null ? parseFloat(parsed.toFixed(precision)) : Math.round(parsed)));
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

function getTableColumns(rows) {
  const columns = [];
  for (const row of rows) {
    if (!row || typeof row !== 'object') continue;
    for (const key of Object.keys(row)) {
      if (!columns.includes(key)) columns.push(key);
    }
  }
  return columns;
}

function formatTableCell(value) {
  if (value == null) return '';
  if (typeof value === 'number') {
    if (!Number.isFinite(value)) return String(value);
    const abs = Math.abs(value);
    if (Number.isInteger(value) && abs < 1e6) return String(value);
    if ((abs > 0 && abs < 1e-3) || abs >= 1e4) return value.toExponential(3);
    return value.toFixed(4).replace(/\.?0+$/, '');
  }
  if (Array.isArray(value)) return value.join(', ');
  return String(value);
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

function getSourceTypeForInput(store, nodeId, inputName) {
  const targetHandle = `input::${inputName}::`;
  const edge = store.edges?.find((e) => e.target === nodeId && e.targetHandle?.startsWith(targetHandle));
  if (!edge?.sourceHandle) return null;
  const parts = edge.sourceHandle.split('::');
  return parts[2] || null;
}

function getSourceNodeForInput(store, nodeId, inputName) {
  const targetHandle = `input::${inputName}::`;
  const edge = store.edges?.find((e) => e.target === nodeId && e.targetHandle?.startsWith(targetHandle));
  if (!edge) return null;
  return store.nodeLookup?.get(edge.source) || store.nodes?.find((n) => n.id === edge.source) || null;
}

function widgetVisibleForSourceType(widget, sourceType) {
  const rules = widget?.opts?.show_when_source_type;
  if (!rules || typeof rules !== 'object') return true;
  const inputName = Object.keys(rules)[0];
  const allowed = Array.isArray(rules[inputName]) ? rules[inputName] : [];
  if (allowed.length === 0) return true;
  return allowed.includes(sourceType);
}

function NodeTable({ rows }) {
  const columns = getTableColumns(rows);
  if (columns.length === 0) return null;

  return (
    <div className="node-table-wrap">
      <div className="node-table-scroll">
        <table className="node-table-grid">
          <thead>
            <tr>
              {columns.map((column) => (
                <th key={column} scope="col">{column}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, rowIndex) => (
              <tr key={row.id ?? row.quantity ?? rowIndex}>
                {columns.map((column) => {
                  const value = row?.[column];
                  return (
                    <td
                      key={`${rowIndex}-${column}`}
                      className={typeof value === 'number' ? 'node-table-num' : ''}
                      title={formatTableCell(value)}
                    >
                      {formatTableCell(value)}
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

  // Parse inputs into data handles and widgets
  const required = def.input.required || {};
  const optional = def.input.optional || {};

  const dataInputs = [];
  const widgets = [];

  const hiddenWidgets = new Set();

  for (const [name, spec] of Object.entries(required)) {
    const [type, opts] = Array.isArray(spec) ? spec : [spec, {}];
    if (DATA_TYPES.has(type)) {
      dataInputs.push({ name, type });
    } else if (opts?.hidden) {
      hiddenWidgets.add(name);
    } else {
      widgets.push({ name, type, opts: opts || {}, socketType: SOCKET_WIDGET_TYPES.has(type) ? type : null });
    }
  }

  // For manual-trigger nodes (Save), show progressive optional inputs:
  // show field_N only if field_(N-1) is connected (or N==0).
  const isProgressive = def.manual_trigger;
  const connectedInputs = useStore(
    useCallback(
      (s) => {
        if (!isProgressive) return null;
        const set = new Set();
        for (const e of s.edges) {
          if (e.target === id) {
            const parts = e.targetHandle?.split('::');
            if (parts) set.add(parts[1]);
          }
        }
        return set;
      },
      [id, isProgressive],
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

  for (const [name, spec] of Object.entries(optional)) {
    const [type, opts] = Array.isArray(spec) ? spec : [spec, {}];
    if (isProgressive && DATA_TYPES.has(type)) {
      // Progressive: show this slot only if it's the first or the previous is connected
      const match = name.match(/^field_(\d+)$/);
      if (match) {
        const idx = parseInt(match[1], 10);
        if (idx === 0 || (connectedInputs && connectedInputs.has(`field_${idx - 1}`))) {
          dataInputs.push({ name, type });
        }
        continue;
      }
    }
    if (opts?.hidden) {
      hiddenWidgets.add(name);
    } else if (DATA_TYPES.has(type)) {
      dataInputs.push({ name, type });
    } else {
      widgets.push({ name, type, opts: opts || {}, socketType: SOCKET_WIDGET_TYPES.has(type) ? type : null });
    }
  }

  const outputs = def.output.map((type, i) => ({
    name: def.output_name[i] || type,
    type,
    slot: i,
  }));

  const catColor = CAT_COLORS[def.category] || '#333';
  const maxIORows = Math.max(dataInputs.length, outputs.length);
  const hasInteractiveLineOverlay = data.overlay?.kind === 'line_plot' && hiddenWidgets.has('x1');
  const overlayTitle = data.overlay?.section_title
    || (data.overlay?.kind === 'crop_box'
      ? 'Crop'
      : data.overlay?.kind === 'line_plot'
        ? 'Line Plot'
        : 'Cross Section');

  return (
    <div className="custom-node">
      {/* Title */}
      <div className="node-title drag-handle" style={{ background: catColor }}>
        {data.label}
      </div>

      <div className="node-body">
        {/* I/O rows — pair inputs[i] with outputs[i] */}
        {Array.from({ length: maxIORows }, (_, i) => {
          const inp = dataInputs[i];
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
                      style={{ background: TYPE_COLORS[inp.type] || '#999' }}
                    />
                    <span className="io-label">{inp.name}</span>
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
                      style={{ background: TYPE_COLORS[out.type] || '#999' }}
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

        {typeof data.scalarValue === 'number' && (
          <div className="node-value-display">
            <div className="node-value-label">Value</div>
            <div className="node-value-box">{formatScalarValue(data.scalarValue)}</div>
          </div>
        )}

        {/* Widget rows */}
        {widgets.filter((w) => widgetVisibleForSourceType(w, connectedSourceTypes?.[w.opts?.source_type_input || w.opts?.choices_from_table_input || Object.keys(w.opts?.show_when_source_type || {})[0]])).map((w) => (
          <div className={`widget-row${w.socketType ? ' widget-row-socket' : ''}`} key={w.name}>
            {w.socketType && (
              <Handle
                type="target"
                position={Position.Left}
                id={`input::${w.name}::${w.socketType}`}
                className="typed-handle"
                style={{ background: TYPE_COLORS[w.socketType] || '#999' }}
              />
            )}
            <WidgetControl
              widget={w}
              nodeId={id}
              value={data.widgetValues[w.name]}
              widgetValues={data.widgetValues}
              onChange={ctx.onWidgetChange}
              openFileBrowser={ctx.openFileBrowser}
            />
          </div>
        ))}

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
            <Suspense fallback={<div className="node-preview" style={{color:'#64748b',padding:4}}>Loading 3D...</div>}>
              <SurfaceView meshData={data.meshData} />
            </Suspense>
          </CollapsibleSection>
        )}

        {/* Collapsible preview image */}
        {data.previewImage && !(hasInteractiveLineOverlay && typeof data.previewImage === 'object' && data.previewImage.kind === 'line_plot') && (
          <CollapsibleSection title="Preview" defaultOpen={true}>
            <PreviewBoundary
              resetKey={typeof data.previewImage === 'string' ? data.previewImage : JSON.stringify({
                kind: data.previewImage.kind,
                len: data.previewImage.line?.length,
              })}
              fallbackImage={typeof data.previewImage === 'object' ? data.previewImage.fallback_image : null}
            >
              {typeof data.previewImage === 'string' ? (
                <div className="node-preview">
                  <img src={data.previewImage} alt="preview" draggable={false} />
                </div>
              ) : data.previewImage.kind === 'line_plot' ? (
                <LinePlotOverlay overlay={data.previewImage} interactive={false} />
              ) : null}
            </PreviewBoundary>
          </CollapsibleSection>
        )}

        {/* Interactive cross-section overlay */}
        {data.overlay && hiddenWidgets.has('x1') && (
          <CollapsibleSection title={overlayTitle} defaultOpen={true}>
            <Suspense fallback={<div className="node-preview" style={{color:'#64748b',padding:4}}>Loading...</div>}>
              {data.overlay.kind === 'line_plot' ? (
                <LinePlotOverlay
                  overlay={data.overlay}
                  x1={data.overlay.a_locked ? data.overlay.x1 : (data.widgetValues.x1 ?? data.overlay.x1)}
                  x2={data.overlay.b_locked ? data.overlay.x2 : (data.widgetValues.x2 ?? data.overlay.x2)}
                  aLocked={data.overlay.a_locked}
                  bLocked={data.overlay.b_locked}
                  nodeId={id}
                  onWidgetChange={ctx.onWidgetChange}
                />
              ) : data.overlay.kind === 'crop_box' ? (
                <CropBoxOverlay
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
          <CollapsibleSection title="Table" defaultOpen={true}>
            <NodeTable rows={data.tableRows} />
          </CollapsibleSection>
        )}
      </div>
    </div>
  );
}

// ── Widget renderer ───────────────────────────────────────────────────

function WidgetControl({ widget, nodeId, value, widgetValues, onChange, openFileBrowser }) {
  const { name, type, opts } = widget;
  const val = value ?? opts?.default ?? '';
  const dynamicSourceType = useStore(
    useCallback(
      (s) => {
        const inputName = opts?.source_type_input
          || opts?.choices_from_table_input
          || Object.keys(opts?.show_when_source_type || {})[0];
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
        if (sourceType !== 'TABLE') return [];
        const sourceNode = getSourceNodeForInput(s, nodeId, tableInputName);
        const rows = sourceNode?.data?.tableRows;
        return Array.isArray(rows) ? getTableColumns(rows) : [];
      },
      [nodeId, opts?.choices_from_table_input],
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
    if (dynamicTypeChoices.length === 0) return;
    const current = String(val ?? '');
    if (dynamicTypeChoices.includes(current)) return;
    onChange(nodeId, name, dynamicTypeChoices[0]);
  }, [dynamicTypeChoices, name, nodeId, onChange, val]);

  // Combo / enum — type itself is the array of options
  if (Array.isArray(type)) {
    return (
      <>
        <label>{name}</label>
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
        <label>{name}</label>
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
        <label>{name}</label>
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

  if (type === 'FILE_PICKER') {
    return (
      <>
        <label>{name}</label>
        <div className="file-picker-row">
          <input
            className="nodrag"
            type="text"
            value={val}
            onChange={(e) => onChange(nodeId, name, e.target.value)}
            placeholder="Select file…"
          />
          <button
            className="nodrag browse-btn"
            onClick={() => openFileBrowser((path) => onChange(nodeId, name, path))}
          >
            Browse
          </button>
        </div>
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
        {opts?.label || name}
      </button>
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
          <label>{name}</label>
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
        <label>{name}</label>
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
        <label>{name}</label>
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
        <label>{name}</label>
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
      <label>{name}</label>
      <input
        className="nodrag"
        type="text"
        value={val}
        onChange={(e) => onChange(nodeId, name, e.target.value)}
      />
    </>
  );
}

export default memo(CustomNode);
