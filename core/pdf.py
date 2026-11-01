"""Turn scanned PDF pages into images so they can be read with OCR."""

from PIL import Image

try:
    import pymupdf
except ImportError:  # older PyMuPDF versions use the name "fitz"
    import fitz as pymupdf

RENDER_DPI = 200          # 200 dpi is a good balance of OCR quality and speed
MAX_SIDE_PIXELS = 4500    # protects memory if a page is unusually large


class PDFError(Exception):
    """Raised with a user-friendly message when a PDF cannot be used."""


def _open(file_bytes):
    try:
        doc = pymupdf.open(stream=file_bytes, filetype="pdf")
    except Exception as err:  # noqa: BLE001
        raise PDFError("This PDF could not be opened. The file may be damaged.") from err
    if doc.needs_pass:
        doc.close()
        raise PDFError(
            "This PDF is password-protected. Remove the password and upload it again."
        )
    if doc.page_count == 0:
        doc.close()
        raise PDFError("This PDF has no pages.")
    return doc


def count_pages(file_bytes):
    """Return the number of pages in a PDF."""
    doc = _open(file_bytes)
    try:
        return doc.page_count
    finally:
        doc.close()


def render_page(file_bytes, index, dpi=RENDER_DPI):
    """Render one page (index starts at 0) to an RGB PIL image."""
    doc = _open(file_bytes)
    try:
        if not 0 <= index < doc.page_count:
            raise PDFError(f"Page {index + 1} does not exist in this PDF.")
        page = doc[index]
        zoom = dpi / 72
        longest = max(page.rect.width, page.rect.height) * zoom
        if longest > MAX_SIDE_PIXELS:
            zoom *= MAX_SIDE_PIXELS / longest
        pixmap = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), alpha=False)
        return Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
    except PDFError:
        raise
    except Exception as err:  # noqa: BLE001
        raise PDFError(f"Page {index + 1} could not be rendered: {err}") from err
    finally:
        doc.close()