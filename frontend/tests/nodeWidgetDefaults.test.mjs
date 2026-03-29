import test from 'node:test';
import assert from 'node:assert/strict';

import { buildDefaultWidgetValues, getDefaultWidgetValue } from '../src/nodeWidgetDefaults.js';

test('enum widget defaults honor opts.default instead of the first option', () => {
  assert.equal(
    getDefaultWidgetValue([['line', 'rectangle', 'circle', 'arrow'], { default: 'arrow' }]),
    'arrow',
  );
});

test('buildDefaultWidgetValues keeps non-data required widget defaults', () => {
  assert.deepEqual(
    buildDefaultWidgetValues({
      input: {
        required: {
          input: ['ANNOTATION_SOURCE', { label: 'Input' }],
          table: ['RECORD_TABLE', { accepted_types: ['DATA_TABLE'] }],
          shape: [['line', 'rectangle', 'circle', 'arrow'], { default: 'arrow' }],
          stroke_color: ['STRING', { default: '#ff0000', color_picker: true }],
          stroke_width: ['INT', { default: 3 }],
        },
      },
    }),
    {
      shape: 'arrow',
      stroke_color: '#ff0000',
      stroke_width: 3,
    },
  );
});
