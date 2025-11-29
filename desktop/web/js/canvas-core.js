// ===== Codex Research Canvas - Core Initialization =====
// Canvas object setup, event listeners, layer management, and mode control

// Extends the Canvas object
Object.assign(Canvas, {
    init() {
        this.setupEventListeners();
        // Disable hover tooltip UI
        this.tooltipEl = null;
        this.renderLayerPalette();
        this.setAppMode(this.appMode);
        this.setHypothesisTargetForLayer(this.currentLayer);
        this.setupMorphBuilder();
        this.setupSyntaxBuilder();
        this.setupStackPanels();
        this.loadSurahSummaries();
        this.loadRootOptions();
        this.loadMorphPatterns();
        this.loadSyntaxPatterns();
        this.loadNotesList();
        this.renderNavMap();
        this.detailZoom = 1;
    },

    setupStackPanels() {
        const container = document.getElementById('sideStacks');
        if (!container) return;

        // restore order
        const saved = localStorage.getItem('codex-stack-order');
        if (saved) {
            const order = saved.split(',');
            order.forEach(id => {
                const panel = container.querySelector(`.stack-panel[data-panel="${id}"]`);
                if (panel) container.appendChild(panel);
            });
        }

        // attach toggles
        container.querySelectorAll('.stack-toggle').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const panel = e.currentTarget.closest('.stack-panel');
                if (!panel) return;
                panel.classList.toggle('collapsed');
                e.currentTarget.textContent = panel.classList.contains('collapsed') ? '+' : '-';
            });
        });

        // drag reorder
        let dragEl = null;
        container.querySelectorAll('.stack-header').forEach(header => {
            header.addEventListener('dragstart', (e) => {
                dragEl = header.closest('.stack-panel');
                e.dataTransfer.effectAllowed = 'move';
            });
            header.addEventListener('dragover', (e) => {
                e.preventDefault();
                const overPanel = header.closest('.stack-panel');
                if (!dragEl || dragEl === overPanel) return;
                const rect = overPanel.getBoundingClientRect();
                const before = (e.clientY - rect.top) < rect.height / 2;
                if (before) {
                    overPanel.parentNode.insertBefore(dragEl, overPanel);
                } else {
                    overPanel.parentNode.insertBefore(dragEl, overPanel.nextSibling);
                }
            });
            header.addEventListener('dragend', () => {
                dragEl = null;
                const order = Array.from(container.querySelectorAll('.stack-panel')).map(p => p.dataset.panel);
                localStorage.setItem('codex-stack-order', order.join(','));
            });
        });
    },

    setupEventListeners() {
        // Menu toggle
        const sideMenu = document.getElementById('sideMenu');
        const canvasEl = document.getElementById('canvas');

        document.getElementById('menuToggle').addEventListener('click', () => {
            sideMenu.classList.toggle('collapsed');
            canvasEl.classList.toggle('menu-open');
        });

        // Layer navigation buttons
        const layerUp = document.getElementById('layerUp');
        const layerDown = document.getElementById('layerDown');
        if (layerUp) layerUp.addEventListener('click', () => this.navigateLayerUp());
        if (layerDown) layerDown.addEventListener('click', () => this.navigateLayerDown());

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
            const menu = document.getElementById('contextMenu');
            if (menu) {
                menu.style.display = 'none';
            }
        });

        // Global mouseup to handle drag selection ending anywhere
        document.addEventListener('mouseup', () => {
            if (this.isDragging) {
                this.isDragging = false;
                this.dragStartElement = null;
                this.dragSelectionActive = false;
            }
        });

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

    setAppMode(mode) {
        this.appMode = 'read';
        this.setMode('select');
    },
});
