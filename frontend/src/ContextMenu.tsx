import React, { useState, useCallback, useEffect, useRef, useMemo } from 'react';
import { socketSpecAcceptsType } from './constants';
import { outputTypeCanConnectToTarget } from './connectionUtils';
import { compareMenuNodes, compareMenuCategories } from './canvasEvents';
import { useFavorites } from './favorites';

const FAVORITES_CATEGORY = 'favorites';

export default function ContextMenu({
  x,
  y,
  nodeDefs,
  onAdd,
  onClose,
  filterType,
  filterSpec = null,
  filterDirection,
  selectedNodeCount = 0,
  onCreateGroup = null,
}: {
  x: number;
  y: number;
  nodeDefs: Record<string, any>;
  onAdd: (className: string, def: any) => void;
  onClose: () => void;
  filterType?: string | null;
  filterSpec?: any;
  filterDirection?: string | null;
  selectedNodeCount?: number;
  onCreateGroup?: (() => void) | null;
}) {
  const favorites = useFavorites();
  const [openCat, setOpenCat] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const menuRef = useRef<HTMLDivElement | null>(null);
  const [menuPos, setMenuPos] = useState({ x, y });
  const subMenuRef = useRef<HTMLDivElement | null>(null);
  const [subPos, setSubPos] = useState({ x: 0, y: 0 });
  const catRowRefs = useRef<Record<string, HTMLDivElement | null>>({});
  const selectedItemRef = useRef<HTMLDivElement | null>(null);

  // Group by category, optionally filtering to compatible nodes
  const categories = useMemo(() => {
    const cats: Record<string, any> = {};
    for (const [className, def] of Object.entries(nodeDefs) as [string, any][]) {
      if (filterType && filterDirection) {
        if (filterDirection === 'source') {
          const req = def.input.required || {};
          const opt = def.input.optional || {};
          const allInputs = { ...req, ...opt };
          const hasMatch = Object.values(allInputs).some((spec: any) => {
            return socketSpecAcceptsType(filterType, spec);
          });
          if (!hasMatch) continue;
        } else {
          const hasMatch = def.output.some((type: string, idx: number) =>
            outputTypeCanConnectToTarget(type, filterSpec || filterType, def.output_accepted_types?.[idx] || [])
          );
          if (!hasMatch) continue;
        }
      }
      const menuCategories = Array.isArray(def.menu_categories) && def.menu_categories.length > 0
        ? def.menu_categories
        : [{
            category: def.category || 'uncategorized',
            category_order: def.category_order,
            menu_order: def.menu_order,
          }];

      for (const menuCategory of menuCategories) {
        const cat = menuCategory?.category || def.category || 'uncategorized';
        if (!cats[cat]) {
          cats[cat] = {
            name: cat,
            order: Number.isFinite(menuCategory?.category_order)
              ? menuCategory.category_order
              : Number.MAX_SAFE_INTEGER,
            items: [],
          };
        }
        cats[cat].order = Math.min(
          cats[cat].order,
          Number.isFinite(menuCategory?.category_order)
            ? menuCategory.category_order
            : Number.MAX_SAFE_INTEGER,
        );
        cats[cat].items.push({
          className,
          def,
          menu_order: Number.isFinite(menuCategory?.menu_order) ? menuCategory.menu_order : def.menu_order,
        });
      }
    }
    const sorted = Object.values(cats)
      .map((category: any) => ({
        ...category,
        items: [...category.items].sort(compareMenuNodes),
      }))
      .sort(compareMenuCategories);

    const favItems: any[] = [];
    const seenFav = new Set<string>();
    for (const category of sorted) {
      for (const item of category.items) {
        if (favorites.has(item.className) && !seenFav.has(item.className)) {
          seenFav.add(item.className);
          favItems.push(item);
        }
      }
    }
    if (favItems.length > 0) {
      return [
        { name: FAVORITES_CATEGORY, order: -Infinity, items: favItems.sort(compareMenuNodes) },
        ...sorted,
      ];
    }
    return sorted;
  }, [nodeDefs, filterDirection, filterSpec, filterType, favorites]);

  // Flat filtered list for search
  const searchResults = useMemo(() => {
    if (!search.trim()) return null;
    const q = search.toLowerCase();
    const results: { className: string; def: any }[] = [];
    const seen = new Set();
    for (const category of categories) {
      for (const { className, def } of category.items) {
        if (seen.has(className)) continue;
        const name = (def.display_name || className).toLowerCase();
        const keywords: string[] = Array.isArray(def.keywords) ? def.keywords : [];
        const keywordMatch = keywords.some((kw) => String(kw).toLowerCase().includes(q));
        if (name.includes(q) || keywordMatch) {
          results.push({ className, def });
          seen.add(className);
        }
      }
    }
    return results;
  }, [search, categories]);

  // Reset selection to top whenever results change
  useEffect(() => {
    setSelectedIndex(0);
  }, [searchResults]);

  // Scroll selected item into view
  useEffect(() => {
    selectedItemRef.current?.scrollIntoView({ block: 'nearest' });
  }, [selectedIndex]);

  const handleSearchKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (!searchResults || searchResults.length === 0) return;
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex((i) => Math.min(i + 1, searchResults.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex((i) => Math.max(i - 1, 0));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      const item = searchResults[selectedIndex];
      if (item) { onAdd(item.className, item.def); onClose(); }
    }
  }, [searchResults, selectedIndex, onAdd, onClose]);

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
    const menuRect = menuRef.current!.getBoundingClientRect();
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

  const handleCatEnter = useCallback((cat: string) => {
    setOpenCat(cat);
  }, []);

  if (categories.length === 0) {
    return (
      <div className="context-menu" ref={menuRef} style={{ left: menuPos.x, top: menuPos.y }} onClick={(e) => e.stopPropagation()}>
        <div className="context-item" style={{ color: 'var(--text-muted)' }}>No compatible nodes</div>
      </div>
    );
  }

  const catNames = categories.map((category) => category.name);
  const categoryMap = Object.fromEntries(categories.map((category) => [category.name, category.items]));

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
          if (subMenuRef.current && subMenuRef.current.contains(related as globalThis.Node | null)) return;
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
            onKeyDown={handleSearchKeyDown}
            autoFocus
          />
        </div>

        {!filterType && selectedNodeCount > 1 && typeof onCreateGroup === 'function' && (
          <div
            className="context-item"
            onClick={() => { onCreateGroup(); onClose(); }}
          >
            create group
          </div>
        )}

        {searchResults ? (
          <div className="ctx-list">
            {searchResults.length === 0 ? (
              <div className="context-item" style={{ color: 'var(--text-muted)' }}>No matches</div>
            ) : (
              searchResults.map(({ className, def }, idx) => (
                <div
                  key={className}
                  ref={idx === selectedIndex ? selectedItemRef : null}
                  className={`context-item${idx === selectedIndex ? ' context-item--selected' : ''}`}
                  onClick={() => { onAdd(className, def); onClose(); }}
                  onMouseEnter={() => setSelectedIndex(idx)}
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
                className={`ctx-cat-item${openCat === cat ? ' ctx-cat-active' : ''}${cat === FAVORITES_CATEGORY ? ' ctx-cat-favorites' : ''}`}
                onMouseEnter={() => handleCatEnter(cat)}
              >
                <span className="ctx-cat-label">
                  {cat === FAVORITES_CATEGORY ? '♥ favorites' : cat}
                </span>
                <span className="ctx-cat-arrow">▶</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Submenu rendered as a sibling, positioned at computed screen coords */}
      {openCat && categoryMap[openCat] && (
        <div
          className="context-menu ctx-submenu"
          ref={subMenuRef}
          style={{ left: subPos.x, top: subPos.y }}
          onClick={(e) => e.stopPropagation()}
          onMouseLeave={(e) => {
            const related = e.relatedTarget;
            if (menuRef.current && menuRef.current.contains(related as globalThis.Node | null)) return;
            setOpenCat(null);
          }}
        >
          {categoryMap[openCat].map(({ className, def }: { className: string; def: any }) => (
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
