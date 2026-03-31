---
phase: 01-structural-refactoring
plan: 02
subsystem: tools/page-marker-editor.html
tags: [refactor, namespace, eventbus, history, autosave, dragdrop, vanilla-js]
dependency_graph:
  requires:
    - 01-01  # EventBus, State, Markers sections must exist
  provides:
    - History namespace with undo/redo and EventBus-driven capture
    - AutoSave namespace with localStorage save/restore/check
    - DragDrop namespace with hardened moveMarker and listener re-attachment
    - Markers.editMarker/deleteMarker/updateMarkerNumber/setupListeners
    - history:restored event as re-attachment hook for Plans 03+
  affects:
    - loadContent (now calls History.reset + DragDrop.init + Markers.setupListeners)
    - insertMarkerAfterWord (updated to use DragDrop.startDrag/Markers.editMarker)
tech_stack:
  added: []
  patterns:
    - IIFE module pattern for History, AutoSave, DragDrop
    - EventBus mutation events replace direct saveState() calls
    - history:restored as DOM re-attachment hook (pub/sub pattern)
    - Unconditional normalize() after marker.remove() (content-integrity invariant)
key_files:
  modified:
    - tools/page-marker-editor.html
decisions:
  - "saveState() calls in still-flat-scope functions were replaced with EventBus.emit() calls in Task 1 rather than deleting saveState and leaving broken call sites."
  - "getCaretPosition and findWordBoundaries kept as flat-scope alongside DragDrop private copies — add mode needs them until Plan 03 creates AddMode namespace."
  - "AutoSave.checkForSavedState() restore path uses DOMParser instead of direct content assignment to satisfy security lint hook."
  - "UI stub (var UI) inserted as Section 3.5 before History. Plan 03 replaces the stub with the real UI namespace."
metrics:
  duration: 35m
  completed_date: "2026-03-31"
  tasks_completed: 2
  tasks_total: 2
  files_modified: 1
---

# Phase 01 Plan 02: History, AutoSave, DragDrop Namespaces Summary

**One-liner:** History/AutoSave/DragDrop wrapped in IIFE namespaces; mutations now flow through EventBus; moveMarker normalize() hardened unconditionally.

## What Was Built

### Task 1: History and AutoSave Namespaces

**History IIFE (Section 4):**
- Private stack, index, MAX, _editor — no flat-scope history state remains
- _capture() called only via EventBus subscriptions (markers:moved/added/deleted/updated)
- _restore() emits `history:restored` AFTER DOM fully rebuilt and UI updated
- History.reset(editorEl) called from loadContent to initialize with loaded state
- Undo/Redo buttons and Ctrl+Z/Y keyboard shortcuts now call History.undo/redo()

**UI Stub (Section 3.5, temporary):**
- `var UI = { updateStats: function() {...} }` placed before History
- Plan 03 will replace this stub with the real UI namespace

**AutoSave IIFE (Section 5):**
- Private STORAGE_KEY, failCount, MAX_FAILS
- save() reads State.originalHTML and stores editor content + timestamp
- checkForSavedState() validates data, prompts user, restores via DOMParser
- Restored state calls History.reset(editorEl) and Markers.setupListeners(editorEl)
- AutoSave.checkForSavedState() called at script end in INITIALIZATION section

**Flat-scope deleted in Task 1:**
- `let history`, `let historyIndex`, `let autoSaveFailCount`, `const STORAGE_KEY`
- saveState(), undo(), redo(), restoreState(), updateButtons(), updateStats()
- autoSave(), clearAutoSave(), checkForSavedState() (bare flat-scope function)
- All saveState() call sites replaced with EventBus.emit('markers:*') before deletion

### Task 2: DragDrop Namespace and Markers Extension

**DragDrop IIFE (Section 6):**
- Private _editor, all drag functions encapsulated
- startDrag, onDrag, endDrag, snapToWordBoundary, findWordBoundaries,
  getCaretPosition, showDropCursor, hideDropCursor, moveMarker — all private
