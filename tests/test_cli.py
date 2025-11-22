"""Tests for CLI commands."""

import json

import pytest
from click.testing import CliRunner

from rx_pagemarker.cli import cli


@pytest.fixture
def runner():
    """Create a CLI runner."""
    return CliRunner()


def test_cli_version(runner):
    """Test --version flag."""
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "version" in result.output.lower() or "0.1.0" in result.output


def test_cli_help(runner):
    """Test --help flag."""
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "mark" in result.output
    assert "generate" in result.output


def test_mark_command_help(runner):
    """Test mark command help."""
    result = runner.invoke(cli, ["mark", "--help"])
    assert result.exit_code == 0
    assert "INPUT_HTML" in result.output
    assert "PAGE_REFERENCES" in result.output


def test_generate_command_help(runner):
    """Test generate command help."""
    result = runner.invoke(cli, ["generate", "--help"])
    assert result.exit_code == 0
    assert "NUM_PAGES" in result.output
    assert "OUTPUT_FILE" in result.output
    assert "--roman" in result.output


def test_generate_command(runner, tmp_path):
    """Test generate command execution."""
    output_file = tmp_path / "test.json"
    result = runner.invoke(cli, ["generate", "5", str(output_file)])

    assert result.exit_code == 0
    assert output_file.exists()

    with open(output_file) as f:
        data = json.load(f)
    assert len(data) == 5


def test_generate_with_roman(runner, tmp_path):
    """Test generate command with --roman flag."""
    output_file = tmp_path / "test.json"
    result = runner.invoke(cli, ["generate", "3", str(output_file), "--roman"])

    assert result.exit_code == 0

    with open(output_file) as f:
        data = json.load(f)
    assert data[0]["page"] == "i"
    assert data[1]["page"] == "ii"
    assert data[2]["page"] == "iii"


def test_generate_with_start_page(runner, tmp_path):
    """Test generate command with --start-page option."""
    output_file = tmp_path / "test.json"
    result = runner.invoke(cli, ["generate", "3", str(output_file), "-s", "10"])

    assert result.exit_code == 0

    with open(output_file) as f:
        data = json.load(f)
    assert data[0]["page"] == "10"
    assert data[2]["page"] == "12"


def test_mark_command(runner, tmp_path):
    """Test mark command execution."""
    # Create test HTML
    html_file = tmp_path / "test.html"
    html_file.write_text(
        """
    <!DOCTYPE html>
    <html><body><p>Test paragraph here.</p></body></html>
    """
    )

    # Create test JSON
    json_file = tmp_path / "refs.json"
    json_file.write_text(json.dumps([{"page": "1", "snippet": "paragraph here."}]))

    # Run mark command
    output_file = tmp_path / "output.html"
    result = runner.invoke(
        cli, ["mark", str(html_file), str(json_file), str(output_file)]
    )

    assert result.exit_code == 0
    assert output_file.exists()
    assert "✓" in result.output


def test_mark_command_missing_file(runner, tmp_path):
    """Test mark command with missing input file."""
    json_file = tmp_path / "refs.json"
    json_file.write_text("[]")

    result = runner.invoke(
        cli, ["mark", "nonexistent.html", str(json_file), "output.html"]
    )

    assert result.exit_code != 0
