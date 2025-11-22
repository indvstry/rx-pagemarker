#!/bin/bash
# Setup script for RX Page Marker

echo "Setting up RX Page Marker..."
echo ""

# Install package with development dependencies
echo "Installing package in development mode..."
pip install -e ".[dev]"

echo ""
echo "Setup complete! ✓"
echo ""
echo "The 'rx-pagemarker' command is now available."
echo ""
echo "Usage:"
echo "  Generate template:  rx-pagemarker generate <num_pages> <output_file>"
echo "  Insert markers:     rx-pagemarker mark <html_file> <json_file> [output_file]"
echo ""
echo "Examples:"
echo "  rx-pagemarker generate 200 pages.json"
echo "  rx-pagemarker mark book.html pages.json output.html"
echo ""
echo "Run tests:"
echo "  pytest"
echo ""
