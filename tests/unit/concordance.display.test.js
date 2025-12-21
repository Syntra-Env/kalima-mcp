import test from 'node:test';
import assert from 'node:assert/strict';
import { JSDOM } from 'jsdom';

const dom = new JSDOM(`<!DOCTYPE html><html><body></body></html>`, { url: 'http://localhost' });
global.document = dom.window.document;
global.window = dom.window;
global.HTMLElement = dom.window.HTMLElement;

const { renderConcordanceSummary } = await import(
  '../../desktop/frontend/lib/concordance/display.js'
);

test('renderConcordanceSummary shows verse counts without total when verse_counts provided', () => {
  const el = renderConcordanceSummary({
    verse_counts: [
      { verse_ref: '2:255', count: 3 },
      { verse_ref: '3:42', count: 2 },
    ],
    total: 5,
  });
  // When verse_counts exists, don't show total (it's redundant)
  assert.equal(el.textContent, 'Found in 2:255 (3), 3:42 (2)');
});

test('renderConcordanceSummary shows total matches when no verse_counts', () => {
  const el = renderConcordanceSummary({
    verses: ['2:255', '3:42'],
    total: 5,
  });
  // When only verses array (no counts), show total
  assert.equal(el.textContent, 'Found in 2:255, 3:42 (5 matches)');
});
