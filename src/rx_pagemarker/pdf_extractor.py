"""PDF text extraction for automatic snippet generation."""

import json
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Literal, Optional, Union

from .word_segmentation import segment_snippet

# Common patterns for production metadata to exclude from snippets
# These appear in professional PDFs from InDesign, Acrobat, etc.
DEFAULT_EXCLUDE_PATTERNS = [
    # InDesign sluglines: "XRDD 4:2025 SEL.indd 818" - starts with uppercase/number
    r"[A-Z0-9][A-Za-z0-9\s:./\-]*\.indd\s+\d+",
    # Timestamps: "5/1/26 2:15 PM"
    r"\d{1,2}/\d{1,2}/\d{2,4}\s+\d{1,2}:\d{2}\s*(AM|PM)?",
]

if TYPE_CHECKING:
    import fitz
    import pdfplumber.page
    from .html_matcher import HTMLMatcher

try:
    import fitz  # PyMuPDF

    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False

try:
    import pdfplumber

    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False


# Custom exceptions
class PDFExtractionError(Exception):
    """Base exception for PDF extraction errors."""

    pass


class MissingDependencyError(PDFExtractionError):
    """Raised when required PDF library is not installed."""

    pass


class PDFNotFoundError(PDFExtractionError):
    """Raised when PDF file is not found."""

    pass


class InvalidParameterError(PDFExtractionError):
    """Raised when invalid parameters are provided."""

    pass


