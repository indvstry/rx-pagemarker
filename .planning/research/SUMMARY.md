# Project Research Summary

**Project:** RX Page Marker — Visual Editor UX Milestone
**Domain:** Single-file vanilla JS browser editor (drag-and-drop annotation tool)
**Researched:** 2026-03-30
**Confidence:** HIGH

## Executive Summary

This milestone improves the existing `tools/page-marker-editor.html` — a ~1854-line single-file browser tool used to correct page marker placement in HTML files before EPUB3 generation. The tool has three documented pain points: imprecise drag-and-drop placement, no navigation in large (200+ marker) documents, and no validation of marker sequence correctness. All four research areas converge on a clear, feasible approach using exclusively vanilla DOM APIs — no libraries, no build tooling, no CDN dependencies — consistent with the single-file offline constraint the tool must maintain.

The recommended approach is a structured refactoring first (namespace-based module organization with an EventBus), followed by three additive feature groups: sidebar navigation with search, sequence validation with visual overlays, and click-to-move as a precision alternative to drag. The structural refactoring is the critical prerequisite — ARCHITECTURE.md establishes that the current flat-scope design will become unmaintainable past ~2500 lines, and all new features add 150–400 lines each. Attempting to bolt on new features to the unrefactored codebase risks the exact anti-patterns the ARCHITECTURE research flags: circular dependencies, stale DOM references, and monolithic `saveState()` call sites.

The primary risks are not technical novelty but implementation discipline in the DOM: the sidebar layout introduction can silently corrupt drag-and-drop coordinate math (PITFALLS Pitfall 1), validation state stored directly in the editor DOM will be corrupted by undo/redo (Pitfall 13), and IntersectionObserver references go stale after history restore (Pitfall 9). All three are avoidable with explicit design decisions made before writing code — they cannot be patched on after the fact without significant rework. Additionally, localStorage auto-save must be measured against real XRDD-sized documents before shipping, as quota exhaustion can cause silent data loss on large files (Pitfall 2).

---

## Key Findings

### Recommended Stack

The stack is already determined by the project constraint: a single HTML file, vanilla JS, no build step, no npm packages, offline-capable. Research confirmed this constraint is not a limitation — all required functionality has well-supported native browser APIs. No library decisions are required for this milestone.

**Core technologies:**

- `caretPositionFromPoint` (standard, Chrome 128+, Firefox, Safari TP): primary caret detection API — replace legacy `caretRangeFromPoint` priority inversion (keep as fallback for production Safari 18.x)
- `IntersectionObserver` (Baseline 2019+): sidebar active-item tracking as markers scroll into view — correct API choice, avoids expensive scroll listener + `getBoundingClientRect` on every scroll event
- `scrollIntoView({ behavior: 'smooth', block: 'center' })` (all target browsers): sidebar-to-editor jump navigation — universally supported
- `scroll-margin-top` CSS (Baseline 2020+): prevents `scrollIntoView` targets from landing behind the fixed toolbar — CSS-only solution, no JS needed
- CSS `@keyframes` + class toggle: all animations (pick-mode pulse, jump flash, warning highlights) — no `requestAnimationFrame` required
- Vanilla EventBus (20 lines, build it inline): decouples modules without any library — the only viable pattern for a maintainable single-file application at this scale

**What NOT to use:** HTML5 Drag API (no caret position on `dragover`), virtual scrolling (overkill at 200 items), Web Components/Shadow DOM (breaks `querySelector` across boundaries), `MutationObserver` for validation triggers (fires on mid-drag text node splits), `transform: scale()` for zoom (breaks coordinate space for caret detection — keep current `font-size` approach).

### Expected Features

Research from FEATURES.md identifies three pain point categories and maps features to them directly. The MVP boundary is clear and well-reasoned.

