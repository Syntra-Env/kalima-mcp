// ===== API base override =====
const API_BASE = window.CodexAPIBase || '';
const __originalFetch = window.fetch.bind(window);
window.fetch = (input, init) => {
    if (typeof input === 'string' && input.startsWith('/api')) {
        input = API_BASE + input;
    }
    return __originalFetch(input, init);
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

// ===== Annotations =====
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
