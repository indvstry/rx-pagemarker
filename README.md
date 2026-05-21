# RX Page Marker

A Python tool to insert page number markers into HTML files for EPUB3 generation. Uses text snippets from a mapping file to accurately place page breaks that match the original PDF pagination.

## Features

- **🚀 Automated PDF extraction**: Automatically extract text snippets from PDF files (supports Greek and Unicode text)
- **⚡ High performance**: Process 500+ page PDFs in seconds using PyMuPDF
- **🎯 Smart extraction strategies**: Choose between end-of-page text or visual positioning
- **🔧 Word boundary reconstruction**: Handles PDFs with missing spaces using dictionary-based segmentation
- **🎯 HTML-based correction**: Match PDF snippets against clean HTML for perfect word boundaries
- **🔁 Sequential position tracking**: Handles duplicate snippets and multiple page breaks per paragraph by tracking insertion progress in document order
- **🧭 Context matching**: Disambiguates duplicate snippets using surrounding-words similarity (Jaccard scoring) — see `--context-words`
- **📐 Page offset hack**: `--page-offset` with +1 adjustment produces EPUB-correct page-list semantics from `end_of_page` extraction
- **📊 Confidence scoring**: Review mode shows quality scores for automatically extracted snippets
- **✅ Built-in validation**: Check for duplicates and verify snippets exist in HTML
- **✨ Intelligent snippet matching**: Finds text even when split across formatting tags (`<i>`, `<b>`, `<span>`)
- **DOM-aware insertion**: Uses BeautifulSoup to parse HTML structure, preventing markers from being inserted into attributes or tags
- **InDesign-friendly**: Handles complex HTML exports with heavy inline formatting; auto-filters sluglines/timestamps and dehyphenates words split across lines
- **Accessibility support**: Generates page markers with proper ARIA attributes
- **Detailed reporting**: Shows statistics on successful insertions, missing snippets, and multiple matches
- **Fallback-ready**: Manual mapping file ensures accuracy when automation isn't feasible
- **🖱️ Visual marker editor**: Browser-based drag-and-drop tool (`tools/page-marker-editor.html`) for correcting misplaced markers with auto-save, undo/redo, and add/edit/delete — no server, no install
- **✂️ PDF splitting**: `rx-pagemarker split` CLI and `tools/pdf-splitter.html` browser tool for extracting page ranges from magazine PDFs (independent from the marking pipeline)

## Installation

### Development Installation (Recommended)

```bash
# Clone or navigate to the project directory
cd rx-pagemarker

# Install in editable mode with all features and development dependencies
pip install -e ".[pdf,dev]"
```

This installs:
- The `rx-pagemarker` command-line tool
- Core dependencies (beautifulsoup4, lxml, click)
- PDF extraction libraries (PyMuPDF, pdfplumber, rapidfuzz)
- Development tools (pytest, black, mypy, flake8)

**Note:** If you only need the manual workflow (without PDF extraction), you can install just the dev dependencies:
```bash
pip install -e ".[dev]"
```

### User Installation

```bash
# With PDF extraction support
pip install "rx-pagemarker[pdf]"

# Or without PDF extraction (manual workflow only)
pip install rx-pagemarker
```

Or install directly from the repository:

```bash
# With PDF extraction
pip install "rx-pagemarker[pdf] @ git+https://github.com/yourusername/rx-pagemarker.git"

# Without PDF extraction
pip install git+https://github.com/yourusername/rx-pagemarker.git
```

## Usage

There are two workflows: **automated PDF extraction** (recommended) or **manual template generation**.

### Workflow 1: Automated PDF Extraction (Recommended)

The fastest way to get started is to automatically extract snippets directly from your PDF.

#### Step 1: Extract Snippets from PDF

```bash
# Standard usage - PDF + JSON output + HTML reference (recommended)
rx-pagemarker extract book.pdf snippets.json book.html

# Extract specific page range (useful for testing)
rx-pagemarker extract book.pdf snippets.json book.html --start-page 1 --end-page 50

# Magazine with page offset (PDF page 7 = print page 507)
rx-pagemarker extract magazine.pdf snippets.json magazine.html --start-page 7 --page-offset 500

# Use pdfplumber for complex layouts with tables/columns
rx-pagemarker extract book.pdf snippets.json book.html --backend pdfplumber
```

