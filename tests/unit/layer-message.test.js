import test from 'node:test';
import assert from 'node:assert/strict';
import { JSDOM } from 'jsdom';

// Setup DOM environment
const dom = new JSDOM(`
<!DOCTYPE html>
<html>
<body>
  <div id="output"></div>
</body>
</html>
`);

global.document = dom.window.document;
global.window = dom.window;

const { handleLayerCommand } = await import('../../desktop/frontend/lib/layers/layerCommand.js');
const { LayerManager } = await import('../../desktop/frontend/lib/layers/manager.js');
const { LAYERS, DEFAULT_LAYER_INDEX } = await import('../../desktop/frontend/lib/layers/definitions.js');

test('Layer switch messages replace previous ones', () => {
  const output = document.getElementById('output');
  output.innerHTML = '';

  const layerManager = new LayerManager({ layers: LAYERS, defaultIndex: DEFAULT_LAYER_INDEX });

  const printLine = (text, className) => {
    const div = document.createElement('div');
    div.className = `output-line ${className}`;
    div.textContent = text;
    output.appendChild(div);
  };

  const clearOutput = () => {
    output.innerHTML = '';
  };

  // Switch to layer 1
  handleLayerCommand('layer 1', { clearOutput, printLine, prompt: 'kalima >' }, layerManager);

  // Should have exactly 1 layer switch message
  let switchMessages = output.querySelectorAll('.layer-switch-message');
  assert.equal(switchMessages.length, 1);
  assert.ok(switchMessages[0].textContent.includes('layer 1'));

  // Switch to layer 2
  handleLayerCommand('layer 2', { clearOutput, printLine, prompt: 'kalima >' }, layerManager);

  // Should still have exactly 1 layer switch message (the new one)
  switchMessages = output.querySelectorAll('.layer-switch-message');
  assert.equal(switchMessages.length, 1);
  assert.ok(switchMessages[0].textContent.includes('layer 2'));

  // Switch using next
  handleLayerCommand('layer next', { clearOutput, printLine, prompt: 'kalima >' }, layerManager);

  // Should still have exactly 1 layer switch message
  switchMessages = output.querySelectorAll('.layer-switch-message');
  assert.equal(switchMessages.length, 1);
  assert.ok(switchMessages[0].textContent.includes('layer 3'));

  // Switch using alias
  handleLayerCommand('layer root', { clearOutput, printLine, prompt: 'kalima >' }, layerManager);

  // Should still have exactly 1 layer switch message
  switchMessages = output.querySelectorAll('.layer-switch-message');
  assert.equal(switchMessages.length, 1);
  assert.ok(switchMessages[0].textContent.includes('layer 1'));
  assert.ok(switchMessages[0].textContent.includes('Root'));
});

test('Multiple layer switches only show latest message', () => {
  const output = document.getElementById('output');
  output.innerHTML = '';

  const layerManager = new LayerManager({ layers: LAYERS, defaultIndex: DEFAULT_LAYER_INDEX });

  const printLine = (text, className) => {
    const div = document.createElement('div');
    div.className = `output-line ${className}`;
    div.textContent = text;
    output.appendChild(div);
  };

  const clearOutput = () => {
    output.innerHTML = '';
  };

  // Switch layers multiple times
  for (let i = 0; i < 5; i++) {
    handleLayerCommand(`layer ${i}`, { clearOutput, printLine, prompt: 'kalima >' }, layerManager);
  }

  // Should only have 1 layer switch message (the last one)
  const switchMessages = output.querySelectorAll('.layer-switch-message');
  assert.equal(switchMessages.length, 1);
  assert.ok(switchMessages[0].textContent.includes('layer 4'));
});

test('Non-switch messages are not affected', () => {
  const output = document.getElementById('output');
  output.innerHTML = '';

  const layerManager = new LayerManager({ layers: LAYERS, defaultIndex: DEFAULT_LAYER_INDEX });

  const printLine = (text, className) => {
    const div = document.createElement('div');
    div.className = `output-line ${className}`;
    div.textContent = text;
    output.appendChild(div);
  };

  const clearOutput = () => {
    output.innerHTML = '';
  };

  // Add some non-switch messages
  printLine('Some other message', 'info');
  printLine('Another message', 'success');

  // Switch layer
  handleLayerCommand('layer 1', { clearOutput, printLine, prompt: 'kalima >' }, layerManager);

  // Should have 2 regular messages + 1 switch message
  const allMessages = output.querySelectorAll('.output-line');
  const switchMessages = output.querySelectorAll('.layer-switch-message');

  assert.equal(allMessages.length, 3);
  assert.equal(switchMessages.length, 1);

  // Switch again
  handleLayerCommand('layer 2', { clearOutput, printLine, prompt: 'kalima >' }, layerManager);

  // Should still have 2 regular messages + 1 switch message
  const allMessages2 = output.querySelectorAll('.output-line');
  const switchMessages2 = output.querySelectorAll('.layer-switch-message');

  assert.equal(allMessages2.length, 3);
  assert.equal(switchMessages2.length, 1);
});
