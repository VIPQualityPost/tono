import React, { useContext, useRef, useState, useEffect, useCallback, useMemo } from 'react';
import { NodeResizeControl, useStore } from '@xyflow/react';
import { marked } from 'marked';
import { NodeContext } from './CustomNode';

marked.use({ breaks: true, gfm: true });

const NOTE_COLORS = {
  default: { bg: '#1e293b', border: '#334155',  dot: '#475569' },
  blue:    { bg: '#0c1f3d', border: '#1d4ed8',  dot: '#3b82f6' },
  green:   { bg: '#062016', border: '#15803d',  dot: '#22c55e' },
  yellow:  { bg: '#1f1500', border: '#a16207',  dot: '#eab308' },
  red:     { bg: '#1f0808', border: '#b91c1c',  dot: '#ef4444' },
  purple:  { bg: '#160c2a', border: '#7c3aed',  dot: '#a855f7' },
};

function TextNoteNode({ id, data }) {
  const ctx = useContext(NodeContext);
  const [isEditing, setIsEditing] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  const textareaRef = useRef(null);

  const selected = useStore(
    useCallback(
      (s) => {
        const node = s.nodeLookup?.get(id) || s.nodes?.find((n) => n.id === id);
        return !!node?.selected;
      },
      [id],
    ),
  );

  const text  = data.widgetValues?.text  ?? '';
  const color = data.widgetValues?.color ?? 'default';
  const palette = NOTE_COLORS[color] ?? NOTE_COLORS.default;

  const setField = useCallback(
    (name, value) => ctx?.onWidgetChange?.(id, name, value),
    [ctx, id],
  );

  useEffect(() => {
    if (isEditing) {
      textareaRef.current?.focus();
    }
  }, [isEditing]);

  const onDoubleClick = useCallback((e) => {
    e.stopPropagation();
    setIsEditing(true);
  }, []);

  const onBlur = useCallback(() => setIsEditing(false), []);

  const onKeyDown = useCallback((e) => {
    // Ctrl/Cmd+Enter or Escape finishes editing
    if (e.key === 'Escape' || (e.key === 'Enter' && (e.ctrlKey || e.metaKey))) {
      e.preventDefault();
      setIsEditing(false);
    }
    // Tab inserts spaces
    if (e.key === 'Tab') {
      e.preventDefault();
      const ta = textareaRef.current;
      const start = ta.selectionStart;
      const end = ta.selectionEnd;
      const next = text.substring(0, start) + '  ' + text.substring(end);
      setField('text', next);
      requestAnimationFrame(() => {
        ta.selectionStart = ta.selectionEnd = start + 2;
      });
    }
  }, [text, setField]);

  const renderedHtml = useMemo(() => {
    if (!text.trim()) return '';
    return marked.parse(text);
  }, [text]);

  return (
    <>
      {selected && (
        <NodeResizeControl
          position="bottom-right"
          className="node-resize-handle"
          minWidth={160}
          minHeight={80}
        />
      )}
      <div
        className={`text-note-node drag-handle${selected ? ' selected' : ''}`}
        style={{
          background: palette.bg,
          borderColor: palette.border,
        }}
      >
        {/* Colour picker row */}
        <div className="text-note-toolbar nodrag nopan">
          <button
            className="text-note-fold-btn nodrag nopan"
            onClick={(e) => { e.stopPropagation(); setCollapsed((c) => !c); }}
            title={collapsed ? 'Expand' : 'Collapse'}
          >
            {collapsed ? '▶' : '▼'}
          </button>
          {Object.entries(NOTE_COLORS).map(([key, p]) => (
            <button
              key={key}
              title={key}
              className={`text-note-color-btn${color === key ? ' active' : ''}`}
              style={{ background: p.dot }}
              onClick={() => setField('color', key)}
            />
          ))}
          <span className="text-note-hint">
            {isEditing ? 'Ctrl+Enter or Esc to finish' : 'Double-click to edit'}
          </span>
        </div>

        {/* Content area */}
        {!collapsed && (isEditing ? (
          <textarea
            ref={textareaRef}
            className="text-note-textarea nodrag nopan nowheel"
            value={text}
            onChange={(e) => setField('text', e.target.value)}
            onBlur={onBlur}
            onKeyDown={onKeyDown}
            placeholder="Write your guide here (Markdown supported)…"
          />
        ) : (
          <div
            className="text-note-content nodrag nopan"
            onDoubleClick={onDoubleClick}
            // eslint-disable-next-line react/no-danger
            dangerouslySetInnerHTML={
              renderedHtml
                ? { __html: renderedHtml }
                : undefined
            }
          >
            {!renderedHtml && (
              <span className="text-note-placeholder">Double-click to write…</span>
            )}
          </div>
        ))}
      </div>
    </>
  );
}

export default TextNoteNode;
