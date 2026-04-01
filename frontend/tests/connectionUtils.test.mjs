import test from 'node:test';
import assert from 'node:assert/strict';

import {
  getHandleType,
  getInputName,
  getOutputSlot,
  encodeProxyHandleRef,
  decodeProxyHandleRef,
  parseGroupProxyHandle,
  getConnectionHandleType,
  getResolvedHandleRef,
  getNodeInputSpecForHandle,
  outputTypeCanConnectToTarget,
  resolveOutputTypeForTarget,
  checkConnectionValid,
} from '../src/connectionUtils.ts';

// ── Handle ID helpers ─────────────────────────────────────────────────

test('getHandleType extracts the type segment from a handle ID', () => {
  assert.equal(getHandleType('output::0::DATA_FIELD'), 'DATA_FIELD');
  assert.equal(getHandleType('input::field::DATA_FIELD'), 'DATA_FIELD');
  assert.equal(getHandleType('output::2::LINE'), 'LINE');
});

test('getInputName extracts the name segment from an input handle ID', () => {
  assert.equal(getInputName('input::field::DATA_FIELD'), 'field');
  assert.equal(getInputName('input::colormap::COLORMAP'), 'colormap');
});

test('getOutputSlot extracts the slot index from an output handle ID', () => {
  assert.equal(getOutputSlot('output::0::DATA_FIELD'), 0);
  assert.equal(getOutputSlot('output::3::LINE'), 3);
});

test('encodeProxyHandleRef round-trips with decodeProxyHandleRef', () => {
  const handle = 'output::0::DATA_FIELD';
  assert.equal(decodeProxyHandleRef(encodeProxyHandleRef(handle)), handle);
});

test('encodeProxyHandleRef handles null/undefined gracefully', () => {
  assert.equal(decodeProxyHandleRef(encodeProxyHandleRef(null)), '');
  assert.equal(decodeProxyHandleRef(encodeProxyHandleRef(undefined)), '');
});

test('decodeProxyHandleRef falls back for malformed percent-encoding', () => {
  // '%zz' is not valid percent-encoding; should return the raw string
  const bad = '%zz';
  const result = decodeProxyHandleRef(bad);
  assert.equal(result, bad);
});

test('decodeProxyHandleRef handles a handle with colons preserved after round-trip', () => {
  const handle = 'output::1::RECORD_TABLE';
  const encoded = encodeProxyHandleRef(handle);
  assert.ok(!encoded.includes('::'), 'colons should be encoded');
  assert.equal(decodeProxyHandleRef(encoded), handle);
});

// ── parseGroupProxyHandle ─────────────────────────────────────────────

test('parseGroupProxyHandle returns null for regular handles', () => {
  assert.equal(parseGroupProxyHandle('output::0::DATA_FIELD'), null);
  assert.equal(parseGroupProxyHandle('input::field::DATA_FIELD'), null);
  assert.equal(parseGroupProxyHandle(''), null);
  assert.equal(parseGroupProxyHandle(null), null);
});

test('parseGroupProxyHandle returns null for too-short proxy handles', () => {
  assert.equal(parseGroupProxyHandle('group-proxy::out::nodeA'), null);
  assert.equal(parseGroupProxyHandle('group-proxy::out::nodeA::DATA_FIELD'), null);
});

test('parseGroupProxyHandle parses a valid outbound proxy handle', () => {
  const inner = 'output::0::DATA_FIELD';
  const encoded = encodeProxyHandleRef(inner);
  const proxy = parseGroupProxyHandle(`group-proxy::out::node42::DATA_FIELD::${encoded}`);
  assert.ok(proxy !== null);
  assert.equal(proxy.direction, 'out');
  assert.equal(proxy.nodeId, 'node42');
  assert.equal(proxy.type, 'DATA_FIELD');
  assert.equal(proxy.realHandle, inner);
});

test('parseGroupProxyHandle parses a valid inbound proxy handle', () => {
  const inner = 'input::field::DATA_FIELD';
  const encoded = encodeProxyHandleRef(inner);
  const proxy = parseGroupProxyHandle(`group-proxy::in::node7::DATA_FIELD::${encoded}`);
  assert.ok(proxy !== null);
  assert.equal(proxy.direction, 'in');
  assert.equal(proxy.nodeId, 'node7');
  assert.equal(proxy.realHandle, inner);
});

