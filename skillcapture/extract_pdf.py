"""
PDF content extraction using Docling.

Primary path : Docling (structured extraction with page references).
Fallback path: pypdf plain-text extraction, clearly flagged in the output.

The caller receives a uniform dict regardless of which path ran, so the
rest of the pipeline never needs to check which extractor was used.
"""

from __future__ import annotations

import io
import tempfile
import os
from pathlib import Path


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def extract_pdf(pdf_bytes: bytes, filename: str = "manual.pdf") -> dict:
    """
    Extract text content from a PDF.

    Returns:
        {
            "text": str,               # full extracted text
            "pages": list[dict],       # [{page: int, text: str}, ...]
            "extractor": str,          # "docling" | "pypdf" | "none"
            "warning": str | None,     # set when falling back or partially failing
            "error": str | None        # set only on complete failure
        }
    """
    result = _try_docling(pdf_bytes, filename)
    if result is not None:
        return result

    result = _try_pypdf(pdf_bytes)
    if result is not None:
        return result

    return {
        "text": "",
        "pages": [],
        "extractor": "none",
        "warning": None,
        "error": (
            "Neither Docling nor pypdf is installed. "
            "Run: pip install docling pypdf"
        ),
    }


# ---------------------------------------------------------------------------
# Docling path
# ---------------------------------------------------------------------------

def _try_docling(pdf_bytes: bytes, filename: str) -> dict | None:
    """Attempt extraction with Docling. Returns None if Docling is unavailable."""
    try:
        from docling.document_converter import DocumentConverter  # type: ignore
    except ImportError:
        return None

    suffix = Path(filename).suffix or ".pdf"
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(pdf_bytes)
            tmp_path = tmp.name

        converter = DocumentConverter()
        result_doc = converter.convert(tmp_path)
        doc = result_doc.document

        # Collect text grouped by page
        pages: list[dict] = []
        full_parts: list[str] = []

        # Docling exposes .export_to_markdown() for the whole document
        # and .texts / .pages for structured access.
        # We use export_to_markdown per page when possible, otherwise whole-doc.
        try:
            # Try page-level grouping
            page_texts: dict[int, list[str]] = {}
            for element, _level in doc.iterate_items():
                prov = getattr(element, "prov", None)
                page_no = None
                if prov:
                    # prov may be a list of ProvenanceItem
                    if isinstance(prov, list) and prov:
                        page_no = getattr(prov[0], "page_no", None)
                    else:
                        page_no = getattr(prov, "page_no", None)
                page_no = page_no or 0
                text = getattr(element, "text", None) or ""
                if text.strip():
                    page_texts.setdefault(page_no, []).append(text.strip())

            for page_no in sorted(page_texts):
                combined = "\n".join(page_texts[page_no])
                pages.append({"page": page_no, "text": combined})
                full_parts.append(f"[Page {page_no}]\n{combined}")

        except Exception:  # noqa: BLE001
            # Fall back to whole-document markdown export
            md = doc.export_to_markdown()
            pages = [{"page": 1, "text": md}]
            full_parts = [md]

        full_text = "\n\n".join(full_parts)
        return {
            "text": full_text,
            "pages": pages,
            "extractor": "docling",
            "warning": None,
            "error": None,
        }

    except Exception as exc:  # noqa: BLE001
        # Docling is installed but processing failed; fall through to pypdf
        return {
            "text": "",
            "pages": [],
            "extractor": "docling",
            "warning": f"Docling processing failed ({exc}). Falling back to pypdf.",
            "error": None,
        }
    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


# ---------------------------------------------------------------------------
# pypdf fallback path
# ---------------------------------------------------------------------------

def _try_pypdf(pdf_bytes: bytes) -> dict | None:
    """Attempt plain-text extraction with pypdf. Returns None if unavailable."""
    try:
        import pypdf  # type: ignore
    except ImportError:
        return None

    try:
        reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
        pages: list[dict] = []
        full_parts: list[str] = []
        for i, page in enumerate(reader.pages, start=1):
            text = (page.extract_text() or "").strip()
            if text:
                pages.append({"page": i, "text": text})
                full_parts.append(f"[Page {i}]\n{text}")

        return {
            "text": "\n\n".join(full_parts),
            "pages": pages,
            "extractor": "pypdf",
            "warning": (
                "Using pypdf plain-text fallback instead of Docling. "
                "Structured layout information is not preserved."
            ),
            "error": None,
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "text": "",
            "pages": [],
            "extractor": "pypdf",
            "warning": None,
            "error": f"pypdf extraction failed: {exc}",
        }
