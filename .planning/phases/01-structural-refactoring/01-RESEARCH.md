# Phase 1: Structural Refactoring - Research

**Researched:** 2026-03-31
**Domain:** Single-file vanilla JS refactoring — namespace modules, EventBus, central State
**Confidence:** HIGH — based on direct source analysis + authoritative pre-existing research

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Organize code by **feature**, not by layer. Create namespace objects: `DragDrop`, `Markers`, `History`, `AutoSave`, `Export`, `UI`. Each namespace owns its functions and local state.
- **D-02:** Keep the instructions panel as-is — no tab structure preparation. Sidebar restructuring happens in Phase 2.
- **D-03:** EventBus and State are infrastructure modules shared across all feature namespaces.
- **D-04:** When removing a marker from its old position, **only merge adjacent text nodes**. Never touch parent elements, classes, or attributes. This is a hard invariant.
- **D-05:** `prepareExportedBody()` must include a **diff check** — compare non-marker DOM structure against the original and warn if anything outside markers changed.
- **D-06:** Marker element creation must be consolidated into a single factory function in the `Markers` namespace (`Markers.createMarker()`). Currently duplicated in 4 places.
- **D-07:** The page marker HTML format is EPUB-compatible and **must not change**:
  ```html
  <span id="page5" class="page-number" role="note" aria-label="Page 5">5</span>
  ```
  Any alternative encoding must be proposed with reasoning and approved by the user before implementation.
- **D-08:** Two-column duplicate markers use `-2`, `-3` suffixes on IDs (e.g., `id="page36-2"`). This convention must be preserved.

### Claude's Discretion

- State management details (what goes in central State vs namespace-local state) — Claude can decide based on what makes the EventBus cleanest.
- Event architecture granularity — Claude can decide event naming and granularity based on what Phase 2-5 features will need.

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| ARCH-01 | Editor JS organized into namespace modules with clear boundaries (no behavior change) | Namespace object pattern documented in ARCHITECTURE.md; direct source map to 6 namespaces confirmed |
| ARCH-02 | Central EventBus decouples modules — mutations emit events, consumers react | EventBus implementation pattern documented; 9 events identified in ARCHITECTURE.md |
| ARCH-03 | Single State object replaces scattered globals — modules read/write via State API | All 9 globals identified at lines 512–543; State.set() pattern defined |
| ARCH-04 | Marker element creation consolidated into single factory function | All 4 duplication sites identified (lines ~666, ~1169, ~1576, ~1679); factory signature defined |
| INTG-01 | Moving a marker preserves all surrounding HTML elements, attributes, and classes | Current moveMarker() already does this; invariant must be documented and enforced by module boundary |
| INTG-02 | Moving a marker leaves no orphaned tags, empty spans, or junk whitespace at source | Current code: `marker.remove()` + conditional `oldParent.normalize()` — must tighten to always normalize after removal |
| INTG-03 | Exported HTML preserves all original document classes, attributes, and structure outside of marker elements | D-05: diff check added to `prepareExportedBody()` — research defines how to implement this |
| INTG-04 | Undo/redo restores exact document state including all HTML classes and attributes | Already achieved by `cloneNode(true)` snapshots; refactoring must not break the restore path |
</phase_requirements>

---

## Summary

Phase 1 is a pure structural refactoring of `tools/page-marker-editor.html` — 1854 lines of flat-scope vanilla JS wrapped into namespace objects with a central EventBus and State object. Zero behavior changes. The goal is a maintainable foundation that Phase 2-5 can build features on without global variable collisions or spaghetti function calls.

The prior research (`.planning/research/`) already did the deep investigation. This document synthesizes those findings into the specific planning artifacts the planner needs: exact code locations to move, concrete module boundaries, the full list of state variables to migrate, the 4 marker-creation sites to consolidate, the event contract between modules, and the critical content-integrity invariants that must hold throughout.

The most significant new obligation in Phase 1 (not just reorganization) is the **export diff check** (D-05): `prepareExportedBody()` must compare the cloned non-marker DOM structure against `originalHTML` and warn if anything outside markers diverged. This is a net-new piece of logic that needs careful implementation.

**Primary recommendation:** Reorganize in strict section order (EventBus → State → Markers factory → History → AutoSave → DragDrop → AddMode → Export → Toast → FileLoader → Init). Wire EventBus between modules. Do not change any logic, only ownership. Verify with end-to-end drag/edit/undo/export smoke test after each namespace is wired.

