# RX Page Marker

## What This Is

A Python CLI tool and browser-based visual editor for inserting page number markers into HTML files for EPUB3 generation. Part of the RX EPUB pipeline, it converts InDesign HTML exports into EPUB3 files with accurate page-list navigation. Used primarily for Greek legal magazines with complex two-column layouts.

## Core Value

Accurate page markers in EPUB files that match the print edition — enabling citation compatibility, page-list navigation, and accessibility for legal professionals.

## Requirements

### Validated

- ✓ DOM-aware page marker insertion into HTML — Phase 2
- ✓ Automated PDF snippet extraction with PyMuPDF/pdfplumber backends — Phase 4
- ✓ Word segmentation for PDFs with missing spaces (Greek dictionary) — Phase 4
- ✓ InDesign metadata filtering (sluglines, timestamps) — Phase 5
- ✓ Dehyphenation for words split across lines — Phase 5
- ✓ Page offset support for magazines with continuing page numbers — Phase 6
- ✓ Footnote filtering with `--skip-footnotes` — Phase 6
- ✓ Partial word completion using HTML reference — Phase 6
- ✓ Context-based correction for merged words — Phase 6
- ✓ CSS injection for visible markers in browser — Phase 6
- ✓ Sequential position tracking for duplicate disambiguation — Phase 8
- ✓ Context matching with Jaccard similarity scoring — Phase 10
- ✓ Visual marker editor with drag-and-drop, add/edit/delete markers — Phase 11
- ✓ Auto-save to localStorage with recovery prompt — Phase 11
- ✓ Copy Body Content for single-article re-editing — Phase 11
- ✓ PDF splitting CLI command and browser tool — Phase 12
- ✓ Professional Python packaging with Click CLI — Phase 3
- ✓ Comprehensive test suite (79 tests) — Phase 3
- ✓ Editor JS namespace modules with EventBus and State — Phase 1 (visual editor milestone)
- ✓ Content integrity: marker moves preserve all HTML classes/attributes — Phase 1 (visual editor milestone)
- ✓ Export diff check validates non-marker structure — Phase 1 (visual editor milestone)
- ✓ Marker factory consolidated from 4 duplicated sites — Phase 1 (visual editor milestone)

### Active

- [ ] Improved drag-and-drop precision with snap-to-word-gap behavior
- [ ] Click-to-move alternative to drag-and-drop for marker repositioning
- [ ] Marker list sidebar with click-to-jump navigation
- [ ] Search/jump-to-page-number quick navigation
- [ ] Out-of-order marker detection and visual warnings
- [ ] Gap detection for missing page numbers in sequence
- [ ] Duplicate page number flagging (distinguishing intentional two-column from accidental)
- [ ] Position sanity warnings (markers in headings, footnotes, wrong sections)

### Out of Scope

- Magazine validator integration — not a priority for this milestone
- Multi-language support (beyond Greek) — no current demand
- Multi-file workflow in editor — current copy-body-content workaround is sufficient
- Import/export pipeline integration in editor — CLI handles this adequately
- Dark mode — nice-to-have but not worth the effort now
- Keyboard shortcuts — mouse-driven workflow is acceptable
- Mobile/tablet support — editing is a desktop task

## Context

- **Brownfield project**: 12 phases of development already complete, production-ready CLI
- **Primary user**: The developer (Aris) processing Greek legal magazines for EPUB generation
- **Visual editor**: `tools/page-marker-editor.html` — standalone HTML file, no server, works offline
- **Editor is ~1854 lines** of vanilla JS in a single HTML file
- **Current pain points**: Drag precision is poor, hard to navigate large documents (200+ page markers), no validation feedback when markers are out of order or misplaced
- **Two-column PDFs**: Only ~57% automated success rate, so the visual editor is critical for fixing the remaining ~43% of markers manually
- **Codebase map**: Available in `.planning/codebase/` with architecture, stack, conventions, testing, and concerns analysis

## Constraints

- **Single-file constraint**: Editor must remain a single HTML file with no build step — this is a key design decision for portability and offline use
- **No frameworks**: Vanilla JS only in the editor — no React, Vue, etc.
- **Browser compatibility**: Must work in modern browsers (Chrome, Firefox, Safari)
- **Backwards compatible**: Editor must continue to load existing marked HTML files without breaking

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Single HTML file for editor | Portability, offline use, no build tooling | ✓ Good |
| Vanilla JS (no framework) | Simplicity, no dependencies, single-file constraint | ✓ Good |
| localStorage for auto-save | No server needed, works offline | ✓ Good |
| Click-to-move as alternative to drag | Drag precision is the #1 UX complaint | — Pending |
| Sidebar + search for navigation | Both needed for different use cases (browsing vs targeted jump) | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd:transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-03-31 after Phase 1 completion*
