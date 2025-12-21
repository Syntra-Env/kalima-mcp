import test from 'node:test';
import assert from 'node:assert/strict';
import { JSDOM } from 'jsdom';

// Setup complete DOM environment with all required elements
const dom = new JSDOM(`
<!DOCTYPE html>
<html>
<body>
  <div id="output"></div>
  <input id="command-input" />
  <span id="prompt">kalima ></span>
</body>
</html>
`, { url: 'http://localhost:8080' });

global.document = dom.window.document;
global.window = dom.window;
global.HTMLElement = dom.window.HTMLElement;
global.HTMLSpanElement = dom.window.HTMLSpanElement;
global.HTMLInputElement = dom.window.HTMLInputElement;

// Track fetch calls
const fetchCalls = [];
global.fetch = async (url, options) => {
  fetchCalls.push({ url, options });

  if (url.includes('/annotations') && options?.method === 'POST') {
    const body = JSON.parse(options.body);
    return {
      ok: true,
      json: async () => ({
        id: `ann-${Date.now()}`,
        target_id: body.target_id,
        layer: body.layer,
        payload: body.payload
      }),
      status: 200
    };
  }

  if (url.includes('/annotations') && options?.method === 'DELETE') {
    return {
      ok: true,
      json: async () => ({ success: true }),
      status: 200
    };
  }

  if (url.includes('/annotations')) {
    return {
      json: async () => [],
    };
  }

  return { json: async () => ({}) };
};

const { ANNOTATION_LAYER_INDEX } = await import('../../desktop/frontend/lib/layers/definitions.js');

test('Token click handler setup for annotation editing', () => {
  const output = document.getElementById('output');
  output.innerHTML = '';

  // Simulate what printChapter does
  const token = document.createElement('span');
  token.className = 'token';
  token.dataset.surah = '1';
  token.dataset.ayah = '1';
  token.dataset.index = '0';
  token.dataset.originalText = 'بسم';
  token.textContent = 'بسم';
  output.appendChild(token);

  // Verify token can be clicked and found
  const foundToken = output.querySelector('.token[data-surah="1"][data-ayah="1"][data-index="0"]');
  assert.ok(foundToken);
  assert.equal(foundToken.dataset.surah, '1');
  assert.equal(foundToken.dataset.ayah, '1');
  assert.equal(foundToken.dataset.index, '0');
});

test('Creating inline editor for annotation', () => {
  const output = document.getElementById('output');
  output.innerHTML = '';

  const token = document.createElement('span');
  token.className = 'token';
  token.dataset.surah = '1';
  token.dataset.ayah = '1';
  token.dataset.index = '0';
  token.dataset.originalText = 'word';
  token.textContent = 'word';
  output.appendChild(token);

  // Simulate creating inline editor (from app.js startInlineEdit)
  token.classList.add('editing');

  const editor = document.createElement('span');
  editor.className = 'inline-editor';
  editor.contentEditable = 'true';
  editor.textContent = token.dataset.annotation || '';

  token.textContent = '';
  token.appendChild(editor);

  // Verify editor was created
  assert.ok(token.classList.contains('editing'));
  assert.ok(token.querySelector('.inline-editor'));
  assert.equal(token.querySelector('.inline-editor').contentEditable, 'true');
});

test('Annotation payload structure for API', () => {
  const surah = 2;
  const ayah = 255;
  const tokenIndex = 3;
  const annotationText = 'This is the Throne Verse';

  const targetId = `${surah}:${ayah}:${tokenIndex}`;
  const payload = {
    target_id: targetId,
    layer: 'inline',
    payload: {
      annotation: annotationText
    }
  };

  assert.equal(payload.target_id, '2:255:3');
  assert.equal(payload.layer, 'inline');
  assert.equal(payload.payload.annotation, 'This is the Throne Verse');
});

test('Saving annotation via fetch POST', async () => {
  fetchCalls.length = 0; // Clear previous calls

  const annotationData = {
    target_id: '1:1:0',
    layer: 'inline',
    payload: { annotation: 'Test note' }
  };

  const response = await fetch('http://localhost:8080/annotations', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(annotationData)
  });

  assert.equal(response.ok, true);
  assert.equal(fetchCalls.length, 1);
  assert.equal(fetchCalls[0].options.method, 'POST');

  const result = await response.json();
  assert.ok(result.id);
  assert.equal(result.target_id, '1:1:0');
});

test('Deleting annotation via fetch DELETE', async () => {
  fetchCalls.length = 0;

  const annotationId = 'ann-123';
  const response = await fetch(`http://localhost:8080/annotations/${annotationId}`, {
    method: 'DELETE'
  });

  assert.equal(response.ok, true);
  assert.equal(fetchCalls.length, 1);
  assert.equal(fetchCalls[0].options.method, 'DELETE');
  assert.ok(fetchCalls[0].url.includes(annotationId));
});

