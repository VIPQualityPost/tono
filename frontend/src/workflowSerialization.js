export function serializeWorkflowState(nodes, edges) {
  return {
    version: 1,
    nodes: nodes.map((node) => ({
      id: node.id,
      type: node.type || 'custom',
      position: node.position,
      dragHandle: node.dragHandle || '.drag-handle',
      data: {
        label: node.data?.label || node.data?.className || 'Node',
        className: node.data?.className || '',
        widgetValues: node.data?.widgetValues || {},
      },
    })),
    edges: edges.map((edge) => ({
      id: edge.id,
      source: edge.source,
      sourceHandle: edge.sourceHandle,
      target: edge.target,
      targetHandle: edge.targetHandle,
      style: edge.style,
    })),
  };
}
