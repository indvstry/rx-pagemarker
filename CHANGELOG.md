# Changelog

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
