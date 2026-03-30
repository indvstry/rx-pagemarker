# Domain Pitfalls

**Domain:** Browser-based visual HTML editor — drag-and-drop precision, navigation sidebar, search, validation overlays
**Researched:** 2026-03-30
**Applies to:** `tools/page-marker-editor.html` (~1854 lines, vanilla JS, single-file constraint)

---

## Critical Pitfalls

Mistakes that require rewrites or corrupt user data.

---

### Pitfall 1: The Sidebar Breaks the Drop Cursor's Coordinate System

**What goes wrong:** The drop cursor (`#drop-cursor`) is positioned using `rect.left` and `rect.top` from `range.getBoundingClientRect()`, which returns viewport-relative coordinates. Adding a fixed-position sidebar shifts the editor's visible region but `getBoundingClientRect()` results remain viewport-relative. The blue drop cursor will appear at the correct viewport position but visually offset from where the text actually is — sometimes by the full sidebar width — making drag-and-drop appear broken after the layout change.

**Why it happens:** The current implementation uses `style.left = rect.left + 'px'` and `style.top = rect.top + 'px'` (lines 1133–1134). These are viewport coordinates, which happen to be correct today because there is no other fixed UI competing for horizontal space. A sidebar that reduces the editor's width will cause the editor content to reflow and the coordinate math to diverge from the visual cursor position.

**Consequences:** Drag-and-drop appears to work but markers land in the wrong location. The user sees the blue cursor in one position and the marker inserts somewhere else. This is a silent data-corruption failure — the marker goes into the document at the wrong word.

**Prevention:**
- Before adding sidebar layout, audit every call to `getBoundingClientRect()` and `getCaretPosition()`.
- The drop cursor must be positioned relative to the viewport's scroll position and the editor's actual layout rect, not absolute page coordinates. A `position: fixed` drop cursor (which it already is) is correct, but only as long as `rect.left`/`rect.top` remain purely viewport values — verify this is still true after layout changes.
- After adding the sidebar, run a drag-and-drop test where a marker is moved and verify the marker lands exactly where the cursor was shown.

**Detection:** Drag a marker slowly. Watch whether the blue drop cursor stays directly under the mouse pointer throughout the drag, including near the left and right edges of the editor area.

**Phase:** Must be verified in the phase that introduces the sidebar layout change.

---

### Pitfall 2: localStorage Quota Exhausted by the Auto-Save Mechanism

**What goes wrong:** The auto-save stores `originalHTML` (the full input file) plus `editor.innerHTML` (the modified content) on every single change. For the XRDD magazine (272-page legal document), the HTML file is likely 300–700 KB. The two copies together — plus JSON overhead — can approach or exceed the 5 MB per-origin localStorage limit common to Chrome and Firefox. Safari's limit is sometimes as low as 2.5 MB.

**Why it happens:** The current auto-save serializes `originalHTML + editorContent` into a single JSON blob. Every marker move triggers `saveState()` which calls `autoSave()`. For a large two-column magazine article with 52+ markers being manually corrected, a 20-minute editing session produces dozens of saves, each writing the full document. The quota check exists (lines 721–727), but it only fires after 3 failures — by which point the most recent save has already silently failed.

**Consequences:** After 3 failures the user sees a toast, but the saves before that succeeded and then stopped. When the user refreshes, they lose the work done after the last successful save. The user may not notice until the browser is closed.

**Prevention:**
- Measure the actual size of a typical XRDD session HTML via `JSON.stringify(data).length` before committing to the current approach.
- If the combined payload approaches 2 MB, store only `editorContent` in localStorage and require the user to reload the original file on recovery. The `originalHTML` is only needed to reconstruct the `<head>` on download — the editor functions perfectly without it.
- Alternatively, store only a diff (list of marker positions + page numbers) rather than the entire DOM snapshot. This would reduce localStorage usage by 99% for typical sessions.

**Detection:** Load a large magazine HTML file (>300 KB). Open DevTools → Application → Storage → localStorage. After 5 marker moves, check the byte size of the stored value.

**Phase:** Must be assessed before shipping the sidebar+search milestone. The current single-article use case may be safe, but full-magazine editing is the target for this milestone.

---

### Pitfall 3: History Snapshots Blow Up Memory for Large Documents

