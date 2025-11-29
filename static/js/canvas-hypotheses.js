// ===== Codex Research Canvas - Hypotheses & Pronouns =====
// Hypothesis management, pronoun reference tracking, and evidence handling

// Extends the Canvas object
Object.assign(Canvas, {
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
    },,

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
    },,

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
    },,

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
    },,

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
    },,

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
    },,

    async promptEvidence(refId, type) {
        const note = prompt(`Add a ${type} evidence note`);
        if (!note) return;
        await this.addPronounEvidence(refId, type, note);
    },,

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
    },,

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
    },,

    buildPronounLabel(pronoun) {
        const base = pronoun.form || pronoun.token_form || pronoun.pronoun_id;
        const features = pronoun.features ? ` (${pronoun.features})` : '';
        return `${base}${features}`.trim();
    },
});
