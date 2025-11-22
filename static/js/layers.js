// ===== Layer Management System =====

const LayerSystem = {
    layers: {
        morphological: { active: false, color: '#2c5f2d', name: 'Morphological' },
        syntactic: { active: false, color: '#97bc62', name: 'Syntactic' },
        thematic: { active: false, color: '#c9a961', name: 'Thematic' },
        phonological: { active: false, color: '#6b4e71', name: 'Phonological' },
        compositional: { active: false, color: '#4a7c9b', name: 'Compositional' },
        annotations: { active: true, color: '#d97742', name: 'Annotations' }
    },

    connections: {
        internal: [], // Connections within current verse
        external: []  // Connections to other verses
    },

    currentVerse: null,

    init() {
        this.createLayerControls();
        this.createConnectionCanvas();
        this.createEdgeIndicators();
    },

    createLayerControls() {
        const container = document.getElementById('layerControls');
        if (!container) return;

        let html = '<div class="layer-toggles">';
        for (const [key, layer] of Object.entries(this.layers)) {
            html += `
                <label class="layer-toggle">
                    <input type="checkbox"
                           id="layer-${key}"
                           ${layer.active ? 'checked' : ''}
                           data-layer="${key}">
                    <span class="layer-color" style="background-color: ${layer.color}"></span>
                    <span class="layer-name">${layer.name}</span>
                </label>
            `;
        }
        html += '</div>';
        container.innerHTML = html;

        // Add event listeners
        container.querySelectorAll('input[type="checkbox"]').forEach(checkbox => {
            checkbox.addEventListener('change', (e) => {
                const layerKey = e.target.dataset.layer;
                this.toggleLayer(layerKey, e.target.checked);
            });
        });
    },

    toggleLayer(layerKey, active) {
        if (this.layers[layerKey]) {
            this.layers[layerKey].active = active;
            this.refreshDisplay();
        }
    },

    createConnectionCanvas() {
        // Create SVG overlay for connections
        const verseContainer = document.querySelector('.verse-text');
        if (!verseContainer) return;

        const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        svg.setAttribute('class', 'connection-canvas');
        svg.setAttribute('id', 'connectionCanvas');

        // Position absolutely over the verse text
        svg.style.position = 'absolute';
        svg.style.top = '0';
        svg.style.left = '0';
        svg.style.width = '100%';
        svg.style.height = '100%';
        svg.style.pointerEvents = 'none';
        svg.style.zIndex = '10';

        verseContainer.parentElement.style.position = 'relative';
        verseContainer.parentElement.appendChild(svg);
    },

    createEdgeIndicators() {
        const container = document.querySelector('.verse-container');
        if (!container) return;

        const indicatorHTML = `
            <div class="edge-indicators">
                <div class="edge-indicator edge-top" id="edgeTop"></div>
                <div class="edge-indicator edge-right" id="edgeRight"></div>
                <div class="edge-indicator edge-bottom" id="edgeBottom"></div>
                <div class="edge-indicator edge-left" id="edgeLeft"></div>
            </div>
        `;

        container.insertAdjacentHTML('beforeend', indicatorHTML);
    },

    // ===== Connection Management =====

    addConnection(connection) {
        if (connection.type === 'internal') {
            this.connections.internal.push(connection);
        } else {
            this.connections.external.push(connection);
        }
        this.refreshDisplay();
        this.saveConnections();
    },

    removeConnection(connectionId) {
        this.connections.internal = this.connections.internal.filter(c => c.id !== connectionId);
        this.connections.external = this.connections.external.filter(c => c.id !== connectionId);
        this.refreshDisplay();
        this.saveConnections();
    },

    loadConnections(verseRef) {
        // Load connections from backend
        fetch(`/api/connections/${verseRef}`)
            .then(res => res.json())
            .then(data => {
                this.connections.internal = data.internal || [];
                this.connections.external = data.external || [];
                this.refreshDisplay();
            })
            .catch(err => console.error('Error loading connections:', err));
    },

    saveConnections() {
        if (!this.currentVerse) return;

        const verseRef = `${this.currentVerse.surah.number}:${this.currentVerse.ayah}`;

        fetch(`/api/connections/${verseRef}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(this.connections)
        });
    },

    // ===== Rendering =====

    refreshDisplay() {
        this.renderInternalConnections();
        this.renderExternalIndicators();
        this.applyLayerHighlights();
    },

    renderInternalConnections() {
        const svg = document.getElementById('connectionCanvas');
        if (!svg) return;

        // Clear existing connections
        svg.innerHTML = '';

        // Render only connections for active layers
        this.connections.internal.forEach(conn => {
            if (this.layers[conn.layer] && this.layers[conn.layer].active) {
                this.drawConnection(svg, conn);
            }
        });
    },

    drawConnection(svg, connection) {
        const source = document.querySelector(`[data-token-id="${connection.from}"]`);
        const target = document.querySelector(`[data-token-id="${connection.to}"]`);

        if (!source || !target) return;

        const sourceRect = source.getBoundingClientRect();
        const targetRect = target.getBoundingClientRect();
        const svgRect = svg.getBoundingClientRect();

        // Calculate positions relative to SVG
        const x1 = sourceRect.left + sourceRect.width / 2 - svgRect.left;
        const y1 = sourceRect.bottom - svgRect.top;
        const x2 = targetRect.left + targetRect.width / 2 - svgRect.left;
        const y2 = targetRect.bottom - svgRect.top;

        // Create curved path
        const curve = this.createCurvePath(x1, y1, x2, y2);

        const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        path.setAttribute('d', curve);
        path.setAttribute('stroke', this.layers[connection.layer].color);
        path.setAttribute('stroke-width', '2');
        path.setAttribute('fill', 'none');
        path.setAttribute('class', 'connection-line');
        path.setAttribute('data-connection-id', connection.id);

        // Add hover effects
        path.style.cursor = 'pointer';
        path.style.pointerEvents = 'stroke';

        path.addEventListener('mouseenter', () => {
            path.setAttribute('stroke-width', '3');
            this.showConnectionTooltip(connection, path);
        });

        path.addEventListener('mouseleave', () => {
            path.setAttribute('stroke-width', '2');
            this.hideConnectionTooltip();
        });

        svg.appendChild(path);
    },

    createCurvePath(x1, y1, x2, y2) {
        // Create a smooth quadratic curve
        const midX = (x1 + x2) / 2;
        const curveDepth = Math.abs(x2 - x1) * 0.3;
        const controlY = y1 + curveDepth;

        return `M ${x1} ${y1} Q ${midX} ${controlY}, ${x2} ${y2}`;
    },

    renderExternalIndicators() {
        const indicators = {
            top: [],
            right: [],
            bottom: [],
            left: []
        };

        // Group external connections by direction
        this.connections.external.forEach(conn => {
            if (!this.layers[conn.layer] || !this.layers[conn.layer].active) return;

            const direction = this.getConnectionDirection(conn);
            indicators[direction].push(conn);
        });

        // Render indicators
        this.updateEdgeIndicator('edgeTop', indicators.top, 'top');
        this.updateEdgeIndicator('edgeRight', indicators.right, 'right');
        this.updateEdgeIndicator('edgeBottom', indicators.bottom, 'bottom');
        this.updateEdgeIndicator('edgeLeft', indicators.left, 'left');
    },

    getConnectionDirection(connection) {
        if (!this.currentVerse) return 'top';

        const currentRef = this.currentVerse.surah.number * 1000 + this.currentVerse.ayah;
        const targetParts = connection.targetVerse.split(':');
        const targetRef = parseInt(targetParts[0]) * 1000 + parseInt(targetParts[1]);

        if (targetRef < currentRef) {
            return 'top'; // Earlier verse
        } else if (targetRef > currentRef) {
            return 'bottom'; // Later verse
        }

        return 'top';
    },

    updateEdgeIndicator(elementId, connections, direction) {
        const indicator = document.getElementById(elementId);
        if (!indicator) return;

        if (connections.length === 0) {
            indicator.style.display = 'none';
            return;
        }

        indicator.style.display = 'flex';
        indicator.innerHTML = `
            <div class="indicator-badge">${connections.length}</div>
            <div class="indicator-arrow">${this.getArrowSymbol(direction)}</div>
        `;

        // Add click handler to navigate to closest connection
        indicator.onclick = () => {
            const closest = connections[0]; // For now, just go to first
            this.navigateToConnection(closest);
        };

        // Add hover preview
        indicator.onmouseenter = () => {
            this.showExternalPreview(connections, indicator);
        };

        indicator.onmouseleave = () => {
            this.hideExternalPreview();
        };
    },

    getArrowSymbol(direction) {
        const arrows = {
            top: '↑',
            right: '→',
            bottom: '↓',
            left: '←'
        };
        return arrows[direction] || '•';
    },

    navigateToConnection(connection) {
        const [surah, ayah] = connection.targetVerse.split(':');
        if (window.loadVerse) {
            window.loadVerse(parseInt(surah), parseInt(ayah));
        }
    },

    applyLayerHighlights() {
        // Apply visual highlights based on active layers
        const tokens = document.querySelectorAll('.token');

        tokens.forEach(token => {
            token.classList.remove('layer-highlight');
            token.style.borderColor = '';

            // Check if token has any active layer connections
            const tokenId = token.dataset.tokenId;
            const hasConnection = this.connections.internal.some(conn =>
                (conn.from === tokenId || conn.to === tokenId) &&
                this.layers[conn.layer] &&
                this.layers[conn.layer].active
            );

            if (hasConnection) {
                token.classList.add('layer-highlight');
            }
        });
    },

    showConnectionTooltip(connection, element) {
        const tooltip = document.createElement('div');
        tooltip.className = 'connection-tooltip';
        tooltip.innerHTML = `
            <strong>${this.layers[connection.layer].name} Connection</strong><br>
            ${connection.note || 'No description'}
        `;

        const rect = element.getBoundingClientRect();
        tooltip.style.position = 'fixed';
        tooltip.style.left = rect.left + rect.width / 2 + 'px';
        tooltip.style.top = rect.top - 10 + 'px';
        tooltip.style.transform = 'translate(-50%, -100%)';

        document.body.appendChild(tooltip);
        tooltip.id = 'connectionTooltip';
    },

    hideConnectionTooltip() {
        const tooltip = document.getElementById('connectionTooltip');
        if (tooltip) tooltip.remove();
    },

    showExternalPreview(connections, indicator) {
        // Show preview of connected verses
        const preview = document.createElement('div');
        preview.className = 'external-preview';
        preview.id = 'externalPreview';

        let html = '<div class="preview-title">Connected Verses:</div>';
        connections.slice(0, 3).forEach(conn => {
            html += `<div class="preview-item">${conn.targetVerse}</div>`;
        });
        if (connections.length > 3) {
            html += `<div class="preview-more">+${connections.length - 3} more</div>`;
        }

        preview.innerHTML = html;

        const rect = indicator.getBoundingClientRect();
        preview.style.position = 'fixed';
        preview.style.left = rect.left + 'px';
        preview.style.top = rect.top + 'px';

        document.body.appendChild(preview);
    },

    hideExternalPreview() {
        const preview = document.getElementById('externalPreview');
        if (preview) preview.remove();
    },

    setCurrentVerse(verse) {
        this.currentVerse = verse;
        const verseRef = `${verse.surah.number}:${verse.ayah}`;
        this.loadConnections(verseRef);
    }
};

// Export for use in main app
window.LayerSystem = LayerSystem;
