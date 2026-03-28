export function sortNodesForParentOrder(nodes) {
  const list = Array.isArray(nodes) ? nodes.filter(Boolean) : [];
  const entries = list.map((node) => ({ id: String(node.id), node }));
  const byId = new Map(entries.map((entry) => [entry.id, entry]));
  const visiting = new Set();
  const visited = new Set();
  const ordered = [];

  function visit(entry) {
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
