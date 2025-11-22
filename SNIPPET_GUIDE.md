# How to Create Your Page References File

## ✅ Good News: You Can Copy Directly from the PDF!

The enhanced page marker script can now find snippets **even when they span across formatting tags** like `<i>`, `<b>`, `<span>`, etc.

**This means you can:**
- ✅ Copy text directly from your PDF
- ✅ Copy from your browser's rendered view
- ✅ Not worry about HTML formatting tags

**The script handles:**
- Text split across `<i>`, `<b>`, `<em>`, `<strong>` tags
- Words wrapped in multiple `<span>` elements
- Complex InDesign export formatting

## Overview

The `page_references.json` file maps page numbers to text snippets. Each snippet should be the **last few words before the page break** in your PDF.

## JSON Structure

```json
[
  {
    "page": 1,
    "snippet": "text that appears right before page 1 ends"
  },
  {
    "page": 2,
    "snippet": "text that appears right before page 2 ends"
  }
]
```

## Step-by-Step Process

### 1. Open Your PDF

Open the PDF you want to match against.

### 2. Find the Page Break

For each page, scroll to the **bottom** of the page and identify the last complete phrase or sentence before the page break.

### 3. Copy the Text

Select and copy 3-10 words from the end of the page. That's it!

### 4. Add to JSON

Add an entry with the page number and the snippet you copied.

## Advanced: When to Check HTML Source

While the script can handle most formatting, you might still want to check the HTML source if:
- A snippet isn't found (may have unusual whitespace)
- You want to verify the exact text structure
- The snippet appears in multiple locations

To check HTML source:
1. Open HTML in a text editor
2. Search (`Ctrl+F` / `Cmd+F`) for your snippet
3. Verify it exists and note any whitespace differences

## Examples

### ✅ Good Snippets

```json
{
  "page": 5,
  "snippet": "walked into the forest."
}
```
**Why good**: Complete phrase, unique, exact match with punctuation

```json
{
  "page": 12,
  "snippet": "According to Dr. Martinez,"
}
```
**Why good**: Proper name makes it unique, includes comma

```json
{
  "page": 23,
  "snippet": "the quarterly revenue figures"
}
```
**Why good**: Specific enough to be unique

### ❌ Bad Snippets

```json
{
  "page": 5,
  "snippet": "the"
}
```
**Why bad**: Too short, will match hundreds of times

```json
{
  "page": 12,
  "snippet": "Chapter 3"
}
```
**Why bad**: Might appear in headers, footers, or table of contents

```json
{
  "page": 23,
  "snippet": "revenue"
}
```
**Why bad**: Single common word, not unique enough

## Real-World Example Workflow

### Step 1: Look at PDF Page 1
```
... and so the journey began. Emma packed her bag and
set out at dawn.
[PAGE BREAK]
```

### Step 2: Choose snippet
The last complete phrase is: `"set out at dawn."`

### Step 3: Add to JSON
```json
{
  "page": 1,
  "snippet": "set out at dawn."
}
```

### Step 4: Repeat for all pages

## Tips for Success

### 1. **Match Exactly**
- Include punctuation: `"hello."` ≠ `"hello"`
- Match spacing: `"hello world"` ≠ `"hello  world"` (note double space)
- Preserve line breaks if they exist in the text

### 2. **Use Context When Needed**
If a phrase repeats, add more context:
```json
{
  "page": 15,
  "snippet": "as mentioned in Chapter 2, the results"
}
```

### 3. **Avoid Headers/Footers**
Don't use text from:
- Page numbers
- Running headers
- Chapter titles that repeat
- Footers

### 4. **Test as You Go**
After creating 5-10 entries, run the tool to verify they work:
```bash
rx-pagemarker mark sample.html page_references.json test_output.html
```

### 5. **Check the Output**
The script will warn you:
```
✗ Page 15: Snippet not found
⚠ Warning: Snippet found in 3 locations, using first occurrence
```

Fix these before continuing.

## Common Issues

### Issue: "Snippet not found"

**Causes:**
- Typo in snippet
- HTML has different whitespace than PDF
- Text was modified during HTML export

**Solutions:**
- Copy-paste directly from HTML if possible
- Check for extra spaces or line breaks
- Use a slightly different portion of text

### Issue: "Multiple matches"

**Causes:**
- Snippet is too generic
- Text repeats in document

**Solutions:**
- Add more context words
- Use a more unique phrase
- Include proper names or numbers

## Advanced: Semi-Automated Extraction

You can use tools to help extract snippets:

### From PDF (using pdftotext)
```bash
pdftotext -layout book.pdf book.txt
```
Then manually identify page break positions in the text file.

### From HTML
Search for unique text near where you expect page breaks, then verify against PDF.

## File Organization

Recommended structure:
```
project/
├── book.html                    # Your HTML file
├── book.pdf                     # Reference PDF
├── page_references.json         # Your mapping file
├── page_marker.py              # The script
└── output/
    └── book_with_pages.html    # Generated output
```

## Quick Reference Template

```json
[
  {
    "page": 1,
    "snippet": "PASTE_LAST_WORDS_OF_PAGE_1_HERE"
  },
  {
    "page": 2,
    "snippet": "PASTE_LAST_WORDS_OF_PAGE_2_HERE"
  },
  {
    "page": 3,
    "snippet": "PASTE_LAST_WORDS_OF_PAGE_3_HERE"
  }
]
```

Start with this template and replace the placeholders with actual text from your PDF.
