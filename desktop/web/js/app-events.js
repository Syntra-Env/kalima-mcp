// ===== App Event Listeners =====
// DOM event listeners and keyboard shortcuts

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
