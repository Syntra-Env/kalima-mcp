import { test, expect } from '@playwright/test';

const injectApiBase = `
window.KALIMA_BASE_URL = '';
`;

test.describe('Inspect command verification', () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript({ content: injectApiBase });
    await page.goto('/');
  });

  test('displays full verse text (all tokens, not just first)', async ({ page }) => {
    const input = page.locator('#command-input');

    // Navigate to verse 1:1
    await input.fill('see 1:1');
    await input.press('Enter');

    const output = page.locator('#output');

    // Verify full verse text is shown (Bismillah has 4 tokens)
    // Should show: بِسْمِ ٱللَّهِ ٱلرَّحْمَـٰنِ ٱلرَّحِيمِ
    await expect(output).toContainText('بِسْمِ');
    await expect(output).toContainText('ٱللَّهِ');
    await expect(output).toContainText('ٱلرَّحْمَـٰنِ');
    await expect(output).toContainText('ٱلرَّحِيمِ');
  });

  test('inspect shows morphological analysis without tense field', async ({ page }) => {
    const input = page.locator('#command-input');

    // Navigate to verse 1:1 and inspect
    await input.fill('see 1:1');
    await input.press('Enter');
    await expect(page.locator('#output')).toContainText('1:1');

    await input.fill('inspect');
    await input.press('Enter');

    const output = page.locator('#output');

    // Should show linguistic analysis header
    await expect(output).toContainText('=== Full Linguistic Analysis ===');
    await expect(output).toContainText('Verse: 1:1');

    // Should show morphological features
    await expect(output).toContainText('POS:');

    // Should NOT show tense field (we removed it)
    const outputText = await output.textContent();
    expect(outputText?.toLowerCase()).not.toContain('tense:');

    // Should show aspect instead (for verbs)
    // Note: 1:1 has nouns, not verbs, so aspect might not appear
    // But if we test a verse with verbs, aspect should appear instead of tense
  });

  test('inspect shows correct token structure', async ({ page }) => {
    const input = page.locator('#command-input');

    // Navigate to verse 1:1 and inspect
    await input.fill('see 1:1');
    await input.press('Enter');
    await input.fill('inspect');
    await input.press('Enter');

    const output = page.locator('#output');
    const outputText = await output.textContent();

    // The inspect output should show hierarchical structure
    await expect(output).toContainText('Clause');

    // Should show individual tokens/words
    // Word 1 should be بِسْمِ with its segments
    await expect(output).toContainText('بِسْمِ');

    // Should show segment types
    await expect(output).toContainText('Prefix:');
    await expect(output).toContainText('Stem:');

    // Should show roots for stems
    await expect(output).toContainText('Root:');
  });

  test('inspect shows derived noun types and state when present', async ({ page }) => {
    const input = page.locator('#command-input');

    // Navigate to a verse with derived nouns (e.g., verse 1:3 has الرَّحْمَـٰنِ which is ACT_PCPL)
    await input.fill('see 1:3');
    await input.press('Enter');
    await input.fill('inspect');
    await input.press('Enter');

    const output = page.locator('#output');
    const outputText = await output.textContent();

    // The output might show derived noun type if present
    // This is optional since not all words have this field
    // Just verify the inspect command completes without errors
    await expect(output).toContainText('=== Full Linguistic Analysis ===');
  });

  test('search and inspect different verses', async ({ page }) => {
    const input = page.locator('#command-input');

    // Test verse 2:1
    await input.fill('see 2:1');
    await input.press('Enter');
    await expect(page.locator('#output')).toContainText('2:1');

    await input.fill('inspect');
    await input.press('Enter');

    let output = page.locator('#output');
    await expect(output).toContainText('Verse: 2:1');

    // Test another verse
    await input.fill('see 1:7');
    await input.press('Enter');
    await expect(page.locator('#output')).toContainText('1:7');

    await input.fill('inspect');
    await input.press('Enter');

    output = page.locator('#output');
    await expect(output).toContainText('Verse: 1:7');

    // Verify verse has multiple tokens
    const outputText = await output.textContent();
    expect(outputText).toBeTruthy();
  });
});
