<!--
  This file is bundled into every release ZIP as README.md.
  It is the FIRST thing recipients see when they extract the ZIP.

  Audience: Greek legal-magazine editors and proofreaders who received
  this ZIP by email/transfer. They are NOT developers. They will not
  run pip, npm, or anything in a terminal.

  Keep this file short. One screen. No jargon.

  TODOs below are for you (Aris) to fill in — your knowledge of the
  recipients' workflow and language preference beats mine.
-->

# RX Page Marker — Editor

<!-- TODO(1): One sentence on what this tool is, in the recipients' language.
     Decide: Greek or English? The recipients are XRDD/XRID editors.
     Example (English): "A browser-based tool for placing page-number markers in HTML files exported from InDesign."
     Example (Greek):   "Εργαλείο για την τοποθέτηση σημαδιών σελίδας σε αρχεία HTML από το InDesign." -->

## How to use it

<!-- TODO(2): 3-5 numbered steps. The minimum to make them productive.
     Suggested skeleton:
       1. Double-click `page-marker-editor.html` — it opens in your browser. No installation needed.
       2. Drag your HTML file (the one exported from InDesign) onto the page.
       3. ...
       4. ...
       5. Click "Download" to save the marked HTML.
     Decide: do they need to know about snippets.json, or only about the visual editing? -->

## What's in this folder

- `page-marker-editor.html` — the main tool. Open this in a browser.
- `pdf-splitter.html` — helper tool for splitting magazine PDFs into page ranges. Open in a browser.
- `help.html` — built-in help and keyboard shortcuts.
- `examples/` — sample HTML files to practice with before opening real work.
- `VERSION` — the version of this release (also in the folder name).

## Examples

<!-- TODO(3): Tell them which example to open first and why.
     e.g. "Open examples/sample_with_markers.html in the editor to see what finished output looks like." -->

## Tips

<!-- TODO(4): 2-3 pitfalls you've seen recipients hit. Optional but valuable.
     e.g. "Do not place markers inside article summaries" (you already warn about this in the editor).
     e.g. "Two-column magazine pages need a marker for each column." -->

## Support

<!-- TODO(5): How do recipients reach you when something breaks?
     Email? A specific Slack? "Reply to whoever sent you this ZIP"? -->
