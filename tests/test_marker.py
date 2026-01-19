"""Tests for page marker insertion."""

import json
import tempfile
from pathlib import Path

import pytest
from bs4 import BeautifulSoup

from rx_pagemarker.marker import PageMarkerInserter


@pytest.fixture
def simple_html():
    """Simple HTML for testing."""
    return """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <p>This is a simple paragraph.</p>
        <p>This is another paragraph with some text.</p>
    </body>
    </html>
    """


@pytest.fixture
def formatted_html():
    """HTML with formatting tags."""
    return """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <p>This has <i>italic text</i> in it.</p>
        <p>This has <b>bold</b> and <i>italic</i> words.</p>
        <p>Split <i>across</i> <span>multiple</span> tags here.</p>
    </body>
    </html>
    """


@pytest.fixture
def page_references():
    """Sample page references."""
    return [
        {"page": "1", "snippet": "simple paragraph."},
        {"page": "2", "snippet": "with some text."},
    ]


@pytest.fixture
def formatted_references():
    """Page references that span formatting tags."""
    return [
        {"page": "1", "snippet": "has italic text in"},
        {"page": "2", "snippet": "bold and italic words"},
        {"page": "3", "snippet": "across multiple tags here"},
    ]


def test_load_html(simple_html, tmp_path):
    """Test HTML loading."""
    html_file = tmp_path / "test.html"
    html_file.write_text(simple_html)
    json_file = tmp_path / "refs.json"
    json_file.write_text("[]")

    inserter = PageMarkerInserter(html_file, json_file)
    inserter.load_html()

    assert inserter.soup is not None
    assert inserter.soup.find("title").string == "Test"


def test_load_page_references(simple_html, page_references, tmp_path):
    """Test JSON loading."""
    html_file = tmp_path / "test.html"
    html_file.write_text(simple_html)
    json_file = tmp_path / "refs.json"
    json_file.write_text(json.dumps(page_references))

    inserter = PageMarkerInserter(html_file, json_file)
    inserter.load_page_references()

    assert len(inserter.page_references) == 2
    assert inserter.page_references[0]["page"] == "1"


def test_create_page_marker(simple_html, tmp_path):
    """Test page marker creation."""
    html_file = tmp_path / "test.html"
    html_file.write_text(simple_html)
    json_file = tmp_path / "refs.json"
    json_file.write_text("[]")

    inserter = PageMarkerInserter(html_file, json_file)
    inserter.load_html()

    marker = inserter.create_page_marker("5")
    assert marker.name == "span"
    # BeautifulSoup returns class as string when set directly
    assert marker.get("class") == "page-number"
    assert marker["role"] == "note"
    assert marker["aria-label"] == "Page 5"
    assert marker.string == "5"


def test_simple_snippet_insertion(simple_html, page_references, tmp_path):
    """Test inserting markers in simple HTML."""
    html_file = tmp_path / "test.html"
    html_file.write_text(simple_html)
    json_file = tmp_path / "refs.json"
    json_file.write_text(json.dumps(page_references))
    output_file = tmp_path / "output.html"

    inserter = PageMarkerInserter(html_file, json_file, output_file)
    inserter.run()

    # Check output exists
    assert output_file.exists()

    # Parse output and check markers
    with open(output_file) as f:
        soup = BeautifulSoup(f.read(), "lxml")

    markers = soup.find_all("span", class_="page-number")
    assert len(markers) == 2
    assert markers[0].string == "1"
    assert markers[1].string == "2"

    # Check stats
    assert inserter.stats["found"] == 2
    assert inserter.stats["not_found"] == 0


def test_formatted_snippet_insertion(formatted_html, formatted_references, tmp_path):
    """Test inserting markers across formatting tags."""
    html_file = tmp_path / "test.html"
    html_file.write_text(formatted_html)
    json_file = tmp_path / "refs.json"
    json_file.write_text(json.dumps(formatted_references))
    output_file = tmp_path / "output.html"

    inserter = PageMarkerInserter(html_file, json_file, output_file)
    inserter.run()

    # Check output
    with open(output_file) as f:
        soup = BeautifulSoup(f.read(), "lxml")

    markers = soup.find_all("span", class_="page-number")
    assert len(markers) == 3
    assert markers[0].string == "1"
    assert markers[1].string == "2"
    assert markers[2].string == "3"

    # Check stats
    assert inserter.stats["found"] == 3
    assert inserter.stats["not_found"] == 0


def test_snippet_not_found(simple_html, tmp_path):
    """Test behavior when snippet not found."""
    html_file = tmp_path / "test.html"
    html_file.write_text(simple_html)
    json_file = tmp_path / "refs.json"
    json_file.write_text(json.dumps([{"page": "1", "snippet": "nonexistent text"}]))
    output_file = tmp_path / "output.html"

    inserter = PageMarkerInserter(html_file, json_file, output_file)
    inserter.run()

    assert inserter.stats["found"] == 0
    assert inserter.stats["not_found"] == 1