**Why HTML is required by default:**
The HTML file is used to correct and complete extracted text:
- Completes hyphenated words at line breaks (e.g., `λό-` → `λόγω`)
- Fixes spacing and quote character differences
- Ensures snippets match the HTML exactly for reliable marker insertion

**Raw PDF mode (no HTML):**
```bash
# If you don't have an HTML file, use --raw-pdf (less accurate)
rx-pagemarker extract book.pdf snippets.json --raw-pdf
```

**Extraction Strategies:**
- `end_of_page` (default) - Extracts last N words from text (faster, simpler)
- `bottom_visual` - Extracts text from visually lowest position on page (better for complex layouts)

**Backends:**
- `auto` (default) - Automatically uses PyMuPDF if available, falls back to pdfplumber
- `pymupdf` - Fast C-based extraction, excellent for large files (500+ pages)
- `pdfplumber` - Better layout analysis, handles tables and columns well

**Footnotes:**
- By default, footnotes are **skipped** (uses font size filtering)
- Use `--include-footnotes` to include footnote text
- Use `--min-font-size` to adjust the threshold (default: 8.5pt)

**Note:** Supports Greek and all Unicode text natively.

#### Advanced: Handling PDFs with Spacing Issues

Some PDFs (especially from Quark→InDesign→PDF conversions) have broken text encoding where spaces between words are missing. The tool provides additional strategies:

**Option 1: Fuzzy Matching** (For heavily corrupted PDFs)

```bash
# Use slow fuzzy matching for complex layouts
rx-pagemarker extract book.pdf snippets.json book.html --fuzzy-match --review
```

This uses fuzzy string matching to find the best match in HTML. Slower but more robust for heavily corrupted text.

**Option 2: Word Segmentation** (Dictionary-based, no HTML needed)

```bash
# Enable word boundary reconstruction using Greek dictionary
rx-pagemarker extract book.pdf snippets.json --raw-pdf --segment-words --review

# Use with different language (currently supports: el=Greek)
rx-pagemarker extract book.pdf snippets.json --raw-pdf --segment-words --language el --review
```

This uses a dictionary-based algorithm to reconstruct word boundaries. The `--review` flag shows confidence scores so you can identify snippets that may need manual correction.

**Performance Comparison:**

| Mode | Speed (272 pages) | Accuracy |
|------|-------------------|----------|
| Standard (with HTML) | ~30-60 seconds | High |
| `--raw-pdf` | ~2 seconds | Lower (may not match HTML) |
| `--fuzzy-match` | ~5-10 minutes | Highest (for corrupted PDFs) |

**Dictionary Size:** The Greek word segmentation uses ~10k most frequent words from Hermit Dave's frequency lists, providing comprehensive coverage for modern Greek text.

#### Step 2: Validate Extracted Snippets

```bash
# Check for duplicates and placeholders
rx-pagemarker validate snippets.json

# Validate against your HTML file to check if snippets will be found
rx-pagemarker validate snippets.json --html book.html
```

The validator checks for:
- **Duplicate snippets** that may cause incorrect page marker placement
- **Placeholder entries** that need manual editing
- **HTML presence** - whether snippets actually exist in your HTML file

#### Step 3: Insert Page Markers

```bash
rx-pagemarker mark book.html snippets.json book_with_pages.html

# Inject CSS so markers are visible in a browser (useful for previewing)
rx-pagemarker mark book.html snippets.json book_with_pages.html --inject-css
```

The marker inserter walks the document in page order and tracks the last insertion position so subsequent markers must come *after* it. This handles duplicate snippet text correctly and supports multiple page breaks within a single paragraph.

---

### Magazine Workflow (Body-Only Content + Offset Hack)

Magazines typically have:
- Frontmatter (TOC, masthead) and backmatter (indexes) that are **not** in the HTML export
- Page numbers that continue across issues (e.g., issue 4 starts at print page 775)

Use `--start-page` / `--end-page` to skip frontmatter/backmatter, and `--page-offset` with the **+1 offset hack** for EPUB-correct semantics:

```bash
# Magazine: PDF page 7 = print page 775, body runs PDF pages 7-237
#
# Offset formula: first_print_page - first_pdf_page + 1 = 775 - 7 + 1 = 769
#
# The +1 matters: end_of_page extraction places a marker at the END of page N,
# but EPUB readers expect "Page N+1" to land at the BEGINNING of N+1. The +1
# offset relabels the marker so the EPUB jumps to the right spot.

rx-pagemarker extract magazine.pdf snippets.json magazine.html \
  --start-page 7 --end-page 237 --page-offset 769
```

