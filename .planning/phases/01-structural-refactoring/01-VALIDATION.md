---
phase: 1
slug: structural-refactoring
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-30
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Bash grep + manual browser testing (single HTML file, no test framework) |
| **Config file** | none — standalone HTML file |
| **Quick run command** | Bash acceptance_criteria greps from each task |
| **Full suite command** | Load `examples/sample_with_markers.html`, test all operations |
| **Estimated runtime** | ~10 seconds automated greps + ~60 seconds manual |

---

## Sampling Rate

- **After every task commit:** Run bash grep commands from task's `<automated>` block
- **After every plan wave:** Full manual test of all operations
- **Before `/gsd:verify-work`:** Complete regression test
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Automated Command | Status |
|---------|------|------|-------------|-------------------|--------|
| 01-01-T1 | 01-01 | 1 | ARCH-02, ARCH-03 | `grep -c 'var EventBus' tools/page-marker-editor.html \| grep -q '^1$' && echo PASS` | ⬜ pending |
| 01-01-T1 | 01-01 | 1 | ARCH-03 | `grep -c "State\.set(" tools/page-marker-editor.html \| awk '{if($1>=10) print "PASS"; else print "FAIL"}'` | ⬜ pending |
| 01-01-T2 | 01-01 | 1 | ARCH-04 | `grep -c 'var Markers' tools/page-marker-editor.html \| grep -q '^1$' && echo PASS` | ⬜ pending |
| 01-01-T2 | 01-01 | 1 | ARCH-04 | `grep -c "newMarker\.className = 'page-marker'" tools/page-marker-editor.html \| grep -q '^0$' && echo PASS` | ⬜ pending |
| 01-02-T1 | 01-02 | 2 | INTG-04 | `grep -c 'var History' tools/page-marker-editor.html \| grep -q '^1$' && echo PASS` | ⬜ pending |
| 01-02-T1 | 01-02 | 2 | INTG-04 | `grep -c "EventBus\.emit('history:restored')" tools/page-marker-editor.html \| grep -q '^1$' && echo PASS` | ⬜ pending |
| 01-02-T2 | 01-02 | 2 | INTG-01, INTG-02 | `grep -c 'var DragDrop' tools/page-marker-editor.html \| grep -q '^1$' && echo PASS` | ⬜ pending |
| 01-02-T2 | 01-02 | 2 | INTG-01, INTG-02 | `grep -c "oldParent\.normalize()" tools/page-marker-editor.html \| awk '{if($1>=1) print "PASS"; else print "FAIL"}'` | ⬜ pending |
| 01-02-T2 | 01-02 | 2 | INTG-04 | `grep -c "EventBus\.on('history:restored'" tools/page-marker-editor.html \| awk '{if($1>=2) print "PASS"; else print "FAIL"}'` | ⬜ pending |
| 01-03-T1 | 01-03 | 3 | INTG-03 | `grep -c 'var AddMode' tools/page-marker-editor.html \| grep -q '^1$' && echo PASS` | ⬜ pending |
| 01-03-T1 | 01-03 | 3 | INTG-03 | `grep -c "EventBus\.emit('markers:added'" tools/page-marker-editor.html \| grep -q '^1$' && echo PASS` | ⬜ pending |
| 01-03-T2 | 01-03 | 3 | INTG-03 | `grep -c 'var Export' tools/page-marker-editor.html \| grep -q '^1$' && echo PASS` | ⬜ pending |
| 01-03-T2 | 01-03 | 3 | INTG-03 | `grep -c '_buildStrippedText' tools/page-marker-editor.html \| awk '{if($1>=2) print "PASS"; else print "FAIL"}'` | ⬜ pending |
| 01-03-T2 | 01-03 | 3 | ARCH-01 | `grep -c "AutoSave\.checkForSavedState()" tools/page-marker-editor.html \| grep -q '^1$' && echo PASS` | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

*Existing infrastructure covers all phase requirements — no test framework needed for a single HTML file refactoring. All automated verification uses bash grep commands embedded directly in each task's `<automated>` block.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| All editor features work identically | ARCH-01 | Browser-only HTML file | Load sample file, test load/drag/add/edit/delete/undo/redo/download/copy/autosave |
| Marker move preserves surroundings | INTG-01, INTG-02 | DOM inspection needed | Move marker, right-click inspect old/new location, verify attributes preserved and `span:empty` count is 0 |
| Export preserves original structure | INTG-03 | File comparison needed | Download exported HTML, diff against original (ignoring marker elements) |
| Undo/redo exact restoration | INTG-04 | Visual + DOM inspection | Make changes, undo all, compare DOM state |

---

## Validation Sign-Off

- [x] All tasks have automated verify commands (`<automated>` blocks in each task)
- [x] Sampling continuity: automated grep after each task, browser test after each wave
- [x] Wave 0 covers all MISSING references (no test framework needed — bash greps are sufficient)
- [x] No watch-mode flags
- [x] Feedback latency < 60s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
