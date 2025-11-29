// ===== Codex Research Canvas - Surah Navigation =====
// Functions for loading, navigating, and displaying Surahs and Ayahs

// Extends the Canvas object
Object.assign(Canvas, {
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
    },,

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
    },,

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
    },,

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
    },,

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
    },,

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
    },,

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
    },,

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
});
