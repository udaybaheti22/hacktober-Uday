"""
SkillCapture — Multimodal Demonstration-to-Procedure Translator
Hacktoberfest x MOSS Hack Day Udupi 2026

Run with:  python -m streamlit run app.py
"""

from __future__ import annotations

import hashlib
import os
import time

import streamlit as st
from dotenv import load_dotenv

load_dotenv()


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------
def _fmt_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 ** 2:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / 1024**2:.1f} MB"


def _sha256(data: bytes) -> str:
    """Content-based cache key: SHA-256 hex of raw bytes."""
    return hashlib.sha256(data).hexdigest()


# ---------------------------------------------------------------------------
# Page config — must be the first Streamlit call
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="SkillCapture",
    page_icon="🎓",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------------
from skillcapture.transcribe import (
    get_whisper_model,
    transcribe_audio_with_model,
    segments_to_annotated_text,
)
from skillcapture.extract_pdf import get_docling_converter, extract_pdf
from skillcapture.synthesize import synthesize_procedure, GEMMA_MODEL
from skillcapture.export import procedure_to_markdown
from skillcapture.diagrams import (
    build_mermaid_flowchart,
    build_mermaid_sequence,
    validate_mermaid_syntax,
)
from skillcapture.validate_procedure import validate_procedure, validate_graph


# ---------------------------------------------------------------------------
# Cached resource initialisation
# These run once per server process and are reused across all reruns.
# ---------------------------------------------------------------------------

@st.cache_resource(show_spinner=False)
def _load_whisper_model():
    """Load faster-whisper base model once. Cached for the process lifetime."""
    try:
        model, init_seconds = get_whisper_model()
        return model, init_seconds, None
    except RuntimeError as exc:
        return None, 0.0, str(exc)


@st.cache_resource(show_spinner=False)
def _load_docling_converter():
    """Build Docling DocumentConverter once. Cached for the process lifetime."""
    try:
        converter, init_seconds = get_docling_converter()
        return converter, init_seconds, None
    except RuntimeError as exc:
        return None, 0.0, str(exc)


# ---------------------------------------------------------------------------
# Cached processing functions
# Cache keys are content-based (SHA-256) so replacing a file invalidates
# the cache automatically. No sensitive data is used as a cache key.
# ---------------------------------------------------------------------------

@st.cache_data(show_spinner=False)
def _cached_transcribe(audio_sha256: str, audio_bytes: bytes) -> dict:
    """
    Transcribe audio. Cached by content hash.
    Re-runs only when the audio file content actually changes.
    audio_sha256 is included explicitly so Streamlit uses it as the cache key
    even though audio_bytes would also differ — this avoids hashing large
    byte arrays twice.
    """
    whisper_model, _init_secs, model_error = _load_whisper_model()
    if model_error:
        return {
            "transcript": "", "segments": [],
            "decode_seconds": 0.0, "transcribe_seconds": 0.0,
            "error": f"Whisper model failed to load: {model_error}",
        }
    return transcribe_audio_with_model(whisper_model, audio_bytes)


@st.cache_data(show_spinner=False)
def _cached_extract_pdf(pdf_sha256: str, pdf_bytes: bytes,
                        filename: str) -> dict:
    """
    Extract PDF. Cached by content hash.
    Re-runs only when the PDF file content actually changes.
    """
    converter, _init_secs, conv_error = _load_docling_converter()
    # conv_error is non-fatal: extract_pdf falls back to pypdf automatically
    return extract_pdf(pdf_bytes, filename,
                       converter=converter if not conv_error else None)


