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

test('renderConcordanceSummary shows match count and verse count', () => {
  const el = renderConcordanceSummary({
    matches: [
      { surah: 2, ayah: 255, tokens: [] },
      { surah: 3, ayah: 42, tokens: [] },
    ],
    total: 5,
  });
  assert.equal(el.textContent, 'Found 5 matches in 2 verses');
});

test('renderConcordanceSummary handles single match', () => {
  const el = renderConcordanceSummary({
    matches: [
      { surah: 2, ayah: 255, tokens: [] },
    ],
    total: 1,
  });
  assert.equal(el.textContent, 'Found 1 match in 1 verse');
});

test('renderConcordanceSummary shows no matches when empty', () => {
  const el = renderConcordanceSummary({
    matches: [],
    total: 0,
  });
  assert.equal(el.textContent, 'No matches');
});
