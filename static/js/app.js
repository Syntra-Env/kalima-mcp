// ===== State Management =====
const state = {
    currentIndex: 0,
    currentVerse: null,
    selectedTokens: [],
    showTokens: true,
    showMorphology: false,
    showAnnotations: true
};

// ===== API Functions =====
async function fetchVerseByIndex(index) {
    const response = await fetch(`/api/verse/index/${index}`);
    return await response.json();
}

async function fetchVerse(surah, ayah) {
    const response = await fetch(`/api/verse/${surah}/${ayah}`);
    return await response.json();
}

async function searchVerses(query, type = 'text') {
    const response = await fetch(`/api/search?q=${encodeURIComponent(query)}&type=${type}`);
    return await response.json();
}

async function createAnnotation(surah, ayah, annotation) {
    const response = await fetch(`/api/annotations/${surah}/${ayah}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(annotation)
    });
    return await response.json();
}

async function fetchTags() {
    const response = await fetch('/api/tags');
    return await response.json();
}

async function fetchStats() {
    const response = await fetch('/api/stats');
    return await response.json();
}

// ===== Display Functions =====
function displayVerse(verse) {
    state.currentVerse = verse;

    // Update header
    const surah = verse.surah;
    document.getElementById('verseTitle').textContent =
        `Surah ${surah.name} (${surah.number}) - Ayah ${verse.ayah}`;

    // Display verse text (RTL is automatic in browser!)
    document.getElementById('verseText').textContent = verse.text;

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

// ===== Navigation =====
async function loadVerseByIndex(index) {
    try {
        const verse = await fetchVerseByIndex(index);
        if (verse.error) {
            alert('Verse not found');
            return;
        }
        state.currentIndex = index;
        displayVerse(verse);
    } catch (error) {
        console.error('Error loading verse:', error);
        alert('Error loading verse');
    }
}

async function loadVerse(surah, ayah) {
    try {
        const verse = await fetchVerse(surah, ayah);
        if (verse.error) {
            alert('Verse not found');
            return;
        }
        displayVerse(verse);
    } catch (error) {
        console.error('Error loading verse:', error);
        alert('Error loading verse');
    }
}

function nextVerse() {
    loadVerseByIndex(state.currentIndex + 1);
}

function prevVerse() {
    if (state.currentIndex > 0) {
        loadVerseByIndex(state.currentIndex - 1);
    }
}

// ===== Search =====
async function performSearch(query, type = 'text') {
    if (!query.trim()) return;

    try {
        const results = await searchVerses(query, type);
        displaySearchResults(results);
    } catch (error) {
        console.error('Search error:', error);
        alert('Search error');
    }
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

// ===== Annotations =====
function showAnnotationModal() {
    // Pre-fill selected tokens if any
    if (state.selectedTokens.length > 0) {
        document.getElementById('targetTokens').value = state.selectedTokens.join(',');
    }
    showModal('annotationModal');
}

async function submitAnnotation(event) {
    event.preventDefault();

    if (!state.currentVerse) {
        alert('No verse loaded');
        return;
    }

    const annotation = {
        type: document.getElementById('annotationType').value,
        target_token_ids: document.getElementById('targetTokens').value.split(',').map(s => s.trim()),
        note: document.getElementById('annotationNote').value,
        tags: document.getElementById('annotationTags').value
            .split(',')
            .map(s => s.trim())
            .filter(s => s.length > 0),
        scope: 'token',
        status: 'hypothesis',
        refs: []
    };

    try {
        const surah = state.currentVerse.surah.number;
        const ayah = state.currentVerse.ayah;

        await createAnnotation(surah, ayah, annotation);
        alert('Annotation saved successfully');

        // Reload verse to show new annotation
        loadVerse(surah, ayah);
        closeModal('annotationModal');

        // Reset form
        document.getElementById('annotationForm').reset();
        state.selectedTokens = [];
    } catch (error) {
        console.error('Error creating annotation:', error);
        alert('Error saving annotation');
    }
}

// ===== Tags/Hypotheses =====
async function showTagsModal() {
    showModal('tagsModal');

    try {
        const tags = await fetchTags();
        displayTags(tags);
    } catch (error) {
        console.error('Error loading tags:', error);
    }
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

// ===== Stats =====
async function showStatsModal() {
    showModal('statsModal');

    try {
        const stats = await fetchStats();
        displayStats(stats);
    } catch (error) {
        console.error('Error loading stats:', error);
    }
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

// ===== Event Listeners =====
document.addEventListener('DOMContentLoaded', () => {
    // Initialize Layer System
    if (window.LayerSystem) {
        LayerSystem.init();
    }

    // Load first verse
    loadVerseByIndex(0);

    // Navigation buttons
    document.getElementById('nextBtn').addEventListener('click', nextVerse);
    document.getElementById('prevBtn').addEventListener('click', prevVerse);

    document.getElementById('goBtn').addEventListener('click', () => {
        const surah = parseInt(document.getElementById('surahInput').value);
        const ayah = parseInt(document.getElementById('ayahInput').value);
        if (surah && ayah) {
            loadVerse(surah, ayah);
        }
    });

    // Display options
    document.getElementById('showTokens').addEventListener('change', (e) => {
        state.showTokens = e.target.checked;
        if (state.currentVerse) displayTokens(state.currentVerse);
    });

    document.getElementById('showMorphology').addEventListener('change', (e) => {
        state.showMorphology = e.target.checked;
        if (state.currentVerse) displayTokens(state.currentVerse);
    });

    document.getElementById('showAnnotations').addEventListener('change', (e) => {
        state.showAnnotations = e.target.checked;
        if (state.currentVerse) displayAnnotations(state.currentVerse);
    });

    // Quick search
    let searchTimeout;
    document.getElementById('quickSearch').addEventListener('input', (e) => {
        clearTimeout(searchTimeout);
        const query = e.target.value;
        if (query.length > 2) {
            searchTimeout = setTimeout(() => {
                const type = document.getElementById('searchType').value;
                performSearch(query, type);
            }, 500);
        }
    });

    // Annotation modal
    document.getElementById('annotateBtn').addEventListener('click', showAnnotationModal);
    document.getElementById('annotationForm').addEventListener('submit', submitAnnotation);

    // Top nav buttons
    document.getElementById('searchBtn').addEventListener('click', () => showModal('searchModal'));
    document.getElementById('tagsBtn').addEventListener('click', showTagsModal);
    document.getElementById('statsBtn').addEventListener('click', showStatsModal);

    // Modal close buttons
    document.querySelectorAll('.close').forEach(closeBtn => {
        closeBtn.addEventListener('click', () => {
            closeBtn.closest('.modal').classList.remove('show');
        });
    });

    // Close modal on outside click
    window.addEventListener('click', (e) => {
        if (e.target.classList.contains('modal')) {
            e.target.classList.remove('show');
        }
    });

    // Keyboard shortcuts
    document.addEventListener('keydown', (e) => {
        // Only if not in input/textarea
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;

        switch(e.key) {
            case 'ArrowLeft':
            case 'n':
                nextVerse();
                break;
            case 'ArrowRight':
            case 'p':
                prevVerse();
                break;
            case '/':
                e.preventDefault();
                document.getElementById('quickSearch').focus();
                break;
        }
    });
});