**Must have (table stakes — these make the tool usable):**
- Click-to-move (two-click precision alternative to drag) — drag has inherent Fitts's Law imprecision; NN/G recommends always pairing with a precise alternative
- Marker list sidebar with click-to-jump — mandatory for 200+ marker documents; VS Code sidebar is the reference pattern
- Search / jump-to-page-number — complements the sidebar; single input + Enter, handles missing page gracefully
- Out-of-order marker detection with visual highlighting — EPUB page-list breaks silently on out-of-order; user cannot detect this without a reader
- Gap detection (missing pages in sequence) — complement to out-of-order; shows in sidebar
- Improved drop cursor precision (dynamic height from `Range.getBoundingClientRect`, snap-to-gap logic)

**Should have (differentiators for this specific domain):**
- Validation summary pre-download gate — surface issues at the right moment without interrupting workflow
- Problem count in stats bar (green = 0, orange = any) — live health status
- Marker badge color coding by validation state (green/orange/purple)
- Heading/footnote zone warnings — documented EPUB production best practice (CLAUDE.md)
- Auto-suggest gap-aware page number on "+ Add Marker"

**Defer (explicitly out of scope for this milestone):**
- Scrollbar overview ruler (High complexity; sidebar + search covers navigation adequately)
- "Next problem" keyboard navigation (depends on validation being stable first)
- Dark mode, mobile/tablet support, real-time collaboration, text editing, multi-file workflow
- AI-assisted placement, PDF preview side-by-side — violate offline/single-file constraint

### Architecture Approach

The recommended architecture is namespace-based module simulation: organize the existing flat-scope code into named objects (modules) within a single `<script>` block, communicating via a central EventBus. This achieves module isolation without any build tooling. The key structural insight from ARCHITECTURE.md is that mutations are owned by a single module and results flow outward via events — never the reverse. The State object replaces ~10 scattered global variables. The Markers module centralizes the currently 4-place-duplicated marker element creation.

**Estimated total line count after refactoring + new features: ~2100 lines** (down from a projected ~2800 if features were added to the flat-scope file).

**Major components:**

1. **EventBus** (~20 lines) — pub/sub backbone; decouples all modules; 9 defined event types
2. **State** (~30 lines) — single source of truth for all application variables; emits `state:changed` on every `set()`
3. **Markers** (~50 lines) — read-only DOM query API; centralizes `createMarkerElement`, `getAll`, `getByPage`
4. **History** (~80 lines) — undo/redo via DOM snapshots; subscribes to all `markers:*` events instead of calling `saveState()` directly
5. **DragDrop** (~200 lines) — existing drag logic refactored into namespace; emits `markers:moved` on drop
6. **ClickMove** (~150 lines) — new two-click move mode; mutually exclusive with DragDrop via State flag + EventBus
7. **Sidebar** (~200 lines) — new marker list panel; tabbed layout replacing static instructions; contains Search as `Sidebar.initSearch()`
8. **Validation** (~180 lines) — new sequence analysis; emits `validation:complete` with issues array; never writes to editor DOM directly
9. **Export, AutoSave, Toast, FileLoader, AddMode, Init** — existing logic extracted into namespaces, minimally changed

**Build order enforced by dependencies:** Structural refactoring (Phase 1) → Sidebar + Search (Phase 2) → Validation (Phase 3) → ClickMove (Phase 4) → Drag precision improvements (Phase 5). Phases 4 and 5 are independent of 2 and 3; they can be ordered by priority.

**Critical architectural rule from PITFALLS:** Validation state must NEVER be stored as CSS classes on the editor DOM elements that get captured by `cloneNode(true)` into the history stack. Keep validation results in a separate external data structure; re-render from scratch after each validation pass.

### Critical Pitfalls

1. **Sidebar layout breaks drop cursor coordinates (Pitfall 1 — CRITICAL)** — The drop cursor uses `getBoundingClientRect()` viewport coordinates that currently work because there is no fixed UI competing for horizontal space. Adding a sidebar reflows the editor, causing the blue cursor to appear at one position while the marker inserts at another — silent data corruption. Prevention: audit all `getBoundingClientRect()` calls before the sidebar layout change; run a full drag-and-drop end-to-end test immediately after.