---

## Standard Stack

### Core (already in use — no new dependencies)

| Component | Approach | Purpose | Why |
|-----------|----------|---------|-----|
| Namespace objects | Plain JS objects `var Foo = {...}` | Module simulation | Zero-dependency, works offline, standard single-file pattern |
| EventBus | Inline pub/sub (~20 lines) | Cross-module decoupling | No library needed; the prior research includes a working implementation |
| State | Plain JS object with `set()` method | Centralized globals | Replaces 9 scattered `var`/`let` declarations at flat scope |
| `cloneNode(true)` | Native DOM API | History snapshots | Already used; unchanged |
| `normalize()` | Native DOM API | Text node merging after marker removal | Already used; must be hardened |

**No new libraries. No CDN. The file must remain fully offline.**

### Marker Factory (consolidation target)

The existing inline `document.createElement('span')` blocks in 4 locations must be replaced by a single `Markers.createMarker(pageNum, markerId)` factory. The factory signature:

```javascript
// Source: synthesis of lines ~666, ~1169, ~1576, ~1679
Markers.createMarker = function(pageNum, markerId) {
    var span = document.createElement('span');
    span.className = 'page-marker';
    span.setAttribute('data-page', String(pageNum));
    span.setAttribute('data-id', markerId || 'marker-' + Date.now());
    span.setAttribute('draggable', 'true');
    span.textContent = String(pageNum);
    return span;
};
```

Every site that creates a marker element must call this and nothing else. No inline `createElement('span')` with marker attributes anywhere outside `Markers.createMarker`.

---

## Architecture Patterns

### Recommended Structure (within single `<script>` block)

```
<script>
  Section 1: EventBus        (~20 lines)  — pub/sub infrastructure
  Section 2: State           (~30 lines)  — replaces 9 globals
  Section 3: Markers         (~60 lines)  — factory + read queries (no mutation)
  Section 4: History         (~80 lines)  — undo/redo stack (IIFE for privacy)
  Section 5: AutoSave        (~60 lines)  — localStorage persistence
  Section 6: DragDrop        (~220 lines) — drag system + moveMarker
  Section 7: AddMode         (~160 lines) — add mode hover/click
  Section 8: Export          (~130 lines) — prepareExportedBody, download, copyBody
  Section 9: Toast           (~25 lines)  — showToast
  Section 10: FileLoader     (~110 lines) — loadContent, checkForSavedState
  Section 11: Init           (~40 lines)  — DOMContentLoaded wiring
</script>
```

Phase 2 will add Sidebar (~200 lines) and Search as a Sidebar sub-function. Phase 3 adds Validation (~180 lines). The file will reach approximately 2100 lines total by Phase 3 — still entirely manageable.

### Global State Migration

All 9 current flat-scope variables move into State:

| Current variable | Line | New home |
|------------------|------|----------|
| `originalFileName` | 512 | `State.originalFileName` |
| `originalHTML` | 514 | `State.originalHTML` |
| `history[]` | 517 | History-local (private inside IIFE, not in State) |
| `historyIndex` | 520 | History-local (private inside IIFE) |
| `zoom` | 523 | `State.zoom` |
| `addMode` | 526 | `State.addMode` |
| `highlightedWord` | 529 | `State.highlightedWord` |
| `hasUnsavedChanges` | 532 | `State.hasUnsavedChanges` |
| `draggedMarker` | 535 | `State.draggedMarker` |
| `dropTarget` | 543 | `State.dropTarget` |
| `autoSaveFailCount` | 704 | AutoSave-local (private) |

**Discretion decision (Claude):** `history[]` and `historyIndex` stay private inside the History IIFE — they are pure implementation detail that no other module needs to read. `autoSaveFailCount` stays private inside AutoSave. Everything else goes into State because other modules read those values.

### Event Contract

The EventBus events that Phase 1 must wire (and that Phase 2-5 will subscribe to):

