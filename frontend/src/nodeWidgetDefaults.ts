import { getSpecTypeAndOptions, isDataSocketSpec } from './constants.ts';
import type { InputSpec, NodeDefinition } from './types';

export function getDefaultWidgetValue(spec: InputSpec) {
  const [type, opts] = getSpecTypeAndOptions(spec);
  if (isDataSocketSpec(spec)) return undefined;
  if (type === 'BUTTON') return undefined;
  if (Array.isArray(type)) {
    if (typeof opts?.default === 'string' && type.includes(opts.default)) {
      return opts.default;
    }
    return type[0];
  }
  return opts?.default ?? '';
}

export function buildDefaultWidgetValues(definition: NodeDefinition | null | undefined) {
  const widgetValues: Record<string, unknown> = {};
  const required = definition?.input?.required || {};
  for (const [name, spec] of Object.entries(required)) {
    const value = getDefaultWidgetValue(spec);
    if (value !== undefined) {
      widgetValues[name] = value;
    }
  }
  return widgetValues;
}
