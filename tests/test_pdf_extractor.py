"""Tests for PDF extraction functionality."""

import json
from pathlib import Path
from unittest.mock import MagicMock, Mock, mock_open, patch

import pytest

from rx_pagemarker.pdf_extractor import (
    InvalidParameterError,
    MissingDependencyError,
    PDFExtractionError,
    PDFExtractor,
    PDFNotFoundError,
    print_validation_results,
    validate_snippets,
)


class TestPDFExtractorInit:
    """Test PDFExtractor initialization and validation."""

    def test_init_with_valid_parameters(self):
        """Test initialization with valid parameters."""
        extractor = PDFExtractor(
            pdf_path="test.pdf",
            backend="auto",
            snippet_words=10,
            min_words=3,
            strategy="end_of_page",
        )
        assert extractor.pdf_path == Path("test.pdf")
        assert extractor.snippet_words == 10
        assert extractor.min_words == 3
        assert extractor.strategy == "end_of_page"

    def test_init_with_invalid_snippet_words_zero(self):
        """Test that snippet_words < 1 raises InvalidParameterError."""
        with pytest.raises(InvalidParameterError, match="snippet_words must be >= 1"):
            PDFExtractor("test.pdf", snippet_words=0)

    def test_init_with_invalid_snippet_words_negative(self):
        """Test that negative snippet_words raises InvalidParameterError."""
        with pytest.raises(InvalidParameterError, match="snippet_words must be >= 1"):
            PDFExtractor("test.pdf", snippet_words=-5)

    def test_init_with_invalid_min_words(self):
        """Test that min_words < 1 raises InvalidParameterError."""
        with pytest.raises(InvalidParameterError, match="min_words must be >= 1"):
            PDFExtractor("test.pdf", min_words=0)

    def test_init_with_snippet_words_too_large(self):
        """Test that snippet_words > 1000 raises InvalidParameterError."""
        with pytest.raises(InvalidParameterError, match="snippet_words must be <= 1000"):
            PDFExtractor("test.pdf", snippet_words=1001)

    @patch("rx_pagemarker.pdf_extractor.HAS_PYMUPDF", False)
    @patch("rx_pagemarker.pdf_extractor.HAS_PDFPLUMBER", False)
    def test_init_with_no_backends_available(self):
        """Test that MissingDependencyError is raised when no backends available."""
        with pytest.raises(
            MissingDependencyError, match="Neither PyMuPDF nor pdfplumber"
        ):
            PDFExtractor("test.pdf", backend="auto")

    @patch("rx_pagemarker.pdf_extractor.HAS_PYMUPDF", False)
    def test_init_with_missing_pymupdf(self):
        """Test that MissingDependencyError is raised when PyMuPDF requested but not available."""
        with pytest.raises(MissingDependencyError, match="PyMuPDF not installed"):
            PDFExtractor("test.pdf", backend="pymupdf")

    @patch("rx_pagemarker.pdf_extractor.HAS_PDFPLUMBER", False)
    def test_init_with_missing_pdfplumber(self):
        """Test that MissingDependencyError is raised when pdfplumber requested but not available."""
        with pytest.raises(MissingDependencyError, match="pdfplumber not installed"):
            PDFExtractor("test.pdf", backend="pdfplumber")

    @patch("rx_pagemarker.pdf_extractor.HAS_PYMUPDF", True)
    @patch("rx_pagemarker.pdf_extractor.HAS_PDFPLUMBER", False)
    def test_backend_auto_selects_pymupdf(self):
        """Test that 'auto' backend selects PyMuPDF when available."""
        extractor = PDFExtractor("test.pdf", backend="auto")
        assert extractor.backend == "pymupdf"

    @patch("rx_pagemarker.pdf_extractor.HAS_PYMUPDF", False)
    @patch("rx_pagemarker.pdf_extractor.HAS_PDFPLUMBER", True)
    def test_backend_auto_fallback_to_pdfplumber(self):
        """Test that 'auto' backend falls back to pdfplumber."""
        extractor = PDFExtractor("test.pdf", backend="auto")
        assert extractor.backend == "pdfplumber"


