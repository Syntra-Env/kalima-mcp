const output = document.getElementById('output');
const commandInput = document.getElementById('command-input');
const promptSpan = document.getElementById('prompt');

let commandHistory = [];
let historyIndex = -1;
let currentPrompt = 'kalima >';
let invoke;
let baseFontSize = 16;
let zoomFactor = 1;
const arabicSurahNames = [
    null,
    'الفاتحة',
    'البقرة',
    'آل عمران',
    'النساء',
    'المائدة',
    'الأنعام',
    'الأعراف',
    'الأنفال',
    'التوبة',
    'يونس',
    'هود',
    'يوسف',
    'الرعد',
    'إبراهيم',
    'الحجر',
    'النحل',
    'الإسراء',
    'الكهف',
    'مريم',
    'طه',
    'الأنبياء',
    'الحج',
    'المؤمنون',
    'النور',
    'الفرقان',
    'الشعراء',
    'النمل',
    'القصص',
    'العنكبوت',
    'الروم',
    'لقمان',
    'السجدة',
    'الأحزاب',
    'سبإ',
    'فاطر',
    'يس',
    'الصافات',
    'ص',
    'الزمر',
    'غافر',
    'فصلت',
    'الشورى',
    'الزخرف',
    'الدخان',
    'الجاثية',
    'الأحقاف',
    'محمد',
    'الفتح',
    'الحجرات',
    'ق',
    'الذاريات',
    'الطور',
    'النجم',
    'القمر',
    'الرحمن',
    'الواقعة',
    'الحديد',
    'المجادلة',
    'الحشر',
    'الممتحنة',
    'الصف',
    'الجمعة',
    'المنافقون',
    'التغابن',
    'الطلاق',
    'التحريم',
    'الملك',
    'القلم',
    'الحاقة',
    'المعارج',
    'نوح',
    'الجن',
    'المزمل',
    'المدثر',
    'القيامة',
    'الإنسان',
    'المرسلات',
    'النبإ',
    'النازعات',
    'عبس',
    'التكوير',
    'الانفطار',
    'المطففين',
    'الانشقاق',
    'البروج',
    'الطارق',
    'الأعلى',
    'الغاشية',
    'الفجر',
    'البلد',
    'الشمس',
    'الليل',
    'الضحى',
    'الشرح',
    'التين',
    'العلق',
    'القدر',
    'البينة',
    'الزلزلة',
    'العاديات',
    'القارعة',
    'التكاثر',
    'العصر',
    'الهمزة',
    'الفيل',
    'قريش',
    'الماعون',
    'الكوثر',
    'الكافرون',
    'النصر',
    'المسد',
    'الإخلاص',
    'الفلق',
    'الناس',
];

function resolveSurahName(number, name) {
    const trimmed = (name || '').trim();
    if (trimmed) return trimmed;
    if (number >= 1 && number < arabicSurahNames.length) {
        return arabicSurahNames[number];
    }
    return `Surah ${number}`;
}

// Initialize
window.addEventListener('DOMContentLoaded', async () => {
    // Load Tauri API
    try {
        if (window.__TAURI__) {
            invoke = window.__TAURI__.core.invoke;
        } else if (window.__TAURI_INTERNALS__) {
            invoke = window.__TAURI_INTERNALS__.invoke;
        } else {
            throw new Error('Tauri API not available. Please run the desktop app.');
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

        if (result.prefill) {
            commandInput.value = result.prefill;
            commandInput.focus();
            const len = result.prefill.length;
            commandInput.setSelectionRange(len, len);
            promptSpan.textContent = currentPrompt; // already updated from result.prompt
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

    if (analysis.tokens && !analysis.tree) {
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

            // Build safe DOM elements instead of HTML strings
            if (token.root) {
                const label = document.createTextNode('Root: ');
                const arabic = document.createElement('span');
                arabic.className = 'arabic';
                arabic.textContent = token.root;
                fields.push({ label, value: arabic });
            }
            if (token.lemma) {
                const label = document.createTextNode('Lemma: ');
                const arabic = document.createElement('span');
                arabic.className = 'arabic';
                arabic.textContent = token.lemma;
                fields.push({ label, value: arabic });
            }
            if (token.form) {
                const label = document.createTextNode('Form: ');
                const arabic = document.createElement('span');
                arabic.className = 'arabic';
                arabic.textContent = token.form;
                fields.push({ label, value: arabic });
            }
            if (token.gender) {
                fields.push({ text: `Gender: ${token.gender}` });
            }
            if (token.number) {
                fields.push({ text: `Number: ${token.number}` });
            }
            if (token.definiteness) {
                fields.push({ text: `Definite: ${token.definiteness}` });
            }
            if (token.determiner !== undefined && token.determiner !== null) {
                fields.push({ text: `Determiner: ${token.determiner ? 'yes' : 'no'}` });
            }
            if (token.features) {
                fields.push({ text: `Feat: ${token.features}` });
            }

            if (fields.length > 0) {
                const detail = document.createElement('div');
                detail.className = 'token-details';

                // Safely append each field
                fields.forEach((field, idx) => {
                    if (idx > 0) {
                        detail.appendChild(document.createTextNode(' | '));
                    }
                    if (field.text) {
                        detail.appendChild(document.createTextNode(field.text));
                    } else {
                        detail.appendChild(field.label);
                        detail.appendChild(field.value);
                    }
                });

                tokenDiv.appendChild(detail);
            }

            output.appendChild(tokenDiv);
        });
    }

    scrollToBottom();
}

function roleClass(role) {
    // Sanitize input to prevent CSS class injection
    if (typeof role !== 'string') return 'role-other';
    const r = role.toLowerCase().trim();
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
