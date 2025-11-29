// ===== Codex Research Canvas - Search Functions =====
// Root search, morphological search, syntactic search, and library functions

// Extends the Canvas object
Object.assign(Canvas, {
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
    },,

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
    },,

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
    },,

    async performRootSearch(root) {
        if (!root) {
            this.renderSearchMessage('Select a root to explore.');
            return;
        }
        try {
            this.renderSearchMessage(`Searching for root ${root}...`);
            const response = await fetch(`/api/search/roots?root=${encodeURIComponent(root)}`);
            const data = await response.json();
            const results = (data.results || []).map(r => ({ ...r, matchTerm: root }));
            this.renderSearchResults(results, `No occurrences found for root ${root}.`, data.count);
        } catch (error) {
            console.error('Root search failed:', error);
            this.renderSearchMessage('Root search failed. Please try again.');
        }
    },,

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
            if (!response.ok) {
                throw new Error(`Morphology search failed (${response.status})`);
            }
            const data = await response.json();
            const results = (data.results || []).map(r => ({ ...r, matchTerm: query }));
            this.renderSearchResults(results, 'No matches for the selected morphological pattern.', data.count);
        } catch (error) {
            console.error('Morphology search failed:', error);
            this.renderSearchMessage('Morphology search failed. Please try again.');
        }
    },,

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
            if (!response.ok) {
                throw new Error(`Syntax search failed (${response.status})`);
            }
            const data = await response.json();
            const results = (data.results || []).map(r => ({ ...r, matchTerm: query }));
            this.renderSearchResults(results, 'No matches for the selected syntactic pattern.', data.count);
        } catch (error) {
            console.error('Syntax search failed:', error);
            this.renderSearchMessage('Syntax search failed. Please try again.');
        }
    },,

    async handleLibrarySearch() {
        const input = document.getElementById('librarySearchInput');
        if (!input || !input.value.trim()) {
            this.renderSearchMessage('Enter a query to search the library.');
            return;
        }

        const query = input.value.trim();
        try {
            this.renderSearchMessage(`Searching library for "${this.escapeHtml(query)}"...`);
            const response = await fetch(`/api/library_search?q=${encodeURIComponent(query)}`);
            const data = await response.json();
            this.renderLibraryResults(data.results || [], query);
        } catch (error) {
            console.error('Library search failed:', error);
            this.renderSearchMessage('Library search failed. Please try again.');
        }
    },,

    renderSearchResults(results, emptyMessage = 'No matches found.', totalCount = null) {
        const container = document.getElementById('quranText');
        if (!container) return;
        const normalized = (results || []).map(r => ({
            ...r,
            matchTerm: r.matchTerm || r.match_term || r.match || '',
            matchRegex: r.matchRegex || r.match_regex || null
        }));
        this.currentSearchResults = normalized;
        container.innerHTML = '';

        if (!normalized.length) {
            container.innerHTML = `<p class="hint">${this.escapeHtml(emptyMessage)}</p>`;
            return;
        }

        const summary = document.createElement('div');
        summary.className = 'search-summary';
        const ayahCount = this.countUniqueAyahs(normalized);
        const matchCount = this.countTotalMatches(normalized, totalCount);
        const showingLabel = matchCount > normalized.length ? ` (showing ${normalized.length})` : '';
        summary.textContent = `Results: ${matchCount} match${matchCount === 1 ? '' : 'es'}${showingLabel} in ${ayahCount} ayah${ayahCount === 1 ? '' : 's'}.`;
        container.appendChild(summary);

        const resultWrapper = document.createElement('div');
        resultWrapper.className = 'search-results-main';

        this.currentSearchResults.slice(0, 150).forEach(result => {
            const verse = result.verse;
            if (!verse) return;
            const item = document.createElement('div');
            item.className = 'search-result-item';
            const text = this.highlightMatch(verse.text || '', (result.matchTerm || ''), result);
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
    },,

    renderSearchMessage(message) {
        const container = document.getElementById('quranText');
        if (!container) return;
        this.currentSearchResults = null;
        container.innerHTML = `<p class="hint">${this.escapeHtml(message)}</p>`;
    },,

    renderLibraryResults(results, query) {
        const container = document.getElementById('searchResults');
        if (container) {
            this.openPatternPanel();
            if (!results || results.length === 0) {
                container.innerHTML = `<p class="hint">No matches in data/ for "${this.escapeHtml(query)}".</p>`;
            } else {
                container.innerHTML = '';
                results.slice(0, 30).forEach(r => {
                    const row = document.createElement('div');
                    row.className = 'search-result-item';
                    row.innerHTML = `<div class="search-result-ref">${this.escapeHtml(r.path)}:${this.escapeHtml(String(r.line))}</div><div class="search-result-text">${this.escapeHtml(r.snippet || '')}</div>`;
                    container.appendChild(row);
                });
            }
        }

        if (!results || results.length === 0) {
            this.renderSearchMessage(`No matches in data/ for "${this.escapeHtml(query)}".`);
            return;
        }

        this.renderSearchResults(results.map(r => ({
            verse: { surah: { name: 'Data' , number: ''}, ayah: r.line, text: `${r.path}: ${r.snippet}` },
            match: 'Library hit',
            matchTerm: query
        })), 'No matches in data');
    },,

    loadNotesList() {
        const list = document.getElementById('notesList');
        if (!list) return;
        fetch('/api/notes')
            .then(res => res.json())
            .then(data => {
                const notes = data.notes || [];
                if (!notes.length) {
                    list.innerHTML = '<p class="hint">No notes found.</p>';
                    return;
                }
                const ul = document.createElement('ul');
                notes.forEach(n => {
                    const li = document.createElement('li');
                    li.className = 'note-item';
                    li.innerHTML = `<strong>${this.escapeHtml(n.title || n.path)}</strong><div class="note-snippet">${this.escapeHtml(n.snippet || '')}</div>`;
                    li.addEventListener('click', () => {
                        this.loadNoteContent(n.path, n.title || n.path);
                    });
                    ul.appendChild(li);
                });
                list.innerHTML = '';
                list.appendChild(ul);
            })
            .catch(() => {
                list.innerHTML = '<p class="hint">Unable to load notes.</p>';
            });
    },,

    loadNoteContent(path, title = '') {
        const panel = document.getElementById('searchResults');
        if (panel) {
            panel.innerHTML = `<p class="hint">Loading note ${this.escapeHtml(title)}...</p>`;
            this.openPatternPanel();
        }
        fetch(`/api/notes/content?path=${encodeURIComponent(path)}`)
            .then(res => res.json())
            .then(data => {
                const content = data.content || '';
                if (panel) {
                    panel.innerHTML = `<h4>${this.escapeHtml(title || path)}</h4><pre class="note-content">${this.escapeHtml(content)}</pre>`;
                } else {
                    this.renderSearchMessage(content);
                }
            })
            .catch(() => {
                if (panel) {
                    panel.innerHTML = '<p class="hint">Failed to load note.</p>';
                }
            });
    },
});