| Event | Emitter | Listeners (Phase 1) | Payload |
|-------|---------|---------------------|---------|
| `markers:moved` | DragDrop | History | `{ marker, fromParent, toParent }` |
| `markers:added` | AddMode | History | `{ marker }` |
| `markers:deleted` | AddMode (edit/delete) | History | `{ pageNum }` |
| `markers:updated` | AddMode (edit/renumber) | History | `{ marker, oldPage }` |
| `file:loaded` | FileLoader | History (reset), AutoSave | `{ html, fileName }` |
| `history:restored` | History | DragDrop (re-attach listeners), AddMode (reset state) | none |

Phase 2 will add `Sidebar` as a subscriber to all `markers:*` and `file:loaded`. Phase 3 will add `Validation` as a subscriber. These slots are empty in Phase 1 but the events must still be emitted — the bus simply has no subscriber yet and that is fine.

**Discretion decision (Claude):** Keep event granularity fine-grained (separate events for moved/added/deleted/updated rather than a single `markers:changed`). Phase 3 Validation needs to know *which* mutation occurred to decide whether to re-run a full pass or a targeted check. Fine events are cheaper to add subscribers to than coarse events that require re-parsing a payload to determine mutation type.

### Pattern: Namespace Object

```javascript
// Source: .planning/research/ARCHITECTURE.md — recommended pattern
var DragDrop = (function() {
    // private state
    var _editor = null;

    function init(editorEl) {
        _editor = editorEl;
        _editor.addEventListener('mousemove', _onDrag);
        _editor.addEventListener('mouseup', _endDrag);
    }

    function _startDrag(e) { /* ... */ }
    function _onDrag(e)    { /* ... */ }
    function _endDrag(e)   { /* ... */ }

    return { init: init, startDrag: _startDrag };
})();
```

History uses IIFE for its private stack. Other namespaces (DragDrop, AddMode, Export) can use either plain objects or IIFEs — prefer IIFE when the namespace has private state that must not leak.

### Pattern: EventBus (build, do not import)

```javascript
// Source: .planning/research/ARCHITECTURE.md
var EventBus = (function() {
    var listeners = {};
    return {
        on:   function(event, fn) { (listeners[event] = listeners[event] || []).push(fn); },
        off:  function(event, fn) { if (listeners[event]) listeners[event] = listeners[event].filter(function(f) { return f !== fn; }); },
        emit: function(event, data) { (listeners[event] || []).forEach(function(fn) { fn(data); }); }
    };
})();
```

### Pattern: State Object

```javascript
// Source: .planning/research/ARCHITECTURE.md
var State = {
    originalFileName:   '',
    originalHTML:       '',
    zoom:               100,
    addMode:            false,
    hasUnsavedChanges:  false,
    draggedMarker:      null,
    dropTarget:         null,
    highlightedWord:    null,

    set: function(key, value) {
        this[key] = value;
        EventBus.emit('state:changed', { key: key, value: value });
    }
};
```

Modules that read State do so directly (`State.zoom`). Modules that write use `State.set('zoom', newValue)`.

### Pattern: Content Integrity on Marker Removal (INTG-01, INTG-02)

The current `moveMarker()` at line 1183–1187 already does:

```javascript
var oldParent = marker.parentNode;
marker.remove();
if (oldParent && oldParent !== parent) {
    oldParent.normalize();
}
```

The conditional `normalize()` only runs when old and new parents differ. After refactoring, **always normalize the old parent** — the conditional is a micro-optimization that obscures intent and can leave stale adjacent text nodes when moving within the same parent. The hardened invariant:

```javascript
// Source: current line 1183 hardened per D-04
var oldParent = marker.parentNode;
marker.remove();
if (oldParent) {
    oldParent.normalize();  // Always — merges adjacent text nodes left by removal
}
```

This is the **only** acceptable DOM operation on the source location. No unwrapping, no class removal, no attribute changes.

### Pattern: Export Diff Check (D-05 — new logic)

`prepareExportedBody()` must compare the cloned export DOM (with markers stripped) against `originalHTML` (parsed fresh) and warn on structural divergence:

