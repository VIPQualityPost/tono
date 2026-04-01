import type { InputSpec, InputOptions } from './types.ts';

// ── Shared type & color constants ─────────────────────────────────────

export const DATA_TYPES = new Set([
  'DATA_FIELD', 'IMAGE', 'LINE', 'RECORD_TABLE', 'DATA_TABLE',
  'COORD', 'ANNOTATION_SOURCE', 'COLORMAP',
  'MESH_MODEL', 'FONT', 'FILE_PATH', 'DIRECTORY', 'COORDPAIR',
]);

export const SOCKET_WIDGET_TYPES = new Set(['FLOAT', 'INT']);

export const TYPE_COLORS: Record<string, string> = {
  DATA_FIELD:    '#3a7abf',
  IMAGE:         '#00ff08a0',
  LINE:          '#ffbe5c',
  RECORD_TABLE: '#35e2fd',
  DATA_TABLE:  '#ff7474',
  COORD:         '#e91ed1',
  COORDPAIR:     '#5cb861',
  FLOAT:         '#ab3197',
  INT:           '#ffffff',
  ANNOTATION_SOURCE: '#06b6d4',
  COLORMAP:      '#f472b6',
  MESH_MODEL:    '#14b8a6',
  FONT:          '#fb7185',
  FILE_PATH:     '#f59e0b',
  DIRECTORY:     '#f97316',
};

export const CAT_COLORS: Record<string, string> = {
  Input:           '#37474f',
  Display:         '#212121',
  Overlay:         '#0f766e',
  Geometry:        '#0d9488',
  Filter:          '#1a237e',
  Spectral:        '#4c1d95',
  'Level & Correct': '#1b5e20',
  Measure:         '#4a148c',
  Mask:            '#7c2d12',
  Grains:    '#bf360c',
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