def test_roman_numerals(simple_html, tmp_path):
    """Test Roman numeral page numbers."""
    html_file = tmp_path / "test.html"
    html_file.write_text(simple_html)
    json_file = tmp_path / "refs.json"
    json_file.write_text(json.dumps([{"page": "i", "snippet": "simple paragraph."}]))
    output_file = tmp_path / "output.html"

    inserter = PageMarkerInserter(html_file, json_file, output_file)
    inserter.run()

    with open(output_file) as f:
        soup = BeautifulSoup(f.read(), "lxml")

    marker = soup.find("span", class_="page-number")
    assert marker.string == "i"
    assert marker["aria-label"] == "Page i"


def test_greek_text(tmp_path):
    """Test handling Greek characters."""
    greek_html = """
    <!DOCTYPE html>
    <html lang="el">
    <head><title>Τίτλος</title></head>
    <body>
        <p>Αυτό είναι ένα κείμενο στα ελληνικά.</p>
    </body>
    </html>
    """
    html_file = tmp_path / "test.html"
    html_file.write_text(greek_html, encoding="utf-8")
    json_file = tmp_path / "refs.json"
    json_file.write_text(
        json.dumps([{"page": "1", "snippet": "στα ελληνικά."}], ensure_ascii=False),
        encoding="utf-8",
    )
    output_file = tmp_path / "output.html"

    inserter = PageMarkerInserter(html_file, json_file, output_file)
    inserter.run()

    assert inserter.stats["found"] == 1
    assert output_file.exists()


