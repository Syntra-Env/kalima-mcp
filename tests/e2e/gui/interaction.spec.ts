import { test, expect } from '@playwright/test';

const injectApiBase = `
window.KALIMA_BASE_URL = '';
`;

test.describe('Kalima GUI CLI interactions', () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript({ content: injectApiBase });
    await page.goto('/');
  });

  test('shows initial prompt and welcome message', async ({ page }) => {
    await page.waitForSelector('#output');
    const output = page.locator('#output');
    await expect(output).toContainText("Kalima CLI. Type 'help' for commands.");
    await expect(page.locator('#prompt')).toHaveText('kalima >');
  });

  test('runs search command and updates prompt with verse output', async ({ page }) => {
    const input = page.locator('#command-input');
    await input.fill('see 1:1');
    await input.press('Enter');

    const output = page.locator('#output');
    await expect(output).toContainText('1:1');
    await expect(page.locator('#prompt')).toContainText('kalima (1:1) >');
  });

  test('shows full analysis output', async ({ page }) => {
    const input = page.locator('#command-input');
    await input.fill('see 1:1');
    await input.press('Enter');
    await expect(page.locator('#output')).toContainText('1:1');
    await input.fill('inspect');
    await input.press('Enter');

    const output = page.locator('#output');
    await expect(output).toContainText('=== Full Linguistic Analysis ===');
    await expect(output).toContainText('1:1');
  });

  test('clears output when clear command is issued', async ({ page }) => {
    const input = page.locator('#command-input');
    await input.fill('see 1:1');
    await input.press('Enter');
    await expect(page.locator('#output')).toContainText('1:1');

    await input.fill('clear');
    await input.press('Enter');
    await page.waitForTimeout(200);
    await expect(page.locator('#output')).toBeEmpty();
  });

  test('pinch zoom (ctrl + wheel) scales font size', async ({ page }) => {
    const root = page.locator('html');
    const originalSize = await root.evaluate((el) => getComputedStyle(el).fontSize);

    // Simulate ctrl+wheel up (zoom in)
    await root.evaluate((el) => {
      const evt = new WheelEvent('wheel', { deltaY: -100, ctrlKey: true, bubbles: true, cancelable: true });
      el.dispatchEvent(evt);
    });

    const zoomedSize = await root.evaluate((el) => getComputedStyle(el).fontSize);
    expect(parseFloat(zoomedSize)).toBeGreaterThan(parseFloat(originalSize));
  });
});