class PDFExtractor:
    """Extract text snippets from PDF files for page marker generation.

    Supports multiple extraction strategies and can use either PyMuPDF (fast)
    or pdfplumber (better layout analysis) as backends.
    """

    def __init__(
        self,
        pdf_path: Union[str, Path],
        backend: Literal["auto", "pymupdf", "pdfplumber"] = "auto",
        snippet_words: int = 10,
        min_words: int = 3,
        strategy: Literal["end_of_page", "bottom_visual"] = "end_of_page",
        segment_words: bool = False,
        language: str = "el",
        match_html_path: Optional[Union[str, Path]] = None,
        exclude_patterns: Optional[List[str]] = None,
        use_default_excludes: bool = True,
        skip_footnotes: bool = False,
        min_font_size: float = 8.5,
    ) -> None:
        """Initialize PDF extractor.

        Args:
            pdf_path: Path to PDF file
            backend: Extraction backend to use (auto, pymupdf, or pdfplumber)
            snippet_words: Target number of words per snippet
            min_words: Minimum words needed for valid snippet
            strategy: How to select snippets:
                - "end_of_page": Last N words of extracted text
                - "bottom_visual": Text from visually lowest position on page
            segment_words: Enable word boundary reconstruction for PDFs with missing spaces
            language: Language code for word segmentation (e.g., 'el' for Greek)
            match_html_path: Optional path to HTML file for matching-based correction
            exclude_patterns: Regex patterns to exclude from text (e.g., InDesign sluglines)
            use_default_excludes: Whether to use default exclude patterns for common
                production metadata (InDesign sluglines, timestamps)
            skip_footnotes: Whether to skip footnote text (smaller font at bottom of page)
            min_font_size: Minimum font size to include (smaller text treated as footnotes)

        Raises:
            InvalidParameterError: If snippet_words or min_words are invalid
            MissingDependencyError: If required PDF library is not installed
        """
        # Validate parameters
        if snippet_words < 1:
            raise InvalidParameterError(
                f"snippet_words must be >= 1, got {snippet_words}"
            )
        if min_words < 1:
            raise InvalidParameterError(f"min_words must be >= 1, got {min_words}")
        if snippet_words > 1000:
            raise InvalidParameterError(
                f"snippet_words must be <= 1000, got {snippet_words}"
            )

        self.pdf_path = Path(pdf_path)
        self.snippet_words = snippet_words
        self.min_words = min_words
        self.strategy = strategy
        self.segment_words = segment_words
        self.language = language
        self.match_html_path = Path(match_html_path) if match_html_path else None
        self.skip_footnotes = skip_footnotes
        self.min_font_size = min_font_size

        # Build list of exclude patterns
        self.exclude_patterns: List[re.Pattern[str]] = []
        if use_default_excludes:
            for pattern in DEFAULT_EXCLUDE_PATTERNS:
                self.exclude_patterns.append(re.compile(pattern, re.IGNORECASE))
        if exclude_patterns:
            for pattern in exclude_patterns:
                self.exclude_patterns.append(re.compile(pattern, re.IGNORECASE))

        # Load HTML content for word completion if path provided
        self.html_text: Optional[str] = None
        if self.match_html_path:
            try:
                with open(self.match_html_path, "r", encoding="utf-8") as f:
                    html_content = f.read()
                # Strip HTML tags for text matching
                self.html_text = re.sub(r"<[^>]+>", "", html_content)
                self.html_text = re.sub(r"\s+", " ", self.html_text)
            except Exception as e:
                print(f"⚠ Warning: Could not load HTML for word completion: {e}")

        # Initialize HTML matcher if provided (for fuzzy matching)
        self.html_matcher: Optional["HTMLMatcher"] = None
        if self.match_html_path:
            try:
                from .html_matcher import HTMLMatcher

                self.html_matcher = HTMLMatcher(self.match_html_path)
            except ImportError as e:
                raise MissingDependencyError(
                    f"HTML matching requires rapidfuzz. Install with: pip install rapidfuzz"
                ) from e

        # Select backend
        if backend == "auto":
            if HAS_PYMUPDF:
                self.backend = "pymupdf"
            elif HAS_PDFPLUMBER:
                self.backend = "pdfplumber"
            else:
                raise MissingDependencyError(
                    "Neither PyMuPDF nor pdfplumber is installed. "
                    "Install with: pip install PyMuPDF pdfplumber"
                )
        elif backend == "pymupdf" and not HAS_PYMUPDF:
            raise MissingDependencyError(
                "PyMuPDF not installed. Install with: pip install PyMuPDF"
            )
        elif backend == "pdfplumber" and not HAS_PDFPLUMBER:
            raise MissingDependencyError(
                "pdfplumber not installed. Install with: pip install pdfplumber"
            )
        else:
            self.backend = backend

        self.stats: Dict[str, int] = {
            "total_pages": 0,
            "successful": 0,
            "insufficient_text": 0,
            "failed": 0,
        }

    def _filter_production_metadata(self, text: str) -> str:
        """Remove production metadata (InDesign sluglines, timestamps, etc.) from text.

        Args:
            text: Raw text extracted from PDF page

        Returns:
            Text with production metadata removed
        """
        if not self.exclude_patterns:
            return text

        filtered = text
        for pattern in self.exclude_patterns:
            filtered = pattern.sub("", filtered)

        # Clean up extra whitespace from removals
        filtered = re.sub(r"\s+", " ", filtered).strip()
        return filtered

    def _dehyphenate(self, text: str) -> str:
        """Remove soft hyphens from line-break hyphenation in PDF text.

        PDFs often have words split across lines with hyphens (e.g., "δικαι- ολογούσα").
        This rejoins them to match the clean HTML text (e.g., "δικαιολογούσα").

        Args:
            text: Text with potential line-break hyphens

        Returns:
            Text with hyphenated words rejoined
        """
        # Pattern: word ending with hyphen, followed by whitespace/newline, then continuation
        # Matches: "word- continuation" or "word-\ncontinuation"
        dehyphenated = re.sub(r"(\w)-\s+(\w)", r"\1\2", text)
        return dehyphenated

    def _clean_snippet(self, snippet: str, html_text: Optional[str] = None) -> str:
        """Clean up snippet for better matching.

        Removes trailing incomplete words and normalizes spacing for better HTML matching.
        If HTML text is provided, attempts to complete partial words at the end.

        Args:
            snippet: Raw snippet text
            html_text: Optional HTML text content for word completion

        Returns:
            Cleaned snippet
        """
        # Remove trailing word fragments ending with hyphen
        cleaned = re.sub(r"\s+\S+-$", "", snippet)
        # Normalize spacing around slashes and punctuation
        cleaned = re.sub(r"\s+/\s*", "/", cleaned)  # "word / word" -> "word/word"
        cleaned = re.sub(r"\s*/\s+", "/", cleaned)  # Also handle "word/ word"
        cleaned = cleaned.strip()

        # Try to complete partial words at the end if HTML is available
        if html_text and cleaned:
            cleaned = self._complete_partial_word(cleaned, html_text)

        return cleaned

    def _complete_partial_word(self, snippet: str, html_text: str) -> str:
        """Complete partial word at end of snippet by finding full word in HTML.

        If snippet ends with incomplete word like "σύγ", finds the complete
        word "σύγχυση" in HTML and replaces it.

        Args:
            snippet: Snippet potentially ending with partial word
            html_text: HTML text to search for complete word

        Returns:
            Snippet with last word completed if possible
        """
        words = snippet.split()
        if not words:
            return snippet

        last_word = words[-1]

        # Check if last word exists in HTML as-is (as whole word, not substring)
        # Use lookahead/lookbehind that work with Unicode by checking for space/boundary
        word_pattern = r'(?:^|[\s])' + re.escape(last_word) + r'(?:[\s.,;:!?\)]|$)'
        if re.search(word_pattern, html_text):
            return snippet

        # Last word not found as complete word - try to find complete word
        # Search for words starting with last_word followed by more letters
        # Use [\s] or start-of-string to mark word boundary (Unicode-safe)
        pattern = r'(?:^|[\s])' + re.escape(last_word) + r'(\w+)'
        match = re.search(pattern, html_text, re.UNICODE)

        if match:
            # Found complete word
            complete_word = last_word + match.group(1)
            words[-1] = complete_word
            return " ".join(words)

        # If still not found and word is very short, it might be a fragment - remove it
        if len(last_word) < 4 and last_word[-1] not in '.,;:!?)»"\'':
            return " ".join(words[:-1])

        return snippet

    def _extract_body_text_pymupdf(self, page: "fitz.Page") -> str:
        """Extract only body text from page, skipping footnotes based on font size.

        Footnotes typically use smaller fonts than body text. This method filters
        out text spans below the minimum font size threshold.

        Args:
            page: PyMuPDF page object

        Returns:
            Body text with footnotes excluded
        """
        # Get detailed text with font information
        blocks = page.get_text("dict")["blocks"]

        body_spans = []
        for block in blocks:
            if "lines" not in block:
                continue
            for line in block["lines"]:
                for span in line["spans"]:
                    # Only include text at or above minimum font size
                    if span["size"] >= self.min_font_size:
                        body_spans.append({
                            "y": span["bbox"][3],  # bottom y coordinate
                            "text": span["text"]
                        })

        # Sort by vertical position (reading order)
        body_spans.sort(key=lambda s: s["y"])

        # Join text
        text = " ".join(s["text"] for s in body_spans)
        return text

    def extract_with_pymupdf(self) -> List[Dict[str, Any]]:
        """Extract snippets using PyMuPDF (fast, good layout analysis).

        Returns:
            List of dictionaries with 'page' and 'snippet' keys

        Raises:
            PDFExtractionError: If PDF reading fails
        """
        snippets = []

        try:
            with fitz.open(str(self.pdf_path)) as doc:
                self.stats["total_pages"] = len(doc)

                print(f"Using PyMuPDF backend for {len(doc)} pages...")

                for page_num in range(len(doc)):
                    page = doc[page_num]

                    # Show progress for large files
                    if (page_num + 1) % 50 == 0:
                        print(f"  Processing page {page_num + 1}/{len(doc)}...")

                    snippet = self._extract_page_snippet_pymupdf(page, page_num + 1)
                    snippets.append(snippet)

        except Exception as e:
            raise PDFExtractionError(f"Error reading PDF with PyMuPDF: {e}") from e

        return snippets

    def _extract_page_snippet_pymupdf(
        self, page: "fitz.Page", page_num: int
    ) -> Dict[str, Any]:
        """Extract snippet from a single page using PyMuPDF."""
        try:
            if self.skip_footnotes:
                # Extract text while filtering by font size to skip footnotes
                text = self._extract_body_text_pymupdf(page)
            elif self.strategy == "bottom_visual":
                # Get text blocks with positions
                blocks = page.get_text("blocks")

                # Sort by Y coordinate descending (bottom first)
                # Block format: (x0, y0, x1, y1, "text", block_no, block_type)
                blocks.sort(key=lambda b: -b[1])

                # Get text from bottommost block
                text = blocks[0][4] if blocks else ""
            else:  # end_of_page
                # Get all text
                text = page.get_text()

            # Filter out production metadata (InDesign sluglines, etc.)
            text = self._filter_production_metadata(text)

            # Rejoin hyphenated words split across lines
            text = self._dehyphenate(text)

            # Extract snippet
            words = text.split()

            if len(words) < self.min_words:
                self.stats["insufficient_text"] += 1
                return {
                    "page": page_num,
                    "snippet": "PASTE_TEXT_FROM_END_OF_PAGE_HERE",
                    "note": f"Insufficient text (found {len(words)} words, need {self.min_words})",
                }

            snippet = " ".join(words[-self.snippet_words :])

            # Clean up trailing incomplete words and complete partial words from HTML
            snippet = self._clean_snippet(snippet, self.html_text)

            # Apply HTML matching if available (highest priority)
            if self.html_matcher:
                result = self.html_matcher.find_match(snippet)
                self.stats["successful"] += 1
                return {
                    "page": page_num,
                    "snippet": result["matched_text"].strip(),
                    "confidence": round(result["confidence"], 2),
                    "method": "html_match",
                }

            # Apply word segmentation if enabled
            if self.segment_words:
                segmented, confidence = segment_snippet(
                    snippet, language=self.language, max_words=self.snippet_words
                )
                self.stats["successful"] += 1
                return {
                    "page": page_num,
                    "snippet": segmented.strip(),
                    "confidence": round(confidence, 2),
                    "method": "word_segmentation",
                }

            self.stats["successful"] += 1

            return {
                "page": page_num,
                "snippet": snippet.strip(),
            }

        except Exception as e:
            self.stats["failed"] += 1
            return {
                "page": page_num,
                "snippet": "PASTE_TEXT_FROM_END_OF_PAGE_HERE",
                "note": f"Extraction failed: {str(e)}",
            }

    def extract_with_pdfplumber(self) -> List[Dict[str, Any]]:
        """Extract snippets using pdfplumber (better for complex layouts).

        Returns:
            List of dictionaries with 'page' and 'snippet' keys

        Raises:
            PDFExtractionError: If PDF reading fails
        """
        snippets = []

        try:
            with pdfplumber.open(str(self.pdf_path)) as pdf:
                self.stats["total_pages"] = len(pdf.pages)
                print(f"Using pdfplumber backend for {len(pdf.pages)} pages...")

                for page_num, page in enumerate(pdf.pages, 1):
                    # Show progress for large files
                    if page_num % 50 == 0:
                        print(f"  Processing page {page_num}/{len(pdf.pages)}...")

                    snippet = self._extract_page_snippet_pdfplumber(page, page_num)
                    snippets.append(snippet)

        except Exception as e:
            raise PDFExtractionError(f"Error reading PDF with pdfplumber: {e}") from e

        return snippets

    def _extract_page_snippet_pdfplumber(
        self, page: "pdfplumber.page.Page", page_num: int
    ) -> Dict[str, Any]:
        """Extract snippet from a single page using pdfplumber."""
        try:
            if self.strategy == "bottom_visual":
                # Get words with bounding boxes
                words = page.extract_words()

                if not words:
                    text = ""
                else:
                    # Sort by vertical position (bottom first)
                    words_sorted = sorted(words, key=lambda w: -w["top"])

                    # Get bottom N words
                    bottom_words = words_sorted[: self.snippet_words]

                    # Re-sort by reading order (top to bottom, left to right)
                    bottom_words.sort(key=lambda w: (w["top"], w["x0"]))

                    text = " ".join(w["text"] for w in bottom_words)
            else:  # end_of_page
                text = page.extract_text() or ""

            # Filter out production metadata (InDesign sluglines, etc.)
            text = self._filter_production_metadata(text)

            # Rejoin hyphenated words split across lines
            text = self._dehyphenate(text)

            # Extract snippet
            words = text.split()

            if len(words) < self.min_words:
                self.stats["insufficient_text"] += 1
                return {
                    "page": page_num,
                    "snippet": "PASTE_TEXT_FROM_END_OF_PAGE_HERE",
                    "note": f"Insufficient text (found {len(words)} words, need {self.min_words})",
                }

            snippet = " ".join(words[-self.snippet_words :])

            # Clean up trailing incomplete words and complete partial words from HTML
            snippet = self._clean_snippet(snippet, self.html_text)

            # Apply HTML matching if available (highest priority)
            if self.html_matcher:
                result = self.html_matcher.find_match(snippet)
                self.stats["successful"] += 1
                return {
                    "page": page_num,
                    "snippet": result["matched_text"].strip(),
                    "confidence": round(result["confidence"], 2),
                    "method": "html_match",
                }

            # Apply word segmentation if enabled
            if self.segment_words:
                segmented, confidence = segment_snippet(
                    snippet, language=self.language, max_words=self.snippet_words
                )
                self.stats["successful"] += 1
                return {
                    "page": page_num,
                    "snippet": segmented.strip(),
                    "confidence": round(confidence, 2),
                    "method": "word_segmentation",
                }

            self.stats["successful"] += 1

            return {
                "page": page_num,
                "snippet": snippet.strip(),
            }

        except Exception as e:
            self.stats["failed"] += 1
            return {
                "page": page_num,
                "snippet": "PASTE_TEXT_FROM_END_OF_PAGE_HERE",
                "note": f"Extraction failed: {str(e)}",
            }

    def extract(self) -> List[Dict[str, Any]]:
        """Extract snippets using the configured backend.

        Returns:
            List of dictionaries with 'page' and 'snippet' keys

        Raises:
            PDFNotFoundError: If PDF file doesn't exist
            PDFExtractionError: If extraction fails
        """
        if not self.pdf_path.exists():
            raise PDFNotFoundError(f"PDF file not found: {self.pdf_path}")

        print(f"\nExtracting snippets from {self.pdf_path.name}")
        print(f"Strategy: {self.strategy}")
        print(f"Snippet length: {self.snippet_words} words")
        print(f"Backend: {self.backend}\n")

        if self.backend == "pymupdf":
            return self.extract_with_pymupdf()
        else:
            return self.extract_with_pdfplumber()

    def save_to_json(
        self, output_path: Union[str, Path], snippets: List[Dict[str, Any]]
    ) -> None:
        """Save extracted snippets to JSON file.

        Args:
            output_path: Path for output JSON file
            snippets: List of snippet dictionaries

        Raises:
            PDFExtractionError: If saving JSON fails
        """
        output_path = Path(output_path)

        try:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(snippets, f, indent=2, ensure_ascii=False)
            print(f"\n✓ Saved {len(snippets)} snippets to {output_path}")
        except Exception as e:
            raise PDFExtractionError(f"Error saving JSON: {e}") from e

    def print_stats(self) -> None:
        """Print extraction statistics."""
        print("\n" + "=" * 50)
        print("EXTRACTION SUMMARY")
        print("=" * 50)
        print(f"Total pages:         {self.stats['total_pages']}")
        print(f"Successfully extracted: {self.stats['successful']}")
        print(f"Insufficient text:   {self.stats['insufficient_text']}")
        print(f"Failed:              {self.stats['failed']}")

        if self.stats["insufficient_text"] > 0 or self.stats["failed"] > 0:
            print("\n⚠ Some pages need manual snippet entry.")
            print("  Look for entries with 'PASTE_TEXT_FROM_END_OF_PAGE_HERE'")
            print("  in the generated JSON file.")


