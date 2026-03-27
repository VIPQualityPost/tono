import test from 'node:test';
import assert from 'node:assert/strict';

import { embedWorkflow, extractWorkflow } from '../src/pngMetadata.js';

const PNG_BASE64 = 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aF9sAAAAASUVORK5CYII=';

function makePngBlob() {
  return new Blob([Buffer.from(PNG_BASE64, 'base64')], { type: 'image/png' });
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

test('extractWorkflow returns the last workflow chunk when an image is re-saved', async () => {
  const first = { version: 1, name: 'old', nodes: [], edges: [] };
  const second = { version: 1, name: 'new', nodes: [], edges: [] };

  const once = await embedWorkflow(makePngBlob(), first);
  const twice = await embedWorkflow(once, second);
  const extracted = await extractWorkflow(twice);

  assert.deepEqual(extracted, second);
});