class TestContextDisambiguation:
    """Test context-based disambiguation for duplicate snippets."""

    def test_normalize_word_removes_greek_accents(self, tmp_path):
        """Test that Greek accents are removed for comparison."""
        html_file = tmp_path / "test.html"
        html_file.write_text("<html><body><p>test</p></body></html>")
        json_file = tmp_path / "refs.json"
        json_file.write_text("[]")

        inserter = PageMarkerInserter(html_file, json_file)
        inserter.load_html()

        # Greek word with accent
        assert inserter._normalize_word("απόφαση") == "αποφαση"
        assert inserter._normalize_word("Ελληνικά") == "ελληνικα"
        # Already lowercase, no accent
        assert inserter._normalize_word("word") == "word"

    def test_jaccard_similarity_identical(self, tmp_path):
        """Test Jaccard similarity for identical word lists."""
        html_file = tmp_path / "test.html"
        html_file.write_text("<html><body><p>test</p></body></html>")
        json_file = tmp_path / "refs.json"
        json_file.write_text("[]")

        inserter = PageMarkerInserter(html_file, json_file)
        inserter.load_html()

        words1 = ["the", "quick", "brown", "fox"]
        words2 = ["the", "quick", "brown", "fox"]
        similarity = inserter._jaccard_similarity(words1, words2)
        assert similarity == 1.0

    def test_jaccard_similarity_partial(self, tmp_path):
        """Test Jaccard similarity for partially overlapping word lists."""
        html_file = tmp_path / "test.html"
        html_file.write_text("<html><body><p>test</p></body></html>")
        json_file = tmp_path / "refs.json"
        json_file.write_text("[]")

        inserter = PageMarkerInserter(html_file, json_file)
        inserter.load_html()

        words1 = ["the", "quick", "brown", "fox"]
        words2 = ["the", "quick", "red", "dog"]
        # Intersection: {the, quick} = 2
        # Union: {the, quick, brown, fox, red, dog} = 6
        # Jaccard: 2/6 = 0.333...
        similarity = inserter._jaccard_similarity(words1, words2)
        assert abs(similarity - 2/6) < 0.01

    def test_jaccard_similarity_no_overlap(self, tmp_path):
        """Test Jaccard similarity for non-overlapping word lists."""
        html_file = tmp_path / "test.html"
        html_file.write_text("<html><body><p>test</p></body></html>")
        json_file = tmp_path / "refs.json"
        json_file.write_text("[]")

        inserter = PageMarkerInserter(html_file, json_file)
        inserter.load_html()

        words1 = ["one", "two", "three"]
        words2 = ["four", "five", "six"]
        similarity = inserter._jaccard_similarity(words1, words2)
        assert similarity == 0.0

    def test_jaccard_similarity_greek_accents(self, tmp_path):
        """Test Jaccard similarity handles Greek accent variations."""
        html_file = tmp_path / "test.html"
        html_file.write_text("<html><body><p>test</p></body></html>")
        json_file = tmp_path / "refs.json"
        json_file.write_text("[]")

        inserter = PageMarkerInserter(html_file, json_file)
        inserter.load_html()

        # Same words with different accent patterns
        words1 = ["απόφαση", "του", "δικαστηρίου"]
        words2 = ["αποφαση", "του", "δικαστηριου"]  # No accents
        similarity = inserter._jaccard_similarity(words1, words2)
        assert similarity == 1.0

    def test_extract_html_context(self, tmp_path):
        """Test HTML context extraction around a match position."""
        html_file = tmp_path / "test.html"
        html_file.write_text("<html><body><p>test</p></body></html>")
        json_file = tmp_path / "refs.json"
        json_file.write_text("[]")

        inserter = PageMarkerInserter(html_file, json_file)
        inserter.load_html()

        container_text = "word1 word2 word3 word4 MATCH word5 word6 word7 word8"
        position = container_text.find("MATCH")
        snippet_len = len("MATCH")

        before, after = inserter._extract_html_context(
            container_text, position, snippet_len, num_words=4
        )

        assert before == "word1 word2 word3 word4"
        assert after == "word5 word6 word7 word8"

    def test_score_context_match(self, tmp_path):
        """Test context scoring for a match."""
        html_file = tmp_path / "test.html"
        html_file.write_text("<html><body><p>test</p></body></html>")
        json_file = tmp_path / "refs.json"
        json_file.write_text("[]")

        inserter = PageMarkerInserter(html_file, json_file)
        inserter.load_html()

        container_text = "before1 before2 before3 before4 MATCH after1 after2 after3 after4"
        position = container_text.find("MATCH")
        snippet_len = len("MATCH")

        # Perfect match
        score = inserter._score_context_match(
            container_text, position, snippet_len,
            "before1 before2 before3 before4",
            "after1 after2 after3 after4"
        )
        assert score == 1.0

        # No match
        score_no_match = inserter._score_context_match(
            container_text, position, snippet_len,
            "completely different words here",
            "totally other text here too"
        )
        assert score_no_match == 0.0

    def test_insert_page_marker_with_context(self, tmp_path):
        """Test inserting page marker uses context when provided."""
        # HTML with duplicate text - same snippet in both paragraphs
        duplicate_html = """
        <!DOCTYPE html>
        <html>
        <body>
            <p>before1 before2 before3 before4 duplicate text after1 after2 after3 after4</p>
            <p>other1 other2 other3 other4 duplicate text other5 other6 other7 other8</p>
        </body>
        </html>
        """
        html_file = tmp_path / "test.html"
        html_file.write_text(duplicate_html)
        json_file = tmp_path / "refs.json"
        json_file.write_text("[]")
        output_file = tmp_path / "output.html"

        inserter = PageMarkerInserter(html_file, json_file, output_file)
        inserter.load_html()
        inserter.load_page_references()

        # Insert with context pointing to SECOND occurrence (other1, other5, etc.)
        result = inserter.insert_page_marker(
            page_number="1",
            snippet="duplicate text",
            context_before="other1 other2 other3 other4",
            context_after="other5 other6 other7 other8"
        )

        assert result is True

        # Verify marker is in the SECOND paragraph, not the first
        # Save and parse output
        inserter.save()
        with open(output_file) as f:
            soup = BeautifulSoup(f.read(), "lxml")

        paragraphs = soup.find_all("p")
        assert len(paragraphs) == 2

        # First paragraph should NOT contain the marker
        first_p_marker = paragraphs[0].find("span", class_="page-number")
        assert first_p_marker is None, "Marker should NOT be in first paragraph"

        # Second paragraph SHOULD contain the marker
        second_p_marker = paragraphs[1].find("span", class_="page-number")
        assert second_p_marker is not None, "Marker should be in second paragraph"
        assert second_p_marker.string == "1"

    def test_find_all_snippet_locations(self, tmp_path):
        """Test finding all occurrences of a snippet."""
        duplicate_html = """
        <!DOCTYPE html>
        <html>
        <body>
            <p>First occurrence of target text here.</p>
            <p>Second occurrence of target text here.</p>
            <p>Third occurrence of target text here.</p>
        </body>
        </html>
        """
        html_file = tmp_path / "test.html"
        html_file.write_text(duplicate_html)
        json_file = tmp_path / "refs.json"
        json_file.write_text("[]")

        inserter = PageMarkerInserter(html_file, json_file)
        inserter.load_html()

        locations = inserter.find_all_snippet_locations("target text")

        # Should find 3 occurrences
        assert len(locations) == 3

    def test_context_in_process_method(self, tmp_path):
        """Test that process() passes context to insert_page_marker()."""
        simple_html = """
        <!DOCTYPE html>
        <html>
        <body>
            <p>some words before the snippet text here and after words.</p>
        </body>
        </html>
        """
        html_file = tmp_path / "test.html"
        html_file.write_text(simple_html)
        json_file = tmp_path / "refs.json"
        # Include context fields in JSON
        refs = [{
            "page": "1",
            "snippet": "snippet text",
            "context_before": "before the",
            "context_after": "here and"
        }]
        json_file.write_text(json.dumps(refs))
        output_file = tmp_path / "output.html"

        inserter = PageMarkerInserter(html_file, json_file, output_file)
        inserter.run()

        assert inserter.stats["found"] == 1
