/**
 * api.js — REST + WebSocket client for tono backend.
 *
 * Uses relative URLs so the Vite dev proxy (port 5173 → 8188)
 * and production same-origin serving both work transparently.
 */

const SESSION_STORAGE_KEY = 'tono-session-id';

let _sessionId: string | null = null;
let _ws: WebSocket | null = null;
let _handler: ((msg: any) => void) | null = null;
let _reconnectTimer: ReturnType<typeof setTimeout> | undefined = undefined;

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

function withSessionHeaders(init: RequestInit = {}) {
  const headers = new Headers(init.headers || {});
  headers.set('X-Argonode-Session', getSessionId());
  return { ...init, headers };
}

async function sessionFetch(input: string, init?: RequestInit) {
  return fetch(input, withSessionHeaders(init));
}

/**
 * XHR wrapper used for file uploads. Unlike fetch(), XHR exposes upload
 * progress events, which the toast UI uses to draw a progress bar.
 */
function xhrRequest(
  method: string,
  url: string,
  body: XMLHttpRequestBodyInit | null,
  {
    headers = {},
    onProgress,
  }: { headers?: Record<string, string>; onProgress?: (fraction: number) => void } = {},
): Promise<{ status: number; text: string }> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open(method, url);
    for (const [k, v] of Object.entries(headers)) xhr.setRequestHeader(k, v);
    if (onProgress && xhr.upload) {
      xhr.upload.onprogress = (e) => {
        if (e.lengthComputable) onProgress(e.loaded / e.total);
      };
    }
    xhr.onload = () => resolve({ status: xhr.status, text: xhr.responseText });
    xhr.onerror = () => reject(new Error('Network error'));
    xhr.send(body);
  });
}

export async function getNodes() {
  const r = await sessionFetch('/nodes');
  if (!r.ok) throw new Error(`GET /nodes failed: ${r.status}`);
  return r.json();
}

export async function getNodeDoc(displayName: string) {
  const r = await sessionFetch(`/docs?name=${encodeURIComponent(displayName)}`);
  if (!r.ok) return null;
  return r.text();
}

export async function getFiles() {
  const r = await sessionFetch('/files');
  if (!r.ok) return [];
  return r.json();
}

export async function createUploadFolder(relativePath: string) {
  const r = await sessionFetch('/upload-folder', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ path: relativePath }),
  });
  if (!r.ok) throw new Error(`Create folder failed: ${r.status}`);
  return r.json();
}

export async function uploadFile(
  file: File,
  {
    relativePath = '',
    onProgress,
  }: { relativePath?: string; onProgress?: (fraction: number) => void } = {},
) {
  const fd = new FormData();
  if (relativePath) fd.append('relative_path', relativePath);
  fd.append('file', file);
  const { status, text } = await xhrRequest('POST', '/upload', fd, {
    headers: { 'X-Argonode-Session': getSessionId() },
    onProgress,
  });
  if (status < 200 || status >= 300) {
    throw new Error(`Upload failed (${status}): ${text}`);
  }
  try { return JSON.parse(text); } catch { return {}; }
}

export async function uploadPlugin(
  file: File,
  { onProgress }: { onProgress?: (fraction: number) => void } = {},
) {
  const fd = new FormData();
  fd.append('file', file);
  const { status, text } = await xhrRequest('POST', '/upload-plugin', fd, { onProgress });
  if (status === 404) {
    throw new Error('Plugin upload is not available in this build.');
  }
  if (status < 200 || status >= 300) {
    throw new Error(text || `Upload failed (${status})`);
  }
  try { return JSON.parse(text); } catch { return {}; }
}

export async function getChannels(filepath: string) {
  const r = await sessionFetch(`/channels?file=${encodeURIComponent(filepath)}`);
  if (!r.ok) return [{ name: 'field', type: 'DATA_FIELD' }];
  return r.json();
}

export async function getFileContent(path: string) {
  const r = await sessionFetch(`/file-content?path=${encodeURIComponent(path)}`);
  if (!r.ok) {
    const text = await r.text();
    throw new Error(`Failed to read file (${r.status}): ${text}`);
  }
  return r.arrayBuffer();
}

export async function getFolderFiles(folderpath: string) {
  const r = await sessionFetch(`/folder-files?folder=${encodeURIComponent(folderpath)}`);
  if (!r.ok) return [];
  return r.json();
}

export async function runPrompt(prompt: Record<string, unknown>) {
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

/** Fetch a saved node output via its one-shot, session-bound download token. */
export async function downloadSavedFile(token: string) {
  const r = await sessionFetch(`/download-save/${encodeURIComponent(token)}`);
  if (!r.ok) throw new Error(`Download failed: ${r.status}`);
  return r.blob();
}

export function setMessageHandler(fn: ((msg: any) => void) | null) {
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
