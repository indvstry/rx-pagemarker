# Feature Landscape: Visual Marker Editor (UX Milestone)

**Domain:** Browser-based document annotation/marker editor for EPUB3 page marker correction
**Researched:** 2026-03-30
**Research mode:** Ecosystem + Feasibility

---

## Context

This research targets the UX improvement milestone for `tools/page-marker-editor.html` — a standalone
single-file vanilla JS editor where the user (Aris) loads marked HTML files and corrects misplaced
page markers by dragging them or adding/deleting them before downloading the corrected file.

**Primary pain points (from PROJECT.md):**
1. Drag precision is poor — markers don't snap cleanly to word gaps
2. No navigation — 200+ markers in a large document means endless scrolling to find the one to fix
3. No validation — out-of-order, missing, or duplicate markers are only caught in the EPUB reader

**Constraint:** Single HTML file, vanilla JS, no build step, no frameworks.

---

## Table Stakes

Features users expect from any document editing tool. Missing these makes the editor feel broken
or unusable for the stated task.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Snap-to-word-gap on drop | Current drop position can land mid-word or on punctuation; every annotation editor snaps to word boundaries | Medium | Already partially implemented via `caretPositionFromPoint`; needs to be more reliable at paragraph/element boundaries |
| Click-to-move (two-click) as drag alternative | Drag-and-drop has inherent imprecision per Fitts's Law — NN/G recommends always pairing drag with a more precise alternative interaction | Medium | User clicks marker (select), then clicks target word gap (place). Escape to cancel. Active marker should be highlighted |
| Marker list sidebar with scroll-to | Long documents (200+ markers) require a way to find a specific marker without scrolling the entire document; VS Code's overview ruler and sidebar navigation are the reference pattern | Medium | Clickable list of all marker numbers; clicking scrolls editor to that marker and briefly highlights it |
| Search / jump-to-page-number | Complement to the sidebar — user types "897" and jumps directly to that marker | Low | Input field + Enter key; must handle missing markers gracefully (no marker 897 → show toast) |
| Out-of-order marker warning | EPUB page-list navigation breaks silently when markers are out of order; this is not detectable by the user until they test in an EPUB reader | Medium | Detect after every edit operation; highlight out-of-order markers in orange/yellow; show count in stats bar |
| Gap detection (missing page numbers) | For a 232-page body, missing page 847 is as bad as a misplaced one — the user cannot know without a sequence audit | Low | Compare marker sequence against expected consecutive range; show gaps in sidebar or as a summary warning |
| Duplicate page number flagging | Intentional duplicates (two-column layout) are valid; accidental duplicates are bugs. Editor must distinguish | Medium | Warn when same page number appears 3+ times (2 is valid for two-column); show in sidebar with distinct styling |
| Undo/Redo reliability | Already implemented, but undo after drag must restore the exact pre-drag position | Low | Currently present; verify it handles the new click-to-move mode too |
| Toast notifications for all operations | User needs confirmation that the action took effect | Low | Already implemented; extend to cover new validation events |
| Download with timestamped filename | Prevents accidentally overwriting previous versions | Low | Already implemented (`corrected_YYYY-MM-DD_HH-MM.html`) |
| Zoom controls | Precise drag/click requires seeing the text clearly | Low | Already implemented; verify it works correctly with click-to-move |

---

## Differentiators