test('parseGroupProxyHandle handles colons inside the encoded real handle', () => {
  // The real handle contains '::' which gets encoded; the join should reconstruct correctly
  const inner = 'output::2::LINE';
  const encoded = encodeProxyHandleRef(inner);
  const proxyId = `group-proxy::out::n1::LINE::${encoded}`;
  const proxy = parseGroupProxyHandle(proxyId);
  assert.equal(proxy.realHandle, inner);
});

// ── getConnectionHandleType ───────────────────────────────────────────

test('getConnectionHandleType returns type from a regular handle', () => {
  assert.equal(getConnectionHandleType('output::0::DATA_FIELD'), 'DATA_FIELD');
  assert.equal(getConnectionHandleType('input::x::LINE'), 'LINE');
});

test('getConnectionHandleType returns type from a proxy handle', () => {
  const encoded = encodeProxyHandleRef('output::0::IMAGE');
  const proxy = `group-proxy::out::nodeX::IMAGE::${encoded}`;
  assert.equal(getConnectionHandleType(proxy), 'IMAGE');
});

// ── getResolvedHandleRef ──────────────────────────────────────────────

test('getResolvedHandleRef returns identity for a regular handle', () => {
  const ref = getResolvedHandleRef('node1', 'input::field::DATA_FIELD');
  assert.equal(ref.nodeId, 'node1');
  assert.equal(ref.handleId, 'input::field::DATA_FIELD');
  assert.equal(ref.type, 'DATA_FIELD');
});

test('getResolvedHandleRef unwraps a proxy handle to the real node and handle', () => {
  const inner = 'input::field::DATA_FIELD';
  const encoded = encodeProxyHandleRef(inner);
  const proxyId = `group-proxy::in::realNode::DATA_FIELD::${encoded}`;
  const ref = getResolvedHandleRef('groupNode', proxyId);
  assert.equal(ref.nodeId, 'realNode');
  assert.equal(ref.handleId, inner);
  assert.equal(ref.type, 'DATA_FIELD');
});

// ── getNodeInputSpecForHandle ─────────────────────────────────────────

test('getNodeInputSpecForHandle returns null for missing node', () => {
  assert.equal(getNodeInputSpecForHandle(null, 'input::field::DATA_FIELD'), null);
  assert.equal(getNodeInputSpecForHandle(undefined, 'input::field::DATA_FIELD'), null);
});

test('getNodeInputSpecForHandle returns null when definition has no input', () => {
  const node = { data: { definition: {} } };
  assert.equal(getNodeInputSpecForHandle(node, 'input::field::DATA_FIELD'), null);
});

test('getNodeInputSpecForHandle finds a required input spec', () => {
  const spec = ['DATA_FIELD', {}];
  const node = { data: { definition: { input: { required: { field: spec }, optional: {} } } } };
  assert.deepEqual(getNodeInputSpecForHandle(node, 'input::field::DATA_FIELD'), spec);
});

test('getNodeInputSpecForHandle finds an optional input spec', () => {
  const spec = ['LINE', { accepted_types: ['DATA_FIELD'] }];
  const node = { data: { definition: { input: { required: {}, optional: { profile: spec } } } } };
  assert.deepEqual(getNodeInputSpecForHandle(node, 'input::profile::LINE'), spec);
});

test('getNodeInputSpecForHandle returns null for unknown input name', () => {
  const node = { data: { definition: { input: { required: { field: ['DATA_FIELD', {}] }, optional: {} } } } };
  assert.equal(getNodeInputSpecForHandle(node, 'input::nonexistent::DATA_FIELD'), null);
});

// ── outputTypeCanConnectToTarget ──────────────────────────────────────

test('outputTypeCanConnectToTarget allows exact type match', () => {
  assert.equal(outputTypeCanConnectToTarget('DATA_FIELD', 'DATA_FIELD'), true);
  assert.equal(outputTypeCanConnectToTarget('LINE', 'LINE'), true);
  assert.equal(outputTypeCanConnectToTarget('FLOAT', 'FLOAT'), true);
});

test('outputTypeCanConnectToTarget allows INT↔FLOAT via socket compatibility', () => {
  assert.equal(outputTypeCanConnectToTarget('INT', 'FLOAT'), true);
  assert.equal(outputTypeCanConnectToTarget('FLOAT', 'INT'), true);
});

test('outputTypeCanConnectToTarget rejects incompatible types with no accepted_types', () => {
  assert.equal(outputTypeCanConnectToTarget('DATA_FIELD', 'LINE'), false);
  assert.equal(outputTypeCanConnectToTarget('LINE', 'IMAGE'), false);
  assert.equal(outputTypeCanConnectToTarget('FLOAT', 'DATA_FIELD'), false);
});

