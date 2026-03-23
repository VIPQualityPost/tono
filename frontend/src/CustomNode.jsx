import React, { useContext, useRef, useCallback, useState, memo, lazy, Suspense } from 'react';
import { Handle, Position } from '@xyflow/react';

const SurfaceView = lazy(() => import('./SurfaceView'));
const CrossSectionOverlay = lazy(() => import('./CrossSectionOverlay'));

// ── Constants ─────────────────────────────────────────────────────────

const DATA_TYPES = new Set(['DATA_FIELD', 'IMAGE', 'LINE', 'TABLE', 'COORD']);

const TYPE_COLORS = {
  DATA_FIELD: '#3a7abf',
  IMAGE:      '#4caf50',
  LINE:       '#ff9800',
  TABLE:      '#fdd835',
  COORD:      '#e91e63',
};

const CAT_COLORS = {
  io:       '#37474f',
  filters:  '#1a237e',
  level:    '#1b5e20',
  analysis: '#4a148c',
  grains:   '#bf360c',
  display:  '#212121',
};

// ── Context (provided by App) ─────────────────────────────────────────

export const NodeContext = React.createContext(null);

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
      widgets.push({ name, type, opts: opts || {} });
    }
  }

  for (const [name, spec] of Object.entries(optional)) {
    const [type] = Array.isArray(spec) ? spec : [spec];
    dataInputs.push({ name, type });
  }

  const outputs = def.output.map((type, i) => ({
    name: def.output_name[i] || type,
    type,
    slot: i,
  }));

  const catColor = CAT_COLORS[def.category] || '#333';
  const maxIORows = Math.max(dataInputs.length, outputs.length);

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

        {/* Widget rows */}
        {widgets.map((w) => (
          <div className="widget-row" key={w.name}>
            <WidgetControl
              widget={w}
              nodeId={id}
              value={data.widgetValues[w.name]}
              onChange={ctx.onWidgetChange}
              openFileBrowser={ctx.openFileBrowser}
            />
          </div>
        ))}

        {/* Interactive 3D surface view */}
        {data.meshData && (
          <CollapsibleSection title="3D View" defaultOpen={true}>
            <Suspense fallback={<div className="node-preview" style={{color:'#64748b',padding:4}}>Loading 3D...</div>}>
              <SurfaceView meshData={data.meshData} />
            </Suspense>
          </CollapsibleSection>
        )}

        {/* Collapsible preview image */}
        {data.previewImage && (
          <CollapsibleSection title="Preview" defaultOpen={true}>
            <div className="node-preview">
              <img src={data.previewImage} alt="preview" draggable={false} />
            </div>
          </CollapsibleSection>
        )}

        {/* Interactive cross-section overlay */}
        {data.overlay && hiddenWidgets.has('x1') && (
          <CollapsibleSection title="Cross Section" defaultOpen={true}>
            <Suspense fallback={<div className="node-preview" style={{color:'#64748b',padding:4}}>Loading...</div>}>
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
            </Suspense>
          </CollapsibleSection>
        )}

        {/* Collapsible table data */}
        {data.tableRows && data.tableRows.length > 0 && (
          <CollapsibleSection title="Table" defaultOpen={true}>
            <div className="node-table">
              {data.tableRows.map((row, i) => {
                let line;
                if (row.quantity !== undefined) {
                  const val = typeof row.value === 'number' ? row.value.toExponential(3) : row.value;
                  line = `${row.quantity}: ${val} ${row.unit || ''}`;
                } else {
                  line = Object.entries(row)
                    .slice(0, 3)
                    .map(([k, v]) => `${k}: ${typeof v === 'number' ? v.toExponential(2) : v}`)
                    .join('  ');
                }
                return <div key={i} className="table-line">{line}</div>;
              })}
            </div>
          </CollapsibleSection>
        )}
      </div>
    </div>
  );
}

// ── Widget renderer ───────────────────────────────────────────────────

function WidgetControl({ widget, nodeId, value, onChange, openFileBrowser }) {
  const { name, type, opts } = widget;
  const val = value ?? opts?.default ?? '';

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

  if (type === 'FLOAT') {
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
