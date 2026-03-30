# Technology Stack

**Project:** RX Page Marker — Visual Editor Improvements
**Researched:** 2026-03-30
**Scope:** Browser-side only. This research covers the `tools/page-marker-editor.html`
single-file editor exclusively. Python CLI stack is unchanged.

---

## Context: What Already Exists

The editor is ~1854 lines of vanilla JS in a single HTML file. The relevant
existing techniques that this research builds on:

| Existing technique | Where used | Quality |
|---|---|---|
| `mousedown/mousemove/mouseup` custom drag | `startDrag / onDrag / endDrag` | Good — correct choice over HTML5 Drag API |
| `caretRangeFromPoint` (Chrome/Safari) + `caretPositionFromPoint` (Firefox) | `getCaretPosition()` | Needs update — Chrome 128+ now supports the standard |
| `snapToWordBoundary()` — scans text node for whitespace boundaries | in `onDrag` | Good — correct approach |
| DOM `cloneNode(true)` history stack | `saveState / restoreState` | Good — simple, correct |
| `localStorage` auto-save | `autoSave()` | Good |
| Left sidebar (280 px, instructions only) | CSS `.instructions` | Repurpose this panel for marker list |

---

## Recommended Techniques by Feature Area

### 1. Drag-and-Drop Precision

**Verdict:** The existing mouse-event system is correct. The precision problem is
not the dragging mechanism — it is the drop cursor height and the word-snapping
threshold.

**What to change:**

**Use `caretPositionFromPoint` as the primary API** (both branches, drop the
`caretRangeFromPoint` primary path). Chrome shipped `caretPositionFromPoint` in
Chrome 128 (August 2024, HIGH confidence — chromestatus.com entry confirmed).
Safari Technology Preview 226 (August 2025) added it; production Safari 18.x
still uses `caretRangeFromPoint`. Keep the two-branch fallback but reverse
priority to standard-first:

```js
function getCaretPosition(x, y) {
    // Standard (Chrome 128+, Firefox, Safari TP 226+)
    if (document.caretPositionFromPoint) {
        const pos = document.caretPositionFromPoint(x, y);
        if (pos) return { node: pos.offsetNode, offset: pos.offset };
    }
    // Legacy fallback (Safari 18.x production)
    if (document.caretRangeFromPoint) {
        const range = document.caretRangeFromPoint(x, y);
        if (range) return { node: range.startContainer, offset: range.startOffset };
    }
    return null;
}
```

**Why this matters:** `caretPositionFromPoint` returns a `CaretPosition` object
that correctly handles Shadow DOM and some edge cases with positioned elements
that `caretRangeFromPoint` misposititions. Keeping both branches costs nothing.

**Drop cursor height:** The fixed `20px` height does not match the document line
height (which varies with zoom). Fix by computing height from a `Range`:

```js
function showDropCursor(pos) {
    const range = document.createRange();
    range.setStart(pos.node, pos.offset);
    range.setEnd(pos.node, pos.offset);
    const rect = range.getBoundingClientRect();
    const lineHeight = parseInt(getComputedStyle(editor).lineHeight) || 24;
    dropCursor.style.left  = rect.left + 'px';
    dropCursor.style.top   = (rect.top - lineHeight * 0.15) + 'px';
    dropCursor.style.height = (lineHeight * 1.1) + 'px';
    dropCursor.classList.add('visible');
}
```

**Confidence:** HIGH — this is pure DOM API usage, well-documented.

---

### 2. Click-to-Move (Two-Click Alternative to Drag)

**Pattern:** "Pick and Place" — click marker to select it, then click a word to
place it. This is the standard alternative UX for precision placement when drag
is too coarse (confirmed as best practice by Nielsen Norman Group and Salesforce
UX team research).

**Implementation approach:**

- A single global `selectedMarker` variable tracks which marker is in "picked"
  state (null = none)
- When a marker is clicked (not dragged — distinguish by checking `mousemove`
  distance < 3px), it enters picked state: add `.selected` CSS class (yellow
  border + scale), set `selectedMarker`
- While a marker is selected, hover over the document shows the same green
  word-highlight already used in add-mode (`onAddModeHover` logic is reusable
  exactly as-is)
- Clicking a word calls `moveMarker(selectedMarker, wordBoundaryPosition)` —
  reusing the exact same function already in the codebase
- Pressing Escape or clicking the same marker again deselects without moving
- Visual indicator: `.selected` marker gets a pulsing yellow ring (CSS
  `@keyframes` — no JS needed for the animation itself)

**Why vanilla CSS keyframes, not JS animation:** The pulse only needs to run
while the marker is selected. Adding/removing a class is sufficient. Using
`requestAnimationFrame` for this would add complexity with no benefit.

**Distinguish click from drag:** Track `mousedown` position, only commit to drag
if `mousemove` fires with delta > 3px before `mouseup`. If `mouseup` fires with
delta <= 3px, treat as a click → enter picked state.

