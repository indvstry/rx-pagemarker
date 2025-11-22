"""RX Page Marker - Insert page markers into HTML files for EPUB3 generation."""

__version__ = "0.1.0"
__author__ = "Aris Karatarakis"
__email__ = "aris@karatarakis.com"

from .marker import PageMarkerInserter

__all__ = ["PageMarkerInserter", "__version__"]