# ---------------------------------------------------------------------------
# Session-state initialisation
# Guard: only set keys that don't exist yet — safe to call on every rerun.
# ---------------------------------------------------------------------------
_DEFAULTS: dict = {
    "procedure":            None,   # validated Procedure object
    "transcript":           None,   # dict from transcribe_audio_with_model
    "pdf_result":           None,   # dict from extract_pdf
    "image_data":           None,   # list[(filename, bytes)]
    "processing_done":      False,  # True once a full successful run completed
    "error_msg":            None,   # last fatal error string
    "timings":              {},     # stage → elapsed seconds
    "validation_warnings":  [],     # post-generation validation messages
}
for _k, _v in _DEFAULTS.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.title("🎓 SkillCapture")
st.caption(
    "Turn a spoken demonstration + photos + an optional manual into a "
    "structured, evidence-linked procedure."
)
st.divider()

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("ℹ️ About")
    st.markdown(
        f"""
**Model:** `{GEMMA_MODEL}`  
Gemma 4 via the Gemini API (Google AI Studio)

**Audio:** faster-whisper (base, CPU int8)  
**PDF:** Docling → pypdf fallback

---
**API key status:**
"""
    )
    if os.getenv("GEMINI_API_KEY"):
        st.success("GEMINI_API_KEY found ✓")
    else:
        st.error("GEMINI_API_KEY not set — add it to .env")

    st.markdown("---")
    st.markdown(
        "Built for **Hacktoberfest x MOSS Hack Day Udupi 2026**  \n"
        "Open-source under the MIT License."
    )

    # Timings diagnostic — shown after a successful run
    if st.session_state["processing_done"] and st.session_state["timings"]:
        st.markdown("---")
        st.markdown("**⏱ Stage timings**")
        for stage, secs in st.session_state["timings"].items():
            st.markdown(f"- {stage}: `{secs:.2f}s`")

    # Reset action
    if st.session_state["processing_done"]:
        st.markdown("---")
        if st.button("🔄 Start new procedure", key="btn_reset",
                     use_container_width=True):
            for _k, _v in _DEFAULTS.items():
                st.session_state[_k] = _v
            st.rerun()

# ---------------------------------------------------------------------------
# Input section
# ---------------------------------------------------------------------------
col_left, col_right = st.columns([1, 1], gap="large")

with col_left:
    st.subheader("1. Upload inputs")

    audio_file = st.file_uploader(
        "🎙️ Audio recording (required)",
        type=["mp3", "wav", "m4a", "ogg", "flac", "webm", "aac"],
        help="Upload a recording of someone explaining or demonstrating the process.",
        key="uploader_audio",
    )

    image_files = st.file_uploader(
        "📷 Step photographs (3–8 images, required)",
        type=["jpg", "jpeg", "png", "webp", "bmp"],
        accept_multiple_files=True,
        help="Upload photos showing the key steps of the process.",
        key="uploader_images",
    )

    pdf_file = st.file_uploader(
        "📄 Reference manual PDF (optional)",
        type=["pdf"],
        help="Upload a supporting manual or instructions document.",
        key="uploader_pdf",
    )

with col_right:
    st.subheader("2. Uploaded files")

    if audio_file:
        st.success(f"🎙️ {audio_file.name} ({_fmt_size(audio_file.size)})")
    else:
        st.info("No audio uploaded yet.")

    if image_files:
        valid_images = [f for f in image_files if f is not None]
        if len(valid_images) < 3:
            st.warning(f"⚠️ {len(valid_images)} image(s) — at least 3 recommended.")
        elif len(valid_images) > 8:
            st.warning(f"⚠️ {len(valid_images)} images — maximum 8 will be sent.")
            valid_images = valid_images[:8]
        else:
            st.success(f"📷 {len(valid_images)} image(s) ready.")

        thumb_cols = st.columns(min(4, len(valid_images)))
        for i, img in enumerate(valid_images[:4]):
            with thumb_cols[i]:
                st.image(img, caption=img.name, use_container_width=True)
    else:
        valid_images = []
        st.info("No images uploaded yet.")

    if pdf_file:
        st.success(f"📄 {pdf_file.name} ({_fmt_size(pdf_file.size)})")
    else:
        st.info("No PDF uploaded (optional).")

st.divider()

# ---------------------------------------------------------------------------
# Generate button
# ---------------------------------------------------------------------------
can_generate = (
    audio_file is not None
    and len(valid_images) >= 1
    and not st.session_state["processing_done"]
)

if not st.session_state["processing_done"] and not can_generate:
    st.info("Upload at least an audio file and one image to generate a procedure.")

generate_btn = st.button(
    "⚙️ Generate Procedure",
    disabled=not can_generate,
    type="primary",
    use_container_width=True,
    key="btn_generate",
)

