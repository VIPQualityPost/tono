/**
 * api.js — REST + WebSocket client for argonode backend.
 *
 * Uses relative URLs so the Vite dev proxy (port 5173 → 8188)
 * and production same-origin serving both work transparently.
 */

// ── REST helpers ──────────────────────────────────────────────────────

export async function getNodes() {
  const r = await fetch('/nodes');
  if (!r.ok) throw new Error(`GET /nodes failed: ${r.status}`);
  return r.json();
}

export async function getFiles() {
  const r = await fetch('/files');
  if (!r.ok) return [];
  return r.json();
}

export async function browse(dir) {
  const url = dir ? `/browse?dir=${encodeURIComponent(dir)}` : '/browse';
  const r = await fetch(url);
  if (!r.ok) throw new Error(`Browse failed: ${r.status}`);
  return r.json();
}

export async function uploadFile(file) {
  const fd = new FormData();
  fd.append('file', file);
  const r = await fetch('/upload', { method: 'POST', body: fd });
  if (!r.ok) throw new Error(`Upload failed: ${r.status}`);
  return r.json();
}

export async function getChannels(filepath) {
  const r = await fetch(`/channels?file=${encodeURIComponent(filepath)}`);
  if (!r.ok) return [{ name: 'field', type: 'DATA_FIELD' }];
  return r.json();
}

export async function runPrompt(prompt) {
  const r = await fetch('/prompt', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ prompt }),
  });
  if (!r.ok) {
    const text = await r.text();
    throw new Error(`POST /prompt failed (${r.status}): ${text}`);
  }
  return r.json();
}

// ── WebSocket ─────────────────────────────────────────────────────────

let _ws = null;
let _handler = null;
let _reconnectTimer = null;

export function setMessageHandler(fn) {
  _handler = fn;
}

export function initWS() {
  if (_ws && _ws.readyState < 2) return; // already open or connecting

  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  _ws = new WebSocket(`${protocol}//${window.location.host}/ws`);

  _ws.onopen = () => {
    console.log('[argonode] WebSocket connected');
  };

  _ws.onclose = () => {
    console.log('[argonode] WebSocket closed, reconnecting in 3s…');
    clearTimeout(_reconnectTimer);
    _reconnectTimer = setTimeout(() => initWS(), 3000);
  };

  _ws.onerror = (e) => {
    console.error('[argonode] WebSocket error', e);
  };

  _ws.onmessage = (e) => {
    try {
      const msg = JSON.parse(e.data);
      if (_handler) _handler(msg);
    } catch {
      // ignore malformed messages
    }
  };
}

export function closeWS() {
  clearTimeout(_reconnectTimer);
  if (_ws) _ws.close();
}
