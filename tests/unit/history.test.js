import test from 'node:test';
import assert from 'node:assert/strict';
import { recordCommandInHistory } from '../../desktop/frontend/lib/history.js';

test('recordCommandInHistory: excludes history command', () => {
  const history = [];
  assert.equal(recordCommandInHistory(history, 'history'), false);
  assert.deepEqual(history, []);
});

test('recordCommandInHistory: trims and records', () => {
  const history = [];
  assert.equal(recordCommandInHistory(history, '  read 1:1  '), true);
  assert.deepEqual(history, ['read 1:1']);
});

test('recordCommandInHistory: skips consecutive duplicates', () => {
  const history = ['read 1:1'];
  assert.equal(recordCommandInHistory(history, 'read 1:1'), false);
  assert.deepEqual(history, ['read 1:1']);
});

test('recordCommandInHistory: allows non-consecutive duplicates', () => {
  const history = ['read 1:1', 'read 2:282'];
  assert.equal(recordCommandInHistory(history, 'read 1:1'), true);
  assert.deepEqual(history, ['read 1:1', 'read 2:282', 'read 1:1']);
});