**What goes wrong:** `saveState()` calls `editor.cloneNode(true)` and stores the result in the `history` array, up to 50 entries (line 1251). For a large Greek legal magazine article, the editor DOM may contain 50k words plus 230 marker spans. Each `cloneNode(true)` of that tree produces a separate in-memory DOM subtree. At 50 snapshots × a large article DOM, memory consumption can reach hundreds of megabytes. Browsers do not evict these from memory until the tab is closed.

**Why it happens:** Snapshot-based undo/redo is simple to implement and correct, but it scales with O(N × H) where N is document size and H is history depth. The 50-snapshot limit prevents unbounded growth but does not bound the size of individual snapshots.

**Consequences:** Browser tab becomes sluggish during long editing sessions. Marker hover and word highlighting (which call `getCaretPosition` on every `mousemove`) will stutter because layout calculations are slower in a memory-pressured tab. In extreme cases the tab crashes.

**Prevention:**
- The snapshot approach is fine for single-article files (typical size: 10–80 KB). For full-magazine files, reduce `MAX_HISTORY` from 50 to 10–15 snapshots.
- Better long-term: replace DOM snapshots with a command log (array of `{action, markerId, fromPosition, toPosition}` objects). This reduces history memory by ~1000x and is the standard approach in mature editors. However, it is significantly more complex to implement correctly.
- For this milestone, the simplest safe fix is: detect document size at load time and scale `MAX_HISTORY` inversely. Files under 100 KB keep 50 snapshots; files over 300 KB use 10.

**Detection:** Load a full-magazine HTML, make 50+ marker moves, then check DevTools → Memory → Heap snapshot for growth in detached DOM nodes.

**Phase:** Address before adding more features that call `saveState()`. Validation overlays (out-of-order detection) will call `updateStats()` on every change — ensure no accidental snapshot is triggered during validation UI updates.

---

### Pitfall 4: Sidebar DOM References Go Stale After Undo/Redo

**What goes wrong:** A navigation sidebar will hold references to marker DOM elements inside the editor (e.g., to call `marker.scrollIntoView()` on click). After an undo or redo, `restoreState()` clears the editor with `editor.textContent = ''` and replaces all child nodes with fresh clones (lines 1291–1299). Every element reference the sidebar holds is now a detached DOM node. Clicking a sidebar item calls `scrollIntoView()` on a disconnected element — this is a silent no-op in most browsers.

**Why it happens:** `querySelectorAll()` returns a static snapshot (not a live collection). The sidebar's item list will point to the elements that existed at the time the sidebar was built. After any undo/redo that replaces the editor content, those references are garbage.

**Consequences:** After undo/redo, the sidebar appears functional (items are still listed) but clicking any item does nothing. The user thinks navigation is broken. This is especially confusing because the markers are visibly present in the editor but unreachable from the sidebar.

**Prevention:**
- Never store direct DOM element references in sidebar item data. Instead, store the marker's `data-id` attribute value.
- On sidebar item click, do a fresh `editor.querySelector('[data-id="' + id + '"]')` to obtain the live element before calling `scrollIntoView()`.
- After `restoreState()`, rebuild the sidebar by re-querying the editor: call a `rebuildSidebar()` function at the end of `restoreState()`.

**Detection:** Load a file, build the sidebar, undo one action, then click a sidebar item. It should scroll. If it does not, references are stale.

**Phase:** This must be designed in from the start when building the sidebar. It cannot be patched on later without a refactor.

---

## Moderate Pitfalls

---

### Pitfall 5: `scrollIntoView()` Lands Behind the Fixed Toolbar

**What goes wrong:** The editor has a fixed toolbar and (after this milestone) a fixed sidebar. `element.scrollIntoView()` positions the element within the viewport but has no awareness of fixed UI that overlaps the top or sides of the viewport. A marker at the top of a paragraph will be scrolled into view but hidden behind the toolbar. The user sees only blank space or partial content where they expected the highlighted marker.

**Why it happens:** `scrollIntoView()` does not accept an offset parameter. It aligns to the viewport edge, not to the visible content area below fixed UI.

**Prevention:**
- Use `scroll-margin-top` CSS on `.page-marker` elements: `scroll-margin-top: 80px` (adjust to match toolbar height). This is the modern, CSS-only solution (Baseline 2020+, all target browsers).
- Alternatively, calculate: `window.scrollBy(0, -toolbarHeight)` immediately after `scrollIntoView()`.
- Measure the actual toolbar height dynamically rather than hardcoding, in case zoom changes affect it.

**Detection:** Jump to the first marker in a document via the sidebar. Check whether the marker is fully visible or hidden behind the toolbar.

