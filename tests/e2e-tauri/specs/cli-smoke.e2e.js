import assert from 'node:assert/strict';

async function waitForSelector(selector, timeout = 60_000) {
  await browser.waitUntil(
    async () => browser.execute((sel) => Boolean(document.querySelector(sel)), selector),
    { timeout, timeoutMsg: `timed out waiting for selector: ${selector}` }
  );
  return $(selector);
}

async function waitForOutputContains(text, timeout = 60_000) {
  const output = await waitForSelector('#output', timeout);
  await browser.waitUntil(
    async () => (await output.getText()).includes(text),
    { timeout, timeoutMsg: `timed out waiting for output to contain: ${text}` }
  );
  return output;
}

describe('Kalima (Tauri)', () => {
  it('shows prompt and welcome', async () => {
    await waitForOutputContains("Kalima CLI. Type 'help' for commands.");
    const prompt = await waitForSelector('#prompt');
    assert.ok((await prompt.getText()).toLowerCase().includes('kalima'));
  });

  it('can read a verse', async () => {
    const input = await waitForSelector('#command-input');
    await input.setValue('read 1:1');
    await browser.keys('Enter');
    await waitForOutputContains('1:1');
  });

  it('layer commands reveal morphology', async () => {
    const input = await waitForSelector('#command-input');
    await input.setValue('read 1:1');
    await browser.keys('Enter');
    await waitForOutputContains('1:1');

    await input.setValue('layer root');
    await browser.keys('Enter');

    await waitForOutputContains('سمو');
    await waitForOutputContains('اله');
  });

  it('clear removes previous output', async () => {
    const input = await waitForSelector('#command-input');
    await input.setValue('read 1:1');
    await browser.keys('Enter');
    await waitForOutputContains('1:1');
    await input.setValue('layer arabic');
    await browser.keys('Enter');
    await waitForOutputContains('بِسْمِ');

    await input.setValue('clear');
    await browser.keys('Enter');

    const output = await waitForSelector('#output');
    await browser.waitUntil(async () => !(await output.getText()).includes('بِسْمِ'), {
      timeout: 60_000,
      timeoutMsg: 'timed out waiting for output to clear previous verse content',
    });
  });
});
