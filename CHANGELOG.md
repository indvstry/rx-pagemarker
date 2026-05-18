# Changelog

## Help Page - 2026-05-18

### Added
- **`tools/help.html`**: Single-file user-facing reference for the visual marker editor. Vanilla HTML/CSS only, zero external dependencies, matches the editor's design tokens. Sections: Quick Start, All Actions (table), Keyboard Shortcuts, Auto-save & Recovery, Best Practices, Troubleshooting, Known Limitations, and pipeline context.
- **Sidebar link in `tools/page-marker-editor.html`**: A small "Need more help?" link at the bottom of the existing instructions sidebar opens `help.html` in a new tab. Editor core logic untouched.

### Design Note
The help page is a separate single file (Option A) rather than an in-editor modal. Reason: distribution model — the editor is shared by sending the HTML file directly, and `help.html` can be sent alongside (or zipped together) without bloating the editor or coupling docs to it. The vanilla CSS duplication is intentional, honoring the "single-file, no frameworks, no build step" constraint.

---

## PDF Splitting - 2025-03-23 (Phase 12)

### Added
- **`rx-pagemarker split` CLI command**: Extract a page range from a PDF file. Thin wrapper over PyMuPDF's `doc.select()`. Supports `--page-offset` for print-page → PDF-page conversion (subtracted: `print_page - offset = pdf_page`). Auto-generates output filename when `OUTPUT_PDF` is omitted.
- **`tools/pdf-splitter.html`**: Single-file browser tool for visual page-range extraction. Uses PDF.js for thumbnails and pdf-lib for client-side PDF creation (both via CDN). Supports offset mapping, frontmatter/backmatter zone marking, and shift-click range selection.

### Design Note
PDF splitting is **deliberately independent** from the marking pipeline. It exists as a convenience for slicing source PDFs before extraction — no shared state with `extract` or `mark`. The `--page-offset` semantics are also intentionally reversed from `extract`: split subtracts the offset (user thinks in print pages, tool converts to PDF pages), while extract adds it.

---

## Visual Marker Editor - 2025-01-17 (Phase 11)

### Added
- **`tools/page-marker-editor.html`**: Browser-based drag-and-drop tool for correcting misplaced page markers. Single HTML file, no server, no dependencies, works offline.
  - Drag markers between words to reposition
  - **+ Add Marker** mode: click any word to insert a marker after it (word-boundary only; suggests next sequential page number)
  - Double-click to edit/delete markers
  - Undo/redo (Ctrl+Z / Ctrl+Y), zoom controls, drop-position indicator
  - Download as `corrected_YYYY-MM-DD_HH-MM.html` or **Copy Body Content** to clipboard for per-article re-editing
  - **Auto-save to localStorage** after every change with restore prompt on reopen (7-day retention; notifies after 3 consecutive save failures)
  - Export skips corrupted markers without page numbers

### Known Limitation
Download uses XMLSerializer which reformats output (adds `<!DOCTYPE html>`, collapses whitespace, may reorder attributes). Content and structure are identical — safe for EPUB generation but not byte-for-byte identical to input.

---

## Context Matching - 2025-01-17 (Phase 10)

### Added
- **`--context-words N` flag**: Captures N words before/after each snippet during extraction (default: 4, set 0 to disable). Stored in JSON as `context_before` / `context_after` fields.
- **Jaccard-similarity scoring during marking**: When a snippet appears at multiple HTML locations, the inserter scores each candidate using normalized word overlap with the captured context (40% before-context, 60% after-context — after is more reliable for `end_of_page` strategy). Falls back to first sequential match if best score < 0.3.

### Why
Sequential position tracking (Phase 8) rejects snippets that appear earlier in the document, but can't *choose* between multiple valid later positions. Context matching disambiguates duplicates like "του δικαστηρίου" that appear verbatim on pages 200, 500, and 900.

### JSON Format Change
```json
{
  "page": 900,
  "snippet": "του δικαστηρίου",
  "context_before": "η απόφαση",
  "context_after": "είναι τελεσίδικη"
}
```

---

## Page Offset Hack for EPUB Navigation - 2025-01-15 (Phase 9)

### Behavior Change
- **Removed `--position-after` flag**: Markers are now always placed *after* the snippet text. Use `--page-offset` with the +1 adjustment instead.
- **The Offset Hack**: `end_of_page` extraction places a marker at the END of page N. EPUB readers expect "Page N+1" to land at the BEGINNING of page N+1 (i.e., right after the page N break). Adding +1 to the user-supplied `--page-offset` relabels the marker so EPUB navigation works correctly.
  - Formula: `offset = first_print_page - first_pdf_page + 1`
  - Example: PDF page 7 = print page 775 → use `--page-offset 769` (not 768)

### Why Not `beginning_of_page` Strategy
Tried it — only 72.7% success rate vs 97.8% for `end_of_page`. Page beginnings repeat headers/section titles too often; sequential tracking rejects too many duplicates.

---

