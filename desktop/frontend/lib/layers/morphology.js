function getDefaultApiBaseUrl() {
  if (typeof window !== 'undefined' && typeof window.KALIMA_BASE_URL === 'string' && window.KALIMA_BASE_URL.trim()) {
    return window.KALIMA_BASE_URL.trim();
  }
  return 'http://localhost:8080';
}

export function createMorphologyCache() {
  return new Map();
}

export function parseMorphologySegments(segmentViews) {
  const byToken = {};

  const rawTokenIndices = (segmentViews || [])
    .map((seg) => seg?.token_index)
    .filter((idx) => idx !== undefined && idx !== null)
    .map((idx) => Number(idx))
    .filter((idx) => Number.isFinite(idx));
  const minTokenIndex = rawTokenIndices.length ? Math.min(...rawTokenIndices) : null;

  const rawWordIndices = (segmentViews || [])
    .map((seg) => seg?.word_index)
    .filter((idx) => idx !== undefined && idx !== null)
    .map((idx) => Number(idx))
    .filter((idx) => Number.isFinite(idx));
  const minWordIndex = rawWordIndices.length ? Math.min(...rawWordIndices) : null;

  for (const view of segmentViews || []) {
    let tokenIndex;
    if (view?.token_index !== undefined && view?.token_index !== null) {
      const raw = Number(view.token_index);
      if (!Number.isFinite(raw)) continue;
      tokenIndex = minTokenIndex === 1 ? raw - 1 : raw;
    } else if (view?.word_index !== undefined && view?.word_index !== null) {
      const raw = Number(view.word_index);
      if (!Number.isFinite(raw)) continue;
      tokenIndex = minWordIndex === 1 ? raw - 1 : raw;
    } else {
      continue;
    }

    const segments = Array.isArray(view?.segments) ? view.segments : [];
    if (!byToken[tokenIndex]) byToken[tokenIndex] = [];
    byToken[tokenIndex].push(...segments);
  }

  return byToken;
}

export async function fetchMorphologyForVerse({ surah, ayah, cache, baseUrl } = {}) {
  const apiBaseUrl = baseUrl || getDefaultApiBaseUrl();
  const cacheKey = `${surah}:${ayah}`;
  if (cache && cache.has(cacheKey)) {
    return cache.get(cacheKey);
  }

  const response = await fetch(`${apiBaseUrl}/api/morphology/${surah}/${ayah}`);
  if (!response.ok) {
    return {};
  }

  const data = await response.json();
  const segmentViews = data.morphology || [];
  const byToken = parseMorphologySegments(segmentViews);

  if (cache) cache.set(cacheKey, byToken);
  return byToken;
}

