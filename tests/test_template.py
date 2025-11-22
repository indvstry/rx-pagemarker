"""Tests for template generation."""

import json
from pathlib import Path

import pytest

from rx_pagemarker.template import generate_template, ROMAN_NUMERALS


def test_generate_basic_template(tmp_path):
    """Test basic template generation."""
    output_file = tmp_path / "template.json"
    generate_template(5, output_file)

    assert output_file.exists()

    with open(output_file) as f:
        data = json.load(f)

    assert len(data) == 5
    assert data[0]["page"] == "1"
    assert data[4]["page"] == "5"
    assert all(entry["snippet"] == "PASTE_TEXT_FROM_END_OF_PAGE_HERE" for entry in data)


def test_generate_with_start_page(tmp_path):
    """Test template generation with custom start page."""
    output_file = tmp_path / "template.json"
    generate_template(5, output_file, start_page=11)

    with open(output_file) as f:
        data = json.load(f)

    assert data[0]["page"] == "11"
    assert data[4]["page"] == "15"


def test_generate_with_roman_numerals(tmp_path):
    """Test template generation with Roman numerals."""
    output_file = tmp_path / "template.json"
    generate_template(5, output_file, start_page=1, use_roman=True)

    with open(output_file) as f:
        data = json.load(f)

    assert data[0]["page"] == "i"
    assert data[1]["page"] == "ii"
    assert data[2]["page"] == "iii"
    assert data[3]["page"] == "iv"
    assert data[4]["page"] == "v"


def test_roman_numerals_constant():
    """Test that Roman numerals constant has expected values."""
    assert ROMAN_NUMERALS[0] == "i"
    assert ROMAN_NUMERALS[4] == "v"
    assert ROMAN_NUMERALS[9] == "x"
    assert ROMAN_NUMERALS[19] == "xx"
    assert len(ROMAN_NUMERALS) == 20


def test_generate_unicode_filename(tmp_path):
    """Test template generation with Unicode filename."""
    output_file = tmp_path / "σελίδες.json"
    generate_template(3, output_file)

    assert output_file.exists()

    with open(output_file, encoding="utf-8") as f:
        data = json.load(f)

    assert len(data) == 3
