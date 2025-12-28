/**
 * Chat Mode Functions for Quran AI Agent
 *
 * This file contains the chat mode logic that integrates with app.js.
 * Import and use these functions in the main app.
 */

import * as chat from './chat.js';

let chatModeActive = false;

export function isChatModeActive() {
    return chatModeActive;
}

export async function enterChatMode(context) {
    const { printLine, clearAllPanes, terminal, promptSpan, currentPrompt, commandInput, scrollToBottom } = context;

    // Check if agent server is running, with retry for slow startup
    printLine('Connecting to Quran AI agent...', 'info');

    const maxWaitMs = 30000; // Wait up to 30 seconds for server to be ready
    const pollIntervalMs = 2000;
    const startTime = Date.now();
    let status = null;
    let attempts = 0;

    while (Date.now() - startTime < maxWaitMs) {
        attempts++;
        status = await chat.checkAgentStatus();

        if (status.loaded) {
            break;
        }

        // Show progress every few attempts
        if (attempts === 1) {
            printLine('Waiting for agent to load model...', 'info');
        } else if (attempts % 3 === 0) {
            printLine(`Still loading... (${Math.round((Date.now() - startTime) / 1000)}s)`, 'info');
        }

        await new Promise(resolve => setTimeout(resolve, pollIntervalMs));
    }

    if (!status || !status.loaded) {
        printLine(`Error: ${status?.error || 'Agent server not available after 30s'}`, 'error');
        printLine('Make sure the agent server is running: python quran_agent_server.py', 'warning');
        return false;
    }

    chatModeActive = true;
    chat.enterChatMode();

    clearAllPanes();
    terminal?.classList.add('chat-mode-active');
    promptSpan.textContent = decoratePromptForChatMode(currentPrompt);

    // Show welcome message
    printLine('='.repeat(60));
    printLine('Quran AI Agent - Chat Mode');
    printLine('='.repeat(60));
    printLine('');
    printLine(`Agent Status: ${status.status}`, 'success');
    printLine(`Vocabulary: ${status.vocab_size?.toLocaleString() || 'N/A'} tokens`);
    printLine(`DTL Constraints: ${status.dtl_constraints || 0} active`);
    printLine('');
    printLine('Type your message in Arabic or English.');
    printLine('Type "exit" to leave chat mode.');
    printLine('');

    commandInput.focus();
    return true;
}

export function exitChatMode(context) {
    const { printLine, terminal, promptSpan, currentPrompt, commandInput } = context;

    chatModeActive = false;
    chat.exitChatMode();

    terminal?.classList.remove('chat-mode-active');
    promptSpan.textContent = currentPrompt;

    printLine('');
    printLine('Exited chat mode.', 'info');
    printLine('');

    commandInput.focus();
}

export function decoratePromptForChatMode(prompt) {
    const base = String(prompt || 'kalima >');
    if (base.includes('[AI]')) return base;
    const trimmed = base.replace(/\s+$/, '');
    if (trimmed.endsWith('>')) {
        return `${trimmed.slice(0, -1).trimEnd()} [AI] >`;
    }
    return `${trimmed} [AI]`;
}

export async function handleChatMessage(message, context) {
    const { output, scrollToBottom, printLine } = context;

    // Display user message
    printChatMessage('user', message, null, context);

    // Show typing indicator
    const typingDiv = document.createElement('div');
    typingDiv.className = 'chat-typing';
    typingDiv.textContent = 'Agent is thinking...';
    output.appendChild(typingDiv);
    scrollToBottom();

    // Send to agent
    const result = await chat.sendMessage(message, {
        temperature: 1.0,
        maxTokens: 30
    });

    // Remove typing indicator
    typingDiv.remove();

    // Display response
    const formatted = chat.formatAgentResponse(result);

    if (formatted.type === 'error') {
        printLine(`Error: ${formatted.content}`, 'error');
    } else {
        printChatMessage('assistant', formatted.content, formatted.metrics, context);
    }
}

function printChatMessage(role, content, metrics, context) {
    const { output, scrollToBottom } = context;

    const container = document.createElement('div');
    container.className = `chat-message chat-${role}`;

    // Role label
    const roleLabel = document.createElement('div');
    roleLabel.className = 'chat-role';
    roleLabel.textContent = role === 'user' ? 'You:' : 'Agent:';
    container.appendChild(roleLabel);

    // Message content
    const messageDiv = document.createElement('div');
    messageDiv.className = 'chat-content';
    messageDiv.dir = 'rtl';  // Arabic text
    messageDiv.textContent = content;
    container.appendChild(messageDiv);

    // Metrics (for agent responses)
    if (metrics && role === 'assistant') {
        const metricsDiv = document.createElement('div');
        metricsDiv.className = 'chat-metrics';
        metricsDiv.textContent = `Lucidity: ${metrics.lucidity} | Alignment: ${metrics.alignment} | Torsion: ${metrics.torsion}`;
        container.appendChild(metricsDiv);
    }

    output.appendChild(container);
    scrollToBottom();
}
