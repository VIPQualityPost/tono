/**
 * PNG tEXt chunk utilities for embedding/extracting workflow metadata.
 *
 * PNG files are composed of chunks: [4-byte length][4-byte type][data][4-byte CRC].
 * We add a tEXt chunk with key "workflow" containing the JSON-serialised graph,
 * inserted just before the IEND chunk.
 */

// ── CRC32 (PNG uses CRC-32/ISO 3309) ────────────────────────────────

const crcTable = new Uint32Array(256);
for (let i = 0; i < 256; i++) {
  let c = i;
  for (let j = 0; j < 8; j++) {
    c = (c & 1) ? (0xEDB88320 ^ (c >>> 1)) : (c >>> 1);
  }
  crcTable[i] = c;
}

function crc32(bytes) {
  let crc = 0xFFFFFFFF;
  for (let i = 0; i < bytes.length; i++) {
    crc = crcTable[(crc ^ bytes[i]) & 0xFF] ^ (crc >>> 8);
  }
  return (crc ^ 0xFFFFFFFF) >>> 0;
}

// ── Helpers ──────────────────────────────────────────────────────────

const PNG_SIG = [0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A];

function isPng(data) {
  if (data.length < 8) return false;
  for (let i = 0; i < 8; i++) {
    if (data[i] !== PNG_SIG[i]) return false;
  }
  return true;
}

function chunkType(data, offset) {
  return String.fromCharCode(
    data[offset + 4], data[offset + 5], data[offset + 6], data[offset + 7],
  );
}

// ── Public API ───────────────────────────────────────────────────────

/**
 * Embed a workflow object into a PNG blob as a tEXt chunk.
 * Returns a new Blob with the metadata inserted before IEND.
 */
export async function embedWorkflow(pngBlob, workflow) {
  const data = new Uint8Array(await pngBlob.arrayBuffer());
  if (!isPng(data)) throw new Error('Not a valid PNG file');

  const encoder = new TextEncoder();

  // Build tEXt payload: keyword \0 text
  const key = encoder.encode('workflow');
  const val = encoder.encode(JSON.stringify(workflow));
  const payload = new Uint8Array(key.length + 1 + val.length);
  payload.set(key, 0);
  // payload[key.length] is already 0 (null separator)
  payload.set(val, key.length + 1);

  // CRC covers type + payload
  const typeBytes = encoder.encode('tEXt');
  const forCrc = new Uint8Array(4 + payload.length);
  forCrc.set(typeBytes, 0);
  forCrc.set(payload, 4);

  // Assemble chunk: length(4) + type(4) + payload + crc(4)
  const chunk = new Uint8Array(12 + payload.length);
  const view = new DataView(chunk.buffer);
  view.setUint32(0, payload.length);
  chunk.set(typeBytes, 4);
  chunk.set(payload, 8);
  view.setUint32(8 + payload.length, crc32(forCrc));

  // Locate IEND
  let pos = 8;
  let iendPos = data.length;
  while (pos < data.length) {
    const len = new DataView(data.buffer, pos, 4).getUint32(0);
    if (chunkType(data, pos) === 'IEND') { iendPos = pos; break; }
    pos += 12 + len;
  }

  // Splice: [before IEND] + [tEXt chunk] + [IEND]
  const result = new Uint8Array(data.length + chunk.length);
  result.set(data.subarray(0, iendPos), 0);
  result.set(chunk, iendPos);
  result.set(data.subarray(iendPos), iendPos + chunk.length);

  return new Blob([result], { type: 'image/png' });
}

/**
 * Extract the workflow object from a PNG blob's tEXt chunks.
 * Returns the parsed object, or null if no "workflow" key is found.
 */
export async function extractWorkflow(pngBlob) {
  const data = new Uint8Array(await pngBlob.arrayBuffer());
  if (!isPng(data)) return null;

  const decoder = new TextDecoder();
  let pos = 8;

  while (pos + 8 <= data.length) {
    const len = new DataView(data.buffer, pos, 4).getUint32(0);
    const type = chunkType(data, pos);

    if (type === 'tEXt' && pos + 8 + len <= data.length) {
      const chunkData = data.subarray(pos + 8, pos + 8 + len);
      const nullIdx = chunkData.indexOf(0);
      if (nullIdx !== -1) {
        const k = decoder.decode(chunkData.subarray(0, nullIdx));
        if (k === 'workflow') {
          return JSON.parse(decoder.decode(chunkData.subarray(nullIdx + 1)));
        }
      }
    }

    if (type === 'IEND') break;
    pos += 12 + len;
  }

  return null;
}
