import { normalizeCommand, recordCommandInHistory } from './lib/history.js';
import { shouldClearForCommand } from './lib/commandBehavior.js';

const output = document.getElementById('output');
const commandInput = document.getElementById('command-input');
const promptSpan = document.getElementById('prompt');

let commandHistory = [];
let historyIndex = -1;
let currentPrompt = 'kalima >';
let invoke;
let baseFontSize = 16;
let zoomFactor = 1;

// Layer system configuration
let currentLayerIndex = 0; // Start at Original Arabic
let morphologyCache = new Map(); // Cache morphology data per verse

// Color maps for layers
const CASE_COLORS = { 'NOM': '#FF8C42', 'ACC': '#FF5252', 'GEN': '#9C6ADE' };
const GENDER_COLORS = { 'M': '#4A90E2', 'F': '#E91E63' };
const NUMBER_COLORS = { 'SG': '#66BB6A', 'DU': '#FFA726', 'PL': '#AB47BC' };
const PERSON_COLORS = { 'P1': '#42A5F5', 'P2': '#66BB6A', 'P3': '#FFA726' };
const POS_COLORS = {
    'N': '#4CAF50', 'NOUN': '#4CAF50',
    'V': '#2196F3', 'VERB': '#2196F3',
    'PREP': '#FF9800', 'P': '#FF9800',
    'ADJ': '#9C27B0',
    'PRON': '#00BCD4',
    'DET': '#FFC107',
    'default': '#9E9E9E'
};
const VOICE_COLORS = { 'ACT': '#66BB6A', 'PASS': '#EF5350' };

// Layer definitions
const LAYERS = [
    { id: 0, name: 'Original Arabic', field: null, colorMap: null },
    { id: 1, name: 'Root', field: 'root', colorMap: null },
    { id: 2, name: 'Lemma', field: 'lemma', colorMap: null },
    { id: 3, name: 'Part of Speech', field: 'pos', colorMap: POS_COLORS },
    { id: 4, name: 'Pattern', field: 'pattern', colorMap: null },
    { id: 5, name: 'Case', field: 'case_', colorMap: CASE_COLORS },
    { id: 6, name: 'Gender', field: 'gender', colorMap: GENDER_COLORS },
    { id: 7, name: 'Number', field: 'number', colorMap: NUMBER_COLORS },
    { id: 8, name: 'Person', field: 'person', colorMap: PERSON_COLORS },
    { id: 9, name: 'Verb Form', field: 'verb_form', colorMap: null },
    { id: 10, name: 'Voice', field: 'voice', colorMap: VOICE_COLORS },
    { id: 11, name: 'Dependency', field: 'dependency_rel', colorMap: null },
    { id: 12, name: 'Role', field: 'role', colorMap: null },
    { id: 13, name: 'Annotations', field: 'user_annotation', colorMap: null }
];

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
        // Only allow editing on annotation layer (Layer 13)
        if (currentLayerIndex === 13) {
            startInlineEdit(token);
        }
    } else if (!e.target.closest('.inline-editor')) {
        commandInput.focus();
    }
});

// Note: Right-click is now used for layer slider navigation
// The old toggleLayer functionality is replaced by the layer system

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
        await runUserCommand(command);
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

async function runUserCommand(command) {
    const trimmed = normalizeCommand(command);
    if (!trimmed) return;

    recordCommandInHistory(commandHistory, trimmed);
    historyIndex = commandHistory.length;

    const prefillApplied = await executeCommand(trimmed);
    if (!prefillApplied) {
        commandInput.value = '';
    }
    commandInput.focus();
}

