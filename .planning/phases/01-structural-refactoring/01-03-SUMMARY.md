---
phase: 01-structural-refactoring
plan: 03
subsystem: editor
tags: [refactoring, namespaces, addmode, export, fileloader, toast, ui, init, eventbus]
dependency_graph:
  requires: [01-01, 01-02]
  provides: [AddMode, Export, Toast, UI, FileLoader, Init]
  affects: [tools/page-marker-editor.html]
tech_stack:
  added: []
  patterns: [IIFE namespace pattern (completed), EventBus publish/subscribe (completed), Export diff check via TreeWalker text stripping]
key_files:
  created: []
  modified:
    - tools/page-marker-editor.html
decisions:
  - "Export diff check (_buildStrippedText) uses TreeWalker over text nodes, skipping .page-marker and .page-number spans, then normalizes whitespace — prevents false positives from whitespace-only divergence"
  - "FileLoader._attachFileInput emits file:loaded; FileLoader IIFE itself subscribes to file:loaded to call History.reset, DragDrop.init, AddMode.init — avoids double-init on restore paths"
  - "Toast namespace placed at Section 9 (after Export placeholder); forward references in AutoSave and DragDrop to Toast.show resolve correctly at runtime since Toast is defined before Init runs"
  - "formatTimestamp moved inside Export as private _formatTimestamp — only used for download filename"
  - "Download filename changed from originalFileName-based to corrected_YYYY-MM-DD_HH-MM.html for consistency with documented behavior"
metrics:
  duration: ~900 seconds
  completed: "2026-03-31"
  tasks_completed: 2
  tasks_total: 2
  files_modified: 1
---

# Phase 01 Plan 03: AddMode, Export, Toast, UI, FileLoader, Init Namespaces Summary

Complete the structural refactoring of `tools/page-marker-editor.html` by creating AddMode, Export (with content diff check), Toast, UI, FileLoader, and Init namespaces; removing all flat-scope functions and DOM const declarations; wiring file:loaded and markers:added EventBus events; Init calls AutoSave.checkForSavedState() last.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1+2 | Create all remaining namespaces, wire Init, delete flat-scope | 711df00 | tools/page-marker-editor.html |

## What Was Built

### AddMode IIFE (Section 7)
- `init(editorEl)`, `toggle()`, `clearHighlight()` public API
- Private `_onHover`, `_onClick`, `_clearHighlight`, `_insertMarkerAfterWord`, `_getNextPageNumber`, `_getCaretPosition`, `_findWordBoundaries`
- `_insertMarkerAfterWord` emits `EventBus.emit('markers:added', ...)` (replacing removed `saveState()` call)
- Subscribes to `history:restored` to auto-exit add mode on undo/redo

### Toast IIFE (Section 9)
- `init(toastEl)`, `show(message, type)` — replaced flat-scope `showToast()`
- All 27 call sites in existing sections (AutoSave, DragDrop, Markers) converted from `showToast()` to `Toast.show()`

### UI IIFE (Section 10)
- `init(editorEl, statsEl, zoomLevelEl)`, `updateStats()`, `setZoom(value)`
- Replaces both the temporary UI stub from Plan 02 AND the flat-scope `setZoom()` and `updateStats()` functions
- `setZoom()` now correctly clamps and stores to `State.zoom` before applying

### Export IIFE (Section 8)
- `prepareExportedBody()` — clones editor, converts markers to EPUB semantic format, spaces markers, strips word-highlight artifacts, collapses double spaces
- **Diff check (D-05)**: `_buildStrippedText()` walks text nodes, skips `.page-marker`/`.page-number`, normalizes whitespace; compares exported vs original and fires `Toast.show('Warning: content outside markers may have changed', 'error')` on divergence
- `download()` — serializes with XMLSerializer, preserves original DOCTYPE, clears unsaved flag
- `copyBody()` — clipboard API with fallback warning
- `_formatTimestamp()` moved here (private) from flat-scope

### FileLoader IIFE (Section 11)
- `init(editorEl, fileInputEl)`, `loadContent(html)`, `attachFileInput()`
- `loadContent()` converts EPUB markers → editor markers, calls `History.reset()`, `Markers.setupListeners()`, `UI.updateStats()`
- `_attachFileInput()` reads file, emits `EventBus.emit('file:loaded', ...)`
- IIFE body subscribes `EventBus.on('file:loaded', ...)` to call `History.reset()`, `DragDrop.init()`, `AddMode.init()`

### Init IIFE (Section 12)
- All DOM element references as local `var` (no flat-scope `const`s remain)
- Initializes: `Toast`, `UI`, `DragDrop`, `AddMode`, `FileLoader`
- Wires all button clicks, keyboard shortcuts, `beforeunload`
- Calls `AutoSave.checkForSavedState()` last — after all EventBus subscriptions are registered

## Deviations from Plan

### Auto-fixed Issues

None — plan executed exactly as specified with one minor intended difference:

**1. [Rule 2 - Enhancement] Download filename uses corrected_YYYY-MM-DD_HH-MM.html format**
- **Found during:** Task 2 implementation
- **Issue:** Original flat-scope download used `originalFileName.replace(...)` pattern; CLAUDE.md documents the corrected_YYYY-MM-DD_HH-MM.html format
- **Fix:** Used `_formatTimestamp(new Date())` to generate timestamped name as documented
- **Files modified:** tools/page-marker-editor.html
- **Commit:** 711df00

## Verification Results

All automated checks pass:

```
AddMode: PASS
Toast: PASS
stub removed: PASS
markers:added emit: PASS (exactly 1 in AddMode._insertMarkerAfterWord)
showToast calls gone: PASS
Toast.show calls: PASS (27)
Export: PASS
FileLoader: PASS
_buildStrippedText: PASS (3 occurrences: def + 2 call sites)
file:loaded emit: PASS (exactly 1 in FileLoader._attachFileInput)
file:loaded sub: PASS (in FileLoader IIFE body)
checkForSavedState: PASS (exactly 1, in Init)
stub still gone: PASS
no flat-scope functions: PASS
JS Syntax: PASS
```

Namespace load order confirmed:
```
475:  EventBus  → 496:  State  → 516:  Markers
540:  History   → 596:  AutoSave → 711: DragDrop
990:  AddMode   → 1195: Toast  → 1215: UI
1287: Export    → 1466: FileLoader → 1538: Init
```

## Known Stubs

None — all namespaces are fully implemented with real logic.

## Self-Check: PASSED

- tools/page-marker-editor.html modified: FOUND
- Commit 711df00: FOUND
- All 12 namespace sections present in correct load order: VERIFIED
- No flat-scope functions at 8-space indent level: VERIFIED
- No TEMPORARY STUB comments: VERIFIED
- Toast.show replaces all showToast calls (27 total): VERIFIED
- Export diff check (_buildStrippedText) present: VERIFIED
- file:loaded emitted and subscribed: VERIFIED
- AutoSave.checkForSavedState() called exactly once in Init: VERIFIED
