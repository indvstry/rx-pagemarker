# Architecture Patterns: Single-File Vanilla JS Editor

**Domain:** Browser-based visual marker editor (single HTML file, no build step)
**Researched:** 2026-03-30
**Confidence:** HIGH — recommendations based on observed current code structure + established vanilla JS patterns

---

## Recommended Architecture

### The Core Constraint

The single-file constraint is real and non-negotiable. The architecture must work within it, not fight it. The solution is **namespace-based module simulation**: organize code into named objects (modules) within a single script block, with a minimal shared event bus for cross-module communication. This achieves the same isolation benefits of actual ES modules without any build tooling.

No IIFE wrapping is recommended for this codebase. IIFEs add syntactic noise and the file is not a library that risks global namespace collision — it is the entire application. Namespace objects are simpler, equally effective, and easier to navigate in a single file.

---

## Recommended Structure

The current file mixes concerns: state variables, DOM references, utility functions, drag logic, add-mode logic, history, auto-save, export, and toast — all at the same flat scope. The new features (sidebar, search, validation) will each add another 150-400 lines. Without structure, the file becomes unmaintainable past ~2500 lines.

The recommended approach: **namespace objects as logical modules**, communicating through a **central state object** and a **lightweight event bus**.

### Structural Layout (within the single `<script>` block)

```
SECTION 1: CSS  (unchanged)
SECTION 2: HTML (add sidebar markup here)
SECTION 3: <script>
  ├── 1. EventBus            (~20 lines)  — publish/subscribe, decouples modules
  ├── 2. State               (~30 lines)  — single source of truth, no scattered globals
  ├── 3. Markers             (~50 lines)  — query/read markers from DOM, no mutation
  ├── 4. History             (~80 lines)  — undo/redo (mostly unchanged from current)
  ├── 5. AutoSave            (~60 lines)  — localStorage (mostly unchanged)
  ├── 6. DragDrop            (~200 lines) — drag, caret, snap-to-word
  ├── 7. ClickMove           (~150 lines) — new: click-to-move alternative
  ├── 8. AddMode             (~150 lines) — add mode (mostly unchanged)
  ├── 9. Sidebar             (~200 lines) — new: marker list panel
  ├── 10. Search             (~100 lines) — new: jump-to-page-number
  ├── 11. Validation         (~180 lines) — new: out-of-order, gap, position warnings
  ├── 12. Export             (~120 lines) — download + copy (mostly unchanged)
  ├── 13. Toast              (~40 lines)  — notifications (unchanged)
  ├── 14. FileLoader         (~100 lines) — file loading (mostly unchanged)
  ├── 15. Init               (~50 lines)  — wires everything together on DOMContentLoaded
  └── (total estimate: ~1580 lines new + ~500 lines existing CSS/HTML = ~2100 lines)
```

The Init section is the only place that reaches across namespaces to attach event listeners. All other namespaces communicate via EventBus.

---

## Component Boundaries

### EventBus

**Responsibility:** Publish/subscribe hub. Nothing else.

**Implementation (build it, do not import a library):**
```javascript
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

**Events to define (the contract between modules):**

| Event | Emitter | Listeners | Payload |
|-------|---------|-----------|---------|
| `state:changed` | State | Sidebar, Validation, History | `{ key, value }` |
| `markers:moved` | DragDrop, ClickMove | History, Sidebar, Validation | `{ marker, from, to }` |
| `markers:added` | AddMode | History, Sidebar, Validation | `{ marker }` |
| `markers:deleted` | AddMode, DragDrop | History, Sidebar, Validation | `{ pageNum }` |
| `markers:updated` | AddMode | History, Sidebar, Validation | `{ marker, oldPage }` |
| `file:loaded` | FileLoader | Sidebar, Validation, History, AutoSave | `{ html, fileName }` |
| `history:restored` | History | DragDrop, AddMode, Sidebar, Validation | none |
| `sidebar:jump` | Sidebar | Editor scroll | `{ pageNum }` |
| `validation:run` | Validation | Validation (internal) | none |

**Communicates with:** Everything. It is the backbone.

---

### State

**Responsibility:** Hold all application-level variables in one place. No logic — just data.

**Replaces:** The current scattered globals (`originalFileName`, `originalHTML`, `history`, `historyIndex`, `zoom`, `addMode`, `hasUnsavedChanges`, `draggedMarker`, `dropTarget`, `highlightedWord`).

```javascript
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

