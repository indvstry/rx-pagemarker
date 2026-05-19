# Tasks

> Outstanding work for `rx-pagemarker`, primarily the visual marker editor
> (`tools/page-marker-editor.html`). Extracted from `.planning/` before that
> directory was retired. Project history lives in CHANGELOG.md.

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
- [ ] `caretPositionFromPoint` primary, `caretRangeFromPoint` Safari fallback

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
