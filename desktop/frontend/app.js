import { normalizeCommand, recordCommandInHistory } from './lib/history.js';
import { shouldClearForCommand } from './lib/commandBehavior.js';
import { ANNOTATION_LAYER_INDEX, DEFAULT_LAYER_INDEX, LAYERS } from './lib/layers/definitions.js';
import { createMorphologyCache, fetchMorphologyForVerse } from './lib/layers/morphology.js';
import { LayerManager } from './lib/layers/manager.js';
import { handleLayerCommand } from './lib/layers/layerCommand.js';
import { QueryBuilder } from './lib/concordance/queryBuilder.js';
import { executeConcordanceSearch } from './lib/concordance/search.js';
import { displayConcordanceResults } from './lib/concordance/display.js';
import * as chat from './lib/chat.js';
import * as chatMode from './lib/chat-mode.js';
import { hotbar } from './lib/hotbar.js';
import { modeManager, MODES } from './lib/modes.js';
import { annotationLayerManager, annotationSearch } from './lib/annotations/index.js';

const terminal = document.getElementById('terminal');
const output = document.getElementById('output');
const resultsPane = document.getElementById('results');
const commandInput = document.getElementById('command-input');
const promptSpan = document.getElementById('prompt');

let commandHistory = [];
let historyIndex = -1;
let currentPrompt = 'kalima >';
let invoke;
let baseFontSize = 16;
let zoomFactor = 1;

// Command history persistence key
const COMMAND_HISTORY_KEY = 'kalima-command-history';
const MAX_HISTORY_SIZE = 100;

function saveCommandHistory() {
    try {
        // Keep only the last MAX_HISTORY_SIZE commands
        const historyToSave = commandHistory.slice(-MAX_HISTORY_SIZE);
        localStorage.setItem(COMMAND_HISTORY_KEY, JSON.stringify(historyToSave));
    } catch (err) {
        console.warn('Failed to save command history:', err);
    }
}

const morphologyCache = createMorphologyCache();
const layerManager = new LayerManager({ layers: LAYERS, defaultIndex: DEFAULT_LAYER_INDEX });

let queryMode = false;
let savedInputValue = '';
let savedScrollPosition = 0;  // Preserve scroll position when switching modes
const queryBuilder = new QueryBuilder();
const anchorTokenMap = new Map();
let queryModeHintShown = false;

// Debounce timer for auto-search
let searchDebounceTimer = null;
const SEARCH_DEBOUNCE_MS = 300;

// Track pending search request to cancel stale ones
let pendingSearchAbortController = null;

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

// Convert Western numerals to Arabic-Indic numerals (٠١٢٣٤٥٦٧٨٩)
function toArabicIndic(num) {
    const arabicNumerals = ['٠', '١', '٢', '٣', '٤', '٥', '٦', '٧', '٨', '٩'];
    return String(num).split('').map(d => arabicNumerals[parseInt(d)] || d).join('');
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

    // Load command history from localStorage
    try {
        const savedHistory = localStorage.getItem(COMMAND_HISTORY_KEY);
        if (savedHistory) {
            commandHistory = JSON.parse(savedHistory);
            historyIndex = commandHistory.length;
        }
    } catch (err) {
        console.warn('Failed to load command history:', err);
    }

    // Disable right-click context menu
    document.addEventListener('contextmenu', (e) => {
        e.preventDefault();
    });

    // Initialize hotbar
    hotbar.init();

    // Connect hotbar layer dropdown to layer manager
    hotbar.setLayerChangeCallback((layerIndex) => {
        layerManager.changeLayer(layerIndex);
    });

    // Track layer before entering annotate mode to restore later
    let layerBeforeAnnotate = null;

    // Connect mode manager to existing query mode
    modeManager.onChange((mode) => {
        if (mode === MODES.SEARCH && !queryMode) {
            enterQueryMode();
        } else if (mode !== MODES.SEARCH && queryMode) {
            exitQueryMode();
        }

        // Auto-switch to annotation layer when entering Annotate mode
        if (mode === MODES.ANNOTATE) {
            layerBeforeAnnotate = layerManager.getCurrentLayerIndex();
            if (layerBeforeAnnotate !== ANNOTATION_LAYER_INDEX) {
                layerManager.changeLayer(ANNOTATION_LAYER_INDEX);
                printLine('Switched to Annotations layer. Click any word to add/edit annotation.', 'info');
            }
        } else if (layerBeforeAnnotate !== null && layerBeforeAnnotate !== ANNOTATION_LAYER_INDEX) {
            // Restore previous layer when leaving annotate mode
            layerManager.changeLayer(layerBeforeAnnotate);
            layerBeforeAnnotate = null;
        }

        // Update hotbar layer indicator when layer changes
        const currentLayer = layerManager.getCurrentLayer();
        if (currentLayer) {
            hotbar.updateLayerIndicator(currentLayer.name);
        }
    });

    // Update hotbar when layer changes
    layerManager.onChange((layer) => {
        hotbar.updateLayerIndicator(layer.name);
    });

    commandInput.focus();
});

