# RX Page Marker - Project Context

## Project Purpose
A Python tool that inserts page number markers into HTML files for EPUB3 generation. Part of the RX EPUB generation pipeline, converting InDesign HTML exports into EPUB3 files with accurate page-list navigation.

## Page Marker HTML Format
The tool inserts standardized page markers:
```html
<span class="page-number" role="note" aria-label="Page 5">5</span>
```
These markers enable EPUB page-list navigation, citation compatibility with print editions, and accessibility.

## Project Evolution

### Phase 1: Basic HTML Marking (Early version)
- Manual JSON creation with text snippets
- Simple text matching in HTML
- Required snippets within single text nodes

### Phase 2: Intelligent Snippet Matching (CHANGELOG: 2025-01-22)
- **DOM-aware insertion**: Snippets now match across formatting tags (`<i>`, `<b>`, `<span>`)
- **Template generator**: Automated JSON file creation with placeholders
- Users can copy directly from PDFs without worrying about HTML structure
- 100% success rate on test cases with complex formatting

### Phase 3: Professional Package Structure (commit: 542bf5e)
- Migrated to `src/` layout with type hints throughout
- Click-based CLI (`rx-pagemarker` command)
- Comprehensive pytest test suite (22 tests)
- Modern `pyproject.toml` packaging
- Development tools: black, mypy, flake8

### Phase 4: Advanced PDF Extraction (commit: 9c8eefb)
- **Automated PDF extraction**: PyMuPDF & pdfplumber backends
- **Word segmentation**: Handles PDFs with missing spaces (dictionary-based)
- **HTML matching**: Matches PDF snippets against clean HTML for perfect word boundaries
- **Confidence scoring**: Review mode identifies low-quality extractions
- Greek language support with extensible framework
- Two extraction strategies: `end_of_page` (fast) and `bottom_visual` (layout-aware)

### Phase 5: Production PDF Support (commit: f13700d)
- **InDesign metadata filtering**: Auto-excludes sluglines (`file.indd 123`) and timestamps
- **Dehyphenation**: Rejoins words split across lines for better HTML matching
- **Text normalization**: Handles spacing around punctuation and slashes
- **Improved validation**: Strips HTML tags before comparing, normalizes whitespace
- **CLI options**: `--exclude-pattern` for custom patterns, `--no-default-excludes`
- Tested on 272-page two-column legal magazine: 78.6% content match rate

### Phase 6: Magazine Support & Smart Correction
- **Page offset**: `--page-offset N` for magazines with continuing page numbers
- **Footnote filtering**: Skipped by default (`--include-footnotes` to include)
- **Partial word completion**: Completes cut-off words using HTML
  - "σύγ" at end of snippet becomes "σύγχυση" if found in HTML
  - Page marker placed AFTER the complete word
- **Context-based correction**: Fixes merged words in middle of snippets
  - Finds anchor sequences of 2-3 correctly-extracted words in HTML
  - Extracts correct surrounding context to replace corrupted snippet
  - Improved match rate from 71.8% to 98.9% on test magazine
- **CSS injection**: `--inject-css` flag on `mark` command for visible page markers in browser
- Unicode-aware word boundary detection for Greek and other scripts

### Phase 7: CLI Simplification (2025-01-13)
- **HTML now default**: HTML file is a required positional argument (enables word completion by default)
- **New CLI syntax**: `rx-pagemarker extract book.pdf snippets.json book.html`
- **`--raw-pdf` flag**: Opt-out of HTML correction for faster but less accurate extraction
- **`--fuzzy-match` flag**: Replaces `--match-html` for slow fuzzy matching on corrupted PDFs
- **Better error messages**: Clear guidance when HTML file is missing

### Phase 8: Sequential Position Tracking (2025-01-14)
- **Problem**: Markers placed out-of-order when snippet text appears multiple times in document
  - Example: Page 900's snippet "του δικαστηρίου" also exists on page 200
  - Old approach: First occurrence wins → wrong placement
