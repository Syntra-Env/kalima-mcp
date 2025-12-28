export function renderConcordanceSummary(results) {
  const summary = document.createElement('div');
  summary.className = 'concordance-summary';
  const matches = results?.matches || [];
  const total = Number(results?.total || matches.length || 0);
  const verseCount = matches.length;

  summary.textContent = total > 0
    ? `Found ${total} match${total !== 1 ? 'es' : ''} in ${verseCount} verse${verseCount !== 1 ? 's' : ''}`
    : `No matches`;
  return summary;
}

export async function displayConcordanceResults(
  results,
  { outputEl, layerManager, morphologyCache, fetchMorphologyForVerse, append = false } = {},
) {
  if (!outputEl) throw new Error('displayConcordanceResults: outputEl is required');
  if (!append) outputEl.innerHTML = '';

  const matches = results?.matches || [];

  // 1. Render summary
  outputEl.appendChild(renderConcordanceSummary(results));

  if (matches.length === 0) return;

  // 2. Create scrollable container for matched verses
  const matchesContainer = document.createElement('div');
  matchesContainer.className = 'concordance-matches';

  // 3. Render each matched verse with highlighted tokens
  for (const match of matches) {
    const matchDiv = document.createElement('div');
    matchDiv.className = 'concordance-match';

    // Verse reference header
    const refHeader = document.createElement('div');
    refHeader.className = 'concordance-ref';
    refHeader.textContent = `${match.surah}:${match.ayah}`;
    matchDiv.appendChild(refHeader);

    // Verse content with tokens
    const verseContent = document.createElement('div');
    verseContent.className = 'concordance-line';
    verseContent.dir = 'rtl';

    // Build set of matched indices for fast lookup
    const matchedIndices = new Set();
    if (match.matched_indices) {
      match.matched_indices.forEach(idx => matchedIndices.add(idx));
    }
    if (match.tokens) {
      match.tokens.forEach(t => {
        if (t.matched) matchedIndices.add(t.index);
      });
    }

    // Render tokens
    const tokens = match.tokens || [];
    tokens.forEach((token, idx) => {
      const tokenSpan = document.createElement('span');
      tokenSpan.className = 'token';
      tokenSpan.dataset.surah = match.surah;
      tokenSpan.dataset.ayah = match.ayah;
      tokenSpan.dataset.index = token.index ?? idx;
      tokenSpan.dataset.originalText = token.text;
      tokenSpan.textContent = token.text;

      // Highlight matched tokens
      if (matchedIndices.has(token.index ?? idx) || token.matched) {
        tokenSpan.dataset.concordanceHit = '1';
      }

      verseContent.appendChild(tokenSpan);

      // Add space between tokens
      if (idx < tokens.length - 1) {
        verseContent.appendChild(document.createTextNode(' '));
      }
    });

    matchDiv.appendChild(verseContent);
    matchesContainer.appendChild(matchDiv);
  }

  outputEl.appendChild(matchesContainer);

  // 4. Also highlight tokens in the main output pane (if loaded)
  for (const match of matches) {
    const matchedIndices = new Set();
    if (match.matched_indices) {
      match.matched_indices.forEach(idx => matchedIndices.add(idx));
    }
    if (match.tokens) {
      match.tokens.forEach(t => {
        if (t.matched) matchedIndices.add(t.index);
      });
    }

    matchedIndices.forEach(idx => {
      const selector = `.token[data-surah="${match.surah}"][data-ayah="${match.ayah}"][data-index="${idx}"]`;
      const tokenEl = document.querySelector(`#output ${selector}`);
      if (tokenEl) {
        tokenEl.dataset.concordanceHit = '1';
      }
    });
  }
}
