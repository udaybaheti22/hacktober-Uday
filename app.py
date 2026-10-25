"""
SkillCapture — Multimodal Demonstration-to-Procedure Translator
Hacktoberfest x MOSS Hack Day Udupi 2026

Run with:  streamlit run app.py
"""

from __future__ import annotations

import os

import streamlit as st
from dotenv import load_dotenv

load_dotenv()  # load GEMINI_API_KEY from .env


# ---------------------------------------------------------------------------
# Utility (defined early because used throughout the page)
# ---------------------------------------------------------------------------
def _fmt_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 ** 2:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / 1024**2:.1f} MB"


# ---------------------------------------------------------------------------
# Page config — must be first Streamlit call
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="SkillCapture",
    page_icon="🎓",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Imports (after dotenv so env vars are available)
# ---------------------------------------------------------------------------
from skillcapture.transcribe import transcribe_audio, segments_to_annotated_text
from skillcapture.extract_pdf import extract_pdf
from skillcapture.synthesize import synthesize_procedure, GEMMA_MODEL
from skillcapture.export import procedure_to_markdown


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
# Sidebar — model info + API key status
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
    )

    image_files = st.file_uploader(
        "📷 Step photographs (3–8 images, required)",
        type=["jpg", "jpeg", "png", "webp", "bmp"],
        accept_multiple_files=True,
        help="Upload photos showing the key steps of the process.",
    )

    pdf_file = st.file_uploader(
        "📄 Reference manual PDF (optional)",
        type=["pdf"],
        help="Upload a supporting manual or instructions document.",
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
            st.warning(f"⚠️ {len(valid_images)} image(s) uploaded — at least 3 recommended.")
        elif len(valid_images) > 8:
            st.warning(f"⚠️ {len(valid_images)} images uploaded — maximum 8 will be sent.")
            valid_images = valid_images[:8]
        else:
            st.success(f"📷 {len(valid_images)} image(s) ready.")

        # Show thumbnails
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
can_generate = audio_file is not None and len(valid_images) >= 1

if not can_generate:
    st.info("Upload at least an audio file and one image to generate a procedure.")

generate_btn = st.button(
    "⚙️ Generate Procedure",
    disabled=not can_generate,
    type="primary",
    use_container_width=True,
)

# ---------------------------------------------------------------------------
# Processing
# ---------------------------------------------------------------------------
if generate_btn and can_generate:
    procedure = None
    transcript_result = None
    pdf_result = None

    # --- Stage 1: Transcribe audio ---
    with st.status("🎙️ Transcribing audio…", expanded=True) as status:
        st.write("Loading faster-whisper (base model, CPU int8)…")
        transcript_result = transcribe_audio(audio_file.read(), audio_file.name)

        if transcript_result["error"]:
            status.update(label="❌ Transcription failed", state="error")
            st.error(transcript_result["error"])
            st.stop()
        else:
            word_count = len(transcript_result["transcript"].split())
            seg_count = len(transcript_result["segments"])
            status.update(
                label=f"✅ Transcribed — {word_count} words, {seg_count} segments",
                state="complete",
            )
            with st.expander("View transcript"):
                st.text(segments_to_annotated_text(transcript_result["segments"])
                        or transcript_result["transcript"])

    # --- Stage 2: Extract PDF (if provided) ---
    if pdf_file:
        with st.status("📄 Extracting PDF…", expanded=True) as status:
            pdf_result = extract_pdf(pdf_file.read(), pdf_file.name)

            if pdf_result["error"]:
                status.update(label="❌ PDF extraction failed", state="error")
                st.error(pdf_result["error"])
                st.stop()
            else:
                extractor_label = pdf_result["extractor"]
                page_count = len(pdf_result["pages"])
                label = f"✅ Extracted {page_count} page(s) via {extractor_label}"
                status.update(label=label, state="complete")

                if pdf_result["warning"]:
                    st.warning(pdf_result["warning"])

                with st.expander("View extracted text (first 1000 chars)"):
                    st.text(pdf_result["text"][:1000])
    else:
        pdf_result = {"text": "", "pages": [], "extractor": "none", "warning": None, "error": None}

    # --- Stage 3: Read image bytes ---
    image_data: list[tuple[str, bytes]] = []
    for img_file in valid_images[:8]:
        img_file.seek(0)
        image_data.append((img_file.name, img_file.read()))

    # --- Stage 4: Synthesize procedure with Gemma 4 ---
    with st.status(
        f"🤖 Synthesising procedure with {GEMMA_MODEL}…", expanded=True
    ) as status:
        st.write(
            f"Sending {len(image_data)} image(s), transcript, and "
            f"{'manual' if pdf_file else 'no manual'} to Gemma 4…"
        )
        try:
            procedure = synthesize_procedure(
                transcript=transcript_result["transcript"],
                segments=transcript_result["segments"],
                images=image_data,
                manual_text=pdf_result["text"],
            )
            status.update(
                label=f"✅ Procedure generated — {len(procedure.steps)} step(s)",
                state="complete",
            )
        except RuntimeError as exc:
            status.update(label="❌ Synthesis failed", state="error")
            st.error(str(exc))
            st.stop()

    # --- Stage 5: Display and download ---
    st.divider()
    st.subheader(f"📋 {procedure.title}")
    st.markdown(procedure.overview)

    # Tools & materials
    if procedure.tools_and_materials:
        with st.expander("🔧 Tools and Materials", expanded=True):
            for item in procedure.tools_and_materials:
                st.markdown(f"- {item}")

    # General warnings
    if procedure.general_warnings:
        with st.expander("⚠️ General Warnings", expanded=True):
            for w in procedure.general_warnings:
                st.warning(w)

    # Steps
    st.markdown("### Steps")
    for step in procedure.steps:
        inferred_note = " *(inferred — no direct source)*" if step.is_inferred else ""
        with st.expander(
            f"Step {step.step_number}: {step.title}{inferred_note}", expanded=True
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
                    src_lines.append("• " + " ".join(parts))
                st.markdown("**Evidence:** " + "  \n".join(src_lines))

            if step.uncertainty_note:
                st.warning(f"🔶 Uncertainty: {step.uncertainty_note}")

    # Gaps, contradictions, questions
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

    # Completion checklist
    if procedure.completion_checklist:
        st.markdown("### ✅ Completion Checklist")
        for item in procedure.completion_checklist:
            st.checkbox(item, value=False)

    st.divider()

    # --- Download ---
    markdown_output = procedure_to_markdown(procedure)
    safe_title = procedure.title.lower().replace(" ", "_")[:40]
    st.download_button(
        label="⬇️ Download procedure as Markdown",
        data=markdown_output.encode("utf-8"),
        file_name=f"{safe_title}_procedure.md",
        mime="text/markdown",
        use_container_width=True,
        type="primary",
    )
