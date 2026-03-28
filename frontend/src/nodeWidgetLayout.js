export function formatUiLabel(text) {
  return String(text ?? '')
    .replace(/_/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .toLowerCase();
}

function normalizeInputNames(raw) {
  if (!raw) return [];
  return (Array.isArray(raw) ? raw : [raw])
    .map((value) => String(value))
    .filter((value) => value.length > 0);
}

export function getWidgetCombinedInputName(widget, dataInputByName) {
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

export function buildCombinedInputNameByWidgetName(widgets, dataInputs) {
  const dataInputByName = new Map((dataInputs || []).map((input) => [input.name, input]));
  const combinedInputNameByWidgetName = new Map();

  for (const widget of widgets || []) {
    const combinedInputName = getWidgetCombinedInputName(widget, dataInputByName);
    if (combinedInputName) {
      combinedInputNameByWidgetName.set(widget.name, combinedInputName);
    }
  }

  return combinedInputNameByWidgetName;
}