# ---------------------------------------------------------------------------
# Processing — runs ONLY on explicit button click.
# Uses @st.cache_data wrappers for audio and PDF so unchanged files reuse
# prior results. Gemma 4 is called once and stored in session_state.
# ---------------------------------------------------------------------------
if generate_btn and can_generate:
    st.session_state["error_msg"] = None
    timings: dict[str, float] = {}
    run_start = time.perf_counter()

    # ── Stage 1: Audio transcription ────────────────────────────────────────
    with st.status("🎙️ Transcribing audio…", expanded=True) as status:
        audio_bytes = audio_file.read()
        audio_hash  = _sha256(audio_bytes)
        st.write(f"Audio: {audio_file.name} · {_fmt_size(len(audio_bytes))} "
                 f"· hash `{audio_hash[:8]}…`")

        t0 = time.perf_counter()
        transcript_result = _cached_transcribe(audio_hash, audio_bytes)
        wall = time.perf_counter() - t0

        if transcript_result["error"]:
            status.update(label="❌ Transcription failed", state="error")
            st.error(transcript_result["error"])
            st.session_state["error_msg"] = transcript_result["error"]
            st.stop()

        word_count = len(transcript_result["transcript"].split())
        seg_count  = len(transcript_result["segments"])
        cached_note = " (cached)" if wall < 0.05 else ""
        timings["Audio decode"]    = transcript_result["decode_seconds"]
        timings["Whisper inference"] = transcript_result["transcribe_seconds"]
        status.update(
            label=(
                f"✅ Transcribed — {word_count} words, {seg_count} segments"
                f" · {transcript_result['transcribe_seconds']:.1f}s{cached_note}"
            ),
            state="complete",
        )
        with st.expander("View transcript", expanded=False):
            st.text(
                segments_to_annotated_text(transcript_result["segments"])
                or transcript_result["transcript"]
            )

    # ── Stage 2: PDF extraction ──────────────────────────────────────────────
    if pdf_file:
        with st.status("📄 Extracting PDF…", expanded=True) as status:
            pdf_bytes = pdf_file.read()
            pdf_hash  = _sha256(pdf_bytes)
            st.write(f"PDF: {pdf_file.name} · hash `{pdf_hash[:8]}…`")

            t0 = time.perf_counter()
            pdf_result = _cached_extract_pdf(pdf_hash, pdf_bytes, pdf_file.name)
            wall = time.perf_counter() - t0

            if pdf_result["error"]:
                status.update(label="❌ PDF extraction failed", state="error")
                st.error(pdf_result["error"])
                st.session_state["error_msg"] = pdf_result["error"]
                st.stop()

            extractor_label = pdf_result["extractor"]
            page_count      = len(pdf_result["pages"])
            cached_note = " (cached)" if wall < 0.05 else ""
            timings["PDF extraction"] = pdf_result["extract_seconds"]
            status.update(
                label=(
                    f"✅ Extracted {page_count} page(s) via {extractor_label}"
                    f" · {pdf_result['extract_seconds']:.1f}s{cached_note}"
                ),
                state="complete",
            )
            if pdf_result["warning"]:
                st.warning(pdf_result["warning"])
            with st.expander("View extracted text (first 1000 chars)",
                             expanded=False):
                st.text(pdf_result["text"][:1000])
    else:
        pdf_result = {
            "text": "", "pages": [], "extractor": "none",
            "extract_seconds": 0.0, "warning": None, "error": None,
        }

    # ── Stage 3: Read image bytes ────────────────────────────────────────────
    image_data: list[tuple[str, bytes]] = []
    for img_file in valid_images[:8]:
        img_file.seek(0)
        image_data.append((img_file.name, img_file.read()))

    # ── Stage 4: Gemma 4 synthesis ───────────────────────────────────────────
    with st.status(
        f"🤖 Synthesising procedure with {GEMMA_MODEL}…", expanded=True
    ) as status:
        st.write(
            f"Sending {len(image_data)} image(s), transcript, and "
            f"{'manual' if pdf_file else 'no manual'} to Gemma 4…"
        )
        t0 = time.perf_counter()
        try:
            procedure = synthesize_procedure(
                transcript=transcript_result["transcript"],
                segments=transcript_result["segments"],
                images=image_data,
                manual_text=pdf_result["text"],
                manual_pages=pdf_result.get("pages", []),
            )
            gemma_seconds = time.perf_counter() - t0
            timings["Gemma 4 API"] = gemma_seconds
            timings["Total"] = time.perf_counter() - run_start

            # ── Post-generation deterministic validation ──────────────────
            supplied_image_ids = {fname for fname, _ in image_data}
            proc_errors  = validate_procedure(procedure, supplied_image_ids)
            graph_errors = validate_graph(procedure)
            all_errors   = proc_errors + graph_errors

            status.update(
                label=(
                    f"✅ Procedure generated — {len(procedure.steps)} step(s)"
                    f" · {gemma_seconds:.1f}s"
                    + (f" · {len(all_errors)} validation warning(s)" if all_errors else "")
                ),
                state="complete",
            )
            if all_errors:
                for ve in all_errors:
                    st.warning(f"Validation: {ve}")

            st.session_state["validation_warnings"] = all_errors
        except RuntimeError as exc:
            status.update(label="❌ Synthesis failed", state="error")
            st.error(str(exc))
            st.session_state["error_msg"] = str(exc)
            st.stop()

    # Persist everything in session_state
    st.session_state["procedure"]            = procedure
    st.session_state["transcript"]           = transcript_result
    st.session_state["pdf_result"]           = pdf_result
    st.session_state["image_data"]           = image_data
    st.session_state["processing_done"]      = True
    st.session_state["timings"]              = timings
    st.rerun()  # clean rerun → display block renders without status widgets

