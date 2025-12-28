import { ANNOTATION_LAYER_INDEX, DEFAULT_LAYER_INDEX, LAYERS } from './definitions.js';
import { extractLayerValue, showAnnotation, showLayerValue } from './render.js';

function getTokenMorphology(token) {
  try {
    const raw = token.dataset.morphology;
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export class LayerManager {
  constructor({ layers = LAYERS, defaultIndex = DEFAULT_LAYER_INDEX } = {}) {
    this.layers = layers;
    this.currentLayerIndex = defaultIndex;
    this._changeListeners = [];
  }

  onChange(callback) {
    if (typeof callback === 'function') {
      this._changeListeners.push(callback);
    }
    return () => {
      this._changeListeners = this._changeListeners.filter(cb => cb !== callback);
    };
  }

  _notifyChange() {
    const layer = this.getCurrentLayer();
    this._changeListeners.forEach(cb => cb(layer));
  }

  getCurrentLayerIndex() {
    return this.currentLayerIndex;
  }

  getCurrentLayer() {
    return this.layers[this.currentLayerIndex];
  }

  changeLayer(newIndex) {
    if (typeof newIndex !== 'number' || newIndex < 0 || newIndex >= this.layers.length) {
      return false;
    }
    this.currentLayerIndex = newIndex;
    this.applyToAllTokens();
    this._notifyChange();
    return true;
  }

  nextLayer() {
    return this.changeLayer(this.currentLayerIndex + 1);
  }

  prevLayer() {
    return this.changeLayer(this.currentLayerIndex - 1);
  }

  applyToAllTokens(root = document) {
    const tokens = root.querySelectorAll('.token');
    tokens.forEach((token) => this.applyToToken(token));
  }

  applyToToken(token) {
    const layer = this.getCurrentLayer();
    const originalText = token.dataset.originalText;
    if (!originalText) return;

    if (layer.id === DEFAULT_LAYER_INDEX) {
      token.textContent = originalText;
      token.className = 'token';
      return;
    }

    if (layer.id === ANNOTATION_LAYER_INDEX) {
      const annotation = token.dataset.annotation;
      if (annotation) {
        showAnnotation(token, annotation, token.dataset.annotationId);
      } else {
        token.textContent = originalText;
        token.className = 'token';
      }
      return;
    }

    const morphSegments = getTokenMorphology(token);
    const value = extractLayerValue(morphSegments, layer.field);
    if (value) {
      showLayerValue(token, value, layer);
    } else {
      token.textContent = originalText;
      token.className = 'token';
    }
  }
}

