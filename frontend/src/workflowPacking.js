/**
 * workflowPacking.js — Pack/unpack file assets into workflow JSON.
 *
 * Packed workflows embed base64-encoded file contents so they are
 * portable across machines and sessions.
 */

import * as api from './api';

const MAX_PACKED_BYTES = 100 * 1024 * 1024; // 100 MB

// ── Helpers ──────────────────────────────────────────────────────────

function arrayBufferToBase64(buffer) {
  const bytes = new Uint8Array(buffer);
  let binary = '';
  for (let i = 0; i < bytes.length; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  return btoa(binary);
}

function base64ToUint8Array(b64) {
  const binary = atob(b64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) {
    bytes[i] = binary.charCodeAt(i);
  }
  return bytes;
}

function getInputType(spec) {
  if (!spec) return null;
  const type = Array.isArray(spec) ? spec[0] : spec;
  return Array.isArray(type) ? type[0] : type;
}

function filenameFromPath(path) {
  return String(path).split('/').pop();
}

/**
 * Extract the relative path portion from a session:// URI.
 * e.g. "session://uploads/myfolder/scan.ibw" → "myfolder/scan.ibw"
 */
function sessionRelativePath(path) {
  const prefix = 'session://uploads/';
  if (path.startsWith(prefix)) return path.slice(prefix.length);
  return filenameFromPath(path);
}

// ── Pack ─────────────────────────────────────────────────────────────

/**
 * Embed referenced files into workflowData.
 *
 * @param {object} workflowData - Serialized workflow (from serializeWorkflowState)
 * @param {object} nodeDefs     - Node definition registry (nodeDefsRef.current)
 * @param {function} [onProgress] - Optional (packed, total) callback
 * @returns {object} workflowData with packedFiles added
 */
export async function packWorkflow(workflowData, nodeDefs, onProgress) {
  // 1. Collect FILE_PICKER paths only (skip FOLDER_PICKER)
  const filePaths = new Set();

  for (const node of workflowData.nodes) {
    const className = node.data?.className;
    const def = className ? nodeDefs[className] : null;
    if (!def) continue;

    const allInputs = { ...(def.input?.required || {}), ...(def.input?.optional || {}) };
    const widgetValues = node.data?.widgetValues || {};

    for (const [name, spec] of Object.entries(allInputs)) {
      const type = getInputType(spec);
      const value = String(widgetValues[name] || '').trim();
      if (!value) continue;

      if (type === 'FILE_PICKER') {
        filePaths.add(value);
      }
    }
  }

  if (filePaths.size === 0) {
    return workflowData;
  }

  // 3. Fetch each file and encode
  const packedFiles = {};
  let totalBytes = 0;
  let packed = 0;
  const total = filePaths.size;

  for (const path of filePaths) {
    try {
      const buffer = await api.getFileContent(path);
      totalBytes += buffer.byteLength;
      if (totalBytes > MAX_PACKED_BYTES) {
        throw new Error(
          `Packed workflow exceeds ${Math.round(MAX_PACKED_BYTES / 1024 / 1024)} MB limit ` +
          `(${Math.round(totalBytes / 1024 / 1024)} MB so far). ` +
          `Reduce the number or size of referenced files.`
        );
      }
      packedFiles[path] = {
        filename: filenameFromPath(path),
        data: arrayBufferToBase64(buffer),
      };
    } catch (err) {
      if (err.message.includes('limit')) throw err;
      // File may not exist (e.g. cleared path) — skip
    }
    packed++;
    if (onProgress) onProgress(packed, total);
  }

  if (Object.keys(packedFiles).length === 0) {
    return workflowData;
  }

  return {
    ...workflowData,
    packed: true,
    packedFiles,
  };
}

// ── Unpack ───────────────────────────────────────────────────────────

/**
 * Extract packed files from workflowData and upload them to the current session.
 *
 * @param {object} workflowData - Workflow data potentially containing packedFiles
 * @returns {{ workflow: object, restoredPaths: Set<string> }}
 */
export async function unpackWorkflow(workflowData) {
  const packedFiles = workflowData.packedFiles;
  if (!packedFiles || Object.keys(packedFiles).length === 0) {
    return { workflow: workflowData, restoredPaths: new Set() };
  }

  const pathMap = {};       // oldPath → newSessionPath
  const restoredPaths = new Set();

  // 1. Upload each packed file
  for (const [origPath, entry] of Object.entries(packedFiles)) {
    const bytes = base64ToUint8Array(entry.data);
    const file = new File([bytes], entry.filename);
    const relativePath = sessionRelativePath(origPath);

    try {
      const result = await api.uploadFile(file, { relativePath });
      const newPath = result.path;
      pathMap[origPath] = newPath;
      restoredPaths.add(newPath);
    } catch {
      // Upload failed — skip this file
    }
  }

  // 2. Remap widget values in nodes
  const updatedNodes = workflowData.nodes.map((node) => {
    const wv = node.data?.widgetValues;
    if (!wv) return node;

    let changed = false;
    const nextWv = { ...wv };
    for (const [key, val] of Object.entries(nextWv)) {
      if (typeof val === 'string' && pathMap[val]) {
        nextWv[key] = pathMap[val];
        changed = true;
      }
    }

    if (!changed) return node;
    return { ...node, data: { ...node.data, widgetValues: nextWv } };
  });

  // Strip packed data from the workflow to avoid storing it again on re-save
  const { packedFiles: _, packed: __, ...cleanWorkflow } = workflowData;

  return {
    workflow: { ...cleanWorkflow, nodes: updatedNodes },
    restoredPaths,
  };
}
