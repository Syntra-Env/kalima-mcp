// ===== Codex Research Canvas - Main Entry Point =====
// Initializes the Canvas object and sets up the application

// Canvas object with initial state
const Canvas = {
    // State
    currentLayer: 'sentence',
    currentDetailLayer: 'verse',
    currentVerse: null,
    selectedStructureCategory: null,
    appMode: 'read',
    mode: 'select',
    selectedWords: [],
    surahSummaries: [],
    surahCache: {},
    currentSurahNumber: null,
    currentSurahData: null,
    currentAyahNumber: null,
    rootOptions: [],
    morphPatterns: [],
    syntaxPatterns: [],
    connectionSource: null,
    connections: { internal: [], external: [] },
    pronounData: null,
    actionHistory: [],
    expandedSurahs: new Set(),
    navJourney: [],
    currentHypotheses: [],
    currentSearchResults: null,
    patternSegments: [],
    isDragging: false,
    dragStartElement: null,
    dragSelectionActive: false,
    translations: [],
    editingSegment: null,
    tooltipEl: null,
    detailZoom: 1
};

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    Canvas.init();
});

// Export for use in other scripts
window.Canvas = Canvas;