2. **Validation CSS classes captured in undo history (Pitfall 13 — CRITICAL)** — Applying validation warnings (`.page-marker.warn-order`) directly to editor DOM elements means those classes get snapshotted by `cloneNode(true)`. After undo, a restored state may show validation indicators from a later edit state. Prevention: store validation results externally in a `Map<markerId, result>`; apply visual indicators via a CSS overlay or by re-rendering after every restore — never modify editor element classes directly.

3. **Stale sidebar DOM references after undo/redo (Pitfall 4 — CRITICAL)** — `querySelectorAll` returns a static snapshot. After `restoreState()` replaces the editor content, every element reference the sidebar holds is a detached ghost node; `scrollIntoView()` silently does nothing. Prevention: store `data-id` attribute strings in sidebar items, never element references; re-query the live DOM fresh on every click.

4. **IntersectionObserver not rebuilt after history restore (Pitfall 9 — MODERATE)** — `observer.observe(el)` tracks specific element instances; replacing the DOM does not transfer observers. Prevention: call `observer.disconnect()` in `restoreState()` and rebuild observers after content replacement; emit `history:restored` event so Sidebar re-attaches.

5. **localStorage quota exhaustion for large documents (Pitfall 2 — MODERATE)** — The current auto-save stores `originalHTML + editor.innerHTML` as one JSON blob. XRDD-sized files (300–700 KB) may push combined payload toward the 5 MB Chrome / 2.5 MB Safari limit. Prevention: measure actual payload size with a real XRDD file in DevTools before shipping; if approaching 2 MB, drop `originalHTML` from the persisted payload (only `editorContent` is needed for session recovery).

---

## Implications for Roadmap

Based on the research, the correct phase sequence is dictated entirely by the dependency graph established in ARCHITECTURE.md:

### Phase 1: Structural Refactoring
**Rationale:** All new features (Sidebar, Validation, ClickMove) require the EventBus communication pattern and the clean module boundaries. Adding any new feature to the current flat-scope code creates the circular-dependency and stale-reference anti-patterns that PITFALLS identifies as requiring rewrites. This is the only safe order. No behavior changes in this phase.
**Delivers:** Same-behavior codebase organized into ~14 namespace modules with EventBus; all global variables consolidated into State; marker element creation centralized in Markers module.
**Addresses:** Pre-emptively prevents Pitfalls 3 (monolithic saveState call sites), 4 (stale references — via `data-id` pattern established here), and 13 (validation DOM entanglement — by establishing that editor DOM is mutation-only territory).
**Avoids:** The temptation to add Sidebar or ClickMove to the flat-scope file and then regret it.

### Phase 2: Sidebar Navigation + Search
**Rationale:** Navigation (pain point 2) is the highest-leverage fix — it unblocks effective use of validation (you can only act on validation warnings if you can navigate to them). The sidebar also provides the display surface that validation needs. Sidebar before Validation is the correct dependency order.
**Delivers:** Tabbed left panel (Instructions | Markers); clickable marker list with page number + context preview; search input for jump-to-page; `scrollIntoView` with `scroll-margin-top` offset for toolbar; sidebar collapsible via CSS class toggle with localStorage persistence.
**Uses:** IntersectionObserver (active item tracking), `scrollIntoView` smooth scroll, `data-id` reference pattern from Phase 1 refactoring.
**Implements:** Sidebar, Search (as Sidebar.initSearch()) components from ARCHITECTURE.md.
**Avoids:** Pitfalls 4 (stale references — by design from Phase 1), 5 (`scroll-margin-top` applied here), 9 (IntersectionObserver rebuild in `restoreState()`), 12 (`z-index: 9999` on drop cursor).

### Phase 3: Sequence Validation
**Rationale:** Validation (pain point 3) requires the Sidebar display surface from Phase 2 to show per-marker status icons. The validation logic itself is independent but its output has nowhere to go until the sidebar exists.
**Delivers:** Out-of-order detection (orange markers + sidebar icons); gap detection (yellow warnings); duplicate detection (>2 occurrences flagged); heading/footnote position check; validation summary in stats bar; pre-download confirmation gate.
**Implements:** Validation component from ARCHITECTURE.md; `validation:complete` event → Sidebar icon update flow.
**Avoids:** Pitfall 6 (validation debounced at 300ms, no `getBoundingClientRect` during validation pass), Pitfall 13 (validation results stored in external Map, not in editor DOM classes — this is the hardest constraint to maintain and the most important).

