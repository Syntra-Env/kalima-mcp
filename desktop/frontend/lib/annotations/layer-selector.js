/**
 * Annotation Layer Selector UI
 *
 * A dropdown/popup component for selecting and managing
 * annotation layers from the hotbar.
 */

import { annotationLayerManager, ANNOTATION_LAYER_TYPES } from './annotation-layers.js';

class LayerSelector {
    constructor() {
        this.element = null;
        this.isOpen = false;
        this.onSelectCallback = null;
    }

    /**
     * Initialize the layer selector
     */
    init(container = document.body) {
        this.element = document.createElement('div');
        this.element.id = 'annotation-layer-selector';
        this.element.className = 'hidden fixed z-[60] bg-zinc-900/98 border border-zinc-700 rounded-lg shadow-xl backdrop-blur-sm min-w-[200px] max-h-[300px] overflow-y-auto';

        container.appendChild(this.element);

        // Close on outside click
        document.addEventListener('click', (e) => {
            if (this.isOpen && !this.element.contains(e.target) && !e.target.closest('#annotation-layer-btn')) {
                this.hide();
            }
        });

        // Subscribe to layer changes
        annotationLayerManager.onChange(() => this._render());

        return this;
    }

    /**
     * Show the layer selector near an element
     */
    show(anchorElement) {
        if (!this.element) return;

        this._render();

        const rect = anchorElement.getBoundingClientRect();
        this.element.style.bottom = `${window.innerHeight - rect.top + 8}px`;
        this.element.style.left = `${rect.left}px`;
        this.element.classList.remove('hidden');
        this.isOpen = true;
    }

    /**
     * Hide the layer selector
     */
    hide() {
        if (!this.element) return;
        this.element.classList.add('hidden');
        this.isOpen = false;
    }

    /**
     * Toggle visibility
     */
    toggle(anchorElement) {
        if (this.isOpen) {
            this.hide();
        } else {
            this.show(anchorElement);
        }
    }

    /**
     * Set callback for layer selection
     */
    onSelect(callback) {
        this.onSelectCallback = callback;
    }

    /**
     * Render the layer list
     */
    _render() {
        if (!this.element) return;

        const layers = annotationLayerManager.getLayers();
        const currentLayer = annotationLayerManager.getCurrentLayer();

        this.element.innerHTML = '';

        // Header
        const header = document.createElement('div');
        header.className = 'px-3 py-2 border-b border-zinc-700 text-xs uppercase tracking-wide text-zinc-500 flex justify-between items-center';
        header.innerHTML = `
            <span>Annotation Layers</span>
            <button class="text-kalima-accent hover:text-kalima-accent/80 text-lg font-bold" title="Add new layer">+</button>
        `;
        header.querySelector('button').addEventListener('click', (e) => {
            e.stopPropagation();
            this._showCreateDialog();
        });
        this.element.appendChild(header);

        // Layer list
        const list = document.createElement('div');
        list.className = 'py-1';

        layers.forEach(layer => {
            const item = this._createLayerItem(layer, layer.id === currentLayer.id);
            list.appendChild(item);
        });

        this.element.appendChild(list);
    }

    /**
     * Create a layer item element
     */
    _createLayerItem(layer, isActive) {
        const item = document.createElement('div');
        item.className = `flex items-center gap-2 px-3 py-2 cursor-pointer transition-colors ${
            isActive
                ? 'bg-kalima-accent/20 text-kalima-accent'
                : 'hover:bg-zinc-800 text-zinc-300'
        }`;

        // Color indicator
        const colorDot = document.createElement('span');
        colorDot.className = 'w-3 h-3 rounded-full flex-shrink-0';
        colorDot.style.backgroundColor = layer.color;
        item.appendChild(colorDot);

        // Icon
        const icon = document.createElement('span');
        icon.className = 'text-base flex-shrink-0';
        icon.textContent = layer.icon;
        item.appendChild(icon);

        // Name
        const name = document.createElement('span');
        name.className = 'flex-1 text-sm truncate';
        name.textContent = layer.name;
        item.appendChild(name);

        // Active indicator
        if (isActive) {
            const check = document.createElement('span');
            check.className = 'text-kalima-accent text-sm';
            check.textContent = '✓';
            item.appendChild(check);
        }

        // Delete button for custom layers
        if (layer.type === ANNOTATION_LAYER_TYPES.CUSTOM) {
            const deleteBtn = document.createElement('button');
            deleteBtn.className = 'text-zinc-500 hover:text-red-400 text-xs opacity-0 group-hover:opacity-100 transition-opacity';
            deleteBtn.innerHTML = '×';
            deleteBtn.title = 'Delete layer';
            deleteBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                if (confirm(`Delete layer "${layer.name}"? All annotations in this layer will be lost.`)) {
                    annotationLayerManager.deleteLayer(layer.id);
                }
            });
            item.appendChild(deleteBtn);
            item.classList.add('group');
        }

        // Click to select
        item.addEventListener('click', () => {
            annotationLayerManager.setCurrentLayer(layer.id);
            if (this.onSelectCallback) {
                this.onSelectCallback(layer);
            }
            this.hide();
        });

        return item;
    }

    /**
     * Show dialog to create new layer
     */
    _showCreateDialog() {
        const name = prompt('Enter layer name:');
        if (!name || !name.trim()) return;

        const layer = annotationLayerManager.createLayer(name.trim());
        if (layer) {
            annotationLayerManager.setCurrentLayer(layer.id);
            if (this.onSelectCallback) {
                this.onSelectCallback(layer);
            }
        }
    }
}

// Singleton instance
export const layerSelector = new LayerSelector();
