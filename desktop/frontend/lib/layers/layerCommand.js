import { LAYERS } from './definitions.js';

const LAYER_ALIASES = {
  original: 0,
  arabic: 0,
  root: 1,
  lemma: 2,
  pos: 3,
  'part of speech': 3,
  pattern: 4,
  case: 5,
  gender: 6,
  number: 7,
  person: 8,
  'verb form': 9,
  verb: 9,
  voice: 10,
  mood: 16,
  aspect: 17,
  dependency: 11,
  dep: 11,
  role: 12,
  'segment type': 14,
  'segment form': 15,
  form: 15,
  'derived noun type': 18,
  derived: 18,
  state: 19,
  annotations: 13,
  annotation: 13,
  notes: 13,
};

export function handleLayerCommand(commandLine, { clearOutput, printLine, prompt } = {}, layerManager) {
  const parts = (commandLine || '').trim().split(/\s+/);

  if (parts.length === 1) {
    clearOutput?.();
    if (prompt) {
      printLine?.(`${prompt} ${commandLine}`, 'command-echo');
    }

    const current = layerManager.getCurrentLayer();
    printLine?.(`Current layer: ${layerManager.getCurrentLayerIndex()} - ${current.name}`, 'info');
    printLine?.('', 'info');
    printLine?.('Available layers:', 'info');
    LAYERS.forEach((layer, index) => {
      const marker = index === layerManager.getCurrentLayerIndex() ? '→ ' : '  ';
      printLine?.(`${marker}${index}: ${layer.name}`, 'info');
    });
    printLine?.('', 'info');
    printLine?.('Usage:', 'info');
    printLine?.(`  layer <number>     - Switch to layer by number (0-${LAYERS.length - 1})`, 'info');
    printLine?.('  layer <name>       - Switch to layer by name', 'info');
    printLine?.('  layer next         - Next layer', 'info');
    printLine?.('  layer prev         - Previous layer', 'info');
    return;
  }

  const arg = parts.slice(1).join(' ').toLowerCase();
  if (arg === 'next') {
    if (layerManager.nextLayer()) {
      const idx = layerManager.getCurrentLayerIndex();
      printLine?.(`Switched to layer ${idx}: ${LAYERS[idx].name}`, 'success');
    } else {
      printLine?.('Already at the last layer', 'warning');
    }
    return;
  }

  if (arg === 'prev' || arg === 'previous') {
    if (layerManager.prevLayer()) {
      const idx = layerManager.getCurrentLayerIndex();
      printLine?.(`Switched to layer ${idx}: ${LAYERS[idx].name}`, 'success');
    } else {
      printLine?.('Already at the first layer', 'warning');
    }
    return;
  }

  const numMatch = arg.match(/^(\d+)$/);
  if (numMatch) {
    const index = parseInt(numMatch[1], 10);
    if (layerManager.changeLayer(index)) {
      printLine?.(`Switched to layer ${index}: ${LAYERS[index].name}`, 'success');
    } else {
      printLine?.(`Invalid layer number. Must be 0-${LAYERS.length - 1}`, 'error');
    }
    return;
  }

  const idx = LAYER_ALIASES[arg];
  if (idx !== undefined) {
    layerManager.changeLayer(idx);
    printLine?.(`Switched to layer ${idx}: ${LAYERS[idx].name}`, 'success');
  } else {
    printLine?.(`Unknown layer: "${arg}"`, 'error');
    printLine?.('Use "layer" to see available layers', 'info');
  }
}
