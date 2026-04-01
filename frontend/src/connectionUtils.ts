// ── Connection utility functions ───────────────────────────────────────
// Pure functions extracted from App.jsx so they can be independently tested.

import { socketSpecAcceptsType } from './constants.ts';
import type { InputSpec, TonoNode } from './types.ts';

// ── Handle ID helpers ─────────────────────────────────────────────────

export function getHandleType(handleId: string): string {
  return handleId.split('::')[2];
}

export function getInputName(handleId: string): string {
  return handleId.split('::')[1];
}

export function getOutputSlot(handleId: string): number {
  return parseInt(handleId.split('::')[1], 10);
}

export function encodeProxyHandleRef(handleId: string): string {
  return encodeURIComponent(String(handleId || ''));
}

export function decodeProxyHandleRef(encoded: string): string {
  try {
    return decodeURIComponent(String(encoded || ''));
  } catch {
    return String(encoded || '');
  }
}

export function parseGroupProxyHandle(handleId: string) {
  const text = String(handleId || '');
  if (!text.startsWith('group-proxy::')) return null;
  const parts = text.split('::');
  if (parts.length < 5) return null;
  return {
    direction: parts[1],
    nodeId: parts[2],
    type: parts[3],
    realHandle: decodeProxyHandleRef(parts.slice(4).join('::')),
  };
}

export function getConnectionHandleType(handleId: string): string {
  const proxy = parseGroupProxyHandle(handleId);
  return proxy?.type || getHandleType(handleId);
}

export function getResolvedHandleRef(nodeId: string, handleId: string) {
  const proxy = parseGroupProxyHandle(handleId);
  return {
    nodeId: proxy?.nodeId || nodeId,
    handleId: proxy?.realHandle || handleId,
    type: proxy?.type || getHandleType(handleId),
  };
}

export function getNodeInputSpecForHandle(node: TonoNode, handleId: string): InputSpec | null {
  const definition = node?.data?.definition;
  if (!definition?.input) return null;
  const inputName = getInputName(handleId);
  return definition.input.required?.[inputName]
    || definition.input.optional?.[inputName]
    || null;
}

// ── Type compatibility ────────────────────────────────────────────────

export function outputTypeCanConnectToTarget(outputType: string, targetSpecOrType: InputSpec | string, outputAcceptedTypes: string[] = []) {
  if (socketSpecAcceptsType(outputType, targetSpecOrType)) {
    return true;
  }
  // Polymorphic output: the output socket declares it can also produce the target type
  if (outputAcceptedTypes.length > 0) {
    const targetType = Array.isArray(targetSpecOrType) ? targetSpecOrType[0] : targetSpecOrType;
    if (outputAcceptedTypes.includes(targetType as string)) return true;
  }
  return outputType === 'ANNOTATION_SOURCE'
    && !socketSpecAcceptsType('ANNOTATION_SOURCE', targetSpecOrType)
    && (
      socketSpecAcceptsType('DATA_FIELD', targetSpecOrType)
      || socketSpecAcceptsType('IMAGE', targetSpecOrType)
    );
}

export function resolveOutputTypeForTarget(outputType: string, targetSpecOrType: InputSpec | string): string {
  if (outputType !== 'ANNOTATION_SOURCE') {
    return outputType;
  }
  if (socketSpecAcceptsType('ANNOTATION_SOURCE', targetSpecOrType)) {
    return 'ANNOTATION_SOURCE';
  }
  if (socketSpecAcceptsType('DATA_FIELD', targetSpecOrType)) {
    return 'DATA_FIELD';
  }
  if (socketSpecAcceptsType('IMAGE', targetSpecOrType)) {
    return 'IMAGE';
  }
  return 'ANNOTATION_SOURCE';
}

// ── Pure connection validation ────────────────────────────────────────
// Extracted from the isValidConnection useCallback so it can be unit-tested
// without a ReactFlow context. Pass a `getNodeFn` that mirrors reactFlow.getNode.

interface ConnectionParams {
  source: string;
  sourceHandle: string;
  target: string;
  targetHandle: string;
}

export function checkConnectionValid(connection: ConnectionParams, getNodeFn: (id: string) => TonoNode | undefined) {
  const srcType = getConnectionHandleType(connection.sourceHandle);
  const resolvedTarget = getResolvedHandleRef(connection.target, connection.targetHandle);
  const targetNode = getNodeFn(resolvedTarget.nodeId);
  const targetSpec = (targetNode ? getNodeInputSpecForHandle(targetNode, resolvedTarget.handleId) : null) || resolvedTarget.type;
  if (socketSpecAcceptsType(srcType, targetSpec)) return true;
  // Polymorphic output: check if the source output declares it can produce the target type
  const srcProxy = parseGroupProxyHandle(connection.sourceHandle);
  const srcNodeId = srcProxy ? srcProxy.nodeId : connection.source;
  const srcHandleId = srcProxy ? srcProxy.realHandle : connection.sourceHandle;
  const srcNode = getNodeFn(srcNodeId);
  const srcSlot = getOutputSlot(srcHandleId);
  const srcAcceptedTypes = srcNode?.data?.definition?.output_accepted_types?.[srcSlot] || [];
  const targetTypeRaw = Array.isArray(targetSpec) ? targetSpec[0] : targetSpec;
  const targetType = Array.isArray(targetTypeRaw) ? targetTypeRaw[0] : targetTypeRaw;
  return Array.isArray(srcAcceptedTypes) && srcAcceptedTypes.includes(targetType);
}
