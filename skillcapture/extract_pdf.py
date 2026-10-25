"""
PDF content extraction using Docling.

Primary path : Docling (structured extraction with page references).
Fallback path: pypdf plain-text extraction, clearly flagged in the output.

DocumentConverter is expensive to build (~3-8 s, loads ML models).
Expose get_docling_converter() so app.py can wrap it with @st.cache_resource
and reuse the same instance across Streamlit reruns.

The caller receives a uniform dict regardless of which path ran.
"""

from __future__ import annotations

import io
import os
import tempfile
import time
from pathlib import Path


# ---------------------------------------------------------------------------
# Converter accessor — wrap with @st.cache_resource in app.py
# ---------------------------------------------------------------------------

def get_docling_converter():
    """
    Build and return a Docling DocumentConverter.

    Intended to be called through @st.cache_resource.

    Returns (converter, init_seconds) or raises RuntimeError if Docling is
    not installed.
    """
    try:
        from docling.document_converter import DocumentConverter  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "Docling is not installed. Run: pip install docling"
        ) from exc

    t0 = time.perf_counter()
    converter = DocumentConverter()
    elapsed = time.perf_counter() - t0
    return converter, elapsed


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def extract_pdf(pdf_bytes: bytes, filename: str = "manual.pdf",
                converter=None) -> dict:
    """
    Extract text content from a PDF.

    Parameters
    ----------
    pdf_bytes : raw PDF bytes
    filename  : original filename (used for suffix detection)
    converter : optional pre-built Docling DocumentConverter; if None, a new
                one is created (slower — prefer passing a cached instance)

    Returns
    -------
    {
        "text":             str,
        "pages":            list[dict],   # [{page: int, text: str}, ...]
        "extractor":        str,          # "docling" | "pypdf" | "none"
        "extract_seconds":  float,        # wall-clock extraction time
        "warning":          str | None,
        "error":            str | None,
    }
    """
    result = _try_docling(pdf_bytes, filename, converter)
    if result is not None:
        return result

    result = _try_pypdf(pdf_bytes)
    if result is not None:
        return result

    return {
        "text": "",
        "pages": [],
        "extractor": "none",
        "extract_seconds": 0.0,
        "warning": None,
        "error": (
            "Neither Docling nor pypdf is installed. "
            "Run: pip install docling pypdf"
        ),
    }


# ---------------------------------------------------------------------------
# Docling path
# ---------------------------------------------------------------------------

def _try_docling(pdf_bytes: bytes, filename: str, converter=None) -> dict | None:
    """Attempt extraction with Docling. Returns None if Docling is unavailable."""
    try:
        from docling.document_converter import DocumentConverter  # type: ignore
    except ImportError:
        return None

    suffix = Path(filename).suffix or ".pdf"
    tmp_path = None
    t0 = time.perf_counter()
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(pdf_bytes)
            tmp_path = tmp.name

        # Use the passed-in converter (cached) or build a fresh one
        conv = converter if converter is not None else DocumentConverter()
        result_doc = conv.convert(tmp_path)
        doc = result_doc.document

        pages: list[dict] = []
        full_parts: list[str] = []

        try:
            page_texts: dict[int, list[str]] = {}
            for element, _level in doc.iterate_items():
                prov = getattr(element, "prov", None)
                page_no = None
                if prov:
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
            md = doc.export_to_markdown()
            pages = [{"page": 1, "text": md}]
            full_parts = [md]

        extract_seconds = time.perf_counter() - t0
        full_text = "\n\n".join(full_parts)
        return {
            "text": full_text,
            "pages": pages,
            "extractor": "docling",
            "extract_seconds": extract_seconds,
            "warning": None,
            "error": None,
        }

    except Exception as exc:  # noqa: BLE001
        extract_seconds = time.perf_counter() - t0
        return {
            "text": "",
            "pages": [],
            "extractor": "docling",
            "extract_seconds": extract_seconds,
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

    t0 = time.perf_counter()
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
            "extract_seconds": time.perf_counter() - t0,
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
            "extract_seconds": time.perf_counter() - t0,
            "warning": None,
            "error": f"pypdf extraction failed: {exc}",
        }
