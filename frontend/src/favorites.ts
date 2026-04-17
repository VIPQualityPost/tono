import { useSyncExternalStore } from 'react';

const STORAGE_KEY = 'tono_favorite_nodes';

let favorites: Set<string> = loadFromStorage();
const listeners = new Set<() => void>();

function loadFromStorage(): Set<string> {
  if (typeof localStorage === 'undefined') return new Set();
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return new Set();
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return new Set();
    return new Set(parsed.filter((x): x is string => typeof x === 'string'));
  } catch {
    return new Set();
  }
}

function persist(): void {
  if (typeof localStorage === 'undefined') return;
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify([...favorites]));
  } catch {
    // Storage full or disabled — ignore.
  }
}

function notify(): void {
  for (const cb of listeners) cb();
}

export function getFavorites(): Set<string> {
  return favorites;
}

export function isFavorite(className: string): boolean {
  return favorites.has(className);
}

export function toggleFavorite(className: string): void {
  const next = new Set(favorites);
  if (next.has(className)) next.delete(className);
  else next.add(className);
  favorites = next;
  persist();
  notify();
}

function subscribe(cb: () => void): () => void {
  listeners.add(cb);
  return () => {
    listeners.delete(cb);
  };
}

export function useFavorites(): Set<string> {
  return useSyncExternalStore(subscribe, getFavorites, getFavorites);
}

export function useIsFavorite(className: string): boolean {
  return useSyncExternalStore(
    subscribe,
    () => favorites.has(className),
    () => favorites.has(className),
  );
}
