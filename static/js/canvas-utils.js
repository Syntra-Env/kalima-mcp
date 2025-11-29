// ===== Codex Research Canvas - Utility Functions =====
// Helper functions for text manipulation, escaping, highlighting, and DOM operations

// Extends the Canvas object with utility methods
Object.assign(Canvas, {
    // Build verse reference string
    buildVerseKey(verse) {
        if (!verse) return null;
        const ayah = verse.ayah;
        let surahNum = null;
        if (verse.surah && typeof verse.surah === 'object' && 'number' in verse.surah) {
            surahNum = verse.surah.number;
        } else if (typeof verse.surah === 'number' || typeof verse.surah === 'string') {
            surahNum = verse.surah;
        }
        if (surahNum == null || ayah == null) return null;
        return `${surahNum}:${ayah}`;
    },

    // Build verse DOM ID
    buildVerseId(surah, ayah) {
        return `verse-${surah}-${ayah}`;
    },

    // Count unique ayahs in search results
    countUniqueAyahs(results) {
        const set = new Set();
        (results || []).forEach(r => {
            const key = this.buildVerseKey(r.verse);
            if (key) {
                set.add(key);
            }
        });
        return set.size;
    },

    // Count total matches in search results
    countTotalMatches(results, totalCountOverride = null) {
        if (typeof totalCountOverride === 'number') return totalCountOverride;
        let total = 0;
        (results || []).forEach(r => {
            const cnt = r.match_count || r.matchCount || 1;
            total += cnt;
        });
        return total;
    },

    // Highlight search term in text
    highlightMatch(text, term, result) {
        const source = text || '';
        const regexStr = result?.matchRegex;
        if (regexStr) {
            try {
                const regex = new RegExp(regexStr, 'gu');
                let out = '';
                let last = 0;
                let match;
                while ((match = regex.exec(source)) !== null) {
                    out += this.escapeHtml(source.slice(last, match.index));
                    out += `<mark>${this.escapeHtml(match[0])}</mark>`;
                    last = match.index + match[0].length;
                    if (match.index === regex.lastIndex) regex.lastIndex++; // avoid zero-length loops
                }
                out += this.escapeHtml(source.slice(last));
                return out || this.escapeHtml(source);
            } catch (e) {
                console.warn('Failed to apply matchRegex, falling back to term highlighting', e);
            }
        }

        const needle = (term || result?.matchTerm || result?.match || '').trim();
        if (!needle) {
            return this.escapeHtml(source);
        }
        try {
            const regex = new RegExp(this.escapeForRegex(needle), 'gi');
            let out = '';
            let last = 0;
            let match;
            while ((match = regex.exec(source)) !== null) {
                out += this.escapeHtml(source.slice(last, match.index));
                out += `<mark>${this.escapeHtml(match[0])}</mark>`;
                last = match.index + match[0].length;
            }
            out += this.escapeHtml(source.slice(last));
            return out || this.escapeHtml(source);
        } catch (e) {
            console.warn('highlightMatch failed, falling back to plain text', e);
            return this.escapeHtml(source);
        }
    },

    // Escape string for use in regex
    escapeForRegex(str) {
        return (str || '').replace(/[-/\\^$*+?.()|[\]{}]/g, '\\$&');
    },

    // Escape HTML special characters
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

    // Get verse data from DOM element
    getVerseFromElement(element) {
        const surahNumber = parseInt(element.dataset.surah, 10);
        const ayahNumber = parseInt(element.dataset.ayah, 10);
        if (!surahNumber || !ayahNumber) return null;
        const surahData = this.surahCache[surahNumber] ||
            (this.currentSurahNumber === surahNumber ? this.currentSurahData : null);
        if (!surahData) return null;
        return surahData.verses.find(v => v.surah.number === surahNumber && v.ayah === ayahNumber) || null;
    },

    // Apply verse metadata to DOM element
    applyVerseMetadata(element, verse) {
        if (!verse || !element) return;
        element.dataset.surah = verse.surah.number;
        element.dataset.ayah = verse.ayah;
        element.dataset.surahName = verse.surah.name;
    },

    // Build tooltip content for elements
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

    // Log action to history
    logAction(action) {
        if (!action) return;
        this.actionHistory.unshift(action);
        this.actionHistory = this.actionHistory.slice(0, 15);
        const historyEl = document.getElementById('actionHistory');
        if (!historyEl) return;

        const items = this.actionHistory.map(entry => {
            const ref = entry.ref ? `<span class="ref">${this.escapeHtml(entry.ref)}</span>` : '';
            const details = entry.details ? `<span class="meta">${this.escapeHtml(entry.details)}</span>` : '';
            return `<li>${ref}${details ? ' | ' + details : ''}</li>`;
        }).join('');
        historyEl.innerHTML = `<ul>${items}</ul>`;
    },

    // Log navigation to verse
    logNavigation(surah, ayah) {
        if (!surah || !ayah) return;
        const latest = this.navJourney[0];
        if (latest && latest.surah === surah && latest.ayah === ayah) {
            return;
        }
        this.navJourney.unshift({ surah, ayah, ts: Date.now() });
        this.navJourney = this.navJourney.slice(0, 30);
        this.renderNavMap();
    },

    // Render navigation map
    renderNavMap() {
        const map = document.getElementById('navMap');
        if (!map) return;
        if (!this.navJourney.length) {
            map.innerHTML = '<p class="hint">No navigation history yet.</p>';
            return;
        }
        map.innerHTML = '';
        this.navJourney.forEach(node => {
            const branch = document.createElement('div');
            branch.className = 'branch';

            const line = document.createElement('div');
            line.className = 'branch-line';
            branch.appendChild(line);

            const branchNode = document.createElement('div');
            branchNode.className = 'branch-node';
            const button = document.createElement('button');
            button.type = 'button';
            button.className = 'node-item';
            button.textContent = `S${node.surah}  Ayah ${node.ayah}`;
            button.title = `Jump to ${node.surah}:${node.ayah}`;
            button.addEventListener('click', () => this.navigateToVerse(node.surah, node.ayah));
            branchNode.appendChild(button);

            branch.appendChild(branchNode);
            map.appendChild(branch);
        });
    },

    // Adjust detail zoom level
    adjustDetailZoom(delta) {
        this.detailZoom = Math.max(0.6, Math.min(1.6, (this.detailZoom || 1) + delta));
        const panel = document.getElementById('patternPanel');
        if (panel) {
            panel.style.setProperty('--detail-zoom', this.detailZoom.toString());
        }
    },

    // Tooltip methods (disabled in current implementation)
    showElementTooltip() {},
    positionTooltip() {},
    hideTextTooltip() {}
});
