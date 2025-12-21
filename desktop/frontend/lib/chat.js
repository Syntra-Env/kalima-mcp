/**
 * Quran Agent Chat Integration
 *
 * Connects to the Python-based Quran agent server for Arabic text generation
 * and deontic reasoning.
 */

const AGENT_SERVER_URL = 'http://localhost:8081';

// Chat state
let chatMode = false;
let chatHistory = [];

/**
 * Check if the agent server is running
 */
export async function checkAgentStatus() {
    try {
        const response = await fetch(`${AGENT_SERVER_URL}/status`, {
            method: 'GET',
            headers: { 'Content-Type': 'application/json' }
        });

        if (!response.ok) {
            return { loaded: false, error: 'Server not responding' };
        }

        return await response.json();
    } catch (error) {
        return { loaded: false, error: 'Cannot connect to agent server' };
    }
}

/**
 * Send a message to the agent and get a response
 */
export async function sendMessage(message, options = {}) {
    const { temperature = 1.0, maxTokens = 30 } = options;

    try {
        const response = await fetch(`${AGENT_SERVER_URL}/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message,
                temperature,
                max_tokens: maxTokens
            })
        });

        if (!response.ok) {
            throw new Error(`Server error: ${response.status}`);
        }

        const data = await response.json();

        if (data.status === 'error') {
            throw new Error(data.error);
        }

        // Add to history
        chatHistory.push({
            role: 'user',
            content: message,
            timestamp: Date.now()
        });

        chatHistory.push({
            role: 'assistant',
            content: data.response,
            metrics: data.metrics,
            timestamp: Date.now()
        });

        return data;
    } catch (error) {
        return {
            status: 'error',
            error: error.message || 'Failed to communicate with agent'
        };
    }
}

/**
 * Enter chat mode
 */
export function enterChatMode() {
    chatMode = true;
    return true;
}

/**
 * Exit chat mode
 */
export function exitChatMode() {
    chatMode = false;
    return false;
}

/**
 * Check if in chat mode
 */
export function isInChatMode() {
    return chatMode;
}

/**
 * Get chat history
 */
export function getChatHistory() {
    return [...chatHistory];
}

/**
 * Clear chat history
 */
export function clearChatHistory() {
    chatHistory = [];
}

/**
 * Format agent response for display
 */
export function formatAgentResponse(data) {
    if (data.status === 'error') {
        return {
            type: 'error',
            content: data.error
        };
    }

    const metrics = data.metrics || {};

    return {
        type: 'response',
        content: data.response,
        metrics: {
            lucidity: (metrics.lucidity * 100).toFixed(1) + '%',
            alignment: (metrics.omega_alignment * 100).toFixed(1) + '%',
            torsion: metrics.torsion?.toFixed(3) || '0.000'
        }
    };
}
