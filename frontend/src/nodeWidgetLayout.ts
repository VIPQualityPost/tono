import type { WidgetDescriptor } from './types.ts';

interface DataInputDescriptor {
  name: string;
  type: string | string[];
  label: string;
}

export function formatUiLabel(text: unknown): string {
  return String(text ?? '')
    .replace(/_/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .toLowerCase();
}

function normalizeInputNames(raw: unknown): string[] {
  if (!raw) return [];
  return (Array.isArray(raw) ? raw : [raw])
    .map((value) => String(value))
    .filter((value) => value.length > 0);
}

export function getWidgetCombinedInputName(widget: WidgetDescriptor | null | undefined, dataInputByName: Map<string, DataInputDescriptor> | null | undefined) {
  const explicitInputName = normalizeInputNames(widget?.opts?.top_socket_input)[0];
  if (explicitInputName && dataInputByName?.has(explicitInputName)) {
    return explicitInputName;
  }

  const widgetLabel = formatUiLabel(widget?.opts?.label || widget?.name);
  if (!widgetLabel) return null;

  for (const inputName of normalizeInputNames(widget?.opts?.hide_when_input_connected)) {
    const input = dataInputByName?.get(inputName);
    if (!input) continue;
    const inputLabel = formatUiLabel(input.label || input.name);
    if (inputLabel === widgetLabel) {
      return input.name;
    }
  }

  return null;
}

export function buildCombinedInputNameByWidgetName(widgets: WidgetDescriptor[], dataInputs: DataInputDescriptor[]) {
  const dataInputByName = new Map((dataInputs || []).map((input: DataInputDescriptor) => [input.name, input]));
  const combinedInputNameByWidgetName = new Map();

  for (const widget of widgets || []) {
    const combinedInputName = getWidgetCombinedInputName(widget, dataInputByName);
    if (combinedInputName) {
      combinedInputNameByWidgetName.set(widget.name, combinedInputName);
    }
  }

  return combinedInputNameByWidgetName;
}