**Communicates with:** EventBus (emits on `set`). All other modules read from `State` directly; they write via `State.set()`.

---

### Markers

**Responsibility:** Read and query markers. Does NOT mutate the DOM — mutation is done by the calling module.

```javascript
var Markers = {
    getAll: function() {
        return Array.from(document.getElementById('editor').querySelectorAll('.page-marker'));
    },
    getPageNumbers: function() {
        return Markers.getAll().map(function(m) {
            return parseInt(m.getAttribute('data-page'), 10);
        }).filter(function(n) { return !isNaN(n); });
    },
    getByPage: function(pageNum) {
        return document.querySelector('.page-marker[data-page="' + pageNum + '"]');
    },
    createMarkerElement: function(pageNum, id) {
        var span = document.createElement('span');
        span.className = 'page-marker';
        span.setAttribute('data-page', String(pageNum));
        span.setAttribute('data-id', id || 'marker-' + Date.now());
        span.setAttribute('draggable', 'true');
        span.textContent = String(pageNum);
        return span;
    }
};
```

**Why separate:** The current code re-implements marker creation in four places (`moveMarker`, `insertMarkerAfterWord`, `loadContent`, and the export path). Centralizing marker element creation and queries here eliminates that duplication.

**Communicates with:** DOM only (read). Called by DragDrop, AddMode, Sidebar, Validation, Export.

---

### History

**Responsibility:** Undo/redo via full DOM snapshots of the editor element.

**Change from current:** Instead of calling `saveState()` directly, mutation operations emit a bus event and History listens. This decouples History from every caller.

```javascript
var History = (function() {
    var stack = [];
    var index = -1;
    var MAX = 50;
    var editor = null;

    function capture() {
        if (index < stack.length - 1) { stack = stack.slice(0, index + 1); }
        stack.push(editor.cloneNode(true));
        index = stack.length - 1;
        if (stack.length > MAX) { stack.shift(); index--; }
        AutoSave.save();
        _updateButtons();
    }

    // ... undo(), redo(), restore(), _updateButtons() as before

    EventBus.on('markers:moved',   capture);
    EventBus.on('markers:added',   capture);
    EventBus.on('markers:deleted', capture);
    EventBus.on('markers:updated', capture);

    return { undo, redo, init: function(el) { editor = el; } };
})();
```

**Communicates with:** EventBus (listens), AutoSave (calls directly after capture), DOM editor element (reads/writes).

---

### DragDrop

**Responsibility:** Mouse-event drag of existing markers to new word boundaries. Owns `startDrag`, `onDrag`, `endDrag`, `getCaretPosition`, `snapToWordBoundary`, `showDropCursor`, `hideDropCursor`, `moveMarker`.

**Key change:** After a successful drop, emits `markers:moved` instead of calling `saveState()` directly. History and Sidebar subscribe independently.

**Communicates with:** EventBus (emits `markers:moved`), State (reads `draggedMarker`, `dropTarget`; writes via `State.set()`), DOM (direct manipulation).

---

### ClickMove

**Responsibility:** Two-click move mode. Click a marker to "pick it up", then click a word position to "place it". This is new functionality.

**Interaction model:**
1. User clicks a marker → it becomes "selected" (visual highlight, different CSS class)
2. Document enters click-move mode (cursor changes, words become clickable targets)
3. User clicks a word position → marker moves there, mode exits
4. Escape cancels selection

**State needed:** `clickMoveMarker` (the selected marker element, or null).

**Why separate from DragDrop:** Drag and click-move are mutually exclusive interaction modes with different state, different event listeners, and different visual feedback. Sharing a namespace would require complex mode-switching flags. Separate namespaces communicate cleanly via EventBus: when ClickMove enters its mode, it can emit a `clickmove:active` event that DragDrop listens to and suppresses its `mousedown` handler.

