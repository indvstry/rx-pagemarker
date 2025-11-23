# RX Page Marker

A Python tool to insert page number markers into HTML files for EPUB3 generation. Uses text snippets from a mapping file to accurately place page breaks that match the original PDF pagination.

## Features

- **🚀 Automated PDF extraction**: Automatically extract text snippets from PDF files (supports Greek and Unicode text)
- **⚡ High performance**: Process 500+ page PDFs in seconds using PyMuPDF
- **🎯 Smart extraction strategies**: Choose between end-of-page text or visual positioning
- **🔧 Word boundary reconstruction**: Handles PDFs with missing spaces using dictionary-based segmentation
- **🎯 HTML-based correction**: Match PDF snippets against clean HTML for perfect word boundaries
- **📊 Confidence scoring**: Review mode shows quality scores for automatically extracted snippets
- **✅ Built-in validation**: Check for duplicates and verify snippets exist in HTML
- **✨ Intelligent snippet matching**: Finds text even when split across formatting tags (`<i>`, `<b>`, `<span>`)
- **DOM-aware insertion**: Uses BeautifulSoup to parse HTML structure, preventing markers from being inserted into attributes or tags
- **InDesign-friendly**: Handles complex HTML exports with heavy inline formatting
- **Accessibility support**: Generates page markers with proper ARIA attributes
- **Detailed reporting**: Shows statistics on successful insertions, missing snippets, and multiple matches
- **Fallback-ready**: Manual mapping file ensures accuracy when automation isn't feasible

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

The fastest way to get started is to automatically extract snippets directly from your PDF:

#### Step 1: Extract Snippets from PDF

```bash
# Basic extraction - uses best available backend (PyMuPDF > pdfplumber)
rx-pagemarker extract book.pdf snippets.json

# Extract with custom settings
rx-pagemarker extract book.pdf snippets.json --words 8 --strategy bottom_visual

# Extract specific page range (useful for testing)
rx-pagemarker extract book.pdf snippets.json --start-page 1 --end-page 50

# Use pdfplumber for complex layouts with tables/columns
rx-pagemarker extract book.pdf snippets.json --backend pdfplumber
```

**Extraction Strategies:**
- `end_of_page` (default) - Extracts last N words from text (faster, simpler)
- `bottom_visual` - Extracts text from visually lowest position on page (better for complex layouts)

**Backends:**
- `auto` (default) - Automatically uses PyMuPDF if available, falls back to pdfplumber
- `pymupdf` - Fast C-based extraction, excellent for large files (500+ pages)
- `pdfplumber` - Better layout analysis, handles tables and columns well

**Note:** Supports Greek and all Unicode text natively.

#### Advanced: Handling PDFs with Spacing Issues

Some PDFs (especially from Quark→InDesign→PDF conversions) have broken text encoding where spaces between words are missing. The tool provides two strategies to handle this:

**Option 1: Word Segmentation** (Dictionary-based)

```bash
# Enable word boundary reconstruction using Greek dictionary
rx-pagemarker extract book.pdf snippets.json --segment-words --review

# Use with different language (currently supports: el=Greek)
rx-pagemarker extract book.pdf snippets.json --segment-words --language el --review
```

This uses a dictionary-based algorithm to reconstruct word boundaries. The `--review` flag shows confidence scores so you can identify snippets that may need manual correction.

**Option 2: HTML Matching** (Recommended for best results)

```bash
# Match against your clean HTML to get perfect word boundaries
rx-pagemarker extract book.pdf snippets.json --match-html book.html --review
```

This matches the PDF text (without spaces) against your HTML file (with correct spacing) to reconstruct accurate word boundaries. Best results when the HTML contains the same content as the PDF.

**Performance Note:** HTML matching is more accurate but slower for large documents (664+ pages). The algorithm is currently being optimized.

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
<span class="page-number" role="note" aria-label="Page 5">5</span>
```

These markers:
- Can be styled with CSS via the `.page-number` class
- Are accessible to screen readers via ARIA attributes
- Can be used to generate EPUB3 page-list navigation

## Workflow Decision Tree

```
PDF Extraction
│
├─ Normal PDF (text has spaces)
│  └─> Use basic extraction
│      rx-pagemarker extract book.pdf snippets.json
│
└─ Broken PDF (missing spaces between words)
   │
   ├─ Have clean HTML with same content?
   │  └─> YES: Use HTML matching (best accuracy)
   │     rx-pagemarker extract book.pdf snippets.json --match-html book.html --review
   │
   └─ NO: Use word segmentation (partial reconstruction)
      rx-pagemarker extract book.pdf snippets.json --segment-words --review

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
1. **Best:** Use `--match-html` flag if you have clean HTML with the same content
2. **Good:** Use `--segment-words` flag for dictionary-based reconstruction
3. **Fallback:** Manual template generation (see Workflow 2)

### HTML Matching is Slow

**Symptoms:** Extraction with `--match-html` takes several minutes for 500+ page PDFs

**Status:** Known performance issue, optimization in progress

**Workarounds:**
1. Process smaller page ranges: `--start-page 1 --end-page 50`
2. Use word segmentation instead: `--segment-words`
3. Consider manual workflow for time-sensitive projects

### Low Confidence Scores in Review Mode

**Symptoms:** Many snippets show confidence <0.7

**For Word Segmentation:**
- Limited dictionary coverage (currently ~50 Greek words)
- Solution: Being expanded in future updates

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

- **Optimize HTML matching algorithm**: Reduce time from minutes to seconds for large documents
- **Expand Greek dictionary**: Add 5k-10k common words for better segmentation accuracy
- **Multi-language support**: Add dictionaries for other languages
- **Context matching**: Use surrounding text to disambiguate duplicate snippets
- **Interactive mode**: Preview matches before insertion
- **Batch processing**: Process multiple HTML files at once
- **Smart snippet refinement**: Auto-adjust snippets that appear multiple times in the document
- **OCR support**: Extract from image-based PDFs using Tesseract
- **Neural word segmentation**: Train ML model on HTML/PDF pairs for language-agnostic segmentation

## Project Context

This tool is part of the RX EPUB generation pipeline, which converts InDesign HTML exports into EPUB3 files. Page markers enable:
- Accurate page-list navigation in the EPUB
- Citation compatibility with print editions
- Better reading experience in academic/reference content
