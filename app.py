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
# Utilities
# ---------------------------------------------------------------------------
def _fmt_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 ** 2:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / 1024**2:.1f} MB"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# ---------------------------------------------------------------------------
# Page config  — must be the very first Streamlit call
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="SkillCapture",
    page_icon="🎓",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Design system — CSS variables + full theme
#
# Palette (retro editorial, inspired by open-source community aesthetic):
#   --forest   #36564F   (hero bg, header)
#   --cream    #F5F3E8   (main page bg, card bg)
#   --ink      #17221F   (text, borders, shadows)
#   --coral    #E76F5A   (primary CTA, step numbers, error accents)
#   --blue     #91B0DF   (secondary labels, info, evidence badges)
#   --mustard  #F3C64E   (highlights, warnings, hover fills)
#   --gray     #BACBC3   (muted text, dividers)
# ---------------------------------------------------------------------------
st.markdown("""
<style>
/* ── Design tokens ── */
:root {
  --forest:  #36564F;
  --cream:   #F5F3E8;
  --ink:     #17221F;
  --coral:   #E76F5A;
  --blue:    #91B0DF;
  --mustard: #F3C64E;
  --gray:    #BACBC3;
  --shadow:  3px 3px 0 var(--ink);
  --shadow-lg: 5px 5px 0 var(--ink);
  --radius:  4px;
}

/* ── Fonts — system stack that doesn't need Google Fonts to load ── */
/* Georgia gives the editorial serif feel; system-ui for body. */
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=DM+Sans:wght@400;500;600&family=DM+Mono:wght@400;500&display=swap');

/* ── Global reset ── */
html, body, [class*="css"] {
  font-family: 'DM Sans', system-ui, sans-serif !important;
  -webkit-font-smoothing: antialiased;
}

/* ── Page background — warm cream with a subtle dot-grid texture ── */
.stApp {
  background-color: var(--cream) !important;
  background-image: radial-gradient(var(--gray) 1px, transparent 1px);
  background-size: 22px 22px;
}

/* ── Streamlit toolbar / top bar — hide it for cleaner look ── */
header[data-testid="stHeader"] {
  background: transparent !important;
  border-bottom: none !important;
  height: 0 !important;
}
[data-testid="stToolbar"] { display: none !important; }

/* ── Sidebar — forest green, clean ── */
section[data-testid="stSidebar"] {
  background-color: var(--forest) !important;
  border-right: 2px solid var(--ink) !important;
  box-shadow: 3px 0 0 var(--ink);
}
section[data-testid="stSidebar"] * { color: var(--cream) !important; }
section[data-testid="stSidebar"] a { color: var(--mustard) !important; text-decoration: underline; }
section[data-testid="stSidebar"] code {
  background: rgba(0,0,0,0.3) !important;
  color: var(--mustard) !important;
}

/* ── Main content container ── */
.block-container {
  padding-top: 0 !important;
  padding-bottom: 4rem;
  max-width: 1140px;
}

/* ── Typography ── */
h1, h2, h3, h4 {
  font-family: 'Syne', Georgia, serif !important;
  color: var(--ink) !important;
  letter-spacing: -0.02em;
}
h1 { font-size: 3rem !important; font-weight: 800 !important; line-height: 1.1; }
h2 { font-size: 2rem !important; font-weight: 800 !important; line-height: 1.2; }
h3 { font-size: 1.35rem !important; font-weight: 700 !important; }
h4 { font-size: 1.05rem !important; font-weight: 700 !important; color: var(--forest) !important; }
p, li, label { color: var(--ink) !important; font-size: 0.97rem; line-height: 1.65; }
strong { color: var(--ink) !important; }

/* ── Dividers ── */
hr {
  border: none !important;
  border-top: 2px solid var(--ink) !important;
  margin: 2.5rem 0 !important;
  opacity: 0.15 !important;
}

/* ── Captions ── */
small, [data-testid="stCaptionContainer"], .stCaption {
  color: var(--gray) !important;
  font-size: 0.8rem !important;
}

/* ── ────────────────────────────────────────────── ── */
/* ── CUSTOM LAYOUT COMPONENTS                       ── */
/* ── ────────────────────────────────────────────── ── */

/* Top navigation bar */
.sc-nav {
  background: var(--forest);
  border-bottom: 2px solid var(--ink);
  padding: 0.85rem 2rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin: -1rem -4rem 0;   /* bleed to container edges */
  box-shadow: 0 2px 0 var(--ink);
}
.sc-nav-logo {
  font-family: 'Syne', Georgia, serif;
  font-weight: 800;
  font-size: 1.3rem;
  color: var(--cream) !important;
  letter-spacing: -0.03em;
  text-transform: uppercase;
}
.sc-nav-logo span { color: var(--coral); }
.sc-nav-sub {
  font-size: 0.78rem;
  color: var(--gray) !important;
  margin-top: 1px;
  font-family: 'DM Mono', monospace;
}
.sc-nav-links {
  display: flex;
  gap: 1.5rem;
  align-items: center;
}
.sc-nav-links a {
  font-size: 0.82rem;
  color: var(--cream) !important;
  text-decoration: none;
  font-family: 'DM Mono', monospace;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  border-bottom: 1px solid transparent;
  padding-bottom: 1px;
  transition: border-color 0.1s;
}
.sc-nav-links a:hover { border-color: var(--mustard); color: var(--mustard) !important; }
.sc-nav-badge {
  background: var(--coral);
  color: var(--cream) !important;
  font-size: 0.7rem;
  font-family: 'DM Mono', monospace;
  font-weight: 500;
  padding: 3px 10px;
  border: 1.5px solid var(--ink);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  text-decoration: none;
}

/* Hero section */
.sc-hero {
  background: var(--forest);
  border: 2px solid var(--ink);
  border-top: none;
  padding: 3.5rem 2.5rem 3rem;
  position: relative;
  overflow: hidden;
  margin: 0 -4rem 0;
  box-shadow: 0 4px 0 var(--ink);
}
/* CSS pixel-art decorative grid — top-right corner */
.sc-hero::after {
  content: "";
  position: absolute;
  top: 18px; right: 24px;
  width: 72px; height: 72px;
  background-image:
    linear-gradient(var(--coral) 0%, var(--coral) 100%),
    linear-gradient(var(--mustard) 0%, var(--mustard) 100%),
    linear-gradient(var(--coral) 0%, var(--coral) 100%),
    linear-gradient(var(--blue) 0%, var(--blue) 100%),
    linear-gradient(var(--coral) 0%, var(--coral) 100%),
    linear-gradient(var(--mustard) 0%, var(--mustard) 100%);
  background-size: 12px 12px;
  background-position:
    0 0, 12px 0, 24px 0,
    0 12px, 12px 12px, 24px 12px;
  background-repeat: no-repeat;
  opacity: 0.7;
}
.sc-hero-eyebrow {
  font-family: 'DM Mono', monospace;
  font-size: 0.72rem;
  font-weight: 500;
  color: var(--mustard) !important;
  text-transform: uppercase;
  letter-spacing: 0.15em;
  margin-bottom: 0.8rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
.sc-hero-eyebrow::before {
  content: "";
  display: inline-block;
  width: 20px; height: 2px;
  background: var(--coral);
}
.sc-hero h1 {
  color: var(--cream) !important;
  font-size: 3.2rem !important;
  font-weight: 800 !important;
  line-height: 1.05 !important;
  margin: 0 0 1rem !important;
  max-width: 700px;
}
.sc-hero h1 em {
  color: var(--coral);
  font-style: normal;
}
.sc-hero-body {
  color: var(--gray) !important;
  font-size: 1.05rem;
  max-width: 580px;
  line-height: 1.6;
  margin-bottom: 1.8rem;
}
.sc-tech-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-top: 1.5rem;
}
.sc-tech-pill {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  background: rgba(255,255,255,0.1);
  border: 1.5px solid rgba(255,255,255,0.3);
  color: var(--cream) !important;
  font-family: 'DM Mono', monospace;
  font-size: 0.78rem;
  padding: 4px 12px;
  border-radius: var(--radius);
  letter-spacing: 0.04em;
}
.sc-tech-pill .dot {
  width: 7px; height: 7px;
  border-radius: 50%;
  background: var(--mustard);
  flex-shrink: 0;
}

/* Section wrapper — light cream card with offset shadow */
.sc-section {
  background: var(--cream);
  border: 2px solid var(--ink);
  border-radius: var(--radius);
  padding: 2rem 2rem 1.5rem;
  margin-bottom: 2rem;
  box-shadow: var(--shadow-lg);
  position: relative;
}
.sc-section-label {
  position: absolute;
  top: -14px; left: 20px;
  background: var(--coral);
  color: var(--cream) !important;
  font-family: 'DM Mono', monospace;
  font-size: 0.68rem;
  font-weight: 500;
  padding: 2px 10px;
  border: 1.5px solid var(--ink);
  border-radius: var(--radius);
  text-transform: uppercase;
  letter-spacing: 0.1em;
}

/* Input card — outlined, hard shadow */
.sc-input-card {
  border: 2px solid var(--ink);
  border-radius: var(--radius);
  padding: 1.4rem 1.4rem 1rem;
  background: white;
  box-shadow: var(--shadow);
  height: 100%;
}
.sc-input-card-icon {
  font-size: 1.6rem;
  margin-bottom: 0.4rem;
  line-height: 1;
}
.sc-input-card-title {
  font-family: 'Syne', Georgia, serif;
  font-weight: 800;
  font-size: 0.85rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--forest) !important;
  margin-bottom: 0.2rem;
}
.sc-input-card-sub {
  font-size: 0.75rem;
  color: var(--gray) !important;
  font-family: 'DM Mono', monospace;
  margin-bottom: 0.8rem;
}
.sc-file-pill {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  background: var(--cream);
  border: 1.5px solid var(--ink);
  border-radius: var(--radius);
  padding: 4px 10px;
  font-family: 'DM Mono', monospace;
  font-size: 0.76rem;
  color: var(--ink) !important;
  margin-top: 0.5rem;
  box-shadow: 2px 2px 0 var(--ink);
}
.sc-file-pill .sz {
  color: var(--gray) !important;
  font-size: 0.7rem;
}

/* Status pill for upload state */
.sc-status { display: inline-block; padding: 2px 8px; border-radius: var(--radius);
  font-family: 'DM Mono', monospace; font-size: 0.7rem; border: 1.5px solid; }
.sc-status-empty  { background: var(--cream); color: var(--gray) !important; border-color: var(--gray); }
.sc-status-ready  { background: #e8f5f0; color: var(--forest) !important; border-color: var(--forest); }
.sc-status-opt    { background: #fdf9ec; color: #7a6020 !important; border-color: var(--mustard); }

/* Generate CTA area */
.sc-cta-wrap {
  border: 2px solid var(--ink);
  border-radius: var(--radius);
  background: var(--forest);
  padding: 1.8rem 2rem;
  box-shadow: var(--shadow-lg);
  display: flex;
  flex-direction: column;
  gap: 1rem;
}
.sc-cta-prompt {
  color: var(--gray) !important;
  font-size: 0.88rem;
  line-height: 1.55;
}
.sc-pipeline {
  display: flex;
  flex-wrap: wrap;
  gap: 0.6rem;
  align-items: center;
}
.sc-pipeline-step {
  font-family: 'DM Mono', monospace;
  font-size: 0.73rem;
  color: var(--cream) !important;
  background: rgba(255,255,255,0.1);
  border: 1px solid rgba(255,255,255,0.25);
  padding: 3px 10px;
  border-radius: var(--radius);
}
.sc-pipeline-arrow { color: var(--coral) !important; font-size: 0.9rem; }

/* Procedure output */
.sc-proc-banner {
  background: var(--forest);
  border: 2px solid var(--ink);
  border-radius: var(--radius);
  padding: 2rem 2.5rem;
  margin-bottom: 2rem;
  box-shadow: var(--shadow-lg);
  position: relative;
}
.sc-proc-banner::before {
  content: "GENERATED PROCEDURE";
  position: absolute; top: -13px; left: 18px;
  background: var(--mustard);
  color: var(--ink) !important;
  font-family: 'DM Mono', monospace; font-size: 0.65rem;
  padding: 2px 10px; border: 1.5px solid var(--ink);
  border-radius: var(--radius); letter-spacing: 0.1em;
}
.sc-proc-banner h2 {
  color: var(--cream) !important;
  font-size: 2rem !important;
  margin: 0 0 0.6rem !important;
}
.sc-proc-banner p { color: var(--gray) !important; margin: 0; font-size: 1rem; }

/* Step cards */
.sc-step {
  border: 1.5px solid var(--ink);
  border-left: 5px solid var(--coral);
  border-radius: var(--radius);
  background: white;
  padding: 1.2rem 1.4rem;
  margin-bottom: 1rem;
  box-shadow: var(--shadow);
  position: relative;
}
.sc-step.inferred { border-left-color: var(--blue); }
.sc-step.review   { border-left-color: var(--mustard); }
.sc-step-num {
  font-family: 'Syne', Georgia, serif;
  font-weight: 800; font-size: 2.2rem;
  color: var(--coral); line-height: 1;
  margin-right: 0.8rem; min-width: 2rem;
}
.sc-step-num.inferred { color: var(--blue); }
.sc-step-title {
  font-family: 'Syne', Georgia, serif;
  font-weight: 700; font-size: 1.05rem;
  color: var(--ink) !important; line-height: 1.2;
}
.sc-step-badge {
  font-family: 'DM Mono', monospace; font-size: 0.65rem;
  padding: 2px 7px; border-radius: var(--radius);
  border: 1.5px solid; display: inline-block; margin-left: 0.4rem;
}
.sc-step-badge.inf { background: #e8eef8; color: var(--blue) !important; border-color: var(--blue); }
.sc-step-badge.rev { background: #fdf9ec; color: #7a6020 !important; border-color: var(--mustard); }
.sc-step-body { color: var(--ink) !important; font-size: 0.95rem; line-height: 1.65; margin-top: 0.6rem; }
.sc-step-sep { border: none; border-top: 1px dashed var(--gray); margin: 0.8rem 0; }

/* Evidence tags */
.sc-ev {
  display: inline-flex; align-items: center; gap: 0.25rem;
  font-family: 'DM Mono', monospace; font-size: 0.7rem;
  padding: 2px 8px; border-radius: var(--radius);
  border: 1.5px solid; margin: 2px;
}
.sc-ev-t { background: #e8f5f0; color: var(--forest) !important; border-color: var(--forest); }
.sc-ev-i { background: #e8eef8; color: #3a5a8a !important; border-color: var(--blue); }
.sc-ev-m { background: #fdf9ec; color: #7a6020 !important; border-color: var(--mustard); }
.sc-ev-x { background: #f5f0f8; color: #6a3a8a !important; border-color: #b07ad0; }

/* Evidence status colours */
.sc-ev-supported  { color: var(--forest) !important; }
.sc-ev-partial    { color: #7a6020 !important; }
.sc-ev-conflict   { color: #b03030 !important; }
.sc-ev-insuf      { color: var(--gray) !important; }

/* Checkpoint */
.sc-checkpoint {
  background: #e8f5f0; border: 1.5px solid var(--forest);
  border-radius: var(--radius); padding: 0.5rem 0.9rem;
  font-size: 0.88rem; color: var(--forest) !important;
  display: flex; gap: 0.5rem; align-items: flex-start;
  margin-top: 0.5rem;
}
.sc-checkpoint::before { content: "✓"; font-weight: 800; flex-shrink: 0; }

/* Meta grid — missing info / contradictions / questions */
.sc-meta-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem; margin-top: 1.5rem; }
.sc-meta-box {
  border: 1.5px solid var(--ink); border-radius: var(--radius);
  padding: 1rem; background: white; box-shadow: var(--shadow);
}
.sc-meta-box-title {
  font-family: 'DM Mono', monospace; font-size: 0.7rem;
  text-transform: uppercase; letter-spacing: 0.08em;
  margin-bottom: 0.6rem; padding-bottom: 0.4rem;
  border-bottom: 1px solid var(--ink);
  color: var(--ink) !important;
}
.sc-meta-box ul { margin: 0; padding-left: 1.1rem; }
.sc-meta-box li { font-size: 0.85rem; margin-bottom: 0.25rem; color: var(--ink) !important; }

/* Checklist */
.sc-checklist { list-style: none; padding: 0; margin: 0; }
.sc-checklist li { padding: 0.4rem 0; border-bottom: 1px dashed var(--gray); font-size: 0.93rem; }
.sc-checklist li:last-child { border-bottom: none; }

/* Export area */
.sc-export {
  border: 2px solid var(--ink); border-radius: var(--radius);
  background: var(--cream); padding: 1.5rem 2rem;
  box-shadow: var(--shadow-lg); margin-top: 2rem;
  display: flex; flex-direction: column; gap: 0.8rem;
}
.sc-export-title {
  font-family: 'Syne', Georgia, serif; font-weight: 800;
  font-size: 1rem; text-transform: uppercase; letter-spacing: 0.06em;
  color: var(--ink) !important; margin-bottom: 0.2rem;
}

/* Diagram section */
.sc-diagram-wrap {
  border: 2px solid var(--ink); border-radius: var(--radius);
  background: white; padding: 1.5rem;
  box-shadow: var(--shadow-lg);
}

/* OSS library row */
.sc-oss-row {
  display: flex; align-items: flex-start; gap: 0.8rem;
  padding: 0.7rem 0; border-bottom: 1px dashed rgba(23,34,31,0.15);
}
.sc-oss-row:last-child { border-bottom: none; }
.sc-oss-name { font-family: 'Syne', Georgia, serif; font-weight: 700;
  color: var(--forest) !important; font-size: 0.95rem; }
.sc-oss-desc { color: var(--ink) !important; font-size: 0.85rem; }
.sc-oss-lic  { font-family: 'DM Mono', monospace; font-size: 0.68rem;
  color: white !important; background: var(--forest);
  border: 1px solid var(--ink); border-radius: var(--radius); padding: 1px 6px; }

/* ── Streamlit widget overrides ── */

/* Primary button — coral, hard offset shadow */
.stButton > button[kind="primary"],
button[data-testid="baseButton-primary"] {
  background: var(--coral) !important;
  color: white !important;
  border: 2px solid var(--ink) !important;
  font-family: 'Syne', Georgia, serif !important;
  font-weight: 800 !important;
  font-size: 1.1rem !important;
  letter-spacing: 0.03em;
  text-transform: uppercase;
  border-radius: var(--radius) !important;
  box-shadow: var(--shadow-lg) !important;
  padding: 0.65rem 2rem !important;
  transition: box-shadow 0.1s, transform 0.1s;
}
.stButton > button[kind="primary"]:hover {
  background: #d45a47 !important;
  box-shadow: 2px 2px 0 var(--ink) !important;
  transform: translate(1px, 1px);
}
.stButton > button[kind="primary"]:disabled {
  background: var(--gray) !important;
  color: rgba(255,255,255,0.6) !important;
  box-shadow: none !important;
  transform: none !important;
  border-color: var(--gray) !important;
  cursor: not-allowed !important;
}

/* Secondary button */
.stButton > button[kind="secondary"] {
  background: transparent !important;
  color: var(--ink) !important;
  border: 2px solid var(--ink) !important;
  font-family: 'DM Sans', sans-serif !important;
  font-weight: 600 !important;
  border-radius: var(--radius) !important;
  box-shadow: var(--shadow) !important;
  transition: box-shadow 0.1s, transform 0.1s;
}
.stButton > button[kind="secondary"]:hover {
  background: var(--mustard) !important;
  box-shadow: 1px 1px 0 var(--ink) !important;
  transform: translate(1px, 1px);
}

/* Download button */
.stDownloadButton > button {
  background: var(--forest) !important;
  color: var(--cream) !important;
  border: 2px solid var(--ink) !important;
  font-family: 'DM Sans', sans-serif !important;
  font-weight: 600 !important;
  border-radius: var(--radius) !important;
  box-shadow: var(--shadow) !important;
  transition: box-shadow 0.1s, transform 0.1s;
}
.stDownloadButton > button:hover {
  background: #2a4640 !important;
  box-shadow: 1px 1px 0 var(--ink) !important;
  transform: translate(1px, 1px);
}

/* File uploader — cream bg, dark border */
[data-testid="stFileUploader"] {
  background: var(--cream) !important;
  border: 1.5px dashed var(--ink) !important;
  border-radius: var(--radius) !important;
  padding: 0.4rem !important;
}
[data-testid="stFileUploader"]:hover { border-color: var(--coral) !important; }
[data-testid="stFileUploader"] label p { color: var(--ink) !important; font-size: 0.88rem !important; }
[data-testid="stFileUploaderDropzone"] { background: transparent !important; }

/* Expander */
details[data-testid="stExpander"] {
  border: 1.5px solid rgba(23,34,31,0.18) !important;
  border-radius: var(--radius) !important;
  background: white !important;
  margin-bottom: 0.5rem;
}
.streamlit-expanderHeader p {
  font-family: 'DM Sans', sans-serif !important;
  font-weight: 600 !important; font-size: 0.92rem !important;
  color: var(--ink) !important;
}
details[data-testid="stExpander"] > div {
  background: white !important;
  border-top: 1px dashed rgba(23,34,31,0.15) !important;
}

/* Tabs */
div[data-baseweb="tab-list"] {
  background: transparent !important;
  border-bottom: 2px solid var(--ink) !important;
  gap: 0;
}
button[data-baseweb="tab"] {
  font-family: 'DM Sans', sans-serif !important;
  font-weight: 600 !important; font-size: 0.9rem !important;
  color: var(--gray) !important;
  border-bottom: 3px solid transparent !important;
  background: transparent !important;
  text-transform: uppercase; letter-spacing: 0.04em;
  padding: 0.5rem 1.2rem !important;
}
button[data-baseweb="tab"][aria-selected="true"] {
  color: var(--ink) !important;
  border-bottom: 3px solid var(--coral) !important;
}
div[data-baseweb="tab-panel"] {
  background: white !important;
  border: 1.5px solid rgba(23,34,31,0.18) !important;
  border-top: none !important;
  padding: 1.2rem !important;
}

/* Alert / status boxes */
div[data-testid="stSuccessMessage"] {
  background: #e8f5f0 !important; border-left: 4px solid var(--forest) !important;
  color: var(--ink) !important;
}
div[data-testid="stWarningMessage"] {
  background: #fdf9ec !important; border-left: 4px solid var(--mustard) !important;
  color: var(--ink) !important;
}
div[data-testid="stErrorMessage"] {
  background: #fceae7 !important; border-left: 4px solid var(--coral) !important;
  color: var(--ink) !important;
}
div[data-testid="stInfoMessage"] {
  background: #edf2fb !important; border-left: 4px solid var(--blue) !important;
  color: var(--ink) !important;
}
[data-testid="stStatusWidget"] {
  background: white !important; border: 1.5px solid var(--ink) !important;
  border-radius: var(--radius) !important;
}

/* Code */
code, pre {
  font-family: 'DM Mono', monospace !important;
  background: #f0ede0 !important;
  color: var(--forest) !important;
  border-radius: var(--radius);
  font-size: 0.82rem !important;
}

/* Checkbox */
input[type="checkbox"] { accent-color: var(--forest); }
label[data-testid="stWidgetLabel"] span { color: var(--ink) !important; }

/* Scrollbar */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: var(--cream); }
::-webkit-scrollbar-thumb { background: var(--gray); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: var(--coral); }

/* Image captions */
[data-testid="stImageCaption"] { color: var(--gray) !important; font-size: 0.72rem !important; }

/* Responsive — tighter padding on narrow screens */
@media (max-width: 768px) {
  .sc-nav { margin: -1rem -1rem 0; padding: 0.7rem 1rem; }
  .sc-hero { margin: 0 -1rem 0; padding: 2rem 1.2rem; }
  .sc-hero h1 { font-size: 2.1rem !important; }
  .sc-meta-grid { grid-template-columns: 1fr; }
  .sc-nav-links { display: none; }
  .block-container { padding-bottom: 2rem; }
}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Imports  (after st.set_page_config + CSS)
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
# ---------------------------------------------------------------------------
@st.cache_resource(show_spinner=False)
def _load_whisper_model():
    try:
        model, init_seconds = get_whisper_model()
        return model, init_seconds, None
    except RuntimeError as exc:
        return None, 0.0, str(exc)


@st.cache_resource(show_spinner=False)
def _load_docling_converter():
    try:
        converter, init_seconds = get_docling_converter()
        return converter, init_seconds, None
    except RuntimeError as exc:
        return None, 0.0, str(exc)


# ---------------------------------------------------------------------------
# Cached processing  (content-hash keyed — safe across reruns)
# ---------------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def _cached_transcribe(audio_sha256: str, audio_bytes: bytes) -> dict:
    whisper_model, _init_secs, model_error = _load_whisper_model()
    if model_error:
        return {
            "transcript": "", "segments": [],
            "decode_seconds": 0.0, "transcribe_seconds": 0.0,
            "error": f"Whisper model failed to load: {model_error}",
        }
    return transcribe_audio_with_model(whisper_model, audio_bytes)


@st.cache_data(show_spinner=False)
def _cached_extract_pdf(pdf_sha256: str, pdf_bytes: bytes, filename: str) -> dict:
    converter, _init_secs, conv_error = _load_docling_converter()
    return extract_pdf(pdf_bytes, filename,
                       converter=converter if not conv_error else None)


# ---------------------------------------------------------------------------
# Session-state initialisation  (guard — safe to call on every rerun)
# ---------------------------------------------------------------------------
_DEFAULTS: dict = {
    "procedure":           None,
    "transcript":          None,
    "pdf_result":          None,
    "image_data":          None,
    "processing_done":     False,
    "error_msg":           None,
    "timings":             {},
    "validation_warnings": [],
}
for _k, _v in _DEFAULTS.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v

# ---------------------------------------------------------------------------
# SIDEBAR
# ---------------------------------------------------------------------------
REPO_URL = "https://github.com/udaybaheti22/hacktober-Uday"

with st.sidebar:
    st.markdown("""
<div style="padding:0.6rem 0 1.2rem;">
  <div style="font-family:'Syne',Georgia,serif;font-weight:800;font-size:1.25rem;
              color:#F5F3E8;text-transform:uppercase;letter-spacing:-0.02em;">
    Skill<span style="color:#E76F5A;">Capture</span>
  </div>
  <div style="font-size:0.72rem;color:#BACBC3;margin-top:3px;
              font-family:'DM Mono',monospace;">
    Multimodal knowledge tool
  </div>
</div>
""", unsafe_allow_html=True)

    st.divider()
    st.markdown("**Model**")
    st.code(GEMMA_MODEL, language=None)
    st.markdown(
        "<span style='font-size:0.78rem;color:#BACBC3;font-family:DM Mono,monospace;'>"
        "Gemma 4 · Gemini API</span>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<div style='font-size:0.82rem;margin-top:0.7rem;'>"
        "<b>Audio</b> · faster-whisper base<br>"
        "<b>PDF</b> · Docling → pypdf fallback</div>",
        unsafe_allow_html=True,
    )
    st.divider()

    if os.getenv("GEMINI_API_KEY"):
        st.markdown(
            "<span style='background:#36564F;color:#F5F3E8;font-family:DM Mono,monospace;"
            "font-size:0.72rem;padding:3px 10px;border:1.5px solid #F5F3E8;"
            "border-radius:4px;'>API KEY ✓</span>",
            unsafe_allow_html=True,
        )
    else:
        st.error("GEMINI_API_KEY not set")

    if st.session_state["processing_done"] and st.session_state["timings"]:
        st.divider()
        st.markdown("**Stage timings**")
        for stage, secs in st.session_state["timings"].items():
            st.markdown(
                f"<div style='display:flex;justify-content:space-between;"
                f"font-size:0.8rem;padding:2px 0;border-bottom:1px dashed rgba(186,203,195,0.3);'>"
                f"<span style='color:#BACBC3;'>{stage}</span>"
                f"<span style='font-family:DM Mono,monospace;color:#F3C64E;'>"
                f"{secs:.2f}s</span></div>",
                unsafe_allow_html=True,
            )

    if st.session_state["processing_done"]:
        st.divider()
        if st.button("Start new procedure", key="btn_reset",
                     use_container_width=True):
            for _k, _v in _DEFAULTS.items():
                st.session_state[_k] = _v
            st.rerun()

    st.divider()
    st.markdown(
        f"<div style='font-size:0.72rem;color:rgba(186,203,195,0.6);'>"
        f"MIT License · "
        f"<a href='{REPO_URL}' style='color:#91B0DF;'>GitHub</a></div>",
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------------------------
# TOP NAVIGATION BAR
# ---------------------------------------------------------------------------
st.markdown(f"""
<div class="sc-nav">
  <div>
    <div class="sc-nav-logo">Skill<span>Capture</span></div>
    <div class="sc-nav-sub">Turn demonstrations into reusable knowledge.</div>
  </div>
  <div class="sc-nav-links">
    <a href="#how-it-works">How it works</a>
    <a href="{REPO_URL}" target="_blank" class="sc-nav-badge">Open source</a>
  </div>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# HERO SECTION
# ---------------------------------------------------------------------------
st.markdown("""
<div class="sc-hero">
  <div class="sc-hero-eyebrow">Multimodal Knowledge Tool</div>
  <h1>Turn demonstrations<br>into <em>instructions.</em></h1>
  <p class="sc-hero-body">
    SkillCapture combines a spoken explanation, step photographs, and a
    reference manual into an evidence-linked procedure — with source citations,
    uncertainty flags, and a Mermaid workflow diagram.
  </p>
  <div class="sc-tech-row">
    <span class="sc-tech-pill"><span class="dot"></span>Gemma&nbsp;4</span>
    <span class="sc-tech-pill"><span class="dot"></span>Whisper</span>
    <span class="sc-tech-pill"><span class="dot"></span>Docling</span>
    <span class="sc-tech-pill"><span class="dot"></span>Pydantic</span>
    <span class="sc-tech-pill"><span class="dot"></span>Mermaid</span>
  </div>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# INPUT WORKSPACE  — "Build a procedure"
# ---------------------------------------------------------------------------
st.markdown("""
<div style="margin-top:2.5rem;margin-bottom:0.5rem;">
  <div style="font-family:'DM Mono',monospace;font-size:0.7rem;
              text-transform:uppercase;letter-spacing:0.12em;color:#BACBC3;
              margin-bottom:0.3rem;">Section 01</div>
  <h2 style="margin:0 0 0.2rem;">Build a procedure.</h2>
  <p style="color:#BACBC3;font-size:0.9rem;margin:0 0 1.5rem;">
    Provide your demonstration materials below. All processing runs locally
    — your files never leave this machine except for the Gemini API call.
  </p>
</div>
""", unsafe_allow_html=True)

c1, c2, c3 = st.columns(3, gap="medium")

with c1:
    st.markdown("""
<div class="sc-input-card">
  <div class="sc-input-card-icon">🎙</div>
  <div class="sc-input-card-title">Audio Recording</div>
  <div class="sc-input-card-sub">MP3 · WAV · M4A · OGG · FLAC · WebM · AAC</div>
</div>
""", unsafe_allow_html=True)
    audio_file = st.file_uploader(
        "Upload audio",
        type=["mp3", "wav", "m4a", "ogg", "flac", "webm", "aac"],
        help="A recording of someone explaining or demonstrating the process.",
        key="uploader_audio",
        label_visibility="collapsed",
    )
    if audio_file:
        st.markdown(
            f"<div class='sc-file-pill'>🎵 {audio_file.name}"
            f"<span class='sz'>{_fmt_size(audio_file.size)}</span></div>"
            f"<span class='sc-status sc-status-ready'>READY</span>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            "<span class='sc-status sc-status-empty'>AWAITING UPLOAD</span>",
            unsafe_allow_html=True,
        )

with c2:
    st.markdown("""
<div class="sc-input-card">
  <div class="sc-input-card-icon">📷</div>
  <div class="sc-input-card-title">Step Photographs</div>
  <div class="sc-input-card-sub">3–8 images · JPG · PNG · WebP · BMP</div>
</div>
""", unsafe_allow_html=True)
    image_files = st.file_uploader(
        "Upload photos",
        type=["jpg", "jpeg", "png", "webp", "bmp"],
        accept_multiple_files=True,
        help="Upload photos showing the key steps of the process.",
        key="uploader_images",
        label_visibility="collapsed",
    )
    if image_files:
        valid_images = [f for f in image_files if f is not None]
        if len(valid_images) > 8:
            st.warning(f"Maximum 8 images — only first 8 will be sent.")
            valid_images = valid_images[:8]
        n = len(valid_images)
        status_cls = "sc-status-ready" if n >= 3 else "sc-status-opt"
        status_txt = f"{n} IMAGE{'S' if n != 1 else ''} READY" if n >= 3 else f"{n} IMAGE{'S' if n != 1 else ''} — 3 MIN."
        st.markdown(
            f"<span class='sc-status {status_cls}'>{status_txt}</span>",
            unsafe_allow_html=True,
        )
        if n > 0:
            thumb_cols = st.columns(min(4, n))
            for i, img in enumerate(valid_images[:4]):
                with thumb_cols[i]:
                    st.image(img, caption=img.name, use_container_width=True)
    else:
        valid_images = []
        st.markdown(
            "<span class='sc-status sc-status-empty'>AWAITING UPLOAD</span>",
            unsafe_allow_html=True,
        )

with c3:
    st.markdown("""
<div class="sc-input-card">
  <div class="sc-input-card-icon">📄</div>
  <div class="sc-input-card-title">Reference Manual</div>
  <div class="sc-input-card-sub">PDF · optional</div>
</div>
""", unsafe_allow_html=True)
    pdf_file = st.file_uploader(
        "Upload PDF",
        type=["pdf"],
        help="Upload a supporting manual or instructions document.",
        key="uploader_pdf",
        label_visibility="collapsed",
    )
    if pdf_file:
        st.markdown(
            f"<div class='sc-file-pill'>📄 {pdf_file.name}"
            f"<span class='sz'>{_fmt_size(pdf_file.size)}</span></div>"
            f"<span class='sc-status sc-status-ready'>READY</span>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            "<span class='sc-status sc-status-opt'>OPTIONAL</span>",
            unsafe_allow_html=True,
        )

# ---------------------------------------------------------------------------
# GENERATE CTA
# ---------------------------------------------------------------------------
can_generate = (
    audio_file is not None
    and len(valid_images) >= 1
    and not st.session_state["processing_done"]
)

st.markdown("<div style='height:1.5rem;'></div>", unsafe_allow_html=True)

cta_col, info_col = st.columns([2, 3], gap="large")

with cta_col:
    st.markdown("""
<div class="sc-cta-wrap">
  <p class="sc-cta-prompt">
    Upload an audio recording and at least one photograph to generate
    a structured, evidence-linked procedure.
  </p>
  <div class="sc-pipeline">
    <span class="sc-pipeline-step">Whisper transcription</span>
    <span class="sc-pipeline-arrow">→</span>
    <span class="sc-pipeline-step">Docling extraction</span>
    <span class="sc-pipeline-arrow">→</span>
    <span class="sc-pipeline-step">Gemma 4 synthesis</span>
    <span class="sc-pipeline-arrow">→</span>
    <span class="sc-pipeline-step">Pydantic validation</span>
  </div>
</div>
""", unsafe_allow_html=True)
    if not can_generate and not st.session_state["processing_done"]:
        st.markdown(
            "<div style='font-family:DM Mono,monospace;font-size:0.78rem;"
            "color:#BACBC3;margin-top:0.4rem;'>Awaiting required inputs.</div>",
            unsafe_allow_html=True,
        )
    generate_btn = st.button(
        "Generate procedure",
        disabled=not can_generate,
        type="primary",
        use_container_width=True,
        key="btn_generate",
    )

with info_col:
    st.markdown("""
<div style="padding:1.2rem 0;">
  <div style="font-family:'DM Mono',monospace;font-size:0.7rem;
              text-transform:uppercase;letter-spacing:0.1em;color:#BACBC3;
              margin-bottom:0.8rem;" id="how-it-works">How it works</div>
  <ol style="margin:0;padding-left:1.2rem;color:#17221F;">
    <li style="margin-bottom:0.45rem;font-size:0.88rem;">
      <strong>faster-whisper</strong> transcribes your audio locally with
      timestamps — no data sent to a remote speech API.
    </li>
    <li style="margin-bottom:0.45rem;font-size:0.88rem;">
      <strong>Docling</strong> extracts structured text from your PDF, preserving
      page references for evidence attribution.
    </li>
    <li style="margin-bottom:0.45rem;font-size:0.88rem;">
      <strong>Gemma 4</strong> receives all three sources — transcript, photographs,
      and manual — in a single multimodal prompt and performs cross-modal
      evidence reconciliation.
    </li>
    <li style="font-size:0.88rem;">
      <strong>Pydantic</strong> validates the structured JSON output against a
      defined schema before anything is displayed.
    </li>
  </ol>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# PROCESSING PIPELINE
# ---------------------------------------------------------------------------
if generate_btn and can_generate:
    st.session_state["error_msg"] = None
    timings: dict[str, float] = {}
    run_start = time.perf_counter()

    with st.status("Transcribing audio with Whisper…", expanded=True) as status:
        audio_bytes = audio_file.read()
        audio_hash  = _sha256(audio_bytes)
        st.write(f"{audio_file.name} · {_fmt_size(len(audio_bytes))} · `{audio_hash[:8]}…`")
        t0 = time.perf_counter()
        transcript_result = _cached_transcribe(audio_hash, audio_bytes)
        wall = time.perf_counter() - t0
        if transcript_result["error"]:
            status.update(label="Transcription failed", state="error")
            st.error(transcript_result["error"])
            st.session_state["error_msg"] = transcript_result["error"]
            st.stop()
        wc = len(transcript_result["transcript"].split())
        sc = len(transcript_result["segments"])
        cached_note = " (cached)" if wall < 0.05 else ""
        timings["Audio decode"]      = transcript_result["decode_seconds"]
        timings["Whisper inference"] = transcript_result["transcribe_seconds"]
        status.update(
            label=f"Whisper — {wc} words, {sc} segments"
                  f" · {transcript_result['transcribe_seconds']:.1f}s{cached_note}",
            state="complete",
        )
        with st.expander("View transcript", expanded=False):
            st.text(
                segments_to_annotated_text(transcript_result["segments"])
                or transcript_result["transcript"]
            )

    if pdf_file:
        with st.status("Extracting PDF with Docling…", expanded=True) as status:
            pdf_bytes = pdf_file.read()
            pdf_hash  = _sha256(pdf_bytes)
            st.write(f"{pdf_file.name} · `{pdf_hash[:8]}…`")
            t0 = time.perf_counter()
            pdf_result = _cached_extract_pdf(pdf_hash, pdf_bytes, pdf_file.name)
            wall = time.perf_counter() - t0
            if pdf_result["error"]:
                status.update(label="PDF extraction failed", state="error")
                st.error(pdf_result["error"])
                st.session_state["error_msg"] = pdf_result["error"]
                st.stop()
            cached_note = " (cached)" if wall < 0.05 else ""
            timings["PDF extraction"] = pdf_result["extract_seconds"]
            status.update(
                label=f"Docling — {len(pdf_result['pages'])} page(s)"
                      f" via {pdf_result['extractor']}"
                      f" · {pdf_result['extract_seconds']:.1f}s{cached_note}",
                state="complete",
            )
            if pdf_result["warning"]:
                st.warning(pdf_result["warning"])
            with st.expander("View extracted text (first 1 000 chars)", expanded=False):
                st.text(pdf_result["text"][:1000])
    else:
        pdf_result = {
            "text": "", "pages": [], "extractor": "none",
            "extract_seconds": 0.0, "warning": None, "error": None,
        }

    image_data: list[tuple[str, bytes]] = []
    for img_file in valid_images[:8]:
        img_file.seek(0)
        image_data.append((img_file.name, img_file.read()))

    with st.status(f"Synthesising with {GEMMA_MODEL}…", expanded=True) as status:
        st.write(
            f"Sending {len(image_data)} image(s), transcript, "
            f"and {'manual' if pdf_file else 'no manual'} to Gemma 4."
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

            supplied_image_ids = {fname for fname, _ in image_data}
            proc_errors  = validate_procedure(procedure, supplied_image_ids)
            graph_errors = validate_graph(procedure)
            all_errors   = proc_errors + graph_errors

            status.update(
                label=f"Gemma 4 — {len(procedure.steps)} step(s)"
                      f" · {gemma_seconds:.1f}s"
                      + (f" · {len(all_errors)} warning(s)" if all_errors else ""),
                state="complete",
            )
            for ve in all_errors:
                st.warning(f"Validation: {ve}")
            st.session_state["validation_warnings"] = all_errors
        except RuntimeError as exc:
            status.update(label="Synthesis failed", state="error")
            st.error(str(exc))
            st.session_state["error_msg"] = str(exc)
            st.stop()

    st.session_state["procedure"]           = procedure
    st.session_state["transcript"]          = transcript_result
    st.session_state["pdf_result"]          = pdf_result
    st.session_state["image_data"]          = image_data
    st.session_state["processing_done"]     = True
    st.session_state["timings"]             = timings
    st.rerun()

# ---------------------------------------------------------------------------
# RESULTS DISPLAY
# ---------------------------------------------------------------------------
if st.session_state["processing_done"] and st.session_state["procedure"] is not None:
    procedure = st.session_state["procedure"]

    # ── Procedure banner ─────────────────────────────────────────────────────
    st.markdown(f"""
<div class="sc-proc-banner">
  <h2>{procedure.title}</h2>
  <p>{procedure.overview}</p>
</div>
""", unsafe_allow_html=True)

    # Validation warnings
    if st.session_state.get("validation_warnings"):
        with st.expander("Validation warnings", expanded=False):
            for vw in st.session_state["validation_warnings"]:
                st.warning(vw)

    # ── Tools & materials ────────────────────────────────────────────────────
    if procedure.tools_and_materials:
        st.markdown("""
<div style="margin-bottom:0.3rem;">
  <div style="font-family:'DM Mono',monospace;font-size:0.7rem;
              text-transform:uppercase;letter-spacing:0.1em;color:#BACBC3;">
    Tools &amp; Materials
  </div>
</div>
""", unsafe_allow_html=True)
        items_html = "".join(
            f"<li style='font-size:0.9rem;margin-bottom:0.25rem;'>{item}</li>"
            for item in procedure.tools_and_materials
        )
        st.markdown(
            f"<ul style='border:1.5px solid rgba(23,34,31,0.15);"
            f"border-radius:4px;background:white;padding:0.8rem 0.8rem 0.8rem 1.8rem;"
            f"box-shadow:3px 3px 0 rgba(23,34,31,0.1);margin-bottom:1.5rem;'>"
            f"{items_html}</ul>",
            unsafe_allow_html=True,
        )

    # ── General warnings ─────────────────────────────────────────────────────
    if procedure.general_warnings:
        for w in procedure.general_warnings:
            st.warning(w)

    # ── Steps ────────────────────────────────────────────────────────────────
    st.markdown("""
<div style="margin:2rem 0 1rem;">
  <div style="font-family:'DM Mono',monospace;font-size:0.7rem;
              text-transform:uppercase;letter-spacing:0.1em;color:#BACBC3;
              margin-bottom:0.3rem;">Section 02</div>
  <h2 style="margin:0;">Procedure steps.</h2>
</div>
""", unsafe_allow_html=True)

    # Map image filename → bytes (for inline thumbnails in steps)
    image_map: dict[str, bytes] = {}
    if st.session_state.get("image_data"):
        for fname, fdata in st.session_state["image_data"]:
            image_map[fname] = fdata

    for step in procedure.steps:
        is_inf = step.is_inferred
        is_rev = step.requires_review
        card_cls = "inferred" if is_inf else ("review" if is_rev else "")
        num_cls  = "inferred" if is_inf else ""
        badges = ""
        if is_inf:
            badges += "<span class='sc-step-badge inf'>INFERRED</span>"
        if is_rev:
            badges += "<span class='sc-step-badge rev'>REVIEW</span>"

        st.markdown(
            f"<div class='sc-step {card_cls}'>"
            f"<div style='display:flex;align-items:baseline;gap:0;'>"
            f"<span class='sc-step-num {num_cls}'>{step.step_number:02d}</span>"
            f"<div style='flex:1;'>"
            f"<div class='sc-step-title'>{step.title}{badges}</div>"
            f"<div class='sc-step-body'>{step.instruction}</div>",
            unsafe_allow_html=True,
        )

        # Checkpoint
        if step.checkpoint:
            st.markdown(
                f"<div class='sc-checkpoint'>{step.checkpoint}</div>",
                unsafe_allow_html=True,
            )

        # Step warnings
        for w in step.warnings:
            st.warning(w)

        # Evidence
        if step.sources:
            ev_html = "<div style='margin-top:0.6rem;'>"
            ev_html += "<span style='font-family:DM Mono,monospace;font-size:0.68rem;" \
                       "text-transform:uppercase;letter-spacing:0.06em;color:#BACBC3;" \
                       "margin-right:0.4rem;'>Evidence</span>"
            # Inline image thumbnail from first IMAGE source if available
            thumb_shown = False
            for src in step.sources:
                kind = src.kind
                if kind == "transcript":
                    ts = f" @{src.transcript_timestamp}" if src.transcript_timestamp else ""
                    q  = f" &ldquo;{src.quote}&rdquo;" if src.quote else ""
                    ev_html += f"<span class='sc-ev sc-ev-t'>T{ts}{q}</span>"
                elif kind == "image":
                    img_label = src.image_id or "photo"
                    ev_html += f"<span class='sc-ev sc-ev-i'>IMG {img_label}</span>"
                    # Show thumbnail once per step
                    if not thumb_shown and src.image_id and src.image_id in image_map:
                        import io as _io
                        st.image(
                            _io.BytesIO(image_map[src.image_id]),
                            caption=src.image_id,
                            width=160,
                        )
                        thumb_shown = True
                elif kind == "manual":
                    pg = f" p.{src.page_ref}" if src.page_ref else ""
                    ev_html += f"<span class='sc-ev sc-ev-m'>DOC{pg}</span>"
                else:
                    ev_html += "<span class='sc-ev sc-ev-x'>INFERRED</span>"
                # Evidence status
                status_map = {
                    "SUPPORTED":           ("sc-ev-supported", "✓"),
                    "PARTIALLY_SUPPORTED": ("sc-ev-partial",   "~"),
                    "CONFLICTING":         ("sc-ev-conflict",  "!"),
                    "INSUFFICIENT":        ("sc-ev-insuf",     "?"),
                }
                cls, sym = status_map.get(src.evidence_status, ("", ""))
                if cls:
                    ev_html += (
                        f"<span style='font-family:DM Mono,monospace;font-size:0.7rem;"
                        f"margin-left:2px;' class='{cls}'>{sym}</span>"
                    )
            ev_html += "</div>"
            st.markdown(ev_html, unsafe_allow_html=True)

        # Uncertainty note
        if step.uncertainty_note:
            st.markdown(
                f"<div style='background:#fdf9ec;border:1.5px solid #F3C64E;"
                f"border-radius:4px;padding:0.5rem 0.9rem;font-size:0.85rem;"
                f"margin-top:0.4rem;color:#17221F;'>"
                f"<strong style='color:#7a6020;'>Uncertain:</strong> {step.uncertainty_note}</div>",
                unsafe_allow_html=True,
            )

        st.markdown("</div></div></div>", unsafe_allow_html=True)

    # ── Meta grid — missing / contradictions / questions ─────────────────────
    has_meta = (
        procedure.missing_information
        or procedure.contradictions
        or procedure.unresolved_questions
    )
    if has_meta:
        m_items = "".join(f"<li>{x}</li>" for x in procedure.missing_information) or "<li style='color:#BACBC3;'>None identified.</li>"
        c_items = "".join(f"<li>{x}</li>" for x in procedure.contradictions) or "<li style='color:#BACBC3;'>None identified.</li>"
        q_items = "".join(f"<li>{x}</li>" for x in procedure.unresolved_questions) or "<li style='color:#BACBC3;'>None identified.</li>"
        st.markdown(f"""
<div class="sc-meta-grid">
  <div class="sc-meta-box">
    <div class="sc-meta-box-title">Missing information</div>
    <ul>{m_items}</ul>
  </div>
  <div class="sc-meta-box">
    <div class="sc-meta-box-title">Contradictions</div>
    <ul>{c_items}</ul>
  </div>
  <div class="sc-meta-box">
    <div class="sc-meta-box-title">Open questions</div>
    <ul>{q_items}</ul>
  </div>
</div>
""", unsafe_allow_html=True)

    # ── Completion checklist ──────────────────────────────────────────────────
    if procedure.completion_checklist:
        st.markdown("""
<div style="margin:2rem 0 0.8rem;">
  <div style="font-family:'DM Mono',monospace;font-size:0.7rem;
              text-transform:uppercase;letter-spacing:0.1em;color:#BACBC3;
              margin-bottom:0.3rem;">Section 03</div>
  <h2 style="margin:0;">Completion checklist.</h2>
</div>
""", unsafe_allow_html=True)
        for idx, item in enumerate(procedure.completion_checklist):
            st.checkbox(item, value=False, key=f"checklist_{idx}")

    # ── Visual workflow (Mermaid) ─────────────────────────────────────────────
    st.markdown("""
<div style="margin:2.5rem 0 1rem;">
  <div style="font-family:'DM Mono',monospace;font-size:0.7rem;
              text-transform:uppercase;letter-spacing:0.1em;color:#BACBC3;
              margin-bottom:0.3rem;">Section 04</div>
  <h2 style="margin:0 0 0.3rem;">Visual workflow.</h2>
  <p style="color:#BACBC3;font-size:0.88rem;margin:0 0 1rem;">
    The diagram below is generated deterministically from the validated
    procedure data — no extra AI calls are made.
  </p>
</div>
""", unsafe_allow_html=True)

    dtab_flow, dtab_seq = st.tabs(["Flowchart", "Sequence diagram"])

    with dtab_flow:
        diagram_fc, err_fc = build_mermaid_flowchart(procedure)
        if err_fc:
            st.warning(f"Could not build flowchart: {err_fc}")
        else:
            src_note = (
                "Built from validated graph data returned by Gemma 4."
                if procedure.graph is not None
                else "Built from step order (Gemma 4 did not return graph data)."
            )
            st.markdown(
                f"<div style='font-family:DM Mono,monospace;font-size:0.72rem;"
                f"color:#BACBC3;margin-bottom:0.6rem;'>{src_note}</div>",
                unsafe_allow_html=True,
            )
            valid_d, msg_d = validate_mermaid_syntax(diagram_fc)
            if not valid_d:
                st.error(f"Diagram validation failed: {msg_d}")
            else:
                st.markdown("<div class='sc-diagram-wrap'>", unsafe_allow_html=True)
                try:
                    from streamlit_mermaid import st_mermaid  # type: ignore
                    st_mermaid(diagram_fc, height=max(320, len(procedure.steps) * 90))
                except Exception as render_exc:
                    st.error(f"Mermaid render error: {render_exc}")
                st.markdown("</div>", unsafe_allow_html=True)
                with st.expander("View Mermaid source", expanded=False):
                    st.code(diagram_fc, language="text")

    with dtab_seq:
        diagram_seq, err_seq = build_mermaid_sequence(procedure)
        if err_seq:
            st.info(f"Sequence diagram not available: {err_seq}")
        else:
            valid_s, msg_s = validate_mermaid_syntax(diagram_seq)
            if not valid_s:
                st.error(f"Diagram validation failed: {msg_s}")
            else:
                st.markdown("<div class='sc-diagram-wrap'>", unsafe_allow_html=True)
                try:
                    from streamlit_mermaid import st_mermaid  # type: ignore
                    st_mermaid(diagram_seq, height=max(320, len(procedure.steps) * 110))
                except Exception as render_exc:
                    st.error(f"Mermaid render error: {render_exc}")
                st.markdown("</div>", unsafe_allow_html=True)
                with st.expander("View Mermaid source", expanded=False):
                    st.code(diagram_seq, language="text")

    # ── Export controls ───────────────────────────────────────────────────────
    st.markdown("""
<div style="margin:2.5rem 0 1rem;">
  <div style="font-family:'DM Mono',monospace;font-size:0.7rem;
              text-transform:uppercase;letter-spacing:0.1em;color:#BACBC3;
              margin-bottom:0.3rem;">Section 05</div>
  <h2 style="margin:0 0 0.5rem;">Export &amp; start over.</h2>
</div>
""", unsafe_allow_html=True)

    exp_col, reset_col = st.columns([3, 1], gap="medium")
    with exp_col:
        markdown_output = procedure_to_markdown(procedure)
        safe_title = procedure.title.lower().replace(" ", "_")[:40]
        st.download_button(
            label="Download procedure as Markdown",
            data=markdown_output.encode("utf-8"),
            file_name=f"{safe_title}_procedure.md",
            mime="text/markdown",
            use_container_width=True,
            key="btn_download",
        )
    with reset_col:
        if st.button("Start over", key="btn_reset2", use_container_width=True):
            for _k, _v in _DEFAULTS.items():
                st.session_state[_k] = _v
            st.rerun()

    # ── Open-source libraries ─────────────────────────────────────────────────
    st.markdown("""
<div style="margin:2.5rem 0 1rem;">
  <div style="font-family:'DM Mono',monospace;font-size:0.7rem;
              text-transform:uppercase;letter-spacing:0.1em;color:#BACBC3;
              margin-bottom:0.3rem;">Built with</div>
  <h2 style="margin:0 0 0.5rem;">Open-source libraries.</h2>
  <p style="color:#BACBC3;font-size:0.88rem;margin:0 0 1rem;">
    Check off any library you want to explore further.
  </p>
</div>
""", unsafe_allow_html=True)

    _OSS_LIBS = [
        ("faster-whisper", "Local audio transcription with timestamped segments.",
         "https://github.com/SYSTRAN/faster-whisper", "MIT"),
        ("Docling", "Structured PDF extraction with page references.",
         "https://github.com/DS4SD/docling", "MIT"),
        ("Gemma 4 (gemma-4-26b-a4b-it)", "Open-weight multimodal model for procedure synthesis.",
         "https://ai.google.dev/gemma", "Gemma Terms"),
        ("Pydantic", "Schema validation for the structured procedure output.",
         "https://github.com/pydantic/pydantic", "MIT"),
        ("Streamlit", "Web UI framework powering this interface.",
         "https://github.com/streamlit/streamlit", "Apache 2.0"),
        ("streamlit-mermaid", "Mermaid diagram rendering inside Streamlit.",
         "https://github.com/jhbale11/streamlit-mermaid", "MIT"),
        ("pypdf", "Plain-text PDF fallback when Docling is unavailable.",
         "https://github.com/py-pdf/pypdf", "BSD-3-Clause"),
        ("python-dotenv", "Loads GEMINI_API_KEY from .env safely.",
         "https://github.com/theskumar/python-dotenv", "BSD-3-Clause"),
    ]

    st.markdown(
        "<div style='border:1.5px solid rgba(23,34,31,0.15);border-radius:4px;"
        "background:white;padding:0.4rem 1.2rem;box-shadow:3px 3px 0 rgba(23,34,31,0.08);'>",
        unsafe_allow_html=True,
    )
    for i, (name, desc, url, lic) in enumerate(_OSS_LIBS):
        col_cb, col_info = st.columns([1, 11])
        with col_cb:
            st.checkbox("", key=f"oss_lib_{i}", label_visibility="collapsed")
        with col_info:
            st.markdown(
                f"<div class='sc-oss-row'>"
                f"<a href='{url}' target='_blank' class='sc-oss-name' "
                f"style='text-decoration:none;'>{name}</a>"
                f"&nbsp;<span class='sc-oss-lic'>{lic}</span><br>"
                f"<span class='sc-oss-desc'>{desc}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )
    st.markdown("</div>", unsafe_allow_html=True)
