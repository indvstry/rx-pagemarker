# RX Page Marker

A Python tool to insert page number markers into HTML files for EPUB3 generation. Uses text snippets from a mapping file to accurately place page breaks that match the original PDF pagination.

## Features

- **✨ Intelligent snippet matching**: Finds text even when split across formatting tags (`<i>`, `<b>`, `<span>`) - just copy from your PDF!
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

# Install in editable mode with development dependencies
pip install -e ".[dev]"
```

This installs:
- The `rx-pagemarker` command-line tool
- All required dependencies (beautifulsoup4, lxml, click)
- Development tools (pytest, black, mypy, flake8)

### User Installation

```bash
pip install rx-pagemarker
```

Or install directly from the repository:

```bash
pip install git+https://github.com/yourusername/rx-pagemarker.git
```

## Usage

### Step 1: Generate a Template (Optional but Recommended)

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

## Tips

1. **Test with a subset**: Start with 5-10 page references to verify your snippets work
2. **Check warnings**: The tool warns about multiple matches - these may need more specific snippets
3. **Whitespace matters**: Ensure snippets match exactly, including spaces and line breaks
4. **Review output**: Always verify a few page markers were inserted correctly before processing the full book

## Future Enhancements

- **Automated PDF extraction**: Parse PDF directly to auto-generate snippets
- **Context matching**: Use surrounding text to disambiguate duplicate snippets
- **Interactive mode**: Preview matches before insertion
- **Batch processing**: Process multiple HTML files at once

## Project Context

This tool is part of the RX EPUB generation pipeline, which converts InDesign HTML exports into EPUB3 files. Page markers enable:
- Accurate page-list navigation in the EPUB
- Citation compatibility with print editions
- Better reading experience in academic/reference content