class TestPDFExtractorExtract:
    """Test PDF extraction methods."""

    def test_extract_with_nonexistent_file(self, tmp_path):
        """Test that PDFNotFoundError is raised for nonexistent PDF."""
        pdf_path = tmp_path / "nonexistent.pdf"
        extractor = PDFExtractor(pdf_path)

        with pytest.raises(PDFNotFoundError, match="PDF file not found"):
            extractor.extract()

    @patch("rx_pagemarker.pdf_extractor.HAS_PYMUPDF", True)
    @patch("rx_pagemarker.pdf_extractor.fitz")
    def test_extract_with_pymupdf_success(self, mock_fitz, tmp_path):
        """Test successful extraction using PyMuPDF."""
        # Create a real PDF file for path.exists() check
        pdf_path = tmp_path / "test.pdf"
        pdf_path.write_bytes(b"fake pdf content")

        # Mock PyMuPDF document and page
        mock_page = MagicMock()
        mock_page.get_text.return_value = "This is sample text from the page."

        mock_doc = MagicMock()
        mock_doc.__len__.return_value = 1
        mock_doc.__getitem__.return_value = mock_page  # Support doc[page_num]
        mock_doc.__enter__.return_value = mock_doc
        mock_doc.__exit__.return_value = None

        mock_fitz.open.return_value = mock_doc

        extractor = PDFExtractor(pdf_path, backend="pymupdf")
        snippets = extractor.extract()

        assert len(snippets) == 1
        assert snippets[0]["page"] == 1
        assert "sample text from the page" in snippets[0]["snippet"]

    @patch("rx_pagemarker.pdf_extractor.HAS_PYMUPDF", True)
    @patch("rx_pagemarker.pdf_extractor.fitz")
    def test_extract_with_pymupdf_insufficient_text(self, mock_fitz, tmp_path):
        """Test extraction when page has insufficient text."""
        pdf_path = tmp_path / "test.pdf"
        pdf_path.write_bytes(b"fake pdf")

        mock_page = MagicMock()
        mock_page.get_text.return_value = "a b"  # Only 2 words

        mock_doc = MagicMock()
        mock_doc.__len__.return_value = 1
        mock_doc.__getitem__.return_value = mock_page
        mock_doc.__enter__.return_value = mock_doc
        mock_doc.__exit__.return_value = None

        mock_fitz.open.return_value = mock_doc

        extractor = PDFExtractor(pdf_path, backend="pymupdf", min_words=3)
        snippets = extractor.extract()

        assert len(snippets) == 1
        assert snippets[0]["snippet"] == "PASTE_TEXT_FROM_END_OF_PAGE_HERE"
        assert "Insufficient text" in snippets[0]["note"]

    @patch("rx_pagemarker.pdf_extractor.HAS_PDFPLUMBER", True)
    @patch("rx_pagemarker.pdf_extractor.pdfplumber")
    def test_extract_with_pdfplumber_success(self, mock_pdfplumber, tmp_path):
        """Test successful extraction using pdfplumber."""
        pdf_path = tmp_path / "test.pdf"
        pdf_path.write_bytes(b"fake pdf")

        mock_page = MagicMock()
        mock_page.extract_text.return_value = "This is sample text from the page."

        mock_pdf = MagicMock()
        mock_pdf.pages = [mock_page]
        mock_pdf.__enter__.return_value = mock_pdf
        mock_pdf.__exit__.return_value = None

        mock_pdfplumber.open.return_value = mock_pdf

        extractor = PDFExtractor(pdf_path, backend="pdfplumber")
        snippets = extractor.extract()

        assert len(snippets) == 1
        assert snippets[0]["page"] == 1
        assert "sample text from the page" in snippets[0]["snippet"]


