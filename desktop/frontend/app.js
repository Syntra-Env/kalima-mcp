const output = document.getElementById('output');
const commandInput = document.getElementById('command-input');
const promptSpan = document.getElementById('prompt');

let commandHistory = [];
let historyIndex = -1;
let currentPrompt = 'kalima >';
let invoke;
let baseApi = window.KALIMA_BASE_URL ?? 'http://127.0.0.1:8080';
let webCurrentVerse = null;
let baseFontSize = 16;
let zoomFactor = 1;

// Initialize
window.addEventListener('DOMContentLoaded', async () => {
    // Load Tauri API
    try {
        if (window.__TAURI__) {
            invoke = window.__TAURI__.core.invoke;
        } else if (window.__TAURI_INTERNALS__) {
            invoke = window.__TAURI_INTERNALS__.invoke;
        } else {
            // Web fallback: emulate Tauri invoke using HTTP API
            invoke = async (cmd, args) => {
                if (cmd !== 'execute_command') {
                    throw new Error('Unknown command');
                }
                return await executeWebCommand(args.command);
            };
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

// Handle trackpad pinch / two-finger zoom (Ctrl + wheel in Chromium)
window.addEventListener('wheel', (event) => {
    if (event.ctrlKey) {
        event.preventDefault();

        // Negative deltaY is zoom-in; positive is zoom-out
        const step = event.deltaY < 0 ? 0.08 : -0.08;
        zoomFactor = Math.min(1.8, Math.max(0.6, zoomFactor + step));
        document.documentElement.style.setProperty('--zoom', zoomFactor.toFixed(2));
        document.documentElement.style.fontSize = `${(baseFontSize * zoomFactor).toFixed(2)}px`;
    }
}, { passive: false });

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
            } else if (outputType === 'clear') {
                clearOutput();
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

    if (analysis.tree) {
        const treePre = document.createElement('pre');
        treePre.className = 'tree';
        treePre.textContent = analysis.tree;
        output.appendChild(treePre);
    }

    if (analysis.tokens) {
        analysis.tokens.forEach((token, idx) => {
            const tokenDiv = document.createElement('div');
            tokenDiv.className = 'token-line';

            const headerLine = document.createElement('div');
            headerLine.className = 'token-header';
            const textSpan = document.createElement('span');
            textSpan.className = 'arabic';
            textSpan.textContent = `${idx + 1}. ${token.text}`;
            headerLine.appendChild(textSpan);

            if (token.role) {
                const roleSpan = document.createElement('span');
                roleSpan.className = `role-badge ${roleClass(token.role)}`;
                roleSpan.textContent = token.role;
                headerLine.appendChild(roleSpan);
            }
            if (token.pos) {
                const posSpan = document.createElement('span');
                posSpan.className = 'pos-badge';
                posSpan.textContent = token.pos;
                headerLine.appendChild(posSpan);
            }
            if (token.case_) {
                const caseSpan = document.createElement('span');
                caseSpan.className = 'case-badge';
                caseSpan.textContent = token.case_;
                headerLine.appendChild(caseSpan);
            }
            tokenDiv.appendChild(headerLine);

            const fields = [];
            if (token.root) fields.push(`Root: <span class="arabic">${token.root}</span>`);
            if (token.lemma) fields.push(`Lemma: <span class="arabic">${token.lemma}</span>`);
            if (token.form) fields.push(`Form: <span class="arabic">${token.form}</span>`);
            if (token.gender) fields.push(`Gender: ${token.gender}`);
            if (token.number) fields.push(`Number: ${token.number}`);
            if (token.definiteness) fields.push(`Definite: ${token.definiteness}`);
            if (token.determiner !== undefined && token.determiner !== null) {
                fields.push(`Determiner: ${token.determiner ? 'yes' : 'no'}`);
            }
            if (token.features) fields.push(`Feat: ${token.features}`);

            if (fields.length > 0) {
                const detail = document.createElement('div');
                detail.className = 'token-details';
                detail.innerHTML = fields.join(' | ');
                tokenDiv.appendChild(detail);
            }

            output.appendChild(tokenDiv);
        });
    }

    scrollToBottom();
}

function roleClass(role) {
    const r = role.toLowerCase();
    if (r.includes('subj')) return 'role-subj';
    if (r.includes('obj')) return 'role-obj';
    if (r.includes('comp')) return 'role-comp';
    return 'role-other';
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

function clearOutput() {
    output.innerHTML = '';
}

async function executeWebCommand(command) {
    const parts = command.trim().split(/\s+/);
    const cmd = parts.shift() || '';

    const api = async (path) => {
        const res = await fetch(`${baseApi}${path}`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
    };

    const renderVerseOutput = (verse) => ({
        output_type: 'verse',
        surah: verse.surah.number,
        ayah: verse.ayah,
        text: verse.text,
        tokens: (verse.tokens || []).map((t) => t.form || t.text || ''),
        legend: 'layers: general on',
    });

    const buildAnalysisFromMorph = (verse, morph) => ({
        output_type: 'analysis',
        header: '=== Morphological Analysis ===',
        verse_ref: `${verse.surah.number}:${verse.ayah}`,
        text: verse.text,
        tokens: (morph || []).map((seg) => ({
            text: seg.text || '',
            root: seg.root || null,
            pos: seg.pos || null,
            form: seg.form || null,
        })),
    });

    const setPrompt = () => {
        if (webCurrentVerse) {
            currentPrompt = `kalima (${webCurrentVerse.surah.number}:${webCurrentVerse.ayah}) >`;
            promptSpan.textContent = currentPrompt;
        } else {
            currentPrompt = 'kalima >';
            promptSpan.textContent = currentPrompt;
        }
    };

    try {
        if (cmd === 'clear') {
            clearOutput();
            return { output: { output_type: 'clear' }, prompt: currentPrompt };
        }
        if (cmd === 'status') {
            return {
                output: {
                    output_type: 'info',
                    message: `base_url: ${baseApi} | current_verse: ${webCurrentVerse ? `${webCurrentVerse.surah.number}:${webCurrentVerse.ayah}` : 'none'}`,
                },
                prompt: currentPrompt,
            };
        }
        if (cmd === 'see') {
            if (parts.length === 1 && parts[0].includes(':')) {
                const [s, a] = parts[0].split(':').map((n) => parseInt(n, 10));
                const verse = await api(`/api/verse/${s}/${a}`);
                webCurrentVerse = verse;
                setPrompt();
                return { output: renderVerseOutput(verse), prompt: currentPrompt };
            }
            const sub = parts.shift();
            const tail = parts.join(' ');
            if (sub === 'book') {
                const surahs = await api('/api/surahs');
                let content = '=== The Noble Quran ===\n\n';
                for (const s of surahs) {
                    const surah = await api(`/api/surah/${s.number}`);
                    content += `[${surah.surah.number}] ${surah.surah.name}\n`;
                    for (const v of surah.verses) {
                        content += `${surah.surah.number}:${v.ayah}  ${v.text}\n`;
                    }
                    content += '\n';
                }
                return { output: { output_type: 'pager', content }, prompt: currentPrompt };
            }
            if (sub === 'chapter') {
                const n = parseInt(tail, 10);
                const surah = await api(`/api/surah/${n}`);
                let content = `=== Surah ${surah.surah.number}: ${surah.surah.name} ===\n\n`;
                for (const v of surah.verses) {
                    content += `${surah.surah.number}:${v.ayah}  ${v.text}\n`;
                }
                if (surah.verses.length > 0) {
                    webCurrentVerse = await api(`/api/verse/${n}/${surah.verses[0].ayah}`);
                    setPrompt();
                }
                return { output: { output_type: 'pager', content }, prompt: currentPrompt };
            }
            if (sub === 'verse') {
                if (tail.includes(':')) {
                    const [s, a] = tail.split(':').map((n) => parseInt(n, 10));
                    const verse = await api(`/api/verse/${s}/${a}`);
                    webCurrentVerse = verse;
                    setPrompt();
                    return { output: renderVerseOutput(verse), prompt: currentPrompt };
                } else {
                    if (!webCurrentVerse) throw new Error('No surah in context');
                    const a = parseInt(tail, 10);
                    const verse = await api(`/api/verse/${webCurrentVerse.surah.number}/${a}`);
                    webCurrentVerse = verse;
                    setPrompt();
                    return { output: renderVerseOutput(verse), prompt: currentPrompt };
                }
            }
            throw new Error(`unknown see subcommand: ${sub}`);
        }
        if (cmd === 'inspect') {
            if (!webCurrentVerse) {
                // Default to the first verse if none in focus to keep UX forgiving.
                webCurrentVerse = await api('/api/verse/1/1');
                setPrompt();
            }
            const morph = await api(`/api/morphology/${webCurrentVerse.surah.number}/${webCurrentVerse.ayah}`);
            return {
                output: buildAnalysisFromMorph(webCurrentVerse, morph.morphology || []),
                prompt: currentPrompt,
            };
        }
        throw new Error(`unknown command: ${cmd}`);
    } catch (e) {
        return {
            output: { output_type: 'error', message: `Error: ${e.message}` },
            prompt: currentPrompt,
        };
    }
}
