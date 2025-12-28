/**
 * Annotation Search System
 *
 * Search annotations and display results with the annotation
 * substituted in place of the original Arabic text.
 * This enables "verification" mode where users can see all
 * occurrences of a particular interpretation.
 */

import { annotationLayerManager } from './annotation-layers.js';

class AnnotationSearch {
    constructor() {
        this.lastResults = [];
    }

    /**
     * Search for annotations matching a query
     * Returns results with context for display
     */
    async search(query, options = {}) {
        if (!query || !query.trim()) {
            return { results: [], query: '' };
        }

        const normalizedQuery = query.trim().toLowerCase();
        const results = await annotationLayerManager.searchAnnotations(normalizedQuery, options);

        // Group results by verse
        const grouped = new Map();
        for (const result of results) {
            const match = result.target_id.match(/^(\d+):(\d+):(\d+)$/);
            if (!match) continue;

            const [, surah, ayah, tokenIndex] = match;
            const verseKey = `${surah}:${ayah}`;

            if (!grouped.has(verseKey)) {
                grouped.set(verseKey, {
                    surah: parseInt(surah),
                    ayah: parseInt(ayah),
                    verseKey,
                    tokens: [],
                });
            }

            grouped.get(verseKey).tokens.push({
                index: parseInt(tokenIndex),
                annotation: result.payload?.annotation || '',
                layer: result.layerInfo,
                annotationId: result.id,
            });
        }

        // Convert to array and sort by verse reference
        const groupedResults = Array.from(grouped.values()).sort((a, b) => {
            if (a.surah !== b.surah) return a.surah - b.surah;
            return a.ayah - b.ayah;
        });

        this.lastResults = groupedResults;

        return {
            query: normalizedQuery,
            results: groupedResults,
            totalMatches: results.length,
            verseCount: groupedResults.length,
        };
    }

    /**
     * Display search results in the results pane
     * Shows each verse with annotated tokens substituted
     */
    async displayResults(searchResults, options = {}) {
        const { outputEl, invoke, layerManager, morphologyCache, fetchMorphologyForVerse } = options;

        if (!outputEl) {
            console.warn('No output element for annotation search results');
            return;
        }

        // Clear previous results
        outputEl.innerHTML = '';

        if (!searchResults.results || searchResults.results.length === 0) {
            const noResults = document.createElement('div');
            noResults.className = 'text-zinc-500 text-sm p-4';
            noResults.textContent = `No annotations found matching "${searchResults.query}"`;
            outputEl.appendChild(noResults);
            return;
        }

        // Summary header
        const summary = document.createElement('div');
        summary.className = 'annotation-search-summary px-2 py-2 border-b border-zinc-700 text-sm';
        summary.innerHTML = `
            <span class="text-kalima-accent font-medium">${searchResults.totalMatches}</span>
            <span class="text-zinc-400">matches in</span>
            <span class="text-kalima-accent font-medium">${searchResults.verseCount}</span>
            <span class="text-zinc-400">verses for</span>
            <span class="text-kalima-search font-medium">"${searchResults.query}"</span>
        `;
        outputEl.appendChild(summary);

        // Display each verse with annotations substituted
        for (const verseResult of searchResults.results) {
            const verseContainer = await this._renderVerseWithSubstitutions(verseResult, options);
            outputEl.appendChild(verseContainer);
        }
    }

    /**
     * Render a verse with annotations substituted in place
     */
    async _renderVerseWithSubstitutions(verseResult, options) {
        const { invoke, fetchMorphologyForVerse, morphologyCache } = options;

        const container = document.createElement('div');
        container.className = 'annotation-search-result my-4 p-3 bg-zinc-800/30 rounded-lg border border-zinc-700/50';

        // Verse reference header
        const header = document.createElement('div');
        header.className = 'flex items-center gap-2 mb-2 text-xs';
        header.innerHTML = `
            <span class="text-kalima-accent font-mono">${verseResult.surah}:${verseResult.ayah}</span>
            <span class="text-zinc-600">•</span>
            <span class="text-zinc-500">${verseResult.tokens.length} annotation(s)</span>
        `;
        container.appendChild(header);

        // Fetch verse text from backend
        let verseData = null;
        try {
            if (invoke) {
                const result = await invoke('execute_command', {
                    command: `show ${verseResult.surah}:${verseResult.ayah}`
                });
                if (result.output && result.output.tokens) {
                    verseData = result.output;
                }
            }
        } catch (err) {
            console.warn('Could not fetch verse for annotation search:', err);
        }

        // Verse content with substitutions
        const content = document.createElement('div');
        content.className = 'font-arabic text-lg leading-relaxed';
        content.dir = 'rtl';

        if (verseData && verseData.tokens) {
            // Build token map for quick lookup
            const annotationMap = new Map();
            verseResult.tokens.forEach(t => annotationMap.set(t.index, t));

            // Render tokens with substitutions
            verseData.tokens.forEach((tokenText, index) => {
                const annotation = annotationMap.get(index);

                if (annotation) {
                    // Show annotation with special styling
                    const annotatedSpan = document.createElement('span');
                    annotatedSpan.className = 'annotation-substituted';
                    annotatedSpan.style.cssText = `
                        background: linear-gradient(135deg, ${annotation.layer.color}22, ${annotation.layer.color}11);
                        border-bottom: 2px solid ${annotation.layer.color};
                        padding: 0 4px;
                        border-radius: 3px;
                        cursor: help;
                    `;
                    annotatedSpan.title = `Original: ${tokenText}\nLayer: ${annotation.layer.name}`;

                    // Show annotation text (LTR for English/transliteration)
                    const annotationText = document.createElement('span');
                    annotationText.className = 'annotation-text text-sm';
                    annotationText.dir = 'ltr';
                    annotationText.style.color = annotation.layer.color;
                    annotationText.textContent = annotation.annotation;
                    annotatedSpan.appendChild(annotationText);

                    content.appendChild(annotatedSpan);
                } else {
                    // Show original Arabic
                    const tokenSpan = document.createElement('span');
                    tokenSpan.className = 'text-zinc-400';
                    tokenSpan.textContent = tokenText;
                    content.appendChild(tokenSpan);
                }

                // Add space between tokens
                content.appendChild(document.createTextNode(' '));
            });
        } else {
            // Fallback: just show annotations without verse context
            content.className = 'text-zinc-500 text-sm italic';
            content.textContent = 'Verse text unavailable';
        }

        container.appendChild(content);

        // Show original Arabic below for reference
        if (verseData && verseData.tokens) {
            const original = document.createElement('div');
            original.className = 'mt-2 pt-2 border-t border-zinc-700/30 text-xs text-zinc-500';
            original.dir = 'rtl';

            const label = document.createElement('span');
            label.className = 'text-zinc-600 ml-2';
            label.textContent = 'Original:';
            original.appendChild(label);

            const text = document.createElement('span');
            text.className = 'font-arabic';
            text.textContent = ' ' + verseData.tokens.join(' ');
            original.appendChild(text);

            container.appendChild(original);
        }

        return container;
    }

    /**
     * Get last search results
     */
    getLastResults() {
        return this.lastResults;
    }

    /**
     * Clear results
     */
    clear() {
        this.lastResults = [];
    }
}

// Singleton instance
export const annotationSearch = new AnnotationSearch();
