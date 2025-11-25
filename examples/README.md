# Examples

This directory contains example files for testing and demonstrating the `rx-pagemarker` tool.

## Files

### sample_book.html
A simple HTML file with sample content for testing page marker insertion.

**Usage:**
```bash
rx-pagemarker mark examples/sample_book.html examples/page_references_example.json output.html
```

### page_references_example.json
Example page reference mapping file showing the correct JSON format.

**Structure:**
```json
[
  {
    "page": 1,
    "snippet": "text from end of page 1"
  },
  {
    "page": 2,
    "snippet": "text from end of page 2"
  }
]
```

### page_references.json
Another example with different snippets for testing variations.

## Quick Test

To quickly test the tool with these examples:

```bash
# Generate a template
rx-pagemarker generate 5 my_test.json

# Or use the provided examples
rx-pagemarker mark examples/sample_book.html examples/page_references_example.json test_output.html
```

## Creating Your Own Examples

1. Start with your HTML file from InDesign export
2. Generate a template:
   ```bash
   rx-pagemarker generate <num_pages> my_pages.json
   ```
3. Fill in snippets from your PDF
4. Test with a small subset first

See the main [README.md](../README.md) for complete documentation.