test('outputTypeCanConnectToTarget allows polymorphic match via outputAcceptedTypes', () => {
  // Output socket declares LINE but can also emit DATA_FIELD
  assert.equal(outputTypeCanConnectToTarget('LINE', 'DATA_FIELD', ['DATA_FIELD']), true);
  assert.equal(outputTypeCanConnectToTarget('LINE', 'IMAGE', ['DATA_FIELD']), false);
});

test('outputTypeCanConnectToTarget allows polymorphic match from spec array', () => {
  const spec = ['DATA_FIELD', {}];
  assert.equal(outputTypeCanConnectToTarget('LINE', spec, ['DATA_FIELD']), true);
});

test('outputTypeCanConnectToTarget: ANNOTATION_SOURCE connects to DATA_FIELD and IMAGE targets', () => {
  assert.equal(outputTypeCanConnectToTarget('ANNOTATION_SOURCE', 'DATA_FIELD'), true);
  assert.equal(outputTypeCanConnectToTarget('ANNOTATION_SOURCE', 'IMAGE'), true);
});

test('outputTypeCanConnectToTarget: ANNOTATION_SOURCE connects to ANNOTATION_SOURCE target', () => {
  assert.equal(outputTypeCanConnectToTarget('ANNOTATION_SOURCE', 'ANNOTATION_SOURCE'), true);
});

test('outputTypeCanConnectToTarget: ANNOTATION_SOURCE does not connect to LINE', () => {
  assert.equal(outputTypeCanConnectToTarget('ANNOTATION_SOURCE', 'LINE'), false);
});

test('outputTypeCanConnectToTarget: empty outputAcceptedTypes does not affect result', () => {
  assert.equal(outputTypeCanConnectToTarget('DATA_FIELD', 'LINE', []), false);
});

test('outputTypeCanConnectToTarget: accepts target given as spec array', () => {
  assert.equal(
    outputTypeCanConnectToTarget('DATA_FIELD', ['DATA_FIELD', { label: 'input' }]),
    true,
  );
});

// ── resolveOutputTypeForTarget ────────────────────────────────────────

test('resolveOutputTypeForTarget returns non-ANNOTATION_SOURCE types unchanged', () => {
  assert.equal(resolveOutputTypeForTarget('DATA_FIELD', 'DATA_FIELD'), 'DATA_FIELD');
  assert.equal(resolveOutputTypeForTarget('LINE', 'LINE'), 'LINE');
  assert.equal(resolveOutputTypeForTarget('IMAGE', 'IMAGE'), 'IMAGE');
});

test('resolveOutputTypeForTarget keeps ANNOTATION_SOURCE when target accepts it', () => {
  assert.equal(resolveOutputTypeForTarget('ANNOTATION_SOURCE', 'ANNOTATION_SOURCE'), 'ANNOTATION_SOURCE');
});

test('resolveOutputTypeForTarget resolves ANNOTATION_SOURCE to DATA_FIELD when target is DATA_FIELD', () => {
  assert.equal(resolveOutputTypeForTarget('ANNOTATION_SOURCE', 'DATA_FIELD'), 'DATA_FIELD');
});

test('resolveOutputTypeForTarget resolves ANNOTATION_SOURCE to IMAGE when target is IMAGE', () => {
  assert.equal(resolveOutputTypeForTarget('ANNOTATION_SOURCE', 'IMAGE'), 'IMAGE');
});

test('resolveOutputTypeForTarget falls back to ANNOTATION_SOURCE for unknown target', () => {
  assert.equal(resolveOutputTypeForTarget('ANNOTATION_SOURCE', 'LINE'), 'ANNOTATION_SOURCE');
  assert.equal(resolveOutputTypeForTarget('ANNOTATION_SOURCE', 'RECORD_TABLE'), 'ANNOTATION_SOURCE');
});

// ── checkConnectionValid ──────────────────────────────────────────────

function makeNode(id, inputs, outputAcceptedTypes = []) {
  return {
    id,
    data: {
      definition: {
        input: inputs,
        output_accepted_types: outputAcceptedTypes,
      },
    },
  };
}

function makeGetNode(nodes) {
  const map = Object.fromEntries(nodes.map((n) => [n.id, n]));
  return (id) => map[id] ?? null;
}