class TestPDFExtractorSaveToJson:
    """Test JSON saving functionality."""

    def test_save_to_json_success(self, tmp_path):
        """Test successful JSON saving."""
        output_path = tmp_path / "output.json"
        snippets = [
            {"page": 1, "snippet": "test snippet one"},
            {"page": 2, "snippet": "test snippet two"},
        ]

        extractor = PDFExtractor("dummy.pdf")
        extractor.save_to_json(output_path, snippets)

        assert output_path.exists()
        with open(output_path, "r", encoding="utf-8") as f:
            loaded = json.load(f)
        assert loaded == snippets

    def test_save_to_json_with_greek_text(self, tmp_path):
        """Test JSON saving with Greek text."""
        output_path = tmp_path / "output.json"
        snippets = [{"page": 1, "snippet": "Ελληνικό κείμενο"}]

        extractor = PDFExtractor("dummy.pdf")
        extractor.save_to_json(output_path, snippets)

        with open(output_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "Ελληνικό κείμενο" in content

    def test_save_to_json_invalid_path(self):
        """Test that PDFExtractionError is raised for invalid path."""
        extractor = PDFExtractor("dummy.pdf")
        invalid_path = "/nonexistent/directory/output.json"

        with pytest.raises(PDFExtractionError, match="Error saving JSON"):
            extractor.save_to_json(invalid_path, [])


class TestValidateSnippets:
    """Test snippet validation functionality."""

    def test_validate_snippets_basic(self, tmp_path):
        """Test basic snippet validation."""
        json_path = tmp_path / "snippets.json"
        snippets = [
            {"page": 1, "snippet": "unique snippet one"},
            {"page": 2, "snippet": "unique snippet two"},
        ]

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(snippets, f)

        results = validate_snippets(json_path)

        assert results["total_snippets"] == 2
        assert results["unique_snippets"] == 2
        assert results["placeholder_count"] == 0
        assert len(results["duplicate_snippets"]) == 0

    def test_validate_snippets_with_duplicates(self, tmp_path):
        """Test validation detects duplicate snippets."""
        json_path = tmp_path / "snippets.json"
        snippets = [
            {"page": 1, "snippet": "same snippet"},
            {"page": 2, "snippet": "same snippet"},
            {"page": 3, "snippet": "unique snippet"},
        ]

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(snippets, f)

        results = validate_snippets(json_path)

        assert results["total_snippets"] == 3
        assert results["unique_snippets"] == 2
        assert results["duplicate_snippets"]["same snippet"] == 2

    def test_validate_snippets_with_placeholders(self, tmp_path):
        """Test validation counts placeholders."""
        json_path = tmp_path / "snippets.json"
        snippets = [
            {"page": 1, "snippet": "PASTE_TEXT_FROM_END_OF_PAGE_HERE"},
            {"page": 2, "snippet": "real snippet"},
        ]

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(snippets, f)

        results = validate_snippets(json_path)

        assert results["placeholder_count"] == 1

    def test_validate_snippets_with_html(self, tmp_path):
        """Test validation against HTML file."""
        json_path = tmp_path / "snippets.json"
        html_path = tmp_path / "book.html"

        snippets = [
            {"page": 1, "snippet": "text in html"},
            {"page": 2, "snippet": "not in html"},
        ]

        html_content = "<html><body>This text in html is present.</body></html>"

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(snippets, f)

        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        results = validate_snippets(json_path, html_path)

        assert len(results["missing_from_html"]) == 1
        assert 2 in results["missing_from_html"]
        assert results["html_match_rate"] == 0.5

    def test_validate_snippets_invalid_json(self, tmp_path):
        """Test that PDFExtractionError is raised for invalid JSON."""
        json_path = tmp_path / "invalid.json"
        json_path.write_text("not valid json{]")

        with pytest.raises(PDFExtractionError, match="Error loading JSON"):
            validate_snippets(json_path)

    def test_validate_snippets_nonexistent_file(self):
        """Test that PDFExtractionError is raised for nonexistent file."""
        with pytest.raises(PDFExtractionError, match="Error loading JSON"):
            validate_snippets("/nonexistent/file.json")


class TestPrintValidationResults:
    """Test validation results printing."""

    def test_print_validation_results_basic(self, capsys):
        """Test basic validation results output."""
        results = {
            "total_snippets": 10,
            "unique_snippets": 9,
            "placeholder_count": 1,
            "duplicate_snippets": {},
        }

        print_validation_results(results)
        captured = capsys.readouterr()

        assert "Total snippets:      10" in captured.out
        assert "Unique snippets:     9" in captured.out
        assert "Needs manual entry:  1" in captured.out

    def test_print_validation_results_with_duplicates(self, capsys):
        """Test validation results with duplicates."""
        results = {
            "total_snippets": 5,
            "unique_snippets": 3,
            "placeholder_count": 0,
            "duplicate_snippets": {"duplicate text": 2},
        }

        print_validation_results(results)
        captured = capsys.readouterr()

        assert "Duplicate snippets found" in captured.out

    def test_print_validation_results_ready_to_use(self, capsys):
        """Test output when snippets are ready to use."""
        results = {
            "total_snippets": 10,
            "unique_snippets": 10,
            "placeholder_count": 0,
            "duplicate_snippets": {},
            "html_match_rate": 1.0,
        }

        print_validation_results(results)
        captured = capsys.readouterr()

        assert "Ready to use" in captured.out


class TestWordCompletion:
    """Test word completion functionality for snippets ending with partial words."""

    def test_complete_partial_word_finds_full_word(self):
        """Test that partial word at end of snippet is completed from HTML."""
        extractor = PDFExtractor("test.pdf")
        html_text = "Η απόφαση αυτή βασίζεται στην σύγχυση που δημιουργήθηκε"
        snippet = "βασίζεται στην σύγ"

        result = extractor._complete_partial_word(snippet, html_text)

        assert result == "βασίζεται στην σύγχυση"

    def test_complete_partial_word_no_change_when_word_exists(self):
        """Test that complete words are not modified."""
        extractor = PDFExtractor("test.pdf")
        html_text = "Η απόφαση αυτή βασίζεται στην σύγχυση"
        snippet = "βασίζεται στην σύγχυση"

        result = extractor._complete_partial_word(snippet, html_text)

        assert result == "βασίζεται στην σύγχυση"

    def test_complete_partial_word_keeps_unknown_words(self):
        """Test that unknown words are kept (never removed)."""
        extractor = PDFExtractor("test.pdf")
        html_text = "Η απόφαση αυτή"
        snippet = "Η απόφαση αβγ"  # "αβγ" not in HTML - should be kept

        result = extractor._complete_partial_word(snippet, html_text)

        # Words that can't be completed should be kept as-is (never removed)
        assert result == "Η απόφαση αβγ"

    def test_complete_partial_word_adds_fixme_for_uncompletable_hyphenated(self):
        """Test that hyphenated words that can't be completed get FIXME marker."""
        extractor = PDFExtractor("test.pdf")
        html_text = "some completely different text"
        snippet = "word1 word2 frag-"  # "frag-" cannot be completed from HTML

        result = extractor._complete_partial_word(snippet, html_text)

        # Should keep the stem and add FIXME marker for manual review
        assert result == "word1 word2 frag<!-- FIXME -->"

    def test_complete_partial_word_keeps_punctuation(self):
        """Test that words ending with punctuation are kept."""
        extractor = PDFExtractor("test.pdf")
        html_text = "Η απόφαση."
        snippet = "Η απόφαση."

        result = extractor._complete_partial_word(snippet, html_text)

        assert result == "Η απόφαση."

    def test_clean_snippet_with_html_text(self):
        """Test _clean_snippet completes partial words when HTML is provided."""
        extractor = PDFExtractor("test.pdf")
        html_text = "Η σύγχυση είναι μεγάλη"
        snippet = "Η σύγ"

        result = extractor._clean_snippet(snippet, html_text)

        assert result == "Η σύγχυση"

    def test_clean_snippet_without_html_text(self):
        """Test _clean_snippet works normally without HTML."""
        extractor = PDFExtractor("test.pdf")
        snippet = "word1 word2 word3"

        result = extractor._clean_snippet(snippet, None)

        assert result == "word1 word2 word3"

    def test_clean_snippet_keeps_trailing_hyphenated_word(self):
        """Test that trailing word fragments with hyphens are kept (never removed)."""
        extractor = PDFExtractor("test.pdf")
        snippet = "complete word another frag-"

        result = extractor._clean_snippet(snippet, None)

        # Hyphenated words are kept as-is when no HTML is provided (never removed)
        assert result == "complete word another frag-"


class TestContextCorrection:
    """Test context-based correction for merged words in snippets."""

    def test_correct_merged_words_in_middle(self):
        """Test that merged words in the middle of snippet are corrected."""
        extractor = PDFExtractor("test.pdf")
        html_text = "δεν επάγονται καμία συνέπεια ουσιαστικού ή δικονομικού δικαίου"
        # Simulated PDF extraction with merged word "ουσιαστιστην" instead of "ουσιαστικού στην"
        snippet = "επάγονται καμία συνέπεια ουσιαστιστην"

        result, was_corrected = extractor._correct_snippet_from_context(
            snippet, html_text, target_words=10
        )

        assert was_corrected
        assert "ουσιαστικού" in result
        assert "ουσιαστιστην" not in result

    def test_no_correction_when_no_anchor_found(self):
        """Test that snippet is unchanged when no anchor sequence is found."""
        extractor = PDFExtractor("test.pdf")
        html_text = "completely different text here"
        snippet = "some random words"

        result, was_corrected = extractor._correct_snippet_from_context(
            snippet, html_text, target_words=10
        )

        assert not was_corrected
        assert result == snippet

    def test_finds_anchor_with_2_words(self):
        """Test that 2-word anchors are found when 3-word anchors fail."""
        extractor = PDFExtractor("test.pdf")
        html_text = "η απόφαση του δικαστηρίου είναι τελεσίδικη και οριστική"
        snippet = "wrongword απόφαση του δικαστηρίου wrongword2"

        result, was_corrected = extractor._correct_snippet_from_context(
            snippet, html_text, target_words=6
        )

        assert was_corrected
        assert "απόφαση του δικαστηρίου" in result


class TestContextExtraction:
    """Test context extraction for snippet disambiguation."""

    def test_extract_context_basic(self):
        """Test basic context extraction from page text."""
        extractor = PDFExtractor("test.pdf")
        page_text = "word1 word2 word3 word4 snippet text here word5 word6 word7 word8"
        snippet = "snippet text here"

        context_before, context_after = extractor._extract_context(
            page_text, snippet, num_words=4
        )

        assert context_before == "word1 word2 word3 word4"
        assert context_after == "word5 word6 word7 word8"

    def test_extract_context_fewer_words_before(self):
        """Test context extraction when fewer words available before snippet."""
        extractor = PDFExtractor("test.pdf")
        page_text = "word1 word2 snippet text here word5 word6 word7 word8"
        snippet = "snippet text here"

        context_before, context_after = extractor._extract_context(
            page_text, snippet, num_words=4
        )

        assert context_before == "word1 word2"
        assert context_after == "word5 word6 word7 word8"

    def test_extract_context_fewer_words_after(self):
        """Test context extraction when fewer words available after snippet."""
        extractor = PDFExtractor("test.pdf")
        page_text = "word1 word2 word3 word4 snippet text here word5 word6"
        snippet = "snippet text here"

        context_before, context_after = extractor._extract_context(
            page_text, snippet, num_words=4
        )

        assert context_before == "word1 word2 word3 word4"
        assert context_after == "word5 word6"

    def test_extract_context_no_context_before(self):
        """Test context extraction when snippet is at start."""
        extractor = PDFExtractor("test.pdf")
        page_text = "snippet text here word1 word2 word3 word4"
        snippet = "snippet text here"

        context_before, context_after = extractor._extract_context(
            page_text, snippet, num_words=4
        )

        assert context_before == ""
        assert context_after == "word1 word2 word3 word4"

    def test_extract_context_no_context_after(self):
        """Test context extraction when snippet is at end."""
        extractor = PDFExtractor("test.pdf")
        page_text = "word1 word2 word3 word4 snippet text here"
        snippet = "snippet text here"

        context_before, context_after = extractor._extract_context(
            page_text, snippet, num_words=4
        )

        assert context_before == "word1 word2 word3 word4"
        assert context_after == ""

    def test_extract_context_snippet_not_found(self):
        """Test context extraction when snippet not in page text."""
        extractor = PDFExtractor("test.pdf")
        page_text = "completely different text"
        snippet = "snippet text here"

        context_before, context_after = extractor._extract_context(
            page_text, snippet, num_words=4
        )

        assert context_before == ""
        assert context_after == ""

    def test_extract_context_disabled(self):
        """Test context extraction with num_words=0."""
        extractor = PDFExtractor("test.pdf")
        page_text = "word1 word2 snippet text here word5 word6"
        snippet = "snippet text here"

        context_before, context_after = extractor._extract_context(
            page_text, snippet, num_words=0
        )

        assert context_before == ""
        assert context_after == ""

    def test_extract_context_greek_text(self):
        """Test context extraction with Greek text."""
        extractor = PDFExtractor("test.pdf")
        page_text = "η απόφαση του δικαστηρίου είναι τελεσίδικη και οριστική"
        snippet = "είναι τελεσίδικη"

        context_before, context_after = extractor._extract_context(
            page_text, snippet, num_words=4
        )

        assert context_before == "η απόφαση του δικαστηρίου"
        assert context_after == "και οριστική"

    def test_context_words_parameter(self):
        """Test that context_words parameter is stored correctly."""
        extractor = PDFExtractor("test.pdf", context_words=6)
        assert extractor.context_words == 6

        extractor_disabled = PDFExtractor("test.pdf", context_words=0)
        assert extractor_disabled.context_words == 0


class TestContextStatsTracking:
    """Test context extraction statistics tracking."""

    def test_context_stats_initialized(self):
        """Test that context stats are initialized in stats dict."""
        extractor = PDFExtractor("test.pdf")
        assert "context_extracted" in extractor.stats
        assert "context_partial" in extractor.stats
        assert extractor.stats["context_extracted"] == 0
        assert extractor.stats["context_partial"] == 0
