import test from 'node:test';
import assert from 'node:assert/strict';

import {
  applySIPrefix,
  formatDisplayUnit,
  formatTableRowCell,
  getTableColumns,
} from '../src/valueFormatting.ts';

test('getTableColumns hides companion record-table unit columns', () => {
  const columns = getTableColumns([
    {
      grain_id: 1,
      area_m2: 2.5e-12,
      area_m2_unit: 'm^2',
      mean_height: 1.5e-9,
      mean_height_unit: 'm',
      bbox: '(0,0)-(2,2)',
    },
  ]);

  assert.deepEqual(columns, ['grain_id', 'area_m2', 'mean_height', 'bbox']);
});

test('formatTableRowCell appends companion units inline for record-table values', () => {
  const row = {
    area_m2: 2.5e-12,
    area_m2_unit: 'm^2',
    mean_height: 1.5e-9,
    mean_height_unit: 'm',
  };

  assert.equal(formatTableRowCell(row, 'area_m2'), '2.5 um²');
  assert.equal(formatTableRowCell(row, 'mean_height'), '1.5 nm');
});

test('formatDisplayUnit renders exponent markers as superscripts', () => {
  assert.equal(formatDisplayUnit('px^2'), 'px²');
  assert.equal(formatDisplayUnit('(V)^2 m^2'), '(V)² m²');
});

test('applySIPrefix scales squared units using squared SI prefixes', () => {
  assert.deepEqual(applySIPrefix(3e-18, 'm^2'), { valueText: '3', unitText: 'nm²' });
  assert.deepEqual(applySIPrefix(3e-9, 'm^2'), { valueText: '3000', unitText: 'um²' });
  assert.deepEqual(applySIPrefix(144, 'px^2'), { valueText: '144', unitText: 'px²' });
});