Tested on a 272-page Greek legal magazine: **97.8% marker insertion rate** with this workflow.

For **two-column PDFs** (where two articles share a page), expect lower automated success (~50–60%) — use the visual editor (below) for the remainder. Do **not** use a `--two-column` flag if you find one in old docs; it has column-sorting bugs.

### Context Matching (Duplicate Disambiguation)

When the same snippet text appears on multiple pages (e.g., a common phrase like "του δικαστηρίου"), sequential tracking alone may pick the wrong occurrence. The extractor captures N words before/after each snippet and the marker inserter scores candidate locations with Jaccard word similarity:

```bash
# Default: 4 words of context on each side; set 0 to disable
rx-pagemarker extract magazine.pdf snippets.json magazine.html --context-words 4
```

Context appears in the JSON as `context_before` / `context_after` fields:

```json
{
  "page": 900,
  "snippet": "του δικαστηρίου",
  "context_before": "η απόφαση",
  "context_after": "είναι τελεσίδικη"
}
```

---

### Workflow 2: Manual Template Generation

If automated extraction doesn't work for your PDF, you can manually create snippets:

#### Step 1: Generate a Template

Instead of manually creating the JSON structure, use the template generator:

```bash
# For regular pages (1, 2, 3...)
rx-pagemarker generate 200 my_pages.json

# For front matter with Roman numerals (i, ii, iii...)
rx-pagemarker generate 5 frontmatter.json --roman

# Start from page 11 (if you have 10 pages of front matter)
rx-pagemarker generate 200 body_pages.json --start-page 11
```

This creates a JSON file with placeholders. Then:
1. Open the JSON file in your text editor
2. Use Find/Replace or Find Next to jump to each placeholder
3. Replace `PASTE_TEXT_FROM_END_OF_PAGE_HERE` with actual text from your PDF
4. Save the file

### Step 2: Insert Page Markers

```bash
rx-pagemarker mark <html_file> <json_file> [output_file]
```

### Example

```bash
rx-pagemarker mark book.html page_references.json book_with_pages.html
```

If no output file is specified, the tool will create `<input_filename>_with_pages.html`.

### File Paths

You can use **any file paths** - files don't need to be in the same directory:

```bash
# Relative paths
rx-pagemarker mark ../books/chapter1.html pages.json ../output/chapter1_marked.html

# Absolute paths
rx-pagemarker mark /Users/name/Documents/book.html pages.json /Users/name/output.html

# Mixed
rx-pagemarker mark ../books/book.html pages.json output.html
```

**Output file location:**
- If you specify an output path → file goes there
- If you omit output path → creates `<input>_with_pages.html` in the same directory as the input HTML

```bash
# This command:
rx-pagemarker mark ../books/mybook.html pages.json

# Creates output at:
../books/mybook_with_pages.html
```

## Page References JSON Format

The JSON file should contain an array of objects with `page` and `snippet` fields:

```json
[
  {
    "page": 1,
    "snippet": "Chapter One"
  },
  {
    "page": 2,
    "snippet": "it was a dark and stormy night"
  },
  {
    "page": 3,
    "snippet": "The next morning"
  }
]
```

### Choosing Good Snippets

- **Uniqueness**: Choose text that appears only once in the document
- **Proximity**: Select text immediately before the page break
- **Copy from PDF**: Just select and copy - the script handles HTML formatting automatically
- **Length**: Use 3-10 words for best results
- **Avoid**: Don't use snippets from headings if they appear in table of contents

## Output Format

Page markers are inserted as:

```html
<span id="page5" class="page-number" role="note" aria-label="Page 5">5</span>
```

| Attribute | Purpose |
|-----------|---------|
| `id="page5"` | Unique target for EPUB page-list links (`<a href="chapter.xhtml#page5">`) |
| `class="page-number"` | CSS styling hook |
| `role="note"` | ARIA landmark — screen readers announce as supplementary info |
| `aria-label="Page 5"` | Full description for accessibility |

When the same page number appears more than once (e.g., two-column layouts where two articles share a page), subsequent IDs are suffixed:

```html
<span id="page36" ...>36</span>      <!-- First occurrence -->
<span id="page36-2" ...>36</span>    <!-- Second occurrence -->
```

These markers:
- Can be styled with CSS via the `.page-number` class
- Are accessible to screen readers via ARIA attributes
- Can be used to generate EPUB3 page-list navigation