Features that are not expected but add significant value for this specific use case. They distinguish
a professional EPUB production tool from a generic annotation editor.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Scrollbar overview ruler with marker density map | Shows the distribution of all markers along the right edge of the document, like VS Code's overview ruler. Red dots for out-of-order, green for valid. User can click to jump. Far more efficient than scrolling for finding problems in a 200-page document | High | Requires a second thin `<div>` as a proportional map; compute marker Y-positions relative to total document height; update on every edit |
| "Next problem" / "Previous problem" keyboard navigation | Tab through out-of-order, missing, and duplicate markers without touching the mouse. F8 / Shift+F8 is the VS Code convention; adapting this pattern for a document editor is novel and high-value | Medium | Only meaningful if validation (out-of-order + gap detection) is implemented first |
| Heading/footnote zone warnings | A marker placed inside a heading or a footnote `<span>` will disrupt EPUB rendering (documented in CLAUDE.md best practices). The editor can detect this and warn the user before download | Medium | Check parent element tag on drop: if `<h1>`-`<h6>` or inside a footnote class, show inline warning on the marker badge |
| Auto-suggest next page number on add | When the user clicks "+ Add Marker", the editor already suggests the next sequential number. Improving this to account for the gap (e.g., the previous is 847, the next existing is 849, suggest 848) is a small UX win | Low | Extend the existing `suggestNextPageNum()` logic; detect gap between surrounding markers |
| Validation summary panel (pre-download gate) | Before download, show a summary: "3 out-of-order markers, 2 gaps, 0 duplicates — download anyway?" This is the right moment to surface issues without interrupting the editing workflow | Low | Modal or inline summary triggered by the Download button; user can dismiss and fix, or proceed |
| Export snippet count in stats bar | Current stats bar shows marker count. Adding a count of "problems" (out-of-order + gaps + accidentals) gives the user a live status of document health without opening the sidebar | Low | Update `updateStats()` to include a problem count with color coding (green = 0, orange = any) |
| Marker badge color coding by validation state | Valid = green, out-of-order = orange, in-heading = yellow, no-ID = red. Color communicates status without requiring the user to open any panel | Medium | Requires re-running validation after each edit and updating CSS classes on markers |

---

## Anti-Features

Features that would be harmful to build, either because they violate the project constraints or
because they add complexity without matching the actual use case.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Real-time collaboration | The tool is used by one person (Aris) processing one file at a time. Adding collaboration adds significant complexity for zero benefit | Keep the tool single-user; localStorage auto-save is sufficient |
| Text editing / content changes | The editor must never change the article text — only move/add/delete marker spans. If text editing is allowed, EPUB export quality is at risk | Enforce read-only content; only markers are interactive |
| Comment or highlight annotation types | This is a page marker tool, not a general annotation tool. Adding other annotation types dilutes the purpose and bloats the codebase | Scope strictly to page-number markers (`<span class="page-marker">`) |
| Multi-file workflow in the editor | The copy-body-content workaround is sufficient for splitting articles. A multi-file workflow would require a file manager, session state, and conflict resolution | Maintain single-file-at-a-time workflow; improve "Copy Body Content" reliability instead |
| Dark mode | Nice-to-have, listed as out-of-scope in PROJECT.md, and adds CSS maintenance burden | Skip; use system default |
| Mobile / tablet support | Drag-and-drop precision editing is a desktop task; Greek legal magazine editing happens on a workstation | Skip responsive layout work beyond the existing media query |
| Keyboard-only marker editing | Full keyboard navigation (for accessibility) is not needed for a single-user production tool. Current Ctrl+Z/Ctrl+Y and Escape are sufficient | Add only the "next problem" navigation shortcut as a targeted improvement, not full keyboard accessibility |
| Undo history persistence across sessions | localStorage already saves the document state. Saving the undo stack would increase localStorage size and complexity significantly | On restore, start with a fresh undo history (current behavior is correct) |
| AI-assisted marker placement suggestions | Out of scope for this milestone; would require backend communication and violates the offline/single-file constraint | Defer indefinitely; the CLI pipeline already achieves 97%+ automated accuracy |
| PDF preview side-by-side | The separate `pdf-splitter.html` tool handles PDF viewing. Embedding a PDF viewer in the marker editor violates the single-file and offline constraints | Keep the tools separate; use `pdf-splitter.html` for PDF reference |

---

## Feature Dependencies

