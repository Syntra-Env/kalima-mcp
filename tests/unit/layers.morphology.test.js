import test from 'node:test';
import assert from 'node:assert/strict';
import { parseMorphologySegments } from '../../desktop/frontend/lib/layers/morphology.js';
import { extractLayerValue } from '../../desktop/frontend/lib/layers/render.js';

test('parseMorphologySegments: flattens SegmentView.segments by token_index', () => {
  const byToken = parseMorphologySegments([
    { token_index: 0, segments: [{ root: 'r1' }, { root: 'r2' }] },
    { token_index: 0, segments: [{ root: 'r3' }] },
  ]);
  assert.deepEqual(byToken[0].map((s) => s.root), ['r1', 'r2', 'r3']);
});

test('parseMorphologySegments: normalizes 1-based token_index to 0-based', () => {
  const byToken = parseMorphologySegments([
    { token_index: 1, segments: [{ pos: 'NOUN' }] },
    { token_index: 2, segments: [{ pos: 'VERB' }] },
  ]);
  assert.equal(byToken[0][0].pos, 'NOUN');
  assert.equal(byToken[1][0].pos, 'VERB');
});

test('extractLayerValue: joins values across segments', () => {
  const value = extractLayerValue([{ root: 'r' }, { root: 'k' }], 'root');
  assert.equal(value, 'r + k');
});

