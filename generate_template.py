#!/usr/bin/env python3
"""
Generate a page references template JSON file.

This script creates a JSON template with placeholder text,
making it easy to fill in snippets without worrying about JSON syntax.
"""

import json
import sys


def generate_template(num_pages, output_file, start_page=1, use_roman=False):
    """
    Generate a template JSON file for page references.

    Args:
        num_pages: Number of page entries to generate
        output_file: Path to output JSON file
        start_page: Starting page number (default: 1)
        use_roman: Use Roman numerals (i, ii, iii, etc.)
    """

    references = []

    # Roman numerals for front matter
    roman_numerals = ['i', 'ii', 'iii', 'iv', 'v', 'vi', 'vii', 'viii', 'ix', 'x',
                      'xi', 'xii', 'xiii', 'xiv', 'xv', 'xvi', 'xvii', 'xviii', 'xix', 'xx']

    for i in range(num_pages):
        page_num = start_page + i

        # Format page number
        if use_roman:
            if page_num <= len(roman_numerals):
                page_str = roman_numerals[page_num - 1]
            else:
                print(f"⚠ Warning: Roman numeral not defined for page {page_num}, using number")
                page_str = str(page_num)
        else:
            page_str = str(page_num)

        references.append({
            "page": page_str,
            "snippet": "PASTE_TEXT_FROM_END_OF_PAGE_HERE"
        })

    # Write to file with nice formatting
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(references, f, indent=2, ensure_ascii=False)

    print("="*60)
    print("PAGE REFERENCES TEMPLATE GENERATOR")
    print("="*60)
    print(f"✓ Generated template with {num_pages} page entries")
    print(f"✓ Page range: {references[0]['page']} to {references[-1]['page']}")
    print(f"✓ Saved to: {output_file}")
    print("\n" + "="*60)
    print("NEXT STEPS")
    print("="*60)
    print(f"1. Open {output_file} in your text editor")
    print(f"2. Find/Replace all 'PASTE_TEXT_FROM_END_OF_PAGE_HERE' with actual text")
    print(f"   - Open your PDF alongside")
    print(f"   - Copy 3-10 words from the end of each page")
    print(f"   - Paste into the corresponding entry")
    print(f"3. Save the file")
    print(f"4. Run: python page_marker.py your_book.html {output_file} output.html")
    print("\n💡 TIP: Use your editor's 'Find Next' feature to jump between placeholders!")


def main():
    """Command-line interface."""
    if len(sys.argv) < 3:
        print("Generate a JSON template for page references")
        print("\nUsage:")
        print("  python generate_template.py <num_pages> <output_file> [start_page] [--roman]")
        print("\nArguments:")
        print("  num_pages    : Number of page entries to generate")
        print("  output_file  : Name of the JSON file to create")
        print("  start_page   : Starting page number (default: 1)")
        print("  --roman      : Use Roman numerals (i, ii, iii, etc.)")
        print("\nExamples:")
        print("  python generate_template.py 50 pages.json")
        print("  python generate_template.py 10 frontmatter.json 1 --roman")
        print("  python generate_template.py 200 book_pages.json 11")
        print("\nFor front matter + body:")
        print("  python generate_template.py 5 frontmatter.json 1 --roman")
        print("  python generate_template.py 200 body.json 1")
        print("  Then manually combine the two files")
        sys.exit(1)

    try:
        num_pages = int(sys.argv[1])
        if num_pages <= 0:
            print("✗ Error: Number of pages must be positive")
            sys.exit(1)
    except ValueError:
        print("✗ Error: First argument must be a number")
        sys.exit(1)

    output_file = sys.argv[2]

    # Parse optional arguments
    start_page = 1
    use_roman = False

    for arg in sys.argv[3:]:
        if arg == '--roman':
            use_roman = True
        else:
            try:
                start_page = int(arg)
            except ValueError:
                print(f"⚠ Warning: Ignoring unrecognized argument: {arg}")

    generate_template(num_pages, output_file, start_page, use_roman)


if __name__ == '__main__':
    main()