def validate_snippets(
    json_path: Union[str, Path],
    html_path: Optional[Union[str, Path]] = None,
    show_missing: bool = True,
) -> Dict[str, Any]:
    """Validate extracted snippets for uniqueness and HTML presence.

    Args:
        json_path: Path to JSON file with snippets
        html_path: Optional path to HTML file to check against
        show_missing: Whether to print missing snippets

    Returns:
        Dictionary with validation results

    Raises:
        PDFExtractionError: If JSON file cannot be loaded
    """
    json_path = Path(json_path)

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            snippets = json.load(f)
    except Exception as e:
        raise PDFExtractionError(f"Error loading JSON: {e}") from e

    # Check for duplicates
    from collections import Counter

    snippet_texts = [s["snippet"] for s in snippets if "snippet" in s]
    snippet_counts = Counter(snippet_texts)
    duplicates = {text: count for text, count in snippet_counts.items() if count > 1}

    # Count placeholders
    placeholders = sum(
        1 for s in snippets if s.get("snippet") == "PASTE_TEXT_FROM_END_OF_PAGE_HERE"
    )

    results = {
        "total_snippets": len(snippets),
        "unique_snippets": len(set(snippet_texts)),
        "duplicate_snippets": duplicates,
        "placeholder_count": placeholders,
    }

    # Check against HTML if provided
    if html_path:
        html_path = Path(html_path)
        try:
            with open(html_path, "r", encoding="utf-8") as f:
                html_content = f.read()

            # Strip HTML tags for text comparison (snippets won't have tags)
            text_content = re.sub(r"<[^>]+>", "", html_content)
            # Normalize whitespace
            text_content = re.sub(r"\s+", " ", text_content)
            # Normalize spacing around slashes (same as snippet cleaning)
            text_content = re.sub(r"\s+/\s*", "/", text_content)
            text_content = re.sub(r"\s*/\s+", "/", text_content)

            missing = []
            for item in snippets:
                snippet = item.get("snippet", "")
                if snippet and snippet != "PASTE_TEXT_FROM_END_OF_PAGE_HERE":
                    if snippet not in text_content:
                        missing.append(item["page"])

            results["missing_from_html"] = missing
            results["html_match_rate"] = (
                len(snippets) - len(missing) - placeholders
            ) / max(1, len(snippets) - placeholders)

        except Exception as e:
            print(f"⚠ Warning: Could not read HTML file: {e}")

    return results


