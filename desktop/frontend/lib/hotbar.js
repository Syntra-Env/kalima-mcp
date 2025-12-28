/**
 * Hotbar Component for Kalima
 *
 * RPG-style action bar with mode icons for switching between
 * Browse, Search, and Annotate modes. Uses Tailwind CSS.
 */

import { modeManager, MODES, MODE_CONFIG } from './modes.js';
import { annotationLayerManager } from './annotations/annotation-layers.js';
import { layerSelector } from './annotations/layer-selector.js';
import { LAYERS, ANNOTATION_LAYER_INDEX } from './layers/definitions.js';

class Hotbar {
    constructor() {
        this.element = null;
        this.buttons = new Map();
        this.layerIndicator = null;
        this.layerDropdown = null;
        this.annotationLayerBtn = null;
        this.annotationLayerIndicator = null;
        this.onLayerChange = null; // Callback for layer changes
    }

    /**
     * Initialize the hotbar and append to DOM
     */
    init(container = document.body) {
        this.element = document.createElement('div');
        this.element.id = 'hotbar';
        // Tailwind classes for the hotbar container
        this.element.className = 'fixed bottom-16 left-1/2 -translate-x-1/2 flex items-center gap-2 px-4 py-2 bg-gradient-to-b from-zinc-800/95 to-zinc-900/98 border border-kalima-accent/30 rounded-lg shadow-lg shadow-black/50 backdrop-blur-sm z-50';

        // Create mode buttons
        Object.values(MODE_CONFIG).forEach((config, index) => {
            const button = this._createModeButton(config, index + 1);
            this.buttons.set(config.id, button);
            this.element.appendChild(button);
        });

        // Add separator
        const separator = document.createElement('div');
        separator.className = 'w-px h-8 bg-gradient-to-b from-transparent via-white/20 to-transparent mx-2';
        this.element.appendChild(separator);

        // Add layer indicator (clickable with dropdown)
        const layerContainer = document.createElement('div');
        layerContainer.className = 'relative';

        this.layerIndicator = document.createElement('button');
        this.layerIndicator.className = 'flex flex-col items-center px-3 py-1 text-xs text-zinc-500 hover:bg-zinc-700/50 rounded cursor-pointer transition-colors';
        this.layerIndicator.title = 'Click to switch layers (or use Alt+O/R/L/P)';
        this.layerIndicator.innerHTML = '<span class="text-[10px] uppercase tracking-wide text-zinc-600">Layer</span><span class="layer-name text-kalima-search font-medium flex items-center gap-1">Original <span class="text-zinc-500">▼</span></span>';
        this.layerIndicator.addEventListener('click', (e) => {
            e.stopPropagation();
            this._toggleLayerDropdown();
        });
        layerContainer.appendChild(this.layerIndicator);

        // Create layer dropdown
        this._createLayerDropdown(layerContainer);

        this.element.appendChild(layerContainer);

        // Add annotation layer selector (hidden by default, shown in annotate mode)
        this.annotationLayerBtn = document.createElement('button');
        this.annotationLayerBtn.id = 'annotation-layer-btn';
        this.annotationLayerBtn.className = 'hidden items-center gap-2 px-3 py-1.5 bg-zinc-800/80 border border-zinc-600/50 rounded-md text-xs text-zinc-400 hover:bg-zinc-700/90 hover:border-kalima-annotate/50 hover:text-zinc-200 transition-all';
        this._updateAnnotationLayerButton();
        this.annotationLayerBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            layerSelector.toggle(this.annotationLayerBtn);
        });
        this.element.appendChild(this.annotationLayerBtn);

        // Add keyboard hint
        const hint = document.createElement('div');
        hint.className = 'text-[10px] text-zinc-600 pl-3 border-l border-white/10';
        hint.textContent = '1-3 or B/S/A';
        this.element.appendChild(hint);

        container.appendChild(this.element);

        // Initialize layer selector
        layerSelector.init(container);
        layerSelector.onSelect((layer) => {
            this._updateAnnotationLayerButton();
        });

        // Subscribe to annotation layer changes
        annotationLayerManager.onChange(() => {
            this._updateAnnotationLayerButton();
        });

        // Subscribe to mode changes
        modeManager.onChange((mode, config) => {
            this._updateActiveButton(mode);
            this._updateAnnotationModeUI(mode);
        });

        // Set up keyboard shortcuts
        this._setupKeyboardShortcuts();

        // Initialize with current mode
        this._updateActiveButton(modeManager.getMode());

        return this;
    }

    /**
     * Create a mode button with Tailwind classes
     */
    _createModeButton(config, slot) {
        const button = document.createElement('button');
        button.className = this._getButtonClasses(false);
        button.dataset.mode = config.id;
        button.title = `${config.name} (${config.shortcut} or ${slot})\n${config.description}`;

        // Icon
        const icon = document.createElement('span');
        icon.className = 'text-xl leading-none';
        icon.textContent = config.icon;
        button.appendChild(icon);

        // Slot number
        const slotNum = document.createElement('span');
        slotNum.className = 'absolute bottom-0.5 right-1 text-[10px] font-mono text-white/40';
        slotNum.textContent = slot;
        button.appendChild(slotNum);

        // Click handler
        button.addEventListener('click', () => {
            modeManager.toggleMode(config.id);
        });

        return button;
    }

    /**
     * Get button classes based on active state
     */
    _getButtonClasses(isActive) {
        const base = 'relative w-12 h-12 flex flex-col items-center justify-center rounded-md cursor-pointer transition-all duration-150 focus:outline-none';
        if (isActive) {
            return `${base} bg-gradient-to-b from-kalima-accent/30 to-kalima-accent/15 border-2 border-kalima-accent text-kalima-accent shadow-lg shadow-kalima-accent/20`;
        }
        return `${base} bg-gradient-to-b from-zinc-700/80 to-zinc-800/90 border-2 border-zinc-600/50 text-zinc-400 hover:from-zinc-600/90 hover:to-zinc-700/95 hover:border-kalima-accent/50 hover:text-zinc-200 hover:-translate-y-0.5`;
    }

    /**
     * Update which button shows as active
     */
    _updateActiveButton(activeMode) {
        this.buttons.forEach((button, mode) => {
            const isActive = mode === activeMode;
            button.className = this._getButtonClasses(isActive);
            // Update slot number styling
            const slotNum = button.querySelector('span:last-child');
            if (slotNum) {
                slotNum.className = isActive
                    ? 'absolute bottom-0.5 right-1 text-[10px] font-mono text-kalima-accent/70'
                    : 'absolute bottom-0.5 right-1 text-[10px] font-mono text-white/40';
            }
        });
    }

    /**
     * Update layer indicator
     */
    updateLayerIndicator(layerName) {
        if (this.layerIndicator) {
            const nameSpan = this.layerIndicator.querySelector('.layer-name');
            if (nameSpan) {
                nameSpan.innerHTML = `${layerName} <span class="text-zinc-500">▼</span>`;
            }
        }
    }

    /**
     * Create layer dropdown menu
     */
    _createLayerDropdown(container) {
        this.layerDropdown = document.createElement('div');
        this.layerDropdown.className = 'absolute bottom-full left-1/2 -translate-x-1/2 mb-2 bg-zinc-800 border border-zinc-600 rounded-lg shadow-xl hidden z-50 min-w-[180px] max-h-[300px] overflow-y-auto';

        // Group layers by category
        const searchableLayers = LAYERS.filter(l => l.id !== ANNOTATION_LAYER_INDEX);

        searchableLayers.forEach((layer, idx) => {
            const item = document.createElement('button');
            item.className = 'w-full px-3 py-2 text-left text-sm text-zinc-300 hover:bg-zinc-700 hover:text-white transition-colors flex items-center gap-2';
            item.dataset.layerIndex = layer.id;

            // Add keyboard shortcut hint for common layers
            const shortcuts = { 0: 'Alt+O', 1: 'Alt+R', 2: 'Alt+L', 3: 'Alt+P', 5: 'Alt+C', 6: 'Alt+G' };
            const shortcut = shortcuts[layer.id] || '';

            item.innerHTML = `
                <span class="flex-1">${layer.name}</span>
                ${shortcut ? `<span class="text-xs text-zinc-500">${shortcut}</span>` : ''}
            `;

            item.addEventListener('click', (e) => {
                e.stopPropagation();
                this._hideLayerDropdown();
                if (this.onLayerChange) {
                    this.onLayerChange(layer.id);
                }
            });

            this.layerDropdown.appendChild(item);

            // Add separator after Original Arabic
            if (idx === 0) {
                const sep = document.createElement('div');
                sep.className = 'border-t border-zinc-600 my-1';
                this.layerDropdown.appendChild(sep);
            }
        });

        container.appendChild(this.layerDropdown);

        // Close dropdown when clicking outside
        document.addEventListener('click', () => this._hideLayerDropdown());
    }

    /**
     * Toggle layer dropdown visibility
     */
    _toggleLayerDropdown() {
        if (!this.layerDropdown) return;
        const isHidden = this.layerDropdown.classList.contains('hidden');
        if (isHidden) {
            this.layerDropdown.classList.remove('hidden');
        } else {
            this._hideLayerDropdown();
        }
    }

    /**
     * Hide layer dropdown
     */
    _hideLayerDropdown() {
        if (this.layerDropdown) {
            this.layerDropdown.classList.add('hidden');
        }
    }

    /**
     * Set callback for layer changes
     */
    setLayerChangeCallback(callback) {
        this.onLayerChange = callback;
    }

    /**
     * Set up keyboard shortcuts for mode switching
     */
    _setupKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            // Don't trigger when typing in input fields
            if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
                return;
            }

            // Number keys 1-3 for slots
            if (e.key === '1' && !e.ctrlKey && !e.altKey && !e.metaKey) {
                e.preventDefault();
                modeManager.toggleMode(MODES.BROWSE);
            } else if (e.key === '2' && !e.ctrlKey && !e.altKey && !e.metaKey) {
                e.preventDefault();
                modeManager.toggleMode(MODES.SEARCH);
            } else if (e.key === '3' && !e.ctrlKey && !e.altKey && !e.metaKey) {
                e.preventDefault();
                modeManager.toggleMode(MODES.ANNOTATE);
            }

            // Letter shortcuts (B/S/A)
            if (!e.ctrlKey && !e.altKey && !e.metaKey) {
                if (e.key === 'b' || e.key === 'B') {
                    e.preventDefault();
                    modeManager.setMode(MODES.BROWSE);
                } else if (e.key === 's' || e.key === 'S') {
                    // Only if not in command input
                    if (document.activeElement?.id !== 'command-input') {
                        e.preventDefault();
                        modeManager.toggleMode(MODES.SEARCH);
                    }
                } else if (e.key === 'a' || e.key === 'A') {
                    // Only if not in command input
                    if (document.activeElement?.id !== 'command-input') {
                        e.preventDefault();
                        modeManager.toggleMode(MODES.ANNOTATE);
                    }
                }
            }

            // Escape returns to browse mode
            if (e.key === 'Escape' && modeManager.getMode() !== MODES.BROWSE) {
                modeManager.setMode(MODES.BROWSE);
            }
        });
    }

    /**
     * Update annotation layer button content
     */
    _updateAnnotationLayerButton() {
        if (!this.annotationLayerBtn) return;

        const layer = annotationLayerManager.getCurrentLayer();
        this.annotationLayerBtn.innerHTML = `
            <span class="w-2 h-2 rounded-full" style="background-color: ${layer.color}"></span>
            <span>${layer.icon}</span>
            <span>${layer.name}</span>
            <span class="text-zinc-500">▼</span>
        `;
    }

    /**
     * Update UI based on annotation mode
     */
    _updateAnnotationModeUI(mode) {
        if (!this.annotationLayerBtn) return;

        if (mode === MODES.ANNOTATE) {
            this.annotationLayerBtn.classList.remove('hidden');
            this.annotationLayerBtn.classList.add('flex');
        } else {
            this.annotationLayerBtn.classList.add('hidden');
            this.annotationLayerBtn.classList.remove('flex');
            layerSelector.hide();
        }
    }

    /**
     * Show/hide the hotbar
     */
    setVisible(visible) {
        if (this.element) {
            this.element.classList.toggle('hidden', !visible);
        }
    }
}

// Singleton instance
export const hotbar = new Hotbar();
