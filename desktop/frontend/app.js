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

// Handle clicks on tokens for inline editing, otherwise focus command input
document.addEventListener('click', (e) => {
    const token = e.target.closest('.token');
    if (token && !token.classList.contains('editing')) {
        startInlineEdit(token);
    } else if (!e.target.closest('.inline-editor')) {
        commandInput.focus();
    }
});

// Handle right-click to toggle between annotation and original text
document.addEventListener('contextmenu', (e) => {
    const token = e.target.closest('.token');
    if (token && !token.classList.contains('editing')) {
        e.preventDefault();
        toggleLayer(token);
    }
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

// Toggle between annotation and original Arabic text
function toggleLayer(tokenElement) {
    const annotation = tokenElement.dataset.annotation;
    const originalArabic = tokenElement.dataset.originalText;

    // Only toggle if there's an annotation
    if (!annotation || !originalArabic) return;

    // Check current state by looking at child elements
    const isShowingAnnotation = tokenElement.querySelector('.annotation-text');

    if (isShowingAnnotation) {
        // Switch to Arabic
        tokenElement.textContent = originalArabic;
    } else {
        // Switch to annotation
        const wrapper = document.createElement('span');
        wrapper.className = 'annotation-text';
        wrapper.dir = 'ltr';
        wrapper.textContent = annotation;
        tokenElement.textContent = '';
        tokenElement.appendChild(wrapper);
    }
}

// Inline annotation editing
function startInlineEdit(tokenElement) {
    // Prevent multiple edits at once
    const existing = document.querySelector('.inline-editor');
    if (existing) {
        cancelInlineEdit(existing);
    }

    // Get original Arabic text (might be stored in dataset if already annotated)
    const originalArabic = tokenElement.dataset.originalText || tokenElement.textContent;
    const currentAnnotation = tokenElement.dataset.annotation || '';
    const surah = tokenElement.dataset.surah;
    const ayah = tokenElement.dataset.ayah;
    const index = tokenElement.dataset.index;

    // Create inline input
    const input = document.createElement('input');
    input.className = 'inline-editor';
    input.type = 'text';
    input.value = currentAnnotation; // Load existing annotation if present
    input.size = 1; // Start small
    input.dataset.originalArabic = originalArabic;
    input.dataset.surah = surah;
    input.dataset.ayah = ayah;
    input.dataset.index = index;

    // Mark token as editing
    tokenElement.classList.add('editing');

    // Replace token text with input
    tokenElement.textContent = '';
    tokenElement.appendChild(input);

    // Auto-resize input as user types
    function resizeInput() {
        input.size = Math.max(1, input.value.length || 1);
    }
    input.addEventListener('input', resizeInput);
    resizeInput();

    // Focus input
    input.focus();

    // Handle Enter to save, Escape to cancel
    input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            saveInlineEdit(input, tokenElement);
        } else if (e.key === 'Escape') {
            e.preventDefault();
            cancelInlineEdit(input, tokenElement);
        }
    });

    // Handle blur (clicking outside)
    input.addEventListener('blur', () => {
        setTimeout(() => saveInlineEdit(input, tokenElement), 100);
    });
}

async function saveInlineEdit(input, tokenElement) {
    if (!input || !input.parentElement) return;

    const annotation = input.value.trim();
    const originalArabic = input.dataset.originalArabic;
    const surah = input.dataset.surah;
    const ayah = input.dataset.ayah;
    const index = input.dataset.index;
    const targetId = `${surah}:${ayah}:${index}`;

    tokenElement.classList.remove('editing');

    if (annotation) {
        // Save annotation to backend via API
        try {
            const response = await fetch('http://localhost:8080/annotations', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    target_id: targetId,
                    layer: 'inline',
                    payload: { annotation }
                })
            });
            const data = await response.json();
            if (data.id) {
                tokenElement.dataset.annotationId = data.id;
            }
        } catch (err) {
            console.error('Failed to save annotation:', err);
        }

        // Show annotation (substitution) wrapped for RTL handling
        const wrapper = document.createElement('span');
        wrapper.className = 'annotation-text';
        wrapper.dir = 'ltr';
        wrapper.textContent = annotation;

        tokenElement.textContent = '';
        tokenElement.appendChild(wrapper);
        tokenElement.classList.add('annotated');
        tokenElement.dataset.annotation = annotation;
        tokenElement.dataset.originalText = originalArabic;

        console.log(`Saved annotation for ${targetId}: "${annotation}"`);
    } else {
        // Delete annotation from backend if it exists
        const annotationId = tokenElement.dataset.annotationId;
        if (annotationId) {
            try {
                await fetch(`http://localhost:8080/annotations/${annotationId}`, {
                    method: 'DELETE'
                });
            } catch (err) {
                console.error('Failed to delete annotation:', err);
            }
        }

        // Empty input - restore original
        tokenElement.textContent = originalArabic;
        tokenElement.classList.remove('annotated');
        delete tokenElement.dataset.annotation;
        delete tokenElement.dataset.originalText;
        delete tokenElement.dataset.annotationId;
        console.log(`Deleted annotation for ${targetId}`);
    }
}

