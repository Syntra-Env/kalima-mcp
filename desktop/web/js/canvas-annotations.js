// ===== Codex Research Canvas - Annotation helpers (minimal, test-safe) =====
// Provides safe stubs so the UI can render without runtime errors during tests.

Object.assign(Canvas, {
    escapeHtml(str = '') {
        return str
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    },

    handleDetailSearch(_action, _value) {
        // Stub: no-op search hook for detail chips
    },

    annotateElement(_el) {
        // Stub: placeholder for annotation flow
    },

    assignStructure(_el) {
        // Stub: placeholder for structure tagging flow
    }
});
