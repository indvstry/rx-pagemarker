# Visual Example: How Snippets Map to Page Breaks

## The Concept

You're looking at your PDF and finding the **last few words** before each page ends. Those words become your "snippet" that marks where to insert the page number.

## Example PDF Pages

```
┌─────────────────────────────────┐
│  PDF - PAGE 1                   │
│                                 │
│  Once upon a time, in a small   │
│  village nestled between        │
│  rolling hills, there lived a   │
│  curious young girl named Emma. │
│                                 │
│  She loved exploring and        │
│  discovering new things. One    │
│  sunny afternoon, she walked    │
│  into the forest. The trees were│  ← THIS IS YOUR SNIPPET
│  tall and ancient,              │
└─────────────────────────────────┘
         ↓ PAGE BREAK
┌─────────────────────────────────┐
│  PDF - PAGE 2                   │
│                                 │
│  their branches forming a       │
│  canopy overhead.               │
│                                 │
│  As Emma ventured deeper, she   │
│  heard a strange noise behind   │  ← THIS IS YOUR SNIPPET
│  her. It sounded like footsteps,│
│  but when she turned            │
└─────────────────────────────────┘
         ↓ PAGE BREAK
┌─────────────────────────────────┐
│  PDF - PAGE 3                   │
│                                 │
│  around, there was nothing      │
│  there.                         │
│                                 │
│  "Who's there?" she called out, │  ← THIS IS YOUR SNIPPET
│  her voice echoing through the  │
│  trees.                         │
└─────────────────────────────────┘
```

## Your JSON File Would Be

```json
[
  {
    "page": 1,
    "snippet": "into the forest. The trees were"
  },
  {
    "page": 2,
    "snippet": "heard a strange noise behind"
  },
  {
    "page": 3,
    "snippet": "\"Who's there?\" she called out,"
  }
]
```

## What Happens When You Run the Script

### Input HTML
```html
<p>She loved exploring and discovering new things. One sunny
afternoon, she walked into the forest. The trees were tall and
ancient, their branches forming a canopy overhead.</p>
```

### After Processing
```html
<p>She loved exploring and discovering new things. One sunny
afternoon, she walked into the forest. The trees were<span
class="page-number" role="note" aria-label="Page 1">1</span> tall
and ancient, their branches forming a canopy overhead.</p>
```

Notice the page marker is inserted **right after** the snippet!

## How to Read Your PDF and Create Snippets

### Method 1: Manual Reading

1. **Open page 1 of PDF**
2. **Scroll to bottom of page 1**
3. **Find the last complete sentence or phrase**
   - Example: "...she walked into the forest. The trees were"
4. **Copy those last few words**
5. **Add to JSON:**
   ```json
   {
     "page": 1,
     "snippet": "into the forest. The trees were"
   }
   ```

### Method 2: Using PDF Reader

Most PDF readers show page numbers. Look at the **bottom right** of each page:

```
Page 1 of 50 → Find text at bottom of this view
Page 2 of 50 → Find text at bottom of this view
Page 3 of 50 → Find text at bottom of this view
```

## Important Notes

### ✅ DO Include:
- Punctuation marks: `"forest."`
- Quotation marks: `"\"Hello,\" she said"`
- Multiple words (3-10 typically)
- Exact spacing

### ❌ DON'T Include:
- Page numbers themselves
- Header/footer text
- Text that repeats many times
- Just one common word

## Testing Your Snippets

After creating your JSON file, test with a small sample:

```bash
python page_marker.py sample_book.html page_references.json test.html
```

You'll see output like:
```
✓ Page 1: Marker inserted
✓ Page 2: Marker inserted
⚠ Page 3: Snippet found in 2 locations, using first occurrence
✗ Page 4: Snippet not found
```

Fix the warnings and errors before processing the full document!

## Complete Example

### Your PDF Pages End With:
- Page 1: "...walked into the forest."
- Page 2: "...a strange noise behind her"
- Page 3: "...\"Who's there?\" she called out"
- Page 4: "...shadow disappeared into"
- Page 5: "...to be discovered."

### Your JSON File:
```json
[
  {"page": 1, "snippet": "walked into the forest."},
  {"page": 2, "snippet": "a strange noise behind her"},
  {"page": 3, "snippet": "\"Who's there?\" she called out"},
  {"page": 4, "snippet": "shadow disappeared into"},
  {"page": 5, "snippet": "to be discovered."}
]
```

That's it! The script finds each snippet in your HTML and inserts the page number marker right after it.
