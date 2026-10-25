# SkillCapture

**Multimodal Demonstration-to-Procedure Translator**

SkillCapture turns a spoken demonstration, a set of step photographs, and an
optional reference manual into a structured, evidence-linked procedure — with
numbered steps, source citations, warnings, uncertainties, and a completion
checklist.

Built for the **Hacktoberfest × MOSS Hack Day Udupi 2026** hackathon,
entering:

- **Best Open-Source AI Project**
- **Best Use of Gemma 4**

---

## How it works

1. **Upload** one audio recording, 3–8 photographs, and an optional PDF manual.
2. **faster-whisper** (base model, CPU int8) transcribes the audio locally and
   produces timestamped segments.
3. **Docling** extracts structured content from the PDF with page references.
   If Docling is unavailable, **pypdf** is used as a clearly flagged fallback.
4. All three sources — transcript, images, and manual text — are sent to
   **Gemma 4** (`gemma-4-26b-a4b-it`) via the Gemini API.
5. Gemma 4 synthesises a structured procedure grounded in the supplied
   evidence. Every step cites its source; inferred steps are flagged.
6. **Pydantic** validates the output schema before it is displayed.
7. Download the procedure as a Markdown file.

The application explicitly distinguishes evidence from inference. It does not
fabricate steps, materials, or safety information absent from the sources.

---

## Team

| Name | Role |
|------|------|
| Uday | Developer |

---

## Installation

### Prerequisites

- Python 3.12 or 3.13
- A Gemini API key from [Google AI Studio](https://aistudio.google.com)

### Steps

```powershell
# 1. Clone the repository
git clone https://github.com/<your-username>/skillcapture.git
cd skillcapture

# 2. (Recommended) Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
copy .env.example .env
# Open .env and set GEMINI_API_KEY=your_key_here

# 5. Run the app
streamlit run app.py
```

The app will open at `http://localhost:8501`.

---

## Running the demo

1. Start the app: `streamlit run app.py`
2. Upload an audio file (MP3, WAV, M4A, OGG, FLAC, WebM, or AAC).
3. Upload 3–8 photographs of the process steps.
4. Optionally upload a PDF reference manual.
5. Click **⚙️ Generate Procedure**.
6. View the generated procedure and download it as Markdown.

---

## Dependencies

| Package | Version | Purpose | License |
|---------|---------|---------|---------|
| streamlit | 1.66.1 | Web UI framework | Apache 2.0 |
| google-genai | 2.14.0 | Gemini API client (Gemma 4) | Apache 2.0 |
| faster-whisper | 1.2.1 | Local audio transcription | MIT |
| docling | 2.36.0 | Structured PDF extraction | MIT |
| pydantic | 2.14.1 | Output schema validation | MIT |
| python-dotenv | 1.2.4 | Environment variable loading | BSD-3-Clause |
| pypdf | 5.1.0 | Plain-text PDF fallback if Docling is unavailable | BSD-3-Clause |
| graphviz | 0.21 | Generates DOT source for `st.graphviz_chart` directed-graph diagrams | MIT — [github.com/xflr6/graphviz](https://github.com/xflr6/graphviz) |
| streamlit-mermaid | 0.2.0 | Renders Mermaid flowchart and sequence diagrams in Streamlit | MIT — [github.com/jhbale11/streamlit-mermaid](https://github.com/jhbale11/streamlit-mermaid) |

---

## AI models used

| Model | Provider | Access | Terms |
|-------|----------|--------|-------|
| **gemma-4-26b-a4b-it** | Google DeepMind | Gemini API (Google AI Studio) | [Gemma Terms of Use](https://ai.google.dev/gemma/terms) |
| **Whisper base** | OpenAI | Faster-whisper (local) | [MIT License](https://github.com/openai/whisper/blob/main/LICENSE) |

### What Gemma 4 does in this application

Gemma 4 (`gemma-4-26b-a4b-it`) performs the core multimodal reasoning. It
receives the timestamped audio transcript, the uploaded photographs (inline),
and extracted manual text in a single prompt, and returns a structured JSON
procedure. The model is explicitly instructed to ground every step in the
supplied evidence, flag inferences, and list missing information and
contradictions. This is not a wrapper or a demo call — Gemma 4 is the
functional heart of the procedure generation.

---

## AI coding assistant disclosure

This project was built with **Kiro** (Kiro IDE, powered by Claude) as an AI
coding assistant during the hackathon build window. Kiro helped produce:

- The Streamlit UI layout (`app.py`)
- The Pydantic schema (`skillcapture/schema.py`)
- The transcription wrapper (`skillcapture/transcribe.py`)
- The PDF extraction module with Docling/pypdf fallback
  (`skillcapture/extract_pdf.py`)
- The Gemma 4 synthesis module (`skillcapture/synthesize.py`)
- The Markdown export helper (`skillcapture/export.py`)
- This README

All code was reviewed, tested, and understood by the team before submission.
We can explain any part of it.

---

## Known limitations

- **Audio format support** depends on what ffmpeg can decode on the host
  machine. WAV and MP3 work reliably without ffmpeg; other formats may require
  it to be installed.
- **Docling model download** on first run requires an internet connection and
  several hundred megabytes of space.
- **Gemma 4 context window**: very long transcripts or large numbers of images
  may exceed the model's context. Manual text is truncated to 12 000 characters
  as a safeguard.
- **No persistent storage**: uploaded files and generated procedures exist only
  for the current session.
- **Inference flagging relies on the model**: the model is instructed to flag
  inferences, but may occasionally miss ambiguous cases.

---

## License

MIT License — see [LICENSE](LICENSE).

---

## Sources of evidence used per procedure

Each generated procedure lists its sources inline:

- `TRANSCRIPT` — from the faster-whisper transcription of the uploaded audio,
  with timestamps where available.
- `IMAGE` — from a specific uploaded photograph, identified by filename.
- `MANUAL` — from Docling- or pypdf-extracted content of the uploaded PDF, with
  page references where available.
- `INFERRED` — an AI interpretation with no direct source; flagged explicitly.
