"""Page marker insertion for HTML files."""

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from bs4 import BeautifulSoup, NavigableString, Tag


class PageMarkerInserter:
    """Handles insertion of page markers into HTML content.

    This class provides DOM-aware insertion of page number markers into HTML files,
    with support for snippets that span across formatting tags like <i>, <b>, <span>.
    """

    def __init__(
        self,
        html_path: Union[str, Path],
        json_path: Union[str, Path],
        output_path: Optional[Union[str, Path]] = None,
        inject_css: bool = False,
    ) -> None:
        """Initialize the page marker inserter.

        Args:
            html_path: Path to input HTML file
            json_path: Path to JSON file with page references
            output_path: Path for output HTML (default: input_with_pages.html)
            inject_css: Whether to inject CSS styling for visible page markers
        """
        self.html_path = Path(html_path)
        self.json_path = Path(json_path)
        self.output_path = (
            Path(output_path)
            if output_path
            else self.html_path.parent / f"{self.html_path.stem}_with_pages.html"
        )
        self.inject_css = inject_css

        self.soup: Optional[BeautifulSoup] = None
        self.page_references: List[Dict[str, Any]] = []
        self.stats: Dict[str, int] = {
            "found": 0,
            "not_found": 0,
            "multiple_matches": 0,
        }

    def load_html(self) -> None:
        """Load and parse the HTML file.

        Raises:
            SystemExit: If file not found or parsing fails
        """
        try:
            with open(self.html_path, "r", encoding="utf-8") as f:
                content = f.read()
            # Use html.parser to preserve original formatting (lxml reorders attributes)
            self.soup = BeautifulSoup(content, "html.parser")
            print(f"✓ Loaded HTML from {self.html_path}")
        except FileNotFoundError:
            print(f"✗ Error: HTML file not found: {self.html_path}")
            sys.exit(1)
        except Exception as e:
            print(f"✗ Error loading HTML: {e}")
            sys.exit(1)

    def load_page_references(self) -> None:
        """Load the JSON mapping file.

        Raises:
            SystemExit: If file not found or JSON parsing fails
        """
        try:
            with open(self.json_path, "r", encoding="utf-8") as f:
                self.page_references = json.load(f)
            print(
                f"✓ Loaded {len(self.page_references)} page references from {self.json_path}"
            )
            print(
                "\n💡 TIP: Snippets can span across formatting tags like <i>, <b>, <span>!"
            )
            print("   You can copy text directly from your PDF - the script will find")
            print("   it even if the HTML has inline formatting.\n")
        except FileNotFoundError:
            print(f"✗ Error: JSON file not found: {self.json_path}")
            sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"✗ Error parsing JSON: {e}")
            sys.exit(1)

    def create_page_marker(self, page_number: Union[str, int]) -> Tag:
        """Create a page marker span element.

        Args:
            page_number: The page number to insert

        Returns:
            BeautifulSoup Tag object for the page marker
        """
        if self.soup is None:
            raise ValueError("HTML not loaded. Call load_html() first.")

        marker = self.soup.new_tag("span")
        marker["class"] = "page-number"
        marker["role"] = "note"
        marker["aria-label"] = f"Page {page_number}"
        marker.string = str(page_number)
        return marker

    def find_snippet_location(
        self, snippet: str
    ) -> Tuple[Optional[NavigableString], Optional[int]]:
        """Find where a snippet ends, even if it spans multiple formatting tags.

        This enhanced version searches through parent containers and can find
        snippets that span across <i>, <b>, <span>, and other inline tags.

        Args:
            snippet: Text snippet to search for

        Returns:
            Tuple of (text_node, position_in_node) or (None, None) if not found
        """
        if self.soup is None:
            raise ValueError("HTML not loaded. Call load_html() first.")

        matches: List[Tuple[NavigableString, int]] = []

        # Search through common container elements
        containers = self.soup.find_all(
            [
                "p",
                "div",
                "td",
                "th",
                "li",
                "dd",
                "dt",
                "h1",
                "h2",
                "h3",
                "h4",
                "h5",
                "h6",
                "blockquote",
                "aside",
                "article",
                "section",
            ]
        )

        # Container types we search through
        container_types = [
            "p", "div", "td", "th", "li", "dd", "dt",
            "h1", "h2", "h3", "h4", "h5", "h6",
            "blockquote", "aside", "article", "section",
        ]

        for container in containers:
            # Skip containers within script, style, etc.
            if container.find_parent(["script", "style", "head"]):
                continue

            # Skip parent containers - only use most specific (leaf) containers
            # If this container has child containers of the same types, skip it
            if container.find(container_types):
                continue

            # Get combined text from this container (strips all tags)
            combined_text = container.get_text()

            # Check if snippet exists in the combined text
            if snippet in combined_text:
                snippet_start = combined_text.find(snippet)
                snippet_end = snippet_start + len(snippet)

                # Walk through all text nodes to find where snippet ends
                current_pos = 0

                for node in container.descendants:
                    if isinstance(node, NavigableString):
                        # Skip non-content elements
                        if node.parent.name in ["script", "style", "head"]:
                            continue

                        node_text = str(node)
                        node_length = len(node_text)

                        # Check if snippet ends within this text node
                        if current_pos < snippet_end <= current_pos + node_length:
                            # Calculate position within this specific node
                            position_in_node = snippet_end - current_pos
                            matches.append((node, position_in_node))
                            break

                        current_pos += node_length

        if len(matches) == 0:
            return None, None
        elif len(matches) > 1:
            self.stats["multiple_matches"] += 1
            print(
                f"  ⚠ Warning: Snippet found in {len(matches)} locations, using last occurrence"
            )

        # Use last occurrence - summaries/abstracts appear first in HTML,
        # so the actual page break location is typically the last match
        return matches[-1]

    def insert_page_marker(self, page_number: Union[str, int], snippet: str) -> bool:
        """Insert a page marker after the specified snippet.

        Args:
            page_number: Page number to insert
            snippet: Text snippet that marks the insertion point

        Returns:
            True if successful, False otherwise
        """
        text_node, position_in_node = self.find_snippet_location(snippet)

        if text_node is None or position_in_node is None:
            print(f"  ✗ Page {page_number}: Snippet not found")
            self.stats["not_found"] += 1
            return False

        # Create the page marker
        marker = self.create_page_marker(page_number)

        # Split the text node at the position where snippet ends
        text_content = str(text_node)

        before_text = text_content[:position_in_node]
        after_text = text_content[position_in_node:]

        # Create new text nodes
        before_node = NavigableString(before_text)
        after_node = NavigableString(after_text) if after_text else None

        # Insert in order: before, marker, after
        text_node.replace_with(before_node)
        before_node.insert_after(marker)
        if after_node:
            marker.insert_after(after_node)

        print(f"  ✓ Page {page_number}: Marker inserted")
        self.stats["found"] += 1
        return True

    def process(self) -> None:
        """Process all page references and insert markers."""
        print("\nInserting page markers...")

        for entry in self.page_references:
            page = entry.get("page")
            snippet = entry.get("snippet")

            if page is None or snippet is None:
                print(f"  ✗ Invalid entry (missing page or snippet): {entry}")
                self.stats["not_found"] += 1
                continue

            self.insert_page_marker(page, snippet)

    def _inject_page_number_css(self) -> None:
        """Inject CSS styling for page-number markers into the HTML head."""
        if self.soup is None:
            return

        css = """
.page-number {
    display: inline-block;
    background-color: #e0e0e0;
    color: #333;
    padding: 2px 6px;
    margin: 0 4px;
    border-radius: 3px;
    font-size: 0.85em;
    font-weight: bold;
    vertical-align: middle;
}
"""
        head = self.soup.find("head")
        if head:
            style_tag = self.soup.new_tag("style")
            style_tag.string = css
            head.append(style_tag)

    def save(self) -> None:
        """Save the modified HTML to output file.

        Raises:
            SystemExit: If saving fails
        """
        if self.soup is None:
            raise ValueError("HTML not loaded. Call load_html() first.")

        if self.inject_css:
            self._inject_page_number_css()

        try:
            with open(self.output_path, "w", encoding="utf-8") as f:
                # Use formatter="minimal" to preserve original whitespace and attributes
                f.write(self.soup.decode(formatter="minimal"))
            print(f"\n✓ Saved output to {self.output_path}")
        except Exception as e:
            print(f"\n✗ Error saving output: {e}")
            sys.exit(1)

    def print_stats(self) -> None:
        """Print processing statistics."""
        total = self.stats["found"] + self.stats["not_found"]
        print("\n" + "=" * 50)
        print("SUMMARY")
        print("=" * 50)
        print(f"Total references:    {total}")
        print(f"Successfully found:  {self.stats['found']}")
        print(f"Not found:           {self.stats['not_found']}")
        print(f"Multiple matches:    {self.stats['multiple_matches']}")

        if self.stats["not_found"] > 0:
            print("\n⚠ Some page markers could not be inserted.")
            print("  Common issues:")
            print("  • Snippets must match EXACTLY (including whitespace)")
            print("  • Check for typos or extra spaces")
            print("  • Snippet may exist in a skipped element (script, style, head)")
            print("  • Try a slightly different snippet from nearby text")

    def run(self) -> None:
        """Execute the full page marker insertion process."""
        print("Page Marker Insertion Tool")
        print("=" * 50)

        self.load_html()
        self.load_page_references()
        self.process()
        self.save()
        self.print_stats()
