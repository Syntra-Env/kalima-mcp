import { test, expect } from '@playwright/test';

const verseByIndex: Record<string, any> = {
  '0': {
    surah: { number: 1, name: 'الفاتحة' },
    ayah: 1,
    text: 'بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ',
    tokens: [
      { id: '1:1:0', form: 'بِسْمِ', segments: [{ id: 'seg-1', type: 'noun', pos: 'n', root: 'بسم' }] },
      { id: '1:1:1', form: 'اللَّهِ', segments: [{ id: 'seg-2', type: 'noun', pos: 'n', root: 'له' }] },
    ],
    annotations: [],
  },
  '1': {
    surah: { number: 1, name: 'الفاتحة' },
    ayah: 2,
    text: 'ٱلْحَمْدُ لِلَّهِ رَبِّ ٱلْعَٰلَمِينَ',
    tokens: [
      { id: '1:2:0', form: 'ٱلْحَمْدُ', segments: [{ id: 'seg-3', type: 'noun', pos: 'n', root: 'حمد' }] },
    ],
    annotations: [],
  },
};

const surahSummaries = [{ number: 1, name: 'الفاتحة', ayah_count: 2 }];
const surahOne = {
  surah: { number: 1, name: 'الفاتحة' },
  number: 1,
  name: 'الفاتحة',
  ayah_count: 2,
  verses: Object.values(verseByIndex),
};

const searchResults = {
  count: 1,
  results: [
    {
      verse: verseByIndex['1'],
      match: 'حمد',
      matchTerm: 'حمد',
    },
  ],
};

test.beforeEach(async ({ page }) => {
  const errors: string[] = [];
  page.on('console', (msg) => {
    if (msg.type() === 'error') {
      const loc = msg.location();
      const locStr = loc.url ? ` @ ${loc.url}:${loc.lineNumber}:${loc.columnNumber}` : '';
      errors.push(`[console] ${msg.text()}${locStr}`);
    }
  });
  page.on('pageerror', (err) => {
    errors.push(`[pageerror] ${err.message}\n${err.stack}`);
  });
  await page.exposeFunction('_assertNoClientErrors', () => {
    if (errors.length) {
      throw new Error(errors.join('\n'));
    }
  });

  await page.route('**/api/**', async (route) => {
    const url = new URL(route.request().url());
    const { pathname } = url;

    if (pathname.startsWith('/api/verse/index/')) {
      const index = pathname.split('/').pop() ?? '0';
      const payload = verseByIndex[index] ?? verseByIndex['0'];
      return route.fulfill({ contentType: 'application/json', body: JSON.stringify(payload) });
    }

    if (pathname.startsWith('/api/verse/')) {
      const [, , , surah, ayah] = pathname.split('/');
      const payload =
        Object.values(verseByIndex).find(
          (v) => `${v.surah.number}` === surah && `${v.ayah}` === ayah,
        ) ?? { error: 'not found' };
      return route.fulfill({ contentType: 'application/json', body: JSON.stringify(payload) });
    }

    if (pathname === '/api/surahs') {
      return route.fulfill({ contentType: 'application/json', body: JSON.stringify(surahSummaries) });
    }

    if (pathname.startsWith('/api/surah/')) {
      return route.fulfill({ contentType: 'application/json', body: JSON.stringify(surahOne) });
    }

    if (pathname === '/api/roots') {
      return route.fulfill({ contentType: 'application/json', body: JSON.stringify(['بسم', 'حمد']) });
    }

    if (pathname.startsWith('/api/search/roots')) {
      return route.fulfill({ contentType: 'application/json', body: JSON.stringify(searchResults) });
    }

    if (pathname.startsWith('/api/search/morphology')) {
      return route.fulfill({ contentType: 'application/json', body: JSON.stringify(searchResults) });
    }

    if (pathname.startsWith('/api/search/syntax')) {
      return route.fulfill({ contentType: 'application/json', body: JSON.stringify(searchResults) });
    }

    if (pathname.startsWith('/api/library_search')) {
      return route.fulfill({
        contentType: 'application/json',
        body: JSON.stringify({ results: [{ verse: verseByIndex['0'], match: 'library' }] }),
      });
    }

    return route.fulfill({ contentType: 'application/json', body: JSON.stringify([]) });
  });
});

test('renders first verse and navigates to the next one', async ({ page }) => {
  await page.goto('/');

  await expect(page.locator('#verseText')).toContainText('بِسْمِ اللَّهِ', { timeout: 10_000 });
  await expect(page.locator('#tokensContainer')).toContainText('1:1:0');

  await page.evaluate(() => nextVerse());

  await expect(page.locator('#verseText')).toContainText('ٱلْحَمْدُ لِلَّهِ');
  await expect(page.locator('#tokensContainer')).toContainText('1:2:0');

  await page.evaluate(async () => {
    // @ts-ignore
    await window._assertNoClientErrors();
  });
});

test('navigates via surah/ayah inputs', async ({ page }) => {
  await page.goto('/');

  await page.fill('#surahInput', '1');
  await page.fill('#ayahInput', '2');
  await page.click('#goBtn');

  await expect(page.locator('#verseText')).toContainText('ٱلْحَمْدُ لِلَّهِ');

  await page.evaluate(async () => {
    // @ts-ignore
    await window._assertNoClientErrors();
  });
});

test('toggles token visibility', async ({ page }) => {
  await page.goto('/');

  const tokens = page.locator('#tokensContainer');
  await expect(tokens).toHaveClass(/show/);

  await page.uncheck('#showTokens');
  await expect(tokens).not.toHaveClass(/show/);

  await page.check('#showTokens');
  await expect(tokens).toHaveClass(/show/);

  await page.evaluate(async () => {
    // @ts-ignore
    await window._assertNoClientErrors();
  });
});

test('root explorer search renders results', async ({ page }) => {
  await page.goto('/');

  // Wait for root letters to render and click ب then بسم
  await page.getByText('ب', { exact: true }).first().click();
  await page.getByText('بسم', { exact: true }).click();

  await expect(page.locator('.search-summary')).toContainText('Results');

  await page.evaluate(async () => {
    // @ts-ignore
    await window._assertNoClientErrors();
  });
});

test('morphology builder search renders results', async ({ page }) => {
  await page.goto('/');

  // Ensure builder chip added before triggering search
  await page.getByText('PREFIX', { exact: true }).click();
  await expect(page.locator('#morphBuilder .builder-token')).toHaveCount(1);
  await page.click('#morphBuildSearch');

  await expect(page.locator('.search-summary')).toContainText('Results');

  await page.evaluate(async () => {
    // @ts-ignore
    await window._assertNoClientErrors();
  });
});

test('syntax builder search renders results', async ({ page }) => {
  await page.goto('/');

  await page.getByText('Noun (N)', { exact: true }).click();
  await expect(page.locator('#syntaxBuilder .builder-token')).toHaveCount(1);
  await page.click('#syntaxBuildSearch');

  await expect(page.locator('.search-summary')).toContainText('Results');

  await page.evaluate(async () => {
    // @ts-ignore
    await window._assertNoClientErrors();
  });
});