## Sequential Position Tracking - 2025-01-14 (Phase 8)

### Fixed
- **Out-of-order marker placement**: When snippet text appeared multiple times in the document, the first occurrence won — even if it was many pages before the correct location. The marker for page 900 could land at the page 200 occurrence.

### How
- Process pages in ascending order
- Track both container index AND character position within container
- Each new marker must come *after* the previous marker's position
- Supports multiple page breaks within the same paragraph

### Added
- **`--start-page` / `--end-page`**: Restrict extraction to body content only. Critical for magazines where PDF frontmatter (TOC, masthead) isn't in the HTML export.

### Results
On XRDD 4/2025 magazine: 47 markers (18%, with 204 out-of-order removed) → **228/232 markers (98.3%)** after filtering + position tracking.

---

## CLI Simplification - 2025-01-13 (Phase 7)

### Behavior Change
- **HTML file is now a required positional argument** for `extract` (enables word completion by default).
- **New syntax**: `rx-pagemarker extract book.pdf snippets.json book.html`
- **`--raw-pdf` flag**: Opt out of HTML correction for faster but less accurate extraction.
- **`--fuzzy-match` flag**: Replaces older `--match-html` for slow fuzzy matching on corrupted PDFs.
- Better error messages when HTML is missing.

---

## Magazine Support & Smart Correction - 2025-01-XX (Phase 6)

### Added
- **`--page-offset N`**: For magazines with continuing page numbers across issues.
- **Footnote filtering by default**: Use `--include-footnotes` to include footnote text; `--min-font-size` to adjust the threshold (default: 8.5pt).
- **Partial word completion**: Cut-off words at snippet boundaries (e.g., "σύγ") are completed using the HTML reference (→ "σύγχυση"), with the marker placed after the *complete* word.
- **Context-based correction**: Merged words inside snippets are fixed by finding anchor sequences of 2-3 correctly-extracted words in the HTML and substituting the correct surrounding text.
- **`--inject-css` flag** on `mark`: Inject visible CSS for previewing page markers in a browser.

### Results
Match rate on test magazine improved from **71.8% → 98.9%** with context-based correction enabled.

---

## Production PDF Support - 2025-01-XX (Phase 5)

### Added
- **InDesign metadata filtering**: Auto-excludes sluglines (e.g., `file.indd 123`) and timestamps from extraction.
- **Dehyphenation**: Rejoins words split across lines (e.g., `αντισυμ-\nβαλλομένων` → `αντισυμβαλλομένων`) before HTML matching.
- **Text normalization**: Handles spacing around punctuation and slashes.
- **Validation improvement**: Strips HTML tags before snippet comparison; normalizes whitespace.

### CLI Options
- **`--exclude-pattern`**: Add custom regex patterns to exclude from extraction.
- **`--no-default-excludes`**: Disable the default InDesign filter list if needed.

### Results
Tested on 272-page two-column legal magazine: **78.6% content match rate** (before later phases pushed this above 97%).

---

## Dictionary Expansion - 2025-11-24

### 🎉 Major Enhancement

#### Expanded Greek Word Dictionary
- **What changed**: Greek dictionary expanded from ~50 words to ~10k most frequent words
- **Source**: Hermit Dave's Greek word frequency lists (top 10k from 50k available)
- **Impact**: Dramatically improved word segmentation accuracy for Greek PDFs with missing spaces
- **Coverage**: Now handles ~95% of common Greek text accurately

### 🔧 Technical Implementation

#### Dictionary Loading System
- Load dictionary from package resource file (`data/greek_words.txt`)
- Supports both Python 3.9+ (`importlib.resources.files`) and 3.7-3.8 (pkg_resources)
- Graceful fallback to basic 50-word dictionary if file not found
- Dictionary stored as plain text (one word per line) for easy maintenance

#### Package Structure Updates
- New directory: `src/rx_pagemarker/data/`
- New file: `src/rx_pagemarker/data/greek_words.txt` (9,713 words)
- Updated `pyproject.toml` to include data files in package distribution
- Module `word_segmentation.py` updated with file-based dictionary loading

### 📊 Performance & Quality

#### Dictionary Statistics
- **Total words**: 9,713 pure Greek words (filtered from 50k source)
- **Max word length**: 19 characters
- **Filter criteria**: Only Greek letters (α-ω, Α-Ω) with accents, no numbers or special chars

#### Test Results
```
Input:  τοβιβλίομου
Output: το βιβλίο μου  (the book mine)
Confidence: 100%

Input:  είναιπολύωραίο
Output: είναι πολύ ωραίο  (is very beautiful)
Confidence: 100%
```

### 📝 Documentation Updates

#### Files Updated
- `README.md` - Updated dictionary size and troubleshooting section
- `CLAUDE.md` - Updated current status and roadmap (dictionary expansion completed)
- `CHANGELOG.md` - This entry

### 🎯 Roadmap Impact

**Completed**: ✅ Expand Greek dictionary (50 words → 10k words)