# ---------------------------------------------------------------------------
# Display — reads only from session_state; no processing here.
# ---------------------------------------------------------------------------
if st.session_state["processing_done"] and st.session_state["procedure"] is not None:

    procedure = st.session_state["procedure"]

    st.divider()
    st.subheader(f"📋 {procedure.title}")
    st.markdown(procedure.overview)

    # Show any post-generation validation warnings
    if st.session_state.get("validation_warnings"):
        with st.expander("⚠️ Validation warnings", expanded=False):
            for vw in st.session_state["validation_warnings"]:
                st.warning(vw)

    if procedure.tools_and_materials:
        with st.expander("🔧 Tools and Materials", expanded=True):
            for item in procedure.tools_and_materials:
                st.markdown(f"- {item}")

    if procedure.general_warnings:
        with st.expander("⚠️ General Warnings", expanded=True):
            for w in procedure.general_warnings:
                st.warning(w)

    st.markdown("### Steps")
    for step in procedure.steps:
        inferred_note  = " *(inferred — no direct source)*" if step.is_inferred else ""
        review_note    = " 🔶 *requires review*" if step.requires_review else ""
        with st.expander(
            f"Step {step.step_number}: {step.title}{inferred_note}{review_note}",
            expanded=True,
        ):
            st.markdown(step.instruction)

            if step.warnings:
                for w in step.warnings:
                    st.warning(w)

            if step.checkpoint:
                st.info(f"**Checkpoint:** {step.checkpoint}")

            if step.sources:
                src_lines = []
                for src in step.sources:
                    parts = [f"`{src.kind.upper()}`"]
                    if src.image_id:
                        parts.append(f"Image: `{src.image_id}`")
                    if src.page_ref:
                        parts.append(f"Page {src.page_ref}")
                    if src.transcript_timestamp:
                        parts.append(f"@ {src.transcript_timestamp}")
                    if src.quote:
                        parts.append(f'— *"{src.quote}"*')
                    # P1: evidence status badge
                    status_colours = {
                        "SUPPORTED":           "🟢",
                        "PARTIALLY_SUPPORTED": "🟡",
                        "CONFLICTING":         "🔴",
                        "INSUFFICIENT":        "⚫",
                    }
                    badge = status_colours.get(src.evidence_status, "")
                    parts.append(f"{badge} `{src.evidence_status}`")
                    if src.support_explanation:
                        parts.append(f"— {src.support_explanation}")
                    src_lines.append("• " + " ".join(parts))
                st.markdown("**Evidence:** " + "  \n".join(src_lines))

            if step.uncertainty_note:
                st.warning(f"🔶 Uncertainty: {step.uncertainty_note}")

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        if procedure.missing_information:
            st.markdown("#### ❓ Missing Info")
            for item in procedure.missing_information:
                st.markdown(f"- {item}")
    with col_b:
        if procedure.contradictions:
            st.markdown("#### ⚡ Contradictions")
            for item in procedure.contradictions:
                st.markdown(f"- {item}")
    with col_c:
        if procedure.unresolved_questions:
            st.markdown("#### 🔍 Unresolved Questions")
            for item in procedure.unresolved_questions:
                st.markdown(f"- {item}")

    if procedure.completion_checklist:
        st.markdown("### ✅ Completion Checklist")
        for idx, item in enumerate(procedure.completion_checklist):
            st.checkbox(item, value=False, key=f"checklist_{idx}")

    st.divider()

    markdown_output = procedure_to_markdown(procedure)
    safe_title = procedure.title.lower().replace(" ", "_")[:40]
    st.download_button(
        label="⬇️ Download procedure as Markdown",
        data=markdown_output.encode("utf-8"),
        file_name=f"{safe_title}_procedure.md",
        mime="text/markdown",
        use_container_width=True,
        type="primary",
        key="btn_download",
    )

    st.caption(
        "Use **🔄 Start new procedure** in the sidebar to upload different files."
    )

    # -------------------------------------------------------------------------
    # Mermaid diagram views
    # Built from the already-generated procedure — no API calls.
    # -------------------------------------------------------------------------
    st.divider()
    st.subheader("📊 Diagram Views")
    st.caption(
        "Visualise the procedure as a Mermaid diagram. "
        "Changing diagram type does not re-run Whisper, Docling, or Gemma 4."
    )

    dtab_flow, dtab_seq = st.tabs(["Flowchart", "Sequence Diagram"])

    with dtab_flow:
        diagram_fc, err_fc = build_mermaid_flowchart(procedure)
        if err_fc and procedure.graph is None:
            st.warning(f"Could not build flowchart: {err_fc}")
        elif err_fc:
            st.warning(f"Graph-based flowchart failed: {err_fc}")
        else:
            graph_source_note = (
                "Built from validated graph data (P2)."
                if procedure.graph is not None
                else "Built from step order (fallback — no graph in response)."
            )
            st.caption(graph_source_note)
            valid, valmsg = validate_mermaid_syntax(diagram_fc)
            if not valid:
                st.error(f"Flowchart validation failed: {valmsg}")
            else:
                try:
                    from streamlit_mermaid import st_mermaid  # type: ignore
                    st_mermaid(diagram_fc, height=max(300, len(procedure.steps) * 90))
                except Exception as render_exc:
                    st.error(f"Mermaid render error: {render_exc}")
                with st.expander("View Mermaid source", expanded=False):
                    st.code(diagram_fc, language="text")

    with dtab_seq:
        diagram_seq, err_seq = build_mermaid_sequence(procedure)
        if err_seq:
            st.info(f"Sequence diagram not available: {err_seq}")
        else:
            valid, valmsg = validate_mermaid_syntax(diagram_seq)
            if not valid:
                st.error(f"Sequence diagram validation failed: {valmsg}")
            else:
                try:
                    from streamlit_mermaid import st_mermaid  # type: ignore
                    st_mermaid(diagram_seq, height=max(300, len(procedure.steps) * 110))
                except Exception as render_exc:
                    st.error(f"Mermaid render error: {render_exc}")
                with st.expander("View Mermaid source", expanded=False):
                    st.code(diagram_seq, language="text")

    # -------------------------------------------------------------------------
    # Open-source libraries used in this procedure
    # Checkbox list — purely informational, no reprocessing triggered.
    # -------------------------------------------------------------------------
    st.divider()
    st.subheader("🔧 Open-Source Libraries")
    st.caption(
        "These are the open-source tools that powered this procedure. "
        "Click any checkbox to mark it as explored."
    )

    # Each entry: (label, description, url, license)
    _OSS_LIBS = [
        (
            "faster-whisper",
            "Local audio transcription — used to transcribe your recording.",
            "https://github.com/SYSTRAN/faster-whisper",
            "MIT",
        ),
        (
            "Docling",
            "PDF extraction — parsed your reference manual with page references.",
            "https://github.com/DS4SD/docling",
            "MIT",
        ),
        (
            "Gemma 4 (gemma-4-26b-a4b-it)",
            "Open-weight multimodal model — synthesised the procedure from your inputs.",
            "https://ai.google.dev/gemma",
            "Gemma Terms of Use",
        ),
        (
            "Pydantic",
            "Schema validation — ensured the generated procedure matched the required structure.",
            "https://github.com/pydantic/pydantic",
            "MIT",
        ),
        (
            "Streamlit",
            "Web UI framework — powers this entire interface.",
            "https://github.com/streamlit/streamlit",
            "Apache 2.0",
        ),
        (
            "streamlit-mermaid",
            "Renders Mermaid flowchart and sequence diagrams inside Streamlit.",
            "https://github.com/jhbale11/streamlit-mermaid",
            "MIT",
        ),
        (
            "pypdf",
            "Plain-text PDF fallback when Docling is unavailable.",
            "https://github.com/py-pdf/pypdf",
            "BSD-3-Clause",
        ),
        (
            "python-dotenv",
            "Loads your GEMINI_API_KEY from the .env file safely.",
            "https://github.com/theskumar/python-dotenv",
            "BSD-3-Clause",
        ),
    ]

    for i, (name, description, url, lic) in enumerate(_OSS_LIBS):
        col_cb, col_info = st.columns([1, 11])
        with col_cb:
            st.checkbox("", key=f"oss_lib_{i}", label_visibility="collapsed")
        with col_info:
            st.markdown(
                f"**[{name}]({url})** &nbsp;`{lic}`  \n{description}"
            )
