interface NodeLike {
  id: string | number;
  parentId?: string | number;
  [key: string]: unknown;
}

export function sortNodesForParentOrder<T extends NodeLike>(nodes: T[]): T[] {
  const list = Array.isArray(nodes) ? nodes.filter(Boolean) : [];
  const entries = list.map((node) => ({ id: String(node.id), node }));
  const byId = new Map(entries.map((entry) => [entry.id, entry]));
  const visiting = new Set<string>();
  const visited = new Set<string>();
  const ordered: T[] = [];

  function visit(entry: { id: string; node: T } | undefined) {
    if (!entry) return;
    const { id, node } = entry;
    if (visited.has(id) || visiting.has(id)) return;

    visiting.add(id);

    const parentId = node?.parentId ? String(node.parentId) : null;
    if (parentId) {
      visit(byId.get(parentId));
    }

    visiting.delete(id);
    visited.add(id);
    ordered.push(node);
  }

  entries.forEach((entry) => visit(entry));
  return ordered;
}
