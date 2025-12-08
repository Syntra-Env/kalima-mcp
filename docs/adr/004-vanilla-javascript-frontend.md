# ADR 004: Vanilla JavaScript Frontend (No Framework)

**Status:** Accepted (Implemented November 2025)

**Decision Date:** 2025-11-01

## Context

The Kalima desktop application requires a user interface with the following characteristics:
- Terminal-like command interface for verse exploration
- Ability to display Arabic text with proper RTL rendering
- Simple, fast, and maintainable codebase
- Integration with Tauri for native desktop packaging

## Decision

We chose to build the frontend using vanilla JavaScript, HTML5, and CSS3 without any frontend frameworks (no React, Vue, Angular, etc.).

## Rationale

### Simplicity
- **Zero build step**: No webpack, no babel, no npm build process
- **282 LOC**: Entire application logic in one [app.js](../../desktop/frontend/app.js) file
- **Direct browser APIs**: No abstraction layers, just DOM manipulation
- **Instant refresh**: F5 reloads in milliseconds, no rebuild wait

### Performance
- **<1KB JavaScript**: Minimal bundle size (vs 100KB+ for React alone)
- **Fast startup**: No framework initialization overhead
- **Direct DOM updates**: No virtual DOM diffing
- **Memory efficient**: ~5MB runtime footprint

### Maintainability
- **Low barrier to entry**: Any JavaScript developer can contribute
- **No version lock-in**: No framework upgrade treadmill
- **Debuggable**: Chrome DevTools works without source maps
- **Stable**: Browser APIs don't have breaking changes

### Dependencies
- **Zero npm packages** for frontend runtime
- **Only dev dependencies**: Playwright for E2E tests, http-server for local testing
- **No lock files**: No package.json.lock to manage
- **Supply chain safety**: Minimal attack surface

## Consequences

### Positive
- ✅ Extremely simple architecture
- ✅ No build step required for development
- ✅ Easy onboarding for contributors
- ✅ No framework churn (React 16 → 17 → 18 → 19...)
- ✅ Full control over rendering
- ✅ Minimal bundle size

### Negative
- ❌ Manual DOM manipulation (no declarative templates)
- ❌ No component reusability framework
- ❌ No state management patterns enforced
- ❌ Imperative style can be harder to reason about at scale

### Neutral
- 🔹 Suitable for application's current scope (282 LOC)
- 🔹 Can introduce framework later if complexity grows significantly
- 🔹 Tauri provides native APIs (no Electron overhead)

## Code Organization

```
desktop/frontend/
├── index.html       (20 LOC)  - Minimal structure
├── styles.css       (170 LOC) - Terminal theme
└── app.js           (282 LOC) - All application logic
```

### app.js structure:
- **Command history**: Array-based with keyboard navigation
- **Output rendering**: Dynamic DOM creation for verses, tables, pagers
- **Tauri integration**: `window.__TAURI__.invoke()` for commands
- **Event handling**: `keydown` listeners for Enter, arrows, Ctrl+wheel

## Design Patterns Used

### Module Pattern (Simple)
```javascript
// State in closure
const commandHistory = [];
let historyIndex = -1;

// Event handlers
document.addEventListener('DOMContentLoaded', () => {
    const input = document.getElementById('command-input');
    input.addEventListener('keydown', handleKeydown);
});
```

### Rendering Functions
```javascript
function printVerse(verse) {
    const container = document.createElement('div');
    // Direct DOM manipulation
    output.appendChild(container);
}
```

### Async/Await for Tauri
```javascript
async function executeCommand(cmd) {
    const result = await window.__TAURI__.invoke('execute_command', { command: cmd });
    // Handle result
}
```

## UI Characteristics

- **Terminal aesthetic**: Monospace font, dark theme, command prompt
- **Arabic support**: Scheherazade New font, RTL text handling
- **Accessibility**: Keyboard-first navigation, zoom support (Ctrl+wheel)
- **Responsive**: CSS flexbox layout adapts to window size

## When to Reconsider

This decision should be revisited if:
1. **Codebase exceeds 1,000 LOC**: At scale, framework benefits outweigh costs
2. **Complex state management needed**: Multiple views with shared state
3. **Team prefers framework**: New contributors strongly prefer React/Vue
4. **Component library required**: Need for rich UI widgets

Current verdict: **282 LOC is well within vanilla JS sweet spot**

## Alternatives Considered

### React
**Pros:** Component reusability, large ecosystem, team familiarity
**Cons:** 100KB bundle, build step required, overkill for 282 LOC
**Verdict:** Rejected as unnecessary complexity

### Vue
**Pros:** Progressive framework, simpler than React, good templates
**Cons:** Still requires build step, adds dependency, learning curve
**Verdict:** Rejected for same reasons as React

### Svelte
**Pros:** Compile-time framework, small bundle, reactive
**Cons:** New syntax to learn, build step, less mature ecosystem
**Verdict:** Rejected; vanilla JS is simpler

### Alpine.js
**Pros:** Minimal framework, declarative, no build step
**Cons:** Another dependency, framework lock-in (albeit lightweight)
**Verdict:** Rejected; prefer zero dependencies

## Framework Escape Hatch

If frontend grows beyond ~1,000 LOC, migration path:
1. Keep existing vanilla JS as-is (works)
2. Incrementally adopt Preact (3KB React-compatible)
3. Use HTM for JSX-like syntax (no build)
4. Migrate one view at a time

Or simply continue with vanilla JS - GitHub (1M+ LOC) uses jQuery, not React.

## References

- [desktop/frontend/app.js](../../desktop/frontend/app.js) - Main application
- [desktop/frontend/styles.css](../../desktop/frontend/styles.css) - Terminal theme
- [tests/e2e/gui/interaction.spec.ts](../../tests/e2e/gui/interaction.spec.ts) - E2E tests
- "You Might Not Need a Framework" - various blog posts on vanilla JS benefits
