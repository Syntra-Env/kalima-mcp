// ===== App Display Functions =====
// Functions for displaying verses, tokens, annotations, and UI updates

function displayVerse(verse) {
    state.currentVerse = verse;

    // Update header
    const surah = verse.surah;
    const verseTitle = document.getElementById('verseTitle');
    if (verseTitle) {
        verseTitle.textContent = `Surah ${surah.name} (${surah.number}) - Ayah ${verse.ayah}`;
    }

    // Display verse text (RTL is automatic in browser!)
    const verseText = document.getElementById('verseText');
    if (verseText) {
        verseText.textContent = verse.text;
    }

    // Render main Quran text view with interactive tokens
    renderQuranText(verse);

    // Display tokens
    displayTokens(verse);

    // Display annotations
    displayAnnotations(verse);

    // Update info panel
    updateInfoPanel(verse);

    // Update layer system with new verse
    if (window.LayerSystem) {
        LayerSystem.setCurrentVerse(verse);
    }
}

function displayTokens(verse) {
    const container = document.getElementById('tokensContainer');
    if (!container) return;

    if (!state.showTokens || !verse.tokens || verse.tokens.length === 0) {
        container.classList.remove('show');
        return;
    }

    container.classList.add('show');
    container.innerHTML = '<h3>Tokens</h3>';

    // Create tokens display
    verse.tokens.forEach(token => {
        const tokenEl = document.createElement('div');
        tokenEl.className = 'token';
        tokenEl.dataset.tokenId = token.id;

        tokenEl.innerHTML = `
            <span class="token-id">${token.id}</span>
            ${token.form}
        `;

        // Click handler
        tokenEl.addEventListener('click', () => {
            tokenEl.classList.toggle('selected');
            toggleTokenSelection(token.id);
            displayTokenDetails(token);
        });

        container.appendChild(tokenEl);

        // Show morphology if enabled
        if (state.showMorphology && token.segments) {
            const morphDiv = document.createElement('div');
            morphDiv.className = 'token-morphology';

            token.segments.forEach(seg => {
                const segDiv = document.createElement('div');
                segDiv.className = 'segment';

                let segHTML = `
                    <span class="segment-id">${seg.id}</span>
                    <span class="segment-type">${seg.type}</span>
                    ${seg.pos}
                `;

                if (seg.root) {
                    segHTML += ` <span style="color: #2c5f2d;">Root: ${seg.root}</span>`;
                }
                if (seg.lemma) {
                    segHTML += ` <span style="color: #97bc62;">Lemma: ${seg.lemma}</span>`;
                }

                segDiv.innerHTML = segHTML;
                morphDiv.appendChild(segDiv);
            });

            container.appendChild(morphDiv);
        }
    });
}

function displayAnnotations(verse) {
    const container = document.getElementById('annotationsContainer');
    if (!container) return;

    if (!state.showAnnotations || !verse.annotations || verse.annotations.length === 0) {
        container.classList.remove('show');
        return;
    }

    container.classList.add('show');
    container.innerHTML = '<h3>Annotations</h3>';

    verse.annotations.forEach(ann => {
        const annEl = document.createElement('div');
        annEl.className = 'annotation';

        let tagsHTML = '';
        if (ann.tags && ann.tags.length > 0) {
            tagsHTML = '<div class="annotation-tags">' +
                ann.tags.map(tag => `<span class="tag">${tag}</span>`).join('') +
                '</div>';
        }

        annEl.innerHTML = `
            <div class="annotation-header">
                <span class="annotation-type">${ann.type}</span>
                <span class="annotation-id">${ann.id}</span>
            </div>
            <div class="annotation-note">${ann.note}</div>
            ${tagsHTML}
        `;

        container.appendChild(annEl);
    });
}

function displayTokenDetails(token) {
    const panel = document.getElementById('detailsPanel');
    if (!panel) return;

    let html = `<h3>Token ${token.id}: <span style="font-family: 'Scheherazade New', 'Amiri', serif; direction: rtl;">${token.form}</span></h3>`;

    if (token.segments && token.segments.length > 0) {
        html += '<div class="segments-detail">';
        token.segments.forEach(seg => {
            html += `
                <div class="detail-item">
                    <span class="detail-label">Segment: </span>${seg.id}<br>
                    <span class="detail-label">Type: </span>${seg.type}<br>
                    <span class="detail-label">POS: </span>${seg.pos}
            `;

            if (seg.root) {
                html += `<br><span class="detail-label">Root: </span>${seg.root}`;
            }
            if (seg.lemma) {
                html += `<br><span class="detail-label">Lemma: </span>${seg.lemma}`;
            }
            if (seg.features) {
                html += `<br><span class="detail-label">Features: </span><small>${seg.features}</small>`;
            }

            html += '</div>';
        });
        html += '</div>';
    }

    panel.innerHTML = html;
}

function toggleTokenSelection(tokenId) {
    const index = state.selectedTokens.indexOf(tokenId);
    if (index > -1) {
        state.selectedTokens.splice(index, 1);
    } else {
        state.selectedTokens.push(tokenId);
    }
}

