// ===== Codex Research Canvas =====
// Interactive Quran text with layered analysis

const LAYER_DEFINITIONS = {
    letter: {
        label: 'Letters & Diacritics',
        description: 'Select individual graphemes or diacritics to describe orthographic cues.',
        categories: [
            { id: 'primary-letter', label: 'حرف أصلي · Primary Letter' },
            { id: 'diacritic-vowel', label: 'حركة · Vowel Diacritic' },
            { id: 'sukun', label: 'سكون · Sukun' },
            { id: 'shadda', label: 'شدة · Gemination' }
        ]
    },

    highlightMatch(text, term, result) {
        if (!text) return '';
        const target = term || result?.matchTerm || '';
        if (!target) return this.escapeHtml(text);
        const re = new RegExp(this.escapeRegex(target), 'g');
        return this.escapeHtml(text).replace(re, m => `<span class="match-highlight">${m}</span>`);
    },

    escapeRegex(str) {
        return str.replace(/[-/\\^$*+?.()|[\]{}]/g, '\\$&');
    },
    morphological: {
        label: 'Morphological Units',
        description: 'Assign prefixes, stems, clitics, and suffixes built from letter spans.',
        categories: [
            { id: 'prefix', label: 'سابقة · Prefix' },
            { id: 'stem', label: 'جذر/أصل · Stem' },
            { id: 'suffix', label: 'لاحقة · Suffix' },
            { id: 'clitic', label: 'ضمير/واو/ياء · Clitic' },
            { id: 'particle', label: 'حرف جر · Particle' }
        ]
    },
    word: {
        label: 'Words & Phrases',
        description: 'Compose linguistically valid word-level structures and idioms.',
        categories: [
            { id: 'idafa', label: 'إضافة · Genitive Construct' },
            { id: 'verbal-clause', label: 'جملة فعلية · Verbal Clause' },
            { id: 'nominal-clause', label: 'جملة اسمية · Nominal Clause' },
            { id: 'prepositional-phrase', label: 'شبه جملة · Prepositional Phrase' },
            { id: 'adjectival-phrase', label: 'تركيب وصفي · Adjectival Phrase' }
        ]
    },
    sentence: {
        label: 'Sentence Structures',
        description: 'Work with supra-ayat structures and discourse composition.',
        categories: [
            { id: 'compound', label: 'جملة مركبة · Compound' },
            { id: 'conditional', label: 'جملة شرطية · Conditional' },
            { id: 'emphatic', label: 'جملة توكيدية · Emphatic' },
            { id: 'interrogative', label: 'جملة استفهامية · Interrogative' },
            { id: 'narrative', label: 'تركيب خبري · Narrative Unit' }
        ]
    }
};

const MORPH_BLOCKS = [
    { label: 'PREFIX', value: 'prefix' },
    { label: 'STEM', value: 'stem' },
    { label: 'SUFFIX', value: 'suffix' },
    { label: 'CLITIC', value: 'clitic' },
    { label: 'NOUN (N)', value: 'pos:n' },
    { label: 'VERB (V)', value: 'pos:v' },
    { label: 'ADJ', value: 'pos:adj' },
    { label: 'PRON', value: 'pos:pron' },
    { label: 'PARTICLE', value: 'pos:part' }
];

const SYNTAX_BLOCKS = [
    { label: 'Noun (N)', value: 'n' },
    { label: 'Verb (V)', value: 'v' },
    { label: 'Adj (ADJ)', value: 'adj' },
    { label: 'Pron (PRON)', value: 'pron' },
    { label: 'Prep (P)', value: 'p' },
    { label: 'Conj (CONJ)', value: 'conj' },
    { label: 'Particle (PART)', value: 'part' }
];

const STRUCTURE_COLOR_CLASSES = {
    'prefix': 'structure-tag-prefix',
    'stem': 'structure-tag-stem',
    'suffix': 'structure-tag-suffix',
    'clitic': 'structure-tag-clitic',
    'particle': 'structure-tag-particle',
    'idafa': 'structure-tag-idafa',
    'verbal-clause': 'structure-tag-verbal-clause',
    'nominal-clause': 'structure-tag-nominal-clause',
    'prepositional-phrase': 'structure-tag-prepositional-phrase',
    'adjectival-phrase': 'structure-tag-adjectival-phrase',
    'compound': 'structure-tag-compound',
    'conditional': 'structure-tag-conditional',
    'emphatic': 'structure-tag-emphatic',
    'interrogative': 'structure-tag-interrogative',
    'narrative': 'structure-tag-narrative',
    'primary-letter': 'structure-tag-primary-letter',
    'diacritic-vowel': 'structure-tag-diacritic-vowel',
    'sukun': 'structure-tag-sukun',
    'shadda': 'structure-tag-shadda'
};

