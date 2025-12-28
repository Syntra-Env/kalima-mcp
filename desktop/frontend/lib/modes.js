/**
 * Mode Manager for Kalima
 *
 * Manages application modes: Browse, Search (Query), Annotate
 * Each mode changes user interaction behavior and cursor style.
 */

export const MODES = {
    BROWSE: 'browse',      // Default reading mode
    SEARCH: 'search',      // Concordance query mode
    ANNOTATE: 'annotate',  // Annotation/interpretation mode
};

// Mode metadata including icons and cursor styles
export const MODE_CONFIG = {
    [MODES.BROWSE]: {
        id: MODES.BROWSE,
        name: 'Browse',
        icon: '📖',
        shortcut: 'B',
        cursor: 'default',
        description: 'Read and explore the text',
    },
    [MODES.SEARCH]: {
        id: MODES.SEARCH,
        name: 'Search',
        icon: '🔍',
        shortcut: 'S',
        cursor: 'crosshair', // Will be replaced with custom cursor
        description: 'Build concordance queries by clicking tokens',
    },
    [MODES.ANNOTATE]: {
        id: MODES.ANNOTATE,
        name: 'Annotate',
        icon: '✒️',
        shortcut: 'A',
        cursor: 'text', // Will be replaced with custom cursor
        description: 'Add interpretive annotations to tokens',
    },
};

class ModeManager {
    constructor() {
        this.currentMode = MODES.BROWSE;
        this.listeners = new Set();
        this.previousMode = null;
    }

    /**
     * Get current mode
     */
    getMode() {
        return this.currentMode;
    }

    /**
     * Get mode configuration
     */
    getModeConfig(mode = this.currentMode) {
        return MODE_CONFIG[mode];
    }

    /**
     * Check if in specific mode
     */
    isMode(mode) {
        return this.currentMode === mode;
    }

    /**
     * Switch to a new mode
     */
    setMode(mode) {
        if (!MODE_CONFIG[mode]) {
            console.warn(`Unknown mode: ${mode}`);
            return false;
        }

        if (this.currentMode === mode) {
            return false; // Already in this mode
        }

        this.previousMode = this.currentMode;
        this.currentMode = mode;
        this._notifyListeners();
        this._updateCursor();
        return true;
    }

    /**
     * Toggle between current mode and browse mode
     */
    toggleMode(mode) {
        if (this.currentMode === mode) {
            this.setMode(MODES.BROWSE);
        } else {
            this.setMode(mode);
        }
    }

    /**
     * Return to previous mode
     */
    restorePreviousMode() {
        if (this.previousMode) {
            this.setMode(this.previousMode);
        }
    }

    /**
     * Subscribe to mode changes
     */
    onChange(callback) {
        this.listeners.add(callback);
        return () => this.listeners.delete(callback);
    }

    /**
     * Notify all listeners of mode change
     */
    _notifyListeners() {
        const config = this.getModeConfig();
        this.listeners.forEach(callback => {
            try {
                callback(this.currentMode, config);
            } catch (err) {
                console.error('Mode change listener error:', err);
            }
        });
    }

    /**
     * Update document cursor based on mode
     */
    _updateCursor() {
        const config = this.getModeConfig();
        document.body.dataset.mode = this.currentMode;

        // Custom cursor classes are applied via CSS
        document.body.classList.remove('mode-browse', 'mode-search', 'mode-annotate');
        document.body.classList.add(`mode-${this.currentMode}`);
    }
}

// Singleton instance
export const modeManager = new ModeManager();