```javascript
// New logic inside prepareExportedBody() — synthesis per D-05
function _buildStrippedText(rootEl) {
    // Walk text nodes only, skip .page-marker spans entirely
    var walker = document.createTreeWalker(rootEl, NodeFilter.SHOW_TEXT);
    var parts = [];
    var node;
    while ((node = walker.nextNode())) {
        if (!node.parentElement.closest('.page-marker, .page-number')) {
            parts.push(node.textContent);
        }
    }
    return parts.join('').replace(/\s+/g, ' ').trim();
}

// In prepareExportedBody(), after marker conversion:
var originalDoc = (new DOMParser()).parseFromString(State.originalHTML, 'text/html');
var exportedText  = _buildStrippedText(container);
var originalText  = _buildStrippedText(originalDoc.body);
if (exportedText !== originalText) {
    console.warn('[Export] Non-marker content differs from original.');
    // Show toast — do not block export, only warn
    showToast('Warning: content outside markers may have changed', 'error');
}
```

The check compares normalized text content (whitespace-collapsed, markers excluded). It does not do a byte-for-byte attribute comparison — that would be too noisy given whitespace normalization during editing. The goal is catching accidental text deletion or corruption, not formatting drift.

### Anti-Patterns to Avoid

- **Calling `saveState()` from multiple sites:** After refactoring, `saveState()` becomes `History._capture()` (private). The only path that triggers a snapshot is via EventBus. If someone adds a direct call to `History.capture()` from a module, it breaks decoupling.
- **Re-attaching drag listeners manually:** Any code that calls `setupMarkerDragging()` directly (bypassing `history:restored` event) will miss AddMode. After refactoring, both DragDrop and AddMode subscribe to `history:restored` to re-attach their listeners.
- **Storing element references across undo/redo:** Phase 2 will introduce Sidebar with element references. Establish the pattern in Phase 1 by ensuring `restoreState()` emits `history:restored` and documents that modules must not cache element references across that event.
- **Modifying marker CSS classes in Export path:** `prepareExportedBody()` clones the editor DOM and works only on the clone. It must never touch the live editor DOM.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Pub/Sub | Custom signal system, callbacks wired through function params | EventBus (inline, 20 lines) | Established pattern; prior research provides complete implementation |
| Marker queries | Duplicated `querySelectorAll('.page-marker')` in every module | `Markers.getAll()`, `Markers.getByPage()` | Central query point; all modules get same live DOM view |
| Marker creation | Inline `createElement('span')` + 4 `setAttribute` calls | `Markers.createMarker(pageNum, markerId)` | 4 current duplications identified; factory enforces attribute consistency |
| Text node merging | Custom merge loops | `parentNode.normalize()` | Native DOM API; handles all adjacent text node edge cases |
| Deep DOM clone | Serialize/deserialize | `element.cloneNode(true)` | Already used; correct for snapshot-based undo |

---

## Common Pitfalls

### Pitfall 1: Re-attaching Drag Listeners After History Restore
**What goes wrong:** `restoreState()` replaces all DOM children with fresh clones. Event listeners (mousedown, dblclick) attached to the old elements are gone.
**Why it happens:** `cloneNode(true)` does NOT copy event listeners — confirmed by MDN.
**How to avoid:** History emits `history:restored` after every restore. DragDrop and AddMode subscribe to `history:restored` and call their respective `_attachListeners()` functions.
**Warning signs:** After undo, dragging a marker has no effect.

### Pitfall 2: Missing Circular Dependency Between Namespaces
**What goes wrong:** History calls `AutoSave.save()` directly. AutoSave reads `State.originalHTML`. If AutoSave is defined after History in the script, the reference works at call time (not declaration time) — but if someone reorders sections, it silently breaks.
**Why it happens:** Section order matters for `var`/`function` hoisting. Object literals like `var AutoSave = {...}` are not hoisted.
**How to avoid:** Define sections in strict dependency order: EventBus → State → Markers → History → AutoSave → DragDrop → AddMode → Export → Toast → FileLoader → Init. Put a comment at the top: "SECTION ORDER IS LOAD ORDER — do not reorder."

### Pitfall 3: EventBus Emitted Before Subscribers Are Registered
**What goes wrong:** If `FileLoader.checkForSavedState()` is called before History and AutoSave have registered their `file:loaded` subscribers, the event fires with no listeners and history is not initialized.
**Why it happens:** `checkForSavedState()` runs on page load. If Init wires it before History.init(), the event fires into a vacuum.
**How to avoid:** Init must register all subscribers before calling `FileLoader.checkForSavedState()`. Init is the last section; all modules are already defined.

