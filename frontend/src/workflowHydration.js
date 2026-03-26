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

function getSocketType(inputDef) {
  if (!inputDef) return null;
  const [type] = Array.isArray(inputDef) ? inputDef : [inputDef];
  return Array.isArray(type) ? type[0] : type;
}

function getInputType(definition, inputName) {
  const required = definition?.input?.required || {};
  const optional = definition?.input?.optional || {};
  return getSocketType(required[inputName] ?? optional[inputName]);
}

function getInputEntries(definition) {
  return [
    ...Object.entries(definition?.input?.required || {}),
    ...Object.entries(definition?.input?.optional || {}),
  ];
}

function sanitizeWidgetValues(widgetValues, definition) {
  const nextValues = { ...(widgetValues || {}) };

  getInputEntries(definition).forEach(([inputName, inputDef]) => {
    const type = getSocketType(inputDef);
    if (type === 'FILE_PICKER' || type === 'FOLDER_PICKER') {
      nextValues[inputName] = '';
    }
  });

  return nextValues;
}

function remapLegacyHandle(handleId, kind, nodeData) {
  if (typeof handleId !== 'string') return handleId;

  const parts = handleId.split('::');
  if (parts.length !== 3 || parts[2] !== 'TABLE') return handleId;

  if (kind === 'source' && parts[0] === 'output') {
    const outputSlot = Number.parseInt(parts[1], 10);
    const outputType = nodeData?.definition?.output?.[outputSlot];
    if (typeof outputType === 'string' && outputType !== 'TABLE') {
      return `output::${outputSlot}::${outputType}`;
    }
    return handleId;
  }

  if (kind === 'target' && parts[0] === 'input') {
    const inputType = getInputType(nodeData?.definition, parts[1]);
    if (typeof inputType === 'string' && inputType !== 'TABLE') {
      return `input::${parts[1]}::${inputType}`;
    }
  }

  return handleId;
}

export function hydrateWorkflowState(data, defs = {}) {
  const loadedNodes = Array.isArray(data?.nodes) ? data.nodes : [];
  const loadedEdges = Array.isArray(data?.edges) ? data.edges : [];

  const nodes = loadedNodes.map((node) => {
    const definition = mergeDefinition(node.data, defs);

    return {
      ...node,
      type: node.type || 'custom',
      dragHandle: node.dragHandle || '.drag-handle',
      data: {
        ...node.data,
        label: node.data?.label || node.data?.className || 'Node',
        widgetValues: sanitizeWidgetValues(node.data?.widgetValues, definition),
        definition,
        previewImage: null,
        tableRows: null,
        meshData: null,
        overlay: null,
        scalarValue: null,
      },
    };
  });

  const nodeById = new Map(nodes.map((node) => [String(node.id), node.data]));

  const edges = loadedEdges.map((edge) => ({
    ...edge,
    sourceHandle: remapLegacyHandle(edge.sourceHandle, 'source', nodeById.get(String(edge.source))),
    targetHandle: remapLegacyHandle(edge.targetHandle, 'target', nodeById.get(String(edge.target))),
  }));

  const nextNodeId = Math.max(0, ...loadedNodes.map((node) => parseInt(node.id, 10) || 0)) + 1;

  return {
    nodes,
    edges,
    nextNodeId,
  };
}
