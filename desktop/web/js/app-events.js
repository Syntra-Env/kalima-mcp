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
    const nextBtn = document.getElementById('nextBtn');
    if (nextBtn) nextBtn.addEventListener('click', nextVerse);
    const prevBtn = document.getElementById('prevBtn');
    if (prevBtn) prevBtn.addEventListener('click', prevVerse);

    const goBtn = document.getElementById('goBtn');
    if (goBtn) {
        goBtn.addEventListener('click', () => {
            const surah = parseInt(document.getElementById('surahInput').value);
            const ayah = parseInt(document.getElementById('ayahInput').value);
            if (surah && ayah) {
                loadVerse(surah, ayah);
            }
        });
    }

    // Display options
    const showTokens = document.getElementById('showTokens');
    if (showTokens) {
        showTokens.addEventListener('change', (e) => {
            state.showTokens = e.target.checked;
            if (state.currentVerse) displayTokens(state.currentVerse);
        });
    }

    const showMorphology = document.getElementById('showMorphology');
    if (showMorphology) {
        showMorphology.addEventListener('change', (e) => {
            state.showMorphology = e.target.checked;
            if (state.currentVerse) displayTokens(state.currentVerse);
        });
    }

    const showAnnotations = document.getElementById('showAnnotations');
    if (showAnnotations) {
        showAnnotations.addEventListener('change', (e) => {
            state.showAnnotations = e.target.checked;
            if (state.currentVerse) displayAnnotations(state.currentVerse);
        });
    }

    // Quick search
    let searchTimeout;
    const quickSearch = document.getElementById('quickSearch');
    if (quickSearch) {
        quickSearch.addEventListener('input', (e) => {
            clearTimeout(searchTimeout);
            const query = e.target.value;
            if (query.length > 2) {
                searchTimeout = setTimeout(() => {
                    const searchType = document.getElementById('searchType');
                    const type = searchType ? searchType.value : 'text';
                    performSearch(query, type);
                }, 500);
            }
        });
    }

    // Annotation modal
    const annotateBtn = document.getElementById('annotateBtn');
    if (annotateBtn) annotateBtn.addEventListener('click', showAnnotationModal);
    const annotationForm = document.getElementById('annotationForm');
    if (annotationForm) annotationForm.addEventListener('submit', submitAnnotation);

    // Top nav buttons
    const searchBtn = document.getElementById('searchBtn');
    if (searchBtn) searchBtn.addEventListener('click', () => showModal('searchModal'));
    const tagsBtn = document.getElementById('tagsBtn');
    if (tagsBtn) tagsBtn.addEventListener('click', showTagsModal);
    const statsBtn = document.getElementById('statsBtn');
    if (statsBtn) statsBtn.addEventListener('click', showStatsModal);

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