function updateInfoPanel(verse) {
    const panel = document.getElementById('verseInfo');
    if (!panel) return;
    const surah = verse.surah;

    let html = `
        <div class="stat-item">
            <span class="stat-label">Surah:</span>
            <span class="stat-value" style="font-family: 'Scheherazade New', 'Amiri', serif;">${surah.name} (${surah.number})</span>
        </div>
        <div class="stat-item">
            <span class="stat-label">Ayah:</span>
            <span class="stat-value">${verse.ayah}</span>
        </div>
        <div class="stat-item">
            <span class="stat-label">Tokens:</span>
            <span class="stat-value">${verse.tokens ? verse.tokens.length : 0}</span>
        </div>
        <div class="stat-item">
            <span class="stat-label">Annotations:</span>
            <span class="stat-value">${verse.annotations ? verse.annotations.length : 0}</span>
        </div>
    `;

    panel.innerHTML = html;
}

function displaySearchResults(data) {
    const container = document.getElementById('searchResults');

    if (data.count === 0) {
        container.innerHTML = '<p class="hint">No results found</p>';
        return;
    }

    container.innerHTML = `<p><strong>Results: ${data.count}</strong></p>`;

    data.results.forEach(result => {
        const verse = result.verse;
        const surah = verse.surah;

        const item = document.createElement('div');
        item.className = 'search-result-item';
        item.innerHTML = `
            <div class="search-result-ref">${surah.name} ${surah.number}:${verse.ayah}</div>
            <div class="search-result-text">${verse.text}</div>
        `;

        item.addEventListener('click', () => {
            state.currentIndex = result.index;
            loadVerseByIndex(result.index);
            closeModal('searchModal');
        });

        container.appendChild(item);
    });
}

function showAnnotationModal() {
    // Pre-fill selected tokens if any
    if (state.selectedTokens.length > 0) {
        document.getElementById('targetTokens').value = state.selectedTokens.join(',');
    }
    showModal('annotationModal');
}

function displayTags(tagsData) {
    const container = document.getElementById('tagsContent');

    const tags = tagsData.tags || {};
    const tagNames = Object.keys(tags);

    if (tagNames.length === 0) {
        container.innerHTML = '<p class="hint">No hypotheses yet</p>';
        return;
    }

    let html = '<div>';
    tagNames.forEach(tagName => {
        const tag = tags[tagName];
        const supporting = tag.evidence ? tag.evidence.supporting.length : 0;

        html += `
            <div class="card" style="margin-bottom: 1rem;">
                <h3>${tagName}</h3>
                <p><strong>Status:</strong> ${tag.status}</p>
                <p><strong>Hypothesis:</strong> ${tag.hypothesis}</p>
                <p><strong>Supporting Evidence:</strong> ${supporting}</p>
            </div>
        `;
    });
    html += '</div>';

    container.innerHTML = html;
}

function displayStats(stats) {
    const container = document.getElementById('statsContent');

    let html = `
        <div class="stat-item">
            <span class="stat-label">Total Verses:</span>
            <span class="stat-value">${stats.total_verses}</span>
        </div>
        <div class="stat-item">
            <span class="stat-label">Verses with Tokens:</span>
            <span class="stat-value">${stats.verses_with_tokens}</span>
        </div>
        <div class="stat-item">
            <span class="stat-label">Total Annotations:</span>
            <span class="stat-value">${stats.total_annotations}</span>
        </div>
        <div class="stat-item">
            <span class="stat-label">Hypotheses:</span>
            <span class="stat-value">${stats.total_hypothesis_tags}</span>
        </div>
    `;

    container.innerHTML = html;
}

// ===== Modal Management =====
function showModal(modalId) {
    document.getElementById(modalId).classList.add('show');
}

function closeModal(modalId) {
    document.getElementById(modalId).classList.remove('show');
}

function renderQuranText(verse) {
    const container = document.getElementById('quranText');
    if (!container) return;
    container.innerHTML = '';

    const line = document.createElement('div');
    line.className = 'quran-line';
    line.dir = 'rtl';

    const tokens = verse.tokens && verse.tokens.length ? verse.tokens : [{ id: verse.id || 'v', text: verse.text, segments: [] }];
    tokens.forEach(token => {
        const span = document.createElement('span');
        span.className = 'quran-token';
        span.textContent = token.form || token.text || '';
        span.dataset.tokenId = token.id;

        // Attach primary segment metadata (if present) for hover/detail
        const seg = token.segments && token.segments[0];
        if (seg) {
            if (seg.root) span.dataset.root = seg.root;
            if (seg.pos) span.dataset.pos = seg.pos;
            if (seg.lemma) span.dataset.lemma = seg.lemma;
            if (seg.pattern) span.dataset.pattern = seg.pattern;
            if (seg.verb_form) span.dataset.verbForm = seg.verb_form || seg.verbForm;
        }

        span.title = [
            seg?.root ? `Root: ${seg.root}` : '',
            seg?.pos ? `POS: ${seg.pos}` : '',
        ].filter(Boolean).join(' • ');

        span.addEventListener('mouseenter', () => span.classList.add('hover'));
        span.addEventListener('mouseleave', () => span.classList.remove('hover'));
        span.addEventListener('click', () => {
            if (window.Canvas && typeof Canvas.showElementDetails === 'function') {
                Canvas.showElementDetails(span);
            } else {
                // Fallback: highlight selection
                span.classList.toggle('selected');
            }
        });

        line.appendChild(span);
    });

    container.appendChild(line);
}