**Phase:** Sidebar navigation phase. Straightforward to fix, easy to miss during development because it only appears with content near the top of the document.

---

### Pitfall 6: Validation Pass Triggers on Every Keystroke/Move, Causing Lag

**What goes wrong:** Out-of-order and gap detection requires scanning all markers in document order and comparing their page numbers. If this scan runs synchronously on every `saveState()` call (which fires on every marker move), it will add a full O(N) DOM walk to every interaction. For 230 markers, this is negligible. If validation is also triggered by `updateStats()` — which already fires on every `saveState()` — and validation reads `getBoundingClientRect()` on each marker to check visual position, it will force a layout reflow on every mouse move during drag.

**Why it happens:** `updateStats()` and `saveState()` are called together and both run synchronously in the event handler chain. Validation logic that reads layout properties (anything involving `offsetTop`, `getBoundingClientRect`, or computed styles) will force the browser to flush pending style recalculations immediately.

**Prevention:**
- Run validation scans as a separate, debounced call triggered after `saveState()`. Debounce delay of 300–500 ms is enough; validation results do not need to be instant.
- Separate the validation scan (which reads `data-page` attributes — fast, no reflow) from any visual positioning checks (which read layout — slow, causes reflow).
- For the out-of-order check, only read `data-page` attributes in document order. Do not read `getBoundingClientRect` during validation.

**Detection:** Move a marker while watching the browser's Performance panel in DevTools. Any forced reflow appearing in the `saveState()` call stack is a sign validation is reading layout properties synchronously.

**Phase:** Validation overlay phase. Design the validation update path to be decoupled from the drag event path before writing the first line of validation code.

---

### Pitfall 7: `caretRangeFromPoint` / `caretPositionFromPoint` Inconsistency After Layout Change

**What goes wrong:** The current `getCaretPosition()` function handles the Firefox/Chrome split correctly (lines 1083–1101): Firefox uses `caretPositionFromPoint`, Chrome/Safari use `caretRangeFromPoint`. However, `caretPositionFromPoint` became Baseline 2025 (available in Chrome since late 2025 as well). The check order is correct (standard API first, non-standard fallback). The risk is not in the fallback logic itself but in what happens if the editor's parent layout changes: `caretRangeFromPoint` and `caretPositionFromPoint` both operate on the **rendered** character position. If zoom is applied via `font-size` on the editor (current implementation, line 1342) rather than via CSS `transform: scale()`, character positions shift with the font. This is correct behavior — but if zoom is ever changed to use `transform: scale()`, coordinates must be divided by the scale factor or caret detection will be off by the zoom ratio.

**Why it happens:** Coordinate space mismatch between CSS transform scaling and `clientX`/`clientY` which are always in unscaled viewport pixels.

**Prevention:**
- Keep the current `font-size` zoom approach. Do not switch to `transform: scale()` without updating `getCaretPosition()` to compensate.
- Document this constraint in the code with an explicit comment near `setZoom()`.

**Detection:** Set zoom to 150%, drag a marker, and verify it lands where the cursor was shown. If it lands offset from the cursor, the coordinate space is mismatched.

**Phase:** Any phase that touches zoom or layout. Low risk if zoom implementation is not changed.

---

### Pitfall 8: Word-Highlight Span Left in DOM Corrupts Export

**What goes wrong:** Add mode wraps a word in a `.word-highlight` span via `range.surroundContents()`. If the user enters add mode, moves the mouse over a word so it gets highlighted, then immediately clicks Download or Copy Body — without exiting add mode — the highlight span may still be in the DOM. The export function `prepareExportedBody()` includes cleanup for this (lines 1711–1718), but the cleanup only runs on the cloned container. If the cleanup fails (e.g., `surroundContents` partially applied a range that crosses element boundaries), a `<span class="word-highlight">` will appear in the exported HTML inside the EPUB. This will not cause a crash but will produce invalid EPUB markup.

**Why it happens:** `surroundContents()` is known to throw when a selection range crosses element boundaries (the catch at line 1484 silently sets `highlightedWord = null`). If the throw happens mid-operation, a partial DOM mutation may remain. The `clearWordHighlight()` function guards against this with an `isConnected` check, but a partial `surroundContents` could leave orphaned text nodes or a half-inserted span.

