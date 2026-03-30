# Phase 1: Structural Refactoring - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-30
**Phase:** 01-structural-refactoring
**Areas discussed:** Module boundaries, Content integrity

---

## Module Boundaries

### Code Organization Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| By feature (Recommended) | DragDrop, Markers, History, AutoSave, Export, UI — each namespace owns its functions and state. ~6 modules. | ✓ |
| By layer | DOM, State, Events, IO — separated by responsibility type rather than feature. More abstract. | |
| You decide | Let Claude choose the best module structure based on the codebase analysis | |

**User's choice:** By feature
**Notes:** User selected with preview showing namespace object pattern

### Instructions Panel

| Option | Description | Selected |
|--------|-------------|----------|
| Keep as-is for now | Don't touch the instructions panel in Phase 1 — sidebar restructuring happens in Phase 2 | ✓ |
| Prepare tab structure | Add a tab container now (Instructions tab only) so Phase 2 just adds a Markers tab | |

**User's choice:** Keep as-is for now
**Notes:** None

---

## Content Integrity

### Marker Removal Cleanup

| Option | Description | Selected |
|--------|-------------|----------|
| Merge text only (Recommended) | Only merge adjacent text nodes after removal — never touch parent elements, classes, or attributes | ✓ |
| Full DOM cleanup | Also remove any empty wrapper spans left behind after marker removal | |
| You decide | Let Claude determine the safest cleanup strategy | |

**User's choice:** Merge text only
**Notes:** None

### Export Validation

| Option | Description | Selected |
|--------|-------------|----------|
| Diff check (Recommended) | After export, compare non-marker DOM structure against original — warn if anything outside markers changed | ✓ |
| No validation | Trust the export logic — keep it simple | |
| You decide | Let Claude determine what level of export validation makes sense | |

**User's choice:** Diff check
**Notes:** None

---

## Additional Constraints (User-Initiated)

- **EPUB marker format is sacrosanct**: The `<span id="pageN" class="page-number" role="note" aria-label="Page N">N</span>` format must not change. Any alternative encoding requires explicit user approval with reasoning.
- **Portability**: Editor must remain a single HTML file with zero install, working on both Windows and macOS.

## Claude's Discretion

- State management details (central State vs namespace-local)
- Event architecture granularity and naming

## Deferred Ideas

None
