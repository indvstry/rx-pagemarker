# Quick Start Guide

## What You Have

Your project now contains:

### Core Package
- **`src/rx_pagemarker/`** - Python package with type hints
  - `marker.py` - Page marker insertion logic
  - `template.py` - Template generation
  - `cli.py` - Click-based command-line interface

### Configuration
- **`pyproject.toml`** - Modern packaging configuration
- **`setup.sh`** - One-click installation script

### Example Files
- **`sample_book.html`** - Example HTML file
- **`page_references_example.json`** - Example mapping file

### Documentation
- **`README.md`** - Complete documentation
- **`SNIPPET_GUIDE.md`** - How to create your mapping file
- **`VISUAL_EXAMPLE.md`** - Visual guide showing the concept

### Tests
- **`tests/`** - Comprehensive pytest test suite

## Getting Started

### Step 1: Install (One Time Only)

```bash
# With PDF extraction support (recommended)
pip install -e ".[pdf,dev]"

# Or without PDF extraction (manual workflow only)
pip install -e ".[dev]"
```

This installs the `rx-pagemarker` command and all dependencies.

### Step 2: Choose Your Workflow

#### Option A: Automated PDF Extraction (Recommended & Fastest)

Extract snippets automatically from your PDF:

```bash
# Basic extraction
rx-pagemarker extract book.pdf snippets.json

# For PDFs with missing spaces (Quark→InDesign→PDF conversions)
rx-pagemarker extract book.pdf snippets.json --match-html book.html --review

# Validate the extracted snippets
rx-pagemarker validate snippets.json --html book.html
```

Then skip to Step 3.

#### Option B: Manual Template Generation

If automated extraction doesn't work, generate a template:

```bash
rx-pagemarker generate 50 my_book.json
```

This creates a JSON file with 50 placeholder entries. Then:

1. Open `my_book.json` in your text editor
2. Open your PDF alongside
3. For each page:
   - Find the last few words at the bottom of the page
   - Copy them from the PDF
   - In your editor, use "Find Next" to jump to the next placeholder
   - Paste the text
4. Save the file

**Alternative:** Create the JSON manually (see `SNIPPET_GUIDE.md`)

#### Option B (continued): For Books with Front Matter

If your book has Roman numeral pages (i, ii, iii...) for front matter:

```bash
# Generate front matter template (pages i-v)
rx-pagemarker generate 5 frontmatter.json --roman

# Generate body template (pages 1-200, starting from page 1)
rx-pagemarker generate 200 body.json --start-page 1

# Manually combine both files into one JSON array
```

### Step 3: Insert Page Markers

```bash
rx-pagemarker mark your_book.html page_references.json output.html
```

## Example Run

```bash
rx-pagemarker mark sample_book.html page_references_example.json test_output.html
```

You'll see output like:
```
Page Marker Insertion Tool
==================================================
✓ Loaded HTML from sample_book.html
✓ Loaded 5 page references from page_references_example.json

Inserting page markers...
  ✓ Page 1: Marker inserted
  ✓ Page 2: Marker inserted
  ✓ Page 3: Marker inserted
  ✓ Page 4: Marker inserted
  ✓ Page 5: Marker inserted

✓ Saved output to test_output.html

==================================================
SUMMARY
==================================================
Total references:    5
Successfully found:  5
Not found:           0
Multiple matches:    0
```

## What Gets Inserted

The script inserts page markers like this:

```html
<span class="page-number" role="note" aria-label="Page 5">5</span>
```

These are:
- Accessible to screen readers
- Styleable with CSS
- Used for EPUB3 page-list navigation

## Troubleshooting

### "Snippet not found"
- Check for typos in your snippet
- Ensure exact match (including punctuation and spacing)
- Try copy-pasting from the HTML file

### "Multiple matches"
- Your snippet appears more than once
- Make it more specific by adding more words
- Include unique elements (names, numbers, etc.)

### "Module not found" or "Command not found: rx-pagemarker"
- Run `pip install -e ".[dev]"` first
- Make sure the installation completed successfully

## Next Steps

1. **Test with sample files** first to understand the workflow
2. **Create 5-10 page references** for your real book
3. **Run and verify** those work correctly
4. **Complete the rest** of your page references
5. **Review the output** HTML to ensure markers are placed correctly

## Tips

- Start small (5-10 pages) to verify your approach works
- Choose unique snippets that won't repeat in the document
- Include punctuation in your snippets for accuracy
- Review warnings/errors and fix before continuing

## File Checklist

Before running, make sure you have:
- [ ] Installed the package (`pip install -e ".[dev]"`)
- [ ] Your HTML file (from InDesign export)
- [ ] Your PDF file (to reference page breaks)
- [ ] `page_references.json` with at least a few entries

## Need Help?

- Read `SNIPPET_GUIDE.md` for creating good snippets
- Read `VISUAL_EXAMPLE.md` for a visual explanation
- Read `README.md` for complete documentation
