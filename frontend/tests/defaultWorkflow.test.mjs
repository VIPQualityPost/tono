import test from 'node:test';
import assert from 'node:assert/strict';

import { embedWorkflow } from '../src/pngMetadata.ts';
import { loadDefaultWorkflowAsset } from '../src/defaultWorkflow.ts';

const PNG_BASE64 = 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aF9sAAAAASUVORK5CYII=';

function makePngBlob() {
  return new Blob([Buffer.from(PNG_BASE64, 'base64')], { type: 'image/png' });
}

test('loadDefaultWorkflowAsset prefers checked-in JSON when present', async () => {
  const workflow = { version: 1, nodes: [{ id: '1' }], edges: [] };
  const requests = [];
  const fetchImpl = async (url) => {
    requests.push(url);
    if (url === '/default-workflow.json') {
      return {
        ok: true,
        status: 200,
        async json() {
          return workflow;
        },
      };
    }
    throw new Error('PNG fallback should not be requested when JSON exists');
  };

  const loaded = await loadDefaultWorkflowAsset({ fetchImpl });

  assert.deepEqual(loaded, {
    source: '/default-workflow.json',
    format: 'json',
    workflow,
  });
  assert.deepEqual(requests, ['/default-workflow.json']);
});

test('loadDefaultWorkflowAsset falls back to PNG workflow metadata when JSON is missing', async () => {
  const workflow = { version: 1, nodes: [{ id: '2' }], edges: [] };
  const pngWithWorkflow = await embedWorkflow(makePngBlob(), workflow);
  const requests = [];
  const fetchImpl = async (url) => {
    requests.push(url);
    if (url === '/default-workflow.json') {
      return { ok: false, status: 404 };
    }
    if (url === '/default-workflow.png') {
      return {
        ok: true,
        status: 200,
        async blob() {
          return pngWithWorkflow;
        },
      };
    }
    throw new Error(`Unexpected URL ${url}`);
  };

  const loaded = await loadDefaultWorkflowAsset({ fetchImpl });

  assert.deepEqual(loaded, {
    source: '/default-workflow.png',
    format: 'png',
    workflow,
  });
  assert.deepEqual(requests, ['/default-workflow.json', '/default-workflow.png']);
});

test('loadDefaultWorkflowAsset returns null when no default workflow asset is present', async () => {
  const fetchImpl = async () => ({ ok: false, status: 404 });

  const loaded = await loadDefaultWorkflowAsset({ fetchImpl });

  assert.equal(loaded, null);
});

test('loadDefaultWorkflowAsset stays quiet when default assets are simply absent in the host runtime', async () => {
  const fetchImpl = async () => {
    throw new TypeError('Failed to fetch');
  };

  const loaded = await loadDefaultWorkflowAsset({ fetchImpl });

  assert.equal(loaded, null);
});

test('loadDefaultWorkflowAsset stays quiet when the host serves app HTML for missing default assets', async () => {
  const fetchImpl = async (url) => ({
    ok: true,
    status: 200,
    headers: {
      get(name) {
        return name.toLowerCase() === 'content-type' ? 'text/html; charset=utf-8' : null;
      },
    },
    async json() {
      throw new SyntaxError(`Unexpected token '<' while parsing ${url}`);
    },
    async blob() {
      return new Blob(['<html></html>'], { type: 'text/html' });
    },
  });

  const loaded = await loadDefaultWorkflowAsset({ fetchImpl });

  assert.equal(loaded, null);
});

test('loadDefaultWorkflowAsset stays quiet when the host reports missing assets with status 0', async () => {
  const fetchImpl = async () => ({ ok: false, status: 0 });

  const loaded = await loadDefaultWorkflowAsset({ fetchImpl });

  assert.equal(loaded, null);
});