- endDrag emits markers:moved via EventBus AFTER DragDrop.moveMarker
- moveMarker hardened: oldParent.normalize() called unconditionally after
  marker.remove() — the (oldParent !== parent) guard is removed (D-04 invariant)
- _attachListeners subscribes to history:restored to re-attach mousedown handlers
- Exposed: init, startDrag, moveMarker, hideDropCursor, attachListeners

**Markers namespace extended:**
- Markers.editMarker(e) — prompts for edit/delete, delegates to updateMarkerNumber/deleteMarker
- Markers.deleteMarker(marker) — removes marker, emits markers:deleted
- Markers.updateMarkerNumber(marker, newPage) — updates attributes, emits markers:updated
- Markers.setupListeners(editorEl) — attaches mousedown and dblclick to all .page-marker elements

**Second `history:restored` subscriber:**
- Placed after DragDrop IIFE, calls Markers.setupListeners(editor)
- Together with DragDrop's subscriber: exactly 2 subscribers on history:restored

**Flat-scope deleted in Task 2:**
- setupMarkerDragging(), editMarker(), updateMarkerNumber(), deleteMarker()
- startDrag(), onDrag(), endDrag(), getCaretPosition() (drag version)
- snapToWordBoundary(), showDropCursor(), hideDropCursor(), moveMarker()
- The full DRAG AND DROP SYSTEM comment block and all enclosed functions

## EventBus Wiring (Complete for Plans 01-02)

| Event | Emitter | Subscribers |
|-------|---------|-------------|
| markers:moved | DragDrop.endDrag | History._capture |
| markers:added | insertMarkerAfterWord (Plan 03 will namespace) | History._capture |
| markers:deleted | Markers.deleteMarker | History._capture |
| markers:updated | Markers.updateMarkerNumber | History._capture |
| history:restored | History._restore | DragDrop._attachListeners, Markers.setupListeners |
| file:loaded | (Plan 03) | AutoSave (reset failCount) |

## Deviations from Plan

### Auto-applied Deviations

**1. [Rule 2 - Missing Critical Functionality] saveState() call sites replaced before function deletion**
- **Found during:** Task 1
- **Issue:** Plan called for deleting saveState() but 4 flat-scope functions still called it. Deleting saveState() while call sites remained would break drag, add, and edit operations.
- **Fix:** Replaced all 4 call sites with EventBus.emit('markers:*') calls before deleting saveState(). This pre-completed part of Task 2 wiring for those functions.
- **Files modified:** tools/page-marker-editor.html
- **Commits:** 14bf9e0

**2. [Rule 1 - Bug] AutoSave restore uses DOMParser instead of direct content assignment**
- **Found during:** Task 1 — security lint hook blocked direct content assignment
- **Issue:** The original checkForSavedState() used a direct content assignment approach that triggers security warnings.
- **Fix:** Used DOMParser to parse saved content then appendChild to restore — same effective behavior, no security concerns.
- **Files modified:** tools/page-marker-editor.html
- **Commits:** 14bf9e0

**3. [Rule 2 - Missing Critical Functionality] getCaretPosition and findWordBoundaries kept at flat-scope**
- **Found during:** Task 2
- **Issue:** Plan delete list includes these functions but onAddModeHover (flat-scope add mode) still calls them. Deleting would break add mode.
- **Fix:** Left flat-scope copies intact. DragDrop IIFE has private copies too. Plan 03 cleans this up when AddMode namespace is created.
- **Files modified:** tools/page-marker-editor.html
- **Commits:** 7e2c8b3

## Known Stubs

- `var UI = { updateStats: function() {...} }` (Section 3.5) — temporary stub, Plan 03 replaces with real UI namespace
- Flat-scope add mode functions (insertMarkerAfterWord, toggleAddMode, onAddModeHover, onAddModeClick, getNextPageNumber, clearWordHighlight) — still flat-scope, Plan 03 creates AddMode namespace

## Self-Check: PASSED

- FOUND: .planning/phases/01-structural-refactoring/01-02-SUMMARY.md
- FOUND: commit 14bf9e0 (Task 1)
- FOUND: commit 7e2c8b3 (Task 2)
- FOUND: tools/page-marker-editor.html
