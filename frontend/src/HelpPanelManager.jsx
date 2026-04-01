import React, { useEffect, useMemo, useRef, useState } from 'react';
import ReactDOM from 'react-dom';
import { marked } from 'marked';

// ── Parse headings from markdown source ──────────────────────────────

function parseHeadings(md) {
  if (!md) return [];
  const headings = [];
  const lines = md.split('\n');
  for (const line of lines) {
    const m = line.match(/^(#{1,6})\s+(.+)/);
    if (m) {
      const text = m[2].replace(/[*_`~\[\]]/g, '').trim();
      const id = text.toLowerCase().replace(/[^\w]+/g, '-').replace(/(^-|-$)/g, '');
      headings.push({ level: m[1].length, text, id });
    }
  }
  return headings;
}

// ── Inject id attributes into rendered HTML headings ─────────────────

function injectHeadingIds(html, headings) {
  let idx = 0;
  return html.replace(/<(h[1-6])>/gi, (match, tag) => {
    if (idx < headings.length) {
      return `<${tag} id="${headings[idx++].id}">`;
    }
    return match;
  });
}

// ── Build a tree from flat heading list ──────────────────────────────

function buildTocTree(headings) {
  const root = { children: [] };
  const stack = [{ node: root, level: 0 }];
  for (const h of headings) {
    const item = { ...h, children: [] };
    while (stack.length > 1 && stack[stack.length - 1].level >= h.level) stack.pop();
    stack[stack.length - 1].node.children.push(item);
    stack.push({ node: item, level: h.level });
  }
  return root.children;
}

// ── TOC sidebar component ────────────────────────────────────────────

function TocItem({ item, collapsed, onToggle, onNavigate }) {
  const hasChildren = item.children.length > 0;
  const isCollapsed = collapsed[item.id];
  return (
    <li className="help-toc-item">
      <div className="help-toc-row">
        {hasChildren ? (
          <button
            className="help-toc-arrow"
            onClick={(e) => { e.stopPropagation(); onToggle(item.id); }}
          >
            {isCollapsed ? '▶' : '▼'}
          </button>
        ) : (
          <span className="help-toc-arrow-spacer" />
        )}
        <a
          className="help-toc-link"
          href={`#${item.id}`}
          onClick={(e) => { e.preventDefault(); onNavigate(item.id); }}
        >
          {item.text}
        </a>
      </div>
      {hasChildren && !isCollapsed && (
        <ul className="help-toc-list">
          {item.children.map((child) => (
            <TocItem key={child.id} item={child} collapsed={collapsed} onToggle={onToggle} onNavigate={onNavigate} />
          ))}
        </ul>
      )}
    </li>
  );
}

function Toc({ headings, contentRef }) {
  const [collapsed, setCollapsed] = useState({});
  const tree = useMemo(() => buildTocTree(headings), [headings]);

  const onToggle = (id) => setCollapsed((prev) => ({ ...prev, [id]: !prev[id] }));

  const onNavigate = (id) => {
    const el = contentRef.current?.querySelector(`#${CSS.escape(id)}`);
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  if (tree.length === 0) return null;

  return (
    <nav className="help-toc nowheel">
      <ul className="help-toc-list help-toc-root">
        {tree.map((item) => (
          <TocItem key={item.id} item={item} collapsed={collapsed} onToggle={onToggle} onNavigate={onNavigate} />
        ))}
      </ul>
    </nav>
  );
}

// ── Click handler for .md links ──────────────────────────────────────

function useMdLinkHandler(onOpenDoc) {
  return (e) => {
    const a = e.target.closest('a[href]');
    if (!a) return;
    const href = a.getAttribute('href');
    if (href && /\.md$/i.test(href) && !href.startsWith('http')) {
      e.preventDefault();
      const filename = href.split('/').pop();
      onOpenDoc(filename);
    }
  };
}

// ── Content pane with TOC ────────────────────────────────────────────

function HelpContent({ content, onOpenDoc }) {
  const contentRef = useRef(null);
  const handleClick = useMdLinkHandler(onOpenDoc);
  const md = content || '*Loading…*';
  const headings = useMemo(() => parseHeadings(md), [md]);
  const html = useMemo(() => {
    let rendered;
    try { rendered = marked.parse(md); } catch { rendered = md; }
    return injectHeadingIds(rendered, headings);
  }, [md, headings]);

  return (
    <div className="help-content-row">
      <Toc headings={headings} contentRef={contentRef} />
      <div
        ref={contentRef}
        className="node-help-panel-body nowheel"
        onClick={handleClick}
        // eslint-disable-next-line react/no-danger
        dangerouslySetInnerHTML={{ __html: html }}
      />
    </div>
  );
}

// ── Journal tab ──────────────────────────────────────────────────────

function JournalTab({ content, onChange, onOpenDoc }) {
  const [isEditing, setIsEditing] = useState(false);
  const contentRef = useRef(null);
  const handleClick = useMdLinkHandler(onOpenDoc);

  let renderedHtml = '';
  let headings = [];
  if (!isEditing && content?.trim()) {
    headings = parseHeadings(content);
    try { renderedHtml = injectHeadingIds(marked.parse(content), headings); } catch { renderedHtml = content; }
  }

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
      ) : renderedHtml ? (
        <div className="help-content-row">
          <Toc headings={headings} contentRef={contentRef} />
          <div
            ref={contentRef}
            className="node-help-panel-body node-help-journal-preview nowheel"
            onDoubleClick={() => setIsEditing(true)}
            onClick={handleClick}
            // eslint-disable-next-line react/no-danger
            dangerouslySetInnerHTML={{ __html: renderedHtml }}
          />
        </div>
      ) : (
        <div
          className="node-help-panel-body node-help-journal-preview nowheel"
          onDoubleClick={() => setIsEditing(true)}
        >
          <span className="node-help-journal-placeholder">Double-click to write…</span>
        </div>
      )}
    </div>
  );
}

// ── Main panel manager ───────────────────────────────────────────────

function HelpPanelManager({ tabs, activeTab, onTabSelect, onTabClose, onTabContentChange, onOpenJournal, onOpenDoc }) {
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
        {!tabs.some((t) => t.type === 'journal') && (
          <button
            className="node-help-tab-add"
            title="Open Journal"
            onClick={onOpenJournal}
          >
            +
          </button>
        )}
      </div>

      {/* Content */}
      {!collapsed && (
        active.type === 'journal' ? (
          <JournalTab
            content={active.content}
            onChange={(val) => onTabContentChange(active.label, val)}
            onOpenDoc={onOpenDoc}
          />
        ) : (
          <HelpContent content={active.content} onOpenDoc={onOpenDoc} />
        )
      )}
    </div>,
    document.body,
  );
}

export default HelpPanelManager;
