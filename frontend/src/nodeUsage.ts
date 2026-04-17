const STORAGE_KEY = 'tono_node_usage_counts';

let counts: Record<string, number> = loadFromStorage();

function loadFromStorage(): Record<string, number> {
  if (typeof localStorage === 'undefined') return {};
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== 'object') return {};
    return parsed;
  } catch {
    return {};
  }
}

function persist(): void {
  if (typeof localStorage === 'undefined') return;
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(counts));
  } catch {
    // ignore
  }
}

export function recordUsage(className: string): void {
  counts = { ...counts, [className]: (counts[className] || 0) + 1 };
  persist();
}

export function getUsageCount(className: string): number {
  return counts[className] || 0;
}

export function pickWeightedRandom(classNames: string[]): string | null {
  if (classNames.length === 0) return null;
  const weights = classNames.map((cn) => 1 / (1 + (counts[cn] || 0)));
  const total = weights.reduce((a, b) => a + b, 0);
  let r = Math.random() * total;
  for (let i = 0; i < classNames.length; i++) {
    r -= weights[i];
    if (r <= 0) return classNames[i];
  }
  return classNames[classNames.length - 1];
}
