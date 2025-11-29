// ===== Codex Research Canvas - Annotation Interactions =====
// Annotation, detail display, and menu action handlers

// Extends the Canvas object
Object.assign(Canvas, {
        const aspect = element.dataset.aspect || '';
        const dependencyRel = element.dataset.dependencyRel || '';

        // Determine layer from element
        const layer = element.dataset.layer ||
                     (element.classList.contains('morpheme') ? 'Segment' :
                      element.classList.contains('word') ? 'Word' : 'Verse');

        const chips = [];

        // Basic features
        if (root) chips.push({ action: 'root', label: `Root: ${root}`, value: root });
        if (pattern) chips.push({ action: 'pattern', label: `Pattern: ${pattern}`, value: pattern });
        if (pos) chips.push({ action: 'pos', label: `POS: ${pos}`, value: pos });
        if (lemma) chips.push({ action: 'lemma', label: `Lemma: ${lemma}`, value: lemma });

        // Verb features
        if (verbForm) chips.push({ action: 'verb_form', label: `Form: ${verbForm}`, value: verbForm });
        if (voice) chips.push({ action: 'voice', label: `Voice: ${voice}`, value: voice });
        if (mood) chips.push({ action: 'mood', label: `Mood: ${mood}`, value: mood });
        if (tense) chips.push({ action: 'tense', label: `Tense: ${tense}`, value: tense });
        if (aspect) chips.push({ action: 'aspect', label: `Aspect: ${aspect}`, value: aspect });

        // Nominal features
        if (person) chips.push({ action: 'person', label: `Person: ${person}`, value: person });
        if (number) chips.push({ action: 'number', label: `Number: ${number}`, value: number });
        if (gender) chips.push({ action: 'gender', label: `Gender: ${gender}`, value: gender });
        if (case_) chips.push({ action: 'case', label: `Case: ${case_}`, value: case_ });

        // Dependency features
        if (dependencyRel) chips.push({ action: 'dependency', label: `Relation: ${dependencyRel}`, value: dependencyRel });

        // Structure and other
        if (type) chips.push({ action: 'type', label: `Type: ${type}`, value: type.toLowerCase() });
        if (structure) chips.push({ action: 'structure', label: structure, value: structure });

        // Build hierarchical display with clickable element
        panel.innerHTML = `
            <div class="detail-layer-info">
                <span class="detail-layer-label">Layer: ${layer}</span>
            </div>
            <div class="detail-text-interactive" title="Left-click to drill down, right-click to go up">
                ${this.escapeHtml(text)}
            </div>
            <div class="detail-meta">
                ${chips.length ? chips.map(chip => `<button class="detail-chip" data-action="${chip.action}" data-value="${this.escapeHtml(chip.value)}">${this.escapeHtml(chip.label)}</button>`).join('') : '<span class="hint">No metadata available for quick search.</span>'}
            </div>
        `;

        // Add click handlers to detail chips for searching
        panel.querySelectorAll('.detail-chip').forEach(btn => {
            btn.addEventListener('click', () => {
                const action = btn.dataset.action;
                const value = btn.dataset.value;
                this.handleDetailSearch(action, value);
            });
        });

        // Add layer navigation handlers to the interactive text display
        const interactiveText = panel.querySelector('.detail-text-interactive');
        if (interactiveText) {
            interactiveText.addEventListener('click', (e) => {
                e.preventDefault();
                this.navigateLayerDown(); // Left-click = drill down
            });

            interactiveText.addEventListener('contextmenu', (e) => {
                e.preventDefault();
                this.navigateLayerUp(); // Right-click = go up
            });
        }

        this.openPatternPanel();
    },,

    handleDetailSearch(action, value) {
        if (!value) return;

        switch(action) {
            case 'root':
                this.performRootSearch(value);
                break;

            case 'pattern':
                this.renderSearchMessage(`Searching pattern ${value}...`);
                fetch(`/api/search/morphology?q=${encodeURIComponent(value)}`)
                    .then(res => res.json())
                    .then(data => this.renderSearchResults(data.results || [], 'No matches found for this pattern.', data.count))
                    .catch(err => {
                        console.error('Pattern search failed', err);
                        this.renderSearchMessage('Pattern search failed.');
                    });
                break;

            case 'pos':
            case 'lemma':
            case 'type':
            case 'structure':
                this.renderSearchMessage(`Searching ${action} ${value}...`);
                fetch(`/api/search/morphology?q=${encodeURIComponent(value)}`)
                    .then(res => res.json())
                    .then(data => this.renderSearchResults(data.results || [], `No matches found for ${action} ${value}.`, data.count))
                    .catch(err => {
                        console.error('Morphology search failed', err);
                        this.renderSearchMessage('Morphology search failed.');
                    });
                break;

            case 'verb_form':
                this.renderSearchMessage(`Searching verb form ${value}...`);
                fetch(`/api/search/verb_forms?form=${encodeURIComponent(value)}`)
                    .then(res => res.json())
                    .then(data => this.renderSearchResults(data.results || [], `No verbs found for form ${value}.`, data.count))
                    .catch(err => {
                        console.error('Verb form search failed', err);
                        this.renderSearchMessage('Verb form search failed.');
                    });
                break;

            case 'person':
                this.renderSearchMessage(`Searching person ${value}...`);
                fetch(`/api/search/verb_forms?person=${encodeURIComponent(value)}`)
                    .then(res => res.json())
                    .then(data => this.renderSearchResults(data.results || [], `No matches found for person ${value}.`, data.count))
                    .catch(err => {
                        console.error('Person search failed', err);
                        this.renderSearchMessage('Person search failed.');
                    });
                break;

            case 'number':
                this.renderSearchMessage(`Searching number ${value}...`);
                fetch(`/api/search/verb_forms?number=${encodeURIComponent(value)}`)
                    .then(res => res.json())
                    .then(data => this.renderSearchResults(data.results || [], `No matches found for number ${value}.`, data.count))
                    .catch(err => {
                        console.error('Number search failed', err);
                        this.renderSearchMessage('Number search failed.');
                    });
                break;

            case 'gender':
                this.renderSearchMessage(`Searching gender ${value}...`);
                fetch(`/api/search/verb_forms?gender=${encodeURIComponent(value)}`)
                    .then(res => res.json())
                    .then(data => this.renderSearchResults(data.results || [], `No matches found for gender ${value}.`, data.count))
                    .catch(err => {
                        console.error('Gender search failed', err);
                        this.renderSearchMessage('Gender search failed.');
                    });
                break;

            case 'voice':
                this.renderSearchMessage(`Searching voice ${value}...`);
                fetch(`/api/search/verb_forms?voice=${encodeURIComponent(value)}`)
                    .then(res => res.json())
                    .then(data => this.renderSearchResults(data.results || [], `No matches found for voice ${value}.`, data.count))
                    .catch(err => {
                        console.error('Voice search failed', err);
                        this.renderSearchMessage('Voice search failed.');
                    });
                break;

            case 'mood':
                this.renderSearchMessage(`Searching mood ${value}...`);
                fetch(`/api/search/verb_forms?mood=${encodeURIComponent(value)}`)
                    .then(res => res.json())
                    .then(data => this.renderSearchResults(data.results || [], `No matches found for mood ${value}.`, data.count))
                    .catch(err => {
                        console.error('Mood search failed', err);
                        this.renderSearchMessage('Mood search failed.');
                    });
                break;

            case 'tense':
            case 'aspect':
            case 'case':
                this.renderSearchMessage(`Searching ${action} ${value}...`);
                fetch(`/api/search/verb_forms?${action}=${encodeURIComponent(value)}`)
                    .then(res => res.json())
                    .then(data => this.renderSearchResults(data.results || [], `No matches found for ${action} ${value}.`, data.count))
                    .catch(err => {
                        console.error(`${action} search failed`, err);
                        this.renderSearchMessage(`${action} search failed.`);
                    });
                break;

            case 'dependency':
                this.renderSearchMessage(`Searching dependency relation ${value}...`);
                fetch(`/api/search/dependency?relation=${encodeURIComponent(value)}`)
                    .then(res => res.json())
                    .then(data => this.renderSearchResults(data.results || [], `No matches found for dependency relation ${value}.`, data.count))
                    .catch(err => {
                        console.error('Dependency search failed', err);
                        this.renderSearchMessage('Dependency search failed.');
                    });
                break;

            case 'syntax':
                this.renderSearchMessage(`Searching syntactic pattern ${value}...`);
                fetch(`/api/search/syntax?q=${encodeURIComponent(value)}`)
                    .then(res => res.json())
                    .then(data => this.renderSearchResults(data.results || [], 'No syntactic matches found.', data.count))
                    .catch(err => {
                        console.error('Syntax search failed', err);
                        this.renderSearchMessage('Syntax search failed.');
                    });
                break;

            default:
                console.warn(`Unknown search action: ${action}`);
                break;
        }
    },,

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
    },,

    annotateWord(wordEl) {
        this.annotateElement(wordEl);
    },,

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
});