async function executeCommand(command) {
    let prefillApplied = false;

    // Handle 'history' command locally
    if (command.trim().toLowerCase() === 'history') {
        clearOutput();
        printLine(`${currentPrompt} ${command}`, 'command-echo');
        showHistory();
        return prefillApplied;
    }

    const trimmed = command.trim();
    const cmd = (trimmed.split(/\s+/)[0] || '').toLowerCase();

    // Handle 'layer' command locally (without clearing)
    if (cmd === 'layer') {
        handleLayerCommand(trimmed);
        return prefillApplied;
    }

    // Clear screen before executing command (for most commands)
    if (shouldClearForCommand(trimmed)) {
        clearOutput();
    }

    // Echo command after clearing
    printLine(`${currentPrompt} ${command}`, 'command-echo');

    if (!invoke) {
        printLine('Error: Tauri API not loaded', 'error');
        return prefillApplied;
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
                // Already cleared above
            } else {
                printLine(JSON.stringify(result.output));
            }
        }

        if (result.prompt) {
            currentPrompt = result.prompt;
            promptSpan.textContent = currentPrompt;
        }

        if (result.prefill) {
            prefillApplied = true;
            commandInput.value = result.prefill;
            commandInput.focus();
            const len = result.prefill.length;
            commandInput.setSelectionRange(len, len);
            promptSpan.textContent = currentPrompt; // already updated from result.prompt
        }
    } catch (error) {
        printLine(`Error: ${error}`, 'error');
    }

    return prefillApplied;
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

    const displayLayer = tokenElement.dataset.displayLayer || 'original';
    const isShowingAnnotation = displayLayer === 'annotation';

    if (isShowingAnnotation) {
        // Switch to Arabic
        tokenElement.textContent = originalArabic;
        tokenElement.dataset.displayLayer = 'original';
    } else {
        // Switch to annotation
        const wrapper = document.createElement('span');
        wrapper.className = 'annotation-text';
        wrapper.dir = 'ltr';
        wrapper.textContent = annotation;
        tokenElement.textContent = '';
        tokenElement.appendChild(wrapper);
        tokenElement.dataset.displayLayer = 'annotation';
    }
}

// Inline annotation editing
function startInlineEdit(tokenElement) {
    // Prevent multiple edits at once
    const existing = document.querySelector('.inline-editor');
    if (existing) {
        cancelInlineEdit(existing);
    }

    const wasShowingAnnotation = (tokenElement.dataset.displayLayer || 'original') === 'annotation';

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
    input.dataset.wasShowingAnnotation = wasShowingAnnotation ? '1' : '0';

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
    const wasShowingAnnotation = input.dataset.wasShowingAnnotation === '1';
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

        if (!tokenElement.dataset.originalText) {
            tokenElement.dataset.originalText = originalArabic;
        }
        tokenElement.classList.add('annotated');
        tokenElement.dataset.annotation = annotation;
        const wrapper = document.createElement('span');
        wrapper.className = 'annotation-text';
        wrapper.dir = 'ltr';
        wrapper.textContent = annotation;
        tokenElement.textContent = '';
        tokenElement.appendChild(wrapper);
        tokenElement.dataset.displayLayer = 'annotation';

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
        tokenElement.textContent = tokenElement.dataset.originalText || originalArabic;
        tokenElement.classList.remove('annotated');
        delete tokenElement.dataset.annotation;
        delete tokenElement.dataset.annotationId;
        tokenElement.dataset.displayLayer = 'original';
        console.log(`Deleted annotation for ${targetId}`);
    }
}

function cancelInlineEdit(input, tokenElement) {
    if (!input || !tokenElement) return;

    const originalArabic = input.dataset.originalArabic;
    const wasShowingAnnotation = input.dataset.wasShowingAnnotation === '1';
    const currentAnnotation = tokenElement.dataset.annotation;

    tokenElement.classList.remove('editing');

    // Restore to whatever state it was before editing
    if (wasShowingAnnotation && currentAnnotation) {
        const wrapper = document.createElement('span');
        wrapper.className = 'annotation-text';
        wrapper.dir = 'ltr';
        wrapper.textContent = currentAnnotation;
        tokenElement.textContent = '';
        tokenElement.appendChild(wrapper);
        tokenElement.dataset.displayLayer = 'annotation';
    } else {
        tokenElement.textContent = tokenElement.dataset.originalText || originalArabic;
        tokenElement.dataset.displayLayer = 'original';
    }
}

// Morphology fetching and parsing functions
async function fetchMorphologyForVerse(surah, ayah) {
    // Check cache first
    const cacheKey = `${surah}:${ayah}`;
    if (morphologyCache.has(cacheKey)) {
        console.log(`Using cached morphology for ${surah}:${ayah}`);
        return morphologyCache.get(cacheKey);
    }

    try {
        // Fetch from API
        console.log(`Fetching morphology for ${surah}:${ayah}...`);
        const response = await fetch(`http://localhost:8080/api/morphology/${surah}/${ayah}`);
        if (!response.ok) {
            console.error(`Failed to fetch morphology: ${response.status}`);
            return {};
        }

        const data = await response.json();
        // API returns {surah, ayah, morphology: [...]}
        const segments = data.morphology || [];
        console.log(`Received ${segments.length} morphology segments for ${surah}:${ayah}`);

        // Parse and organize by token index
        const morphByToken = parseMorphologySegments(segments);
        console.log(`Parsed morphology by token:`, morphByToken);

        // Cache it
        morphologyCache.set(cacheKey, morphByToken);

        return morphByToken;
    } catch (err) {
        console.error('Error fetching morphology:', err);
        return {};
    }
}

