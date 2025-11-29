// ===== Codex Research Canvas - User Interactions =====
// Click handlers, selection management, and annotation interactions

// Extends the Canvas object
Object.assign(Canvas, {
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
    },,

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
    },,

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
    },,

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
    },,

    handleWordMouseDown(e, wordEl) {
        if (this.mode === 'connect') {
            this.connectionSource = wordEl;
            wordEl.classList.add('connection-source');
        }
    },,

    handleWordMouseUp(e, wordEl) {
        if (this.mode === 'connect' && this.connectionSource && this.connectionSource !== wordEl) {
            this.createConnection(this.connectionSource, wordEl);
            this.connectionSource.classList.remove('connection-source');
            this.connectionSource = null;
        }
    },,

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
    },,

    handleElementMouseEnter(e, element) {
        if (this.isDragging && this.dragSelectionActive && this.mode === 'select') {
            e.preventDefault();
            this.selectRangeFromStartTo(element);
        }
    },,

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
    },,

    selectElement(element) {
        if (!element.classList.contains('selected')) {
            element.classList.add('selected');

            const id = element.dataset.segmentId || element.dataset.tokenId ||
                       element.dataset.wordId || element.dataset.position;

            if (!this.selectedWords.includes(id)) {
                this.selectedWords.push(id);
            }
        }
    },,

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
    },,

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
    },,

    clearSelection() {
        document.querySelectorAll('.selected').forEach(el => {
            el.classList.remove('selected');
        });
        this.selectedWords = [];
        this.connectionSource = null;
        this.updateSelectionInfo();
    },,

    updateSelectionInfo() {
        // Could show selected elements in sidebar
        const count = this.selectedWords.length;
        const display = document.getElementById('hypTargetDisplay');
        if (display && this.selectedWords.length > 1) {
            const labels = this.selectedWords.map(e => e.label).join(', ');
            display.textContent = `Phrase: ${labels}`;
        }
    },,

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
    },,

    showElementDetails(element) {
        const panel = document.getElementById('elementDetails');
        if (!panel) return;

        // Store current element for layer navigation
        this.currentDetailElement = element;

        const text = element.dataset.displayText || element.textContent.trim();
        const type = element.dataset.type || element.dataset.layer || '';
        const pos = element.dataset.pos || '';
        const root = element.dataset.root && element.dataset.root !== '—' ? element.dataset.root : '';
        const pattern = element.dataset.pattern || '';
        const lemma = element.dataset.lemma && element.dataset.lemma !== '—' ? element.dataset.lemma : '';
        const structure = element.dataset.structureCategoryLabel || '';
        const features = element.dataset.features || '';

        // Extract enhanced morphological features
        const verbForm = element.dataset.verbForm || '';
        const person = element.dataset.person || '';
        const number = element.dataset.number || '';
        const gender = element.dataset.gender || '';
        const voice = element.dataset.voice || '';
        const mood = element.dataset.mood || '';
        const case_ = element.dataset.case || '';
        const tense = element.dataset.tense || '';