**Communicates with:** EventBus (emits `markers:moved`, listens to `history:restored`), State, DOM.

---

### AddMode

**Responsibility:** Click-on-word to insert new marker. Mostly unchanged from current implementation. Extracted into namespace.

**Communicates with:** EventBus (emits `markers:added`), State (`addMode` flag), DOM.

---

### Sidebar

**Responsibility:** Render the marker list panel. Sync itself when markers change. Handle click-to-jump navigation.

**UI structure:**
```
┌──────────────────────────────────────────┐
│  [Sidebar panel, left side, 220px wide]  │
│                                          │
│  Search: [____________________]          │
│                                          │
│  ● 775  (green = in-order)               │
│  ● 776  (green)                          │
│  ▲ 778  (yellow = gap: 777 missing)      │
│  ✕ 801  (red = out of order after 778)   │
│  ● 779                                   │
│  ...                                     │
│                                          │
│  [228 markers]                           │
└──────────────────────────────────────────┘
```

**Implementation approach:**
- Sidebar is a `<div>` in the HTML alongside the existing `.instructions` panel. Replace the static instructions div with a two-tab layout: "Instructions" tab and "Markers" tab.
- Marker list uses a `<ul>` with `<li>` per marker. Each `<li>` has a click handler that calls `Sidebar.jumpTo(pageNum)`.
- `jumpTo` scrolls the editor to the marker's `getBoundingClientRect()` position.
- Sidebar re-renders its list on `file:loaded`, `markers:moved`, `markers:added`, `markers:deleted`, `markers:updated`, and `history:restored` events.
- Validation status icons (green/yellow/red) are fed from Validation module via a shared data structure, updated after each validation pass.

**Performance note:** Re-rendering a list of 200+ `<li>` elements on every change is fine with vanilla DOM manipulation (no virtual DOM needed). Create an `<ul>`, build all `<li>` elements, replace old `<ul>` in one DOM operation. At 230 markers, this is sub-millisecond.

**Communicates with:** EventBus (listens to all `markers:*` and `file:loaded` events), Validation (reads results to show icons), DOM.

---

### Search

**Responsibility:** Input field for jumping to a specific page number. Lives in the sidebar.

**Interaction model:**
1. User types a page number in the search input
2. As they type, the first matching marker scrolls into view (live search)
3. If no match: brief red outline on input
4. Enter key: same as clicking on the matched sidebar item

**Implementation:** ~30 lines. Attach `input` event listener to a text `<input>`. Call `Markers.getByPage(value)` and scroll to result. This is simple enough that it does not need its own namespace — it belongs inside Sidebar as `Sidebar.initSearch()`.

**Communicates with:** Sidebar (part of), Markers (query), DOM (scroll).

---

### Validation

**Responsibility:** Analyze the current marker sequence and produce a list of issues. Issues are consumed by Sidebar for display and by the editor for visual overlays.

**Validation checks to implement:**

| Check | What it Detects | Severity |
|-------|----------------|----------|
| Out-of-order | Page N+1 marker appears before page N in DOM | Error (red) |
| Gap | Page numbers skip more than 1 (e.g., 776 then 778) | Warning (yellow) |
| Duplicate | Same page number appears twice (not an intentional two-column case) | Warning (yellow) |
| Position | Marker is inside a heading or footnote element | Info (blue) |

**Output format:**
```javascript
// Validation.run() returns:
[
  { type: 'out-of-order', pageNum: 801, message: '801 appears before 779 in document' },
  { type: 'gap',          pageNum: 777, message: '777 is missing (776 → 778)' },
  { type: 'position',     pageNum: 783, message: '783 is inside a heading element' }
]
```

**When validation runs:** After every mutation (subscribe to all `markers:*` events). Validation is synchronous and fast (one DOM traversal to collect ordered page numbers, then a single pass comparison). On a 230-marker document this is under 5ms.

**Visual overlay on the editor:** When a marker has an error/warning, add a CSS class to the `.page-marker` span in the editor (`page-marker--error`, `page-marker--warning`). Remove them before each validation pass, re-add based on results. This requires no extra DOM elements — just CSS class toggling.

