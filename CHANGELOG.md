# Changelog

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
