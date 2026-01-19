"""Page marker insertion for HTML files."""

import json
import re
import sys
import unicodedata
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
        # Track failed pages for reporting
        self.failed_pages: List[Dict[str, Any]] = []
        # Track position for sequential insertion (container index + position within)
        self._last_insertion_container_idx: int = -1
        self._last_insertion_position: int = 0  # Position within the container
        self._containers: Optional[List[Tag]] = None

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

    def _get_containers(self) -> List[Tag]:
        """Get all content containers in document order (cached).

        Containers are filtered to exclude nested containers and
        non-content elements like script, style, head.

        Returns:
            List of Tag objects representing leaf containers
        """
        if self._containers is not None:
            return self._containers

        if self.soup is None:
            raise ValueError("HTML not loaded. Call load_html() first.")

        container_types = [
            "p", "div", "td", "th", "li", "dd", "dt",
            "h1", "h2", "h3", "h4", "h5", "h6",
            "blockquote", "aside", "article", "section",
        ]

        all_containers = self.soup.find_all(container_types)

        # Filter to leaf containers only
        self._containers = [
            c for c in all_containers
            if not c.find_parent(["script", "style", "head"])
            and not c.find(container_types)
        ]

        return self._containers

    def _normalize_word(self, word: str) -> str:
        """Normalize a word for comparison by removing accents and lowercasing.

        Handles Greek accents (tonos, dialytika) for better matching.

        Args:
            word: Word to normalize

        Returns:
            Normalized word (lowercase, no accents)
        """
        # NFD decomposition separates base characters from combining marks
        normalized = unicodedata.normalize("NFD", word.lower())
        # Remove combining diacritical marks (accents)
        return "".join(c for c in normalized if unicodedata.category(c) != "Mn")

    def _jaccard_similarity(self, words1: List[str], words2: List[str]) -> float:
        """Calculate Jaccard similarity between two word lists.

        Uses normalized words for comparison to handle accent differences.

        Args:
            words1: First list of words
            words2: Second list of words

        Returns:
            Similarity score between 0.0 and 1.0
        """
        if not words1 or not words2:
            return 0.0

        set1 = {self._normalize_word(w) for w in words1}
        set2 = {self._normalize_word(w) for w in words2}

        intersection = len(set1 & set2)
        union = len(set1 | set2)

        return intersection / union if union > 0 else 0.0

    def _extract_html_context(
        self, container_text: str, position: int, snippet_len: int, num_words: int = 4
    ) -> Tuple[str, str]:
        """Extract context words before and after a match position in HTML.

        Args:
            container_text: Full text of the container
            position: Start position of the snippet match
            snippet_len: Length of the matched snippet
            num_words: Number of context words to extract

        Returns:
            Tuple of (context_before, context_after)
        """
        # Text before the snippet
        text_before = container_text[:position]
        words_before = text_before.split()
        context_before = " ".join(words_before[-num_words:]) if words_before else ""

        # Text after the snippet
        text_after = container_text[position + snippet_len:]
        words_after = text_after.split()
        context_after = " ".join(words_after[:num_words]) if words_after else ""

        return (context_before, context_after)

    def _score_context_match(
        self,
        container_text: str,
        position: int,
        snippet_len: int,
        expected_before: str,
        expected_after: str,
    ) -> float:
        """Score how well the context around a match position matches expected context.

        Uses Jaccard word similarity with Greek accent normalization.
        Weights are 40% before-context, 60% after-context (empirically chosen;
        can be adjusted based on extraction strategy and content type).

        Args:
            container_text: Full text of the container
            position: Start position of the snippet match
            snippet_len: Length of the matched snippet
            expected_before: Expected context before (from PDF)
            expected_after: Expected context after (from PDF)

        Returns:
            Similarity score between 0.0 and 1.0
        """
        actual_before, actual_after = self._extract_html_context(
            container_text, position, snippet_len
        )

        before_words = expected_before.split() if expected_before else []
        after_words = expected_after.split() if expected_after else []
        actual_before_words = actual_before.split()
        actual_after_words = actual_after.split()

        before_score = self._jaccard_similarity(before_words, actual_before_words)
        after_score = self._jaccard_similarity(after_words, actual_after_words)

        # Weighted average of before/after scores (40/60 split, empirically chosen)
        # If only one context is available, use just that one
        if expected_before and expected_after:
            return 0.4 * before_score + 0.6 * after_score
        elif expected_after:
            return after_score
        elif expected_before:
            return before_score
        else:
            return 0.0

    def find_all_snippet_locations(
        self, snippet: str, search_after_idx: int = -1, search_after_pos: int = 0
    ) -> List[Tuple[NavigableString, int, int, int, str]]:
        """Find ALL occurrences of snippet after the current position.

        Used for context-based disambiguation when multiple matches exist.

        Args:
            snippet: Text snippet to search for
            search_after_idx: Container index of last insertion
            search_after_pos: Position within that container of last insertion

        Returns:
            List of tuples: (text_node, position_in_node, container_index,
                           marker_position, container_text)
        """
        # Handle page break marker
        if "|" in snippet:
            parts = snippet.split("|", 1)
            snippet_before = parts[0].strip()
            snippet_after = parts[1].strip() if len(parts) > 1 else ""
            search_snippet = f"{snippet_before} {snippet_after}".strip()
            marker_offset = len(snippet_before)
        else:
            search_snippet = snippet
            marker_offset = len(snippet)

        if self.soup is None:
            raise ValueError("HTML not loaded. Call load_html() first.")

        containers = self._get_containers()
        locations = []

        for idx, container in enumerate(containers):
            # Skip containers before our current position
            if idx < search_after_idx:
                continue

            combined_text = container.get_text()

            # Find ALL occurrences in this container
            start_pos = 0
            while True:
                snippet_start = combined_text.find(search_snippet, start_pos)
                if snippet_start == -1:
                    break

                marker_position = snippet_start + marker_offset

                # If same container as last insertion, must be after that position
                if idx == search_after_idx and marker_position <= search_after_pos:
                    start_pos = snippet_start + 1
                    continue

                # Walk through all text nodes to find where marker should go
                current_pos = 0

                for node in container.descendants:
                    if isinstance(node, NavigableString):
                        if node.parent.name in ["script", "style", "head"]:
                            continue

                        node_text = str(node)
                        node_length = len(node_text)

                        if current_pos < marker_position <= current_pos + node_length:
                            position_in_node = marker_position - current_pos
                            locations.append((
                                node, position_in_node, idx, marker_position, combined_text
                            ))
                            break

                        current_pos += node_length

                start_pos = snippet_start + 1

        return locations

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
        self, snippet: str, search_after_idx: int = -1, search_after_pos: int = 0
    ) -> Tuple[Optional[NavigableString], Optional[int], int, int]:
        """Find where to place a marker after a snippet.

        This method searches through containers in document order, but only
        considers positions AFTER the last insertion point. This allows
        multiple page markers within the same container (paragraph).

        Markers are placed AFTER the snippet text. For EPUB page navigation,
        use a +1 page offset so the marker at the END of page N is labeled
        as page N+1 (indicating where the next page begins).

        Supports page break marker "|" in snippets:
        - "word1 word2|word3 word4" searches for "word1 word2 word3 word4"
        - Returns position at the "|" marker point

        Args:
            snippet: Text snippet to search for (may contain | for page break)
            search_after_idx: Container index of last insertion
            search_after_pos: Position within that container of last insertion

        Returns:
            Tuple of (text_node, position_in_node, container_index, marker_position)
            or (None, None, -1, 0) if not found
        """
        # Handle page break marker - split into before/after parts
        if "|" in snippet:
            parts = snippet.split("|", 1)
            snippet_before = parts[0].strip()
            snippet_after = parts[1].strip() if len(parts) > 1 else ""
            # Search for combined context (without the |)
            search_snippet = f"{snippet_before} {snippet_after}".strip()
            # Position at the | marker
            marker_offset = len(snippet_before)
        else:
            search_snippet = snippet
            # Marker goes AFTER snippet
            marker_offset = len(snippet)

        if self.soup is None:
            raise ValueError("HTML not loaded. Call load_html() first.")

        containers = self._get_containers()

        for idx, container in enumerate(containers):
            # Skip containers before our current position
            if idx < search_after_idx:
                continue

            # Get combined text from this container (strips all tags)
            combined_text = container.get_text()

            # Check if snippet exists in the combined text
            if search_snippet in combined_text:
                snippet_start = combined_text.find(search_snippet)
                # marker_position is where the page break marker should go
                # (after snippet_before, not after the full search_snippet)
                marker_position = snippet_start + marker_offset

                # If same container as last insertion, must be after that position
                if idx == search_after_idx and marker_position <= search_after_pos:
                    # Snippet is before our last insertion point, try to find later occurrence
                    later_start = combined_text.find(search_snippet, search_after_pos)
                    if later_start == -1:
                        continue  # No later occurrence in this container
                    snippet_start = later_start
                    marker_position = snippet_start + marker_offset

                # Walk through all text nodes to find where marker should go
                current_pos = 0

                for node in container.descendants:
                    if isinstance(node, NavigableString):
                        # Skip non-content elements
                        if node.parent.name in ["script", "style", "head"]:
                            continue

                        node_text = str(node)
                        node_length = len(node_text)

                        # Check if marker position is within this text node
                        if current_pos < marker_position <= current_pos + node_length:
                            # Calculate position within this specific node
                            position_in_node = marker_position - current_pos
                            return (node, position_in_node, idx, marker_position)

                        current_pos += node_length

        return (None, None, -1, 0)

    def insert_page_marker(
        self,
        page_number: Union[str, int],
        snippet: str,
        context_before: Optional[str] = None,
        context_after: Optional[str] = None,
    ) -> bool:
        """Insert a page marker after the specified snippet.

        Uses sequential position tracking: each marker is only placed AFTER
        the previous marker's position in the document. This ensures correct
        ordering even when snippet text appears multiple times, including
        multiple page breaks within the same paragraph.

        When context is provided and multiple matches exist, uses Jaccard
        similarity scoring to select the best match.

        Args:
            page_number: Page number to insert
            snippet: Text snippet that marks the insertion point
            context_before: Optional context words before snippet (from PDF)
            context_after: Optional context words after snippet (from PDF)

        Returns:
            True if successful, False otherwise
        """
        # Determine snippet length for context scoring
        if "|" in snippet:
            parts = snippet.split("|", 1)
            snippet_before = parts[0].strip()
            snippet_after = parts[1].strip() if len(parts) > 1 else ""
            search_snippet = f"{snippet_before} {snippet_after}".strip()
        else:
            search_snippet = snippet

        snippet_len = len(search_snippet)

        # Check if we have context for disambiguation
        has_context = bool(context_before or context_after)

        if has_context:
            # Find ALL matching locations for context-based selection
            all_locations = self.find_all_snippet_locations(
                snippet, self._last_insertion_container_idx, self._last_insertion_position
            )

            if len(all_locations) > 1:
                # Multiple matches - use context to disambiguate
                best_location = None
                best_score = -1.0

                for loc in all_locations:
                    text_node, position_in_node, container_idx, marker_position, container_text = loc
                    # Calculate snippet start position from marker position
                    # marker_position is where the marker goes:
                    # - Without |: after the full search_snippet
                    # - With |: after snippet_before (the | marker point)
                    if "|" in snippet:
                        actual_snippet_start = marker_position - len(snippet_before)
                    else:
                        actual_snippet_start = marker_position - len(search_snippet)

                    score = self._score_context_match(
                        container_text, actual_snippet_start, snippet_len,
                        context_before or "", context_after or ""
                    )

                    if score > best_score:
                        best_score = score
                        best_location = loc

                # Use context match if score >= 0.3 (empirically chosen threshold requiring
                # at least ~1/3 word overlap to avoid false positives from unrelated context)
                if best_score >= 0.3 and best_location is not None:
                    text_node, position_in_node, container_idx, container_pos, _ = best_location
                    self.stats["context_used"] = self.stats.get("context_used", 0) + 1
                    print(f"  ℹ Page {page_number}: Context disambiguation used (score: {best_score:.2f})")
                else:
                    # Fall back to first sequential match - warn user as placement may be wrong
                    text_node, position_in_node, container_idx, container_pos, _ = all_locations[0]
                    self.stats["context_fallback"] = self.stats.get("context_fallback", 0) + 1
                    print(f"  ⚠ Page {page_number}: Context score too low ({best_score:.2f}), using first sequential match - verify placement")
            elif len(all_locations) == 1:
                # Single match - use it directly
                text_node, position_in_node, container_idx, container_pos, _ = all_locations[0]
            else:
                text_node, position_in_node, container_idx, container_pos = None, None, -1, 0
        else:
            # No context - use original sequential matching
            text_node, position_in_node, container_idx, container_pos = self.find_snippet_location(
                snippet, self._last_insertion_container_idx, self._last_insertion_position
            )

        if text_node is None or position_in_node is None:
            print(f"  ✗ Page {page_number}: Snippet not found after container {self._last_insertion_container_idx}:{self._last_insertion_position}")
            self.stats["not_found"] += 1
            self.failed_pages.append({
                "page": page_number,
                "snippet": snippet,
                "last_container": self._last_insertion_container_idx,
                "last_position": self._last_insertion_position,
            })
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

        # Update position tracking for next insertion
        self._last_insertion_container_idx = container_idx
        self._last_insertion_position = container_pos

        print(f"  ✓ Page {page_number}: Marker inserted (container {container_idx}:{container_pos})")
        self.stats["found"] += 1
        return True

    def process(self) -> None:
        """Process all page references and insert markers.

        Pages are processed in ascending order to ensure sequential placement.
        Sequential position tracking ensures each marker is placed AFTER the
        previous one in document order.

        If entries contain context_before/context_after fields, these are used
        for disambiguation when multiple matches exist.
        """
        print("\nInserting page markers...")

        # Reset position tracking for fresh processing
        self._last_insertion_container_idx = -1
        self._last_insertion_position = 0
        self._containers = None  # Re-cache containers

        # Sort by page number to process in order
        sorted_refs = sorted(
            self.page_references,
            key=lambda x: (
                # Handle both numeric and roman numeral pages
                int(x.get("page", 0)) if str(x.get("page", "")).isdigit() else 0,
                str(x.get("page", ""))
            )
        )

        for entry in sorted_refs:
            page = entry.get("page")
            snippet = entry.get("snippet")

            if page is None or snippet is None:
                print(f"  ✗ Invalid entry (missing page or snippet): {entry}")
                self.stats["not_found"] += 1
                continue

            # Extract context for disambiguation (if present in JSON)
            context_before = entry.get("context_before")
            context_after = entry.get("context_after")

            self.insert_page_marker(page, snippet, context_before, context_after)

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

    def _remove_out_of_order_markers(self) -> int:
        """Remove page markers that are out of sequential order.

        Page markers should appear in ascending order throughout the document.
        Any marker that breaks this sequence is likely placed incorrectly.

        Returns:
            Number of markers removed
        """
        if self.soup is None:
            return 0

        # Find all page markers in document order
        markers = self.soup.find_all("span", class_="page-number")

        # Extract page numbers and track which to remove
        to_remove = []
        max_page_seen = -1

        for marker in markers:
            try:
                page_num = int(marker.get_text())
                if page_num < max_page_seen:
                    # This marker is out of order - mark for removal
                    to_remove.append(marker)
                else:
                    max_page_seen = page_num
            except (ValueError, TypeError):
                # Non-numeric page (e.g., roman numerals) - skip
                continue

        # Remove out-of-order markers
        for marker in to_remove:
            page_num = marker.get_text()
            # Replace marker with empty string (remove it)
            marker.decompose()

        if to_remove:
            print(f"\n⚠ Removed {len(to_remove)} out-of-order markers")
            self.stats["out_of_order"] = len(to_remove)

        return len(to_remove)

    def save(self) -> None:
        """Save the modified HTML to output file.

        Raises:
            SystemExit: If saving fails
        """
        if self.soup is None:
            raise ValueError("HTML not loaded. Call load_html() first.")

        # Remove any out-of-order markers before saving
        self._remove_out_of_order_markers()

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
        out_of_order = self.stats.get("out_of_order", 0)
        context_used = self.stats.get("context_used", 0)
        kept = self.stats["found"] - out_of_order

        print("\n" + "=" * 50)
        print("SUMMARY")
        print("=" * 50)
        print(f"Total references:    {total}")
        print(f"Successfully found:  {self.stats['found']}")
        print(f"Not found:           {self.stats['not_found']}")
        print(f"Multiple matches:    {self.stats['multiple_matches']}")
        if context_used > 0:
            print(f"Context disambiguations: {context_used}")
        context_fallback = self.stats.get("context_fallback", 0)
        if context_fallback > 0:
            print(f"Context fallbacks:   {context_fallback} ⚠ (verify these placements)")
        if out_of_order > 0:
            print(f"Out-of-order removed: {out_of_order}")
            print(f"Final markers kept:  {kept}")

        if self.stats["not_found"] > 0:
            print("\n⚠ Some page markers could not be inserted.")
            print("  Common issues:")
            print("  • Snippets must match EXACTLY (including whitespace)")
            print("  • Check for typos or extra spaces")
            print("  • Snippet may exist in a skipped element (script, style, head)")
            print("  • Try a slightly different snippet from nearby text")
            self._print_failed_report()

    def _print_failed_report(self) -> None:
        """Print detailed report of failed page insertions."""
        if not self.failed_pages:
            return

        print("\n" + "=" * 50)
        print("FAILED PAGES REPORT")
        print("=" * 50)
        print(f"\nPages that could not be inserted: {', '.join(str(f['page']) for f in self.failed_pages)}")
        print("\nDetails:")
        print("-" * 50)

        for failure in self.failed_pages:
            page = failure["page"]
            snippet = failure["snippet"]
            last_container = failure["last_container"]
            last_position = failure["last_position"]

            # Truncate snippet for display
            display_snippet = snippet[:60] + "..." if len(snippet) > 60 else snippet

            print(f"\nPage {page}:")
            print(f"  Snippet: \"{display_snippet}\"")
            print(f"  Searched after: container {last_container}, position {last_position}")
            print(f"  Possible causes:")
            print(f"    - Snippet text doesn't exist in HTML")
            print(f"    - Snippet exists only before position {last_position} (duplicate text)")

    def run(self) -> None:
        """Execute the full page marker insertion process."""
        print("Page Marker Insertion Tool")
        print("=" * 50)

        self.load_html()
        self.load_page_references()
        self.process()
        self.save()
        self.print_stats()