**Communicates with:** EventBus (listens to `markers:*`, emits `validation:complete` with results array), DOM (adds/removes CSS classes on marker spans), Sidebar (Sidebar subscribes to `validation:complete`).

---

### Export

**Responsibility:** `prepareExportedBody()`, download handler, copy-body handler. Unchanged from current implementation, extracted into namespace.

**Communicates with:** State (`originalHTML`, `originalFileName`), DOM (editor element), AutoSave (clears after download).

---

### AutoSave

**Responsibility:** localStorage persistence. Unchanged from current, extracted into namespace.

**Communicates with:** State (reads `originalHTML`), DOM (reads editor `innerHTML`), EventBus (none — called directly by History after capture).

---

### Toast

**Responsibility:** `showToast(message, type)`. Unchanged, extracted into namespace.

**Communicates with:** DOM only.

---

### FileLoader

**Responsibility:** File input change handler, `loadContent()`, `checkForSavedState()`. Emits `file:loaded` when content is ready.

**Key change:** Currently `loadContent()` calls `setupMarkerDragging()` directly. In the new structure, it emits `file:loaded` and DragDrop and ClickMove subscribe to re-attach their event listeners after a load.

**Communicates with:** EventBus (emits `file:loaded`), State (writes `originalHTML`, `originalFileName`), Markers (calls `createMarkerElement` during conversion), DOM.

---

### Init

**Responsibility:** Called once on `DOMContentLoaded`. Initializes all modules with their DOM element references, attaches button click handlers, calls `FileLoader.checkForSavedState()`.

```javascript
document.addEventListener('DOMContentLoaded', function() {
    var editor = document.getElementById('editor');
    History.init(editor);
    DragDrop.init(editor);
    ClickMove.init(editor);
    AddMode.init(editor);
    Sidebar.init(document.getElementById('sidebar-panel'));
    Validation.init(editor);
    FileLoader.init(document.getElementById('fileInput'), editor);

    // Toolbar button wiring
    document.getElementById('undoBtn').addEventListener('click', History.undo);
    document.getElementById('redoBtn').addEventListener('click', History.redo);
    document.getElementById('addModeBtn').addEventListener('click', AddMode.toggle);
    document.getElementById('downloadBtn').addEventListener('click', Export.download);
    document.getElementById('copyBodyBtn').addEventListener('click', Export.copyBody);
    document.getElementById('zoomIn').addEventListener('click', function() { Zoom.change(10); });
    document.getElementById('zoomOut').addEventListener('click', function() { Zoom.change(-10); });

    FileLoader.checkForSavedState();
});
```

**Communicates with:** All modules (initialization only). After init, modules communicate via EventBus.

---

## Data Flow

### File Load Flow

```
User selects file
  → FileLoader reads via FileReader API
  → FileLoader converts semantic markers to editor markers (.page-marker)
  → FileLoader copies body into #editor
  → FileLoader emits file:loaded
      → History.init (reset stack)
      → DragDrop (re-attach mousedown to all .page-marker)
      → ClickMove (re-attach click listeners)
      → Sidebar (render marker list)
      → Validation.run() (initial pass)
      → AutoSave.save()
```

### Marker Move (Drag) Flow

```
mousedown on .page-marker
  → DragDrop.startDrag() — sets State.draggedMarker
  → mousemove → DragDrop.onDrag() — updates dropCursor position
  → mouseup → DragDrop.endDrag()
      → DragDrop.moveMarker() — DOM: remove from old position, insert at new
      → EventBus.emit('markers:moved')
          → History.capture() → AutoSave.save()
          → Sidebar.render()
          → Validation.run() → EventBus.emit('validation:complete')
              → Sidebar.updateIcons()
              → editor: CSS classes updated on affected markers
```

### Marker Move (Click-Move) Flow

```
click on .page-marker (when NOT in addMode)
  → ClickMove.selectMarker() — adds 'selected' class, sets State.clickMoveMarker
  → editor enters click-move mode (CSS cursor change, Escape handler)
  → click anywhere in editor text
      → ClickMove resolves caret position, snaps to word boundary
      → ClickMove.placeMarker() — same DOM manipulation as DragDrop.moveMarker()
      → EventBus.emit('markers:moved')
          → (same downstream chain as drag flow above)
```