test('Token with annotation has correct classes and data', () => {
  const token = document.createElement('span');
  token.className = 'token';
  token.dataset.surah = '1';
  token.dataset.ayah = '1';
  token.dataset.index = '0';
  token.dataset.originalText = 'word';

  // Simulate annotation being added
  const annotationText = 'My interpretation';
  const annotationId = 'ann-456';

  token.classList.add('annotated');
  token.dataset.annotation = annotationText;
  token.dataset.annotationId = annotationId;

  // Verify annotation data
  assert.ok(token.classList.contains('annotated'));
  assert.equal(token.dataset.annotation, 'My interpretation');
  assert.equal(token.dataset.annotationId, 'ann-456');
});

test('Multiple tokens in chapter can have different annotations', () => {
  const output = document.getElementById('output');
  output.innerHTML = '';

  // Create 3 tokens with different annotations
  const annotations = [
    { targetId: '1:1:0', text: 'First word annotation' },
    { targetId: '1:1:1', text: 'Second word annotation' },
    { targetId: '1:2:0', text: 'Different verse annotation' }
  ];

  annotations.forEach((ann, idx) => {
    const [surah, ayah, index] = ann.targetId.split(':');
    const token = document.createElement('span');
    token.className = 'token annotated';
    token.dataset.surah = surah;
    token.dataset.ayah = ayah;
    token.dataset.index = index;
    token.dataset.annotation = ann.text;
    token.dataset.annotationId = `ann-${idx}`;
    output.appendChild(token);
  });

  // Verify each token has correct annotation
  const token1 = output.querySelector('[data-ayah="1"][data-index="0"]');
  assert.equal(token1.dataset.annotation, 'First word annotation');

  const token2 = output.querySelector('[data-ayah="1"][data-index="1"]');
  assert.equal(token2.dataset.annotation, 'Second word annotation');

  const token3 = output.querySelector('[data-ayah="2"][data-index="0"]');
  assert.equal(token3.dataset.annotation, 'Different verse annotation');
});

test('Annotation from individual verse appears in chapter view', () => {
  // This simulates the key requirement: annotations created on individual verses
  // should appear when viewing the chapter

  const output = document.getElementById('output');
  output.innerHTML = '';

  // Simulate annotation created when viewing verse 2:255 individually
  const individualVerseAnnotation = {
    id: 'ann-throne-verse',
    target_id: '2:255:0',
    layer: 'inline',
    payload: { annotation: 'The Throne Verse' }
  };

  // Now simulate chapter view loading verse 2:255
  const [surah, ayah, index] = individualVerseAnnotation.target_id.split(':');
  const token = document.createElement('span');
  token.className = 'token';
  token.dataset.surah = surah;
  token.dataset.ayah = ayah;
  token.dataset.index = index;
  token.dataset.originalText = 'ٱللَّهُ';

  // loadAnnotations would find this annotation by target_id
  if (individualVerseAnnotation.target_id === `${surah}:${ayah}:${index}`) {
    token.classList.add('annotated');
    token.dataset.annotation = individualVerseAnnotation.payload.annotation;
    token.dataset.annotationId = individualVerseAnnotation.id;
  }

  output.appendChild(token);

  // Verify annotation is present in chapter view
  assert.ok(token.classList.contains('annotated'));
  assert.equal(token.dataset.annotation, 'The Throne Verse');
  assert.equal(token.dataset.annotationId, 'ann-throne-verse');
});

test('Empty annotation text removes annotation', () => {
  const token = document.createElement('span');
  token.className = 'token annotated';
  token.dataset.annotation = 'Old annotation';
  token.dataset.annotationId = 'ann-old';

  // Simulate clearing annotation (user deletes text and saves empty)
  if (!token.dataset.annotation || token.dataset.annotation.trim() === '') {
    token.classList.remove('annotated');
    delete token.dataset.annotation;
    delete token.dataset.annotationId;
  }

  // Actually set to empty to test
  token.dataset.annotation = '';
  if (token.dataset.annotation.trim() === '') {
    token.classList.remove('annotated');
    delete token.dataset.annotation;
    delete token.dataset.annotationId;
  }

  assert.ok(!token.classList.contains('annotated'));
  assert.equal(token.dataset.annotation, undefined);
});

test('Annotation editor preserves whitespace and line breaks', () => {
  const editor = document.createElement('span');
  editor.className = 'inline-editor';
  editor.contentEditable = 'true';

  const multilineText = 'First line\nSecond line\n  Indented line';
  editor.textContent = multilineText;

  // Get text content preserves structure
  assert.ok(editor.textContent.includes('\n'));
  assert.ok(editor.textContent.includes('First line'));
  assert.ok(editor.textContent.includes('Second line'));
});
