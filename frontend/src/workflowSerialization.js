import { sanitizeRuntimeValuesForPersistence } from './runtimeValuePersistence.js';

export function serializeWorkflowState(nodes, edges) {
  const compactObject = (value) => {
    if (!value || typeof value !== 'object') return null;
    const entries = Object.entries(value);
    return entries.length > 0 ? Object.fromEntries(entries) : null;
  };
  const getExtraData = (data) => compactObject(Object.fromEntries(
    Object.entries(data || {}).filter(([key]) => ![
      'label',
      'className',
      'widgetValues',
      'runtimeValues',
      'definition',
      'previewImage',
      'tableRows',
      'meshData',
      'overlay',
      'scalarValue',
      'processingTimeMs',
      'warning',
    ].includes(key))
  ));
  const getRuntimeValues = (node) => compactObject(
    sanitizeRuntimeValuesForPersistence(node.data?.className, node.data?.runtimeValues),
  );

  return {
    version: 1,
    nodes: nodes.map((node) => {
      const runtimeValues = getRuntimeValues(node);
      return {
        id: node.id,
        type: node.type || 'custom',
        position: node.position,
        ...(node.className ? { className: node.className } : {}),
        ...(node.parentId ? { parentId: node.parentId } : {}),
        ...(node.extent ? { extent: node.extent } : {}),
        ...(node.hidden ? { hidden: true } : {}),
        ...(node.style ? { style: node.style } : {}),
        dragHandle: node.dragHandle || '.drag-handle',
        data: {
          label: node.data?.label || node.data?.className || 'Node',
          className: node.data?.className || '',
          widgetValues: node.data?.widgetValues || {},
          ...(runtimeValues ? { runtimeValues } : {}),
          ...(getExtraData(node.data) ? { extraData: getExtraData(node.data) } : {}),
          output: node.data?.definition?.output || [],
          output_name: node.data?.definition?.output_name || [],
        },
      };
    }),
    edges: edges.map((edge) => ({
      id: edge.id,
      source: edge.source,
      sourceHandle: edge.sourceHandle,
      target: edge.target,
      targetHandle: edge.targetHandle,
      ...(edge.style ? { style: edge.style } : {}),
      ...(edge.hidden ? { hidden: true } : {}),
      ...(edge.data ? { data: edge.data } : {}),
    })),
  };
}