### Validation Flow

```
EventBus.emit('markers:*') or EventBus.emit('history:restored')
  → Validation.run()
      → Collect all .page-marker elements in DOM order → [pageNums]
      → Compare to sorted [pageNums] → detect out-of-order
      → Walk consecutive pairs → detect gaps
      → Check for duplicates (not adjacent) → flag
      → Check parent elements → detect heading/footnote position
      → Remove old CSS classes from all markers
      → Apply new CSS classes to flagged markers
      → EventBus.emit('validation:complete', issues[])
          → Sidebar.updateIcons(issues)
```

### Sidebar Jump Flow

```
User clicks marker in sidebar list
  → Sidebar.jumpTo(pageNum)
      → element = Markers.getByPage(pageNum)
      → element.scrollIntoView({ behavior: 'smooth', block: 'center' })
      → brief CSS highlight on the marker (500ms, then remove)
```

---

## Layout Change for Sidebar

The current layout is:

```
┌─────────────────────────────────────────────┐
│  .instructions (280px)  │  .editor-area     │
│  (static how-to text)   │                   │
└─────────────────────────────────────────────┘
```

The new layout replaces `.instructions` with a tabbed panel:

```
┌─────────────────────────────────────────────┐
│  [Instructions] [Markers]  │  .editor-area  │
│  ─────────────────────     │                │
│  (tab content, 280px)      │                │
└─────────────────────────────────────────────┘
```

Tab switching is pure CSS with a class toggle: `sidebar.classList.toggle('show-markers')`. No JavaScript tab routing needed.

The "Markers" tab content:
```html
<div id="sidebar-panel">
    <div class="sidebar-search">
        <input type="text" id="markerSearch" placeholder="Jump to page..." />
    </div>
    <ul id="markerList">
        <!-- Rendered by Sidebar module -->
    </ul>
    <div class="sidebar-footer">
        <span id="sidebarStats"></span>
    </div>
</div>
```

---

## Build Order (Phase Dependencies)

The features have clear dependencies that determine implementation order:

### Phase 1: Structural Refactoring (prerequisite for everything)

Reorganize the existing 1854 lines into namespace objects without changing any behavior. This is the foundation — all new features assume this structure.

**Deliverable:** Same behavior, organized code. All globals moved into State. Functions wrapped in namespace objects. EventBus wired between modules. Regression tested manually.

**No new features. No new tests. Just reorganization.**

### Phase 2: Sidebar + Search

Requires Phase 1 (needs `file:loaded` and `markers:*` events to be wired). Sidebar depends on Markers module being a clean query API.

Add sidebar HTML, Sidebar namespace, Search inside Sidebar. Tab UI for Instructions/Markers panels.

**Unblocks:** Validation (validation icons need sidebar to display them).

### Phase 3: Validation

Requires Phase 2 (sidebar icons). The validation logic itself is independent, but displaying results requires the sidebar list to exist.

Add Validation namespace. Add CSS classes for error/warning state. Wire `validation:complete` event to Sidebar icon updates.

**Unblocks:** Nothing — this is a terminal feature, not a dependency.

### Phase 4: ClickMove

Requires Phase 1 (needs EventBus for `markers:moved`). Independent of Sidebar and Validation.

Add ClickMove namespace. Add CSS for selected state. Wire mutual exclusion with AddMode and DragDrop via State flags.

**Unblocks:** Nothing — terminal feature.

### Phase 5: Drag-Drop Precision Improvements

Requires Phase 1. Independent.

The existing drag system works but precision suffers when text is densely packed. The improvement is in `snapToWordBoundary` — currently it snaps to the nearest boundary of the word under the cursor, but it does not prefer gap positions (whitespace between words). Improved algorithm:

1. Check if cursor is already in whitespace → use that position directly
2. If in a word, find both boundaries of that word
3. Prefer the boundary that has adjacent whitespace (a true gap between words)
4. If both are word boundaries (no whitespace), snap to the closer one

