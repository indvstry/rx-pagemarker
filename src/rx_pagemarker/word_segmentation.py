"""Word segmentation for texts with missing word boundaries.

This module provides functionality to reconstruct word boundaries in text
where spaces are missing, using language-specific dictionaries and algorithms.
"""

import warnings
from typing import Dict, List, Optional, Set, Tuple
import unicodedata
import importlib.resources


class WordSegmenter:
    """Segments text without word boundaries using dictionary-based approach."""

    def __init__(self, language: str = "el"):
        """Initialize word segmenter with language dictionary.

        Args:
            language: Language code (currently supports 'el' for Greek)
        """
        self.language = language
        self.dictionary: Set[str] = set()
        self.max_word_length = 0
        self._load_dictionary()

    def _load_dictionary(self) -> None:
        """Load language dictionary."""
        if self.language == "el":
            self._load_greek_dictionary()
        else:
            raise ValueError(f"Unsupported language: {self.language}")

    def _load_greek_dictionary(self) -> None:
        """Load Greek word dictionary from frequency list.

        Loads from package resource data/greek_words.txt containing ~10k most
        frequent Greek words from Hermit Dave's frequency lists.
        Falls back to basic dictionary if file not found.
        """
        try:
            # Try to load from package resource
            if hasattr(importlib.resources, 'files'):
                # Python 3.9+
                data_path = importlib.resources.files('rx_pagemarker').joinpath('data/greek_words.txt')
                with data_path.open('r', encoding='utf-8') as f:
                    words = {line.strip() for line in f if line.strip()}
            else:
                # Python 3.8 fallback (pkg_resources for older importlib.resources)
                import pkg_resources
                resource_path = pkg_resources.resource_filename('rx_pagemarker', 'data/greek_words.txt')
                with open(resource_path, 'r', encoding='utf-8') as f:
                    words = {line.strip() for line in f if line.strip()}

            self.dictionary = self._expand_greek_morphology(words)
            self.max_word_length = max(len(w) for w in self.dictionary) if self.dictionary else 0
            self._using_fallback = False

        except (FileNotFoundError, ModuleNotFoundError, AttributeError, OSError, TypeError) as e:
            # Warn user about degraded functionality
            warnings.warn(
                f"Failed to load Greek dictionary ({e}). "
                f"Using minimal 50-word fallback - word segmentation accuracy significantly reduced. "
                f"Reinstall package to fix: pip install --force-reinstall rx-pagemarker",
                UserWarning,
                stacklevel=2
            )
            self._using_fallback = True
            # Fallback to basic hardcoded dictionary
            basic_greek_words = {
                # Common articles, conjunctions, prepositions
                "ο", "η", "το", "οι", "τα", "των", "του", "της", "τον", "την",
                "και", "ή", "αλλά", "με", "από", "για", "στο", "στη", "στον", "στην",
                "που", "ότι", "αυτό", "αυτή", "αυτός", "αυτά", "αυτές", "αυτοί",
                "είναι", "ήταν", "θα", "να", "δεν", "μη", "μην",
                "πως", "σε", "ως", "ενώ", "όταν", "αν", "όπως",

                # Common verbs
                "έχει", "έχουν", "είχε", "έχω", "έχεις",
                "γίνεται", "γίνονται", "έγινε", "γίνει",
                "μπορεί", "μπορούν", "μπορώ",
            }
            self.dictionary = self._expand_greek_morphology(basic_greek_words)
            self.max_word_length = max(len(w) for w in self.dictionary) if self.dictionary else 0

    def _expand_greek_morphology(self, base_words: Set[str]) -> Set[str]:
        """Expand base words with common Greek morphological variations."""
        expanded = set(base_words)

        # Add lowercase versions
        for word in list(expanded):
            expanded.add(word.lower())

        return expanded

    def segment_text(self, text: str, max_words: int = 15) -> Tuple[str, float]:
        """Segment text without word boundaries into words.

        Args:
            text: Text without proper word boundaries
            max_words: Maximum number of words to extract

        Returns:
            Tuple of (segmented_text, confidence_score)
        """
        text = text.strip()
        if not text:
            return "", 0.0

        # Normalize text
        text = self._normalize_text(text)

        # Try to segment
        words, score = self._segment_string(text)

        # Take last max_words
        if len(words) > max_words:
            words = words[-max_words:]

        segmented_text = " ".join(words)
        return segmented_text, score

    def _normalize_text(self, text: str) -> str:
        """Normalize Greek text for processing."""
        # Remove any existing spaces
        text = text.replace(" ", "")

        # Normalize Unicode (Greek has various accent forms)
        text = unicodedata.normalize('NFC', text)

        return text

    def _segment_string(self, text: str) -> Tuple[List[str], float]:
        """Segment a string into words using dynamic programming.

        Args:
            text: Text to segment

        Returns:
            Tuple of (word_list, confidence_score)
        """
        n = len(text)
        if n == 0:
            return [], 0.0

        # dp[i] = (best_score, best_segmentation) for text[0:i]
        dp: List[Optional[Tuple[float, List[str]]]] = [None] * (n + 1)
        dp[0] = (0.0, [])

        for i in range(1, n + 1):
            best_score = float('-inf')
            best_words: List[str] = []

            # Try all possible previous positions
            for j in range(max(0, i - self.max_word_length), i):
                if dp[j] is None:
                    continue

                word = text[j:i].lower()
                prev_score, prev_words = dp[j]

                # Score this segmentation
                if word in self.dictionary:
                    # Found a valid word
                    word_score = len(word) / 10.0  # Longer words score higher
                    total_score = prev_score + word_score
                else:
                    # Not in dictionary, penalize
                    total_score = prev_score - 1.0

                if total_score > best_score:
                    best_score = total_score
                    best_words = prev_words + [text[j:i]]

            dp[i] = (best_score, best_words)

        if dp[n] is None:
            # Fallback: return original text as single "word"
            return [text], 0.0

        final_score, final_words = dp[n]

        # Calculate confidence (0-1 scale)
        if not final_words:
            confidence = 0.0
        else:
            # Confidence based on how many words were found in dictionary
            words_in_dict = sum(1 for w in final_words if w.lower() in self.dictionary)
            confidence = words_in_dict / len(final_words)

        return final_words, confidence


def segment_snippet(text: str, language: str = "el", max_words: int = 15) -> Tuple[str, float]:
    """Segment a text snippet with missing word boundaries.

    Args:
        text: Text with missing spaces
        language: Language code
        max_words: Maximum number of words to return

    Returns:
        Tuple of (segmented_text, confidence_score)
    """
    segmenter = WordSegmenter(language=language)
    return segmenter.segment_text(text, max_words=max_words)