**Next Priority**: Optimize HTML matching algorithm for large documents

### 📦 Data Source Attribution

Greek word frequency data sourced from:
- Repository: [hermitdave/FrequencyWords](https://github.com/hermitdave/FrequencyWords)
- File: `content/2018/el/el_50k.txt`
- License: MIT (maintained in project)

---

## Enhanced Version - 2025-01-22

### 🎉 Major Enhancements

#### 1. **Intelligent Snippet Matching Across Formatting Tags**
- **What changed**: Snippets can now span across `<i>`, `<b>`, `<span>`, and other inline formatting tags
- **Why it matters**: Users can copy text directly from PDFs without worrying about HTML structure
- **Example**: The snippet `"hello beautiful world"` will match even if the HTML is:
  ```html
  <span>hello </span><i>beautiful</i><span> world</span>
  ```
- **Technical**: Script searches within parent containers (paragraphs, divs, etc.) and reconstructs text by walking through the DOM tree

#### 2. **Template Generator Script**
- **What's new**: `generate_template.py` - automatically creates JSON files with placeholders
- **Why it matters**: Eliminates manual JSON creation and reduces syntax errors
- **Features**:
  - Specify number of pages
  - Roman numerals support for front matter (`--roman` flag)
  - Custom starting page numbers
  - Clear placeholders for easy Find/Replace workflow

### 🔧 Improvements

#### User Experience
- **Better error messages**: More helpful guidance when snippets aren't found
- **Informative tips**: Shows helpful tips about the enhanced capabilities
- **Clearer output**: Better formatting and statistics display

#### Documentation
- **Updated SNIPPET_GUIDE.md**: Now emphasizes that users can copy from PDF
- **Enhanced README.md**: Added template generation workflow
- **Updated QUICK_START.md**: Step-by-step guide including template generation

### 📊 Technical Details

#### Algorithm Changes
- **Old approach**:
  - Searched only within individual text nodes
  - Failed if snippet crossed tag boundaries

- **New approach**:
  - Searches within parent containers (p, div, td, etc.)
  - Gets combined text using `.get_text()`
  - Walks through DOM descendants to find exact insertion point
  - Handles complex nesting and formatting

#### Supported Container Elements
- Paragraphs: `<p>`
- Divisions: `<div>`
- Table cells: `<td>`, `<th>`
- Lists: `<li>`, `<dd>`, `<dt>`
- Headings: `<h1>` through `<h6>`
- Semantic: `<article>`, `<section>`, `<aside>`, `<blockquote>`

### 🧪 Testing

Created test suite with:
- **test_formatted.html**: HTML with various formatting scenarios
- **test_formatted_references.json**: Snippets that span across tags
- **Results**: 100% success rate (5/5 snippets found)

Notable test cases:
- Text across `<i>` boundaries
- Text across `<b>` and `<i>` tags
- Word split across THREE separate `<i>` tags: `<i>for</i><i>mat</i><i>ted</i>`
- Text spanning multiple `<span>` elements with different classes

### 📝 Files Added

1. `generate_template.py` - Template generator script
2. `test_formatted.html` - Test file with complex formatting
3. `test_formatted_references.json` - Test snippets
4. `CHANGELOG.md` - This file

### 📝 Files Modified

1. `page_marker.py` - Enhanced snippet matching algorithm
2. `README.md` - Added template generator documentation
3. `QUICK_START.md` - Updated workflow to include template generation
4. `SNIPPET_GUIDE.md` - Simplified instructions (copy from PDF now works!)

### 🎯 Impact for InDesign Exports

**Before**: Users had to carefully inspect HTML source and choose snippets that didn't cross formatting tags.

**After**: Users can:
1. Generate a template: `python generate_template.py 200 pages.json`
2. Open PDF and template side-by-side
3. Copy text from PDF
4. Paste into template (use Find Next to jump between placeholders)
5. Run the script
6. Done!

### 🚀 Usage Example

```bash
# Setup (one time)
./setup.sh

# Activate virtual environment
source venv/bin/activate

# Generate template for a 200-page book
python generate_template.py 200 my_book.json

# Edit my_book.json and fill in snippets from PDF

# Run page marker script
python page_marker.py book.html my_book.json book_with_pages.html

# Deactivate when done
deactivate
```

### 🎓 Key Learnings

1. **BeautifulSoup's `.get_text()` is powerful**: Strips all tags and gives clean text
2. **`.descendants` enables position tracking**: Iterate through all nodes to find insertion points
3. **User experience > technical purity**: The "smart" approach is more complex but dramatically better UX
4. **Template generation reduces friction**: Removing JSON syntax concerns makes the tool accessible to non-programmers

### 🔮 Future Enhancements (Not Implemented)

Potential improvements for future versions:
- Auto-extract page breaks from PDF using pdfminer or PyPDF2
- Interactive mode to preview matches before insertion
- Batch processing for multiple HTML files
- GUI for non-technical users
- Fuzzy matching for slight variations in whitespace
