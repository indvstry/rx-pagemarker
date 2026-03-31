---
phase: 01-structural-refactoring
plan: 01
subsystem: editor
tags: [refactoring, eventbus, state, markers, namespaces]
dependency_graph:
  requires: []
  provides: [EventBus, State, Markers.createMarker, Markers.getAll, Markers.getByPage]
  affects: [tools/page-marker-editor.html]
tech_stack:
  added: []
  patterns: [EventBus pattern (publish/subscribe), State object with reactive set(), Factory pattern (Markers.createMarker)]
key_files:
  created: []
  modified:
    - tools/page-marker-editor.html
decisions:
  - "EventBus implemented as IIFE to keep listeners private; exposes on/off/emit"
  - "State uses plain object with set() method that emits state:changed event — enables future reactive listeners without changing call sites"
  - "Markers implemented as plain object (not IIFE) since it has no private state to protect"
  - "Site 4 in prepareExportedBody left untouched — it creates EPUB-format spans, not editor markers (Plan 03 handles it)"
  - "history, historyIndex, autoSaveFailCount kept as flat-scope — moved to private IIFEs in Plan 02"
metrics:
  duration: 323 seconds
  completed: "2026-03-31"
  tasks_completed: 2
  tasks_total: 2
  files_modified: 1
---

# Phase 01 Plan 01: EventBus, State, and Markers Infrastructure Summary

**One-liner:** Three infrastructure namespaces (EventBus IIFE, State reactive object, Markers factory) added to page-marker-editor.html, replacing all 8 flat-scope globals and 3 of 4 inline createElement blocks.

## What Was Built

### EventBus (Section 1)
Publish/subscribe event channel implemented as an IIFE. Private `listeners` map. Exposes `on(event, fn)`, `off(event, fn)`, `emit(event, data)`. Currently used only internally by `State.set()` to emit `state:changed` events. Plans 02 and 03 will wire feature namespaces to this channel.

### State (Section 2)
Plain object with 8 named properties matching the former flat-scope globals:
- `originalFileName`, `originalHTML` — file identity
- `zoom` — editor zoom level (50–200)
- `addMode` — whether add-marker mode is active
- `hasUnsavedChanges` — dirty flag
- `draggedMarker`, `dropTarget` — transient drag state
- `highlightedWord` — hovered word element in add mode

`State.set(key, value)` assigns the value and emits `EventBus.emit('state:changed', { key, value })`. Read sites use direct property access (`State.zoom`, `State.addMode`).

### Markers (Section 3)
Plain object namespace with three members:
- `Markers.createMarker(pageNum, markerId)` — factory that creates a `<span class="page-marker">` with all required attributes
- `Markers.getAll()` — returns all markers in `#editor`
- `Markers.getByPage(pageNum)` — returns markers matching a page number

## Tasks Completed

| Task | Description | Commit |
|------|-------------|--------|
| 1 | Add EventBus + State sections, remove 8 flat-scope globals, migrate all read/write sites | 33f668e |
| 2 | Add Markers namespace, replace 3 inline createElement blocks with Markers.createMarker() | 1770a04 |

## Verification Results

All automated checks passed:
- `var EventBus`: 1 match
- `var State`: 1 match
- `var Markers`: 1 match
- `State.set(` calls: 17 (>= 10 required)
- `EventBus.emit('state:changed'` calls: 1 (inside State.set only)
- `Markers.createMarker` calls: 4 (definition + 3 call sites)
- `Markers.getAll`: 1 match
- `Markers.getByPage`: 1 match
- `newMarker.className = 'page-marker'`: 0 matches (all inline blocks replaced)
- `newMarker.className = 'page-number'`: 1 match (export site untouched, as required)
- All 8 flat-scope declarations confirmed removed (0 matches each)

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None. All infrastructure is fully implemented and wired. The `state:changed` event is emitted but has no subscribers yet — this is intentional, subscribers will be added in Plans 02 and 03.

## Self-Check: PASSED

Files verified:
- `tools/page-marker-editor.html` — exists and contains all three sections
- Commit `33f668e` — confirmed in git log
- Commit `1770a04` — confirmed in git log
