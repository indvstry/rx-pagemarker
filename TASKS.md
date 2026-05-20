# Tasks

> Outstanding work for `rx-pagemarker`, primarily the visual marker editor
> (`tools/page-marker-editor.html`). Extracted from `.planning/` before that
> directory was retired. Project history lives in CHANGELOG.md.

## Roadmap — UI / UX

> Detailed plans for the highest-value editor UX work. Sequenced **by pain**:
> drag precision is the #1 user complaint, so Phase A ships first; navigation
> next; validation last. The checklists in the sections below remain the
> day-to-day source of truth — this Roadmap fleshes out the *why* and the
> *how* for the non-trivial items.

### Phase A — Precision (now)

The drop cursor and drag mechanics are the friction users hit every session.
Fixing this is a small amount of code with disproportionate UX payoff.

#### R0. Replace add-mode word highlight with a CSS overlay

- **Problem.** Add-mode currently wraps the hovered word in a
  `<span class="word-highlight">` via `surroundContents`, then unwraps it
  on the next mousemove. The same-word guard added in the editor
  (`page-marker-editor.html` `onAddModeHover`) stops the unwrap/rewrap when
  the cursor stays inside one word — but every transition between words
  still mutates the DOM, and `clearWordHighlight` never normalizes the
  parent, so the document accumulates fragmented text nodes over a long
  editing session.
- **Approach.** Don't wrap the word at all. Introduce a single
  `position: absolute` overlay element (sibling of `#drop-cursor`),
  positioned by `range.getBoundingClientRect()` to cover the word's
  bounding box. On mousemove → update overlay rect; on word-change →
  move it; on exit → hide it. Zero text-node mutation.
- **Acceptance.**
  - No `surroundContents` calls in `onAddModeHover`.
  - No measurable text-node fragmentation after extended hover (verify
    by comparing `editor.childNodes` length before / after a session).
  - Click-to-add still resolves to the correct word (use the same
    `getCaretPosition` + `findWordBoundaries` flow to derive the range).
- **Open questions.**
  - Multi-line words (rare, only at word-wrap boundaries) — overlay needs
    to be a union of two rects, or accept the visual quirk?

#### R1. Word-boundary snap on drop

- **Problem.** `caretPositionFromPoint` / `caretRangeFromPoint` return the
  exact text-node offset under the pointer, so a careless drop lands the
  marker mid-word (e.g., between `νο` and `μολογία`). Mid-word markers break
  EPUB rendering and look wrong in the editor.