```js
// In startDrag — record mousedown position
let dragStartX = e.clientX, dragStartY = e.clientY;
let hasMoved = false;

// In onDrag — set hasMoved flag
if (Math.abs(e.clientX - dragStartX) > 3 || Math.abs(e.clientY - dragStartY) > 3) {
    hasMoved = true;
}

// In endDrag — if not moved, treat as pick
if (!hasMoved) {
    pickMarker(draggedMarker);
    return;
}
```

**Confidence:** HIGH — this is a well-established interaction pattern, no exotic
APIs required.

---

### 3. Marker List Sidebar with Click-to-Jump Navigation

**Approach:** Replace the current instructions-only left sidebar (`.instructions`,
280 px) with a tabbed panel: "Instructions" tab + "Markers" tab. The sidebar
already has `position: sticky`-compatible layout and `overflow-y: auto`.

**Rendering the marker list:**

- Do NOT use virtual scrolling. 200 markers = 200 `<li>` elements, each ~40 px
  rendered height. That is 8000 px total list height — well within browser DOM
  performance limits (virtual scroll adds significant complexity and is only
  needed at 5000+ items). Render all markers as a flat `<ul>`.
- Each list item shows: page number + first 30 chars of following text (for
  context)
- Active marker (currently visible in viewport) highlighted via
  `IntersectionObserver`

**IntersectionObserver for active state:**

```js
const markerObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        const id = entry.target.getAttribute('data-id');
        const li = sidebarList.querySelector('[data-marker-id="' + id + '"]');
        if (li) li.classList.toggle('active', entry.isIntersecting);
    });
}, { threshold: 0.5 });

// Call after loadContent / restoreState
editor.querySelectorAll('.page-marker').forEach(m => markerObserver.observe(m));
```

**Click-to-jump:** Each `<li>` click calls:

```js
marker.scrollIntoView({ behavior: 'smooth', block: 'center' });
```

`scrollIntoView` with `behavior: 'smooth'` and `block: 'center'` is universally
supported in all target browsers (Chrome, Firefox, Safari 14+). HIGH confidence.

**Sidebar auto-scroll to active:** When `IntersectionObserver` marks an item
active, also scroll the sidebar list to keep the active `<li>` visible:

```js
li.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
```

`block: 'nearest'` avoids jumping when the item is already partially visible —
correct choice here.

**Rebuilding the list after changes:** Call a `rebuildMarkerList()` function
from `updateStats()` (already called after every state change). Keep it fast:
clear the `<ul>` and re-render all items from scratch. 200 items renders in
under 1ms — no diffing needed.

**Confidence:** HIGH for IntersectionObserver (baseline 2019+), HIGH for
scrollIntoView (all target browsers), HIGH for the no-virtual-scroll decision.

---

### 4. Search / Jump-to-Page Navigation

**Approach:** An `<input type="number">` in the sidebar header with a "Go"
button (or Enter key). No external library needed.

**Implementation:**

```js
function jumpToPage(pageNum) {
    const marker = editor.querySelector('.page-marker[data-page="' + pageNum + '"]');
    if (marker) {
        marker.scrollIntoView({ behavior: 'smooth', block: 'center' });
        // Flash highlight to draw attention
        marker.classList.add('jump-highlight');
        setTimeout(() => marker.classList.remove('jump-highlight'), 1200);
    } else {
        showToast('Page ' + pageNum + ' not found', 'error');
    }
}
```

**Flash highlight CSS:**

```css
@keyframes jump-flash {
    0%   { box-shadow: 0 0 0 4px rgba(255, 200, 0, 0.9); }
    100% { box-shadow: 0 0 0 0   rgba(255, 200, 0, 0); }
}
.page-marker.jump-highlight {
    animation: jump-flash 1.2s ease-out forwards;
}
```

This is pure CSS animation triggered by class toggle — no JS animation loop
required. `forwards` fill mode leaves the shadow at 0 after animation ends.

**Why not a floating search bar:** A sidebar input is simpler and consistent
with the panel. A floating search would require z-index management and
positioning logic that adds complexity for no UX gain in a single-column layout.

**Confidence:** HIGH — querySelector with data attribute selector is universally
supported.

---

### 5. Validation Overlays

**What needs validation:**

| Check | How to detect |
|---|---|
| Out-of-order markers | Scan `querySelectorAll('.page-marker')` (document order = DOM order), compare `parseInt(data-page)` values sequentially |
| Missing page numbers in sequence | After collecting all page numbers, scan for gaps > 1 between consecutive values |
| Duplicate page numbers | Use a `Map` counting occurrences; flag count > 2 (>2 may be unintentional; 2 is valid for two-column) |
| Markers in headings | Walk up `.parentElement` chain checking for `H1`–`H6` tags |

**Pattern — in-place CSS classes, not modal overlays:**

Apply warning classes directly to the `.page-marker` elements and the
corresponding sidebar `<li>` items. This avoids the complexity of a separate
overlay layer and keeps validation feedback visible while the user works.