**Prevention:**
- The existing `[data-word-start]` cleanup in `prepareExportedBody()` is the right defense. Verify it catches `.word-highlight` even when `surroundContents` partially succeeded.
- Add a defensive `clearWordHighlight()` call at the start of the download and copy-body handlers, before `prepareExportedBody()`.
- Add-mode should disable the Download and Copy Body buttons (or show a warning) while active, since exporting mid-edit is likely unintentional.

**Detection:** Enter add mode, hover over a word to highlight it, then immediately click Download without clicking a word or pressing Escape. Inspect the downloaded file for `class="word-highlight"` or `data-word-start` attributes.

**Phase:** Any phase that adds new export triggers (validation export, sidebar copy). Check that each export path calls cleanup.

---

### Pitfall 9: IntersectionObserver Must Be Rebuilt After Undo/Redo

**What goes wrong:** If IntersectionObserver is used to auto-highlight the active sidebar item as the user scrolls through the document, the observers must be attached to the marker elements currently in the DOM. After undo/redo replaces the editor content, all observed elements are detached and the IntersectionObserver silently stops firing for them. New elements (even with the same `data-id`) are not automatically observed.

**Why it happens:** IntersectionObserver tracks specific element instances. Replacing the DOM via `restoreState()` creates new element instances even if their attributes are identical. There is no mechanism for auto-transfer of observers.

**Prevention:**
- Rebuild IntersectionObservers in `restoreState()` alongside `setupMarkerDragging()`.
- Use a single `observer.observe(el)` call pattern that can be re-run safely after each restore. Call `observer.disconnect()` before `restoreState()`, then reconnect after.
- Consider whether IntersectionObserver is even needed: if the sidebar highlights the active item by comparing scroll position to `marker.getBoundingClientRect().top`, this can be done on a debounced scroll listener without IntersectionObserver at all. For 200 markers, a scroll listener reading `getBoundingClientRect()` on all 200 on every scroll event is too slow — IntersectionObserver is the right choice, but the rebuild requirement must be accounted for.

**Detection:** Load a file, scroll to see the sidebar auto-highlight tracking, perform undo, then scroll again. If the active highlight stops updating, observers were not rebuilt.

**Phase:** Sidebar implementation phase.

---

## Minor Pitfalls

---

### Pitfall 10: `getNextPageNumber()` Returns Wrong Suggestion for Two-Column Layouts

**What goes wrong:** When the user adds a marker in add mode, the suggested page number is `max(existing page numbers) + 1`. For two-column layouts, the same page number is used twice (intentionally). When adding the second marker for a split page, the suggestion will be wrong (one too high). The user must manually correct it each time.

**Prevention:** Not worth fixing at the UX level — the prompt makes it easy to change the value. But if the validation overlay later flags duplicate page numbers as warnings, it must distinguish intentional two-column duplicates from accidental duplicates. The key signal is: two duplicates in close proximity in the document (within a few paragraphs) are likely intentional. Two duplicates hundreds of nodes apart are likely a mistake.

**Phase:** Validation overlay phase. Design the duplicate detection heuristic at that point.

---

### Pitfall 11: Search "Jump to Page" Fails for Non-Numeric Page References

**What goes wrong:** Page markers use numeric strings for `data-page` (e.g., `"776"`). A search input that trims and compares strings will work for exact matches. It will fail silently if the user types with a leading zero (`"0776"`) or a Greek-language prefix (`"σελ. 776"`), since the editor strips the prefix on load (line 663) but users may not know this. The bigger risk: if future work adds appendix markers with letter suffixes (e.g., `"A1"`, `"XII"`), numeric search will not find them.

**Prevention:** Use `.trim()` and case-insensitive comparison in the search handler. Document in UI that the search expects bare numbers as they appear in the red badge.

**Phase:** Search implementation phase.

---

### Pitfall 12: Fixed `#drop-cursor` Element Is Hidden Under a Fixed Sidebar

**What goes wrong:** The `#drop-cursor` is a `position: fixed` element with no explicit `z-index` higher than the sidebar. If the sidebar is also `position: fixed` with a higher z-index, the drop cursor may appear behind the sidebar panel when dragging a marker near the left edge of the editor. The cursor becomes invisible exactly where the user needs it most (placing a marker near the boundary of the sidebar).

**Prevention:** Assign an explicit, high `z-index` to `#drop-cursor` (e.g., `z-index: 9999`) so it always renders above all other UI elements. This is a one-line CSS fix but only catches it if you test by dragging near the sidebar edge.

**Phase:** Sidebar layout phase.

