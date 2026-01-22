"""
PDF utilities for slides processing.

Provides functions for PDF to image conversion using PyMuPDF.
Used by SlidesExtractor to prepare slides for vision API.

v0.50+: Initial implementation for slides integration.
"""

import logging
from collections.abc import Iterator

import fitz  # PyMuPDF

logger = logging.getLogger(__name__)

# Default DPI for rendering PDF pages
# 150 DPI is sufficient for text recognition while keeping file sizes reasonable
DEFAULT_DPI = 150


def pdf_to_images(
    pdf_bytes: bytes,
    dpi: int = DEFAULT_DPI,
) -> Iterator[tuple[bytes, str]]:
    """
    Convert PDF to PNG images.

    Renders each page of the PDF as a PNG image at the specified DPI.
    Uses iterator to avoid loading all pages into memory at once.

    Args:
        pdf_bytes: PDF file content as bytes
        dpi: Resolution for rendering (default: 150)

    Yields:
        Tuple of (png_bytes, filename) for each page

    Example:
        with open("slides.pdf", "rb") as f:
            pdf_bytes = f.read()

        for png_data, filename in pdf_to_images(pdf_bytes):
            # Process each page image
            print(f"Page: {filename}, Size: {len(png_data)} bytes")
    """
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception as e:
        logger.error(f"Failed to open PDF: {e}")
        raise ValueError(f"Invalid PDF file: {e}") from e

    try:
        page_count = len(doc)
        logger.debug(f"Converting PDF: {page_count} pages, {dpi} DPI")

        for page_num in range(page_count):
            page = doc[page_num]

            # Calculate zoom matrix for desired DPI
            # PDF default is 72 DPI, so zoom = dpi / 72
            zoom = dpi / 72
            mat = fitz.Matrix(zoom, zoom)

            # Render page to pixmap
            pix = page.get_pixmap(matrix=mat)

            # Convert to PNG bytes
            png_bytes = pix.tobytes("png")

            # Generate filename (1-indexed for user-friendliness)
            filename = f"page_{page_num + 1:03d}.png"

            yield png_bytes, filename

    finally:
        doc.close()


def pdf_page_count(pdf_bytes: bytes) -> int:
    """
    Get the number of pages in a PDF.

    Args:
        pdf_bytes: PDF file content as bytes

    Returns:
        Number of pages

    Raises:
        ValueError: If PDF is invalid

    Example:
        count = pdf_page_count(pdf_bytes)
        print(f"PDF has {count} pages")
    """
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        count = len(doc)
        doc.close()
        return count
    except Exception as e:
        logger.error(f"Failed to get PDF page count: {e}")
        raise ValueError(f"Invalid PDF file: {e}") from e


if __name__ == "__main__":
    """Run tests when executed directly."""
    import sys
    from pathlib import Path

    def run_tests():
        """Test PDF utilities."""
        print("\nTesting pdf_utils...\n")

        # Test 1: Empty PDF handling
        print("Test 1: Invalid PDF handling...", end=" ")
        try:
            list(pdf_to_images(b"not a pdf"))
            print("FAILED (should have raised)")
            return 1
        except ValueError:
            print("OK")

        # Test 2: Page count for invalid PDF
        print("Test 2: Page count for invalid PDF...", end=" ")
        try:
            pdf_page_count(b"invalid")
            print("FAILED (should have raised)")
            return 1
        except ValueError:
            print("OK")

        # Test 3: Create minimal valid PDF and test
        print("Test 3: Minimal PDF conversion...", end=" ")
        try:
            # Create a simple PDF with one page
            doc = fitz.open()
            page = doc.new_page()
            page.insert_text((72, 72), "Test slide content")
            pdf_bytes = doc.tobytes()
            doc.close()

            # Test page count
            count = pdf_page_count(pdf_bytes)
            assert count == 1, f"Expected 1 page, got {count}"

            # Test conversion
            pages = list(pdf_to_images(pdf_bytes))
            assert len(pages) == 1, f"Expected 1 image, got {len(pages)}"

            png_bytes, filename = pages[0]
            assert filename == "page_001.png"
            assert len(png_bytes) > 0
            # PNG magic bytes
            assert png_bytes[:4] == b"\x89PNG"

            print("OK")
            print(f"  Generated PNG: {len(png_bytes)} bytes")

        except Exception as e:
            print(f"FAILED: {e}")
            import traceback
            traceback.print_exc()
            return 1

        # Test 4: Multi-page PDF
        print("Test 4: Multi-page PDF...", end=" ")
        try:
            doc = fitz.open()
            for i in range(3):
                page = doc.new_page()
                page.insert_text((72, 72), f"Slide {i + 1}")
            pdf_bytes = doc.tobytes()
            doc.close()

            count = pdf_page_count(pdf_bytes)
            assert count == 3, f"Expected 3 pages, got {count}"

            pages = list(pdf_to_images(pdf_bytes))
            assert len(pages) == 3

            filenames = [p[1] for p in pages]
            assert filenames == ["page_001.png", "page_002.png", "page_003.png"]

            print("OK")
            print(f"  Generated {len(pages)} pages")

        except Exception as e:
            print(f"FAILED: {e}")
            return 1

        print("\n" + "=" * 40)
        print("All tests passed!")
        return 0

    sys.exit(run_tests())
