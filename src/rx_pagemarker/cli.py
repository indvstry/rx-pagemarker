"""Command-line interface for RX Page Marker."""

import sys
from pathlib import Path
from typing import Optional

import click

from . import __version__
from .marker import PageMarkerInserter
from .pdf_extractor import (
    InvalidParameterError,
    MissingDependencyError,
    PDFExtractionError,
    PDFExtractor,
    PDFNotFoundError,
    print_validation_results,
    validate_snippets,
)
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
@click.option(
    "--inject-css", is_flag=True, help="Inject CSS styling to make page markers visible"
)
def mark(
    input_html: Path,
    page_references: Path,
    output_html: Optional[Path],
    verbose: bool,
    inject_css: bool,
) -> None:
    """Insert page markers into HTML file.

    Takes an HTML file and a JSON file containing page references, and inserts
    page markers at the specified locations. The markers can span across
    formatting tags like <i>, <b>, <span>.

    Markers are placed AFTER snippet text. For correct EPUB page navigation,
    use a +1 page offset during extraction so markers indicate where the
    NEXT page begins (see README for the "offset hack" explanation).

    \b
    Examples:
        rx-pagemarker mark book.html pages.json output.html
        rx-pagemarker mark book.html pages.json --inject-css
    """
    try:
        inserter = PageMarkerInserter(input_html, page_references, output_html, inject_css)
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


