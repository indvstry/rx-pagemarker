# Roadmap: RX Page Marker — Visual Editor UX Milestone

## Overview

Five phases transform the existing ~1854-line flat-scope visual marker editor into a structured, navigable, and self-validating tool. Phase 1 establishes the architectural foundation (namespace modules, EventBus, State object) that all subsequent phases depend on. Phase 2 adds sidebar navigation. Phase 3 adds sequence validation with visual feedback. Phase 4 introduces click-to-move as a precision alternative to drag. Phase 5 sharpens drag precision itself. The result is a tool where a user can quickly find any marker, see validation problems immediately, and place markers with confidence.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Structural Refactoring** - Reorganize flat-scope code into namespace modules with EventBus and central State — no behavior change
- [ ] **Phase 2: Sidebar Navigation** - Clickable marker list panel with jump-to-marker navigation
- [ ] **Phase 3: Sequence Validation** - Out-of-order, gap, and duplicate detection with visual warnings and pre-download gate
- [ ] **Phase 4: Click-to-Move** - Two-click precision alternative to drag for repositioning markers
- [ ] **Phase 5: Drag Precision** - Snap-to-word-gap drop cursor with correct API priority and dynamic height

## Phase Details

### Phase 1: Structural Refactoring
**Goal**: Editor JS organized into namespace modules with EventBus and single State object — same behavior, maintainable foundation for all new features
**Depends on**: Nothing (first phase)
**Requirements**: ARCH-01, ARCH-02, ARCH-03, ARCH-04, INTG-01, INTG-02, INTG-03, INTG-04
**Success Criteria** (what must be TRUE):
  1. All existing editor features work identically after refactoring — load, drag, add, edit, delete, undo, redo, download, copy body content, auto-save and restore all produce the same results as before
  2. Moving a marker leaves no orphaned tags, empty spans, or whitespace artifacts at the source location, and all surrounding HTML attributes and classes are preserved intact
  3. Exported HTML preserves all original document classes, attributes, and structure outside of marker elements — a diff of pre/post export shows only marker element changes
  4. Undo and redo restore the exact document state including all HTML classes and attributes — no validation artifacts bleed into history snapshots
**Plans**: 3 plans

Plans:
- [ ] 01-01-PLAN.md — Add EventBus, State, Markers namespaces; migrate 8 flat-scope globals; replace 3 inline marker createElement sites with Markers.createMarker factory
- [ ] 01-02-PLAN.md — Create History, AutoSave, DragDrop namespaces; wire EventBus mutations; harden moveMarker normalize() invariant
- [ ] 01-03-PLAN.md — Create AddMode, Export (with diff check), Toast, UI, FileLoader namespaces; wire Init; complete all EventBus wiring

### Phase 2: Sidebar Navigation
**Goal**: Users can navigate a 200+ marker document via a clickable sidebar list and jump directly to any marker
**Depends on**: Phase 1
**Requirements**: NAV-01, NAV-02
**Success Criteria** (what must be TRUE):
  1. A sidebar panel lists all page markers with their page numbers and a brief text preview, visible at all times while editing
  2. Clicking any entry in the sidebar list scrolls the document to that marker's position and brings it into view — even in documents with 200+ markers
  3. The sidebar remains accurate after any marker operation (add, move, edit, delete, undo, redo) — no stale entries
**Plans**: TBD

### Phase 3: Sequence Validation
**Goal**: Users see immediate visual warnings for out-of-order markers, sequence gaps, and accidental duplicates — and must acknowledge problems before downloading
**Depends on**: Phase 2
**Requirements**: VAL-01, VAL-02, VAL-03, VAL-04
**Success Criteria** (what must be TRUE):
  1. Out-of-order markers are visually highlighted in the editor and flagged with an icon in the sidebar — user can see at a glance which markers are in the wrong position
  2. Missing page numbers in the sequence are reported in the sidebar — user knows which page numbers are absent
  3. More than two occurrences of the same page number are flagged as accidental duplicates (two occurrences are treated as valid two-column layout)
  4. Clicking "Download" when validation problems exist shows a summary of warning count — user must confirm before the file is saved
**Plans**: TBD

### Phase 4: Click-to-Move
**Goal**: Users can reposition a marker with two precise clicks instead of a drag — a reliable fallback when drag precision is insufficient
**Depends on**: Phase 3
**Requirements**: PREC-01
**Success Criteria** (what must be TRUE):
  1. Clicking a marker activates pick mode — the marker shows a pulsing highlight and the cursor changes to indicate placement mode
  2. Clicking any word position in the document moves the selected marker to that word boundary — the marker lands exactly where clicked, not at a nearby approximation
  3. Pressing Escape cancels pick mode without moving the marker
  4. The moved marker appears in undo history and can be restored with Ctrl+Z
**Plans**: TBD

### Phase 5: Drag Precision
**Goal**: Drag-and-drop places markers at the exact word gap under the mouse pointer — drop cursor height and position are accurate at all zoom levels
**Depends on**: Phase 4
**Requirements**: PREC-02, PREC-03, PREC-04
**Success Criteria** (what must be TRUE):
  1. The drop cursor snaps to the gap between words — dragging slowly across a line shows the cursor jumping from gap to gap, never stopping mid-word
  2. The drop cursor height matches the actual line height at the current zoom level — it does not appear too tall or too short at non-default zoom
  3. Drag-and-drop places the marker at the position shown by the drop cursor — the marker does not jump to a different location on release
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Structural Refactoring | 0/3 | Not started | - |
| 2. Sidebar Navigation | 0/TBD | Not started | - |
| 3. Sequence Validation | 0/TBD | Not started | - |
| 4. Click-to-Move | 0/TBD | Not started | - |
| 5. Drag Precision | 0/TBD | Not started | - |
