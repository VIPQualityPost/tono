// ── Shared type & color constants ─────────────────────────────────────

export const DATA_TYPES = new Set([
  'DATA_FIELD', 'IMAGE', 'LINE', 'MEASURE_TABLE', 'RECORD_TABLE', 'ANY_TABLE',
  'COORD', 'STATS_SOURCE', 'CURSOR_SOURCE', 'VALUE_SOURCE', 'ANNOTATION_SOURCE', 'COLORMAP',
  'SAVE_LAYER', 'SAVE_VALUE', 'MESH_MODEL', 'FONT', 'FILE_PATH', 'DIRECTORY', 'COORDPAIR',
]);

export const SOCKET_WIDGET_TYPES = new Set(['FLOAT', 'INT']);

export const TYPE_COLORS = {
  DATA_FIELD:    '#3a7abf',
  IMAGE:         '#00ff08a0',
  LINE:          '#ffbe5c',
  MEASURE_TABLE: '#35e2fd',
  RECORD_TABLE:  '#fbbf24',
  ANY_TABLE:     '#67e8f9',
  COORD:         '#e91ed1',
  COORDPAIR:     '#5c7cb8',
  FLOAT:         '#ab3197',
  INT:           '#38bdf8',
  STATS_SOURCE:  '#c084fc',
  CURSOR_SOURCE: '#a78bfa',
  VALUE_SOURCE:  '#60a5fa',
  ANNOTATION_SOURCE: '#06b6d4',
  COLORMAP:      '#f472b6',
  SAVE_LAYER:    '#22c55e',
  SAVE_VALUE:    '#4ade80',
  MESH_MODEL:    '#14b8a6',
  FONT:          '#fb7185',
  FILE_PATH:     '#f59e0b',
  DIRECTORY:     '#f97316',
};

export const CAT_COLORS = {
  io:        '#37474f',
  filters:   '#1a237e',
  modify:    '#0f766e',
  level:     '#1b5e20',
  analysis:  '#4a148c',
  particles: '#bf360c',
  display:   '#212121',
};

export const SOCKET_COMPATIBILITY = {
  STATS_SOURCE:  new Set(['DATA_FIELD', 'IMAGE', 'LINE', 'RECORD_TABLE']),
  CURSOR_SOURCE: new Set(['DATA_FIELD', 'LINE']),
  ANY_TABLE:     new Set(['MEASURE_TABLE', 'RECORD_TABLE']),
  VALUE_SOURCE:  new Set(['FLOAT', 'MEASURE_TABLE']),
  ANNOTATION_SOURCE: new Set(['DATA_FIELD', 'IMAGE']),
  SAVE_LAYER:    new Set(['DATA_FIELD', 'IMAGE']),
  SAVE_VALUE:    new Set(['DATA_FIELD', 'IMAGE', 'LINE', 'MEASURE_TABLE', 'RECORD_TABLE', 'MESH_MODEL', 'FLOAT']),
  FLOAT:         new Set(['INT']),
  INT:           new Set(['FLOAT']),
  LINE:          new Set(['COORDPAIR']),
};

// Colors used in Canvas 2D / toBlob contexts where CSS var() is unavailable.
export const CANVAS_COLORS = {
  bgDeep:      '#0f172a',
  maskStroke:  '#ffffff',
  maskOverlay: 'rgba(255, 59, 59, 0.16)',
};