### Pitfall 4: Export Diff Check Triggered by Whitespace-Only Differences
**What goes wrong:** The diff check in `prepareExportedBody()` fires a warning on every file that was saved by the editor, because XMLSerializer normalizes whitespace differently from the original file.
**Why it happens:** The original file may have `\r\n` line endings; the editor's text nodes use `\n`. Spaces before/after markers are adjusted by the existing spacing normalization code.
**How to avoid:** Collapse whitespace in both comparison strings before comparing: `text.replace(/\s+/g, ' ').trim()`. The implementation pattern above already includes this. Do not compare raw innerHTML strings.

### Pitfall 5: `history:restored` Emitted Before DOM Is Fully Rebuilt
**What goes wrong:** DragDrop subscribes to `history:restored` and immediately calls `editor.querySelectorAll('.page-marker')`. If the event is emitted before `Array.from(savedEditor.childNodes).forEach(...)` finishes, the query finds zero markers.
**Why it happens:** Emitting an event partway through a synchronous DOM rebuild.
**How to avoid:** Emit `history:restored` at the very end of `restoreState()`, after all `appendChild` calls complete and `updateButtons()` / `updateStats()` have run.

### Pitfall 6: `normalize()` Merging the Target Text Node During Move
**What goes wrong:** When moving a marker, `marker.remove()` runs then `oldParent.normalize()` runs. If `target.node` is adjacent to the old location in the same parent, `normalize()` merges text nodes — invalidating `target.node` and `target.offset` which were captured before the remove.
**Why it happens:** `normalize()` merges ALL adjacent text nodes in the parent, potentially consuming the node that `dropTarget` is pointing at.
**How to avoid:** Capture the target position as `{ node, offset }` before removing the marker. After `normalize()`, check `target.node.isConnected` before using it — the existing code at line 1191 already does this. Preserve this check after refactoring.

---

## Code Examples

### EventBus (complete, ready to paste)

```javascript
// Source: .planning/research/ARCHITECTURE.md — EventBus section
var EventBus = (function() {
    var listeners = {};
    return {
        on: function(event, fn) {
            (listeners[event] = listeners[event] || []).push(fn);
        },
        off: function(event, fn) {
            if (listeners[event]) {
                listeners[event] = listeners[event].filter(function(f) { return f !== fn; });
            }
        },
        emit: function(event, data) {
            (listeners[event] || []).forEach(function(fn) { fn(data); });
        }
    };
})();
```

### State (complete, ready to paste)

```javascript
// Source: .planning/research/ARCHITECTURE.md — State section
var State = {
    originalFileName: '',
    originalHTML: '',
    zoom: 100,
    addMode: false,
    hasUnsavedChanges: false,
    draggedMarker: null,
    dropTarget: null,
    highlightedWord: null,

    set: function(key, value) {
        this[key] = value;
        EventBus.emit('state:changed', { key: key, value: value });
    }
};
```

### History (IIFE with EventBus wiring)

```javascript
// Source: synthesis — ARCHITECTURE.md History section + current lines 1237–1306
var History = (function() {
    var stack = [];
    var index = -1;
    var MAX = 50;
    var _editor = null;

    function _capture() {
        if (index < stack.length - 1) { stack = stack.slice(0, index + 1); }
        stack.push(_editor.cloneNode(true));
        index = stack.length - 1;
        if (stack.length > MAX) { stack.shift(); index--; }
        State.set('hasUnsavedChanges', true);
        AutoSave.save();
        _updateButtons();
        updateStats();  // updateStats remains accessible — called here directly
    }

    function _restore(savedEditor) {
        _editor.textContent = '';
        Array.from(savedEditor.childNodes).forEach(function(node) {
            _editor.appendChild(node.cloneNode(true));
        });
        _editor.classList.remove('empty');
        _updateButtons();
        updateStats();
        EventBus.emit('history:restored');  // AFTER DOM is fully rebuilt
    }

    function _updateButtons() {
        document.getElementById('undoBtn').disabled = index <= 0;
        document.getElementById('redoBtn').disabled = index >= stack.length - 1;
    }

    // Subscribe to all mutation events — never call capture() directly
    EventBus.on('markers:moved',   _capture);
    EventBus.on('markers:added',   _capture);
    EventBus.on('markers:deleted', _capture);
    EventBus.on('markers:updated', _capture);

    return {
        undo: function() { if (index > 0) { index--; _restore(stack[index]); } },
        redo: function() { if (index < stack.length - 1) { index++; _restore(stack[index]); } },
        reset: function(editorEl) {
            _editor = editorEl;
            stack = [_editor.cloneNode(true)];
            index = 0;
            _updateButtons();
        }
    };
})();
```