### Phase 4: Click-to-Move (Precision Interaction)
**Rationale:** Click-to-move (pain point 1) is independent of Sidebar and Validation — it only needs the EventBus from Phase 1. It is placed after Phase 3 because: (a) its value is higher when the user can navigate to a specific problem marker via the sidebar, and (b) it shares visual state (marker highlight classes) with the validation color coding from Phase 3, and coordinating them is cleaner when both exist.
**Delivers:** Click-to-pick a marker (yellow pulsing ring via CSS `@keyframes`), then click any word position to place it; Escape to cancel; mutual exclusion with AddMode and drag via State flag; full undo/redo integration via `markers:moved` event.
**Uses:** Existing `snapToWordBoundary()` and `moveMarker()` logic reused exactly; click-vs-drag distinguished by 3px mousemove threshold.
**Avoids:** Pitfall 7 (reuses `getCaretPosition()` with `font-size` zoom — no coordinate space change).

### Phase 5: Drag Precision Improvements
**Rationale:** A targeted fix to the existing `snapToWordBoundary()` function — prefer gap positions (whitespace between words) over word-interior boundaries. This is the lowest-risk phase because it is a small change to a single existing function with clear test criteria: drag slowly and verify the drop cursor stays precisely under the mouse pointer throughout.
**Delivers:** Improved `caretPositionFromPoint` priority (standard-first, `caretRangeFromPoint` as fallback for production Safari 18.x); dynamic drop cursor height from `Range.getBoundingClientRect`; gap-preferring snap algorithm in `snapToWordBoundary`.
**Avoids:** Pitfall 1 (re-verified after sidebar layout is already stable from Phase 2).

### Phase Ordering Rationale

- Phase 1 must be first because EventBus is required by every other phase, and the `data-id` reference pattern must be established before any sidebar code is written.
- Phase 2 must precede Phase 3 because validation icons have no display surface until the sidebar exists. Starting with validation first would require designing Sidebar later to fit Validation's output format — the reverse dependency is cleaner.
- Phases 4 and 5 are terminal (no downstream dependencies) and could be swapped. Phase 4 before Phase 5 is preferred because click-to-move is the more user-facing fix and its visual state interacts with validation badge colors from Phase 3.
- The overall sequence avoids the biggest architectural risk: starting with features before refactoring, which would require a rewrite at exactly the moment when the file is most complex.

### Research Flags

Phases with well-documented patterns (no additional research needed):
- **Phase 1 (Refactoring):** Standard namespace/EventBus pattern in vanilla JS — extensively documented; no novel techniques.
- **Phase 2 (Sidebar):** IntersectionObserver and `scrollIntoView` are both Baseline APIs with comprehensive MDN documentation; the tabbed CSS class toggle is a standard pattern.
- **Phase 4 (ClickMove):** Two-click interaction pattern is well-established (NN/G, Salesforce UX research); implementation reuses existing codebase functions.
- **Phase 5 (Drag precision):** Pure DOM API work; no novel APIs.

Phases that may need closer attention during implementation:
- **Phase 3 (Validation):** The duplicate detection heuristic for two-column layouts (distinguishing intentional from accidental duplicates) is a domain judgment call, not a technical research gap. The proximity heuristic (two duplicates close in the document = intentional) is reasonable but should be validated against real XRDD two-column pages.
- **All phases:** localStorage payload size for XRDD-scale documents — verify before Phase 2 ships (see Pitfall 2).

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All APIs are native browser standards with Baseline status confirmed; no library choices required; MDN + chromestatus sources |
| Features | HIGH | Pain points are directly stated in PROJECT.md; feature mapping to those pain points verified against NN/G and EPUB standards documentation |
| Architecture | HIGH | Based on direct code analysis of the existing 1854-line file; namespace patterns from established vanilla JS resources; EventBus is a solved problem |
| Pitfalls | HIGH | All critical pitfalls traced to specific line numbers in the existing codebase and to authoritative MDN/web.dev sources; not speculative |