## Visual Marker Editor

`tools/page-marker-editor.html` is a browser-based drag-and-drop tool for correcting marker positions in marked HTML files. It is a **single HTML file** with no server, no build step, no dependencies — just open it in any modern browser.

Use it when automated extraction misplaces a marker, or when you need to add markers for two-column pages where one column extraction failed.

**Features:**
- Load any marked HTML file via file picker
- Page markers appear as red draggable badges
- Drag markers between words to reposition them
- Click **+ Add Marker** then click any word to insert a marker after it (word-boundary only; suggests the next sequential page number)
- Double-click a marker to edit its page number or delete it (leave empty + confirm to delete)
- Undo/redo (Ctrl+Z / Ctrl+Y), zoom controls, drop-position indicator
- Download as `corrected_YYYY-MM-DD_HH-MM.html`, or **Copy Body Content** (inner-body HTML only) for pasting back into per-article files
- **Auto-save to localStorage** after every change with a restore prompt next time you open the editor — work survives refresh or accidental close (7-day retention)
- Export skips corrupted markers without page numbers and notifies you

**Known limitation:** The download uses XMLSerializer which reformats the file (adds `<!DOCTYPE html>`, collapses whitespace, may reorder attributes). Content and structure are identical — safe for EPUB generation, but not byte-for-byte identical to the input.

**Help page:** `tools/help.html` is a standalone single-file reference covering quick start, all actions, keyboard shortcuts, auto-save behavior, troubleshooting (Clipboard API on `file://`, XMLSerializer reformatting, data-loss causes), and known limitations. The editor's sidebar links to it. Zero dependencies, works offline.

## PDF Splitting

`rx-pagemarker split` extracts a page range from a PDF — useful for processing individual articles from magazine PDFs. The same range logic is also available as a visual tool at `tools/pdf-splitter.html`.

**This is independent from the marking pipeline** — split exists purely as a convenience for slicing source PDFs before extraction.

```bash
# Extract PDF pages 5-19 directly
rx-pagemarker split magazine.pdf article.pdf --start-page 5 --end-page 19

# Extract print pages 81-95 when PDF page 5 = print page 81
# Note: --page-offset is SUBTRACTED here (reverse of extract's offset direction).
# So you think in print pages; the tool converts to PDF pages.
rx-pagemarker split magazine.pdf --start-page 81 --end-page 95 --page-offset 76

# Output filename auto-generated: magazine_pages_81-95.pdf
```

The browser tool (`tools/pdf-splitter.html`) shows thumbnails, supports shift-click range selection, lets you visually mark frontmatter/backmatter zones, and does client-side PDF extraction (PDF.js + pdf-lib via CDN — no server).

## Workflow Decision Tree

```
PDF Extraction
│
├─ Have clean HTML with same content? (RECOMMENDED)
│  └─> YES: Use standard extraction
│      rx-pagemarker extract book.pdf snippets.json book.html
│
├─ No HTML file available?
│  └─> Use raw PDF mode
│      rx-pagemarker extract book.pdf snippets.json --raw-pdf
│
└─ Heavily corrupted PDF (missing spaces)?
   │
   ├─ Have HTML? → Use fuzzy matching
   │  rx-pagemarker extract book.pdf snippets.json book.html --fuzzy-match --review
   │
   └─ No HTML? → Use word segmentation
      rx-pagemarker extract book.pdf snippets.json --raw-pdf --segment-words --review

Review Mode Output:
├─ High confidence (>0.7): Ready to use
├─ Low confidence (<0.7): Manual review recommended
└─ Confidence = 0: Manual entry required
```

## Tips

1. **Test with a subset**: Start with 5-10 page references to verify your snippets work
2. **Check warnings**: The tool warns about multiple matches - these may need more specific snippets
3. **Whitespace matters**: Ensure snippets match exactly, including spaces and line breaks
4. **Review output**: Always verify a few page markers were inserted correctly before processing the full book
5. **Use --review mode**: When using word segmentation or HTML matching, always use `--review` to see confidence scores
6. **Start-page filtering**: Test with a small range first: `--start-page 1 --end-page 10`

## Troubleshooting

### PDF Text Has No Spaces Between Words

**Symptoms:** Extracted snippets look like "ΗοικονομίατηςΕλλάδας" instead of "Η οικονομία της Ελλάδας"

**Cause:** PDF encoding issue, common in Quark→InDesign→PDF conversions

