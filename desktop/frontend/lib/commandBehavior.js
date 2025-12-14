import { normalizeCommand } from './history.js';

const NO_CLEAR_COMMANDS = new Set(['inspect']);

export function getCommandName(line) {
  const trimmed = normalizeCommand(line);
  if (!trimmed) return '';
  return trimmed.split(/\s+/)[0].toLowerCase();
}

export function shouldClearForCommand(line) {
  const cmd = getCommandName(line);
  if (!cmd) return true;
  if (cmd === 'history') return true;
  return !NO_CLEAR_COMMANDS.has(cmd);
}