### DragDrop — endDrag emitting instead of calling saveState

```javascript
// Source: current lines 1157–1206 refactored
function _endDrag(e) {
    document.removeEventListener('mousemove', _onDrag);
    document.removeEventListener('mouseup', _endDrag);

    if (!State.draggedMarker || !State.dropTarget) {
        State.set('draggedMarker', null);
        State.set('dropTarget', null);
        DragDrop.hideDropCursor();
        return;
    }

    DragDrop.moveMarker(State.draggedMarker, State.dropTarget);
    // emit AFTER moveMarker succeeds — History._capture() subscribes to this
    EventBus.emit('markers:moved', { marker: State.draggedMarker });

    State.set('draggedMarker', null);
    State.set('dropTarget', null);
    DragDrop.hideDropCursor();
}
```

### FileLoader — emitting file:loaded

```javascript
// Source: current lines 595–612 refactored
fileInput.addEventListener('change', function(e) {
    var file = e.target.files[0];
    if (!file) return;
    var reader = new FileReader();
    reader.onload = function(e) {
        State.set('originalHTML', e.target.result);
        State.set('originalFileName', file.name);
        loadContent(State.originalHTML);
        EventBus.emit('file:loaded', { html: State.originalHTML, fileName: State.originalFileName });
        showToast('File loaded successfully', 'success');
    };
    reader.readAsText(file);
});
```

---

## State of the Art

| Old Pattern | Phase 1 Pattern | Used By Phase |
|-------------|-----------------|---------------|
| Flat-scope `var history = []` | `History` IIFE with private stack | Phase 1 |
| `saveState()` called from 6 sites | `EventBus.emit('markers:moved')` — History subscribes | Phase 1 |
| `setupMarkerDragging()` called directly | `EventBus.on('history:restored', ...)` re-attaches | Phase 1 |
| `updateStats()` called everywhere | Remains a shared utility; Phase 2 replaces with `Sidebar.render()` | Phase 2 |
| 4 inline marker creation blocks | `Markers.createMarker(pageNum, markerId)` | Phase 1 |

---

## Open Questions

1. **`updateStats()` ownership after refactoring**
   - What we know: `updateStats()` writes to `statsEl` (toolbar count). It is called from `saveState()`, `loadContent()`, `checkForSavedState()`, and `restoreState()`.
   - What's unclear: Should it become `UI.updateStats()` or stay a free function called from History's `_capture()` and `_restore()`?
   - Recommendation: Make it `UI.updateStats()` and call it from History's private `_capture()` and `_restore()` functions. Phase 2 will likely replace or augment it when the Sidebar renders a full marker list. Keeping it in a UI namespace makes that transition explicit.

2. **`updateButtons()` — where does it live?**
   - What we know: It only touches `undoBtn.disabled` and `redoBtn.disabled` — UI concerns driven entirely by History state.
   - What's unclear: History private vs UI namespace?
   - Recommendation: Keep it private inside the History IIFE as `_updateButtons()`. It has no use case outside History. The implementation above reflects this.

3. **`checkForSavedState()` — where does it live?**
   - What we know: It reads localStorage, prompts user, restores `editor.innerHTML`, then calls `setupMarkerDragging()`, `updateButtons()`, `updateStats()`.
   - What's unclear: It currently acts like a second `loadContent()` path. Should it go in AutoSave or FileLoader?
   - Recommendation: `AutoSave.checkForSavedState()`. It is a recovery function that AutoSave owns. After restoring, it emits `file:loaded` so History, DragDrop, and AddMode re-initialize from the same event channel as a regular file load.

---

## Environment Availability

Step 2.6: SKIPPED — this phase is code-only refactoring of a browser HTML file. No external tools, CLI utilities, databases, or runtimes beyond a web browser are required.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | Manual browser testing only (no automated JS test framework in project) |
| Config file | None |
| Quick run command | Open `tools/page-marker-editor.html` in browser, load `examples/sample_with_markers.html` |
| Full suite command | Same + run through complete smoke checklist below |

