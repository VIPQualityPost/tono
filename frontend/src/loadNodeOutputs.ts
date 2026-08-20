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

interface ChannelLike {
  name: string | undefined;
  type: string | undefined;
}

/**
 * Build the dynamic `output`/`output_name` arrays for a load node from its
 * resolved channels. Image exposes the resolved path as a leading FILE_PATH
 * output, so every channel slot is shifted by one; ImageDemo has no path
 * output and exposes the channels directly. Keeping the two in lockstep with
 * the backend OUTPUTS tuple is what makes slot N connect to channel N's data.
 */
export function buildLoadNodeOutputs(className: string | undefined, channels: ChannelLike[]): { output: string[]; outputName: string[] } {
  const channelTypes = channels.map((channel) => channel.type || 'DATA_FIELD');
  const channelNames = channels.map((channel) => channel.name || 'field');
  if (className === 'ImageDemo') {
    return { output: channelTypes, outputName: channelNames };
  }
  return { output: ['FILE_PATH', ...channelTypes], outputName: ['path', ...channelNames] };
}