@cli.command()
@click.argument("pdf_file", type=click.Path(exists=True, path_type=Path))
@click.argument("output_json", type=click.Path(path_type=Path))
@click.argument("html_file", type=click.Path(exists=True, path_type=Path), required=False)
@click.option(
    "--raw-pdf",
    is_flag=True,
    default=False,
    help="Extract raw PDF text without HTML correction (no HTML file needed)",
)
@click.option(
    "--fuzzy-match",
    is_flag=True,
    default=False,
    help="Use slow fuzzy matching for complex layouts (requires HTML file)",
)
@click.option(
    "--words",
    "-w",
    type=int,
    default=10,
    help="Number of words per snippet (default: 10)",
)
@click.option(
    "--strategy",
    "-s",
    type=click.Choice(["end_of_page", "bottom_visual", "beginning_of_page"]),
    default="end_of_page",
    help="Snippet selection strategy (default: end_of_page)",
)
@click.option(
    "--backend",
    "-b",
    type=click.Choice(["auto", "pymupdf", "pdfplumber"]),
    default="auto",
    help="PDF extraction backend (default: auto)",
)
@click.option(
    "--start-page",
    type=int,
    default=1,
    help="First page number to extract (default: 1)",
)
@click.option(
    "--end-page",
    type=int,
    default=None,
    help="Last page number to extract (default: all pages)",
)
@click.option(
    "--page-offset",
    type=int,
    default=0,
    help="Offset to add to page numbers (e.g., --page-offset 500 makes page 7 output as 507)",
)
@click.option(
    "--segment-words",
    is_flag=True,
    default=False,
    help="Enable word boundary reconstruction for PDFs with missing spaces",
)
@click.option(
    "--language",
    "-l",
    type=str,
    default="el",
    help="Language code for word segmentation (default: el for Greek)",
)
@click.option(
    "--review",
    is_flag=True,
    default=False,
    help="Show confidence scores for manual review",
)
@click.option(
    "--exclude-pattern",
    "-x",
    type=str,
    multiple=True,
    help="Regex pattern to exclude from text (e.g., production metadata). Can be used multiple times.",
)
@click.option(
    "--no-default-excludes",
    is_flag=True,
    default=False,
    help="Disable default exclusion patterns (InDesign sluglines, timestamps)",
)
@click.option(
    "--include-footnotes",
    is_flag=True,
    default=False,
    help="Include footnote text (smaller font); by default footnotes are skipped",
)
@click.option(
    "--min-font-size",
    type=float,
    default=8.5,
    help="Minimum font size for body text (smaller text treated as footnotes, default: 8.5pt)",
)
@click.option(
    "--context-words",
    type=int,
    default=4,
    help="Number of context words to capture before/after snippet for disambiguation (default: 4, 0 to disable)",
)
def extract(
    pdf_file: Path,
    output_json: Path,
    html_file: Optional[Path],
    raw_pdf: bool,
    fuzzy_match: bool,
    words: int,
    strategy: str,
    backend: str,
    start_page: int,
    end_page: Optional[int],
    page_offset: int,
    segment_words: bool,
    language: str,
    review: bool,
    exclude_pattern: tuple,
    no_default_excludes: bool,
    include_footnotes: bool,
    min_font_size: float,
    context_words: int,
) -> None:
    """Extract text snippets from PDF file for page marker generation.

    By default, requires an HTML file to correct and complete extracted text.
    Use --raw-pdf to extract without HTML correction.

    \b
    Arguments:
      PDF_FILE     - Source PDF file
      OUTPUT_JSON  - Output JSON file for snippets
      HTML_FILE    - HTML file for text correction (required unless --raw-pdf)

    \b
    Strategies:
      end_of_page       - Last N words from extracted text (default, for page markers)
      bottom_visual     - Text from visually lowest position (for complex layouts)
      beginning_of_page - First N words from extracted text (cleaner, for citations)

    \b
    Backends:
      auto        - Automatically choose best available (PyMuPDF > pdfplumber)
      pymupdf     - Fast C-based extraction (recommended for 500+ pages)
      pdfplumber  - Better layout analysis (better for tables/columns)

    \b
    Examples:
      # Standard usage with HTML correction (recommended)
      rx-pagemarker extract book.pdf snippets.json book.html

      # Magazine with page offset (PDF page 7 = print page 507)
      rx-pagemarker extract magazine.pdf snippets.json mag.html --start-page 7 --page-offset 500

      # Raw PDF extraction without HTML (faster but less accurate)
      rx-pagemarker extract book.pdf snippets.json --raw-pdf

      # Use slow fuzzy matching for heavily corrupted PDFs
      rx-pagemarker extract book.pdf snippets.json book.html --fuzzy-match

      # Extract with 8 words per snippet using pdfplumber
      rx-pagemarker extract book.pdf snippets.json book.html -w 8 -b pdfplumber

      # Use beginning_of_page strategy for cleaner snippets
      rx-pagemarker extract book.pdf snippets.json book.html --strategy beginning_of_page

      # Include footnotes (normally skipped)
      rx-pagemarker extract book.pdf snippets.json book.html --include-footnotes
    """
    # Validate HTML file requirement
    if not raw_pdf and html_file is None:
        click.echo(
            "Error: HTML_FILE is required for text correction.\n"
            "Either provide an HTML file or use --raw-pdf for raw extraction.\n\n"
            "Examples:\n"
            "  rx-pagemarker extract book.pdf snippets.json book.html\n"
            "  rx-pagemarker extract book.pdf snippets.json --raw-pdf",
            err=True,
        )
        sys.exit(1)

    if fuzzy_match and html_file is None:
        click.echo(
            "Error: --fuzzy-match requires an HTML file.",
            err=True,
        )
        sys.exit(1)

    if raw_pdf and html_file is not None:
        click.echo(
            "Warning: --raw-pdf ignores the HTML file argument.",
            err=True,
        )

    try:
        extractor = PDFExtractor(
            pdf_file,
            backend=backend,
            snippet_words=words,
            strategy=strategy,
            segment_words=segment_words,
            language=language,
            match_html_path=html_file if fuzzy_match else None,
            exclude_patterns=list(exclude_pattern) if exclude_pattern else None,
            use_default_excludes=not no_default_excludes,
            skip_footnotes=not include_footnotes,  # Skip by default, include if flag set
            min_font_size=min_font_size,
            complete_words_html_path=html_file if (not fuzzy_match and not raw_pdf) else None,
            context_words=context_words,
        )

        # Extract snippets
        snippets = extractor.extract()

        # Filter by page range if specified
        if start_page > 1 or end_page is not None:
            filtered = []
            for snippet in snippets:
                page_num = snippet["page"]
                if page_num >= start_page and (
                    end_page is None or page_num <= end_page
                ):
                    filtered.append(snippet)
            snippets = filtered
            click.echo(
                f"Filtered to pages {start_page}-{end_page or 'end'}: {len(snippets)} pages"
            )

        # Apply page offset if specified (for magazines with continuing page numbers)
        if page_offset != 0:
            for snippet in snippets:
                snippet["page"] = snippet["page"] + page_offset
            first_page = snippets[0]["page"] if snippets else start_page + page_offset
            last_page = snippets[-1]["page"] if snippets else end_page + page_offset if end_page else "end"
            click.echo(f"Applied page offset {page_offset}: pages now {first_page}-{last_page}")

        # Review mode: show confidence scores
        if review and segment_words:
            click.echo("\n" + "=" * 60)
            click.echo("WORD SEGMENTATION REVIEW")
            click.echo("=" * 60)

            low_confidence = []
            for snippet in snippets:
                conf = snippet.get("confidence", 1.0)
                if conf < 0.7:
                    low_confidence.append(snippet)

            if low_confidence:
                click.echo(f"\n⚠ Found {len(low_confidence)} snippets with low confidence (<0.7):\n")
                for item in low_confidence[:10]:  # Show first 10
                    click.echo(f"Page {item['page']}: {item['snippet'][:60]}...")
                    click.echo(f"  Confidence: {item.get('confidence', 'N/A')}\n")

                if len(low_confidence) > 10:
                    click.echo(f"... and {len(low_confidence) - 10} more\n")
            else:
                click.echo("✓ All snippets have high confidence (≥0.7)\n")

            # Show average confidence
            confidences = [s.get("confidence", 1.0) for s in snippets]
            avg_conf = sum(confidences) / len(confidences) if confidences else 0
            click.echo(f"Average confidence: {avg_conf:.2f}")
            click.echo("=" * 60 + "\n")

        # Save to JSON
        extractor.save_to_json(output_json, snippets)

        # Print statistics
        extractor.print_stats()

        click.echo(f"\n💡 Next: Validate with 'rx-pagemarker validate {output_json}'")

    except MissingDependencyError as e:
        click.echo(f"✗ Missing dependency: {e}", err=True)
        sys.exit(1)
    except PDFNotFoundError as e:
        click.echo(f"✗ File not found: {e}", err=True)
        sys.exit(1)
    except InvalidParameterError as e:
        click.echo(f"✗ Invalid parameter: {e}", err=True)
        sys.exit(1)
    except PDFExtractionError as e:
        click.echo(f"✗ Extraction failed: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"✗ Unexpected error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument("json_file", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--html",
    "-h",
    type=click.Path(exists=True, path_type=Path),
    help="HTML file to validate snippets against",
)
@click.option(
    "--show-duplicates",
    "-d",
    is_flag=True,
    help="Show all duplicate snippets (default: first 5)",
)
def validate(json_file: Path, html: Optional[Path], show_duplicates: bool) -> None:
    """Validate extracted snippets for quality and uniqueness.

    Checks the JSON file for:
    - Duplicate snippets (may cause incorrect page marker placement)
    - Placeholder entries that need manual filling
    - Whether snippets exist in the target HTML file (if provided)

    \b
    Examples:
      # Basic validation
      rx-pagemarker validate snippets.json

      # Validate against HTML to check if snippets will be found
      rx-pagemarker validate snippets.json --html book.html

      # Show all duplicates
      rx-pagemarker validate snippets.json -d
    """
    try:
        results = validate_snippets(json_file, html)
        print_validation_results(results)

    except PDFExtractionError as e:
        click.echo(f"✗ Validation error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"✗ Unexpected error: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    cli()
