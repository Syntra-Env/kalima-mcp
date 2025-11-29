// ===== Codex Research Canvas - Rendering Layers =====
// Layer rendering for text, morphological, letter, translation, and sentence views

// Extends the Canvas object
Object.assign(Canvas, {
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
            });
            wordEl.addEventListener('mousemove', () => {});
            wordEl.addEventListener('mouseleave', () => {});
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
                    });
                    morpheme.addEventListener('mousemove', () => {});
                    morpheme.addEventListener('mouseleave', () => {});
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
            });
            letterEl.addEventListener('mousemove', () => {});
            letterEl.addEventListener('mouseleave', () => {});
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
        });
        sentenceEl.addEventListener('mousemove', () => {});
        sentenceEl.addEventListener('mouseleave', () => {});
        sentenceEl.addEventListener('mouseup', (e) => {
            e.stopPropagation();
            this.handleElementMouseUp(e, sentenceEl);
        });

        container.appendChild(sentenceEl);
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

    cancelTranslationEdit() {
        if (this.editingSegment) {
            this.renderSurah();
            this.editingSegment = null;
        }
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
});
