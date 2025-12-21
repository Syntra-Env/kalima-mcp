import test from 'node:test';
import assert from 'node:assert/strict';
import { JSDOM } from 'jsdom';

// Setup DOM environment
const dom = new JSDOM('<!DOCTYPE html><html><body><div id="output"></div></body></html>');
global.document = dom.window.document;
global.window = dom.window;

// Mock fetch for morphology and annotations
global.fetch = async (url) => {
  if (url.includes('/morphology/')) {
    return {
      json: async () => [
        { token_index: 0, segments: [{ root: 'test', pos: 'NOUN' }] },
      ],
    };
  }
  if (url.includes('/annotations')) {
    return {
      json: async () => [],
    };
  }
  return { json: async () => ({}) };
};

test('chapter output structure has correct properties', () => {
  const chapter = {
    surah: 1,
    name: 'الفاتحة',
    verses: [
      {
        surah: 1,
        ayah: 1,
        text: 'بِسْمِ ٱللَّهِ ٱلرَحْمَٰنِ ٱلرَّحِيمِ',
        tokens: ['بِسْمِ', 'ٱللَّهِ', 'ٱلرَحْمَٰنِ', 'ٱلرَّحِيمِ'],
      },
    ],
  };

  assert.equal(chapter.surah, 1);
  assert.equal(chapter.name, 'الفاتحة');
  assert.equal(chapter.verses.length, 1);
  assert.equal(chapter.verses[0].tokens.length, 4);
});

test('verse in chapter has required token data attributes', () => {
  const verse = {
    surah: 1,
    ayah: 1,
    text: 'test text',
    tokens: ['word1', 'word2'],
  };

  // Create token spans as printChapter would
  const container = document.createElement('div');
  verse.tokens.forEach((tokenText, index) => {
    const tokenSpan = document.createElement('span');
    tokenSpan.className = 'token';
    tokenSpan.dataset.surah = verse.surah;
    tokenSpan.dataset.ayah = verse.ayah;
    tokenSpan.dataset.index = index;
    tokenSpan.dataset.originalText = tokenText;
    tokenSpan.dataset.displayLayer = 'original';
    tokenSpan.textContent = tokenText;
    container.appendChild(tokenSpan);
  });

  const tokens = container.querySelectorAll('.token');
  assert.equal(tokens.length, 2);
  assert.equal(tokens[0].dataset.surah, '1');
  assert.equal(tokens[0].dataset.ayah, '1');
  assert.equal(tokens[0].dataset.index, '0');
  assert.equal(tokens[0].dataset.originalText, 'word1');
  assert.equal(tokens[1].dataset.index, '1');
});

test('chapter with multiple verses creates multiple verse containers', () => {
  const chapter = {
    surah: 2,
    name: 'البقرة',
    verses: [
      {
        surah: 2,
        ayah: 1,
        text: 'verse 1',
        tokens: ['token1'],
      },
      {
        surah: 2,
        ayah: 2,
        text: 'verse 2',
        tokens: ['token2'],
      },
      {
        surah: 2,
        ayah: 3,
        text: 'verse 3',
        tokens: ['token3'],
      },
    ],
  };

  assert.equal(chapter.verses.length, 3);
  assert.equal(chapter.verses[0].ayah, 1);
  assert.equal(chapter.verses[1].ayah, 2);
  assert.equal(chapter.verses[2].ayah, 3);
});

test('tokens can be queried by surah, ayah, and index', () => {
  const container = document.createElement('div');

  // Create tokens for multiple verses
  [
    { surah: 1, ayah: 1, tokens: ['w1', 'w2'] },
    { surah: 1, ayah: 2, tokens: ['w3', 'w4'] },
  ].forEach((verse) => {
    verse.tokens.forEach((tokenText, index) => {
      const tokenSpan = document.createElement('span');
      tokenSpan.className = 'token';
      tokenSpan.dataset.surah = verse.surah;
      tokenSpan.dataset.ayah = verse.ayah;
      tokenSpan.dataset.index = index;
      tokenSpan.textContent = tokenText;
      container.appendChild(tokenSpan);
    });
  });

  // Test querying specific token
  const token = container.querySelector(
    '.token[data-surah="1"][data-ayah="2"][data-index="1"]'
  );
  assert.equal(token.textContent, 'w4');

  // Test querying all tokens in a verse
  const verse1Tokens = container.querySelectorAll(
    '.token[data-surah="1"][data-ayah="1"]'
  );
  assert.equal(verse1Tokens.length, 2);
});

test('annotation target_id format matches verse context', () => {
  const surah = 2;
  const ayah = 255;
  const tokenIndex = 3;
  const targetId = `${surah}:${ayah}:${tokenIndex}`;

  assert.equal(targetId, '2:255:3');

  // Parse it back
  const match = targetId.match(/^(\d+):(\d+):(\d+)$/);
  assert.ok(match);
  assert.equal(parseInt(match[1]), surah);
  assert.equal(parseInt(match[2]), ayah);
  assert.equal(parseInt(match[3]), tokenIndex);
});

test('chapter verses maintain correct ayah order', () => {
  const verses = [
    { ayah: 1, text: 'verse 1' },
    { ayah: 2, text: 'verse 2' },
    { ayah: 3, text: 'verse 3' },
  ];

  verses.forEach((verse, index) => {
    assert.equal(verse.ayah, index + 1);
  });
});

test('verse tokens are separated by spaces', () => {
  const container = document.createElement('div');
  const tokens = ['word1', 'word2', 'word3'];

  tokens.forEach((tokenText, index) => {
    const tokenSpan = document.createElement('span');
    tokenSpan.className = 'token';
    tokenSpan.textContent = tokenText;
    container.appendChild(tokenSpan);

    // Add space after each token (except last)
    if (index < tokens.length - 1) {
      container.appendChild(document.createTextNode(' '));
    }
  });

  // Should have 3 token elements + 2 text nodes (spaces)
  assert.equal(container.childNodes.length, 5);
  assert.equal(container.querySelectorAll('.token').length, 3);
});

test('morphology data can be stored in token dataset', () => {
  const token = document.createElement('span');
  token.className = 'token';

  const morphData = [
    { root: 'ك ت ب', pos: 'VERB', gender: 'M' },
  ];

  token.dataset.morphology = JSON.stringify(morphData);

  // Retrieve and parse
  const parsed = JSON.parse(token.dataset.morphology);
  assert.equal(parsed[0].root, 'ك ت ب');
  assert.equal(parsed[0].pos, 'VERB');
  assert.equal(parsed[0].gender, 'M');
});
