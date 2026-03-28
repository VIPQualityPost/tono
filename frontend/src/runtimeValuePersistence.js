export function sanitizeRuntimeValuesForPersistence(className, runtimeValues) {
  if (!runtimeValues || typeof runtimeValues !== 'object' || Array.isArray(runtimeValues)) {
    return {};
  }

  if (className === 'View3D') {
    return {};
  }
  return { ...runtimeValues };
}
