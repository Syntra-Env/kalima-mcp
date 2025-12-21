export function renderConcordanceSummary(results) {
  const summary = document.createElement('div');
  summary.className = 'concordance-summary';
  const verseCounts = results?.verse_counts || results?.verseCounts || null;
  const hasPerVerseCounts = Array.isArray(verseCounts) && verseCounts.length;
  const verseList = hasPerVerseCounts
    ? verseCounts.map((v) => `${v.verse_ref ?? v.verseRef} (${v.count})`).join(', ')
    : (results?.verses || []).join(', ');
  const total = Number(results?.total || 0);

  // If we have per-verse counts, don't add total (already shown in counts)
  // Otherwise, show total matches
  summary.textContent = verseList
    ? (hasPerVerseCounts ? `Found in ${verseList}` : `Found in ${verseList} (${total} matches)`)
    : `No matches`;
  return summary;
}

export async function displayConcordanceResults(
  results,
  { outputEl, layerManager, morphologyCache, fetchMorphologyForVerse, append = false } = {},
) {
  if (!outputEl) throw new Error('displayConcordanceResults: outputEl is required');
  if (!append) outputEl.innerHTML = '';

  // 1. Render summary in the results pane
  outputEl.appendChild(renderConcordanceSummary(results));

  // 2. Highlight matching tokens in the main output pane, not here.
  const matches = results?.matches || [];
  for (const match of matches) {
    for (const token of match.tokens) {
      if (!token.matched) continue;

      // Find the original token in the main document (output pane) and highlight it
      const selector = `.token[data-surah="${match.surah}"][data-ayah="${match.ayah}"][data-index="${token.index}"]`;
      const tokenEl = document.querySelector(selector);
      if (tokenEl) {
        tokenEl.dataset.concordanceHit = '1';
      }
    }
  }

  // 3. The rest of the function is not needed, as we are not re-rendering tokens.
  // The layer manager and morphology logic is already handled when verses are first rendered.
}