```
Out-of-order detection
  └─> marker color coding (requires detection results on each marker)
  └─> validation summary panel (requires detection results as input)
  └─> "Next problem" navigation (requires detection results to iterate)
  └─> scrollbar overview ruler (requires detection results for red/green dot color)

Gap detection
  └─> depends on knowing the expected page range (needs start/end page inputs OR derived from existing markers)
  └─> validation summary panel (contributes to the summary count)
  └─> "Next problem" navigation (gaps are also "problems" to cycle through)

Click-to-move
  └─> independent of validation features
  └─> shares the "selected marker" visual state with color coding (both need to modify marker appearance)
  └─> must integrate with undo/redo (same saveState() call as drag)

Marker list sidebar
  └─> requires out-of-order detection to show status icons next to each entry
  └─> search/jump-to-page-number can be embedded in the sidebar or standalone
  └─> scrollbar overview ruler is a complement (map vs list — different navigation styles)

Heading/footnote zone warnings
  └─> independent; triggered on drop/placement
  └─> contributes to the validation summary count
```

---

## MVP Recommendation

The minimum set that solves the three stated pain points:

**Pain point 1 (drag precision):**
- Build click-to-move as the primary alternative interaction (Medium complexity)
- Improve snap behavior to reliably land at word gaps including at element boundaries (Low-Medium)

**Pain point 2 (navigation in large documents):**
- Build marker list sidebar with click-to-scroll (Medium complexity)
- Add search/jump-to-page-number (Low complexity)

**Pain point 3 (no validation):**
- Build out-of-order detection with visual marker highlighting (Medium complexity)
- Add gap detection with sidebar indication (Low complexity — once out-of-order is done)
- Build validation summary pre-download gate (Low complexity — requires detection first)

**Defer:**
- Scrollbar overview ruler (High complexity; sidebar + search covers navigation adequately for MVP)
- "Next problem" keyboard navigation (depends on validation; can add in a follow-up)
- Marker badge color coding (valuable but add after validation logic is stable)
- Heading/footnote zone warnings (Medium complexity; useful but not a core pain point)

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Table stakes identification | HIGH | Based on direct user feedback (PROJECT.md pain points), verified against NN/G and UX research |
| Drag precision patterns | HIGH | NN/G drag-and-drop guidelines verified via WebSearch; click-to-move is a standard precision fallback |
| Navigation patterns | HIGH | VS Code overview ruler and sidebar patterns are well-documented; directly applicable |
| Validation UX patterns | MEDIUM | General inline validation research applies; specific sequence-gap detection patterns are less documented but logically sound |
| Complexity estimates | MEDIUM | Estimated against current 1854-line single-file constraint; actual complexity depends on JS implementation details |
| Anti-features | HIGH | Grounded in PROJECT.md out-of-scope decisions and single-file constraint |

---

## Sources

- [Drag–and–Drop: How to Design for Ease of Use - NN/G](https://www.nngroup.com/articles/drag-drop/)
- [Drag-and-Drop UX: Guidelines and Best Practices - Smart Interface Design Patterns](https://smart-interface-design-patterns.com/articles/drag-and-drop-ux/)
- [Best UX Practices for Designing a Sidebar Menu in 2025](https://uiuxdesigntrends.com/best-ux-practices-for-sidebar-menu-in-2025/)
- [Inline Validation UX - Smart Interface Design Patterns](https://smart-interface-design-patterns.com/articles/inline-validation-ux/)
- [VS Code Overview Ruler - GitHub issue #23587](https://github.com/Microsoft/vscode/issues/23587)
- [Scroll bar map mode and bar mode - Visual Studio - Microsoft Learn](https://learn.microsoft.com/en-us/visualstudio/ide/how-to-track-your-code-by-customizing-the-scrollbar?view=visualstudio)
- [Why I Use Page List, and How - EPUBSecrets](https://epubsecrets.com/why-i-use-page-list-and-how.php)
- [Page List - Accessible Publishing Knowledge Base - DAISY](https://kb.daisy.org/publishing/docs/navigation/pagelist.html)
- PROJECT.md — active requirements and pain points
- CLAUDE.md — best practices for marker placement (headings, footnotes)
- `tools/page-marker-editor.html` — current implementation (1854 lines)
