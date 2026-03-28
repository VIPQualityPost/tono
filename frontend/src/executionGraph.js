import { DATA_TYPES } from './constants.js';

const OMITTED_WIDGET_INPUTS_BY_CLASS = {
  View3D: new Set([
    'camera_azimuth',
    'camera_polar',
    'camera_distance',
    'camera_target_x',
    'camera_target_y',
    'camera_target_z',
  ]),
};

function getInputName(handleId) {
  return handleId.split('::')[1];
}

function getOutputSlot(handleId) {
  return parseInt(handleId.split('::')[1], 10);
}

function resolveExecutionEdge(edge) {
  const original = edge?.data?.groupProxyOriginal;
  if (!original) return edge;
  return {
    ...edge,
    source: original.source || edge.source,
    sourceHandle: original.sourceHandle || edge.sourceHandle,
    target: original.target || edge.target,
    targetHandle: original.targetHandle || edge.targetHandle,
  };
}

export function getConnectedNodeIds(edges) {
  const connectedNodeIds = new Set();
  for (const edge of edges) {
    const resolved = resolveExecutionEdge(edge);
    connectedNodeIds.add(resolved.source);
    connectedNodeIds.add(resolved.target);
  }
  return connectedNodeIds;
}

function isPreviewLoadNode(node) {
  return ['Image', 'ImageDemo'].includes(node?.data?.className);
}

function hasPreviewLoadSelection(node) {
  if (node?.data?.className === 'Image') {
    return !!String(node.data?.widgetValues?.filename || '').trim();
  }
  if (node?.data?.className === 'ImageDemo') {
    return !!String(node.data?.widgetValues?.name || '').trim();
  }
  return false;
}

function getRunnableNodeIds(nodes, edges) {
  const connectedNodeIds = getConnectedNodeIds(edges);

  const runnableNodeIds = new Set(connectedNodeIds);
  for (const node of nodes) {
    if (connectedNodeIds.has(node.id)) continue;
    if (isPreviewLoadNode(node) && hasPreviewLoadSelection(node)) {
      runnableNodeIds.add(node.id);
    }
  }

  return runnableNodeIds;
}

export function serializeExecutionGraph(nodes, edges, { excludeManualTrigger = false } = {}) {
  const runnableNodeIds = getRunnableNodeIds(nodes, edges);
  const prompt = {};

  for (const node of nodes) {
    if (!runnableNodeIds.has(node.id)) continue;

    const { className, definition, widgetValues, runtimeValues } = node.data;
    if (className === 'Group') continue;
    if (!definition) continue;
    if (excludeManualTrigger && definition.manual_trigger) continue;

    const inputs = {};
    const valueBag = { ...(widgetValues || {}), ...(runtimeValues || {}) };
    const omittedInputs = OMITTED_WIDGET_INPUTS_BY_CLASS[className] || null;

    const allWidgets = {
      ...(definition.input.required || {}),
      ...(definition.input.optional || {}),
    };
    for (const [name, spec] of Object.entries(allWidgets)) {
      if (omittedInputs?.has(name)) continue;
      const [type] = Array.isArray(spec) ? spec : [spec];
      if (DATA_TYPES.has(type)) continue;
      if (type === 'BUTTON') continue;
      if (valueBag[name] !== undefined) {
        inputs[name] = valueBag[name];
      }
    }

    const incoming = edges
      .map(resolveExecutionEdge)
      .filter((edge) => edge.target === node.id);
    for (const edge of incoming) {
      const inputName = getInputName(edge.targetHandle);
      const outputSlot = getOutputSlot(edge.sourceHandle);
      inputs[inputName] = [edge.source, outputSlot];
    }

    prompt[node.id] = { class_type: className, inputs };
  }

  return prompt;
}

export function getAutoRunnableNodes(nodes, edges) {
  const runnableNodeIds = getRunnableNodeIds(nodes, edges);
  return nodes.filter((node) => runnableNodeIds.has(node.id));
}

export function hasBlockingAutoRunInput(node, edges) {
  const def = node.data?.definition;
  if (!def || def.manual_trigger) return false;

  const required = def.input.required || {};
  for (const [name, spec] of Object.entries(required)) {
    const [type, opts] = Array.isArray(spec) ? spec : [spec, {}];
      const hiddenByConnectedInput = (() => {
        const raw = opts?.hide_when_input_connected;
        if (!raw) return false;
        const inputs = Array.isArray(raw) ? raw : [raw];
        return inputs.some((inputName) => edges.some(
          (edge) => {
            const resolved = resolveExecutionEdge(edge);
            return resolved.target === node.id && getInputName(resolved.targetHandle) === String(inputName);
          }
      ));
    })();

    if (hiddenByConnectedInput) continue;

    if (type === 'FILE_PICKER' || type === 'FOLDER_PICKER') {
      if (!node.data.widgetValues?.[name]) return true;
      continue;
    }
    if (!DATA_TYPES.has(type)) continue;
    const hasEdge = edges.some(
      (edge) => {
        const resolved = resolveExecutionEdge(edge);
        return resolved.target === node.id && getInputName(resolved.targetHandle) === name;
      }
    );
    if (!hasEdge) return true;
  }

  return false;
}
