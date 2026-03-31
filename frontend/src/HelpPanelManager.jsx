import React, { useEffect, useState } from 'react';
import ReactDOM from 'react-dom';
import { marked } from 'marked';

function JournalTab({ content, onChange }) {
  const [isEditing, setIsEditing] = useState(false);
  const renderedHtml = content?.trim() ? marked.parse(content) : '';

  return (
    <div className="node-help-journal">
      <div className="node-help-journal-toolbar">
        <button
          className="node-help-journal-toggle"
          onClick={() => setIsEditing((e) => !e)}
        >
          {isEditing ? 'Preview' : 'Edit'}
        </button>
        {isEditing && (
          <span className="node-help-journal-hint">Ctrl+Enter to preview</span>
        )}
      </div>
      {isEditing ? (
        <textarea
          className="node-help-journal-textarea nowheel"
          value={content || ''}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
              e.preventDefault();
              setIsEditing(false);
            }
          }}
          placeholder="Write your notes here (Markdown supported)…"
          // eslint-disable-next-line jsx-a11y/no-autofocus
          autoFocus
        />
      ) : (
        <div
          className="node-help-panel-body node-help-journal-preview nowheel"
          onDoubleClick={() => setIsEditing(true)}
          // eslint-disable-next-line react/no-danger
          dangerouslySetInnerHTML={renderedHtml ? { __html: renderedHtml } : undefined}
        >
          {!renderedHtml && (
            <span className="node-help-journal-placeholder">Double-click to write…</span>
          )}
        </div>
      )}
    </div>
  );
}

function HelpPanelManager({ tabs, activeTab, onTabSelect, onTabClose, onTabContentChange }) {
  const [collapsed, setCollapsed] = useState(false);

  useEffect(() => {
    const handler = (e) => {
      if (e.key === 'Escape' && activeTab) onTabClose(activeTab);
    };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [activeTab, onTabClose]);

  if (tabs.length === 0) return null;

  const active = tabs.find((t) => t.label === activeTab) || tabs[0];

  return ReactDOM.createPortal(
    <div className="node-help-panel">
      {/* Tab bar */}
      <div className="node-help-tabs">
        <button
          className="node-help-fold-btn"
          onClick={() => setCollapsed((c) => !c)}
          title={collapsed ? 'Expand' : 'Collapse'}
        >
          {collapsed ? '▶' : '▼'}
        </button>
        {tabs.map((t) => (
          <div
            key={t.label}
            className={`node-help-tab${t.label === active.label ? ' active' : ''}`}
            onClick={() => onTabSelect(t.label)}
          >
            <span className="node-help-tab-label">{t.label}</span>
            <button
              className="node-help-tab-close"
              title="Close"
              onClick={(e) => { e.stopPropagation(); onTabClose(t.label); }}
            >
              ×
            </button>
          </div>
        ))}
      </div>

      {/* Content */}
      {!collapsed && (
        active.type === 'journal' ? (
          <JournalTab
            content={active.content}
            onChange={(val) => onTabContentChange(active.label, val)}
          />
        ) : (
          <div
            className="node-help-panel-body nowheel"
            // eslint-disable-next-line react/no-danger
            dangerouslySetInnerHTML={{ __html: marked.parse(active.content || '*Loading…*') }}
          />
        )
      )}
    </div>,
    document.body,
  );
}

export default HelpPanelManager;
