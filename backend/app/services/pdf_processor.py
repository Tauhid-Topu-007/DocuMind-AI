import re


class PDFError(Exception):
    pass


def is_pdf_header(head: bytes) -> bool:
    return head[:5] == b"%PDF-"


def clean_text(text: str) -> str:
    text = text.replace("\x00", "")
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)  # re-join hyphenated line breaks
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_pages(path: str) -> tuple[list[tuple[int, str]], int]:
    """Return ([(page_number, text), ...], total_pages). Page numbers are 1-based."""
    import pymupdf as fitz  # PyMuPDF

    try:
        doc = fitz.open(path)
    except Exception as e:
        raise PDFError("The file could not be opened as a PDF.") from e
    try:
        if doc.needs_pass:
            raise PDFError("Encrypted / password-protected PDFs are not supported.")
        total = doc.page_count
        pages = []
        for i in range(total):
            text = clean_text(doc[i].get_text("text"))
            if text:
                pages.append((i + 1, text))
    except PDFError:
        raise
    except Exception as e:
        raise PDFError("The PDF is damaged or could not be read.") from e
    finally:
        doc.close()
    if not pages:
        raise PDFError(
            "No extractable text found. This looks like a scanned PDF; OCR is not included in this version."
        )
    return pages, total
