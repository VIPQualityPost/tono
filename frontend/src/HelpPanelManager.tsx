import React, { useEffect, useMemo, useRef, useState } from 'react';
import ReactDOM from 'react-dom';
import { marked } from 'marked';

interface Heading {
  level: number;
  text: string;
  id: string;
  children: Heading[];
}

interface HelpTab {
  label: string;
  type: string;
  content: string;
}

// ── Parse headings from markdown source ──────────────────────────────

function parseHeadings(md: string): Heading[] {
  if (!md) return [];
  const headings: Heading[] = [];
  const lines = md.split('\n');
  for (const line of lines) {
    const m = line.match(/^(#{1,6})\s+(.+)/);
    if (m) {
      const text = m[2].replace(/[*_`~[\]]/g, '').trim();
      const id = text.toLowerCase().replace(/[^\w]+/g, '-').replace(/(^-|-$)/g, '');
      headings.push({ level: m[1].length, text, id, children: [] });
    }
  }
  return headings;
}

// ── Inject id attributes into rendered HTML headings ─────────────────

function injectHeadingIds(html: string, headings: Heading[]) {
  let idx = 0;
  return html.replace(/<(h[1-6])>/gi, (match: string, tag: string) => {
    if (idx < headings.length) {
      return `<${tag} id="${headings[idx++].id}">`;
    }
    return match;
  });
}

// ── Build a tree from flat heading list ──────────────────────────────

function buildTocTree(headings: Heading[]): Heading[] {
  const root: { children: Heading[] } = { children: [] };
  const stack: { node: { children: Heading[] }; level: number }[] = [{ node: root, level: 0 }];
  for (const h of headings) {
    const item = { ...h, children: [] };
    while (stack.length > 1 && stack[stack.length - 1].level >= h.level) stack.pop();
    stack[stack.length - 1].node.children.push(item);
    stack.push({ node: item, level: h.level });
  }
  return root.children;
}

// ── TOC sidebar component ────────────────────────────────────────────

interface TocItemProps {
  item: Heading;
  collapsed: Record<string, boolean>;
  onToggle: (id: string) => void;
  onNavigate: (id: string) => void;
}

function TocItem({ item, collapsed, onToggle, onNavigate }: TocItemProps) {
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

interface TocProps {
  headings: Heading[];
  contentRef: React.RefObject<HTMLDivElement | null>;
}

function Toc({ headings, contentRef }: TocProps) {
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>({});
  const tree = useMemo(() => buildTocTree(headings), [headings]);

  const onToggle = (id: string) => setCollapsed((prev) => ({ ...prev, [id]: !prev[id] }));

  const onNavigate = (id: string) => {
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

function useMdLinkHandler(onOpenDoc: (filename: string) => void) {
  return (e: React.MouseEvent<HTMLElement>) => {
    const a = (e.target as HTMLElement).closest('a[href]');
    if (!a) return;
    const href = a.getAttribute('href');
    if (href && /\.md$/i.test(href) && !href.startsWith('http')) {
      e.preventDefault();
      const filename = href.split('/').pop() ?? href;
      onOpenDoc(filename);
    }
  };
}

// ── Content pane with TOC ────────────────────────────────────────────

interface HelpContentProps {
  content: string;
  onOpenDoc: (filename: string) => void;
}

function HelpContent({ content, onOpenDoc }: HelpContentProps) {
  const contentRef = useRef<HTMLDivElement>(null);
  const handleClick = useMdLinkHandler(onOpenDoc);
  const md = content || '*Loading…*';
  const headings = useMemo(() => parseHeadings(md), [md]);
  const html = useMemo(() => {
    let rendered: string;
    try { rendered = marked.parse(md) as string; } catch { rendered = md; }
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

interface JournalTabProps {
  content: string;
  onChange: (value: string) => void;
  onOpenDoc: (filename: string) => void;
}

function JournalTab({ content, onChange, onOpenDoc }: JournalTabProps) {
  const [isEditing, setIsEditing] = useState(false);
  const contentRef = useRef<HTMLDivElement>(null);
  const handleClick = useMdLinkHandler(onOpenDoc);

  let renderedHtml = '';
  let headings: Heading[] = [];
  if (!isEditing && content?.trim()) {
    headings = parseHeadings(content);
    try { renderedHtml = injectHeadingIds(marked.parse(content) as string, headings); } catch { renderedHtml = content; }
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

interface HelpPanelManagerProps {
  tabs: HelpTab[];
  activeTab: string;
  onTabSelect: (label: string) => void;
  onTabClose: (label: string) => void;
  onTabContentChange: (label: string, value: string) => void;
  onOpenJournal: () => void;
  onOpenDoc: (filename: string) => void;
}

function HelpPanelManager({ tabs, activeTab, onTabSelect, onTabClose, onTabContentChange, onOpenJournal, onOpenDoc }: HelpPanelManagerProps) {
  const [collapsed, setCollapsed] = useState(false);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
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