```css
.page-marker.warn-order    { background: linear-gradient(135deg, #e67e22, #d35400); }
.page-marker.warn-missing  { /* marker before gap — amber border */ border: 2px solid #f39c12; }
.page-marker.warn-heading  { background: linear-gradient(135deg, #8e44ad, #6c3483); }
```

Sidebar list items get matching `.warn-*` classes and an icon prefix (unicode
character, not an image — "⚠ " prepended to the label text).

**When to run validation:** After every `saveState()` call (already called
after every edit). Validation is a pure DOM scan — O(n) where n = number of
markers, under 1ms for 200 markers. No debouncing needed.

**Validation summary bar:** Add a thin `<div class="validation-bar">` below the
toolbar that shows "3 warnings" with a click to scroll to the first warning.
This is a simpler pattern than a separate panel.

**Do NOT use a `MutationObserver` for triggering validation.** `saveState()` is
already the correct hook — it fires on every meaningful change. MutationObserver
would fire multiple times per drag (text node splits) causing unnecessary work.

**Confidence:** HIGH for DOM scanning approach, HIGH for CSS class-based
warnings, MEDIUM for the specific warning conditions (these are domain decisions,
not technical ones).

---

### 6. Panel Layout — Sidebar Toggle

The sidebar currently takes a fixed 280 px and is hidden on screens < 900 px.
For the improved version with a marker list, allow users to collapse/expand it.

**CSS approach — no JS for the animation itself:**

```css
.instructions {
    width: 280px;
    transition: width 0.2s ease, padding 0.2s ease;
    overflow: hidden;
}
.instructions.collapsed {
    width: 0;
    padding: 0;
}
```

Toggle button in the sidebar header calls
`instructionsPanel.classList.toggle('collapsed')`. Persist collapsed state in
`localStorage` (one key, one string).

**Do NOT use ResizeObserver for the sidebar toggle.** ResizeObserver is for
observing external size changes (e.g., window resize). A toggle is a
user-initiated action — just toggle the class.

**Do NOT make the sidebar resizable by drag handle** — this milestone does not
require it, and the added complexity (pointermove tracking, `cursor: col-resize`
hit zones, persisting widths) is disproportionate to the benefit for a tool used
by a single developer.

**Confidence:** HIGH — CSS transitions with class toggle is the standard
single-file approach.

---

## What NOT to Use

| Approach | Why not |
|---|---|
| HTML5 Drag and Drop API | Already correctly rejected in existing code. `dragover` does not provide caret positions; `dataTransfer` adds no value here |
| Virtual scrolling for sidebar list | Overkill. 200 markers at ~40px each = 8000px — browser handles this trivially |
| MutationObserver for validation triggers | `saveState()` is already called on every meaningful change. MutationObserver fires on text node splits during drag, causing spurious work |
| Web Components / Shadow DOM | Single-file constraint makes Shadow DOM actively harmful (complicates `querySelector` across boundaries) |
| `requestAnimationFrame` for pulse/flash animations | CSS `@keyframes` + class toggle is simpler and achieves the same result |
| ResizeObserver for sidebar toggle | Wrong tool — for a user-initiated toggle, just add/remove a CSS class |
| Any npm library (even small ones) | Single-file offline constraint makes CDN unreliable and inline bundling impractical. The pdf-splitter already uses CDN libs (PDF.js, pdf-lib) for justified reasons — the marker editor must not depend on network access |
| `contenteditable` for the document display | The editor already uses a non-editable `<div>` with custom events, which is correct. `contenteditable` would conflict with the custom drag system and break text node assumptions |

---

## Sources

- [Document: caretPositionFromPoint() — MDN](https://developer.mozilla.org/en-US/docs/Web/API/Document/caretPositionFromPoint)
- [Chrome 128 caretPositionFromPoint — Chromestatus](https://chromestatus.com/feature/5201014343073792)
- [Safari Technology Preview 226 release notes — WebKit](https://webkit.org/blog/17282/release-notes-for-safari-technology-preview-226/)
- [Element.scrollIntoView() — MDN](https://developer.mozilla.org/en-US/docs/Web/API/Element/scrollIntoView)
- [IntersectionObserver — MDN](https://developer.mozilla.org/en-US/docs/Web/API/Intersection_Observer_API) *(implied from search results)*
- [4 Major Patterns for Accessible Drag and Drop — Salesforce UX](https://medium.com/salesforce-ux/4-major-patterns-for-accessible-drag-and-drop-1d43f64ebf09)
- [Drag & Drop UX: think twice — Dave Feldman / Medium](https://medium.com/@dfeldman/drag-drop-think-twice-49e7bf3e6b31)
- [TreeWalker — MDN](https://developer.mozilla.org/en-US/docs/Web/API/TreeWalker)
- [Click and Swap (alternative to drag) — Hacker News thread](https://news.ycombinator.com/item?id=30034999)

---

*Research date: 2026-03-30*
