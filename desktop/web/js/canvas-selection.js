// ===== Codex Research Canvas - User Interactions (minimal, test-safe) =====
// Lightweight selection and detail helpers to keep the app stable in tests.

Object.assign(Canvas, {
    handleWordClick(_e, el) {
        this.showElementDetails(el);
    },

    handleMorphemeClick(_e, el) {
        this.showElementDetails(el);
    },

    handleLetterClick(_e, el) {
        this.showElementDetails(el);
    },

    selectElement(el) {
        this.toggleSelection(el);
    },

    toggleSelection(element) {
        element.classList.toggle('selected');
        const baseId = element.dataset.segmentId || element.dataset.tokenId ||
                       element.dataset.wordId || element.dataset.position || element.dataset.elementIndex || '';
        const verseKey = `${element.dataset.surah || 's'}:${element.dataset.ayah || 'a'}`;
        const id = `${verseKey}:${baseId}`;
        const label = element.dataset.displayText || element.textContent.trim();
        const type = element.dataset.layer ? element.dataset.layer.toLowerCase() : (element.dataset.segmentId ? 'morpheme' : 'word');

        if (!this.selectedWords) this.selectedWords = [];
        const idx = this.selectedWords.findIndex(e => e.id === id);
        if (idx > -1) {
            this.selectedWords.splice(idx, 1);
        } else {
            this.selectedWords.push({ id, label, type });
        }

        this.updateSelectionInfo();
        this.setTargetFromSelection();
    },

    clearSelection() {
        document.querySelectorAll('.selected').forEach(el => el.classList.remove('selected'));
        this.selectedWords = [];
        this.connectionSource = null;
        this.updateSelectionInfo();
    },

    updateSelectionInfo() {
        const display = document.getElementById('hypTargetDisplay');
        if (!display) return;
        if (!this.selectedWords || this.selectedWords.length === 0) {
            display.textContent = 'No selection';
            return;
        }
        if (this.selectedWords.length === 1) {
            const item = this.selectedWords[0];
            display.textContent = `${item.type.toUpperCase()} ${item.label}`;
        } else {
            const labels = this.selectedWords.map(e => e.label).join(', ');
            display.textContent = `Phrase: ${labels}`;
        }
    },

    setTargetFromSelection() {
        // Minimal stub to avoid runtime errors
    },

    selectRangeFromStartTo(_endElement) {
        // Minimal stub for drag-to-select
    },

    showElementDetails(element) {
        const panel = document.getElementById('elementDetails');
        if (!panel || !element) return;

        const text = element.dataset.displayText || element.textContent.trim();
        const type = element.dataset.type || element.dataset.layer || '';
        const pos = element.dataset.pos || '';
        const root = element.dataset.root || '';
        const pattern = element.dataset.pattern || '';
        const lemma = element.dataset.lemma || '';
        const structure = element.dataset.structureCategoryLabel || '';
        const verbForm = element.dataset.verbForm || '';
        const person = element.dataset.person || '';
        const number = element.dataset.number || '';
        const gender = element.dataset.gender || '';
        const voice = element.dataset.voice || '';
        const mood = element.dataset.mood || '';
        const case_ = element.dataset.case || '';
        const tense = element.dataset.tense || '';

        const chips = [];
        if (root) chips.push(`Root: ${root}`);
        if (pattern) chips.push(`Pattern: ${pattern}`);
        if (pos) chips.push(`POS: ${pos}`);
        if (lemma) chips.push(`Lemma: ${lemma}`);
        if (verbForm) chips.push(`Form: ${verbForm}`);
        if (voice) chips.push(`Voice: ${voice}`);
        if (mood) chips.push(`Mood: ${mood}`);
        if (tense) chips.push(`Tense: ${tense}`);
        if (person) chips.push(`Person: ${person}`);
        if (number) chips.push(`Number: ${number}`);
        if (gender) chips.push(`Gender: ${gender}`);
        if (case_) chips.push(`Case: ${case_}`);
        if (structure) chips.push(`Structure: ${structure}`);

        panel.innerHTML = `
            <div class="detail-layer-info">
                <span class="detail-layer-label">Layer: ${type || 'unknown'}</span>
            </div>
            <div class="detail-text-interactive">${this.escapeHtml ? this.escapeHtml(text) : text}</div>
            <div class="detail-meta">
                ${chips.length ? chips.map(c => `<span class="detail-chip">${this.escapeHtml ? this.escapeHtml(c) : c}</span>`).join('') : '<span class="hint">No metadata.</span>'}
            </div>
        `;
    }
});
