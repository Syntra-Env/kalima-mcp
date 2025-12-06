const output = document.getElementById('output');
const commandInput = document.getElementById('command-input');
const promptSpan = document.getElementById('prompt');

let commandHistory = [];
let historyIndex = -1;
let currentPrompt = 'kalima >';
let invoke;

// Initialize
window.addEventListener('DOMContentLoaded', async () => {
    // Load Tauri API
    try {
        if (window.__TAURI__) {
            invoke = window.__TAURI__.core.invoke;
        } else if (window.__TAURI_INTERNALS__) {
            invoke = window.__TAURI_INTERNALS__.invoke;
        } else {
            throw new Error('Tauri API not available');
        }
        printLine('Kalima CLI. Type \'help\' for commands.');
    } catch (error) {
        printLine('Error: Could not load Tauri API - ' + error.message, 'error');
        printLine('Please rebuild the application.', 'warning');
    }
    commandInput.focus();
});

// Keep focus on input
document.addEventListener('click', () => {
    commandInput.focus();
});

// Handle command input
commandInput.addEventListener('keydown', async (e) => {
    if (e.key === 'Enter') {
        const command = commandInput.value.trim();
        if (command) {
            // Add to history
            commandHistory.push(command);
            historyIndex = commandHistory.length;

            // Echo command
            printLine(`${currentPrompt} ${command}`, 'command-echo');

            // Execute command
            await executeCommand(command);

            // Clear input
            commandInput.value = '';
        }
    } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        if (historyIndex > 0) {
            historyIndex--;
            commandInput.value = commandHistory[historyIndex];
        }
    } else if (e.key === 'ArrowDown') {
        e.preventDefault();
        if (historyIndex < commandHistory.length - 1) {
            historyIndex++;
            commandInput.value = commandHistory[historyIndex];
        } else {
            historyIndex = commandHistory.length;
            commandInput.value = '';
        }
    }
});

async function executeCommand(command) {
    if (!invoke) {
        printLine('Error: Tauri API not loaded', 'error');
        return;
    }

    try {
        const result = await invoke('execute_command', { command });

        if (result.output) {
            const outputType = result.output.output_type;

            if (outputType === 'info' && result.output.message) {
                printLine(result.output.message);
            } else if (outputType === 'error' && result.output.message) {
                printLine(result.output.message, 'error');
            } else if (outputType === 'success' && result.output.message) {
                printLine(result.output.message, 'success');
            } else if (outputType === 'warning' && result.output.message) {
                printLine(result.output.message, 'warning');
            } else if (outputType === 'verse') {
                printVerse(result.output);
            } else if (outputType === 'analysis') {
                printAnalysis(result.output);
            } else if (outputType === 'pager' && result.output.content) {
                printPager(result.output.content);
            } else {
                printLine(JSON.stringify(result.output));
            }
        }

        if (result.prompt) {
            currentPrompt = result.prompt;
            promptSpan.textContent = currentPrompt;
        }
    } catch (error) {
        printLine(`Error: ${error}`, 'error');
    }
}

function printOutput(content, type) {
    if (type === 'verse') {
        printVerse(content);
    } else if (type === 'analysis') {
        printAnalysis(content);
    } else if (type === 'pager') {
        printPager(content);
    } else if (type === 'error') {
        printLine(content, 'error');
    } else if (type === 'success') {
        printLine(content, 'success');
    } else if (type === 'warning') {
        printLine(content, 'warning');
    } else {
        printLine(content);
    }
}

function printVerse(verse) {
    const div = document.createElement('div');
    div.className = 'verse-ref';

    const ref = document.createElement('span');
    ref.className = 'ref-num';
    ref.textContent = `${verse.surah}:${verse.ayah} `;

    const arabic = document.createElement('span');
    arabic.className = 'arabic';
    arabic.textContent = verse.text;

    div.appendChild(ref);
    div.appendChild(arabic);
    output.appendChild(div);

    if (verse.tokens && verse.tokens.length > 0) {
        const tokensDiv = document.createElement('div');
        tokensDiv.className = 'output-line';
        let tokensText = '';
        verse.tokens.forEach((token, idx) => {
            tokensText += `${idx + 1}:${token} `;
        });
        tokensDiv.textContent = tokensText;
        output.appendChild(tokensDiv);
    }

    if (verse.legend) {
        printLine(verse.legend, 'info');
    }

    scrollToBottom();
}

function printAnalysis(analysis) {
    if (analysis.header) {
        const header = document.createElement('div');
        header.className = 'analysis-header';
        header.textContent = analysis.header;
        output.appendChild(header);
    }

    if (analysis.verse_ref) {
        printLine(`Verse: ${analysis.verse_ref}`);
    }

    if (analysis.text) {
        const textDiv = document.createElement('div');
        textDiv.className = 'arabic';
        textDiv.textContent = analysis.text;
        output.appendChild(textDiv);
        printLine('');
    }

    if (analysis.tokens) {
        analysis.tokens.forEach((token, idx) => {
            const tokenDiv = document.createElement('div');
            tokenDiv.className = 'token-line';

            const tokenText = document.createElement('div');
            tokenText.className = 'arabic';
            tokenText.textContent = `${idx + 1}. ${token.text}`;
            tokenDiv.appendChild(tokenText);

            if (token.root) {
                const root = document.createElement('div');
                root.innerHTML = `   Root: <span class="root arabic">${token.root}</span>`;
                tokenDiv.appendChild(root);
            }

            if (token.pos) {
                const pos = document.createElement('div');
                pos.innerHTML = `   POS: <span class="pos">${token.pos}</span>`;
                tokenDiv.appendChild(pos);
            }

            if (token.form) {
                const form = document.createElement('div');
                form.innerHTML = `   Form: <span class="arabic">${token.form}</span>`;
                tokenDiv.appendChild(form);
            }

            output.appendChild(tokenDiv);
        });
    }

    scrollToBottom();
}

function printPager(content) {
    const div = document.createElement('div');
    div.className = 'pager-content';

    // Split content into lines and handle Arabic text
    const lines = content.split('\n');
    lines.forEach(line => {
        const lineDiv = document.createElement('div');

        // Check if line contains Arabic characters
        if (/[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]/.test(line)) {
            lineDiv.className = 'arabic';
        }

        lineDiv.textContent = line;
        div.appendChild(lineDiv);
    });

    output.appendChild(div);

    const footer = document.createElement('div');
    footer.className = 'pager-footer';
    footer.textContent = 'End of output';
    output.appendChild(footer);

    scrollToBottom();
}

function printLine(text, className = '') {
    const div = document.createElement('div');
    div.className = `output-line ${className}`;

    // Check if text contains Arabic and apply appropriate styling
    if (/[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]/.test(text)) {
        div.classList.add('arabic');
    }

    div.textContent = text;
    output.appendChild(div);
    scrollToBottom();
}

function scrollToBottom() {
    output.scrollTop = output.scrollHeight;
}
