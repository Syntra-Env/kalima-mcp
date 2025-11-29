// ===== Codex Research Canvas - Pattern Handling =====
// Pattern builder, pattern search, and pattern management

// Extends the Canvas object
Object.assign(Canvas, {
    breakPatternWord() {
        const input = document.getElementById('patternInput');
        const word = (input?.value || '').trim();
        this.patternSegments = this.parseArabicWord(word);
        this.renderPatternSegments();
    },,

    parseArabicWord(word) {
        const segments = [];
        const isDiacritic = (ch) => /[\u064B-\u0652\u0670\u0653-\u0655]/.test(ch);
        const isLetter = (ch) => /[\u0620-\u064a\u0671-\u0673\u0675]/.test(ch);
        for (let i = 0; i < word.length; i++) {
            const ch = word[i];
            if (isDiacritic(ch)) {
                if (segments.length) {
                    segments[segments.length - 1].diacritics.push(ch);
                }
            } else if (isLetter(ch)) {
                segments.push({ letter: ch, diacritics: [], any_letter: false, any_diacritics: false });
            } else {
                // Skip tatweel/whitespace/other symbols
                continue;
            }
        }
        return segments;
    },,

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
    },,

    async submitPatternSearch() {
        if (!this.patternSegments || this.patternSegments.length === 0) {
            const input = document.getElementById('patternInput');
            const word = (input?.value || '').trim();
            if (word) {
                this.patternSegments = this.parseArabicWord(word);
                this.renderPatternSegments();
            }
        }
        if (!this.patternSegments || this.patternSegments.length === 0) {
            this.renderSearchMessage('Add a word and break it into pattern segments first.');
            return;
        }
        const allowPrefix = document.getElementById('patternAllowPrefix')?.checked || false;
        const autoFlexSuffix = this.patternSegments.some(seg => seg.any_letter || seg.any_diacritics);
        const allowSuffix = document.getElementById('patternAllowSuffix')?.checked || autoFlexSuffix;
        this.renderSearchMessage('Searching pattern...');
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
            if (!resp.ok) {
                throw new Error(`Pattern search failed (${resp.status})`);
            }
            const data = await resp.json();
            const results = (data.results || []).map(r => ({
                ...r,
                matchRegex: r.match_regex || r.matchRegex || null
            }));
            const totalMatches = results.reduce((sum, r) => sum + (r.match_count || 1), 0);
            this.renderSearchResults(results, 'No matches for this pattern.', totalMatches);
        } catch (error) {
            console.error('Pattern search failed', error);
            this.renderSearchMessage('Pattern search failed. Please try again.');
        }
    },,

    async loadMorphPatterns() {
        try {
            const response = await fetch('/api/morph_patterns');
            this.morphPatterns = await response.json();
        } catch (error) {
            console.error('Error loading morphological patterns:', error);
        }
    },,

    async loadSyntaxPatterns() {
        try {
            const response = await fetch('/api/syntax_patterns');
            this.syntaxPatterns = await response.json();
        } catch (error) {
            console.error('Error loading syntactic patterns:', error);
        }
    },,

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
    },,

    showPatternModal(wordId) {
        const modal = document.getElementById('patternModal');
        modal.style.display = 'flex';
        modal.dataset.wordId = wordId;
    },
});
