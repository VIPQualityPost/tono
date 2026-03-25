function mergeDefinition(nodeData, defs) {
  const savedData = nodeData || {};
  const savedDefinition = savedData.definition && typeof savedData.definition === 'object'
    ? savedData.definition
    : null;
  const registryDefinition = savedData.className ? defs[savedData.className] : null;
  const definition = registryDefinition || savedDefinition;

  if (!definition) return null;

  const output = Array.isArray(savedData.output)
    ? savedData.output
    : (Array.isArray(savedDefinition?.output) ? savedDefinition.output : null);
  const outputName = Array.isArray(savedData.output_name)
    ? savedData.output_name
    : (Array.isArray(savedDefinition?.output_name) ? savedDefinition.output_name : null);

  return {
    ...definition,
    ...(output ? { output } : {}),
    ...(outputName ? { output_name: outputName } : {}),
  };
}

export function hydrateWorkflowState(data, defs = {}) {
  const loadedNodes = Array.isArray(data?.nodes) ? data.nodes : [];
  const loadedEdges = Array.isArray(data?.edges) ? data.edges : [];

  const nodes = loadedNodes.map((node) => ({
    ...node,
    type: node.type || 'custom',
    dragHandle: node.dragHandle || '.drag-handle',
    data: {
      ...node.data,
      label: node.data?.label || node.data?.className || 'Node',
      widgetValues: node.data?.widgetValues || {},
      definition: mergeDefinition(node.data, defs),
      previewImage: null,
      tableRows: null,
      meshData: null,
      overlay: null,
      scalarValue: null,
    },
  }));

  const nextNodeId = Math.max(0, ...loadedNodes.map((node) => parseInt(node.id, 10) || 0)) + 1;

  return {
    nodes,
    edges: loadedEdges,
    nextNodeId,
  };
}