From `CONCERNS.md`: "Browser tools have zero automated tests — manual testing is acceptable for the current scope."

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Verification |
|--------|----------|-----------|-------------|
| ARCH-01 | Namespace objects exist, flat globals gone | Manual — inspect console | `typeof DragDrop === 'object'` etc.; no `window.history`, `window.addMode` |
| ARCH-02 | EventBus wired — drag emits `markers:moved`, History receives it | Manual — add `EventBus.on('markers:moved', console.log)` in console, drag a marker | Console shows event payload |
| ARCH-03 | State object holds all app state | Manual — inspect `State` in console after loading file | All keys present with correct values |
| ARCH-04 | Single factory function; no inline createElement with marker attrs | Code review — grep for `createElement('span')` outside `Markers.createMarker` | Zero matches outside factory |
| INTG-01 | Drag marker; surrounding text/elements unchanged | Manual — load article HTML, drag marker, inspect source before/after | No attribute loss on surrounding elements |
| INTG-02 | No orphaned empty spans after move | Manual — load HTML, drag marker 10 times, run `editor.querySelectorAll('span:empty')` in console | Count = 0 (or only expected empties) |
| INTG-03 | Export diff check fires on corrupted content | Manual — load HTML, manually delete a word in devtools, click Download | Warning toast appears |
| INTG-04 | Undo restores exact state | Manual — move 3 markers, undo 3 times, compare innerHTML | Matches original |

### Smoke Checklist (run after refactoring each section)

1. Load `examples/sample_with_markers.html` — file loads, markers appear as red badges
2. Drag a marker to a new position — marker moves, count unchanged
3. Double-click a marker — edit dialog appears; change number; marker updates
4. Double-click a marker — edit dialog; leave empty; marker deleted
5. Ctrl+Z × 3 — three states restored correctly
6. Ctrl+Y × 3 — three states re-applied correctly
7. Click "+ Add Marker" — add mode active; click a word; enter number; marker inserted
8. Press Escape — add mode exits, no highlight left in DOM
9. Click "Download Corrected HTML" — file downloads; open downloaded file; markers use EPUB format
10. Click "Copy Body Content" — clipboard has body HTML with EPUB marker format
11. Zoom in/out — text reflows; drag still works at new zoom

### Wave 0 Gaps

None — existing sample file covers all tests. No test framework installation needed.

---

## Sources

### Primary (HIGH confidence)
- `.planning/research/ARCHITECTURE.md` — Namespace module pattern, EventBus design, State object, build order, data flow diagrams
- `.planning/research/PITFALLS.md` — Event listener re-attachment, stale references, normalize() behavior
- `.planning/research/STACK.md` — Browser API recommendations, zoom coordinate space
- `.planning/codebase/CONCERNS.md` — Known bugs, fragile areas
- `.planning/codebase/CONVENTIONS.md` — Code style (JS section: comment style, section headers)
- `tools/page-marker-editor.html` lines 507–543 — State variables audit (direct source read)
- `tools/page-marker-editor.html` lines 644–697 — `loadContent()` marker creation site 1 (direct source read)
- `tools/page-marker-editor.html` lines 1157–1206 — `moveMarker()` marker creation site 2 (direct source read)
- `tools/page-marker-editor.html` lines 1557–1608 — `insertMarkerAfterWord()` marker creation site 3 (direct source read)
- `tools/page-marker-editor.html` lines 1656–1731 — `prepareExportedBody()` marker creation site 4 + export logic (direct source read)
- `tools/page-marker-editor.html` lines 1237–1306 — History system (direct source read)
- MDN: Node.cloneNode() — confirmed: no event listener copying
- MDN: Node.normalize() — merges adjacent text nodes

### Secondary (MEDIUM confidence)
- Revealing Module Pattern: patterns.dev/vanilla/module-pattern
- EventBus in vanilla JS: CSS-Tricks lightweight native event bus

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new libraries; all patterns verified in prior research and source code
- Architecture: HIGH — prior research is authoritative; direct source mapping confirmed all 4 duplication sites and all 9 globals
- Pitfalls: HIGH — most pitfalls sourced from direct source analysis and prior research with MDN verification

**Research date:** 2026-03-31
**Valid until:** No expiry — pure vanilla JS, no library versions to go stale. Re-validate if browser compatibility targets change.
