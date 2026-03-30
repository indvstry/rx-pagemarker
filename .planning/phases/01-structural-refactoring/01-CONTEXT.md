# Phase 1: Structural Refactoring - Context

**Gathered:** 2026-03-30
**Status:** Ready for planning

<domain>
## Phase Boundary

Reorganize the visual editor's flat-scope JavaScript (~1854 lines in `tools/page-marker-editor.html`) into namespace modules with EventBus and central State object. **No behavior changes** — all existing features must work identically after refactoring. Establish content integrity invariants that all future phases must maintain.

</domain>

<decisions>
## Implementation Decisions

### Module Organization
- **D-01:** Organize code by **feature**, not by layer. Create namespace objects: `DragDrop`, `Markers`, `History`, `AutoSave`, `Export`, `UI`. Each namespace owns its functions and local state.
- **D-02:** Keep the instructions panel as-is — no tab structure preparation. Sidebar restructuring happens in Phase 2.
- **D-03:** EventBus and State are infrastructure modules shared across all feature namespaces.

### Content Integrity
- **D-04:** When removing a marker from its old position, **only merge adjacent text nodes**. Never touch parent elements, classes, or attributes. This is a hard invariant.
- **D-05:** `prepareExportedBody()` must include a **diff check** — compare non-marker DOM structure against the original and warn if anything outside markers changed.
- **D-06:** Marker element creation must be consolidated into a single factory function in the `Markers` namespace (`Markers.createMarker()`). Currently duplicated in 4 places.

### EPUB Marker Format (HARD CONSTRAINT)
- **D-07:** The page marker HTML format is EPUB-compatible and **must not change**:
  ```html
  <span id="page5" class="page-number" role="note" aria-label="Page 5">5</span>
  ```
  Any alternative encoding must be proposed with reasoning and approved by the user before implementation. This applies to both in-editor markers and exported markers.
- **D-08:** Two-column duplicate markers use `-2`, `-3` suffixes on IDs (e.g., `id="page36-2"`). This convention must be preserved.

### Claude's Discretion
- State management details (what goes in central State vs namespace-local state) — Claude can decide based on what makes the EventBus cleanest
- Event architecture granularity — Claude can decide event naming and granularity based on what Phase 2-5 features will need

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Editor Source
- `tools/page-marker-editor.html` — The single file being refactored (1854 lines, all HTML/CSS/JS)

### Project Context
- `.planning/PROJECT.md` — Project goals, constraints (single-file, zero-install, cross-platform)
- `.planning/REQUIREMENTS.md` — ARCH-01 through ARCH-04, INTG-01 through INTG-04
- `CLAUDE.md` §Phase 11 — Visual marker editor feature documentation and known limitations

### Research
- `.planning/research/ARCHITECTURE.md` — Namespace module pattern, EventBus design, State object, build order
- `.planning/research/PITFALLS.md` — Stale DOM references after undo/redo, validation state vs editor DOM separation, localStorage quota
- `.planning/research/STACK.md` — Browser API recommendations, caretPositionFromPoint priority

### Codebase Analysis
- `.planning/codebase/CONVENTIONS.md` — Code style patterns used in the project
- `.planning/codebase/CONCERNS.md` — Known issues and tech debt

</canonical_refs>

<code_context>
## Existing Code Insights

### Current Global State (9 variables at flat scope)
- `originalFileName`, `originalHTML` — file identity
- `history[]`, `historyIndex` — undo/redo stack
- `zoom` — current zoom level
- `addMode` — add-marker mode toggle
- `highlightedWord` — word highlight during add mode
- `hasUnsavedChanges` — dirty flag
- `draggedMarker`, `dropTarget` — drag state

### Marker Creation Duplication (4 locations)
1. `loadContent()` line ~666 — creating markers from loaded HTML
2. `moveMarker()` line ~1169 — recreating marker at new position
3. `insertMarkerAfterWord()` line ~1576 — creating marker in add mode
4. `prepareExportedBody()` line ~1679 — rebuilding markers for export

### Key Functions by Future Namespace
- **DragDrop**: `startDrag`, `onDrag`, `endDrag`, `snapToWordBoundary`, `getCaretPosition`, `showDropCursor`, `hideDropCursor`, `findWordBoundaries`
- **Markers**: `moveMarker`, `editMarker`, `deleteMarker`, `updateMarkerNumber`, `insertMarkerAfterWord`, `setupMarkerDragging`, `updateStats`, `getNextPageNumber`
- **History**: `saveState`, `undo`, `redo`, `restoreState`
- **AutoSave**: `autoSave`, `clearAutoSave`, `checkForSavedState`
- **Export**: `prepareExportedBody`, download handler, copy-body handler
- **UI**: `setZoom`, `toggleAddMode`, `clearWordHighlight`, `onAddModeHover`, `onAddModeClick`, `showToast`, `updateButtons`

### Integration Points
- Event listeners on `editor` element for drag, click, mousemove
- `fileInput.addEventListener('change')` for file loading
- `window.addEventListener('beforeunload')` for unsaved changes warning
- `document.addEventListener('keydown')` for Ctrl+Z/Y shortcuts

</code_context>

<specifics>
## Specific Ideas

- User explicitly requires: moving a marker must never leave orphaned tags, empty spans, or junk whitespace
- User explicitly requires: exported HTML must preserve all original classes, attributes, and structure
- User explicitly requires: EPUB marker format is sacrosanct — no changes without explicit approval and reasoning
- Portability constraint: editor must remain a single HTML file, zero dependencies, works on Windows/macOS by copying the folder

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 01-structural-refactoring*
*Context gathered: 2026-03-30*
