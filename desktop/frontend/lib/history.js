export function normalizeCommand(command) {
  return (command || '').trim();
}

export function isHistoryCommand(command) {
  return normalizeCommand(command).toLowerCase() === 'history';
}

export function recordCommandInHistory(history, command) {
  const trimmed = normalizeCommand(command);
  if (!trimmed) return false;
  if (isHistoryCommand(trimmed)) return false;

  const last = history[history.length - 1];
  if (last === trimmed) return false;

  history.push(trimmed);
  return true;
}

