import { sortNodesForParentOrder } from './nodeHierarchy.ts';
import { sanitizeRuntimeValuesForPersistence } from './runtimeValuePersistence.ts';
import type { NodeDefsRegistry, NodeDefinition, InputSpec, SerializedWorkflow } from './types';

function mergeDefinition(nodeData: Record<string, unknown> | undefined, defs: NodeDefsRegistry): NodeDefinition | null {
  const savedData = nodeData || {};
  const registryDefinition = savedData.className ? defs[savedData.className as string] : null;
  return registryDefinition || null;
}

function getSocketType(inputDef: InputSpec | undefined) {
  if (!inputDef) return null;
  const [type] = Array.isArray(inputDef) ? inputDef : [inputDef];
  return Array.isArray(type) ? type[0] : type;
}

function getInputEntries(definition: NodeDefinition | null) {
  return [
    ...Object.entries(definition?.input?.required || {}),
    ...Object.entries(definition?.input?.optional || {}),
  ];
}

function sanitizeWidgetValues(widgetValues: Record<string, unknown> | undefined, definition: NodeDefinition | null, preservedPaths: Set<unknown> | undefined) {
  const nextValues = { ...(widgetValues || {}) };

  getInputEntries(definition).forEach(([inputName, inputDef]: [string, InputSpec]) => {
    const type = getSocketType(inputDef);
    if (type === 'FILE_PICKER' || type === 'FOLDER_PICKER') {
      if (preservedPaths && preservedPaths.has(nextValues[inputName])) return;
      nextValues[inputName] = '';
    }
  });

  return nextValues;
}

export function hydrateWorkflowState(data: SerializedWorkflow | null | undefined, defs: NodeDefsRegistry = {}, { preservedPaths }: { preservedPaths?: Set<unknown> } = {}) {
  const loadedNodes = Array.isArray(data?.nodes) ? data.nodes : [];
  const loadedEdges = Array.isArray(data?.edges) ? data.edges : [];

  const nodes = sortNodesForParentOrder(loadedNodes.map((node) => {
    const definition = mergeDefinition(node.data, defs);

    const restoredStyle = { ...(node.style || {}) };
    if (node.width && !restoredStyle.width) restoredStyle.width = node.width;
    if (node.height && !restoredStyle.height) restoredStyle.height = node.height;

    return {
      ...node,
      type: node.type || 'custom',
      className: node.className,
      parentId: node.parentId,
      extent: node.extent,
      hidden: !!node.hidden,
      style: restoredStyle,
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
