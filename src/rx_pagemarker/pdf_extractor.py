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
        strategy: Literal["end_of_page", "bottom_visual", "beginning_of_page"] = "end_of_page",
        segment_words: bool = False,
        language: str = "el",
        match_html_path: Optional[Union[str, Path]] = None,
        exclude_patterns: Optional[List[str]] = None,
        use_default_excludes: bool = True,
        skip_footnotes: bool = False,
        min_font_size: float = 8.5,
        complete_words_html_path: Optional[Union[str, Path]] = None,
        context_words: int = 4,
        two_column: bool = False,
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
                - "beginning_of_page": First N words of extracted text
            segment_words: Enable word boundary reconstruction for PDFs with missing spaces
            language: Language code for word segmentation (e.g., 'el' for Greek)
            match_html_path: Optional path to HTML file for matching-based correction
                (includes fuzzy matching - slow but accurate)
            exclude_patterns: Regex patterns to exclude from text (e.g., InDesign sluglines)
            use_default_excludes: Whether to use default exclude patterns for common
                production metadata (InDesign sluglines, timestamps)
            skip_footnotes: Whether to skip footnote text (smaller font at bottom of page)
            min_font_size: Minimum font size to include (smaller text treated as footnotes)
            complete_words_html_path: Optional path to HTML file for word completion only
                (fast - completes partial words at end of snippets using HTML reference)
            context_words: Number of words to capture before/after snippet for disambiguation
                (default: 4, set to 0 to disable context extraction)
            two_column: Enable two-column layout extraction. When True, extracts text only
                from the body columns area (top ~75% of page), skipping the footnote zone
                at the bottom. Text is extracted from the end of the rightmost column.

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
        self.context_words = context_words
        self.two_column = two_column

        # Build list of exclude patterns
        self.exclude_patterns: List[re.Pattern[str]] = []
        if use_default_excludes:
            for pattern in DEFAULT_EXCLUDE_PATTERNS:
                self.exclude_patterns.append(re.compile(pattern, re.IGNORECASE))
        if exclude_patterns:
            for pattern in exclude_patterns:
                self.exclude_patterns.append(re.compile(pattern, re.IGNORECASE))

        # Determine HTML path for word completion (prefer complete_words_html_path if both set)
        self.complete_words_html_path = (
            Path(complete_words_html_path) if complete_words_html_path else None
        )
        word_completion_path = self.complete_words_html_path or self.match_html_path

        # Load HTML content for word completion if path provided
        self.html_text: Optional[str] = None
        if word_completion_path:
            try:
                with open(word_completion_path, "r", encoding="utf-8") as f:
                    html_content = f.read()
                # Remove footnotes section before stripping tags (InDesign exports)
                # Footnotes appear in <ol class="_idFootAndEndNoteOLAttrs"> containers
                html_content = re.sub(
                    r'<ol[^>]*class="[^"]*_idFootAndEndNoteOLAttrs[^"]*"[^>]*>.*?</ol>',
                    '',
                    html_content,
                    flags=re.DOTALL | re.IGNORECASE
                )
                # Strip HTML tags for text matching
                self.html_text = re.sub(r"<[^>]+>", "", html_content)
                self.html_text = re.sub(r"\s+", " ", self.html_text)
                print(f"Loaded HTML for word completion: {word_completion_path.name} (footnotes excluded)")
            except Exception as e:
                print(f"⚠ Warning: Could not load HTML for word completion: {e}")

        # Initialize HTML matcher if match_html_path provided (for fuzzy matching - slow)
        self.html_matcher: Optional["HTMLMatcher"] = None
        if self.match_html_path:
            try:
                from .html_matcher import HTMLMatcher

                self.html_matcher = HTMLMatcher(self.match_html_path)
                print("Enabled fuzzy HTML matching (this may be slow for large files)")
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
            "context_extracted": 0,
            "context_partial": 0,
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

    def _trim_to_boundary(self, snippet: str) -> str:
        """Trim snippet to end at a natural boundary if possible.

        Looks for sentence-ending punctuation (. ; :) and trims to that point
        to avoid placing markers in the middle of phrases.

        Args:
            snippet: Raw snippet text

        Returns:
            Snippet trimmed to natural boundary, or original if no boundary found
        """
        # Find the last natural boundary (period, semicolon, colon followed by space or end)
        # Look for these patterns in reverse order
        boundary_chars = [". ", "; ", ": ", "· "]  # Include Greek semicolon

        best_pos = -1
        for boundary in boundary_chars:
            pos = snippet.rfind(boundary)
            if pos > best_pos and pos > len(snippet) // 3:  # Must keep at least 1/3
                best_pos = pos

        # Also check for end-of-snippet punctuation
        if snippet.rstrip().endswith((".", ";", ":", "·")):
            return snippet.rstrip()

        if best_pos > 0:
            # Include the punctuation but not the space after
            return snippet[: best_pos + 1].rstrip()

        return snippet

    def _trim_to_start_boundary(self, snippet: str) -> str:
        """Trim snippet to start at a natural boundary if possible.

        For beginning_of_page strategy, only trims if snippet starts with
        punctuation or whitespace (indicating mid-sentence extraction).
        Preserves snippets that start with letters (even lowercase).

        Args:
            snippet: Raw snippet text

        Returns:
            Snippet trimmed to start at natural boundary, or original if no boundary found
        """
        if not snippet:
            return snippet

        # If snippet starts with a letter (uppercase or lowercase), keep it as-is
        # This preserves Greek text that often starts with lowercase
        first_char = snippet[0]
        if first_char.isalpha():
            return snippet

        # Only trim if snippet starts with punctuation/whitespace
        # Look for a letter after the initial non-letter characters
        match = re.search(r'[A-Za-zΑ-Ωα-ωά-ώ]', snippet)
        if match:
            return snippet[match.start():]

        return snippet

    def _clean_snippet(self, snippet: str, html_text: Optional[str] = None) -> str:
        """Clean up snippet for better matching.

        Completes trailing hyphenated words and normalizes spacing for better HTML matching.
        If HTML text is provided, attempts to complete partial words at the end.

        Args:
            snippet: Raw snippet text
            html_text: Optional HTML text content for word completion

        Returns:
            Cleaned snippet
        """
        cleaned = snippet.strip()

        # Normalize spacing around slashes and punctuation
        cleaned = re.sub(r"\s+/\s*", "/", cleaned)  # "word / word" -> "word/word"
        cleaned = re.sub(r"\s*/\s+", "/", cleaned)  # Also handle "word/ word"

        # Try to complete partial/hyphenated words at the end if HTML is available
        if html_text and cleaned:
            cleaned = self._complete_partial_word(cleaned, html_text)

            # Only run context correction if snippet doesn't match HTML as-is
            # (indicates merged words that need fixing)
            if cleaned not in html_text:
                corrected, was_corrected = self._correct_snippet_from_context(
                    cleaned, html_text, target_words=self.snippet_words
                )
                if was_corrected:
                    cleaned = corrected

        return cleaned

    def _clean_snippet_beginning(self, snippet: str, html_text: Optional[str] = None) -> str:
        """Clean up beginning-of-page snippet for better matching.

        Completes partial first word and normalizes spacing for better HTML matching.
        If HTML text is provided, attempts to complete partial words at the beginning.

        Note: Context correction is skipped for beginning_of_page as it's designed
        for end_of_page snippets and would pull wrong context direction.

        Args:
            snippet: Raw snippet text
            html_text: Optional HTML text content for word completion

        Returns:
            Cleaned snippet
        """
        cleaned = snippet.strip()

        # Normalize spacing around slashes and punctuation
        cleaned = re.sub(r"\s+/\s*", "/", cleaned)
        cleaned = re.sub(r"\s*/\s+", "/", cleaned)

        # Try to complete partial words at the beginning if HTML is available
        if html_text and cleaned:
            cleaned = self._complete_first_word(cleaned, html_text)
            # Note: Skip context correction for beginning_of_page - it extracts
            # in wrong direction (designed for end_of_page)

        return cleaned

    def _extract_context(
        self, page_text: str, snippet: str, num_words: int = 4
    ) -> tuple[str, str]:
        """Extract context words before and after snippet in page text.

        Used for disambiguating duplicate snippets during HTML matching.
        When the same snippet text appears multiple times in the document,
        the context helps identify which occurrence is correct.

        Args:
            page_text: Full text of the page
            snippet: The extracted snippet
            num_words: Number of context words to capture (default: 4)

        Returns:
            Tuple of (context_before, context_after) as space-separated words.
            Empty strings if context couldn't be extracted.
        """
        if num_words <= 0 or not snippet or not page_text:
            return ("", "")

        # Find snippet in page text
        snippet_pos = page_text.find(snippet)
        if snippet_pos == -1:
            return ("", "")

        # Extract text before and after snippet
        text_before = page_text[:snippet_pos]
        text_after = page_text[snippet_pos + len(snippet) :]

        # Get last N words before snippet
        words_before = text_before.split()
        context_before = " ".join(words_before[-num_words:]) if words_before else ""

        # Get first N words after snippet
        words_after = text_after.split()
        context_after = " ".join(words_after[:num_words]) if words_after else ""

        return (context_before, context_after)

    def _complete_first_word(self, snippet: str, html_text: str) -> str:
        """Complete partial word at beginning of snippet by finding full word in HTML.

        If snippet starts with incomplete word like "χυση" (from "σύγχυση"), finds the
        complete word in HTML using context (words that follow) to find the right occurrence.

        Args:
            snippet: Snippet potentially starting with partial word
            html_text: HTML text to search for complete word

        Returns:
            Snippet with first word completed if possible
        """
        words = snippet.split()
        if not words:
            return snippet

        first_word = words[0]

        # Check if first word exists in HTML as a whole word (not substring)
        word_pattern = r'(?:^|[\s])' + re.escape(first_word) + r'(?:[\s.,;:!?\)]|$)'
        if re.search(word_pattern, html_text):
            return snippet

        # Use context (following words) to find the correct completion
        # Build context pattern from next 2-3 words after the incomplete word
        if len(words) >= 2:
            # Try with 2 words of context
            context = " ".join(words[1:3])  # words after first
            # Pattern: (prefix)first_word + context
            context_pattern = r'(\w+)' + re.escape(first_word) + r'\s+' + re.escape(context)
            match = re.search(context_pattern, html_text, re.UNICODE)
            if match:
                complete_word = match.group(1) + first_word
                words[0] = complete_word
                return " ".join(words)

        # Fallback: search without context (first occurrence)
        # Pattern: any word ending with our partial word
        pattern = r'(\w+)' + re.escape(first_word) + r'(?:[\s.,;:!?\)]|$)'
        match = re.search(pattern, html_text, re.UNICODE)

        if match:
            complete_word = match.group(1) + first_word
            words[0] = complete_word
            return " ".join(words)

        # Return snippet as-is if no completion found
        return snippet

    def _complete_partial_word(self, snippet: str, html_text: str) -> str:
        """Complete partial word at end of snippet by finding full word in HTML.

        If snippet ends with incomplete word like "σύγ" or "λό-", finds the complete
        word "σύγχυση" or "λόγω" in HTML using context to find the right occurrence.

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

        # Handle hyphenated word endings like "λό-" -> search for "λό"
        word_stem = last_word.rstrip("-")
        is_hyphenated = last_word.endswith("-")

        # Check if last word exists in HTML as-is (as whole word, not substring)
        if not is_hyphenated:
            word_pattern = r'(?:^|[\s])' + re.escape(last_word) + r'(?:[\s.,;:!?\)]|$)'
            if re.search(word_pattern, html_text):
                return snippet

        # Use context (previous words) to find the correct completion
        # Build context pattern from last 2-3 words before the incomplete word
        if len(words) >= 2:
            # Try with 2 words of context
            context = " ".join(words[-2:-1])  # word before last
            context_pattern = re.escape(context) + r'\s+' + re.escape(word_stem) + r'(\w+)'
            match = re.search(context_pattern, html_text, re.UNICODE)
            if match:
                complete_word = word_stem + match.group(1)
                words[-1] = complete_word
                return " ".join(words)

        # Fallback: search without context (first occurrence)
        pattern = r'(?:^|[\s])' + re.escape(word_stem) + r'(\w+)'
        match = re.search(pattern, html_text, re.UNICODE)

        if match:
            complete_word = word_stem + match.group(1)
            words[-1] = complete_word
            return " ".join(words)

        # Completion failed - keep stem and add FIXME marker for manual review
        if is_hyphenated:
            words[-1] = word_stem + "<!-- FIXME -->"
            return " ".join(words)

        # Return snippet as-is if no completion found
        return snippet

    def _correct_snippet_from_context(
        self, snippet: str, html_text: str, target_words: int = 10
    ) -> tuple[str, bool]:
        """Correct snippet by finding anchor words in HTML and extracting context.

        When PDF extraction produces merged words (e.g., "ουσιαστιστην" instead of
        "ουσιαστικού στην"), this method finds sequences of correctly-extracted words
        in the HTML and uses them as anchors to extract the correct surrounding text.

        Args:
            snippet: Potentially corrupted snippet from PDF
            html_text: Clean HTML text to search in
            target_words: Number of words to extract from HTML

        Returns:
            Tuple of (corrected_snippet, was_corrected)
        """
        words = snippet.split()
        if len(words) < 3:
            return snippet, False

        # Try to find anchor sequences of 3-4 consecutive words
        for anchor_len in [4, 3]:
            for i in range(len(words) - anchor_len + 1):
                anchor = " ".join(words[i : i + anchor_len])

                # Search for this anchor in HTML (use find to get FIRST occurrence,
                # since pages are processed in order)
                pos = html_text.find(anchor)
                if pos == -1:
                    continue

                # Found anchor! Extract surrounding context
                # Find word boundaries around the match
                start = pos
                end = pos + len(anchor)

                # Expand backwards to get more words
                words_before = 0
                while start > 0 and words_before < (target_words - anchor_len) // 2:
                    start -= 1
                    if html_text[start] == " ":
                        words_before += 1

                # Expand forwards to get more words
                words_after = 0
                while end < len(html_text) and words_after < (
                    target_words - anchor_len - words_before
                ):
                    if html_text[end] == " ":
                        words_after += 1
                    end += 1

                # Extract and clean the corrected snippet
                corrected = html_text[start:end].strip()
                corrected_words = corrected.split()

                # Take last target_words words (end of page)
                if len(corrected_words) > target_words:
                    corrected = " ".join(corrected_words[-target_words:])

                return corrected, True

        return snippet, False

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

        # Clean up spacing around punctuation (caused by filtered footnote numbers)
        # " ." -> "." and " ," -> "," etc.
        text = re.sub(r'\s+([.,;:!?·])', r'\1', text)

        return text

    def _extract_two_column_body_pymupdf(
        self, page: "fitz.Page", footnote_zone_ratio: float = 0.25
    ) -> str:
        """Extract body text from two-column layout, excluding footnote zone.

        For two-column PDFs, the footnote zone is at the very bottom of the page
        spanning both columns. This method extracts text only from the body area
        above the footnotes, sorted by reading order (top-to-bottom, left-to-right
        within each column).

        Args:
            page: PyMuPDF page object
            footnote_zone_ratio: Fraction of page height to consider as footnote zone
                (default: 0.25 = bottom 25%)

        Returns:
            Body text with footnotes excluded, in reading order
        """
        page_height = page.rect.height
        page_width = page.rect.width
        footnote_cutoff_y = page_height * (1 - footnote_zone_ratio)

        # Get detailed text with position information
        blocks = page.get_text("dict")["blocks"]

        body_spans = []
        for block in blocks:
            if "lines" not in block:
                continue
            for line in block["lines"]:
                for span in line["spans"]:
                    bbox = span["bbox"]  # (x0, y0, x1, y1)
                    y_bottom = bbox[3]
                    x_center = (bbox[0] + bbox[2]) / 2

                    # Skip spans in the footnote zone (bottom of page)
                    if y_bottom > footnote_cutoff_y:
                        continue

                    # Also filter by font size if skip_footnotes is enabled
                    if self.skip_footnotes and span["size"] < self.min_font_size:
                        continue

                    # Determine column (left or right)
                    column = 0 if x_center < page_width / 2 else 1

                    body_spans.append({
                        "y": y_bottom,
                        "x": bbox[0],
                        "column": column,
                        "text": span["text"]
                    })

        # Sort by reading order: column first, then y position, then x position
        # This gives us left column top-to-bottom, then right column top-to-bottom
        body_spans.sort(key=lambda s: (s["column"], s["y"], s["x"]))

        # Join text
        text = " ".join(s["text"] for s in body_spans)

        # Clean up spacing around punctuation
        text = re.sub(r'\s+([.,;:!?·])', r'\1', text)

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

                # First pass: extract all page texts
                page_texts = []
                for page_num in range(len(doc)):
                    page = doc[page_num]
                    if self.two_column:
                        # Two-column layout: extract from body columns only, skip footnote zone
                        text = self._extract_two_column_body_pymupdf(page)
                    elif self.skip_footnotes:
                        text = self._extract_body_text_pymupdf(page)
                    else:
                        text = page.get_text()
                    text = self._filter_production_metadata(text)
                    text = self._dehyphenate(text)
                    page_texts.append(text)

                # Second pass: extract snippets with context from next page
                for page_num in range(len(doc)):
                    if (page_num + 1) % 50 == 0:
                        print(f"  Processing page {page_num + 1}/{len(doc)}...")

                    current_text = page_texts[page_num]
                    next_text = page_texts[page_num + 1] if page_num + 1 < len(doc) else ""

                    snippet = self._extract_snippet_with_context(
                        current_text, next_text, page_num + 1
                    )
                    snippets.append(snippet)

        except Exception as e:
            raise PDFExtractionError(f"Error reading PDF with PyMuPDF: {e}") from e

        return snippets

    def _extract_snippet_with_context(
        self, current_text: str, next_text: str, page_num: int
    ) -> Dict[str, Any]:
        """Extract snippet from current page with optional context for disambiguation.

        Args:
            current_text: Text from current page
            next_text: Text from next page (unused, kept for API compatibility)
            page_num: Page number

        Returns:
            Dictionary with page number, snippet, and optional context_before/context_after
        """
        current_words = current_text.split()

        if len(current_words) < self.min_words:
            self.stats["insufficient_text"] += 1
            placeholder = (
                "PASTE_TEXT_FROM_BEGINNING_OF_PAGE_HERE"
                if self.strategy == "beginning_of_page"
                else "PASTE_TEXT_FROM_END_OF_PAGE_HERE"
            )
            return {
                "page": page_num,
                "snippet": placeholder,
                "note": f"Insufficient text (found {len(current_words)} words)",
            }

        # Get words based on strategy
        if self.strategy == "beginning_of_page":
            snippet = " ".join(current_words[:self.snippet_words])
        else:
            # end_of_page (default) and bottom_visual
            snippet = " ".join(current_words[-self.snippet_words:])

        # Store original snippet before cleaning for context extraction
        original_snippet = snippet

        # Trim to natural boundary and complete partial words based on strategy
        if self.strategy == "beginning_of_page":
            snippet = self._trim_to_start_boundary(snippet)
            if self.html_text:
                snippet = self._clean_snippet_beginning(snippet, self.html_text)
        else:
            snippet = self._trim_to_boundary(snippet)
            if self.html_text:
                snippet = self._clean_snippet(snippet, self.html_text)

        self.stats["successful"] += 1

        result: Dict[str, Any] = {
            "page": page_num,
            "snippet": snippet,
        }

        # Extract context for disambiguation if enabled
        if self.context_words > 0:
            # Use the original snippet (before HTML correction) to find position in page text
            context_before, context_after = self._extract_context(
                current_text, original_snippet, self.context_words
            )

            # Only include context fields if at least one has content
            if context_before or context_after:
                result["context_before"] = context_before
                result["context_after"] = context_after

                # Track stats
                if context_before and context_after:
                    self.stats["context_extracted"] += 1
                else:
                    self.stats["context_partial"] += 1
            else:
                # Context extraction failed - snippet not found in original page text
                # This can happen if the snippet was modified during cleaning/correction
                self.stats["context_failed"] = self.stats.get("context_failed", 0) + 1

        return result

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

            # Trim to natural boundary (period, semicolon) if possible
            snippet = self._trim_to_boundary(snippet)

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

        except (KeyboardInterrupt, SystemExit, MemoryError):
            # Don't suppress critical system exceptions
            raise
        except Exception as e:
            self.stats["failed"] += 1
            placeholder = (
                "PASTE_TEXT_FROM_BEGINNING_OF_PAGE_HERE"
                if self.strategy == "beginning_of_page"
                else "PASTE_TEXT_FROM_END_OF_PAGE_HERE"
            )
            return {
                "page": page_num,
                "snippet": placeholder,
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

    def _extract_two_column_body_pdfplumber(
        self, page: "pdfplumber.page.Page", footnote_zone_ratio: float = 0.25
    ) -> str:
        """Extract body text from two-column layout using pdfplumber.

        Args:
            page: pdfplumber page object
            footnote_zone_ratio: Fraction of page height to consider as footnote zone

        Returns:
            Body text with footnotes excluded, in reading order
        """
        page_height = page.height
        page_width = page.width
        footnote_cutoff_y = page_height * (1 - footnote_zone_ratio)

        words = page.extract_words()
        if not words:
            return ""

        body_words = []
        for word in words:
            y_bottom = word["bottom"]
            x_center = (word["x0"] + word["x1"]) / 2

            # Skip words in the footnote zone
            if y_bottom > footnote_cutoff_y:
                continue

            # Determine column
            column = 0 if x_center < page_width / 2 else 1

            body_words.append({
                "y": y_bottom,
                "x": word["x0"],
                "column": column,
                "text": word["text"]
            })

        # Sort by reading order: column first, then y position, then x position
        body_words.sort(key=lambda w: (w["column"], w["y"], w["x"]))

        text = " ".join(w["text"] for w in body_words)
        text = re.sub(r'\s+([.,;:!?·])', r'\1', text)

        return text

    def _extract_page_snippet_pdfplumber(
        self, page: "pdfplumber.page.Page", page_num: int
    ) -> Dict[str, Any]:
        """Extract snippet from a single page using pdfplumber."""
        try:
            if self.two_column:
                # Two-column layout: extract from body columns only
                text = self._extract_two_column_body_pdfplumber(page)
            elif self.strategy == "bottom_visual":
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
            else:  # end_of_page or beginning_of_page
                text = page.extract_text() or ""

            # Filter out production metadata (InDesign sluglines, etc.)
            text = self._filter_production_metadata(text)

            # Rejoin hyphenated words split across lines
            text = self._dehyphenate(text)

            # Extract snippet
            words = text.split()

            if len(words) < self.min_words:
                self.stats["insufficient_text"] += 1
                placeholder = (
                    "PASTE_TEXT_FROM_BEGINNING_OF_PAGE_HERE"
                    if self.strategy == "beginning_of_page"
                    else "PASTE_TEXT_FROM_END_OF_PAGE_HERE"
                )
                return {
                    "page": page_num,
                    "snippet": placeholder,
                    "note": f"Insufficient text (found {len(words)} words, need {self.min_words})",
                }

            # Select words based on strategy
            if self.strategy == "beginning_of_page":
                snippet = " ".join(words[:self.snippet_words])
            else:
                snippet = " ".join(words[-self.snippet_words:])

            # Trim to natural boundary and clean based on strategy
            if self.strategy == "beginning_of_page":
                snippet = self._trim_to_start_boundary(snippet)
                snippet = self._clean_snippet_beginning(snippet, self.html_text)
            else:
                snippet = self._trim_to_boundary(snippet)
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

        except (KeyboardInterrupt, SystemExit, MemoryError):
            # Don't suppress critical system exceptions
            raise
        except Exception as e:
            self.stats["failed"] += 1
            placeholder = (
                "PASTE_TEXT_FROM_BEGINNING_OF_PAGE_HERE"
                if self.strategy == "beginning_of_page"
                else "PASTE_TEXT_FROM_END_OF_PAGE_HERE"
            )
            return {
                "page": page_num,
                "snippet": placeholder,
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
        print(f"Backend: {self.backend}")
        if self.two_column:
            print("Layout: Two-column (footnote zone excluded)")
        print()

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

        # Show context extraction stats if context was enabled
        context_failed = self.stats.get("context_failed", 0)
        context_total = self.stats["context_extracted"] + self.stats["context_partial"]
        if context_total > 0 or context_failed > 0 or self.context_words > 0:
            print(f"\nContext extraction ({self.context_words} words):")
            print(f"  Full context:      {self.stats['context_extracted']}")
            print(f"  Partial context:   {self.stats['context_partial']}")
            if context_failed > 0:
                print(f"  Failed:            {context_failed} ⚠")

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

    # Count context coverage
    context_full = sum(
        1 for s in snippets
        if s.get("context_before") and s.get("context_after")
    )
    context_partial = sum(
        1 for s in snippets
        if (s.get("context_before") or s.get("context_after"))
        and not (s.get("context_before") and s.get("context_after"))
    )
    context_none = len(snippets) - context_full - context_partial

    results = {
        "total_snippets": len(snippets),
        "unique_snippets": len(set(snippet_texts)),
        "duplicate_snippets": duplicates,
        "placeholder_count": placeholders,
        "context_full": context_full,
        "context_partial": context_partial,
        "context_none": context_none,
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

    # Show context coverage if present
    if results.get("context_full", 0) > 0 or results.get("context_partial", 0) > 0:
        print(f"\nContext coverage:")
        print(f"  Full context:      {results['context_full']}")
        print(f"  Partial context:   {results['context_partial']}")
        print(f"  No context:        {results['context_none']}")

    if results["duplicate_snippets"]:
        print(f"\n⚠ Duplicate snippets found: {len(results['duplicate_snippets'])}")
        if results.get("context_full", 0) > 0:
            print("  Context matching will help disambiguate these duplicates.")
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
