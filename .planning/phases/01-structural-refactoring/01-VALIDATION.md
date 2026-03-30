---
phase: 1
slug: structural-refactoring
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-30
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Manual browser testing (single HTML file, no test framework) |
| **Config file** | none — standalone HTML file |
| **Quick run command** | Open `tools/page-marker-editor.html` in browser, load test file |
| **Full suite command** | Load `examples/sample_with_markers.html`, test all operations |
| **Estimated runtime** | ~60 seconds manual |

---

## Sampling Rate

- **After every task commit:** Open editor in browser, verify basic load/drag/undo works
- **After every plan wave:** Full manual test of all operations
- **Before `/gsd:verify-work`:** Complete regression test
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| TBD | TBD | 1 | ARCH-01 | manual | Open editor, verify namespace objects exist in console | N/A | ⬜ pending |
| TBD | TBD | 1 | ARCH-02 | manual | Verify EventBus.emit/on work in console | N/A | ⬜ pending |
| TBD | TBD | 1 | ARCH-03 | manual | Verify State.get/set work in console | N/A | ⬜ pending |
| TBD | TBD | 1 | ARCH-04 | manual | Grep for single createMarker factory | N/A | ⬜ pending |
| TBD | TBD | 1 | INTG-01 | manual | Move marker, inspect surrounding DOM for preserved attributes | N/A | ⬜ pending |
| TBD | TBD | 1 | INTG-02 | manual | Move marker, inspect source location for orphaned elements | N/A | ⬜ pending |
| TBD | TBD | 1 | INTG-03 | manual | Export HTML, diff against original (non-marker structure) | N/A | ⬜ pending |
| TBD | TBD | 1 | INTG-04 | manual | Undo/redo, verify exact state restoration | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

*Existing infrastructure covers all phase requirements — no test framework needed for a single HTML file refactoring.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| All editor features work identically | ARCH-01 | Browser-only HTML file | Load sample file, test load/drag/add/edit/delete/undo/redo/download/copy/autosave |
| Marker move preserves surroundings | INTG-01, INTG-02 | DOM inspection needed | Move marker, right-click inspect old/new location, verify attributes preserved |
| Export preserves original structure | INTG-03 | File comparison needed | Download exported HTML, diff against original (ignoring marker elements) |
| Undo/redo exact restoration | INTG-04 | Visual + DOM inspection | Make changes, undo all, compare DOM state |

---

## Validation Sign-Off

- [ ] All tasks have manual verify instructions
- [ ] Sampling continuity: browser test after each task
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
