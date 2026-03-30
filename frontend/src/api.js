/**
 * api.js — REST + WebSocket client for tono backend.
 *
 * Uses relative URLs so the Vite dev proxy (port 5173 → 8188)
 * and production same-origin serving both work transparently.
 */

const SESSION_STORAGE_KEY = 'tono-session-id';

let _sessionId = null;
let _ws = null;
let _handler = null;
let _reconnectTimer = null;

function generateSessionId() {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }
  return `session-${Math.random().toString(36).slice(2)}-${Date.now().toString(36)}`;
}

export function getSessionId() {
  if (_sessionId) return _sessionId;

  if (typeof window === 'undefined') {
    _sessionId = 'session-test-runner';
    return _sessionId;
  }

  try {
    const stored = window.sessionStorage?.getItem(SESSION_STORAGE_KEY);
    if (stored) {
      _sessionId = stored;
      return _sessionId;
    }
  } catch {
    // Fall through to in-memory session id generation.
  }

  _sessionId = generateSessionId();
  try {
    window.sessionStorage?.setItem(SESSION_STORAGE_KEY, _sessionId);
  } catch {
    // Ignore storage failures and keep the in-memory id.
  }
  return _sessionId;
}

function withSessionHeaders(init = {}) {
  const headers = new Headers(init.headers || {});
  headers.set('X-Argonode-Session', getSessionId());
  return { ...init, headers };
}

async function sessionFetch(input, init) {
  return fetch(input, withSessionHeaders(init));
}

export async function getNodes() {
  const r = await sessionFetch('/nodes');
  if (!r.ok) throw new Error(`GET /nodes failed: ${r.status}`);
  return r.json();
}

export async function getFiles() {
  const r = await sessionFetch('/files');
  if (!r.ok) return [];
  return r.json();
}

export async function createUploadFolder(relativePath) {
  const r = await sessionFetch('/upload-folder', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ path: relativePath }),
  });
  if (!r.ok) throw new Error(`Create folder failed: ${r.status}`);
  return r.json();
}

export async function uploadFile(file, { relativePath = '' } = {}) {
  const fd = new FormData();
  if (relativePath) fd.append('relative_path', relativePath);
  fd.append('file', file);
  const r = await sessionFetch('/upload', { method: 'POST', body: fd });
  if (!r.ok) {
    const text = await r.text();
    throw new Error(`Upload failed (${r.status}): ${text}`);
  }
  return r.json();
}

export async function uploadPlugin(file) {
  const fd = new FormData();
  fd.append('file', file);
  const r = await fetch('/upload-plugin', { method: 'POST', body: fd });
  if (r.status === 404) {
    throw new Error('Plugin upload is not available in this build.');
  }
  if (!r.ok) {
    const text = await r.text();
    throw new Error(text || `Upload failed (${r.status})`);
  }
  return r.json();
}

export async function getChannels(filepath) {
  const r = await sessionFetch(`/channels?file=${encodeURIComponent(filepath)}`);
  if (!r.ok) return [{ name: 'field', type: 'DATA_FIELD' }];
  return r.json();
}

export async function getFolderFiles(folderpath) {
  const r = await sessionFetch(`/folder-files?folder=${encodeURIComponent(folderpath)}`);
  if (!r.ok) return [];
  return r.json();
}

export async function runPrompt(prompt) {
  const r = await sessionFetch('/prompt', {
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

export function setMessageHandler(fn) {
  _handler = fn;
}

export function initWS() {
  if (_ws && _ws.readyState < 2) return;

  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const session = encodeURIComponent(getSessionId());
  _ws = new WebSocket(`${protocol}//${window.location.host}/ws?session=${session}`);

  _ws.onopen = () => {
    console.log('[tono] WebSocket connected');
  };

  _ws.onclose = () => {
    console.log('[tono] WebSocket closed, reconnecting in 3s…');
    clearTimeout(_reconnectTimer);
    _reconnectTimer = setTimeout(() => initWS(), 3000);
  };

  _ws.onerror = (e) => {
    console.error('[tono] WebSocket error', e);
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