- **Solution**: Track insertion position sequentially
  - Process pages in ascending order
  - Track both container index AND position within container
  - Each new marker must come AFTER previous marker's position
  - Handles multiple page breaks within same paragraph
- **Frontmatter/backmatter filtering**: Use `--start-page` and `--end-page` to exclude non-body content
  - Critical for magazines where PDF frontmatter (TOC, etc.) isn't in HTML export
- **Results on test magazine (XRDD 4/2025)**:
  - Before: 47 markers (18% - 204 out-of-order removed)
  - After filtering + position tracking: **228/232 markers (98.3%)**
- **Remaining issues**: 4 pages with PDF extraction problems (791, 825, 862, 897)

## Current Status (as of 2025-01-14)

### Production Ready
- ✅ Full CLI tool with professional packaging
- ✅ Automated PDF extraction with multiple backends
- ✅ Advanced text reconstruction for broken PDFs
- ✅ Expanded Greek dictionary (~10k most frequent words from Hermit Dave's lists)
- ✅ Comprehensive validation and reporting
- ✅ Strong test coverage (58 tests)
- ✅ **Production metadata filtering** - Auto-removes InDesign sluglines and timestamps
- ✅ **Magazine PDF support** - Tested with 272-page legal magazine (98.3% marker insertion rate)
- ✅ **Dehyphenation** - Rejoins words split across lines
- ✅ **Improved validation** - Strips HTML tags before comparing snippets
- ✅ **Page offset support** - For magazines with continuing page numbers (`--page-offset`)
- ✅ **Footnote filtering** - Skip small font text with `--skip-footnotes`
- ✅ **Partial word completion** - Completes cut-off words using HTML (`--complete-words`)
- ✅ **Context-based correction** - Fixes merged words using anchor sequences from HTML
- ✅ **CSS injection** - `--inject-css` for visible page markers in browser
- ✅ **Sequential position tracking** - Handles duplicate snippets and multiple page breaks per paragraph

### Known Issues
- **HTML matching performance**: Slow for 500+ page PDFs (several minutes)
- **Morphological coverage**: Some rare Greek word forms not in top-10k frequency list
- **PDF extraction edge cases**: ~1.7% of pages may have extraction issues requiring manual snippets

## Architecture

### Core Modules (`src/rx_pagemarker/`)
- `cli.py` - Click-based command-line interface
- `marker.py` - Page marker insertion logic (DOM-aware snippet matching)
- `template.py` - JSON template generation
- `pdf_extractor.py` - PDF text extraction with multiple backends
- `word_segmentation.py` - Dictionary-based word boundary reconstruction
- `html_matcher.py` - HTML-based word boundary correction

### Workflows

#### Workflow 1: Automated (Recommended)
```bash
# Extract snippets from PDF with HTML correction (default, recommended)
# HTML file is required for word completion and context correction
rx-pagemarker extract book.pdf snippets.json book.html

# For magazines with page offset (PDF page 7 = print page 775)
rx-pagemarker extract magazine.pdf snippets.json mag.html --start-page 7 --page-offset 768

# Raw PDF extraction without HTML (faster but less accurate)
rx-pagemarker extract book.pdf snippets.json --raw-pdf

# For heavily corrupted PDFs, use fuzzy matching (slow)
rx-pagemarker extract book.pdf snippets.json book.html --fuzzy-match

# Validate snippets
rx-pagemarker validate snippets.json --html book.html

# Insert markers (invisible markers by default for EPUB)
rx-pagemarker mark book.html snippets.json output.html

# Or with visible markers for previewing in browser
rx-pagemarker mark book.html snippets.json output.html --inject-css
```

#### Workflow 2: Manual
```bash
# Generate template
rx-pagemarker generate 200 pages.json

# Manually fill in snippets
# (edit pages.json)

# Insert markers
rx-pagemarker mark book.html pages.json output.html
```

## Roadmap & Next Steps

### High Priority
1. **Optimize HTML matching algorithm** - Reduce 500+ page processing from minutes to seconds

### Medium Priority
2. **Multi-language support** - Add frequency dictionaries for other languages (English, French, etc.)
3. **Enhanced morphological coverage** - Add morphological rules or expanded word forms for Greek
4. **Context matching** - Disambiguate duplicate snippets using surrounding text
5. **Smart snippet refinement** - Auto-adjust snippets that appear multiple times

### Future Enhancements
6. **Interactive preview mode** - Preview matches before insertion
7. **Batch processing** - Process multiple HTML files at once
8. **OCR support** - Handle image-based PDFs with Tesseract
9. **Neural word segmentation** - ML model for language-agnostic segmentation

## Technical Decisions

### Why PyMuPDF over pdfplumber?
- **Performance**: 10x faster for large files (500+ pages)
- **Memory**: Lower memory footprint
- **Use pdfplumber when**: Complex layouts with tables/columns

### Why dictionary-based segmentation?
- **Zero dependencies**: No external services or large ML models
- **Fast**: Real-time processing even for large PDFs
- **Extensible**: Easy to add new languages by adding word lists

### Why HTML matching for broken PDFs?
- **Accuracy**: Perfect word boundaries when HTML source is available
- **Trade-off**: Slower than segmentation but higher quality
- **Use case**: Best for InDesign exports where you have both PDF and clean HTML

## Project Structure

### Directory Organization

**`tests/`** - Automated Test Suite
- Python unit and integration tests (`test_*.py`)
- Run with `pytest`
- Verifies code correctness
- Part of CI/CD pipeline

**`examples/`** - User Examples and Samples
- Sample HTML/JSON files for documentation
- Demonstrates tool usage for end users
- Manual testing and quick starts
- Referenced in README and guides

**`src/rx_pagemarker/`** - Source Code
- Main package code
- `data/` subdirectory contains dictionary files

**Root test artifacts** (`.gitignored`)
- `test_*.json`, `test_*.html` - Temporary test outputs
- `chapter*.json` - Test data from real PDFs
- Not tracked in git

## Development Commands

```bash
# Install with all features
pip install -e ".[pdf,dev]"

# Run automated tests
pytest

# Try tool with examples
rx-pagemarker mark examples/sample_book.html examples/page_references_example.json output.html

# Format code
black src/ tests/

# Type check
mypy src/

# Lint
flake8 src/ tests/
```

## Related Projects
- **rx-ind-epub-gen**: EPUB3 generator from InDesign HTML exports
- Uses same quality standards and conventions

## Session Notes (2025-01-14) - XRDD 4/2025 Magazine

### Test Files
- **PDF**: `sample-files/XRDD 4:2025 FINAL.pdf` (272 pages total)
- **HTML**: `sample-files/XRDDD4 2025ENOMENO-fixed-class.html`
- **Output**: `sample-files/XRDDD4 2025ENOMENO-fixed-class_with_pages.html`
- **Snippets**: `sample-files/XRDD4_2025_snippets.json` (232 entries for body pages)

### PDF Structure
- Pages 1-6: Frontmatter (excluded)
- Pages 7-238: Body content (232 pages) → Magazine pages 775-1006
- Pages 239-272: Backmatter (excluded)
- Page offset: 768 (PDF page 7 = magazine page 775)

### Extraction Command Used
```bash
rx-pagemarker extract "sample-files/XRDD 4:2025 FINAL.pdf" /tmp/snippets_body.json \
  "sample-files/XRDDD4 2025ENOMENO-fixed-class.html" \
  --start-page 7 --end-page 238 --page-offset 768
```

### Results
- 228/232 markers inserted (98.3%)
- 4 pages with extraction issues: **791, 825, 862, 897**

### Next Steps
1. Investigate the 4 failing pages - likely PDF text extraction issues
2. May need manual snippet entry for those pages
3. Consider committing the sequential tracking improvements