This is a targeted change to the existing `snapToWordBoundary` function, not a new module. Can be done independently of all other phases.

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Circular Dependencies Between Namespaces

**What goes wrong:** Sidebar calls Validation, Validation calls Markers, Markers calls Sidebar → import loops, initialization order problems.

**Prevention:** One-way data flow via EventBus. Sidebar does not call Validation directly. Validation emits results; Sidebar consumes them. Markers is read-only and has no dependencies. The direction is always: mutation → EventBus → side-effect consumers.

### Anti-Pattern 2: DOM as State

**What goes wrong:** Two modules query `.page-marker` elements to answer different questions, getting subtly different results depending on timing, normalize() calls, or in-progress drag operations.

**Prevention:** Mutations happen atomically (complete DOM change before emitting event). `Markers.getAll()` is called by consumers only in response to events (never during an in-progress drag). During drag, DragDrop tracks its own `draggedMarker` reference via State.

### Anti-Pattern 3: Monolithic `saveState()` Call Sites

**What goes wrong:** Current code calls `saveState()` from 6+ different places. Adding History as an EventBus subscriber means someone might still add a `saveState()` call instead of emitting an event, creating duplicate history entries.

**Prevention:** Remove `saveState()` as a public function. It becomes `History._capture()` (private). The only way to trigger history capture is via EventBus events. Document this in a comment at the top of the History namespace.

### Anti-Pattern 4: Re-attaching Event Listeners After History Restore

**What goes wrong:** Current `restoreState()` calls `setupMarkerDragging()` to re-attach event listeners to newly created marker elements. After refactoring, forgetting to do this in ClickMove, AddMode, and DragDrop after history restore causes broken interactions.

**Prevention:** History emits `history:restored` after every restore. DragDrop, ClickMove, and AddMode all subscribe to this event and re-attach their per-marker listeners. AddMode and ClickMove may additionally need to reset any active mode state.

### Anti-Pattern 5: Validation in the Critical Path

**What goes wrong:** Validation runs synchronously after every mutation. If it becomes slow (e.g., walking the entire DOM to check heading ancestors for all 230 markers), it blocks the UI.

**Prevention:** Keep validation scoped. The heading/footnote check for position warnings should walk up the ancestor chain for each marker once (short chain — typically 3-5 levels) rather than traversing the full document. Total cost is O(N * depth) not O(N * document_size). If it becomes a bottleneck, defer with `requestAnimationFrame`.

---

## Scalability Considerations

| Concern | At 50 markers | At 230 markers | At 1000 markers |
|---------|---------------|----------------|-----------------|
| History snapshots | ~50KB/snapshot | ~200KB/snapshot | ~1MB/snapshot — reduce MAX from 50 to 20 |
| Sidebar render | <1ms | <5ms | ~20ms — add virtual scroll if needed |
| Validation pass | <1ms | <5ms | ~20ms — acceptable for background pass |
| Drag performance | smooth | smooth | smooth — O(1) per mousemove |

The realistic upper bound for this tool is ~300 markers (a single large magazine issue). No virtual scroll or deferred rendering is needed at that scale.

---

## Sources

- Current code analysis: `/Users/ariskaratarakis/_projects/rx-pagemarker/tools/page-marker-editor.html` (1854 lines, read directly)
- Revealing Module Pattern: [patterns.dev/vanilla/module-pattern](https://www.patterns.dev/vanilla/module-pattern/)
- EventBus in vanilla JS: [CSS-Tricks — Lightweight Native Event Bus](https://css-tricks.com/lets-create-a-lightweight-native-event-bus-in-javascript/)
- Pub/Sub best practices: [freeCodeCamp — Event-Based Architectures in JavaScript](https://www.freecodecamp.org/news/event-based-architectures-in-javascript-a-handbook-for-devs/)
- Vanilla JS project structure: [gomakethings.com — How I structure my vanilla JS projects](https://gomakethings.com/how-i-structure-my-vanilla-js-projects/)
- Extensible vanilla JS: [gomakethings.com — Building an extensible app with vanilla JS](https://gomakethings.com/building-an-extensible-app-or-library-with-vanilla-js/)

---

*Analysis date: 2026-03-30*