---

### Pitfall 13: Validation Overlay State Survives Undo

**What goes wrong:** If validation warnings (e.g., red underline on an out-of-order marker) are applied as CSS classes directly to the live editor DOM, those classes will be captured in the next `saveState()` snapshot. After undoing to a previous state, the validation classes from a *later* state may appear on markers that were not yet out of order at the time of the snapshot. Validation state and edit state become entangled.

**Prevention:** Never store validation state in the editor DOM. Keep validation results in a separate data structure (`Map<markerId, validationResult>`). Render validation indicators as an overlay or via a shadow DOM layer — not by modifying the editor's element classes directly. Recompute validation on every `saveState()` call (debounced) and re-render the overlay from scratch.

**Phase:** Validation overlay phase. This is a foundational architectural decision — establish it before writing the first validation rule.

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|----------------|------------|
| Sidebar layout addition | Drop cursor coordinate offset (Pitfall 1) | Verify drag-and-drop end-to-end after layout change |
| Sidebar navigation clicks | Stale DOM references after undo/redo (Pitfall 4) | Store `data-id`, never element references |
| Sidebar navigation clicks | `scrollIntoView` behind toolbar (Pitfall 5) | Add `scroll-margin-top` CSS to `.page-marker` |
| Sidebar scroll tracking | IntersectionObserver not rebuilt (Pitfall 9) | Rebuild in `restoreState()` |
| Out-of-order validation | Validation running on drag mousemove (Pitfall 6) | Debounce validation, never read layout in validation |
| Out-of-order validation | Validation classes captured in history (Pitfall 13) | Keep validation state external to editor DOM |
| Click-to-move feature | Same coordinate-space issues as drag (Pitfall 7) | Reuse `getCaretPosition()`, test at all zoom levels |
| Large document editing | localStorage quota exceeded (Pitfall 2) | Measure payload size before shipping |
| Long editing sessions | History snapshots memory growth (Pitfall 3) | Scale `MAX_HISTORY` with document size |
| Export during add mode | Word-highlight span in exported file (Pitfall 8) | Call `clearWordHighlight()` before every export |

---

## Sources

- [MDN: Document.caretPositionFromPoint()](https://developer.mozilla.org/en-US/docs/Web/API/Document/caretPositionFromPoint) — Baseline 2025 status confirmed; `caretRangeFromPoint` is non-standard fallback. (HIGH confidence)
- [MDN: Storage quotas and eviction criteria](https://developer.mozilla.org/en-US/docs/Web/API/Storage_API/Storage_quotas_and_eviction_criteria) — 5 MB limit per origin, Safari as low as 2.5 MB. (HIGH confidence)
- [Pawel Grzybek: Cloning DOM nodes and handling attached events](https://pawelgrzybek.com/cloning-dom-nodes-and-handling-attached-events/) — Event listeners not copied by `cloneNode`. (HIGH confidence)
- [MDN: Node.cloneNode()](https://developer.mozilla.org/en-US/docs/Web/API/Node/cloneNode) — Confirmed: no event listener copying. (HIGH confidence)
- [web.dev: Avoid large, complex layouts and layout thrashing](https://web.dev/articles/avoid-large-complex-layouts-and-layout-thrashing) — Reading layout after DOM mutation causes forced reflow. (HIGH confidence)
- [Stefan Judis: Live vs. static element collections](https://www.stefanjudis.com/blog/accessing-the-dom-is-not-equal-accessing-the-dom/) — `querySelectorAll` returns static snapshot. (HIGH confidence)
- [MDN: Element.scrollIntoView()](https://developer.mozilla.org/en-US/docs/Web/API/Element/scrollIntoView) — No offset parameter; `scroll-margin-top` is the CSS-native solution. (HIGH confidence)
- [CSS-Tricks: Sticky Table of Contents with Scrolling Active States](https://css-tricks.com/sticky-table-of-contents-with-scrolling-active-states/) — IntersectionObserver pattern for sidebar active tracking. (MEDIUM confidence)
- [MDN: IntersectionObserver API](https://developer.mozilla.org/en-US/docs/Web/API/Intersection_Observer_API) — `observe()` must be called on new elements; disconnect before DOM replacement. (HIGH confidence)
- Codebase analysis of `tools/page-marker-editor.html` (lines 688, 797, 1133–1134, 1244–1254, 1291–1299, 1481–1488, 1656–1730) — Direct inspection of current implementation. (HIGH confidence)
