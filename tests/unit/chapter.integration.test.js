import test from 'node:test';
import assert from 'node:assert/strict';
import { JSDOM } from 'jsdom';

// Setup more complete DOM environment
const dom = new JSDOM(`
<!DOCTYPE html>
<html>
<body>
  <div id="output"></div>
  <input id="command-input" />
  <span id="prompt">kalima ></span>
</body>
</html>
`, { url: 'http://localhost' });

global.document = dom.window.document;
global.window = dom.window;
global.HTMLElement = dom.window.HTMLElement;

// Import the actual modules
const { parseMorphologySegments } = await import('../../desktop/frontend/lib/layers/morphology.js');
const { extractLayerValue, showLayerValue } = await import('../../desktop/frontend/lib/layers/render.js');
const { LAYERS, ANNOTATION_LAYER_INDEX } = await import('../../desktop/frontend/lib/layers/definitions.js');
const { LayerManager } = await import('../../desktop/frontend/lib/layers/manager.js');

// Mock fetch for morphology and annotations
global.fetch = async (url) => {
  if (url.includes('/morphology/1/1')) {
    return {
      json: async () => [
        {
          token_index: 0,
          segments: [{
            root: 'س م و',
            lemma: 'اسم',
            pos: 'NOUN',
            gender: 'M',
            number: 'SG',
            case: 'GEN'
          }]
        },
        {
          token_index: 1,
          segments: [{
            root: 'ا ل ه',
            lemma: 'الله',
            pos: 'NOUN',
            gender: 'M',
            number: 'SG'
          }]
        },
      ],
    };
  }
  if (url.includes('/annotations')) {
    return {
      json: async () => [
        {
          id: 'ann-1',
          target_id: '1:1:0',
          layer: 'inline',
          payload: { annotation: 'Test annotation' }
        }
      ],
    };
  }
  return { json: async () => ([]) };
};

test('LayerManager can switch layers and update token display', async () => {
  const output = document.getElementById('output');
  const layerManager = new LayerManager({ layers: LAYERS, defaultIndex: 0 });

  // Create a mock token with morphology
  const token = document.createElement('span');
  token.className = 'token';
  token.dataset.morphology = JSON.stringify([{
    root: 'ك ت ب',
    lemma: 'كتاب',
    pos: 'NOUN',
    gender: 'M',
    number: 'SG'
  }]);
  token.dataset.originalText = 'كتاب';
  token.textContent = 'كتاب';
  output.appendChild(token);

  // Initially on layer 0 (original)
  assert.equal(layerManager.getCurrentLayerIndex(), 0);

  // Switch to layer 1 (root)
  layerManager.changeLayer(1);
  assert.equal(layerManager.getCurrentLayerIndex(), 1);

  // Apply layer to token
  layerManager.applyToToken(token);

  // Token should now display root instead of original text
  assert.notEqual(token.textContent, 'كتاب');
  assert.equal(token.textContent, 'ك ت ب');
});

test('LayerManager applies correct morphology field for each layer', async () => {
  const layerManager = new LayerManager({ layers: LAYERS, defaultIndex: 0 });

  const morphData = [{
    root: 'ك ت ب',
    lemma: 'كتاب',
    pos: 'NOUN',
    gender: 'M',
    number: 'SG',
    case: 'NOM'
  }];

  const token = document.createElement('span');
  token.className = 'token';
  token.dataset.morphology = JSON.stringify(morphData);
  token.dataset.originalText = 'كتاب';

  // Test different layers
  const testCases = [
    { layerIndex: 0, expectedContains: 'كتاب' },  // original
    { layerIndex: 1, expectedContains: 'ك ت ب' },  // root
    { layerIndex: 2, expectedContains: 'كتاب' },   // lemma
    { layerIndex: 3, expectedContains: 'NOUN' },   // pos
    { layerIndex: 6, expectedContains: 'M' },      // gender
    { layerIndex: 7, expectedContains: 'SG' },     // number
  ];

  for (const { layerIndex, expectedContains } of testCases) {
    layerManager.changeLayer(layerIndex);
    layerManager.applyToToken(token);

    // Check that token content was updated
    const hasExpected = token.textContent.includes(expectedContains) ||
                       token.innerHTML.includes(expectedContains);
    assert.ok(hasExpected,
      `Layer ${layerIndex} should display "${expectedContains}", got "${token.textContent}"`);
  }
});

