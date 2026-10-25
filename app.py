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
# Hacktoberfest theme — injected CSS
# Palette from hacktoberfest.com brand kit:
#   Forest       #3D5F58   Deep forest  #2E4742
#   Ink          #231F20   Paper        #F2F2EB
#   Orange       #E53927   Maroon       #671912
#   Ochre        #F5B726   Sky          #8BB2DE
# ---------------------------------------------------------------------------
st.markdown(
    """
<style>
/* ── Google Fonts ── */
@import url('https://fonts.googleapis.com/css2?family=Barlow+Semi+Condensed:wght@400;600;700;800&family=Inter:wght@400;500;600&family=Martian+Mono:wght@400;600&display=swap');

/* ── Root overrides ── */
html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

/* ── Main background ── */
.stApp {
    background-color: #2E4742;
}

/* ── Top navbar strip ── */
header[data-testid="stHeader"] {
    background-color: #231F20 !important;
    border-bottom: 3px solid #E53927;
}

/* ── Sidebar ── */
section[data-testid="stSidebar"] {
    background-color: #231F20 !important;
    border-right: 2px solid #3D5F58;
}
section[data-testid="stSidebar"] * {
    color: #F2F2EB !important;
}

/* ── Main content area ── */
.block-container {
    padding-top: 2rem;
    padding-bottom: 3rem;
    max-width: 1200px;
}

/* ── App title — Barlow Semi Condensed, bold ── */
h1 {
    font-family: 'Barlow Semi Condensed', sans-serif !important;
    font-weight: 800 !important;
    font-size: 2.6rem !important;
    color: #F2F2EB !important;
    letter-spacing: -0.5px;
    text-transform: uppercase;
}

/* ── H2 / H3 — section headings ── */
h2 {
    font-family: 'Barlow Semi Condensed', sans-serif !important;
    font-weight: 700 !important;
    color: #F2F2EB !important;
    font-size: 1.8rem !important;
}
h3 {
    font-family: 'Barlow Semi Condensed', sans-serif !important;
    font-weight: 600 !important;
    color: #F5B726 !important;
    font-size: 1.3rem !important;
}
h4 {
    font-family: 'Barlow Semi Condensed', sans-serif !important;
    font-weight: 600 !important;
    color: #8BB2DE !important;
}

/* ── Orange accent on subheader ── */
h2 em, h3 em {
    color: #E53927;
    font-style: normal;
}

/* ── Body text ── */
p, li, label, .stMarkdown {
    color: #F2F2EB !important;
    font-size: 0.97rem;
    line-height: 1.6;
}

/* ── Caption / small text ── */
small, .stCaption, [data-testid="stCaptionContainer"] {
    color: #8BB2DE !important;
    font-size: 0.82rem !important;
}

/* ── Divider ── */
hr {
    border: none;
    border-top: 2px dashed #3D5F58 !important;
    margin: 1.5rem 0;
}

/* ── PRIMARY button (Generate Procedure) ── */
.stButton > button[kind="primary"],
button[data-testid="baseButton-primary"] {
    background-color: #E53927 !important;
    color: #F2F2EB !important;
    border: 2px solid #671912 !important;
    font-family: 'Barlow Semi Condensed', sans-serif !important;
    font-weight: 700 !important;
    font-size: 1.05rem !important;
    letter-spacing: 0.5px;
    text-transform: uppercase;
    border-radius: 4px !important;
    padding: 0.5rem 1.5rem !important;
    transition: background 0.15s ease;
}
.stButton > button[kind="primary"]:hover,
button[data-testid="baseButton-primary"]:hover {
    background-color: #671912 !important;
}

/* ── SECONDARY button ── */
.stButton > button[kind="secondary"],
button[data-testid="baseButton-secondary"] {
    background-color: transparent !important;
    color: #F2F2EB !important;
    border: 2px solid #F2F2EB !important;
    font-family: 'Barlow Semi Condensed', sans-serif !important;
    font-weight: 600 !important;
    text-transform: uppercase;
    border-radius: 4px !important;
    transition: border-color 0.15s ease;
}
.stButton > button[kind="secondary"]:hover {
    border-color: #E53927 !important;
    color: #E53927 !important;
}

/* ── Download button ── */
.stDownloadButton > button {
    background-color: #3D5F58 !important;
    color: #F2F2EB !important;
    border: 2px solid #F5B726 !important;
    font-family: 'Barlow Semi Condensed', sans-serif !important;
    font-weight: 700 !important;
    text-transform: uppercase;
    border-radius: 4px !important;
}
.stDownloadButton > button:hover {
    background-color: #F5B726 !important;
    color: #231F20 !important;
}

/* ── Expander — card style ── */
details[data-testid="stExpander"],
.streamlit-expanderHeader {
    background-color: #243B36 !important;
    border: 1.5px solid #3D5F58 !important;
    border-radius: 6px !important;
    margin-bottom: 0.6rem;
}
.streamlit-expanderHeader p {
    font-family: 'Barlow Semi Condensed', sans-serif !important;
    font-weight: 600 !important;
    font-size: 1.0rem !important;
    color: #F2F2EB !important;
}
details[data-testid="stExpander"] > div {
    background-color: #243B36 !important;
    border-top: 1px dashed #3D5F58 !important;
    padding: 0.8rem 1rem !important;
}

/* ── Tabs ── */
button[data-baseweb="tab"] {
    font-family: 'Barlow Semi Condensed', sans-serif !important;
    font-weight: 600 !important;
    font-size: 0.97rem !important;
    color: #8BB2DE !important;
    border-bottom: 2px solid transparent !important;
    text-transform: uppercase;
    letter-spacing: 0.4px;
}
button[data-baseweb="tab"][aria-selected="true"] {
    color: #E53927 !important;
    border-bottom: 2px solid #E53927 !important;
}
div[data-baseweb="tab-list"] {
    background-color: #243B36 !important;
    border-bottom: 1px solid #3D5F58 !important;
    gap: 0;
}
div[data-baseweb="tab-panel"] {
    background-color: #243B36 !important;
    border: 1px solid #3D5F58 !important;
    border-top: none !important;
    padding: 1rem !important;
}

/* ── File uploader ── */
[data-testid="stFileUploader"] {
    background-color: #243B36 !important;
    border: 2px dashed #3D5F58 !important;
    border-radius: 6px !important;
    padding: 0.5rem;
}
[data-testid="stFileUploader"]:hover {
    border-color: #E53927 !important;
}

/* ── Status boxes (success / info / warning / error) ── */
[data-testid="stAlert"][data-baseweb="notification"][kind="success"],
div[data-testid="stSuccessMessage"] {
    background-color: #1e3d30 !important;
    border-left: 4px solid #3D5F58 !important;
    color: #F2F2EB !important;
}
[data-testid="stAlert"][kind="warning"],
div[data-testid="stWarningMessage"] {
    background-color: #3d3410 !important;
    border-left: 4px solid #F5B726 !important;
    color: #F2F2EB !important;
}
[data-testid="stAlert"][kind="error"],
div[data-testid="stErrorMessage"] {
    background-color: #3d1010 !important;
    border-left: 4px solid #E53927 !important;
    color: #F2F2EB !important;
}
[data-testid="stAlert"][kind="info"],
div[data-testid="stInfoMessage"] {
    background-color: #1a2f3f !important;
    border-left: 4px solid #8BB2DE !important;
    color: #F2F2EB !important;
}

/* ── st.status (processing steps) ── */
[data-testid="stStatusWidget"] {
    background-color: #243B36 !important;
    border: 1px solid #3D5F58 !important;
    border-radius: 6px !important;
    color: #F2F2EB !important;
}

/* ── Code blocks ── */
code, pre {
    font-family: 'Martian Mono', monospace !important;
    background-color: #1a2d29 !important;
    color: #F5B726 !important;
    border-radius: 3px;
    font-size: 0.82rem !important;
}

/* ── Checkbox ── */
label[data-testid="stWidgetLabel"] span {
    color: #F2F2EB !important;
}
input[type="checkbox"] {
    accent-color: #E53927;
}

/* ── Selectbox / radio ── */
[data-testid="stSelectbox"] select,
[data-testid="stRadio"] {
    background-color: #243B36 !important;
    color: #F2F2EB !important;
    border: 1px solid #3D5F58 !important;
}

/* ── Metric boxes ── */
[data-testid="stMetricValue"] {
    color: #E53927 !important;
    font-family: 'Barlow Semi Condensed', sans-serif !important;
    font-weight: 800 !important;
}

/* ── Thumbnail image captions ── */
[data-testid="stImageCaption"] {
    color: #8BB2DE !important;
    font-size: 0.75rem !important;
}

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: #2E4742; }
::-webkit-scrollbar-thumb { background: #3D5F58; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #E53927; }

/* ── Hero banner (top of page) ── */
.hf-hero {
    background: linear-gradient(135deg, #231F20 0%, #2E4742 60%);
    border: 2px solid #3D5F58;
    border-radius: 8px;
    padding: 2rem 2.5rem 1.5rem;
    margin-bottom: 1.5rem;
    position: relative;
    overflow: hidden;
}
.hf-hero::before {
    content: "";
    position: absolute;
    top: 0; left: 0;
    width: 6px; height: 100%;
    background: #E53927;
}
.hf-hero h1 {
    margin: 0 0 0.3rem 0;
    font-size: 2.4rem !important;
    color: #F2F2EB !important;
}
.hf-hero h1 span { color: #E53927; }
.hf-hero p {
    margin: 0;
    color: #8BB2DE !important;
    font-size: 0.95rem;
}

/* ── Section card ── */
.hf-card {
    background-color: #243B36;
    border: 1.5px solid #3D5F58;
    border-radius: 6px;
    padding: 1.2rem 1.4rem;
    margin-bottom: 1rem;
}

/* ── Tag / badge pill ── */
.hf-tag {
    display: inline-block;
    background-color: #3D5F58;
    color: #F5B726;
    font-family: 'Martian Mono', monospace;
    font-size: 0.72rem;
    font-weight: 600;
    padding: 2px 8px;
    border-radius: 3px;
    border: 1px solid #F5B726;
    margin-right: 4px;
    letter-spacing: 0.3px;
}
.hf-tag-red  { background-color: #671912; color: #F2F2EB; border-color: #E53927; }
.hf-tag-blue { background-color: #1a2f3f; color: #8BB2DE; border-color: #8BB2DE; }

/* ── OSS library row ── */
.oss-row {
    display: flex;
    align-items: flex-start;
    gap: 0.8rem;
    padding: 0.6rem 0;
    border-bottom: 1px dashed #3D5F58;
}
.oss-row:last-child { border-bottom: none; }
.oss-name {
    font-family: 'Barlow Semi Condensed', sans-serif;
    font-weight: 700;
    color: #F5B726;
    font-size: 1rem;
}
.oss-desc { color: #F2F2EB; font-size: 0.88rem; }
.oss-lic {
    font-family: 'Martian Mono', monospace;
    font-size: 0.72rem;
    color: #8BB2DE;
}

/* ── Step card ── */
.step-number {
    font-family: 'Barlow Semi Condensed', sans-serif;
    font-weight: 800;
    font-size: 1.4rem;
    color: #E53927;
    min-width: 2rem;
}
</style>
""",
    unsafe_allow_html=True,
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
# Hero banner
# ---------------------------------------------------------------------------
st.markdown(
    """
<div class="hf-hero">
  <h1>SKILL<span>CAPTURE</span></h1>
  <p>Turn a spoken demonstration + photos + an optional manual into a
  structured, evidence-linked procedure — powered by Gemma&nbsp;4.</p>
</div>
""",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown(
        """
<div style="padding:0.5rem 0 1rem;">
  <div style="font-family:'Barlow Semi Condensed',sans-serif;font-weight:800;
              font-size:1.3rem;color:#F2F2EB;text-transform:uppercase;
              letter-spacing:1px;">
    SKILL<span style="color:#E53927;">CAPTURE</span>
  </div>
  <div style="font-size:0.75rem;color:#8BB2DE;margin-top:2px;">
    Hacktoberfest × MOSS Hack Day Udupi 2026
  </div>
</div>
""",
        unsafe_allow_html=True,
    )
    st.divider()

    st.markdown("**🤖 Model**")
    st.code(GEMMA_MODEL, language=None)
    st.markdown(
        "<span style='font-size:0.8rem;color:#8BB2DE;'>"
        "Gemma 4 via Gemini API · Google AI Studio</span>",
        unsafe_allow_html=True,
    )
    st.markdown("**🎙 Audio** · faster-whisper base int8")
    st.markdown("**📄 PDF** · Docling → pypdf fallback")
    st.divider()

    if os.getenv("GEMINI_API_KEY"):
        st.markdown(
            "<span class='hf-tag'>API KEY ✓</span>",
            unsafe_allow_html=True,
        )
    else:
        st.error("GEMINI_API_KEY not set — add it to .env")

    # Timings diagnostic
    if st.session_state["processing_done"] and st.session_state["timings"]:
        st.divider()
        st.markdown("**⏱ Stage timings**")
        for stage, secs in st.session_state["timings"].items():
            st.markdown(
                f"<div style='display:flex;justify-content:space-between;"
                f"font-size:0.82rem;padding:2px 0;'>"
                f"<span style='color:#8BB2DE;'>{stage}</span>"
                f"<span style='font-family:Martian Mono,monospace;color:#F5B726;'>"
                f"{secs:.2f}s</span></div>",
                unsafe_allow_html=True,
            )

    # Reset action
    if st.session_state["processing_done"]:
        st.divider()
        if st.button("🔄 Start new procedure", key="btn_reset",
                     use_container_width=True):
            for _k, _v in _DEFAULTS.items():
                st.session_state[_k] = _v
            st.rerun()

    st.divider()
    st.markdown(
        "<div style='font-size:0.75rem;color:#3D5F58;'>MIT License · "
        "<a href='https://github.com/udaybaheti22/hacktober-Uday' "
        "style='color:#3D5F58;'>GitHub</a></div>",
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------------------------
# Input section
# ---------------------------------------------------------------------------
col_left, col_right = st.columns([1, 1], gap="large")

with col_left:
    st.markdown(
        "<h3 style='margin-bottom:0.8rem;'>01 &nbsp;Upload inputs</h3>",
        unsafe_allow_html=True,
    )

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
    st.markdown(
        "<h3 style='margin-bottom:0.8rem;'>02 &nbsp;Uploaded files</h3>",
        unsafe_allow_html=True,
    )

    if audio_file:
        st.markdown(
            f"<div class='hf-card' style='border-color:#3D5F58;'>"
            f"🎙️ <strong>{audio_file.name}</strong> &nbsp;"
            f"<span class='hf-tag'>{_fmt_size(audio_file.size)}</span></div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            "<div style='color:#8BB2DE;font-size:0.88rem;padding:0.4rem 0;'>"
            "No audio uploaded yet.</div>",
            unsafe_allow_html=True,
        )

    if image_files:
        valid_images = [f for f in image_files if f is not None]
        if len(valid_images) < 3:
            st.warning(f"⚠️ {len(valid_images)} image(s) — at least 3 recommended.")
        elif len(valid_images) > 8:
            st.warning(f"⚠️ {len(valid_images)} images — maximum 8 will be sent.")
            valid_images = valid_images[:8]
        else:
            st.markdown(
                f"<div class='hf-card' style='border-color:#3D5F58;'>"
                f"📷 <strong>{len(valid_images)} image(s) ready</strong></div>",
                unsafe_allow_html=True,
            )

        thumb_cols = st.columns(min(4, len(valid_images)))
        for i, img in enumerate(valid_images[:4]):
            with thumb_cols[i]:
                st.image(img, caption=img.name, use_container_width=True)
    else:
        valid_images = []
        st.markdown(
            "<div style='color:#8BB2DE;font-size:0.88rem;padding:0.4rem 0;'>"
            "No images uploaded yet.</div>",
            unsafe_allow_html=True,
        )

    if pdf_file:
        st.markdown(
            f"<div class='hf-card' style='border-color:#3D5F58;'>"
            f"📄 <strong>{pdf_file.name}</strong> &nbsp;"
            f"<span class='hf-tag'>{_fmt_size(pdf_file.size)}</span></div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            "<div style='color:#8BB2DE;font-size:0.88rem;padding:0.4rem 0;'>"
            "No PDF uploaded <em>(optional)</em>.</div>",
            unsafe_allow_html=True,
        )

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
    st.markdown(
        "<div style='text-align:center;color:#8BB2DE;font-size:0.9rem;"
        "padding:0.6rem;border:1.5px dashed #3D5F58;border-radius:6px;"
        "margin-bottom:0.5rem;'>"
        "Upload at least an audio file and one image to generate a procedure.</div>",
        unsafe_allow_html=True,
    )

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

    st.markdown(
        f"<div class='hf-hero' style='margin-top:1rem;'>"
        f"<h1 style='font-size:2rem!important;'>"
        f"<span style='color:#E53927;'>📋</span> {procedure.title}</h1>"
        f"<p>{procedure.overview}</p></div>",
        unsafe_allow_html=True,
    )

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

    st.markdown(
        "<h2 style='margin-top:1.5rem;'>Procedure <span style='color:#E53927;'>Steps</span></h2>",
        unsafe_allow_html=True,
    )
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
        st.markdown(
            "<h3 style='margin-top:1.5rem;'>✅ Completion Checklist</h3>",
            unsafe_allow_html=True,
        )
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

    st.markdown(
        "<div style='text-align:center;color:#8BB2DE;font-size:0.82rem;"
        "padding:0.4rem;border-top:1px dashed #3D5F58;margin-top:0.5rem;'>"
        "Use <strong>🔄 Start new procedure</strong> in the sidebar to upload different files.</div>",
        unsafe_allow_html=True,
    )

    # -------------------------------------------------------------------------
    # Mermaid diagram views
    # Built from the already-generated procedure — no API calls.
    # -------------------------------------------------------------------------
    st.markdown(
        "<h2 style='margin-top:2rem;'>📊 Diagram <span style='color:#E53927;'>Views</span></h2>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='color:#8BB2DE;margin-top:-0.5rem;margin-bottom:1rem;'>"
        "Changing diagram type does not re-run Whisper, Docling, or Gemma 4.</p>",
        unsafe_allow_html=True,
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
    st.markdown(
        "<h2 style='margin-top:2rem;'>🔧 Open-Source <span style='color:#E53927;'>Libraries</span></h2>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='color:#8BB2DE;margin-top:-0.5rem;margin-bottom:1rem;'>"
        "The open-source tools that powered this procedure. "
        "Click any checkbox to mark it as explored.</p>",
        unsafe_allow_html=True,
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

    st.markdown("<div class='hf-card'>", unsafe_allow_html=True)
    for i, (name, description, url, lic) in enumerate(_OSS_LIBS):
        col_cb, col_info = st.columns([1, 11])
        with col_cb:
            st.checkbox("", key=f"oss_lib_{i}", label_visibility="collapsed")
        with col_info:
            st.markdown(
                f"<div class='oss-row'>"
                f"<div>"
                f"<a href='{url}' target='_blank' class='oss-name' "
                f"style='text-decoration:none;color:#F5B726;'>{name}</a>"
                f"&nbsp;&nbsp;<span class='oss-lic hf-tag-blue'>{lic}</span><br>"
                f"<span class='oss-desc'>{description}</span>"
                f"</div></div>",
                unsafe_allow_html=True,
            )
    st.markdown("</div>", unsafe_allow_html=True)
