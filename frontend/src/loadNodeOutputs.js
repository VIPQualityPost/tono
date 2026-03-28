export function resolveLoadNodeChannelPath({
  explicitPath = null,
  resolvedPathInput = null,
  className = '',
  widgetValues = {},
} = {}) {
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

export function beginTrackedNodeRequest(requestVersions, nodeId) {
  const nextVersion = (requestVersions.get(nodeId) || 0) + 1;
  requestVersions.set(nodeId, nextVersion);
  return nextVersion;
}

export function isTrackedNodeRequestCurrent(requestVersions, nodeId, version) {
  return requestVersions.get(nodeId) === version;
}