test('checkConnectionValid accepts a direct type match', () => {
  const srcNode = makeNode('src', {});
  const tgtNode = makeNode('tgt', { required: { field: ['DATA_FIELD', {}] } });
  const getNode = makeGetNode([srcNode, tgtNode]);
  const conn = {
    source: 'src',
    sourceHandle: 'output::0::DATA_FIELD',
    target: 'tgt',
    targetHandle: 'input::field::DATA_FIELD',
  };
  assert.equal(checkConnectionValid(conn, getNode), true);
});

test('checkConnectionValid rejects a type mismatch with no accepted_types', () => {
  const srcNode = makeNode('src', {});
  const tgtNode = makeNode('tgt', { required: { field: ['LINE', {}] } });
  const getNode = makeGetNode([srcNode, tgtNode]);
  const conn = {
    source: 'src',
    sourceHandle: 'output::0::DATA_FIELD',
    target: 'tgt',
    targetHandle: 'input::field::LINE',
  };
  assert.equal(checkConnectionValid(conn, getNode), false);
});

test('checkConnectionValid accepts INT→FLOAT via intrinsic compatibility', () => {
  const srcNode = makeNode('src', {});
  const tgtNode = makeNode('tgt', { required: { v: ['FLOAT', {}] } });
  const getNode = makeGetNode([srcNode, tgtNode]);
  const conn = {
    source: 'src',
    sourceHandle: 'output::0::INT',
    target: 'tgt',
    targetHandle: 'input::v::FLOAT',
  };
  assert.equal(checkConnectionValid(conn, getNode), true);
});

test('checkConnectionValid accepts polymorphic output_accepted_types match', () => {
  // Source slot 0 declares it can also produce DATA_FIELD (its primary type is LINE)
  const srcNode = makeNode('src', {}, [['DATA_FIELD']]);
  const tgtNode = makeNode('tgt', { required: { field: ['DATA_FIELD', {}] } });
  const getNode = makeGetNode([srcNode, tgtNode]);
  const conn = {
    source: 'src',
    sourceHandle: 'output::0::LINE',
    target: 'tgt',
    targetHandle: 'input::field::DATA_FIELD',
  };
  assert.equal(checkConnectionValid(conn, getNode), true);
});

test('checkConnectionValid rejects when accepted_types does not include target type', () => {
  const srcNode = makeNode('src', {}, [['IMAGE']]);
  const tgtNode = makeNode('tgt', { required: { field: ['DATA_FIELD', {}] } });
  const getNode = makeGetNode([srcNode, tgtNode]);
  const conn = {
    source: 'src',
    sourceHandle: 'output::0::LINE',
    target: 'tgt',
    targetHandle: 'input::field::DATA_FIELD',
  };
  assert.equal(checkConnectionValid(conn, getNode), false);
});

test('checkConnectionValid falls back to handle type when target node is missing', () => {
  const srcNode = makeNode('src', {});
  const getNode = makeGetNode([srcNode]);
  const conn = {
    source: 'src',
    sourceHandle: 'output::0::DATA_FIELD',
    target: 'missing',
    targetHandle: 'input::field::DATA_FIELD',
  };
  // resolvedTarget.type will be DATA_FIELD, which matches the source
  assert.equal(checkConnectionValid(conn, getNode), true);
});

test('checkConnectionValid handles group proxy source handles', () => {
  const realSrcNode = makeNode('realSrc', {}, [[]]);
  const tgtNode = makeNode('tgt', { required: { field: ['DATA_FIELD', {}] } });
  const getNode = makeGetNode([realSrcNode, tgtNode]);
  const realHandle = 'output::0::DATA_FIELD';
  const proxyHandle = `group-proxy::out::realSrc::DATA_FIELD::${encodeProxyHandleRef(realHandle)}`;
  const conn = {
    source: 'groupNode',
    sourceHandle: proxyHandle,
    target: 'tgt',
    targetHandle: 'input::field::DATA_FIELD',
  };
  assert.equal(checkConnectionValid(conn, getNode), true);
});

test('checkConnectionValid handles group proxy target handles', () => {
  const srcNode = makeNode('src', {});
  const realTgtNode = makeNode('realTgt', { required: { field: ['DATA_FIELD', {}] } });
  const getNode = makeGetNode([srcNode, realTgtNode]);
  const realHandle = 'input::field::DATA_FIELD';
  const proxyHandle = `group-proxy::in::realTgt::DATA_FIELD::${encodeProxyHandleRef(realHandle)}`;
  const conn = {
    source: 'src',
    sourceHandle: 'output::0::DATA_FIELD',
    target: 'groupNode',
    targetHandle: proxyHandle,
  };
  assert.equal(checkConnectionValid(conn, getNode), true);
});