def print_validation_results(results: Dict[str, Any]) -> None:
    """Print validation results in a readable format."""
    print("\n" + "=" * 50)
    print("VALIDATION RESULTS")
    print("=" * 50)
    print(f"Total snippets:      {results['total_snippets']}")
    print(f"Unique snippets:     {results['unique_snippets']}")
    print(f"Needs manual entry:  {results['placeholder_count']}")

    if results["duplicate_snippets"]:
        print(f"\n⚠ Duplicate snippets found: {len(results['duplicate_snippets'])}")
        print("  These may cause incorrect page marker placement:")
        for snippet, count in list(results["duplicate_snippets"].items())[:5]:
            print(f'  • "{snippet[:60]}..." (appears {count} times)')
        if len(results["duplicate_snippets"]) > 5:
            print(f"  ... and {len(results['duplicate_snippets']) - 5} more")

    if "missing_from_html" in results:
        print(f"\nHTML match rate:     {results['html_match_rate']:.1%}")
        if results["missing_from_html"]:
            print(
                f"⚠ Snippets not found in HTML: {len(results['missing_from_html'])} pages"
            )
            print(f"  Pages: {results['missing_from_html'][:10]}")
            if len(results["missing_from_html"]) > 10:
                print(f"  ... and {len(results['missing_from_html']) - 10} more")

    print("\n💡 Next steps:")
    if results["placeholder_count"] > 0:
        print("  1. Edit the JSON file and replace placeholder entries")
    if results["duplicate_snippets"]:
        print("  2. Update duplicate snippets to be more specific")
    if results.get("missing_from_html"):
        print("  3. Verify missing snippets or use different text")

    if (
        results["placeholder_count"] == 0
        and not results["duplicate_snippets"]
        and results.get("html_match_rate", 1.0) > 0.95
    ):
        print("  ✓ Ready to use! Run: rx-pagemarker mark <html> <json>")
