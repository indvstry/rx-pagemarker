"""HTML-based text matching for PDF snippet correction.

This module provides functionality to match PDF snippets (with missing spaces)
against clean HTML text to reconstruct correct word boundaries.
"""

import re
import unicodedata
from pathlib import Path
from typing import Dict, Optional, Tuple, Union

try:
    from rapidfuzz import fuzz, process

    HAS_RAPIDFUZZ = True
except ImportError:
    HAS_RAPIDFUZZ = False


class HTMLMatcherError(Exception):
    """Base exception for HTML matching errors."""

    pass


class MissingDependencyError(HTMLMatcherError):
    """Raised when rapidfuzz is not installed."""

    pass


class HTMLNotFoundError(HTMLMatcherError):
    """Raised when HTML file is not found."""

    pass


class HTMLMatcher:
    """Match PDF snippets against HTML text to reconstruct word boundaries.

    Uses fuzzy matching to find PDF text (without spaces) in HTML text (with
    correct spacing), then returns the HTML version with proper word boundaries.
    """

    def __init__(self, html_path: Union[str, Path]):
        """Initialize HTML matcher.

        Args:
            html_path: Path to HTML file with correct text

        Raises:
            HTMLNotFoundError: If HTML file doesn't exist
            MissingDependencyError: If rapidfuzz is not installed
        """
        if not HAS_RAPIDFUZZ:
            raise MissingDependencyError(
                "rapidfuzz not installed. Install with: pip install rapidfuzz"
            )

        self.html_path = Path(html_path)
        if not self.html_path.exists():
            raise HTMLNotFoundError(f"HTML file not found: {self.html_path}")

        self.html_text = self._load_html()
        self.html_no_spaces = self._normalize_text(self.html_text.replace(" ", ""))

        # Common PDF footer/header patterns to remove
        self.noise_patterns = [
            r"\d{2}_Layout\s+\d+\s+\d{1,2}/\d{1,2}/\d{2,4}\s+\d{1,2}:\d{2}\s+[AP]M\s+Page\s+\d+",  # Full layout marker
            r"\d{2}_Layout\s+\d+.*?Page\s+\d+",  # Layout marker variations
            r"Page\s+\d+",  # Simple page numbers
            r"\d{1,2}/\d{1,2}/\d{2,4}\s+\d{1,2}:\d{2}\s+[AP]M",  # Timestamps
        ]

    def _load_html(self) -> str:
        """Load and extract text from HTML file."""
        try:
            with open(self.html_path, "r", encoding="utf-8") as f:
                html_content = f.read()

            # Simple HTML tag removal (could use BeautifulSoup for complex HTML)
            text = re.sub(r"<[^>]+>", " ", html_content)

            # Clean up whitespace
            text = re.sub(r"\s+", " ", text)

            return text.strip()

        except Exception as e:
            raise HTMLMatcherError(f"Error loading HTML: {e}") from e

    def _normalize_text(self, text: str) -> str:
        """Normalize text for matching (Unicode normalization, lowercase)."""
        # Normalize Unicode
        text = unicodedata.normalize("NFC", text)

        # Convert to lowercase for case-insensitive matching
        text = text.lower()

        # Remove common punctuation that might differ
        text = text.replace("-", "")
        text = text.replace("—", "")
        text = text.replace("–", "")

        return text

    def clean_pdf_snippet(self, snippet: str) -> str:
        """Remove PDF-specific noise (page numbers, footers, layout markers).

        Args:
            snippet: Raw PDF snippet text

        Returns:
            Cleaned snippet with noise removed
        """
        cleaned = snippet

        # Apply all noise patterns
        for pattern in self.noise_patterns:
            cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)

        # Remove extra whitespace
        cleaned = re.sub(r"\s+", " ", cleaned)

        return cleaned.strip()

    def find_match(
        self, pdf_snippet: str, min_confidence: float = 0.6
    ) -> Dict[str, any]:
        """Find best matching text in HTML for the given PDF snippet.

        Args:
            pdf_snippet: Raw PDF snippet (possibly with noise and no spaces)
            min_confidence: Minimum confidence threshold (0-1)

        Returns:
            Dictionary with:
                - matched_text: Best matching text from HTML (with spaces)
                - confidence: Match confidence score (0-1)
                - cleaned_snippet: PDF snippet after noise removal
        """
        # Clean PDF snippet
        cleaned = self.clean_pdf_snippet(pdf_snippet)
        cleaned_normalized = self._normalize_text(cleaned.replace(" ", ""))

        if not cleaned_normalized:
            return {
                "matched_text": "",
                "confidence": 0.0,
                "cleaned_snippet": cleaned,
            }

        # Find best match using sliding window approach
        best_match, best_score = self._find_best_substring_match(cleaned_normalized)

        # Convert score to 0-1 confidence
        confidence = best_score / 100.0

        if confidence < min_confidence:
            return {
                "matched_text": cleaned,  # Fall back to cleaned PDF text
                "confidence": confidence,
                "cleaned_snippet": cleaned,
            }

        return {
            "matched_text": best_match,
            "confidence": confidence,
            "cleaned_snippet": cleaned,
        }

    def _find_best_substring_match(
        self, query_no_spaces: str, window_ratio: float = 1.5
    ) -> Tuple[str, float]:
        """Find best matching substring in HTML using sliding window.

        Args:
            query_no_spaces: Query text without spaces
            window_ratio: How much larger the search window should be (ratio)

        Returns:
            Tuple of (best_match_text_with_spaces, confidence_score)
        """
        query_len = len(query_no_spaces)
        window_size = int(query_len * window_ratio)

        # Split HTML into words for reconstruction
        html_words = self.html_text.split()

        best_score = 0
        best_match = ""

        # Try different window sizes
        for num_words in range(max(1, len(query_no_spaces) // 20), len(html_words)):
            for i in range(len(html_words) - num_words + 1):
                # Get window of words
                window_words = html_words[i : i + num_words]
                window_text = " ".join(window_words)
                window_normalized = self._normalize_text(window_text.replace(" ", ""))

                # Skip if length difference is too large
                if abs(len(window_normalized) - query_len) > query_len * 0.5:
                    continue

                # Calculate similarity
                score = fuzz.ratio(query_no_spaces, window_normalized)

                if score > best_score:
                    best_score = score
                    best_match = window_text

                # Early exit if we found excellent match
                if score > 95:
                    return best_match, score

        return best_match, best_score


def match_snippet(
    pdf_snippet: str, html_path: Union[str, Path], min_confidence: float = 0.6
) -> Tuple[str, float]:
    """Match a PDF snippet against HTML text (convenience function).

    Args:
        pdf_snippet: PDF snippet to match
        html_path: Path to HTML file
        min_confidence: Minimum confidence threshold

    Returns:
        Tuple of (matched_text, confidence_score)
    """
    matcher = HTMLMatcher(html_path)
    result = matcher.find_match(pdf_snippet, min_confidence)
    return result["matched_text"], result["confidence"]
