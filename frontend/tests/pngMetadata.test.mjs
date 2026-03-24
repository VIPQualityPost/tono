import test from 'node:test';
import assert from 'node:assert/strict';

import { embedWorkflow, extractWorkflow } from '../src/pngMetadata.js';

const PNG_BASE64 = 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aF9sAAAAASUVORK5CYII=';

function makePngBlob() {
  return new Blob([Buffer.from(PNG_BASE64, 'base64')], { type: 'image/png' });
}

function crc32(bytes) {
  const table = new Uint32Array(256);
  for (let i = 0; i < 256; i++) {
    let c = i;
    for (let j = 0; j < 8; j++) {
      c = (c & 1) ? (0xEDB88320 ^ (c >>> 1)) : (c >>> 1);
    }
    table[i] = c;
  }

  let crc = 0xFFFFFFFF;
  for (let i = 0; i < bytes.length; i++) {
    crc = table[(crc ^ bytes[i]) & 0xFF] ^ (crc >>> 8);
  }
  return (crc ^ 0xFFFFFFFF) >>> 0;
}

function buildChunk(type, payload) {
  const typeBytes = new TextEncoder().encode(type);
  const crcInput = new Uint8Array(4 + payload.length);
  crcInput.set(typeBytes, 0);
  crcInput.set(payload, 4);

  const chunk = new Uint8Array(12 + payload.length);
  const view = new DataView(chunk.buffer);
  view.setUint32(0, payload.length);
  chunk.set(typeBytes, 4);
  chunk.set(payload, 8);
  view.setUint32(8 + payload.length, crc32(crcInput));
  return chunk;
}

async function insertTextChunk(blob, workflow) {
  const png = new Uint8Array(await blob.arrayBuffer());
  const encoder = new TextEncoder();
  const key = encoder.encode('workflow');
  const text = encoder.encode(JSON.stringify(workflow));
  const payload = new Uint8Array(key.length + 1 + text.length);
  payload.set(key, 0);
  payload.set(text, key.length + 1);
  const chunk = buildChunk('tEXt', payload);

  let pos = 8;
  while (pos < png.length) {
    const len = new DataView(png.buffer, pos, 4).getUint32(0);
    const type = String.fromCharCode(png[pos + 4], png[pos + 5], png[pos + 6], png[pos + 7]);
    if (type === 'IEND') break;
    pos += 12 + len;
  }

  const out = new Uint8Array(png.length + chunk.length);
  out.set(png.subarray(0, pos), 0);
  out.set(chunk, pos);
  out.set(png.subarray(pos), pos + chunk.length);
  return new Blob([out], { type: 'image/png' });
}

test('embedWorkflow roundtrips workflow data through an iTXt chunk', async () => {
  const workflow = {
    version: 1,
    nodes: [
      {
        id: '1',
        type: 'custom',
        position: { x: 12, y: 34 },
        data: { className: 'DemoNode', widgetValues: { title: 'naïve café', sigma: 'β' } },
      },
    ],
    edges: [],
  };

  const embedded = await embedWorkflow(makePngBlob(), workflow);
  const extracted = await extractWorkflow(embedded);
  const bytes = new Uint8Array(await embedded.arrayBuffer());

  assert.deepEqual(extracted, workflow);
  assert.match(Buffer.from(bytes).toString('latin1'), /iTXt/);
});

test('extractWorkflow still supports legacy tEXt metadata chunks', async () => {
  const workflow = { version: 1, legacy: true, nodes: [], edges: [] };
  const legacyBlob = await insertTextChunk(makePngBlob(), workflow);

  const extracted = await extractWorkflow(legacyBlob);

  assert.deepEqual(extracted, workflow);
});

test('extractWorkflow returns the last workflow chunk when an image is re-saved', async () => {
  const first = { version: 1, name: 'old', nodes: [], edges: [] };
  const second = { version: 1, name: 'new', nodes: [], edges: [] };

  const once = await embedWorkflow(makePngBlob(), first);
  const twice = await embedWorkflow(once, second);
  const extracted = await extractWorkflow(twice);

  assert.deepEqual(extracted, second);
});
