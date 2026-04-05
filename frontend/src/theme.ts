/**
 * Theme manager. Three user-visible modes:
 *   - 'light'  — force light palette
 *   - 'dark'   — force dark palette
 *   - 'auto'   — follow the OS's prefers-color-scheme (default)
 *
 * The active palette is selected by setting data-theme on <html> to either
 * 'light' or 'dark'. auto mode resolves via matchMedia and re-applies on
 * system changes. The user's chosen mode is persisted in localStorage.
 */

export type Theme = 'light' | 'dark' | 'auto';

const STORAGE_KEY = 'tono_theme';

const systemMedia = typeof window !== 'undefined' && window.matchMedia
  ? window.matchMedia('(prefers-color-scheme: light)')
  : null;

export function getStoredTheme(): Theme {
  if (typeof localStorage === 'undefined') return 'auto';
  const raw = localStorage.getItem(STORAGE_KEY);
  if (raw === 'light' || raw === 'dark' || raw === 'auto') return raw;
  return 'auto';
}

export function setStoredTheme(theme: Theme): void {
  if (typeof localStorage === 'undefined') return;
  localStorage.setItem(STORAGE_KEY, theme);
}

/** Resolve a Theme (possibly 'auto') to a concrete palette. */
export function resolveTheme(theme: Theme): 'light' | 'dark' {
  if (theme === 'auto') {
    return systemMedia?.matches ? 'light' : 'dark';
  }
  return theme;
}

/** Write data-theme on <html>, which drives the CSS overrides. */
export function applyTheme(theme: Theme): void {
  if (typeof document === 'undefined') return;
  const resolved = resolveTheme(theme);
  document.documentElement.dataset.theme = resolved;
}

type ThemeListener = (theme: Theme, resolved: 'light' | 'dark') => void;
const listeners = new Set<ThemeListener>();

/**
 * Initialise theming on startup. Reads the stored preference, applies it,
 * and wires up a listener so that 'auto' mode tracks OS changes at runtime.
 * Call once, as early as possible (before first paint) from the entry point.
 */
export function initTheme(): Theme {
  const theme = getStoredTheme();
  applyTheme(theme);

  if (systemMedia) {
    systemMedia.addEventListener('change', () => {
      if (getStoredTheme() === 'auto') {
        applyTheme('auto');
        for (const cb of listeners) cb('auto', resolveTheme('auto'));
      }
    });
  }

  return theme;
}

/** Change the theme (persist + apply + notify subscribers). */
export function setTheme(theme: Theme): void {
  setStoredTheme(theme);
  applyTheme(theme);
  const resolved = resolveTheme(theme);
  for (const cb of listeners) cb(theme, resolved);
}

/** Cycle auto → light → dark → auto. Returns the new value. */
export function cycleTheme(): Theme {
  const order: Theme[] = ['auto', 'light', 'dark'];
  const current = getStoredTheme();
  const next = order[(order.indexOf(current) + 1) % order.length];
  setTheme(next);
  return next;
}

/** Subscribe to theme changes. Returns an unsubscribe function. */
export function subscribeTheme(cb: ThemeListener): () => void {
  listeners.add(cb);
  return () => listeners.delete(cb);
}
