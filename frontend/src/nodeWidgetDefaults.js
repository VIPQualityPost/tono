import { DATA_TYPES } from './constants.js';

export function getDefaultWidgetValue(spec) {
  const [type, opts] = Array.isArray(spec) ? spec : [spec, {}];
  if (DATA_TYPES.has(type)) return undefined;
  if (type === 'BUTTON') return undefined;
  if (Array.isArray(type)) {
    if (typeof opts?.default === 'string' && type.includes(opts.default)) {
      return opts.default;
    }
    return type[0];
  }
  return opts?.default ?? '';
}

export function buildDefaultWidgetValues(definition) {
  const widgetValues = {};
  const required = definition?.input?.required || {};
  for (const [name, spec] of Object.entries(required)) {
    const value = getDefaultWidgetValue(spec);
    if (value !== undefined) {
      widgetValues[name] = value;
    }
  }
  return widgetValues;
}