**Solutions:**
1. **Best:** Use standard extraction with HTML file (default behavior)
2. **Better:** Use `--fuzzy-match` flag for heavily corrupted PDFs
3. **Good:** Use `--raw-pdf --segment-words` for dictionary-based reconstruction
4. **Fallback:** Manual template generation (see Workflow 2)

### Fuzzy Matching is Slow

**Symptoms:** Extraction with `--fuzzy-match` takes several minutes for 500+ page PDFs

**Status:** Known performance issue, optimization in progress

**Workarounds:**
1. Use standard extraction (without `--fuzzy-match`) - usually sufficient
2. Process smaller page ranges: `--start-page 1 --end-page 50`
3. Use word segmentation instead: `--raw-pdf --segment-words`

### Low Confidence Scores in Review Mode

**Symptoms:** Many snippets show confidence <0.7

**For Word Segmentation:**
- Dictionary covers ~10k most common Greek words
- Some rare morphological forms may not be recognized
- Continuous improvements to algorithm and dictionary coverage

**For HTML Matching:**
- HTML content doesn't match PDF content exactly
- Check if HTML and PDF represent the same version of the document

### Duplicate Snippets Warning

**Cause:** Same text appears multiple times in document (e.g., chapter titles in TOC)

**Solutions:**
1. Choose longer, more specific snippets (8-12 words)
2. Select text that's unique to that page
3. Avoid using headings that appear in table of contents

## Future Enhancements

- **Optimize HTML fuzzy matching algorithm**: Only affects the `--fuzzy-match` flag (rarely needed); reduce time from minutes to seconds for large documents
- **Multi-language support**: Add frequency-based dictionaries for other languages (English, French, etc.)
- **Visual editor: marker list sidebar**: Click-to-jump navigation for documents with 200+ markers
- **Visual editor: out-of-order detection**: Highlight markers that violate sequential page order
- **Interactive mode**: Preview matches before insertion
- **Batch processing**: Process multiple HTML files at once
- **Smart snippet refinement**: Auto-adjust snippets that appear multiple times in the document
- **OCR support**: Extract from image-based PDFs using Tesseract
- **Neural word segmentation**: Train ML model on HTML/PDF pairs for language-agnostic segmentation

## Project Structure

- **`tests/`** - Automated test suite (pytest) for code verification
- **`examples/`** - Sample files for users to learn and test the tool
- **`tools/`** - Browser-based standalone HTML utilities
  - **`page-marker-editor.html`** - Visual drag-and-drop marker editor
  - **`pdf-splitter.html`** - Visual PDF page-range extractor
  - **`help.html`** - User-facing reference for the editor (linked from sidebar)
- **`scripts/`** - Maintenance scripts (release packaging, etc.)
- **`src/rx_pagemarker/`** - Main package source code
  - **`data/`** - Dictionary files (Greek word frequency list)

## Releasing

Distributable ZIPs of the editor (for non-technical recipients) are built by `scripts/release.sh`. Versioning mirrors the sibling project `rx-ind-epub-gen`:

- **Single source of truth**: a `vX.Y.Z` git tag.
- **Python package version** is derived dynamically via `setuptools-scm` (see `[tool.setuptools_scm]` in `pyproject.toml`). The generated `src/rx_pagemarker/_version.py` is gitignored.
- **ZIP filename** is derived from the same tag, so the wheel and the ZIP always agree.

The script enforces a clean working tree and requires HEAD to be on a `vX.Y.Z` tag — there is no untagged "snapshot" build, and it refuses to overwrite an existing ZIP for the same version (bump the tag instead).

```bash
# 1. Tag the commit you want to ship
git tag v0.1.0
git push --tags

# 2. Build the ZIP
./scripts/release.sh
# → versions/rx-pagemarker-editor-v0.1.0.zip

# 3. Send the ZIP. Recipients extract it and open page-marker-editor.html.
```

Every release is archived locally under `versions/` (gitignored). The script lists all existing versions after each build so you can see your release history at a glance.

The ZIP contains the editor, the PDF splitter, the help page, the `examples/` folder, a `VERSION` file, and a recipient-facing `README.md` (sourced from `scripts/release-readme.md` — edit that file to change what recipients see).

## Project Context

This tool is part of the RX EPUB generation pipeline, which converts InDesign HTML exports into EPUB3 files. Page markers enable:
- Accurate page-list navigation in the EPUB
- Citation compatibility with print editions
- Better reading experience in academic/reference content