test('Multiple tokens in chapter all update when layer changes', async () => {
  const output = document.getElementById('output');
  output.innerHTML = ''; // Clear

  const layerManager = new LayerManager({ layers: LAYERS, defaultIndex: 0 });

  // Create multiple tokens (simulating chapter with multiple verses)
  const tokens = [];
  for (let i = 0; i < 5; i++) {
    const token = document.createElement('span');
    token.className = 'token';
    token.dataset.morphology = JSON.stringify([{
      root: `root${i}`,
      pos: `POS${i}`,
      gender: 'M'
    }]);
    token.dataset.originalText = `word${i}`;
    token.textContent = `word${i}`;
    output.appendChild(token);
    tokens.push(token);
  }

  // Switch to root layer
  layerManager.changeLayer(1);
  layerManager.applyToAllTokens();

  // All tokens should show roots
  tokens.forEach((token, i) => {
    assert.ok(token.textContent.includes(`root${i}`),
      `Token ${i} should display its root`);
  });

  // Switch to POS layer
  layerManager.changeLayer(3);
  layerManager.applyToAllTokens();

  // All tokens should show POS
  tokens.forEach((token, i) => {
    assert.ok(token.innerHTML.includes(`POS${i}`) || token.textContent.includes(`POS${i}`),
      `Token ${i} should display its POS`);
  });
});

test('Annotation layer shows existing annotations', async () => {
  const output = document.getElementById('output');
  output.innerHTML = '';

  const layerManager = new LayerManager({ layers: LAYERS, defaultIndex: 0 });

  // Create token with annotation
  const token = document.createElement('span');
  token.className = 'token annotated';
  token.dataset.surah = '1';
  token.dataset.ayah = '1';
  token.dataset.index = '0';
  token.dataset.originalText = 'بسم';
  token.dataset.annotation = 'This means "in the name"';
  token.dataset.annotationId = 'ann-123';
  token.dataset.displayLayer = 'original';
  token.textContent = 'بسم';
  output.appendChild(token);

  // Switch to annotation layer
  layerManager.changeLayer(ANNOTATION_LAYER_INDEX);
  layerManager.applyToToken(token);

  // Token should display annotation
  assert.ok(token.classList.contains('annotated'));
  assert.ok(token.innerHTML.includes('This means'));
});

test('Tokens without morphology handle layer changes gracefully', async () => {
  const output = document.getElementById('output');
  output.innerHTML = '';

  const layerManager = new LayerManager({ layers: LAYERS, defaultIndex: 0 });

  // Create token WITHOUT morphology data
  const token = document.createElement('span');
  token.className = 'token';
  token.dataset.originalText = 'word';
  token.textContent = 'word';
  output.appendChild(token);

  // Switch to root layer
  layerManager.changeLayer(1);

  // Should not throw error
  assert.doesNotThrow(() => {
    layerManager.applyToToken(token);
  });

  // Token should still display something (likely original or empty)
  assert.ok(token.textContent !== undefined);
});

test('Layer switching preserves annotation data', async () => {
  const layerManager = new LayerManager({ layers: LAYERS, defaultIndex: 0 });

  const token = document.createElement('span');
  token.className = 'token annotated';
  token.dataset.morphology = JSON.stringify([{ root: 'test' }]);
  token.dataset.originalText = 'word';
  token.dataset.annotation = 'My note';
  token.dataset.annotationId = 'ann-456';

  // Switch to root layer
  layerManager.changeLayer(1);
  layerManager.applyToToken(token);

  // Annotation data should still be present
  assert.equal(token.dataset.annotation, 'My note');
  assert.equal(token.dataset.annotationId, 'ann-456');

  // Switch to annotation layer
  layerManager.changeLayer(ANNOTATION_LAYER_INDEX);
  layerManager.applyToToken(token);

  // Should display annotation
  assert.ok(token.innerHTML.includes('My note'));
});

test('extractLayerValue handles multiple segments correctly', () => {
  const segments = [
    { root: 'ك ت ب' },
    { root: 'ه' }
  ];

  const value = extractLayerValue(segments, 'root');
  assert.equal(value, 'ك ت ب + ه');
});

test('extractLayerValue returns null for missing fields', () => {
  const segments = [
    { root: 'test', pos: 'NOUN' }
  ];

  const value = extractLayerValue(segments, 'gender');
  assert.equal(value, null);
});

test('Token query works across multiple verses in chapter', () => {
  const output = document.getElementById('output');
  output.innerHTML = '';

  // Create tokens for chapter with 3 verses
  const verses = [
    { surah: 1, ayah: 1, tokens: ['w1', 'w2'] },
    { surah: 1, ayah: 2, tokens: ['w3', 'w4'] },
    { surah: 1, ayah: 3, tokens: ['w5'] },
  ];

  verses.forEach(verse => {
    verse.tokens.forEach((text, idx) => {
      const token = document.createElement('span');
      token.className = 'token';
      token.dataset.surah = verse.surah;
      token.dataset.ayah = verse.ayah;
      token.dataset.index = idx;
      token.textContent = text;
      output.appendChild(token);
    });
  });

  // Should be able to find specific token
  const target = output.querySelector('.token[data-ayah="2"][data-index="1"]');
  assert.equal(target.textContent, 'w4');

  // Should be able to find all tokens in verse 1
  const verse1Tokens = output.querySelectorAll('.token[data-ayah="1"]');
  assert.equal(verse1Tokens.length, 2);

  // Should be able to find all tokens in chapter
  const allTokens = output.querySelectorAll('.token');
  assert.equal(allTokens.length, 5);
});
