export function resolveLoadNodeChannelPath({
  explicitPath = null as string | null,
  resolvedPathInput = null as string | null,
  className = '',
  widgetValues = {} as Record<string, unknown>,
} = {}): string {
  if (typeof explicitPath === 'string' && explicitPath) {
    return explicitPath;
  }
  if (typeof resolvedPathInput === 'string' && resolvedPathInput) {
    return resolvedPathInput;
  }
  if (className === 'Image') {
    return String(widgetValues?.filename || '');
  }
  if (className === 'ImageDemo') {
    return String(widgetValues?.name || '');
  }
  return '';
}

export function beginTrackedNodeRequest(requestVersions: Map<string, number>, nodeId: string): number {
  const nextVersion = (requestVersions.get(nodeId) || 0) + 1;
  requestVersions.set(nodeId, nextVersion);
  return nextVersion;
}

export function isTrackedNodeRequestCurrent(requestVersions: Map<string, number>, nodeId: string, version: number): boolean {
  return requestVersions.get(nodeId) === version;
}