function parseMorphologySegments(segments) {
    const byToken = {};

    const rawTokenIndices = segments
        .map((seg) => seg.token_index)
        .filter((idx) => idx !== undefined && idx !== null)
        .map((idx) => Number(idx))
        .filter((idx) => Number.isFinite(idx));
    const minTokenIndex = rawTokenIndices.length ? Math.min(...rawTokenIndices) : null;

    const rawWordIndices = segments
        .map((seg) => seg.word_index)
        .filter((idx) => idx !== undefined && idx !== null)
        .map((idx) => Number(idx))
        .filter((idx) => Number.isFinite(idx));
    const minWordIndex = rawWordIndices.length ? Math.min(...rawWordIndices) : null;

    for (const seg of segments) {
        // Try both token_index and word_index fields
        let tokenIndex;
        if (seg.token_index !== undefined && seg.token_index !== null) {
            const raw = Number(seg.token_index);
            if (!Number.isFinite(raw)) continue;
            tokenIndex = minTokenIndex === 1 ? raw - 1 : raw;
        } else if (seg.word_index !== undefined && seg.word_index !== null) {
            const raw = Number(seg.word_index);
            if (!Number.isFinite(raw)) continue;
            tokenIndex = minWordIndex === 1 ? raw - 1 : raw;
        } else {
            continue;
        }
        if (!Number.isFinite(tokenIndex)) continue;

        if (!byToken[tokenIndex]) {
            byToken[tokenIndex] = [];
        }
        byToken[tokenIndex].push(seg);
    }

    return byToken;
}

function extractLayerValue(morphSegments, layerField) {
    if (!morphSegments || morphSegments.length === 0) {
        return null;
    }

    // Concatenate values from all segments
    const values = morphSegments
        .map(seg => seg[layerField])
        .filter(v => v != null && v !== '');

    if (values.length === 0) return null;

    // For multiple segments, join with " + "
    return values.join(' + ');
}

