import { sortNodesForParentOrder } from './nodeHierarchy.ts';
import { sanitizeRuntimeValuesForPersistence } from './runtimeValuePersistence.ts';

function mergeDefinition(nodeData, defs) {
  const savedData = nodeData || {};
  const registryDefinition = savedData.className ? defs[savedData.className] : null;
  return registryDefinition || null;
}

function getSocketType(inputDef) {
  if (!inputDef) return null;
  const [type] = Array.isArray(inputDef) ? inputDef : [inputDef];
  return Array.isArray(type) ? type[0] : type;
}

function getInputEntries(definition) {
  return [
    ...Object.entries(definition?.input?.required || {}),
    ...Object.entries(definition?.input?.optional || {}),
  ];
}

function sanitizeWidgetValues(widgetValues, definition, preservedPaths) {
  const nextValues = { ...(widgetValues || {}) };

  getInputEntries(definition).forEach(([inputName, inputDef]) => {
    const type = getSocketType(inputDef);
    if (type === 'FILE_PICKER' || type === 'FOLDER_PICKER') {
      if (preservedPaths && preservedPaths.has(nextValues[inputName])) return;
      nextValues[inputName] = '';
    }
  });

  return nextValues;
}

export function hydrateWorkflowState(data, defs = {}, { preservedPaths } = {}) {
  const loadedNodes = Array.isArray(data?.nodes) ? data.nodes : [];
  const loadedEdges = Array.isArray(data?.edges) ? data.edges : [];

  const nodes = sortNodesForParentOrder(loadedNodes.map((node) => {
    const definition = mergeDefinition(node.data, defs);

    return {
      ...node,
      type: node.type || 'custom',
      className: node.className,
      parentId: node.parentId,
      extent: node.extent,
      hidden: !!node.hidden,
      style: node.style,
      dragHandle: node.dragHandle || '.drag-handle',
      data: {
        ...node.data,
        label: node.data?.label || node.data?.className || 'Node',
        widgetValues: sanitizeWidgetValues(node.data?.widgetValues, definition, preservedPaths),
        runtimeValues: sanitizeRuntimeValuesForPersistence(
          node.data?.className,
          node.data?.runtimeValues,
        ),
        ...(node.data?.extraData || {}),
        definition,
        previewImage: null,
        tableRows: null,
        meshData: null,
        overlay: null,
        scalarValue: null,
        processingTimeMs: null,
        warning: null,
      },
    };
  }));

  const edges = loadedEdges.map((edge) => ({ ...edge }));

  const nextNodeId = Math.max(0, ...loadedNodes.map((node) => parseInt(node.id, 10) || 0)) + 1;

  return {
    nodes,
    edges,
    nextNodeId,
  };
}