function cancelInlineEdit(input, tokenElement) {
    if (!input || !tokenElement) return;

    const originalArabic = input.dataset.originalArabic;
    const currentAnnotation = tokenElement.dataset.annotation;

    tokenElement.classList.remove('editing');

    // Restore to whatever state it was before editing
    if (currentAnnotation) {
        const wrapper = document.createElement('span');
        wrapper.className = 'annotation-text';
        wrapper.dir = 'ltr';
        wrapper.textContent = currentAnnotation;
        tokenElement.textContent = '';
        tokenElement.appendChild(wrapper);
    } else {
        tokenElement.textContent = originalArabic;
    }
}

function printVerse(verse) {
    const container = document.createElement('div');
    container.className = 'verse-container';

    const ref = document.createElement('div');
    ref.className = 'verse-ref-header';
    ref.textContent = `${verse.surah}:${verse.ayah}`;

    const verseContent = document.createElement('div');
    verseContent.className = 'verse-content';
    verseContent.dir = 'rtl';

    // If tokens are available, render them individually as clickable elements
    if (verse.tokens && verse.tokens.length > 0) {
        verse.tokens.forEach((tokenText, index) => {
            const tokenSpan = document.createElement('span');
            tokenSpan.className = 'token';
            tokenSpan.dataset.surah = verse.surah;
            tokenSpan.dataset.ayah = verse.ayah;
            tokenSpan.dataset.index = index;
            tokenSpan.textContent = tokenText;

            verseContent.appendChild(tokenSpan);

            // Add space after each token (except last)
            if (index < verse.tokens.length - 1) {
                verseContent.appendChild(document.createTextNode(' '));
            }
        });
    } else {
        // Fallback: render full text if no tokens
        const arabic = document.createElement('span');
        arabic.className = 'arabic';
        arabic.textContent = verse.text;
        verseContent.appendChild(arabic);
    }

    container.appendChild(ref);
    container.appendChild(verseContent);
    output.appendChild(container);

    // Load existing annotations for this verse (pass container to scope the search)
    loadAnnotations(verse.surah, verse.ayah, container);

    scrollToBottom();
}

// Load existing annotations from backend
async function loadAnnotations(surah, ayah, container) {
    try {
        const response = await fetch(`http://localhost:8080/annotations?layer=inline`);
        const annotations = await response.json();

        // Filter annotations for this verse
        annotations.forEach(annotation => {
            const match = annotation.target_id.match(/^(\d+):(\d+):(\d+)$/);
            if (match && parseInt(match[1]) === surah && parseInt(match[2]) === ayah) {
                const tokenIndex = parseInt(match[3]);
                const tokenElement = container.querySelector(
                    `.token[data-surah="${surah}"][data-ayah="${ayah}"][data-index="${tokenIndex}"]`
                );

                if (tokenElement && annotation.payload && annotation.payload.annotation) {
                    const originalArabic = tokenElement.textContent;
                    const annotationText = annotation.payload.annotation;

                    // Apply annotation
                    const wrapper = document.createElement('span');
                    wrapper.className = 'annotation-text';
                    wrapper.dir = 'ltr';
                    wrapper.textContent = annotationText;

                    tokenElement.textContent = '';
                    tokenElement.appendChild(wrapper);
                    tokenElement.classList.add('annotated');
                    tokenElement.dataset.annotation = annotationText;
                    tokenElement.dataset.originalText = originalArabic;
                    tokenElement.dataset.annotationId = annotation.id;
                }
            }
        });
    } catch (err) {
        console.error('Failed to load annotations:', err);
    }
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
