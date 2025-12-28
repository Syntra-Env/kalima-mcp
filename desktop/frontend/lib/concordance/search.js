function getDefaultApiBaseUrl() {
  if (typeof window !== 'undefined' && typeof window.KALIMA_BASE_URL === 'string' && window.KALIMA_BASE_URL.trim()) {
    return window.KALIMA_BASE_URL.trim();
  }
  return 'http://localhost:8080';
}

export async function executeConcordanceSearch(body, { baseUrl, signal } = {}) {
  const apiBaseUrl = baseUrl || getDefaultApiBaseUrl();
  const response = await fetch(`${apiBaseUrl}/concordance`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal,
  });

  if (!response.ok) {
    const text = await response.text().catch(() => '');
    throw new Error(text || `Concordance request failed (${response.status})`);
  }

  return response.json();
}

