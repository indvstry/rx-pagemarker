"""Command-line interface for RX Page Marker."""

import sys
from pathlib import Path
from typing import Optional

import click

from . import __version__
from .marker import PageMarkerInserter
from .template import generate_template


@click.group()
@click.version_option(version=__version__)
def cli() -> None:
    """RX Page Marker - Insert page markers into HTML files for EPUB3 generation."""
    pass


@cli.command()
@click.argument("input_html", type=click.Path(exists=True, path_type=Path))
@click.argument("page_references", type=click.Path(exists=True, path_type=Path))
@click.argument("output_html", type=click.Path(path_type=Path), required=False)
@click.option(
    "--verbose", "-v", is_flag=True, help="Enable verbose output (currently unused)"
)
def mark(
    input_html: Path,
    page_references: Path,
    output_html: Optional[Path],
    verbose: bool,
) -> None:
    """Insert page markers into HTML file.

    Takes an HTML file and a JSON file containing page references, and inserts
    page markers at the specified locations. The markers can span across
    formatting tags like <i>, <b>, <span>.

    \b
    Examples:
        rx-pagemarker mark book.html pages.json output.html
        rx-pagemarker mark ../books/book.html pages.json
    """
    try:
        inserter = PageMarkerInserter(input_html, page_references, output_html)
        inserter.run()
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument("num_pages", type=int)
@click.argument("output_file", type=click.Path(path_type=Path))
@click.option(
    "--start-page",
    "-s",
    type=int,
    default=1,
    help="Starting page number (default: 1)",
)
@click.option(
    "--roman",
    "-r",
    is_flag=True,
    help="Use Roman numerals (i, ii, iii) for front matter",
)
def generate(num_pages: int, output_file: Path, start_page: int, roman: bool) -> None:
    """Generate a template JSON file for page references.

    Creates a JSON file with placeholder text, making it easy to fill in
    snippets without worrying about JSON syntax.

    \b
    Examples:
        rx-pagemarker generate 200 pages.json
        rx-pagemarker generate 5 frontmatter.json --start-page 1 --roman
        rx-pagemarker generate 200 body.json --start-page 11
    """
    if num_pages <= 0:
        click.echo("Error: Number of pages must be positive", err=True)
        sys.exit(1)

    try:
        generate_template(num_pages, output_file, start_page, roman)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    cli()
