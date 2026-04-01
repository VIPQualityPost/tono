export function sanitizeRuntimeValuesForPersistence(className: string | undefined, runtimeValues: Record<string, unknown> | undefined): Record<string, unknown> {
  if (!runtimeValues || typeof runtimeValues !== 'object' || Array.isArray(runtimeValues)) {
    return {};
  }

  if (className === 'View3D') {
    return {};
  }
  return { ...runtimeValues };
}
