"""Template generator for page references JSON files."""

import json
from pathlib import Path
from typing import List, Union


# Roman numerals for front matter (up to 20)
ROMAN_NUMERALS = [
    "i",
    "ii",
    "iii",
    "iv",
    "v",
    "vi",
    "vii",
    "viii",
    "ix",
    "x",
    "xi",
    "xii",
    "xiii",
    "xiv",
    "xv",
    "xvi",
    "xvii",
    "xviii",
    "xix",
    "xx",
]


def generate_template(
    num_pages: int,
    output_file: Union[str, Path],
    start_page: int = 1,
    use_roman: bool = False,
) -> None:
    """Generate a template JSON file for page references.

    Args:
        num_pages: Number of page entries to generate
        output_file: Path to output JSON file
        start_page: Starting page number (default: 1)
        use_roman: Use Roman numerals (i, ii, iii, etc.)
    """
    references: List[dict] = []

    for i in range(num_pages):
        page_num = start_page + i

        # Format page number
        if use_roman:
            if page_num <= len(ROMAN_NUMERALS):
                page_str = ROMAN_NUMERALS[page_num - 1]
            else:
                print(
                    f"⚠ Warning: Roman numeral not defined for page {page_num}, using number"
                )
                page_str = str(page_num)
        else:
            page_str = str(page_num)

        references.append(
            {"page": page_str, "snippet": "PASTE_TEXT_FROM_END_OF_PAGE_HERE"}
        )

    # Write to file with nice formatting
    output_path = Path(output_file)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(references, f, indent=2, ensure_ascii=False)

    print("=" * 60)
    print("PAGE REFERENCES TEMPLATE GENERATOR")
    print("=" * 60)
    print(f"✓ Generated template with {num_pages} page entries")
    print(f"✓ Page range: {references[0]['page']} to {references[-1]['page']}")
    print(f"✓ Saved to: {output_path}")
    print("\n" + "=" * 60)
    print("NEXT STEPS")
    print("=" * 60)
    print(f"1. Open {output_path} in your text editor")
    print("2. Find/Replace all 'PASTE_TEXT_FROM_END_OF_PAGE_HERE' with actual text")
    print("   - Open your PDF alongside")
    print("   - Copy 3-10 words from the end of each page")
    print("   - Paste into the corresponding entry")
    print("3. Save the file")
    print(f"4. Run: rx-pagemarker mark your_book.html {output_path} output.html")
    print(
        "\n💡 TIP: Use your editor's 'Find Next' feature to jump between placeholders!"
    )
