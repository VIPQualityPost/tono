import type { InputSpec, InputOptions } from './types.ts';

// ── Shared type & color constants ─────────────────────────────────────

export const DATA_TYPES = new Set([
  'DATA_FIELD', 'IMAGE', 'LINE', 'RECORD_TABLE', 'DATA_TABLE',
  'COORD', 'ANNOTATION_SOURCE', 'COLORMAP',
  'MESH_MODEL', 'FONT', 'FILE_PATH', 'DIRECTORY', 'COORDPAIR',
]);

export const SOCKET_WIDGET_TYPES = new Set(['FLOAT', 'INT']);

export const TYPE_COLORS: Record<string, string> = {
  DATA_FIELD:    '#7d8bdc',
  IMAGE:         '#69cc6c',
  LINE:          '#ffb300',
  RECORD_TABLE: '#cf6868',
  DATA_TABLE:  '#cbcd67',
  COORD:         '#bb65c2',
  COORDPAIR:     '#bababa',
  FLOAT:         '#76bcd4',
  INT:           '#cf8e8e',
  ANNOTATION_SOURCE: '#79cab6',
  COLORMAP:      '#905454',
  MESH_MODEL:    '#6e659e',
  FONT:          '#cccf7f',
  FILE_PATH:     '#b87f7f',
  DIRECTORY:     '#90d294',
};

export const CAT_COLORS: Record<string, string> = {
  Input:           '#2c4b31',
  Display:         '#5f4e35',
  Overlay:         '#214844',
  Geometry:        '#3c2a46',
  Filter:          '#34375a',
  Spectral:        '#5f4938',
  'Level & Correct': '#553636',
  Measure:         '#382f43',
  Mask:            '#4d3c2a',
  Grains:    '#5a4703',
  Detect:          '#4b3f57',
  SPM:             '#3f4a5a',
  Probe:           '#55423a',
};

export const SOCKET_COMPATIBILITY: Record<string, Set<string>> = {
  FLOAT:         new Set(['INT']),
  INT:           new Set(['FLOAT']),
  LINE:          new Set(['COORDPAIR']),
};

const EMPTY_SOCKET_TYPE_SET: Set<string> = new Set();

export function getSpecTypeAndOptions(spec: InputSpec): [string | string[], InputOptions] {
  if (Array.isArray(spec)) {
    return [spec[0], (spec[1] || {}) as InputOptions];
  }
  return [spec, {}];
}

export function isDataSocketType(type: unknown): boolean {
  return typeof type === 'string' && DATA_TYPES.has(type);
}

export function isDataSocketSpec(spec: InputSpec): boolean {
  const [type] = getSpecTypeAndOptions(spec);
  return isDataSocketType(type);
}

export function getAcceptedSocketTypes(specOrType: InputSpec | string): Set<string> {
  const [type, opts] = Array.isArray(specOrType)
    ? getSpecTypeAndOptions(specOrType as InputSpec)
    : [specOrType, {} as InputOptions];
  if (typeof type !== 'string') {
    return EMPTY_SOCKET_TYPE_SET;
  }

  const accepted = new Set([type]);
  const explicitAccepted = Array.isArray(opts?.accepted_types) ? opts.accepted_types : [];
  for (const acceptedType of explicitAccepted) {
    if (typeof acceptedType === 'string' && acceptedType) {
      accepted.add(acceptedType);
    }
  }

  const fallbackAccepted = SOCKET_COMPATIBILITY[type];
  if (fallbackAccepted) {
    for (const acceptedType of fallbackAccepted) {
      accepted.add(acceptedType);
    }
  }

  return accepted;
}

export function socketSpecAcceptsType(sourceType: string, targetSpecOrType: InputSpec | string): boolean {
  if (typeof sourceType !== 'string' || !sourceType) return false;
  return getAcceptedSocketTypes(targetSpecOrType).has(sourceType);
}

// Colors used in Canvas 2D / toBlob contexts where CSS var() is unavailable.
export const CANVAS_COLORS = {
  bgDeep:      '#0f172a',
  maskStroke:  '#ffffff',
  maskOverlay: 'rgba(255, 59, 59, 0.16)',
};
