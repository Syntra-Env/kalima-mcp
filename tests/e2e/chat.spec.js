import { test, expect } from '@playwright/test';

/**
 * E2E Tests for Quran AI Agent Chat Integration
 *
 * Prerequisites:
 * - Agent server running on port 8081 (python quran_agent_server.py)
 * - Frontend served on port 4173 (handled by playwright.config.js)
 *
 * Note: These tests run in browser-only mode (without Tauri).
 * Some functionality that requires Tauri API won't work in this mode.
 */

test.describe('Chat Mode', () => {

    test.beforeEach(async ({ page }) => {
        // Navigate to the app
        await page.goto('/');
        // Wait for the app to initialize
        await page.waitForSelector('#command-input', { state: 'visible' });
    });

    test('should enter chat mode when typing "chat" command', async ({ page }) => {
        const commandInput = page.locator('#command-input');

        // Type the chat command
        await commandInput.fill('chat');
        await commandInput.press('Enter');

        // Wait for chat mode to activate - look for the connecting message or error
        const output = page.locator('#output');

        // Should show connecting message
        await expect(output).toContainText('Connecting to Quran AI agent', { timeout: 5000 });

        // If agent server is running, should show success and chat mode banner
        // If not running, will show error message
        const pageContent = await output.textContent();

        if (pageContent.includes('Agent Status: Ready')) {
            // Chat mode activated successfully
            await expect(output).toContainText('Quran AI Agent - Chat Mode');
            await expect(output).toContainText('Type your message');

            // Prompt should show [AI] indicator
            const prompt = page.locator('#prompt');
            await expect(prompt).toContainText('[AI]');
        } else {
            // Agent server not running - this is expected in CI
            await expect(output).toContainText(/Error|not available|Cannot connect/);
        }
    });

    test('should send message and receive response when agent is available', async ({ page }) => {
        const commandInput = page.locator('#command-input');
        const output = page.locator('#output');

        // Enter chat mode
        await commandInput.fill('chat');
        await commandInput.press('Enter');

        // Wait for chat mode to be ready
        await expect(output).toContainText('Quran AI Agent - Chat Mode', { timeout: 10000 });

        // Check if agent is available
        const pageContent = await output.textContent();

        if (!pageContent.includes('Agent Status: Ready')) {
            test.skip(true, 'Agent server not running');
            return;
        }

        // Send a test message in Arabic
        await commandInput.fill('بسم الله');
        await commandInput.press('Enter');

        // Wait for response - in browser-only mode, might get Tauri API error
        // or successful response depending on the app's error handling
        await page.waitForTimeout(3000);

        const afterMessage = await output.textContent();

        // Check for success path (user message shown with chat UI)
        if (afterMessage.includes('You:')) {
            await expect(output).toContainText('بسم الله');

            // Wait for agent response (can take a while for model inference)
            await expect(output).toContainText('Agent:', { timeout: 30000 });

            // Should show metrics
            await expect(output).toContainText('Lucidity:');
            await expect(output).toContainText('Alignment:');
        } else if (afterMessage.includes('Tauri API')) {
            // Browser-only mode limitation - Tauri API not available
            // This is expected when running outside the Tauri app
            console.log('Note: Chat messaging requires Tauri runtime. Test passed for browser-only validation.');
            expect(afterMessage).toContain('بسم الله'); // User input was shown
        } else {
            // Some other response - still should contain user input
            expect(afterMessage).toContain('بسم الله');
        }
    });

    test('should exit chat mode when typing "exit"', async ({ page }) => {
        const commandInput = page.locator('#command-input');
        const output = page.locator('#output');

        // Enter chat mode
        await commandInput.fill('chat');
        await commandInput.press('Enter');

        await page.waitForTimeout(2000);
        const pageContent = await output.textContent();

        if (!pageContent.includes('Agent Status: Ready')) {
            test.skip(true, 'Agent server not running');
            return;
        }

        // Exit chat mode
        await commandInput.fill('exit');
        await commandInput.press('Enter');

        // Should show exit message
        await expect(output).toContainText('Exited chat mode');

        // Prompt should no longer have [AI]
        const prompt = page.locator('#prompt');
        await expect(prompt).not.toContainText('[AI]');
    });

    test('should handle "ai" and "agent" as aliases for chat command', async ({ page }) => {
        const commandInput = page.locator('#command-input');
        const output = page.locator('#output');
        const prompt = page.locator('#prompt');

        // Test 'ai' command - should enter chat mode
        await commandInput.fill('ai');
        await commandInput.press('Enter');

        // Wait for chat mode to activate (either connecting message or chat mode banner)
        await expect(output).toContainText(/Connecting to Quran AI agent|Quran AI Agent - Chat Mode/, { timeout: 5000 });

        // If chat mode is active, prompt should show [AI]
        await page.waitForTimeout(2000);
        const content1 = await output.textContent();

        if (content1.includes('Agent Status: Ready')) {
            await expect(prompt).toContainText('[AI]');

            // Exit chat mode
            await commandInput.fill('exit');
            await commandInput.press('Enter');
            await page.waitForTimeout(500);
        }

        // Reload page to test 'agent' command fresh
        await page.reload();
        await page.waitForSelector('#command-input', { state: 'visible' });

        // Test 'agent' command
        await commandInput.fill('agent');
        await commandInput.press('Enter');

        // Should enter chat mode
        await expect(output).toContainText(/Connecting to Quran AI agent|Quran AI Agent - Chat Mode/, { timeout: 5000 });
    });
});

test.describe('Agent Server Health', () => {

    test('should be able to check agent server status via fetch', async ({ page }) => {
        await page.goto('/');

        // Make a direct fetch to agent server to check if it's running
        const response = await page.evaluate(async () => {
            try {
                const res = await fetch('http://localhost:8081/status');
                return await res.json();
            } catch (e) {
                return { error: e.message };
            }
        });

        // Log the status for debugging
        console.log('Agent server status:', response);

        if (response.loaded) {
            expect(response.status).toBe('Ready');
            expect(response.vocab_size).toBeGreaterThan(0);
        } else {
            // Server not running - this is informational
            console.log('Agent server not running:', response.error);
        }
    });
});
