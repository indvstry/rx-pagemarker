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