const Canvas = {
    // State
    currentLayer: 'sentence',
    currentVerse: null,
    selectedStructureCategory: null,
    appMode: 'read',
    mode: 'select', // select, annotate
    selectedWords: [],
    surahSummaries: [],
    surahCache: {},
    currentSurahNumber: null,
    currentSurahData: null,
    currentAyahNumber: null,
    rootOptions: [],
    morphPatterns: [],
    syntaxPatterns: [],
    connectionSource: null,
    connections: { internal: [], external: [] },
    pronounData: null,
    actionHistory: [],
    expandedSurahs: new Set(),
    navJourney: [],
    currentHypotheses: [],
    currentSearchResults: null,
    patternSegments: [],

    // Drag selection state
    isDragging: false,
    dragStartElement: null,
    dragSelectionActive: false,

    // Translation state
    translations: [],
    editingSegment: null,
    tooltipEl: null,

    // Initialize
    init() {
        this.setupEventListeners();
        this.tooltipEl = document.getElementById('textTooltip');
        this.renderLayerPalette();
        this.setAppMode(this.appMode);
        this.setHypothesisTargetForLayer(this.currentLayer);
        this.setupMorphBuilder();
        this.setupSyntaxBuilder();
        this.loadSurahSummaries();
        this.loadRootOptions();
        this.loadMorphPatterns();
        this.loadSyntaxPatterns();
        this.renderNavMap();
    },

    setupEventListeners() {
        // Menu toggle
        const sideMenu = document.getElementById('sideMenu');
        const canvasEl = document.getElementById('canvas');

        document.getElementById('menuToggle').addEventListener('click', () => {
            sideMenu.classList.toggle('collapsed');
            canvasEl.classList.toggle('menu-open');
        });

        // Pattern instances panel toggle
        const patternToggle = document.getElementById('patternToggle');
        if (patternToggle) {
            patternToggle.addEventListener('click', () => this.togglePatternPanel());
        }

        const closePatternPanel = document.getElementById('closePatternPanel');
        if (closePatternPanel) {
            closePatternPanel.addEventListener('click', () => this.closePatternPanel());
        }

        // Tool buttons

        // Pattern form
        document.getElementById('patternForm').addEventListener('submit', (e) => {
            e.preventDefault();
            this.savePattern();
        });

        document.getElementById('cancelPattern').addEventListener('click', () => {
            document.getElementById('patternModal').style.display = 'none';
        });

        const refreshPronouns = document.getElementById('refreshPronouns');
        if (refreshPronouns) {
            refreshPronouns.addEventListener('click', () => this.loadPronounData());
        }

        const pronounForm = document.getElementById('pronounForm');
        if (pronounForm) {
            pronounForm.addEventListener('submit', (e) => this.submitPronounReference(e));
        }

        const libraryBtn = document.getElementById('librarySearchBtn');
        if (libraryBtn) {
            libraryBtn.addEventListener('click', () => this.handleLibrarySearch());
        }
        const libraryInput = document.getElementById('librarySearchInput');
        if (libraryInput) {
            libraryInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    this.handleLibrarySearch();
                }
            });
        }

        const hypForm = document.getElementById('hypothesisForm');
        if (hypForm) {
            hypForm.addEventListener('submit', (e) => this.submitHypothesis(e));
        }

        const patternBreakBtn = document.getElementById('patternBreakBtn');
        if (patternBreakBtn) {
            patternBreakBtn.addEventListener('click', () => this.breakPatternWord());
        }
        const patternSearchBtn = document.getElementById('patternSearchBtn');
        if (patternSearchBtn) {
            patternSearchBtn.addEventListener('click', () => this.submitPatternSearch());
        }

        // Global keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;

            switch(e.key.toLowerCase()) {
                case 'escape':
                    this.setMode('select');
                    this.clearSelection();
                    break;
                case 'backspace':
                case 'arrowleft':
                case 'arrowup':
                    this.navigateLayerUp();
                    break;
            }
        });

        // Disable default context menu (we use right-click for layer up)
        document.addEventListener('contextmenu', (e) => {
            e.preventDefault();
        });

        // Hide context menu on click outside
        document.addEventListener('click', () => {
            document.getElementById('contextMenu').style.display = 'none';
        });

        // Global mouseup to handle drag selection ending anywhere
        document.addEventListener('mouseup', () => {
            if (this.isDragging) {
                this.isDragging = false;
                this.dragStartElement = null;
                this.dragSelectionActive = false;
            }
        });

        window.addEventListener('scroll', () => this.hideTextTooltip());
        window.addEventListener('resize', () => this.hideTextTooltip());
    },

    togglePatternPanel() {
        const panel = document.getElementById('patternPanel');
        const canvas = document.getElementById('canvas');
        if (!panel || !canvas) return;

        const collapsed = panel.classList.toggle('collapsed');
        canvas.classList.toggle('pattern-open', !collapsed);
    },

    openPatternPanel() {
        const panel = document.getElementById('patternPanel');
        const canvas = document.getElementById('canvas');
        if (!panel || !canvas) return;

        panel.classList.remove('collapsed');
        canvas.classList.add('pattern-open');
    },

    closePatternPanel() {
        const panel = document.getElementById('patternPanel');
        const canvas = document.getElementById('canvas');
        if (!panel || !canvas) return;

        panel.classList.add('collapsed');
        canvas.classList.remove('pattern-open');
    },

    renderLayerPalette() {
        const palette = document.getElementById('layerPalette');
        if (!palette) return;

        const definition = LAYER_DEFINITIONS[this.currentLayer];
        palette.innerHTML = '';

        if (!definition || !definition.categories || definition.categories.length === 0) {
            const placeholder = document.createElement('span');
            placeholder.className = 'palette-option';
            placeholder.textContent = 'No categories';
            palette.appendChild(placeholder);
            this.selectedStructureCategory = null;
            return;
        }

        if (!definition.categories.some(cat => cat.id === this.selectedStructureCategory)) {
            this.selectedStructureCategory = definition.categories[0].id;
        }

        definition.categories.forEach(cat => {
            const option = document.createElement('button');
            option.type = 'button';
            option.className = 'palette-option' + (cat.id === this.selectedStructureCategory ? ' active' : '');
            option.textContent = cat.label;
            option.title = definition.description;
            option.addEventListener('click', () => this.setStructureCategory(cat.id));
            palette.appendChild(option);
        });
    },

    setStructureCategory(categoryId) {
        this.selectedStructureCategory = categoryId;
        this.renderLayerPalette();
        const layerDef = LAYER_DEFINITIONS[this.currentLayer];
        const cat = layerDef?.categories?.find(c => c.id === categoryId);
        if (cat) {
            this.logAction({
                ref: `${this.currentSurahNumber || ''}:${this.currentAyahNumber || ''}`,
                details: `Selected structure type ${cat.label}`
            });
        }
    },

    setCurrentTarget(type, id, meta = {}, label = '') {
        this.currentTarget = { type, id, meta, label };
        const display = document.getElementById('hypTargetDisplay');
        if (display) {
            display.textContent = label || `${type}: ${id}`;
        }
    },

    setupMorphBuilder() {
        this.renderBuilderChips('morphChipRow', MORPH_BLOCKS, 'morphBuilder');
        const clearBtn = document.getElementById('morphClearBtn');
        if (clearBtn) {
            clearBtn.addEventListener('click', () => this.clearBuilder('morphBuilder'));
        }
        const searchBtn = document.getElementById('morphBuildSearch');
        if (searchBtn) {
            searchBtn.addEventListener('click', () => this.handleMorphSearch());
        }
    },

    setupSyntaxBuilder() {
        this.renderBuilderChips('syntaxChipRow', SYNTAX_BLOCKS, 'syntaxBuilder');
        const clearBtn = document.getElementById('syntaxClearBtn');
        if (clearBtn) {
            clearBtn.addEventListener('click', () => this.clearBuilder('syntaxBuilder'));
        }
        const searchBtn = document.getElementById('syntaxBuildSearch');
        if (searchBtn) {
            searchBtn.addEventListener('click', () => this.handleSyntaxSearch());
        }
    },

    renderBuilderChips(rowId, blocks, builderId) {
        const row = document.getElementById(rowId);
        if (!row) return;
        row.innerHTML = '';
        blocks.forEach(block => {
            const chip = document.createElement('span');
            chip.className = 'builder-chip';
            chip.textContent = block.label;
            chip.addEventListener('click', () => this.appendToBuilder(builderId, block.label, block.value));
            row.appendChild(chip);
        });

        const builder = document.getElementById(builderId);
        if (builder) {
            builder.addEventListener('click', (e) => {
                const token = e.target.closest('.builder-token');
                if (token) {
                    token.remove();
                }
            });
        }
    },

    appendToBuilder(builderId, label, value) {
        const builder = document.getElementById(builderId);
        if (!builder) return;
        const token = document.createElement('span');
        token.className = 'builder-token';
        token.textContent = label;
        token.dataset.value = value;
        builder.appendChild(token);
    },

    getBuilderTokens(builderId) {
        const builder = document.getElementById(builderId);
        if (!builder) return [];
        return Array.from(builder.querySelectorAll('.builder-token')).map(token => token.dataset.value || token.textContent.trim());
    },

    clearBuilder(builderId) {
        const builder = document.getElementById(builderId);
        if (builder) {
            builder.innerHTML = '';
        }
    },

    async loadRootOptions() {
        const letterRow = document.getElementById('rootLetterRow');
        if (!letterRow) return;
        letterRow.textContent = 'Loading roots...';
        try {
            const response = await fetch('/api/roots');
            this.rootOptions = await response.json();
            this.renderRootLetters();
        } catch (error) {
            console.error('Error loading roots:', error);
            letterRow.textContent = 'Failed to load roots.';
        }
    },

    renderRootLetters() {
        const row = document.getElementById('rootLetterRow');
        const chipContainer = document.getElementById('rootChipContainer');
        if (!row || !chipContainer) return;

        row.innerHTML = '';
        chipContainer.innerHTML = '<p class="hint">Select a letter to view available roots.</p>';

        const letters = Array.from(new Set(this.rootOptions.map(root => root.charAt(0)))).sort();
        letters.forEach(letter => {
            const chip = document.createElement('span');
            chip.className = 'letter-chip';
            chip.textContent = letter || '?';
            chip.addEventListener('click', () => this.showRootsForLetter(letter));
            row.appendChild(chip);
        });
    },

    showRootsForLetter(letter) {
        const container = document.getElementById('rootChipContainer');
        if (!container) return;

        const filtered = this.rootOptions.filter(root => root.startsWith(letter));
        if (!filtered.length) {
            container.innerHTML = `<p class="hint">No roots found for ${letter}.</p>`;
            return;
        }

        container.innerHTML = '';
        filtered.forEach(root => {
            const chip = document.createElement('span');
            chip.className = 'search-chip';
            chip.textContent = root;
            chip.addEventListener('click', () => this.performRootSearch(root));
            container.appendChild(chip);
        });
    },

    async performRootSearch(root) {
        if (!root) {
            this.renderSearchMessage('Select a root to explore.');
            return;
        }
        try {
            this.renderSearchMessage(`Searching for root ${root}...`);
            const response = await fetch(`/api/search/roots?root=${encodeURIComponent(root)}`);
            const data = await response.json();
            this.renderSearchResults(data.results, `No occurrences found for root ${root}.`);
        } catch (error) {
            console.error('Root search failed:', error);
            this.renderSearchMessage('Root search failed. Please try again.');
        }
    },

    async loadMorphPatterns() {
        try {
            const response = await fetch('/api/morph_patterns');
            this.morphPatterns = await response.json();
        } catch (error) {
            console.error('Error loading morphological patterns:', error);
        }
    },

    async loadSyntaxPatterns() {
        try {
            const response = await fetch('/api/syntax_patterns');
            this.syntaxPatterns = await response.json();
        } catch (error) {
            console.error('Error loading syntactic patterns:', error);
        }
    },

    setAppMode(mode) {
        this.appMode = 'read';
        this.setMode('select');
    },

    async loadSurahSummaries() {
        try {
            const response = await fetch('/api/surahs');
            this.surahSummaries = await response.json();
            this.renderSurahList();
            if (this.surahSummaries.length) {
                this.selectSurah(this.surahSummaries[0].number);
            }
        } catch (error) {
            console.error('Error loading surah summaries:', error);
        }
    },

    renderSurahList() {
        const tree = document.getElementById('surahTree');
        if (!tree) return;
        tree.innerHTML = '';

        if (!this.surahSummaries.length) {
            tree.innerHTML = '<p class="hint">Loading surahs…</p>';
            return;
        }

        this.surahSummaries.forEach(summary => {
            const node = document.createElement('div');
            node.className = 'surah-node';

            const header = document.createElement('div');
            header.className = 'surah-header' + (summary.number === this.currentSurahNumber ? ' active' : '');
            const isExpanded = this.expandedSurahs.has(summary.number);

            header.innerHTML = `
                <span class="toggle">${isExpanded ? '▾' : '▸'}</span>
                <span>${summary.number}. ${summary.name} (${summary.ayah_count})</span>
            `;

            header.addEventListener('click', async () => {
                await this.selectSurah(summary.number, { keepScroll: true });
                if (isExpanded) {
                    this.expandedSurahs.delete(summary.number);
                } else {
                    this.expandedSurahs.add(summary.number);
                }
                this.renderSurahList();
            });

            node.appendChild(header);

            if (isExpanded && summary.number === this.currentSurahNumber && this.currentSurahData) {
                const ayahList = document.createElement('div');
                ayahList.className = 'ayah-list-inline';
                this.currentSurahData.verses.forEach(verse => {
                    const chip = document.createElement('span');
                    chip.className = 'ayah-chip' + (verse.ayah === this.currentAyahNumber ? ' active' : '');
                    chip.textContent = verse.ayah;
                    chip.addEventListener('click', () => {
                        this.navigateToVerse(verse.surah.number, verse.ayah);
                    });
                    ayahList.appendChild(chip);
                });
                node.appendChild(ayahList);
            }

            tree.appendChild(node);
        });
    },

    async selectSurah(number, options = {}) {
        try {
            const data = await this.getSurahData(number);
            this.currentSurahNumber = number;
            this.currentSurahData = data;
            this.currentVerse = data.verses[0] || null;
            this.currentAyahNumber = data.verses[0]?.ayah || null;
            await this.loadPronounData();
            await this.loadHypotheses();
            this.renderSurah();
            this.renderSurahList();
            this.renderAyahList();
            this.logNavigation(this.currentSurahNumber, this.currentAyahNumber);
            if (!options.keepScroll) {
                const canvasEl = document.getElementById('canvas');
                if (canvasEl) {
                    canvasEl.scrollTop = 0;
                }
            }
        } catch (error) {
            console.error('Error selecting surah:', error);
        }
    },

    async getSurahData(number) {
        if (this.surahCache[number]) {
            return this.surahCache[number];
        }
        const response = await fetch(`/api/surah/${number}`);
        const data = await response.json();
        if (data.error) {
            throw new Error(data.error);
        }
        this.surahCache[number] = data;
        return data;
    },

    renderAyahList() {
        const list = document.getElementById('ayahList');
        if (!list) return;
        list.innerHTML = '';

        if (!this.currentSurahData) {
            list.innerHTML = '<p class="hint">Select a surah to view ayahs</p>';
            return;
        }

        this.currentSurahData.verses.forEach(verse => {
            const button = document.createElement('button');
            button.type = 'button';
            button.className = 'ayah-item' + (verse.ayah === this.currentAyahNumber ? ' active' : '');
            button.textContent = `Ayah ${verse.ayah}`;
            button.addEventListener('click', () => {
                this.currentAyahNumber = verse.ayah;
                this.currentVerse = verse;
                this.loadPronounData();
                this.renderAyahList();
                this.scrollToAyah(verse.ayah);
            });
            list.appendChild(button);
        });
    },

    renderSearchMessage(message) {
        const container = document.getElementById('searchResults');
        if (!container) return;
        container.innerHTML = `<p class="hint">${this.escapeHtml(message)}</p>`;
        this.openPatternPanel();
    },

    renderSearchResults(results, emptyMessage = 'No matches found.') {
        const container = document.getElementById('quranText');
        if (!container) return;
        this.currentSearchResults = results || [];
        container.innerHTML = '';

        if (!results || results.length === 0) {
            container.innerHTML = `<p class="hint">${this.escapeHtml(emptyMessage)}</p>`;
            return;
        }

        const resultWrapper = document.createElement('div');
        resultWrapper.className = 'search-results-main';

        this.currentSearchResults.slice(0, 150).forEach(result => {
            const verse = result.verse;
            if (!verse) return;
            const item = document.createElement('div');
            item.className = 'search-result-item';
            const text = this.highlightMatch(verse.text, (result.matchTerm || ''), result);
            item.innerHTML = `
                <div class="search-result-ref">${this.escapeHtml(verse.surah.name)} ${verse.surah.number}:${verse.ayah}</div>
                <div class="search-result-text">${text}</div>
                ${result.match ? `<div class="search-result-match">${this.escapeHtml(result.match)}</div>` : ''}
            `;
            item.addEventListener('click', () => {
                this.currentSearchResults = null;
                this.navigateToVerse(verse.surah.number, verse.ayah);
            });
            resultWrapper.appendChild(item);
        });

        const backBtn = document.createElement('button');
        backBtn.type = 'button';
        backBtn.className = 'btn';
        backBtn.textContent = 'Return to text';
        backBtn.addEventListener('click', () => {
            this.currentSearchResults = null;
            this.renderSurah();
        });

        container.appendChild(backBtn);
        container.appendChild(resultWrapper);
    },

    setLayer(layer, rerender = true) {
        const normalized = ['letter', 'morphological', 'word', 'sentence'].includes(layer) ? layer : this.currentLayer;
        this.currentLayer = normalized;
        this.setHypothesisTargetForLayer(normalized);
        if (rerender) {
            this.renderLayerPalette();
            this.renderSurah();
        }
    },

    setHypothesisTargetForLayer(layer) {
        const display = document.getElementById('hypTargetDisplay');
        if (!display) return;
        let mapped = 'other';
        if (layer === 'sentence') mapped = 'clause';
        else if (layer === 'word') mapped = 'word';
        else if (layer === 'morphological') mapped = 'morpheme';
        else if (layer === 'letter') mapped = 'letter';
        display.textContent = this.currentTarget ? `${mapped.toUpperCase()} • ${this.currentTarget.label || ''}` : `${mapped.toUpperCase()} (select element)`;
    },

    navigateLayerUp() {
        const order = ['letter', 'morphological', 'word', 'sentence'];
        const idx = order.indexOf(this.currentLayer);
        const nextIdx = idx < order.length - 1 ? idx + 1 : order.length - 1;
        const target = order[nextIdx];
        if (target !== this.currentLayer) {
            this.setLayer(target);
            this.logAction({ ref: `${this.currentSurahNumber || ''}:${this.currentAyahNumber || ''}`, details: `Switched to ${target} layer` });
        }
    },

    // ===== Pattern Search =====
    breakPatternWord() {
        const input = document.getElementById('patternInput');
        const word = (input?.value || '').trim();
        this.patternSegments = this.parseArabicWord(word);
        this.renderPatternSegments();
    },

    parseArabicWord(word) {
        const segments = [];
        const isDiacritic = (ch) => /[\u064B-\u0652\u0670]/.test(ch);
        for (let i = 0; i < word.length; i++) {
            const ch = word[i];
            if (isDiacritic(ch)) {
                if (segments.length) {
                    segments[segments.length - 1].diacritics.push(ch);
                }
            } else if (ch >= '\u0620' && ch <= '\u064a') {
                segments.push({ letter: ch, diacritics: [], any_letter: false, any_diacritics: false });
            }
        }
        return segments;
    },

    renderPatternSegments() {
        const container = document.getElementById('patternSegments');
        if (!container) return;
        container.innerHTML = '';
        if (!this.patternSegments || this.patternSegments.length === 0) {
            container.innerHTML = '<p class="hint">Break a word to edit per-letter pattern.</p>';
            return;
        }

        this.patternSegments.forEach((seg, idx) => {
            const wrapper = document.createElement('div');
            wrapper.className = 'pattern-segment' + (seg.any_letter ? ' placeholder' : '');
            wrapper.title = 'Click to toggle letter any/specific; shift+click for diacritics any/specific';
            wrapper.innerHTML = `
                <span class="pattern-letter">${seg.any_letter ? '●' : this.escapeHtml(seg.letter)}</span>
                <span class="pattern-diac">${seg.any_diacritics ? '◦' : this.escapeHtml(seg.diacritics.join('') || '◦')}</span>
            `;
            wrapper.addEventListener('click', () => {
                seg.any_letter = !seg.any_letter;
                this.renderPatternSegments();
            });
            wrapper.addEventListener('contextmenu', (e) => {
                e.preventDefault();
                seg.any_diacritics = !seg.any_diacritics;
                this.renderPatternSegments();
            });
            container.appendChild(wrapper);
        });
    },

    async submitPatternSearch() {
        const allowPrefix = document.getElementById('patternAllowPrefix')?.checked || false;
        const allowSuffix = document.getElementById('patternAllowSuffix')?.checked || false;
        const payload = {
            segments: (this.patternSegments || []).map(seg => ({
                letter: seg.letter,
                diacritics: seg.any_diacritics ? null : seg.diacritics,
                any_letter: seg.any_letter,
                any_diacritics: seg.any_diacritics
            })),
            allow_prefix: allowPrefix,
            allow_suffix: allowSuffix
        };
        try {
            const resp = await fetch('/api/search/pattern_word', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await resp.json();
            this.renderSearchResults(data.results, 'No matches for this pattern.');
        } catch (error) {
            console.error('Pattern search failed', error);
        }
    },
    logAction(action) {
        if (!action) return;
        this.actionHistory.unshift(action);
        this.actionHistory = this.actionHistory.slice(0, 15);
        const historyEl = document.getElementById('actionHistory');
        if (!historyEl) return;

        const items = this.actionHistory.map(entry => {
            const ref = entry.ref ? `<span class="ref">${this.escapeHtml(entry.ref)}</span>` : '';
            const details = entry.details ? `<span class="meta">${this.escapeHtml(entry.details)}</span>` : '';
            return `<li>${ref}${details ? ' · ' + details : ''}</li>`;
        }).join('');
        historyEl.innerHTML = `<ul>${items}</ul>`;
    },

    logNavigation(surah, ayah) {
        if (!surah || !ayah) return;
        this.navJourney.unshift({ surah, ayah, ts: Date.now() });
        this.navJourney = this.navJourney.slice(0, 30);
        this.renderNavMap();
    },

    renderNavMap() {
        const map = document.getElementById('navMap');
        if (!map) return;
        if (!this.navJourney.length) {
            map.innerHTML = '<p class="hint">No navigation history yet.</p>';
            return;
        }
        const items = this.navJourney.map(node => {
            return `
                <div class="branch">
                    <div class="branch-line"></div>
                    <div class="branch-node">
                        <span class="node-item">S${this.escapeHtml(node.surah)} <span class="ayah-label">· A${this.escapeHtml(node.ayah)}</span></span>
                    </div>
                </div>
            `;
        }).join('');
        map.innerHTML = items;
    },

    async loadHypotheses() {
        if (!this.currentSurahNumber || !this.currentAyahNumber) {
            this.currentHypotheses = [];
            this.renderHypotheses();
            return;
        }
        try {
            const resp = await fetch(`/api/hypotheses/${this.currentSurahNumber}:${this.currentAyahNumber}`);
            this.currentHypotheses = await resp.json();
            this.renderHypotheses();
        } catch (error) {
            console.error('Error loading hypotheses', error);
            this.currentHypotheses = [];
            this.renderHypotheses();
        }
    },

    renderHypotheses() {
        const list = document.getElementById('hypothesisList');
        if (!list) return;
        if (!this.currentHypotheses || this.currentHypotheses.length === 0) {
            list.innerHTML = '<p class="hint">No hypotheses yet.</p>';
            return;
        }
        list.innerHTML = '';
        this.currentHypotheses.forEach(h => {
            const card = document.createElement('div');
            card.className = 'hyp-card';
            card.innerHTML = `
                <div><strong>${this.escapeHtml(h.hypothesis || '')}</strong></div>
                <div class="meta">${this.escapeHtml(h.target_type || '')} · ${this.escapeHtml(h.status || '')}</div>
            `;
            list.appendChild(card);
        });
    },

    async submitHypothesis(event) {
        event.preventDefault();
        if (!this.currentSurahNumber || !this.currentAyahNumber) return;
        if (!this.currentTarget || !this.currentTarget.id) {
            alert('Select a target (sentence/word/morpheme/letter) first.');
            return;
        }
        const payload = {
            target_type: this.currentTarget.type,
            target_id: this.currentTarget.id,
            target_meta: this.currentTarget.meta || {},
            hypothesis: document.getElementById('hypText').value,
            status: 'hypothesis'
        };
        try {
            await fetch(`/api/hypotheses/${this.currentSurahNumber}:${this.currentAyahNumber}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            document.getElementById('hypothesisForm').reset();
            await this.loadHypotheses();
            this.logAction({ ref: `${this.currentSurahNumber}:${this.currentAyahNumber}`, details: 'Saved hypothesis' });
        } catch (error) {
            console.error('Error saving hypothesis', error);
        }
    },

    async handleLibrarySearch() {
        const input = document.getElementById('librarySearchInput');
        if (!input || !input.value.trim()) {
            this.renderSearchMessage('Enter a query to search the library.');
            return;
        }

        const query = input.value.trim();
        try {
            this.renderSearchMessage(`Searching library for “${this.escapeHtml(query)}”…`);
            const response = await fetch(`/api/library_search?q=${encodeURIComponent(query)}`);
            const data = await response.json();
            this.renderLibraryResults(data.results || [], query);
        } catch (error) {
            console.error('Library search failed:', error);
            this.renderSearchMessage('Library search failed. Please try again.');
        }
    },

    renderLibraryResults(results, query) {
        const container = document.getElementById('searchResults');
        if (!container) return;

        if (!results || results.length === 0) {
            container.innerHTML = `<p class=\"hint\">No matches in data/ for “${this.escapeHtml(query)}”.</p>`;
            this.openPatternPanel();
            return;
        }
        this.renderSearchResults(results.map(r => ({
            verse: { surah: { name: 'Data' , number: ''}, ayah: r.line, text: `${r.path}: ${r.snippet}` },
            match: 'Library hit',
            matchTerm: query
        })), 'No matches in data');
    },

    async loadPronounData() {
        if (!this.currentSurahNumber || !this.currentAyahNumber) {
            return;
        }
        try {
            const response = await fetch(`/api/pronouns/${this.currentSurahNumber}:${this.currentAyahNumber}`);
            const data = await response.json();
            this.pronounData = data;
            this.renderPronounPanel(data);
        } catch (error) {
            console.error('Error loading pronoun data:', error);
        }
    },

    renderPronounPanel(data) {
        const list = document.getElementById('pronounList');
        const summary = document.getElementById('pronounSummary');
        const select = document.getElementById('pronounTarget');
        if (!list || !summary || !select) return;

        list.innerHTML = '';
        select.innerHTML = '';

        if (!data || data.error) {
            summary.textContent = data?.error || 'Unable to load pronoun data';
            select.innerHTML = '<option value="">No pronouns detected</option>';
            select.disabled = true;
            return;
        }

        const pronouns = data.pronouns || [];
        const references = data.references || [];
        const stats = data.stats || { supporting_evidence: 0, counter_evidence: 0 };

        if (pronouns.length === 0) {
            summary.textContent = 'No pronouns detected in this ayah.';
            select.innerHTML = '<option value="">No pronouns detected</option>';
            select.disabled = true;
        } else {
            pronouns.forEach(pr => {
                const opt = document.createElement('option');
                opt.value = pr.pronoun_id;
                opt.textContent = this.buildPronounLabel(pr);
                select.appendChild(opt);
            });
            if (pronouns[0]) {
                select.value = pronouns[0].pronoun_id;
            }
            select.disabled = false;
            summary.textContent = `Pronouns: ${pronouns.length} • Annotated: ${references.length} • Evidence (+/-): ${stats.supporting_evidence}/${stats.counter_evidence}`;
        }

        if (references.length === 0) {
            list.innerHTML = '<p class="hint">Add a referent hypothesis to start tracking evidence.</p>';
            return;
        }

        references.forEach(ref => {
            const card = document.createElement('div');
            card.className = 'pronoun-card';

            const header = document.createElement('div');
            header.className = 'pronoun-card-header';
            header.innerHTML = `
                <div class="pronoun-chip">${this.escapeHtml(ref.pronoun_form || ref.pronoun_id || '')}</div>
                <div class="pronoun-ref">${this.escapeHtml(ref.referent || '')}</div>
            `;

            const statusRow = document.createElement('div');
            statusRow.className = 'pronoun-card-row';

            const statusLabel = document.createElement('span');
            statusLabel.className = `status-badge status-${ref.status || 'hypothesis'}`;
            statusLabel.textContent = ref.status || 'hypothesis';

            const statusSelect = document.createElement('select');
            ['hypothesis', 'plausible', 'verified', 'challenged'].forEach(status => {
                const opt = document.createElement('option');
                opt.value = status;
                opt.textContent = status.charAt(0).toUpperCase() + status.slice(1);
                if ((ref.status || 'hypothesis') === status) {
                    opt.selected = true;
                }
                statusSelect.appendChild(opt);
            });
            statusSelect.addEventListener('change', (e) => this.updatePronounStatus(ref.id, e.target.value));

            statusRow.appendChild(statusLabel);
            statusRow.appendChild(statusSelect);

            const evidenceRow = document.createElement('div');
            evidenceRow.className = 'pronoun-card-row';
            evidenceRow.innerHTML = `
                <span class="evidence-count positive">+${ref.evidence_summary?.supporting || 0}</span>
                <span class="evidence-count negative">-${ref.evidence_summary?.counter || 0}</span>
                <span class="evidence-count neutral">/${ref.evidence_summary?.total || 0}</span>
            `;

            const actions = document.createElement('div');
            actions.className = 'pronoun-card-actions';

            const addSupport = document.createElement('button');
            addSupport.type = 'button';
            addSupport.className = 'btn btn-ghost';
            addSupport.textContent = 'Add support';
            addSupport.addEventListener('click', () => this.promptEvidence(ref.id, 'supporting'));

            const addCounter = document.createElement('button');
            addCounter.type = 'button';
            addCounter.className = 'btn btn-ghost';
            addCounter.textContent = 'Add counter';
            addCounter.addEventListener('click', () => this.promptEvidence(ref.id, 'counter'));

            actions.appendChild(addSupport);
            actions.appendChild(addCounter);

            card.appendChild(header);
            if (ref.note) {
                const note = document.createElement('p');
                note.className = 'pronoun-note';
                note.textContent = ref.note;
                card.appendChild(note);
            }
            card.appendChild(statusRow);
            card.appendChild(evidenceRow);
            card.appendChild(actions);

            list.appendChild(card);
        });
    },

    buildPronounLabel(pronoun) {
        const base = pronoun.form || pronoun.token_form || pronoun.pronoun_id;
        const features = pronoun.features ? ` (${pronoun.features})` : '';
        return `${base}${features}`.trim();
    },

    async submitPronounReference(event) {
        event.preventDefault();
        if (!this.currentSurahNumber || !this.currentAyahNumber) {
            alert('Select an ayah first');
            return;
        }

        const payload = {
            pronoun_id: document.getElementById('pronounTarget').value,
            referent: document.getElementById('pronounReferent').value,
            referent_type: document.getElementById('pronounType').value,
            status: document.getElementById('pronounStatus').value,
            note: document.getElementById('pronounNote').value,
            evidence_note: document.getElementById('pronounEvidenceNote').value,
            evidence_type: document.getElementById('pronounEvidenceType').value,
            evidence_verse: document.getElementById('pronounEvidenceVerse').value
        };

        try {
            await fetch(`/api/pronouns/${this.currentSurahNumber}:${this.currentAyahNumber}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(payload)
            });
            document.getElementById('pronounForm').reset();
            this.loadPronounData();
        } catch (error) {
            console.error('Error saving pronoun referent:', error);
            alert('Unable to save pronoun referent');
        }
    },

    async promptEvidence(refId, type) {
        const note = prompt(`Add a ${type} evidence note`);
        if (!note) return;
        await this.addPronounEvidence(refId, type, note);
    },

    async addPronounEvidence(refId, type, note) {
        if (!this.currentSurahNumber || !this.currentAyahNumber) return;
        try {
            await fetch(`/api/pronouns/${this.currentSurahNumber}:${this.currentAyahNumber}/${refId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    evidence_entry: {
                        type,
                        note
                    }
                })
            });
            this.loadPronounData();
        } catch (error) {
            console.error('Error adding pronoun evidence:', error);
        }
    },

    async updatePronounStatus(refId, status) {
        if (!this.currentSurahNumber || !this.currentAyahNumber) return;
        try {
            await fetch(`/api/pronouns/${this.currentSurahNumber}:${this.currentAyahNumber}/${refId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ status })
            });
            this.loadPronounData();
        } catch (error) {
            console.error('Error updating pronoun status:', error);
        }
    },

    async handleMorphSearch() {
        const tokens = this.getBuilderTokens('morphBuilder');
        if (!tokens.length) {
            this.renderSearchMessage('Add morphological building blocks to search.');
            return;
        }
        const query = tokens.join(' ');
        try {
            this.renderSearchMessage('Searching morphological pattern...');
            const response = await fetch(`/api/search/morphology?q=${encodeURIComponent(query)}`);
            const data = await response.json();
            this.renderSearchResults(data.results, 'No matches for the selected morphological pattern.');
        } catch (error) {
            console.error('Morphology search failed:', error);
            this.renderSearchMessage('Morphology search failed. Please try again.');
        }
    },

    async handleSyntaxSearch() {
        const tokens = this.getBuilderTokens('syntaxBuilder');
        if (!tokens.length) {
            this.renderSearchMessage('Add syntactic building blocks to search.');
            return;
        }
        const query = tokens.join(' ');
        try {
            this.renderSearchMessage('Searching syntactic pattern...');
            const response = await fetch(`/api/search/syntax?q=${encodeURIComponent(query)}`);
            const data = await response.json();
            this.renderSearchResults(data.results, 'No matches for the selected syntactic pattern.');
        } catch (error) {
            console.error('Syntax search failed:', error);
            this.renderSearchMessage('Syntax search failed. Please try again.');
        }
    },

    buildVerseId(surah, ayah) {
        return `verse-${surah}-${ayah}`;
    },

    scrollToAyah(ayahNumber, smooth = true) {
        if (!this.currentSurahNumber || !ayahNumber) return;
        this.currentAyahNumber = ayahNumber;
        const verseId = this.buildVerseId(this.currentSurahNumber, ayahNumber);
        const el = document.getElementById(verseId);
        document.querySelectorAll('.ayah.current-ayah').forEach(node => node.classList.remove('current-ayah'));
        if (el) {
            el.classList.add('current-ayah');
            el.scrollIntoView({ behavior: smooth ? 'smooth' : 'auto', block: 'start' });
        }
    },

    async navigateToVerse(surahNumber, ayahNumber) {
        await this.selectSurah(surahNumber);
        this.currentAyahNumber = ayahNumber;
        if (this.currentSurahData) {
            this.currentVerse = this.currentSurahData.verses.find(v => v.ayah === ayahNumber) || this.currentVerse;
        }
        this.loadPronounData();
        await this.loadHypotheses();
        this.renderAyahList();
        this.logNavigation(surahNumber, ayahNumber);
        this.scrollToAyah(ayahNumber);
    },

    renderSurah() {
        if (!this.currentSurahData) return;

        const verseRef = document.getElementById('verseReference');
        if (verseRef) {
            const surahInfo = this.currentSurahData.surah;
            verseRef.textContent = `Surah ${surahInfo.name} (${surahInfo.number}) • ${this.currentSurahData.verses.length} ayahs`;
        }

        const container = document.getElementById('quranText');
        if (!container) return;
        container.innerHTML = '';
        this.hideTextTooltip();

        const heading = document.createElement('div');
        heading.className = 'surah-heading';
        heading.textContent = `Surah ${this.currentSurahData.surah.name}`;
        container.appendChild(heading);

        const surahText = document.createElement('div');
        surahText.className = 'surah-text';

        this.currentSurahData.verses.forEach(verse => {
            const ayahSpan = document.createElement('span');
            ayahSpan.className = 'ayah';
            ayahSpan.id = this.buildVerseId(verse.surah.number, verse.ayah);
            this.applyVerseMetadata(ayahSpan, verse);

            const verseLayer = document.createElement('span');
            verseLayer.className = 'ayah-layer';

            if (this.currentLayer === 'letter') {
                this.renderLetterLayer(verseLayer, verse);
            } else if (this.currentLayer === 'morphological' && verse.tokens) {
                this.renderMorphologicalLayer(verseLayer, verse);
            } else if (this.currentLayer === 'sentence') {
                this.renderSentenceLayer(verseLayer, verse);
            } else {
                this.renderTextLayer(verseLayer, verse);
            }

            ayahSpan.appendChild(verseLayer);

            const marker = document.createElement('span');
            marker.className = 'ayah-marker';
            marker.textContent = `﴿${verse.ayah}﴾`;
            ayahSpan.appendChild(marker);

            surahText.appendChild(ayahSpan);
        });

        container.appendChild(surahText);

        if (this.currentAyahNumber) {
            requestAnimationFrame(() => this.scrollToAyah(this.currentAyahNumber, false));
        } else {
            const canvasEl = document.getElementById('canvas');
            if (canvasEl) {
                canvasEl.scrollTop = 0;
            }
        }
    },

    applyVerseMetadata(element, verse) {
        if (!verse || !element) return;
        element.dataset.surah = verse.surah.number;
        element.dataset.ayah = verse.ayah;
        element.dataset.surahName = verse.surah.name;
    },

    assignStructure(element) {
        const definition = LAYER_DEFINITIONS[this.currentLayer];
        if (!definition || !definition.categories) return;
        const category = definition.categories.find(cat => cat.id === this.selectedStructureCategory);
        if (!category) return;

        // Remove previous structure tag color classes
        Object.values(STRUCTURE_COLOR_CLASSES).forEach(cls => element.classList.remove(cls));

        element.dataset.structureCategory = category.id;
        element.dataset.structureCategoryLabel = category.label;
        element.classList.add('structure-assigned');
        const colorClass = STRUCTURE_COLOR_CLASSES[category.id];
        if (colorClass) {
            element.classList.add(colorClass);
        }

        const ref = `${element.dataset.surah || this.currentSurahNumber}:${element.dataset.ayah || this.currentAyahNumber}`;
        this.logAction({
            ref,
            details: `Tagged as ${category.label}`
        });
    },

    getVerseFromElement(element) {
        const surahNumber = parseInt(element.dataset.surah, 10);
        const ayahNumber = parseInt(element.dataset.ayah, 10);
        if (!surahNumber || !ayahNumber) return null;
        const surahData = this.surahCache[surahNumber] ||
            (this.currentSurahNumber === surahNumber ? this.currentSurahData : null);
        if (!surahData) return null;
        return surahData.verses.find(v => v.surah.number === surahNumber && v.ayah === ayahNumber) || null;
    },

    showElementTooltip(element) {
        if (!this.tooltipEl || this.isDragging) return;
        const content = this.buildTooltipContent(element);
        if (!content) {
            this.hideTextTooltip();
            return;
        }

        this.tooltipEl.innerHTML = content;
        this.tooltipEl.classList.remove('hidden');
        this.positionTooltip(element);
    },

    positionTooltip(element) {
        if (!this.tooltipEl || this.tooltipEl.classList.contains('hidden')) return;
        const rect = element.getBoundingClientRect();
        const tooltipRect = this.tooltipEl.getBoundingClientRect();

        let top = rect.top - tooltipRect.height - 12;
        if (top < 70) {
            top = rect.bottom + 12;
        }

        let left = rect.left + (rect.width / 2) - (tooltipRect.width / 2);
        left = Math.max(12, Math.min(left, window.innerWidth - tooltipRect.width - 12));

        this.tooltipEl.style.top = `${top}px`;
        this.tooltipEl.style.left = `${left}px`;
    },

    hideTextTooltip() {
        if (!this.tooltipEl) return;
        this.tooltipEl.classList.add('hidden');
    },

    buildTooltipContent(element) {
        const text = element.dataset.displayText ||
            element.dataset.originalText ||
            element.textContent.trim();
        const type = element.dataset.type ||
            element.dataset.layer ||
            element.dataset.pos ||
            (element.classList.contains('letter') ? 'Letter' : 'Word');
        const pos = element.dataset.pos;
        const root = element.dataset.root;
        const lemma = element.dataset.lemma;
        const translation = element.dataset.translation;
        const structureLabel = element.dataset.structureCategoryLabel;

        const surahName = element.dataset.surahName ||
            this.currentSurahData?.surah?.name ||
            (this.currentVerse ? this.currentVerse.surah.name : '');
        const surahNumber = element.dataset.surah ||
            (this.currentVerse ? this.currentVerse.surah.number : '') ||
            this.currentSurahNumber ||
            '';
        const ayahNumber = element.dataset.ayah ||
            (this.currentVerse ? this.currentVerse.ayah : '') ||
            '';

        const chips = [];
        if (type) chips.push(this.escapeHtml(type));
        if (pos && pos !== type) chips.push(`POS ${this.escapeHtml(pos)}`);
        if (root && root !== '—') chips.push(`Root ${this.escapeHtml(root)}`);
        if (lemma && lemma !== '—') chips.push(`Lemma ${this.escapeHtml(lemma)}`);

        return `
            <div class="info-verse">${this.escapeHtml(surahName)} (${this.escapeHtml(surahNumber)}) — Ayah ${this.escapeHtml(ayahNumber)}</div>
            <div class="info-text">${this.escapeHtml(text)}</div>
            ${chips.length ? `<div class="info-meta">${chips.map(c => `<span>${c}</span>`).join('')}</div>` : ''}
            ${structureLabel ? `<div class="info-structure">${this.escapeHtml(structureLabel)}</div>` : ''}
            ${translation ? `<div class="info-translation">${this.escapeHtml(translation)}</div>` : ''}
        `;
    },

    escapeHtml(value) {
        if (value === undefined || value === null) return '';
        return value
            .toString()
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    },

    setMode(mode) {
        if (mode !== 'annotate') {
            mode = 'select';
        }
        if (mode === 'annotate' && this.appMode !== 'write') {
            mode = 'select';
        }
        this.mode = mode;

        // Update UI
        document.querySelectorAll('.tool-btn').forEach(btn => btn.classList.remove('active'));
        const canvas = document.getElementById('canvas');
        canvas.classList.remove('connect-mode');
        canvas.classList.toggle('annotate-mode', mode === 'annotate');

        const annotateBtn = document.getElementById('annotateMode');
        if (annotateBtn && mode === 'annotate') {
            annotateBtn.classList.add('active');
        }

        this.clearSelection();
    },

    // ===== Surah Loading =====

    renderTextLayer(container, verse) {
        // Simple word-by-word rendering
        const words = verse.text.split(' ');

        words.forEach((word, index) => {
            const wordEl = document.createElement('span');
            wordEl.className = 'word selectable';
            wordEl.textContent = word;
            wordEl.dataset.wordId = index + 1;
            wordEl.dataset.elementIndex = index;
            wordEl.dataset.displayText = word;
            wordEl.dataset.layer = 'Word';
            this.applyVerseMetadata(wordEl, verse);

            // Add click handlers
            wordEl.addEventListener('click', (e) => this.handleWordClick(e, wordEl));
            wordEl.addEventListener('contextmenu', (e) => this.handleWordClick(e, wordEl));
            wordEl.addEventListener('mousedown', (e) => this.handleElementMouseDown(e, wordEl));
            wordEl.addEventListener('mouseenter', (e) => {
                this.handleElementMouseEnter(e, wordEl);
                this.showElementTooltip(wordEl);
            });
            wordEl.addEventListener('mousemove', () => this.positionTooltip(wordEl));
            wordEl.addEventListener('mouseleave', () => this.hideTextTooltip());
            wordEl.addEventListener('mouseup', (e) => this.handleElementMouseUp(e, wordEl));

            container.appendChild(wordEl);
        });
    },

    renderMorphologicalLayer(container, verse) {
        // Render with selectable morphemes (prefix/stem/suffix)
        let elementIndex = 0;
        verse.tokens.forEach(token => {
            const wordEl = document.createElement('span');
            wordEl.className = 'word';
            wordEl.dataset.tokenId = token.id;
            this.applyVerseMetadata(wordEl, verse);

            // Render each segment as selectable element
            if (token.segments && token.segments.length > 0) {
                const segments = token.segments;
                const totalLength = token.form.length;

                segments.forEach((seg, idx) => {
                    const morpheme = document.createElement('span');
                    morpheme.className = 'morpheme selectable';
                    morpheme.dataset.segmentId = seg.id;
                    morpheme.dataset.type = seg.type;
                    morpheme.dataset.root = seg.root || '';
                    morpheme.dataset.pos = seg.pos;
                    morpheme.dataset.lemma = seg.lemma || '';
                    morpheme.dataset.features = seg.features || '';
                    morpheme.dataset.elementIndex = elementIndex++;

                    // Estimate which part of the word this morpheme represents
                    const startRatio = idx / segments.length;
                    const endRatio = (idx + 1) / segments.length;
                    const start = Math.floor(totalLength * startRatio);
                    const end = Math.floor(totalLength * endRatio);

                    const snippet = token.form.substring(start, end) || token.form;
                    morpheme.textContent = snippet;
                    morpheme.dataset.displayText = snippet;
                    morpheme.dataset.layer = 'Morpheme';
                    this.applyVerseMetadata(morpheme, verse);

                    // Add inline annotation badge for morpheme type
                    if (seg.type) {
                        const badge = document.createElement('span');
                        badge.className = 'morpheme-badge';
                        badge.textContent = seg.type.charAt(0); // P, S, or first letter of type
                        badge.title = `${seg.type} - ${seg.pos}`;
                        morpheme.appendChild(badge);
                    }

                    // Add handlers
                    morpheme.addEventListener('click', (e) => {
                        e.stopPropagation();
                        this.handleMorphemeClick(e, morpheme);
                    });
                    morpheme.addEventListener('contextmenu', (e) => {
                        e.stopPropagation();
                        this.handleMorphemeClick(e, morpheme);
                    });
                    morpheme.addEventListener('mousedown', (e) => {
                        e.stopPropagation();
                        this.handleElementMouseDown(e, morpheme);
                    });
                    morpheme.addEventListener('mouseenter', (e) => {
                        e.stopPropagation();
                        this.handleElementMouseEnter(e, morpheme);
                        this.showElementTooltip(morpheme);
                    });
                    morpheme.addEventListener('mousemove', () => this.positionTooltip(morpheme));
                    morpheme.addEventListener('mouseleave', () => this.hideTextTooltip());
                    morpheme.addEventListener('mouseup', (e) => {
                        e.stopPropagation();
                        this.handleElementMouseUp(e, morpheme);
                    });

                    wordEl.appendChild(morpheme);
                });
            } else {
                // No morphological data, treat as single word
                const wordSpan = document.createElement('span');
                wordSpan.className = 'morpheme selectable';
                wordSpan.textContent = token.form;
                wordSpan.dataset.tokenId = token.id;
                wordSpan.dataset.elementIndex = elementIndex++;
                wordSpan.dataset.displayText = token.form;
                wordSpan.dataset.layer = 'Word';
                this.applyVerseMetadata(wordSpan, verse);

                wordSpan.addEventListener('click', (e) => {
                    e.stopPropagation();
                    this.handleMorphemeClick(e, wordSpan);
                });
                wordSpan.addEventListener('contextmenu', (e) => {
                    e.stopPropagation();
                    this.handleMorphemeClick(e, wordSpan);
                });
                wordSpan.addEventListener('mousedown', (e) => {
                    e.stopPropagation();
                    this.handleElementMouseDown(e, wordSpan);
                });
                wordSpan.addEventListener('mouseenter', (e) => {
                    e.stopPropagation();
                    this.handleElementMouseEnter(e, wordSpan);
                    this.showElementTooltip(wordSpan);
                });
                wordSpan.addEventListener('mousemove', () => this.positionTooltip(wordSpan));
                wordSpan.addEventListener('mouseleave', () => this.hideTextTooltip());
                wordSpan.addEventListener('mouseup', (e) => {
                    e.stopPropagation();
                    this.handleElementMouseUp(e, wordSpan);
                });

                wordEl.appendChild(wordSpan);
            }

            // Add word-level handlers
            wordEl.addEventListener('contextmenu', (e) => this.handleWordClick(e, wordEl));

            container.appendChild(wordEl);
        });
    },

    renderLetterLayer(container, verse) {
        // Render with individual letter selection
        const text = verse.text;
        let elementIndex = 0;

        for (let i = 0; i < text.length; i++) {
            const char = text[i];

            if (char === ' ') {
                container.appendChild(document.createTextNode(' '));
                continue;
            }

            const letterEl = document.createElement('span');
            letterEl.className = 'letter selectable';
            letterEl.textContent = char;
            letterEl.dataset.position = i;
            letterEl.dataset.elementIndex = elementIndex++;
            letterEl.dataset.displayText = char;
            letterEl.dataset.layer = 'Letter';
            letterEl.dataset.type = 'Letter';
            this.applyVerseMetadata(letterEl, verse);

            letterEl.addEventListener('click', (e) => {
                e.stopPropagation();
                this.handleLetterClick(e, letterEl);
            });
            letterEl.addEventListener('mousedown', (e) => {
                e.stopPropagation();
                this.handleElementMouseDown(e, letterEl);
            });
            letterEl.addEventListener('mouseenter', (e) => {
                e.stopPropagation();
                this.handleElementMouseEnter(e, letterEl);
                this.showElementTooltip(letterEl);
            });
            letterEl.addEventListener('mousemove', () => this.positionTooltip(letterEl));
            letterEl.addEventListener('mouseleave', () => this.hideTextTooltip());
            letterEl.addEventListener('mouseup', (e) => {
                e.stopPropagation();
                this.handleElementMouseUp(e, letterEl);
            });
            letterEl.addEventListener('contextmenu', (e) => {
                e.stopPropagation();
                this.handleLetterClick(e, letterEl);
            });

            container.appendChild(letterEl);
        }
    },

    renderTranslationLayer(container, verse) {
        // Render mixed Arabic/English translation view
        // Default granularity: word-level

        if (!verse.tokens || verse.tokens.length === 0) {
            // Fallback to simple word splitting
            const words = verse.text.split(' ');
            words.forEach((word, idx) => {
                this.renderTranslationSegment(container, {
                    id: `word-${idx}`,
                    text: word,
                    type: 'word'
                }, verse);
            });
        } else {
            // Use token data
            verse.tokens.forEach(token => {
                this.renderTranslationSegment(container, {
                    id: token.id,
                    text: token.form,
                    type: 'token',
                    tokenData: token
                }, verse);
            });
        }
    },

    renderTranslationSegment(container, segment, verse) {
        // Find if this segment has a translation
        const translation = this.translations.find(t =>
            t.segment_id === segment.id || t.segment_id === segment.text
        );

        const segmentEl = document.createElement('span');
        segmentEl.className = 'segment editable';
        segmentEl.dataset.segmentId = segment.id;
        segmentEl.dataset.originalText = segment.text;
        segmentEl.dataset.displayText = segment.text;
        segmentEl.dataset.layer = 'Translation';
        if (verse) {
            this.applyVerseMetadata(segmentEl, verse);
        }

        if (translation) {
            // Show translation
            segmentEl.classList.add('translated');
            segmentEl.textContent = translation.translation;
            segmentEl.dataset.translationId = translation.id;
            segmentEl.dataset.translation = translation.translation;

            // Add tooltip showing original Arabic
            const tooltip = document.createElement('span');
            tooltip.className = 'original-tooltip';
            tooltip.textContent = segment.text;
            segmentEl.appendChild(tooltip);
        } else {
            // Show original Arabic
            segmentEl.classList.add('untranslated');
            segmentEl.textContent = segment.text;
        }

        // Click to edit
        segmentEl.addEventListener('click', (e) => {
            e.stopPropagation();
            this.startTranslationEdit(segmentEl, segment, translation);
        });
        segmentEl.addEventListener('mouseenter', () => this.showElementTooltip(segmentEl));
        segmentEl.addEventListener('mousemove', () => this.positionTooltip(segmentEl));
        segmentEl.addEventListener('mouseleave', () => this.hideTextTooltip());

        container.appendChild(segmentEl);
        container.appendChild(document.createTextNode(' '));
    },

    startTranslationEdit(segmentEl, segment, existingTranslation) {
        // Clear any other editing segments
        document.querySelectorAll('.segment.editing').forEach(el => {
            el.classList.remove('editing');
            const editor = el.querySelector('.inline-editor');
            if (editor) editor.remove();
            const controls = el.querySelector('.translation-controls');
            if (controls) controls.remove();
        });

        this.editingSegment = { element: segmentEl, segment, existingTranslation };

        segmentEl.classList.add('editing');
        const currentText = existingTranslation ? existingTranslation.translation : '';

        // Create inline editor
        const editor = document.createElement('input');
        editor.className = 'inline-editor';
        editor.type = 'text';
        editor.value = currentText;
        editor.placeholder = 'Enter translation...';

        // Create control buttons
        const controls = document.createElement('span');
        controls.className = 'translation-controls';

        const saveBtn = document.createElement('button');
        saveBtn.className = 'translation-btn save';
        saveBtn.textContent = '✓';
        saveBtn.title = 'Save';
        saveBtn.onclick = (e) => {
            e.stopPropagation();
            this.saveTranslation(editor.value);
        };

        const cancelBtn = document.createElement('button');
        cancelBtn.className = 'translation-btn';
        cancelBtn.textContent = '✕';
        cancelBtn.title = 'Cancel';
        cancelBtn.onclick = (e) => {
            e.stopPropagation();
            this.cancelTranslationEdit();
        };

        controls.appendChild(saveBtn);
        controls.appendChild(cancelBtn);

        // Replace segment content with editor
        segmentEl.textContent = '';
        segmentEl.appendChild(editor);
        segmentEl.appendChild(controls);

        // Focus editor
        editor.focus();
        editor.select();

        // Enter to save, Esc to cancel
        editor.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                this.saveTranslation(editor.value);
            } else if (e.key === 'Escape') {
                e.preventDefault();
                this.cancelTranslationEdit();
            }
        });
    },

    async saveTranslation(translationText) {
        if (!this.editingSegment || !translationText.trim()) {
            this.cancelTranslationEdit();
            return;
        }

        const { segment, existingTranslation } = this.editingSegment;

        const translation = {
            segment_type: segment.type,
            segment_id: segment.id,
            original_text: segment.text,
            translation: translationText.trim()
        };

        if (existingTranslation) {
            // Update existing
            translation.id = existingTranslation.id;
        }

        // Save to backend
        const verseRef = `${this.currentVerse.surah.number}:${this.currentVerse.ayah}`;

        try {
            const response = await fetch(`/api/translations/${verseRef}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(translation)
            });

            const result = await response.json();
            if (result.success) {
                // Reload translations and re-render
                await this.loadTranslations();
                this.renderSurah();
            }
        } catch (error) {
            console.error('Error saving translation:', error);
            alert('Failed to save translation');
        }

        this.editingSegment = null;
    },

    cancelTranslationEdit() {
        if (this.editingSegment) {
            this.renderSurah();
            this.editingSegment = null;
        }
    },

    async loadTranslations() {
        if (!this.currentVerse) return;

        const verseRef = `${this.currentVerse.surah.number}:${this.currentVerse.ayah}`;

        try {
            const response = await fetch(`/api/translations/${verseRef}`);
            this.translations = await response.json();
        } catch (error) {
            console.error('Error loading translations:', error);
            this.translations = [];
        }
    },

    // ===== Word Interactions =====

    handleWordClick(e, wordEl) {
        e.preventDefault();
        if (e.type === 'contextmenu') {
            this.navigateLayerUp();
            return;
        }
        const verse = this.getVerseFromElement(wordEl);
        if (verse) {
            this.currentVerse = verse;
            this.currentSurahNumber = verse.surah.number;
            this.currentAyahNumber = verse.ayah;
            this.renderAyahList();
            this.loadPronounData();
        }

        this.showElementDetails(wordEl);
        const label = wordEl.dataset.displayText || wordEl.textContent.trim();
        const id = wordEl.dataset.tokenId || wordEl.dataset.wordId || wordEl.dataset.elementIndex;

        if (this.appMode === 'read') {
            this.assignStructure(wordEl);
        } else if (this.mode === 'annotate') {
            this.annotateElement(wordEl);
        } else {
            this.toggleSelection(wordEl);
        }

        // Drill down to morphology
        this.setLayer('morphological');
    },

    handleMorphemeClick(e, morphemeEl) {
        e.preventDefault();
        e.stopPropagation();
        if (e.type === 'contextmenu') {
            this.navigateLayerUp();
            return;
        }
        this.setHypothesisTargetForLayer('morphological');

        const verse = this.getVerseFromElement(morphemeEl);
        if (verse) {
            this.currentVerse = verse;
            this.currentSurahNumber = verse.surah.number;
            this.currentAyahNumber = verse.ayah;
            this.renderAyahList();
            this.loadPronounData();
        }

        this.showElementDetails(morphemeEl);
        const label = morphemeEl.dataset.displayText || morphemeEl.textContent.trim();
        const id = morphemeEl.dataset.segmentId || morphemeEl.dataset.tokenId || morphemeEl.dataset.elementIndex;

        if (this.appMode === 'read') {
            this.assignStructure(morphemeEl);
        } else if (this.mode === 'annotate') {
            this.annotateElement(morphemeEl);
        } else {
            this.toggleSelection(morphemeEl);
        }

        // Drill down to letters
        this.setLayer('letter');
    },

    handleLetterClick(e, letterEl) {
        e.preventDefault();
        e.stopPropagation();
        if (e.type === 'contextmenu') {
            this.navigateLayerUp();
            return;
        }
        this.setHypothesisTargetForLayer('letter');

        const verse = this.getVerseFromElement(letterEl);
        if (verse) {
            this.currentVerse = verse;
            this.currentSurahNumber = verse.surah.number;
            this.currentAyahNumber = verse.ayah;
            this.renderAyahList();
            this.loadPronounData();
        }

        this.showElementDetails(letterEl);
        const label = letterEl.dataset.displayText || letterEl.textContent.trim();
        const id = letterEl.dataset.elementIndex;

        if (this.appMode === 'read') {
            this.assignStructure(letterEl);
        } else if (this.mode === 'annotate') {
            this.annotateElement(letterEl);
        } else {
            this.toggleSelection(letterEl);
        }
    },

    handleSentenceClick(e, sentenceEl) {
        e.preventDefault();
        e.stopPropagation();
        if (e.type === 'contextmenu') {
            this.navigateLayerUp();
            return;
        }
        this.setHypothesisTargetForLayer('sentence');

        const verse = this.getVerseFromElement(sentenceEl);
        if (verse) {
            this.currentVerse = verse;
            this.currentSurahNumber = verse.surah.number;
            this.currentAyahNumber = verse.ayah;
            this.renderAyahList();
            this.loadPronounData();
        }

        this.showElementDetails(sentenceEl);
        const label = sentenceEl.dataset.displayText || sentenceEl.textContent.trim().slice(0, 40) + '...';
        const id = sentenceEl.dataset.sentenceId || `${sentenceEl.dataset.surah}:${sentenceEl.dataset.ayah}`;
        this.setCurrentTarget('clause', id, { text: label }, `Sentence ${label}`);

        if (this.appMode === 'read') {
            this.assignStructure(sentenceEl);
        } else if (this.mode === 'annotate') {
            this.annotateElement(sentenceEl);
        } else {
            this.toggleSelection(sentenceEl);
        }

        // Drill down to word layer after viewing sentence
        this.setLayer('word');
    },

    handleWordMouseDown(e, wordEl) {
        if (this.mode === 'connect') {
            this.connectionSource = wordEl;
            wordEl.classList.add('connection-source');
        }
    },

    handleWordMouseUp(e, wordEl) {
        if (this.mode === 'connect' && this.connectionSource && this.connectionSource !== wordEl) {
            this.createConnection(this.connectionSource, wordEl);
            this.connectionSource.classList.remove('connection-source');
            this.connectionSource = null;
        }
    },

    // ===== Drag Selection Handlers =====

    handleElementMouseDown(e, element) {
        if (this.mode === 'select' && e.button === 0) { // Left mouse button only
            e.preventDefault();
            this.isDragging = true;
            this.dragStartElement = element;
            this.dragSelectionActive = true;

            // Clear existing selection unless Shift is held
            if (!e.shiftKey) {
                this.clearSelection();
            }

            // Select the starting element
            this.selectElement(element);
        } else if (this.mode === 'connect') {
            this.connectionSource = element;
            element.classList.add('connection-source');
        }
    },

    handleElementMouseEnter(e, element) {
        if (this.isDragging && this.dragSelectionActive && this.mode === 'select') {
            e.preventDefault();
            this.selectRangeFromStartTo(element);
        }
    },

    handleElementMouseUp(e, element) {
        if (this.mode === 'select' && this.isDragging) {
            e.preventDefault();
            this.isDragging = false;
            this.dragStartElement = null;
            this.dragSelectionActive = false;
        } else if (this.mode === 'connect' && this.connectionSource && this.connectionSource !== element) {
            this.createConnection(this.connectionSource, element);
            this.connectionSource.classList.remove('connection-source');
            this.connectionSource = null;
        }
    },

    selectElement(element) {
        if (!element.classList.contains('selected')) {
            element.classList.add('selected');

            const id = element.dataset.segmentId || element.dataset.tokenId ||
                       element.dataset.wordId || element.dataset.position;

            if (!this.selectedWords.includes(id)) {
                this.selectedWords.push(id);
            }
        }
    },

    selectRangeFromStartTo(endElement) {
        if (!this.dragStartElement) return;

        const startIndex = parseInt(this.dragStartElement.dataset.elementIndex);
        const endIndex = parseInt(endElement.dataset.elementIndex);
        const startSurah = this.dragStartElement.dataset.surah;
        const startAyah = this.dragStartElement.dataset.ayah;

        const minIndex = Math.min(startIndex, endIndex);
        const maxIndex = Math.max(startIndex, endIndex);

        // Clear previous selection
        this.clearSelection();

        // Select all elements in range
        const selector = `.selectable${startSurah ? `[data-surah="${startSurah}"]` : ''}${startAyah ? `[data-ayah="${startAyah}"]` : ''}`;
        const selectables = document.querySelectorAll(selector);
        selectables.forEach(el => {
            const elIndex = parseInt(el.dataset.elementIndex);
            if (elIndex >= minIndex && elIndex <= maxIndex) {
                this.selectElement(el);
            }
        });

        this.updateSelectionInfo();
    },

    toggleSelection(element) {
        element.classList.toggle('selected');

        const baseId = element.dataset.segmentId || element.dataset.tokenId ||
                       element.dataset.wordId || element.dataset.position || element.dataset.elementIndex;
        const verseKey = `${element.dataset.surah || 's'}:${element.dataset.ayah || 'a'}`;
        const id = `${verseKey}:${baseId}`;
        const label = element.dataset.displayText || element.textContent.trim();
        const type = element.dataset.layer ? element.dataset.layer.toLowerCase() : (element.dataset.segmentId ? 'morpheme' : 'word');

        const idx = this.selectedWords.findIndex(e => e.id === id);
        if (idx > -1) {
            this.selectedWords.splice(idx, 1);
        } else {
            this.selectedWords.push({ id, label, type });
        }

        // Show selection info in sidebar
        this.updateSelectionInfo();
        this.setTargetFromSelection();
    },

    clearSelection() {
        document.querySelectorAll('.selected').forEach(el => {
            el.classList.remove('selected');
        });
        this.selectedWords = [];
        this.connectionSource = null;
        this.updateSelectionInfo();
    },

    updateSelectionInfo() {
        // Could show selected elements in sidebar
        const count = this.selectedWords.length;
        const display = document.getElementById('hypTargetDisplay');
        if (display && this.selectedWords.length > 1) {
            const labels = this.selectedWords.map(e => e.label).join(', ');
            display.textContent = `Phrase: ${labels}`;
        }
    },

    setTargetFromSelection() {
        // If a clause is already selected, keep it unless multiple words are selected
        if (this.currentTarget && this.currentTarget.type === 'clause') {
            if (this.selectedWords.length > 1) {
                const labels = this.selectedWords.map(e => e.label).join(', ');
                this.setCurrentTarget('phrase', this.selectedWords.map(e => e.id).join('|'), { items: this.selectedWords }, `Phrase (${labels})`);
            }
            return;
        }

        if (this.selectedWords.length === 0) {
            return;
        }

        if (this.selectedWords.length === 1) {
            const item = this.selectedWords[0];
            this.setCurrentTarget(item.type, item.id, { text: item.label }, `${item.type.toUpperCase()} ${item.label}`);
        } else {
            const labels = this.selectedWords.map(e => e.label).join(', ');
            this.setCurrentTarget('phrase', this.selectedWords.map(e => e.id).join('|'), { items: this.selectedWords }, `Phrase (${labels})`);
        }
    },

    // ===== Pattern Definition =====

    showPatternModal(wordId) {
        const modal = document.getElementById('patternModal');
        modal.style.display = 'flex';
        modal.dataset.wordId = wordId;
    },

    async savePattern() {
        const pattern = {
            name: document.getElementById('patternName').value,
            type: document.getElementById('patternType').value,
            description: document.getElementById('patternDescription').value,
            example_word_id: document.getElementById('patternModal').dataset.wordId,
            verse_ref: `${this.currentVerse.surah.number}:${this.currentVerse.ayah}`,
            apply_corpus: document.getElementById('applyCorpus').checked
        };

        try {
            const response = await fetch('/api/patterns', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(pattern)
            });

            const result = await response.json();

            if (result.success) {
                alert('Pattern saved successfully!');
                document.getElementById('patternModal').style.display = 'none';
                document.getElementById('patternForm').reset();
            }
        } catch (error) {
            console.error('Error saving pattern:', error);
            alert('Error saving pattern');
        }
    },

    renderSentenceLayer(container, verse) {
        const sentenceEl = document.createElement('span');
        sentenceEl.className = 'sentence selectable';
        sentenceEl.textContent = verse.text;
        sentenceEl.dataset.layer = 'Sentence';
        sentenceEl.dataset.displayText = verse.text;
        sentenceEl.dataset.elementIndex = 0;
        sentenceEl.dataset.sentenceId = `${verse.surah.number}:${verse.ayah}`;
        this.applyVerseMetadata(sentenceEl, verse);

        sentenceEl.addEventListener('click', (e) => {
            e.stopPropagation();
            this.handleSentenceClick(e, sentenceEl);
        });
        sentenceEl.addEventListener('mousedown', (e) => {
            e.stopPropagation();
            this.handleElementMouseDown(e, sentenceEl);
        });
        sentenceEl.addEventListener('mouseenter', (e) => {
            e.stopPropagation();
            this.handleElementMouseEnter(e, sentenceEl);
            this.showElementTooltip(sentenceEl);
        });
        sentenceEl.addEventListener('mousemove', () => this.positionTooltip(sentenceEl));
        sentenceEl.addEventListener('mouseleave', () => this.hideTextTooltip());
        sentenceEl.addEventListener('mouseup', (e) => {
            e.stopPropagation();
            this.handleElementMouseUp(e, sentenceEl);
        });

        container.appendChild(sentenceEl);
    },

    // ===== Connections =====

    async createConnection(sourceEl, targetEl) {
        const connection = {
            id: Date.now().toString(),
            type: 'internal',
            layer: this.currentLayer,
            from: sourceEl.dataset.tokenId || sourceEl.dataset.wordId,
            to: targetEl.dataset.tokenId || targetEl.dataset.wordId,
            note: prompt('Connection note (optional):') || ''
        };

        this.connections.internal.push(connection);
        this.renderConnections();
        await this.saveConnections();
    },

    async loadConnections() {
        if (!this.currentVerse) return;

        const verseRef = `${this.currentVerse.surah.number}:${this.currentVerse.ayah}`;

        try {
            const response = await fetch(`/api/connections/${verseRef}`);
            const data = await response.json();

            this.connections = data;
            this.renderConnections();
            this.renderExternalIndicators();
        } catch (error) {
            console.error('Error loading connections:', error);
        }
    },

    async saveConnections() {
        if (!this.currentVerse) return;

        const verseRef = `${this.currentVerse.surah.number}:${this.currentVerse.ayah}`;

        try {
            await fetch(`/api/connections/${verseRef}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(this.connections)
            });
        } catch (error) {
            console.error('Error saving connections:', error);
        }
    },

    renderConnections() {
        const svg = document.getElementById('connectionCanvas');
        svg.innerHTML = '';

        this.connections.internal.forEach(conn => {
            this.drawConnection(svg, conn);
        });
    },

    drawConnection(svg, connection) {
        const source = document.querySelector(`[data-token-id="${connection.from}"], [data-word-id="${connection.from}"]`);
        const target = document.querySelector(`[data-token-id="${connection.to}"], [data-word-id="${connection.to}"]`);

        if (!source || !target) return;

        const sourceRect = source.getBoundingClientRect();
        const targetRect = target.getBoundingClientRect();
        const canvasRect = svg.getBoundingClientRect();

        const x1 = sourceRect.left + sourceRect.width / 2 - canvasRect.left;
        const y1 = sourceRect.top + sourceRect.height / 2 - canvasRect.top;
        const x2 = targetRect.left + targetRect.width / 2 - canvasRect.left;
        const y2 = targetRect.top + targetRect.height / 2 - canvasRect.top;

        const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');

        // Curved path
        const midX = (x1 + x2) / 2;
        const midY = (y1 + y2) / 2;
        const curveDepth = 40;
        const d = `M ${x1} ${y1} Q ${midX} ${midY - curveDepth}, ${x2} ${y2}`;

        path.setAttribute('d', d);
        path.setAttribute('class', 'connection-line');
        path.setAttribute('stroke', this.getLayerColor(connection.layer));
        path.setAttribute('data-connection-id', connection.id);

        svg.appendChild(path);
    },

    renderExternalIndicators() {
        // Group external connections by direction
        const directions = { top: [], right: [], bottom: [], left: [] };

        this.connections.external.forEach(conn => {
            const direction = this.getConnectionDirection(conn);
            directions[direction].push(conn);
        });

        // Update indicators
        Object.entries(directions).forEach(([dir, conns]) => {
            const indicator = document.getElementById(`edge${dir.charAt(0).toUpperCase() + dir.slice(1)}`);

            if (conns.length === 0) {
                indicator.style.display = 'none';
            } else {
                indicator.style.display = 'flex';
                indicator.innerHTML = `
                    <div class="indicator-count">${conns.length}</div>
                    <div class="indicator-arrow">${this.getArrow(dir)}</div>
                `;
            }
        });
    },

    getConnectionDirection(connection) {
        const [targetSurah, targetAyah] = connection.targetVerse.split(':').map(Number);
        const currentSurah = this.currentVerse.surah.number;
        const currentAyah = this.currentVerse.ayah;

        if (targetSurah < currentSurah || (targetSurah === currentSurah && targetAyah < currentAyah)) {
            return 'top';
        } else {
            return 'bottom';
        }
    },

    getArrow(direction) {
        return { top: '↑', right: '→', bottom: '↓', left: '←' }[direction] || '•';
    },

    getLayerColor(layer) {
        const colors = {
            morphological: '#2c5f2d',
            syntactic: '#97bc62',
            thematic: '#c9a961',
            phonological: '#6b4e71',
            compositional: '#4a7c9b',
            annotations: '#d97742'
        };
        return colors[layer] || '#2c5f2d';
    },

    // ===== Context Menu Actions =====

    handleMenuAction(action, wordEl) {
        if (action === 'annotate' && this.appMode !== 'write') {
            alert('Switch to Write mode to annotate.');
            return;
        }

        switch(action) {
            case 'annotate':
                this.annotateWord(wordEl);
                break;
            case 'pattern':
                this.showPatternModal(wordEl.dataset.tokenId || wordEl.dataset.wordId);
                break;
            case 'copy':
                navigator.clipboard.writeText(wordEl.textContent);
                break;
        }
    },

    annotateWord(wordEl) {
        this.annotateElement(wordEl);
    },

    annotateElement(element) {
        const note = prompt('Enter annotation:');
        if (note) {
            const id = element.dataset.segmentId || element.dataset.tokenId ||
                       element.dataset.wordId || element.dataset.position ||
                       element.dataset.sentenceId;
            const surah = parseInt(element.dataset.surah, 10);
            const ayah = parseInt(element.dataset.ayah, 10);

            if (!surah || !ayah) {
                alert('Unable to determine verse for this element.');
                return;
            }

            const scopeMap = {
                letter: 'letter',
                morphological: 'morpheme',
                word: 'phrase',
                sentence: 'sentence'
            };

            const layerDefinition = LAYER_DEFINITIONS[this.currentLayer];
            const categoryMeta = layerDefinition?.categories?.find(cat => cat.id === this.selectedStructureCategory);

            const annotation = {
                type: 'note',
                target_token_ids: [id],
                note: note,
                layer: this.currentLayer,
                layer_label: layerDefinition?.label || this.currentLayer,
                tags: [],
                scope: scopeMap[this.currentLayer] || 'word',
                status: 'hypothesis',
                refs: [],
                structure_category: this.selectedStructureCategory,
                structure_category_label: categoryMeta?.label || null
            };

            // Save annotation via API
            this.saveAnnotation(annotation, surah, ayah);
        }
    },

    async saveAnnotation(annotation, surah, ayah) {
        if (!surah || !ayah) return;
        try {
            const response = await fetch(`/api/annotations/${surah}/${ayah}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(annotation)
            });

            const result = await response.json();
            if (result.success) {
                console.log('Annotation saved successfully');
                // Refresh cached surah data
                delete this.surahCache[surah];
                if (this.currentSurahNumber === surah) {
                    const targetAyah = ayah;
                    await this.selectSurah(surah);
                    if (targetAyah) {
                        this.currentAyahNumber = targetAyah;
                        this.renderAyahList();
                        this.scrollToAyah(targetAyah, false);
                    }
                }
            }
        } catch (error) {
            console.error('Error saving annotation:', error);
            alert('Failed to save annotation');
        }
    },

    showElementDetails(element) {
        const panel = document.getElementById('elementDetails');
        if (!panel) return;

        const text = element.dataset.displayText || element.textContent.trim();
        const type = element.dataset.type || element.dataset.layer || '';
        const pos = element.dataset.pos || '';
        const root = element.dataset.root && element.dataset.root !== '—' ? element.dataset.root : '';
        const lemma = element.dataset.lemma && element.dataset.lemma !== '—' ? element.dataset.lemma : '';
        const structure = element.dataset.structureCategoryLabel || '';
        const features = element.dataset.features || '';

        const chips = [];
        if (root) chips.push({ action: 'root', label: `Root ${root}`, value: root });
        if (pos) chips.push({ action: 'morph', label: `POS ${pos}`, value: `pos:${pos}`.toLowerCase() });
        if (type) chips.push({ action: 'morph', label: type.toUpperCase(), value: type.toLowerCase() });
        if (lemma) chips.push({ action: 'morph', label: `Lemma ${lemma}`, value: lemma });
        if (features) chips.push({ action: 'morph', label: features, value: features });
        if (structure) chips.push({ action: 'morph', label: structure, value: structure });

        panel.innerHTML = `
            <div class="detail-text">${this.escapeHtml(text)}</div>
            <div class="detail-meta">
                ${chips.length ? chips.map(chip => `<button class="detail-chip" data-action="${chip.action}" data-value="${this.escapeHtml(chip.value)}">${this.escapeHtml(chip.label)}</button>`).join('') : '<span class="hint">No metadata available for quick search.</span>'}
            </div>
        `;

        panel.querySelectorAll('.detail-chip').forEach(btn => {
            btn.addEventListener('click', () => {
                const action = btn.dataset.action;
                const value = btn.dataset.value;
                this.handleDetailSearch(action, value);
            });
        });

        this.openPatternPanel();
    },

    handleDetailSearch(action, value) {
        if (!value) return;
        switch(action) {
            case 'root':
                this.performRootSearch(value);
                break;
            case 'morph':
                this.renderSearchMessage(`Searching ${value}...`);
                fetch(`/api/search/morphology?q=${encodeURIComponent(value)}`)
                    .then(res => res.json())
                    .then(data => this.renderSearchResults(data.results, 'No matches found for this pattern.'))
                    .catch(err => {
                        console.error('Morph search failed', err);
                        this.renderSearchMessage('Morphology search failed.');
                    });
                break;
            case 'syntax':
                this.renderSearchMessage(`Searching syntactic pattern ${value}...`);
                fetch(`/api/search/syntax?q=${encodeURIComponent(value)}`)
                    .then(res => res.json())
                    .then(data => this.renderSearchResults(data.results, 'No syntactic matches found.'))
                    .catch(err => {
                        console.error('Syntax search failed', err);
                        this.renderSearchMessage('Syntax search failed.');
                    });
                break;
            default:
                break;
        }
    }
};

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    Canvas.init();
});

// Export for use in other scripts
window.Canvas = Canvas;