- **Approach.** After computing the caret position (editor.html:1352–1389),
  walk forward/backward in the same text node to the nearest word boundary
  (whitespace, `.,;:·»«()`, or end-of-node). Bias toward the *start* of the
  word the pointer is closer to (split at the word's horizontal midpoint).
- **Acceptance.**
  - Drop anywhere inside a word's bounding box → marker lands at word start.
  - Drop past the word's horizontal midpoint → marker lands at word end /
    next word's start.
  - No regression in drop performance at 500+ markers.
- **Open questions.**
  - Punctuation handling: `"word. Word"` — does the marker land before the
    period, between, or before the next word?
  - Should snap distance be capped (e.g., don't snap across > 40px)?

#### R2. Drop cursor height tracks the line

- **Problem.** `dropCursor.style.height = '20px'` is hardcoded
  (editor.html:1402). At 50% zoom the cursor overhangs; at 200%+ it looks
  cramped.
- **Approach.** Use `range.getBoundingClientRect().height` when non-zero
  (it often is, because we set start = end on the same offset). Fall back
  to `getComputedStyle(parentEl).lineHeight` parsed to px. No zoom math
  needed — `getBoundingClientRect` already returns scaled coordinates.
- **Acceptance.** Cursor height matches surrounding text at 50–400% zoom in
  Chrome, Firefox, Safari.

#### R3. Click-to-move (two-click alternative to drag)

- **Problem.** Dragging is the #1 reported friction — trackpad users,
  touchscreen users, and anyone with low motor precision struggle. Users
  want: *click marker → click target → done*.
- **Approach.** Single click on an existing marker "arms" it (visual cue:
  pulsing outline + body cursor → crosshair). Second click anywhere uses
  the same caret/snap logic as drag to place it. `Esc` cancels.
- **Acceptance.**
  - Click marker → marker visibly armed.
  - Click target → marker moves, history entry recorded.
  - `Esc` while armed cancels.
  - Drag still works; the two flows don't conflict.
- **Open questions.**
  - Conflict with double-click-to-edit: gate by a 250ms debounce, or treat
    "click then click" as move only when the second click is **not on the
    same marker**? (Lean: debounce.)
  - Should armed state survive `Ctrl+Z`?

#### R4. `caretPositionFromPoint` primary / `caretRangeFromPoint` Safari fallback

- **Status. Already done** — editor.html:1352–1389 implements both branches
  in the correct order. Item is being marked complete in the checklist
  below. No further work unless a regression appears.

### Phase B — Navigation (next)

Once markers can be placed precisely, the next bottleneck is *finding* the
ones that need fixing in a 200+ marker magazine.

#### R5. Marker sidebar with previews

- **Problem.** With 200+ markers, surveying placement requires scrolling
  the whole document.
- **Approach.** Right-rail panel with one row per marker: page-number
  badge + first ~6 words of following text. Click → smooth-scroll +
  yellow flash on the target marker. Virtualize the list above ~300 rows.
- **Acceptance.** All markers listed in document order; click jumps and
  centers; loads in <100ms at 500 markers.
- **Open questions.**
  - The right rail already hosts the Articles panel (editor.html:562).
    Coexist as two stacked panels, or toggle between them with a tab
    control? (Lean: tab toggle to preserve horizontal space.)

#### R6. Jump-to-page search

- **Problem.** Even with a sidebar list, hunting *page 873* in a 232-row
  list is slow.
- **Approach.** Search input above the sidebar list. As-you-type filter
  (substring match on the page number string). `Enter` on a unique match
  jumps + closes the search.
- **Acceptance.** Filter response <16ms; `Enter` jumps; `Esc` clears.

#### R7. Active-marker tracking

- **Problem.** Scrolling the document doesn't update the sidebar; users
  lose orientation.
- **Approach.** `IntersectionObserver` on all markers; the marker closest
  to viewport center is the "active" one. Sidebar highlights it and
  auto-scrolls it into the sidebar's visible range (only if not already
  visible — don't fight the user).
- **Acceptance.** Smooth scrolling of the document smoothly updates the
  sidebar highlight; no layout thrash on rapid scroll.

#### R8. Density ruler on scrollbar

- **Problem.** Where are the gaps? Where do markers cluster? Currently
  invisible.
- **Approach.** Thin SVG strip pinned to the right edge of the editor
  (separate from sidebar), one tick per marker proportional to document
  position. Hover → page-label tooltip; click → scroll to that marker.
  Tick color reflects validation state once Phase C lands.
- **Acceptance.** Strip visible during editing; click jumps; ticks
  proportional to document position (not marker index).

### Phase C — Validation (later)

With precision and navigation solid, validation surfaces the remaining
issues before they ship into an EPUB.

#### R9. Out-of-order detection

- **Problem.** Edits can leave page 776 placed before page 775. Currently
  invisible until export.
- **Approach.** After every mutation, walk markers in document order;
  flag any with `current < prev` or `current > next`. Add red border +
  tooltip "Out of order: 776 < 777".
- **Acceptance.** Warning appears within 100ms of edit; cleared when fixed.

#### R10. Gap detection

- **Problem.** Missing *page 873* in a 775–1006 run is easy to miss.
- **Approach.** Compute the numeric range of present markers; any integer
  in `[min, max]` not present is a gap. Top banner: "Missing pages: 873,
  901". Click banner entry → scroll to the marker preceding the gap.
- **Acceptance.** Banner refreshes on load + after each edit; click jumps.
- **Open questions.**
  - Some gaps are intentional (e.g., a deliberately unmarked blank). Add a
    per-gap dismiss-once that persists in `localStorage`? (Lean: yes.)

#### R11. Duplicate flagging

- **Problem.** Per CLAUDE.md, the same page number appearing **>2 times** is
  almost always an accident; ≤2 times is the valid two-column case.
- **Approach.** Count occurrences per page number. Apply class:
  `dup-2` (yellow, informational) and `dup-many` (red, error).
- **Acceptance.** Color cue on markers in the document *and* in the
  sidebar.

#### R12. Position sanity warnings

- **Problem.** Per CLAUDE.md "Best Practices": markers landing in headings
  render poorly in EPUB; should be at the start of the first body
  paragraph. Same for footnote regions.
- **Approach.** Walk the marker's ancestor chain at mutation time:
  - `h1`–`h6` → yellow flag "Marker in heading — move to body paragraph".
  - Class matches `*footnote*` / `*fn*` / `_superscript` → yellow flag
    "Marker in footnote region".
- **Acceptance.** Both cases flagged; tooltip explains; no false positives
  on normal body text.
- **Open questions.**
  - Footnote detection by CSS class alone, or also by font-size?

#### R13. Pre-download validation summary

- **Problem.** Users can click *Download Paginated HTML* with errors
  present and not know.
- **Approach.** Intercept the download click; if there are warnings/errors,
  show a modal: counts per category, list of affected pages, *Cancel* /
  *Download anyway*. Bypass modal when state is clean.
- **Acceptance.** Modal lists categories and counts; Cancel returns to
  editor; Download anyway proceeds.
- **Open questions.**
  - Hard-block on red errors, or always allow override? (Lean: always
    allow override — users may know better than the validator.)

#### R14. Color-coded markers by state

- **Problem.** Without color, validation issues are invisible at a glance.
- **Approach.** Apply a class to each marker reflecting its aggregate
  state: `state-ok` (green border-bottom), `state-warn` (yellow),
  `state-error` (red). Classes recomputed on mutation; same color is
  reflected in sidebar rows and density-ruler ticks.
- **Acceptance.** Marker colors update reactively; one marker can show
  the union of multiple warning sources but only one dominant color.

## Editor — Navigation

- [x] **Articles panel** — right-hand outline of rubrics + legal-domain
      sections with clickable essay-title / court-decision entries that
      scroll the document. Policy isolated in `classifyArticleBoundary`;
      preview-only, never exported. (CHANGELOG 2026-05-19.) Distinct from
      the *marker*-list sidebar below, which is still pending.
- [ ] Sidebar panel with clickable marker list (page number + text preview)
- [ ] Click sidebar entry to scroll the document to that marker
- [ ] Search / jump-to-page-number field
- [ ] Active marker tracking — sidebar highlights marker in viewport
- [ ] Scrollbar overview ruler showing marker density

## Editor — Validation

- [ ] Out-of-order marker detection with visual warnings
- [ ] Gap detection — missing page numbers in sequence
- [ ] Duplicate flagging (>2 occurrences of same page = accidental, ≤2 = valid two-column)
- [ ] Pre-download validation summary — user confirms before save
- [ ] Position sanity warnings (markers in headings or footnotes)
- [ ] Color-coded markers by validation state (green / yellow / red)

## Editor — Precision

- [ ] Click-to-move: two-click precision alternative to drag
- [ ] Drop cursor snaps to word boundary, not mid-word
- [ ] Drop cursor height matches line height at current zoom
- [x] `caretPositionFromPoint` primary, `caretRangeFromPoint` Safari fallback
      *(already implemented at editor.html:1352–1389; see Roadmap R4.)*

## Deferred

- [ ] Editor JS module reorganization — was attempted (commits 1770a04 / 7e2c8b3 / 711df00),
      regressed editor behavior, reverted in `b761c33`. Any retry must be
      incremental edits, not a full rewrite. See memory `feedback_gsd_refactoring.md`.

## Out of Scope

- Magazine validator integration — not a priority
- Multi-language beyond Greek — no current demand
- Multi-file workflow in editor — copy-body-content workaround is sufficient
- Import/export pipeline in editor — CLI handles this
- Dark mode — not worth the effort now
- Mobile / tablet support — desktop-only task
- Frameworks (React / Vue) or build step — violates single-file constraint
- Text editing in document — editor is for marker positioning only

## Constraints (always-on)

- Single HTML file, no build step, no frameworks
- Vanilla JS only
- Must load existing marked HTML files (backwards compatible)
- Must work in modern Chrome / Firefox / Safari

## Decisions

| Decision | Rationale | Status |
|---|---|---|
| Single HTML file for editor | Portability, offline use, no tooling | ✓ Good |
| Vanilla JS | No deps, fits single-file constraint | ✓ Good |
| localStorage for auto-save | No server, offline | ✓ Good |
| Click-to-move alongside drag | Drag precision is the #1 UX complaint | Pending |
| Sidebar + search (both) | Different use cases — browsing vs. targeted jump | Pending |