**Overall confidence:** HIGH

### Gaps to Address

- **localStorage payload measurement:** Must check actual byte size of `originalHTML + editorContent` for a real XRDD magazine file before Phase 2 ships. The 5 MB / 2.5 MB quota risk (Pitfall 2) is real but can only be assessed against actual file sizes. If the payload is safe, no code change is needed. If it is not, the fix is dropping `originalHTML` from localStorage — a well-understood change.
- **Duplicate detection heuristic for two-column pages:** The threshold for "how close is intentional?" (Pitfall 10 / Validation phase) needs to be tuned against real XRDD two-column examples. Not a research gap — a calibration gap to be resolved during Phase 3 implementation.
- **Production Safari 18.x behavior:** `caretPositionFromPoint` ships in Safari TP 226 (August 2025) but not confirmed in Safari 18.x production. The existing two-branch fallback is already correct; the only gap is not knowing exactly when production Safari will ship. The fallback means there is no functional risk — only a future cleanup opportunity.

---

## Sources

### Primary (HIGH confidence)
- [MDN: Document.caretPositionFromPoint()](https://developer.mozilla.org/en-US/docs/Web/API/Document/caretPositionFromPoint) — caret API standard status, browser support
- [Chrome 128 caretPositionFromPoint — Chromestatus](https://chromestatus.com/feature/5201014343073792) — Chrome 128 ship date confirmed
- [Safari Technology Preview 226 release notes — WebKit](https://webkit.org/blog/17282/release-notes-for-safari-technology-preview-226/) — Safari TP support confirmed
- [MDN: Element.scrollIntoView()](https://developer.mozilla.org/en-US/docs/Web/API/Element/scrollIntoView) — behavior options, cross-browser support
- [MDN: IntersectionObserver API](https://developer.mozilla.org/en-US/docs/Web/API/Intersection_Observer_API) — observe/disconnect semantics
- [MDN: Storage quotas and eviction criteria](https://developer.mozilla.org/en-US/docs/Web/API/Storage_API/Storage_quotas_and_eviction_criteria) — 5 MB Chrome / 2.5 MB Safari localStorage limits
- [web.dev: Avoid large, complex layouts and layout thrashing](https://web.dev/articles/avoid-large-complex-layouts-and-layout-thrashing) — forced reflow from layout reads after DOM mutation
- [MDN: Node.cloneNode()](https://developer.mozilla.org/en-US/docs/Web/API/Node/cloneNode) — event listeners not copied
- Direct codebase analysis: `tools/page-marker-editor.html` (1854 lines) — all pitfall line references verified against live code

### Secondary (MEDIUM confidence)
- [Drag–and–Drop: How to Design for Ease of Use — NN/G](https://www.nngroup.com/articles/drag-drop/) — click-to-move as precision alternative, Fitts's Law reasoning
- [4 Major Patterns for Accessible Drag and Drop — Salesforce UX](https://medium.com/salesforce-ux/4-major-patterns-for-accessible-drag-and-drop-1d43f64ebf09) — "pick and place" pattern
- [CSS-Tricks: Sticky Table of Contents with Scrolling Active States](https://css-tricks.com/sticky-table-of-contents-with-scrolling-active-states/) — IntersectionObserver sidebar active-tracking pattern
- Revealing Module Pattern: [patterns.dev/vanilla/module-pattern](https://www.patterns.dev/vanilla/module-pattern/) — namespace module approach

### Tertiary (informational)
- [VS Code Overview Ruler — GitHub issue #23587](https://github.com/Microsoft/vscode/issues/23587) — scrollbar ruler pattern (deferred feature, not in MVP)
- PROJECT.md active requirements and CLAUDE.md best practices — confirmed pain points and domain constraints

---

*Research completed: 2026-03-30*
*Ready for roadmap: yes*
