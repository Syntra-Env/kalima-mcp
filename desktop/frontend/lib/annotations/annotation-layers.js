/**
 * Dynamic Annotation Layer System
 *
 * Allows users to create, switch between, and manage multiple
 * annotation layers. Each layer can hold different types of
 * interpretations or notes at the token/verse level.
 */

// Built-in annotation layer types
export const ANNOTATION_LAYER_TYPES = {
    INLINE: 'inline',           // Default inline annotations
    NOTES: 'notes',             // Personal study notes
    TAFSIR: 'tafsir',           // Tafsir references
    GRAMMAR: 'grammar',         // Grammar notes
    MORPHOLOGY: 'morphology',   // Morphological analysis
    CUSTOM: 'custom',           // User-defined layers
};

const DEFAULT_LAYERS = [
    { id: 'inline', name: 'Inline', type: ANNOTATION_LAYER_TYPES.INLINE, color: '#4ec9b0', icon: '📝' },
    { id: 'notes', name: 'Notes', type: ANNOTATION_LAYER_TYPES.NOTES, color: '#ffc66d', icon: '🗒️' },
];

class AnnotationLayerManager {
    constructor() {
        this.layers = new Map();
        this.currentLayerId = 'inline';
        this.listeners = new Set();

        // Initialize default layers
        DEFAULT_LAYERS.forEach(layer => {
            this.layers.set(layer.id, { ...layer, visible: true });
        });
    }

    /**
     * Get all annotation layers
     */
    getLayers() {
        return Array.from(this.layers.values());
    }

    /**
     * Get visible layers
     */
    getVisibleLayers() {
        return this.getLayers().filter(l => l.visible);
    }

    /**
     * Get current annotation layer
     */
    getCurrentLayer() {
        return this.layers.get(this.currentLayerId) || this.layers.get('inline');
    }

    /**
     * Get layer by ID
     */
    getLayer(id) {
        return this.layers.get(id);
    }

    /**
     * Set current annotation layer
     */
    setCurrentLayer(id) {
        if (!this.layers.has(id)) {
            console.warn(`Unknown annotation layer: ${id}`);
            return false;
        }

        if (this.currentLayerId === id) return false;

        this.currentLayerId = id;
        this._notifyListeners('change');
        return true;
    }

    /**
     * Create a new custom annotation layer
     */
    createLayer(name, options = {}) {
        const id = options.id || `custom_${Date.now()}`;

        if (this.layers.has(id)) {
            console.warn(`Layer already exists: ${id}`);
            return null;
        }

        const layer = {
            id,
            name,
            type: options.type || ANNOTATION_LAYER_TYPES.CUSTOM,
            color: options.color || '#9cdcfe',
            icon: options.icon || '📌',
            visible: true,
            createdAt: Date.now(),
        };

        this.layers.set(id, layer);
        this._notifyListeners('create', layer);
        this._persist();

        return layer;
    }

    /**
     * Delete a custom annotation layer
     */
    deleteLayer(id) {
        const layer = this.layers.get(id);
        if (!layer) return false;

        // Prevent deleting built-in layers
        if (layer.type === ANNOTATION_LAYER_TYPES.INLINE) {
            console.warn('Cannot delete built-in inline layer');
            return false;
        }

        this.layers.delete(id);

        // Switch to inline if current layer was deleted
        if (this.currentLayerId === id) {
            this.currentLayerId = 'inline';
        }

        this._notifyListeners('delete', layer);
        this._persist();

        return true;
    }

    /**
     * Toggle layer visibility
     */
    toggleLayerVisibility(id) {
        const layer = this.layers.get(id);
        if (!layer) return false;

        layer.visible = !layer.visible;
        this._notifyListeners('visibility', layer);
        this._persist();

        return layer.visible;
    }

    /**
     * Rename a layer
     */
    renameLayer(id, newName) {
        const layer = this.layers.get(id);
        if (!layer) return false;

        layer.name = newName;
        this._notifyListeners('rename', layer);
        this._persist();

        return true;
    }

    /**
     * Subscribe to layer changes
     */
    onChange(callback) {
        this.listeners.add(callback);
        return () => this.listeners.delete(callback);
    }

    /**
     * Notify listeners of changes
     */
    _notifyListeners(event, data) {
        this.listeners.forEach(cb => {
            try {
                cb(event, data, this.getCurrentLayer());
            } catch (err) {
                console.error('Annotation layer listener error:', err);
            }
        });
    }

    /**
     * Persist layers to localStorage
     */
    _persist() {
        try {
            const data = this.getLayers().filter(l => l.type === ANNOTATION_LAYER_TYPES.CUSTOM);
            localStorage.setItem('kalima_annotation_layers', JSON.stringify(data));
        } catch (err) {
            console.warn('Could not persist annotation layers:', err);
        }
    }

    /**
     * Load layers from localStorage
     */
    load() {
        try {
            const data = localStorage.getItem('kalima_annotation_layers');
            if (data) {
                const customLayers = JSON.parse(data);
                customLayers.forEach(layer => {
                    this.layers.set(layer.id, { ...layer, visible: true });
                });
            }
        } catch (err) {
            console.warn('Could not load annotation layers:', err);
        }
    }

    /**
     * Get annotations for a target from all visible layers
     */
    async getAnnotationsForTarget(targetId) {
        const results = [];
        const visibleLayers = this.getVisibleLayers();

        for (const layer of visibleLayers) {
            try {
                const response = await fetch(`http://localhost:8080/annotations?layer=${layer.id}&target_id=${targetId}`);
                if (response.ok) {
                    const annotations = await response.json();
                    annotations.forEach(ann => {
                        results.push({ ...ann, layerInfo: layer });
                    });
                }
            } catch (err) {
                console.warn(`Could not fetch annotations for layer ${layer.id}:`, err);
            }
        }

        return results;
    }

    /**
     * Search annotations across all layers
     */
    async searchAnnotations(query, options = {}) {
        const results = [];
        const layersToSearch = options.layerId
            ? [this.getLayer(options.layerId)].filter(Boolean)
            : this.getVisibleLayers();

        for (const layer of layersToSearch) {
            try {
                const response = await fetch(`http://localhost:8080/annotations?layer=${layer.id}`);
                if (response.ok) {
                    const annotations = await response.json();
                    const matches = annotations.filter(ann => {
                        const payload = ann.payload || {};
                        const text = payload.annotation || '';
                        return text.toLowerCase().includes(query.toLowerCase());
                    });

                    matches.forEach(ann => {
                        results.push({ ...ann, layerInfo: layer });
                    });
                }
            } catch (err) {
                console.warn(`Could not search annotations in layer ${layer.id}:`, err);
            }
        }

        return results;
    }
}

// Singleton instance
export const annotationLayerManager = new AnnotationLayerManager();
