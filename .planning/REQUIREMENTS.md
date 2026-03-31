# Requirements: RX Page Marker — Visual Editor Milestone

**Defined:** 2026-03-30
**Core Value:** Accurate page markers in EPUB files that match the print edition

**Portability constraint:** Editor must remain a single HTML file with zero dependencies, zero build step, works on any Windows/macOS machine by copying the folder — no installation required.

## v1 Requirements

### Architecture

- [x] **ARCH-01**: Editor JS is organized into namespace modules with clear boundaries (no behavior change)
- [x] **ARCH-02**: Central EventBus decouples modules — mutations emit events, consumers react
- [x] **ARCH-03**: Single State object replaces scattered globals — modules read/write via State API
- [x] **ARCH-04**: Marker element creation consolidated into single factory function

### Precision Interaction

- [ ] **PREC-01**: User can click a marker then click a destination word gap to move it (click-to-move)
- [ ] **PREC-02**: Drop positions snap to word boundaries with a clear visual gap indicator
- [ ] **PREC-03**: `caretPositionFromPoint` is primary API with `caretRangeFromPoint` fallback for Safari
- [ ] **PREC-04**: Drop cursor height matches actual line height at current zoom level

### Navigation

- [ ] **NAV-01**: Sidebar panel shows clickable list of all page markers with page numbers
- [ ] **NAV-02**: Clicking a marker in the sidebar scrolls the document to that marker's position

### Content Integrity

- [x] **INTG-01**: Moving a marker preserves all surrounding HTML elements, attributes, and classes — no content loss or stripping
- [x] **INTG-02**: Moving a marker leaves no orphaned tags, empty spans, or junk whitespace at the source location
- [x] **INTG-03**: Exported HTML preserves all original document classes, attributes, and structure outside of marker elements
- [x] **INTG-04**: Undo/redo restores exact document state including all HTML classes and attributes

### Validation

- [ ] **VAL-01**: Editor detects out-of-order markers and displays visual warning on affected markers
- [ ] **VAL-02**: Editor detects gaps in page number sequence and reports missing numbers
- [ ] **VAL-03**: Editor flags >2 occurrences of same page number as accidental duplicate (≤2 = valid two-column)
- [ ] **VAL-04**: Validation summary shown before download — user sees warning count and can proceed or fix

## v2 Requirements

### Navigation Enhancements

- **NAV-03**: Search/jump-to-page-number field for direct navigation
- **NAV-04**: Active marker tracking — sidebar highlights whichever marker is currently in viewport
- **NAV-05**: Scrollbar overview ruler showing marker density across document

### Validation Enhancements

- **VAL-05**: Position sanity warnings (markers in headings, footnotes, or wrong sections)
- **VAL-06**: Color-coded markers by validation state (green=ok, yellow=warning, red=error)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Magazine validator integration | Not priority for this milestone |
| Multi-language support | No current demand beyond Greek |
| Multi-file workflow | Copy-body-content workaround is sufficient |
| Dark mode | Nice-to-have, not worth the effort now |
| Keyboard-only navigation | Mouse-driven workflow is acceptable |
| Mobile/tablet support | Desktop-only editing task |
| Framework migration (React/Vue) | Violates single-file, zero-install constraint |
| Build step or bundler | Violates portability constraint |
| Text editing in document | Editor is for marker positioning only |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| ARCH-01 | Phase 1 | Complete |
| ARCH-02 | Phase 1 | Complete |
| ARCH-03 | Phase 1 | Complete |
| ARCH-04 | Phase 1 | Complete |
| INTG-01 | Phase 1 | Complete |
| INTG-02 | Phase 1 | Complete |
| INTG-03 | Phase 1 | Complete |
| INTG-04 | Phase 1 | Complete |
| NAV-01 | Phase 2 | Pending |
| NAV-02 | Phase 2 | Pending |
| VAL-01 | Phase 3 | Pending |
| VAL-02 | Phase 3 | Pending |
| VAL-03 | Phase 3 | Pending |
| VAL-04 | Phase 3 | Pending |
| PREC-01 | Phase 4 | Pending |
| PREC-02 | Phase 5 | Pending |
| PREC-03 | Phase 5 | Pending |
| PREC-04 | Phase 5 | Pending |

**Coverage:**
- v1 requirements: 18 total
- Mapped to phases: 18
- Unmapped: 0 ✓

---
*Requirements defined: 2026-03-30*
*Last updated: 2026-03-30 after roadmap creation — all 18 requirements mapped*