// Handle clicks on tokens for inline editing, otherwise focus command input
document.addEventListener('click', (e) => {
    const token = e.target.closest('.token');
    if (token && !token.classList.contains('editing')) {
        if (queryMode) {
            e.preventDefault();
            handleTokenQueryClick(token, { addConstraint: e.shiftKey });
            commandInput.focus();
            return;
        }
        // Only allow editing on annotation layer (Layer 13)
        if (layerManager.getCurrentLayerIndex() === ANNOTATION_LAYER_INDEX) {
            startInlineEdit(token);
        }
    } else if (!e.target.closest('.inline-editor')) {
        commandInput.focus();
    }
});

output.addEventListener('mouseover', (e) => {
    if (!queryMode || !e.shiftKey) return;
    const token = e.target.closest('.token');
    if (!token) return;
    showTransientLabel(token);
});

output.addEventListener('mouseout', (e) => {
    const token = e.target.closest('.token');
    if (!token) return;
    removeTransientLabel(token);
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
    // Ctrl/Cmd+Q enters Query Mode without stealing normal typing (e.g. starting a command with 'q').
    if (!queryMode && (e.ctrlKey || e.metaKey) && (e.key === 'q' || e.key === 'Q')) {
        e.preventDefault();
        enterQueryMode();
        return;
    }

    if (queryMode) {
        e.stopImmediatePropagation();
        if (e.key === 'Enter') {
            e.preventDefault();
            const text = (commandInput.value || '').trim();
            if (text && !text.startsWith('#')) {
                await runCommandWhileQueryMode(text);
            } else {
                await executeConcordance();
            }
        } else if (e.key === 'Escape') {
            e.preventDefault();
            // If there are selections, clear them first; otherwise exit query mode
            if (queryBuilder.anchors && queryBuilder.anchors.length > 0) {
                clearAllQuerySelections();
            } else {
                exitQueryMode();
            }
        } else if ((e.ctrlKey || e.metaKey) && (e.key === 'z' || e.key === 'Z')) {
            e.preventDefault();
            removeLastQueryAnchor();
        }
        return;
    }

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

document.addEventListener('keydown', (e) => {
    if (!queryMode) return;

    const layerMap = {
        o: 0, O: 0,  // Original
        r: 1, R: 1,  // Root
        l: 2, L: 2,  // Lemma
        p: 3, P: 3,  // POS
        c: 5, C: 5,  // Case
        g: 6, G: 6   // Gender
    };

    if (e.key === 'Escape') {
        e.preventDefault();
        e.stopImmediatePropagation();
        exitQueryMode();
        return;
    }

    if (e.key === 'Enter') {
        e.preventDefault();
        e.stopImmediatePropagation();
        executeConcordance();
        return;
    }

    if (e.key === '?' || (e.shiftKey && e.key === '/')) {
        const current = commandInput?.value?.trim() || '';
        if (!current) {
            e.preventDefault();
            e.stopImmediatePropagation();
            showQueryModeHint();
            return;
        }
    }

    const isLayerKey = layerMap[e.key] !== undefined;
    if (isLayerKey) {
        // Avoid stealing normal typing in Query Mode: layer shortcuts always require Alt.
        if (!e.altKey) return;
        e.preventDefault();
        e.stopImmediatePropagation();
        layerManager.changeLayer(layerMap[e.key]);
        commandInput?.focus();
        return;
    }
}, true);

function getChatContext() {    return {        printLine,        clearAllPanes,        terminal,        promptSpan,        currentPrompt,        commandInput,        output,        scrollToBottom    };}
async function runUserCommand(command) {
    // Handle chat mode messages
    if (chatMode.isChatModeActive() && command.trim().toLowerCase() !== 'exit') {
        const trimmed = command.trim();
        if (trimmed) {
            await chatMode.handleChatMessage(trimmed, getChatContext());
        }
        commandInput.value = '';
        commandInput.focus();
        return;
    }
    const trimmed = normalizeCommand(command);
    if (!trimmed) return;

    recordCommandInHistory(commandHistory, trimmed);
    historyIndex = commandHistory.length;

    // Persist command history to localStorage
    saveCommandHistory();

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
        clearAllPanes();
        printLine(`${currentPrompt} ${command}`, 'command-echo');
        showHistory();
        return prefillApplied;
    }

    let trimmed = command.trim();

    // Simpler commands: bare number → chapter, colon format → verse
    // Match patterns like "1", "114", "1:1", "2:255"
    const bareNumberMatch = /^(\d{1,3})$/.exec(trimmed);
    const colonFormatMatch = /^(\d{1,3}):(\d{1,3})$/.exec(trimmed);

    if (colonFormatMatch) {
        // "2:255" → "read 2:255" (go to specific verse)
        trimmed = `read ${colonFormatMatch[1]}:${colonFormatMatch[2]}`;
    } else if (bareNumberMatch) {
        // "2" → "read chapter 2" (go to entire surah)
        const surahNum = parseInt(bareNumberMatch[1], 10);
        if (surahNum >= 1 && surahNum <= 114) {
            trimmed = `read chapter ${surahNum}`;
        }
    }

    const cmd = (trimmed.split(/\s+/)[0] || '').toLowerCase();

    // Enter concordance Query Mode locally (no server roundtrip)
    if (cmd === 'q' || cmd === 'query' || cmd === 'concordance') {
        enterQueryMode();
        return true; // prevent input clear
    }

    // Enter Chat Mode with Quran AI agent
    if (cmd === 'chat' || cmd === 'agent' || cmd === 'ai') {
        await chatMode.enterChatMode(getChatContext());
        return true; // prevent input clear
    }

    // Exit chat mode
    if (cmd === 'exit' && chatMode.isChatModeActive()) {
        chatMode.exitChatMode(getChatContext());
        return prefillApplied;
    }

    // Handle 'layer' command locally (without clearing)
    if (cmd === 'layer') {
        handleLayerCommand(trimmed, { clearOutput, printLine, prompt: currentPrompt }, layerManager);
        return prefillApplied;
    }

    // Handle annotation search command
    if (cmd === 'annotations' || cmd === 'ann' || cmd === 'verify') {
        const searchQuery = trimmed.slice(cmd.length).trim();
        await executeAnnotationSearch(searchQuery);
        return prefillApplied;
    }

    // Clear screen before executing command (for most commands)
    if (shouldClearForCommand(trimmed)) {
        clearAllPanes();
    }

    // Echo command after clearing
    printLine(`${currentPrompt} ${command}`, 'command-echo');

    if (!invoke) {
        printLine('Error: Tauri API not loaded', 'error');
        return prefillApplied;
    }

    try {
        const result = await invoke('execute_command', { command: trimmed });

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
            } else if (outputType === 'chapter') {
                printChapter(result.output);
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

function enterQueryMode() {
    queryMode = true;
    queryBuilder.isActive = true;
    savedInputValue = commandInput.value;
    savedScrollPosition = output.scrollTop;  // Save scroll position before mode switch
    commandInput.readOnly = true;  // Make read-only in search mode
    commandInput.value = '';  // Hide confusing text query - visual builder shows it
    commandInput.placeholder = 'Click words to search • Esc to clear • Switch layers via hotbar';
    terminal?.classList.add('query-mode-active');
    promptSpan.textContent = decoratePromptForQueryMode(currentPrompt);
    maybeShowQueryModeHint();
    commandInput.focus();
}

function exitQueryMode() {
    queryMode = false;
    queryBuilder.isActive = false;
    queryBuilder.clear();
    anchorTokenMap.clear();
    commandInput.readOnly = false;
    commandInput.value = savedInputValue;
    commandInput.placeholder = '';  // Clear search mode placeholder
    terminal?.classList.remove('query-mode-active');
    promptSpan.textContent = currentPrompt;
    clearQueryMarkers();
    commandInput.focus();
    // Restore scroll position after mode switch
    requestAnimationFrame(() => {
        output.scrollTop = savedScrollPosition;
    });
}

function decoratePromptForQueryMode(prompt) {
    const base = String(prompt || 'kalima >');
    if (base.includes('[Q]')) return base;
    const trimmed = base.replace(/\s+$/, '');
    if (trimmed.endsWith('>')) {
        return `${trimmed.slice(0, -1).trimEnd()} [Q] >`;
    }
    return `${trimmed} [Q]`;
}

function clearQueryMarkers(root = document) {
    root.querySelectorAll('.token[data-anchor-num]').forEach((token) => {
        delete token.dataset.anchorNum;
    });
    root.querySelectorAll('.transient-layer-label').forEach((label) => label.remove());
    anchorTokenMap.clear();
}

function showTransientLabel(token) {
    if (!token) return;
    const existing = token.querySelector(':scope > .transient-layer-label');
    if (existing) return;

    const currentLayer = layerManager.getCurrentLayer();
    const label = document.createElement('span');
    label.className = 'transient-layer-label';
    label.textContent = currentLayer?.name || '';
    token.appendChild(label);
}

function removeTransientLabel(token) {
    if (!token) return;
    const existing = token.querySelector(':scope > .transient-layer-label');
    existing?.remove();
}

function getTokenMorphology(token) {
    try {
        const raw = token.dataset.morphology;
        if (!raw) return [];
        const parsed = JSON.parse(raw);
        return Array.isArray(parsed) ? parsed : [];
    } catch {
        return [];
    }
}

function getConstraintForCurrentLayer(token) {
    const layer = layerManager.getCurrentLayer();
    if (layer?.id === 0) {
        const value = token.dataset.originalText || token.textContent || '';
        return value ? { field: 'text', value } : null;
    }

    if (!layer?.field) return null;
    const segments = getTokenMorphology(token);
    for (const seg of segments) {
        const value = seg?.[layer.field];
        if (value != null && value !== '') {
            return { field: layer.field, value: String(value) };
        }
    }
    return null;
}

function ensureTokenAnchor(token) {
    const existing = Number(token.dataset.anchorNum);
    if (Number.isFinite(existing) && existing > 0) return existing;
    const anchorNum = queryBuilder.createAnchor();
    token.dataset.anchorNum = String(anchorNum);
    anchorTokenMap.set(anchorNum, token);
    return anchorNum;
}

function handleTokenQueryClick(token, { addConstraint = false } = {}) {
    // Check if token already has an anchor
    const existingAnchor = Number(token.dataset.anchorNum);
    const hasExistingAnchor = Number.isFinite(existingAnchor) && existingAnchor > 0;

    // If token already selected and not adding constraint, toggle it off
    if (hasExistingAnchor && !addConstraint) {
        queryBuilder.removeAnchor(existingAnchor);
        delete token.dataset.anchorNum;
        anchorTokenMap.delete(existingAnchor);
        commandInput.value = queryBuilder.buildQueryString();
        triggerAutoSearch();
        return;
    }

    const anchorNum = ensureTokenAnchor(token);
    const constraint = getConstraintForCurrentLayer(token);
    if (!constraint) {
        printResultLine(`Cannot search on current layer. Switch to a searchable layer (Original, Root, Lemma, POS, etc.)`, 'warning');
        return;
    }

    if (addConstraint) {
        // Shift+click adds additional constraint from current layer to existing anchor
        queryBuilder.toggleConstraint(anchorNum, constraint.field, constraint.value);
        if (!queryBuilder.getAnchor(anchorNum)) {
            delete token.dataset.anchorNum;
            anchorTokenMap.delete(anchorNum);
        }
    } else {
        queryBuilder.addConstraint(anchorNum, constraint.field, constraint.value);
    }

    commandInput.value = queryBuilder.buildQueryString();
    triggerAutoSearch();
}

function removeLastQueryAnchor() {
    const anchors = (queryBuilder.anchors || []).slice().sort((a, b) => a.anchorNum - b.anchorNum);
    if (anchors.length === 0) return false;
    const last = anchors[anchors.length - 1];
    queryBuilder.removeAnchor(last.anchorNum);

    const token = anchorTokenMap.get(last.anchorNum);
    if (token) {
        delete token.dataset.anchorNum;
    }
    anchorTokenMap.delete(last.anchorNum);

    commandInput.value = queryBuilder.buildQueryString();
    triggerAutoSearch();
    return true;
}

/**
 * Clear all query selections
 */
function clearAllQuerySelections() {
    // Clear all anchor markers from tokens
    anchorTokenMap.forEach((token, anchorNum) => {
        if (token) delete token.dataset.anchorNum;
    });
    anchorTokenMap.clear();
    queryBuilder.clear();
    commandInput.value = '';
    clearResults();
    clearConcordanceHighlights();
}

function showQueryModeHint() {
    printLine(
        "Search Mode: Click words to search (auto-updates). Click again to unselect. Shift+click adds layer constraint. Switch layers via hotbar or Alt+O/R/L/P/C/G. Esc clears selection. Ctrl+Z removes last word.",
        "info"
    );
}

function maybeShowQueryModeHint() {
    if (queryModeHintShown) return;
    queryModeHintShown = true;
    showQueryModeHint();
}

/**
 * Trigger auto-search with debouncing.
 * Cancels any pending search and schedules a new one.
 */
function triggerAutoSearch() {
    // Clear existing debounce timer
    if (searchDebounceTimer) {
        clearTimeout(searchDebounceTimer);
        searchDebounceTimer = null;
    }

    // Cancel any pending search request
    if (pendingSearchAbortController) {
        pendingSearchAbortController.abort();
        pendingSearchAbortController = null;
    }

    const queryString = queryBuilder.buildQueryString().trim();

    // If query is empty, clear results
    if (!queryString) {
        clearResults();
        updateVisualQueryBuilder();
        return;
    }

    // Update visual query builder immediately
    updateVisualQueryBuilder();

    // Schedule search with debounce
    searchDebounceTimer = setTimeout(async () => {
        searchDebounceTimer = null;

        // Create abort controller for this request
        pendingSearchAbortController = new AbortController();

        // Clear results but preserve visual query builder
        clearConcordanceHighlights();
        const visualBuilder = resultsPane?.querySelector('.visual-query-builder');
        if (resultsPane) {
            resultsPane.innerHTML = '';
            if (visualBuilder) resultsPane.appendChild(visualBuilder);
        }

        try {
            const searchResults = await executeConcordanceSearch(
                { query: queryString },
                { signal: pendingSearchAbortController.signal }
            );
            await displayConcordanceResults(searchResults, {
                outputEl: resultsPane,
                layerManager,
                morphologyCache,
                fetchMorphologyForVerse,
                append: true,
            });
        } catch (err) {
            if (err.name !== 'AbortError') {
                printResultLine(`Search error: ${err?.message || err}`, 'error');
            }
        } finally {
            pendingSearchAbortController = null;
        }
    }, SEARCH_DEBOUNCE_MS);
}

/**
 * Update the visual query builder display in results pane
 */
function updateVisualQueryBuilder() {
    // Remove existing visual query builder if present
    const existing = resultsPane?.querySelector('.visual-query-builder');
    if (existing) existing.remove();

    const anchors = queryBuilder.anchors;
    if (!anchors || anchors.length === 0) return;

    const container = document.createElement('div');
    container.className = 'visual-query-builder';

    anchors.forEach((anchor, idx) => {
        if (!anchor.constraints || anchor.constraints.length === 0) return;

        const anchorBox = document.createElement('div');
        anchorBox.className = 'query-anchor-box';
        anchorBox.dataset.anchorNum = anchor.anchorNum;

        // Get the token element for this anchor to show the word
        const tokenEl = anchorTokenMap.get(anchor.anchorNum);
        const wordText = tokenEl?.dataset?.originalText || `#${anchor.anchorNum}`;

        const wordSpan = document.createElement('span');
        wordSpan.className = 'query-word arabic';
        wordSpan.textContent = wordText;
        anchorBox.appendChild(wordSpan);

        const constraintsDiv = document.createElement('div');
        constraintsDiv.className = 'query-constraints';

        anchor.constraints.forEach(c => {
            const pill = document.createElement('span');
            pill.className = `query-constraint query-constraint-${c.field}`;
            pill.textContent = `${c.field}: ${c.value}`;
            pill.title = `Click to remove`;
            pill.addEventListener('click', () => {
                queryBuilder.toggleConstraint(anchor.anchorNum, c.field, c.value);
                if (!queryBuilder.getAnchor(anchor.anchorNum)) {
                    const token = anchorTokenMap.get(anchor.anchorNum);
                    if (token) delete token.dataset.anchorNum;
                    anchorTokenMap.delete(anchor.anchorNum);
                }
                commandInput.value = queryBuilder.buildQueryString();
                triggerAutoSearch();
            });
            constraintsDiv.appendChild(pill);
        });

        anchorBox.appendChild(constraintsDiv);

        // Add remove button for entire anchor
        const removeBtn = document.createElement('button');
        removeBtn.className = 'query-anchor-remove';
        removeBtn.textContent = '×';
        removeBtn.title = 'Remove this word from query';
        removeBtn.addEventListener('click', () => {
            queryBuilder.removeAnchor(anchor.anchorNum);
            const token = anchorTokenMap.get(anchor.anchorNum);
            if (token) delete token.dataset.anchorNum;
            anchorTokenMap.delete(anchor.anchorNum);
            commandInput.value = queryBuilder.buildQueryString();
            triggerAutoSearch();
        });
        anchorBox.appendChild(removeBtn);

        container.appendChild(anchorBox);

        // Add connector between anchors (except last)
        if (idx < anchors.length - 1) {
            const connector = document.createElement('span');
            connector.className = 'query-connector';
            connector.textContent = '+';
            container.appendChild(connector);
        }
    });

    // Insert at top of results pane
    if (resultsPane?.firstChild) {
        resultsPane.insertBefore(container, resultsPane.firstChild);
    } else {
        resultsPane?.appendChild(container);
    }
}

async function runCommandWhileQueryMode(commandText) {
    const queryString = queryBuilder.buildQueryString();

    // Temporarily suspend query mode UI so command entry behaves normally.
    queryMode = false;
    queryBuilder.isActive = false;
    terminal?.classList.remove('query-mode-active');
    promptSpan.textContent = currentPrompt;

    await runUserCommand(commandText);

    // Restore query mode UI (keep current query builder state).
    queryMode = true;
    queryBuilder.isActive = true;
    terminal?.classList.add('query-mode-active');
    promptSpan.textContent = decoratePromptForQueryMode(currentPrompt);
    commandInput.value = queryString;
    commandInput.focus();
}

async function executeConcordance() {
    const queryString = (commandInput.value || queryBuilder.buildQueryString()).trim();
    if (!queryString) {
        printLine('Query is empty.', 'warning');
        return;
    }

    clearResults();
    clearConcordanceHighlights();
    printResultLine(`${decoratePromptForQueryMode(currentPrompt)} ${queryString}`, 'command-echo');
    try {
        const searchResults = await executeConcordanceSearch({ query: queryString });
        await displayConcordanceResults(searchResults, {
            outputEl: resultsPane,
            layerManager,
            morphologyCache,
            fetchMorphologyForVerse,
            append: true,
        });
        scrollResultsToTop();
    } catch (err) {
        printResultLine(`Concordance error: ${err?.message || err}`, 'error');
    } finally {
        exitQueryMode();
    }
}

function clearConcordanceHighlights(root = document) {
    root.querySelectorAll('.token[data-concordance-hit]').forEach((token) => {
        delete token.dataset.concordanceHit;
    });
}

async function executeAnnotationSearch(query) {
    if (!query) {
        printLine('Usage: annotations <search term>', 'info');
        printLine('Search for annotations matching a term and see all occurrences.', 'info');
        return;
    }

    clearResults();
    printResultLine(`Searching annotations for: "${query}"`, 'command-echo');

    try {
        const searchResults = await annotationSearch.search(query);
        await annotationSearch.displayResults(searchResults, {
            outputEl: resultsPane,
            invoke,
            layerManager,
            morphologyCache,
            fetchMorphologyForVerse,
        });
        scrollResultsToTop();
    } catch (err) {
        printResultLine(`Annotation search error: ${err?.message || err}`, 'error');
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
    const surah = input.dataset.surah;
    const ayah = input.dataset.ayah;
    const index = input.dataset.index;
    const targetId = `${surah}:${ayah}:${index}`;

    // Get current annotation layer
    const currentAnnotationLayer = annotationLayerManager.getCurrentLayer();

    tokenElement.classList.remove('editing');

    if (annotation) {
        // Save annotation to backend via API using current annotation layer
        try {
            const response = await fetch('http://localhost:8080/annotations', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    target_id: targetId,
                    layer: currentAnnotationLayer.id,
                    payload: { annotation }
                })
            });
            const data = await response.json();
            if (data.id) {
                tokenElement.dataset.annotationId = data.id;
                tokenElement.dataset.annotationLayer = currentAnnotationLayer.id;
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
    const morphData = await fetchMorphologyForVerse({ surah: verse.surah, ayah: verse.ayah, cache: morphologyCache });

    // Store morphology in each token's dataset
    if (verse.tokens && verse.tokens.length > 0) {
        verse.tokens.forEach((_, index) => {
            const tokenSpan = container.querySelector(
                `.token[data-surah="${verse.surah}"][data-ayah="${verse.ayah}"][data-index="${index}"]`
            );

            // Only set morphology if not already present (respects pre-set data in tests)
            if (tokenSpan && morphData[index] && !tokenSpan.dataset.morphology) {
                tokenSpan.dataset.morphology = JSON.stringify(morphData[index]);
            }
        });
    }

    // Load existing annotations for this verse (pass container to scope the search)
    await loadAnnotations(verse.surah, verse.ayah, container);

    // Apply current layer to the newly added verse
    layerManager.applyToAllTokens();

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

async function printChapter(chapter) {
    const container = document.createElement('div');
    container.className = 'chapter-container mushaf-layout';

    // Chapter header with Surah name in Arabic
    const header = document.createElement('div');
    header.className = 'chapter-header';
    const surahName = resolveSurahName(chapter.surah, chapter.name);
    header.innerHTML = `<span class="surah-name-arabic">سورة ${surahName}</span>`;
    container.appendChild(header);

    // Bismillah for all surahs except At-Tawbah (9) - shown as decorative header
    if (chapter.surah !== 9 && chapter.surah !== 1) {
        const bismillah = document.createElement('div');
        bismillah.className = 'bismillah';
        bismillah.textContent = 'بِسْمِ ٱللَّهِ ٱلرَّحْمَٰنِ ٱلرَّحِيمِ';
        container.appendChild(bismillah);
    }

    // Single continuous text container for Mushaf-style layout
    const textFlow = document.createElement('div');
    textFlow.className = 'mushaf-text-flow';
    textFlow.dir = 'rtl';
    container.appendChild(textFlow);
    output.appendChild(container);

    // Render all verses inline with verse markers
    for (const verse of chapter.verses) {
        // Render tokens inline
        if (verse.tokens && verse.tokens.length > 0) {
            verse.tokens.forEach((token, index) => {
                // Token is now { index, segments: [{ token_text, root, pos, ... }] }
                const segments = token.segments || [];
                const tokenText = segments[0]?.token_text || '';

                const tokenSpan = document.createElement('span');
                tokenSpan.className = 'token';
                tokenSpan.dataset.surah = verse.surah;
                tokenSpan.dataset.ayah = verse.ayah;
                tokenSpan.dataset.index = token.index ?? index;
                tokenSpan.dataset.originalText = tokenText;
                tokenSpan.dataset.displayLayer = 'original';
                tokenSpan.textContent = tokenText;

                // Attach morphology data for layer switching
                if (segments.length > 0) {
                    tokenSpan.dataset.morphology = JSON.stringify(segments);
                }

                textFlow.appendChild(tokenSpan);

                // Add space after each token
                textFlow.appendChild(document.createTextNode(' '));
            });
        } else if (verse.text) {
            // Fallback: render full text if no tokens
            const textSpan = document.createElement('span');
            textSpan.className = 'verse-text';
            textSpan.dataset.surah = verse.surah;
            textSpan.dataset.ayah = verse.ayah;
            textSpan.textContent = verse.text;
            textFlow.appendChild(textSpan);
            textFlow.appendChild(document.createTextNode(' '));
        }

        // Add verse number marker ﴿١﴾
        const marker = document.createElement('span');
        marker.className = 'verse-marker';
        marker.dataset.surah = verse.surah;
        marker.dataset.ayah = verse.ayah;
        marker.textContent = `﴿${toArabicIndic(verse.ayah)}﴾`;
        marker.title = `${verse.surah}:${verse.ayah}`;
        textFlow.appendChild(marker);
        textFlow.appendChild(document.createTextNode(' '));
    }

    // Morphology is now included with token data - no additional requests needed

    // Apply current layer to all tokens
    layerManager.applyToAllTokens();

    // Scroll to top for chapter view
    output.scrollTop = 0;
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

        const arabicStats = analyzeArabic(line);
        if (arabicStats.hasArabic) {
            if (arabicStats.ratio >= 0.6) {
                lineDiv.classList.add('arabic');
            } else {
                lineDiv.classList.add('contains-arabic');
            }
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
    const arabicStats = analyzeArabic(text);
    if (arabicStats.hasArabic) {
        if (arabicStats.ratio >= 0.6) {
            div.classList.add('arabic');
        } else {
            div.classList.add('contains-arabic');
        }
    }

    div.textContent = text;
    output.appendChild(div);
    scrollToBottom();
}

function analyzeArabic(text) {
    let arabic = 0;
    let total = 0;
    for (const ch of String(text || '')) {
        if (/\s/.test(ch)) continue;
        total += 1;
        if (/[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]/.test(ch)) {
            arabic += 1;
        }
    }
    return { hasArabic: arabic > 0, ratio: total ? arabic / total : 0 };
}

function scrollToBottom() {
    output.scrollTop = output.scrollHeight;
}

function scrollResultsToTop() {
    if (!resultsPane) return;
    resultsPane.scrollTop = 0;
}

function clearOutput() {
    output.innerHTML = '';
}

function clearResults() {
    if (!resultsPane) return;
    resultsPane.innerHTML = '';
}

function clearAllPanes() {
    clearOutput();
    clearResults();
}

function printResultLine(text, className = '') {
    if (!resultsPane) {
        printLine(text, className);
        return;
    }

    const div = document.createElement('div');
    div.className = `output-line ${className}`;
    if (/[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]/.test(text)) {
        div.classList.add('arabic');
    }
    div.textContent = text;
    resultsPane.appendChild(div);
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

// (layer system moved to desktop/frontend/lib/layers/*)