async function printVerse(verse) {
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
            tokenSpan.dataset.originalText = tokenText;
            tokenSpan.dataset.displayLayer = 'original';
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

    // Fetch morphology data for this verse
    const morphData = await fetchMorphologyForVerse(verse.surah, verse.ayah);

    // Store morphology in each token's dataset
    if (verse.tokens && verse.tokens.length > 0) {
        verse.tokens.forEach((_, index) => {
            const tokenSpan = container.querySelector(
                `.token[data-surah="${verse.surah}"][data-ayah="${verse.ayah}"][data-index="${index}"]`
            );

            if (tokenSpan && morphData[index]) {
                tokenSpan.dataset.morphology = JSON.stringify(morphData[index]);
            }
        });
    }

    // Load existing annotations for this verse (pass container to scope the search)
    await loadAnnotations(verse.surah, verse.ayah, container);

    // Apply current layer to the newly added verse
    applyLayerToAllTokens();

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
                    const originalArabic = tokenElement.dataset.originalText || tokenElement.textContent;
                    const annotationText = annotation.payload.annotation;
                    tokenElement.classList.add('annotated');
                    tokenElement.dataset.annotation = annotationText;
                    if (!tokenElement.dataset.originalText) {
                        tokenElement.dataset.originalText = originalArabic;
                    }
                    tokenElement.dataset.annotationId = annotation.id;
                    tokenElement.textContent = tokenElement.dataset.originalText;
                    tokenElement.dataset.displayLayer = 'original';
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

function showHistory() {
    if (commandHistory.length === 0) {
        printLine('No command history available.', 'info');
        return;
    }

    // Create history container
    const container = document.createElement('div');
    container.className = 'history-container';

    // Add header
    const header = document.createElement('div');
    header.className = 'history-header';
    header.textContent = `Command History (${commandHistory.length} commands)`;
    container.appendChild(header);

    // Add history items in reverse order (most recent first)
    const historyItems = [];

    for (let i = commandHistory.length - 1; i >= 0; i--) {
        const item = document.createElement('div');
        item.className = 'history-item';
        item.dataset.index = i;

        const index = document.createElement('span');
        index.className = 'history-index';
        index.textContent = `${i + 1}.`;

        const cmd = document.createElement('span');
        cmd.className = 'history-command';
        cmd.textContent = commandHistory[i];

        item.appendChild(index);
        item.appendChild(cmd);

        // Click handler
        item.addEventListener('click', async () => {
            commandInput.removeEventListener('keydown', historyKeyHandler);
            await runUserCommand(commandHistory[i]);
        });

        container.appendChild(item);
        historyItems.push(item);
    }

    output.appendChild(container);

    // Add keyboard navigation for history items
    let currentSelection = -1;

    const navigateHistory = (direction) => {
        if (historyItems.length === 0) return;

        // Clear previous selection
        if (currentSelection >= 0 && currentSelection < historyItems.length) {
            historyItems[currentSelection].classList.remove('selected');
        }

        // Update selection
        if (direction === 'up') {
            currentSelection = currentSelection < 0 ? 0 : Math.min(currentSelection + 1, historyItems.length - 1);
        } else if (direction === 'down') {
            currentSelection = currentSelection < 0 ? 0 : Math.max(currentSelection - 1, 0);
        }

        // Apply new selection
        if (currentSelection >= 0 && currentSelection < historyItems.length) {
            historyItems[currentSelection].classList.add('selected');
            historyItems[currentSelection].scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
    };

    const selectCurrent = () => {
        if (currentSelection >= 0 && currentSelection < historyItems.length) {
            const index = parseInt(historyItems[currentSelection].dataset.index);
            return runUserCommand(commandHistory[index]);
        }
    };

    // Temporarily override arrow keys for history navigation
    const historyKeyHandler = (e) => {
        if (document.activeElement === commandInput) {
            if (e.key === 'ArrowUp') {
                e.preventDefault();
                navigateHistory('up');
            } else if (e.key === 'ArrowDown') {
                e.preventDefault();
                navigateHistory('down');
            } else if (e.key === 'Enter' && currentSelection >= 0) {
                e.preventDefault();
                selectCurrent();
                // Remove the temporary handler after selection
                commandInput.removeEventListener('keydown', historyKeyHandler);
            } else if (e.key === 'Escape') {
                // Cancel history navigation
                commandInput.removeEventListener('keydown', historyKeyHandler);
                if (currentSelection >= 0 && currentSelection < historyItems.length) {
                    historyItems[currentSelection].classList.remove('selected');
                }
                currentSelection = -1;
            }
        }
    };

    // Add temporary event listener for history navigation
    commandInput.addEventListener('keydown', historyKeyHandler);

    scrollToBottom();
}

// Layer command handler
function handleLayerCommand(command) {
    const parts = command.trim().split(/\s+/);

    // Just 'layer' - show current layer info (clear screen for this)
    if (parts.length === 1) {
        clearOutput();
        printLine(`${currentPrompt} ${command}`, 'command-echo');
        const currentLayer = LAYERS[currentLayerIndex];
        printLine(`Current layer: ${currentLayerIndex} - ${currentLayer.name}`, 'info');
        printLine('', 'info');
        printLine('Available layers:', 'info');
        LAYERS.forEach((layer, index) => {
            const marker = index === currentLayerIndex ? '→ ' : '  ';
            printLine(`${marker}${index}: ${layer.name}`, 'info');
        });
        printLine('', 'info');
        printLine('Usage:', 'info');
        printLine('  layer <number>     - Switch to layer by number (0-13)', 'info');
        printLine('  layer <name>       - Switch to layer by name', 'info');
        printLine('  layer next         - Next layer', 'info');
        printLine('  layer prev         - Previous layer', 'info');
        return;
    }

    const arg = parts.slice(1).join(' ').toLowerCase();

    // Handle next/prev
    if (arg === 'next') {
        const newIndex = currentLayerIndex + 1;
        if (changeLayer(newIndex)) {
            printLine(`Switched to layer ${newIndex}: ${LAYERS[newIndex].name}`, 'success');
        } else {
            printLine('Already at the last layer', 'warning');
        }
        return;
    }

    if (arg === 'prev' || arg === 'previous') {
        const newIndex = currentLayerIndex - 1;
        if (changeLayer(newIndex)) {
            printLine(`Switched to layer ${newIndex}: ${LAYERS[newIndex].name}`, 'success');
        } else {
            printLine('Already at the first layer', 'warning');
        }
        return;
    }

    // Handle numeric argument
    const numMatch = arg.match(/^(\d+)$/);
    if (numMatch) {
        const index = parseInt(numMatch[1]);
        if (changeLayer(index)) {
            printLine(`Switched to layer ${index}: ${LAYERS[index].name}`, 'success');
        } else {
            printLine(`Invalid layer number. Must be 0-${LAYERS.length - 1}`, 'error');
        }
        return;
    }

    // Handle name-based switching with aliases
    const layerAliases = {
        'original': 0,
        'arabic': 0,
        'root': 1,
        'lemma': 2,
        'pos': 3,
        'part of speech': 3,
        'pattern': 4,
        'case': 5,
        'gender': 6,
        'number': 7,
        'person': 8,
        'verb form': 9,
        'verb': 9,
        'voice': 10,
        'dependency': 11,
        'dep': 11,
        'role': 12,
        'annotations': 13,
        'annotation': 13,
        'notes': 13
    };

    const layerIndex = layerAliases[arg];
    if (layerIndex !== undefined) {
        changeLayer(layerIndex);
        printLine(`Switched to layer ${layerIndex}: ${LAYERS[layerIndex].name}`, 'success');
    } else {
        printLine(`Unknown layer: "${arg}"`, 'error');
        printLine('Use "layer" to see available layers', 'info');
    }
}

// Layer switching functions
function changeLayer(newIndex) {
    // Bounds checking
    if (newIndex < 0 || newIndex >= LAYERS.length) {
        return false;
    }

    currentLayerIndex = newIndex;
    applyLayerToAllTokens();
    return true;
}

// Apply layer to all visible tokens
function applyLayerToAllTokens() {
    const tokens = document.querySelectorAll('.token');
    tokens.forEach(token => {
        applyLayerToToken(token);
    });
}

function applyLayerToToken(token) {
    const layer = LAYERS[currentLayerIndex];
    const originalText = token.dataset.originalText;

    if (!originalText) {
        console.warn('Token missing originalText', token);
        return; // No original text stored
    }

    // Layer 0: Show original Arabic
    if (layer.id === 0) {
        token.textContent = originalText;
        token.className = 'token';
        return;
    }

    // Layer 13: Show user annotations
    if (layer.id === 13) {
        const annotation = token.dataset.annotation;
        if (annotation) {
            showAnnotation(token, annotation, token.dataset.annotationId);
        } else {
            token.textContent = originalText;
            token.className = 'token';
        }
        return;
    }

    // Linguistic layers (1-12)
    const morphDataRaw = token.dataset.morphology;
    console.log(`Token "${originalText}": morphology data =`, morphDataRaw);

    const morphData = JSON.parse(morphDataRaw || '[]');
    console.log(`Token "${originalText}": parsed morphData =`, morphData);

    const value = extractLayerValue(morphData, layer.field);
    console.log(`Token "${originalText}": extracted ${layer.field} =`, value);

    if (value) {
        showLayerValue(token, value, layer);
    } else {
        // Missing data: show original Arabic
        console.warn(`Token "${originalText}": No value for layer ${layer.name}, showing original`);
        token.textContent = originalText;
        token.className = 'token';
    }
}

function showLayerValue(token, value, layer) {
    const wrapper = document.createElement('span');
    wrapper.className = 'layer-value';
    wrapper.textContent = value;
    wrapper.dir = 'ltr';

    // Apply color coding
    if (layer.colorMap) {
        const colorKey = value.split(' + ')[0]; // Use first value for color
        const colorClass = `${layer.field}-${colorKey}`;
        wrapper.classList.add(colorClass);

        // Fallback to default if specific color not found
        if (!layer.colorMap[colorKey] && layer.colorMap['default']) {
            wrapper.classList.add(`${layer.field}-default`);
        }
    } else {
        wrapper.classList.add(`${layer.field}-value`);
    }

    token.textContent = '';
    token.appendChild(wrapper);
    token.className = 'token';
}

function showAnnotation(token, annotationText, annotationId) {
    const wrapper = document.createElement('span');
    wrapper.className = 'annotation-text';
    wrapper.dir = 'ltr';
    wrapper.textContent = annotationText;

    token.textContent = '';
    token.appendChild(wrapper);
    token.classList.add('annotated');

    if (annotationId) {
        token.dataset.annotationId = annotationId;
    }
}
