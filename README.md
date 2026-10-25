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
| streamlit-mermaid | 0.2.0 | Renders Mermaid flowchart and sequence diagrams in Streamlit | MIT — [github.com/jhbale11/streamlit-mermaid](https://github.com/jhbale11/streamlit-mermaid) |

---

## AI models used

| Model | Provider | Access | Terms |
|-------|----------|--------|-------|
| **gemma-4-26b-a4b-it** | Google DeepMind | Gemini API (Google AI Studio) | [Gemma Terms of Use](https://ai.google.dev/gemma/terms) |
| **Whisper base** | OpenAI | Faster-whisper (local) | [MIT License](https://github.com/openai/whisper/blob/main/LICENSE) |

### What Gemma 4 does in this application — and how

Gemma 4 (`gemma-4-26b-a4b-it`) performs the **core multimodal reasoning** that
makes SkillCapture possible. This is not a wrapper around another model, a
retrieval system, or a summarization task — Gemma 4 is the functional heart of
the procedure generation pipeline.

#### The multimodal prompt

The model receives three inputs in a single API call:

1. **Timestamped audio transcript** — segments with speaker timestamps from
   faster-whisper, formatted as structured text.
2. **Inline photographs** — the uploaded step images, sent as base64-encoded
   image data inside the prompt.
3. **Manual text** — the plain-text or structured content extracted from the
   PDF by Docling, with page references preserved.

No retrieval augmentation, no vector search, no external knowledge base — just
the raw demonstration materials and an instruction prompt.

#### The synthesis task

Gemma 4 is instructed to:

- **Cross-reference the three modalities**: match what the speaker says in the
  transcript to what appears in the photographs, and reconcile both against
  what the manual specifies.
- **Generate a structured procedure** with numbered steps, each step grounded
  in one or more sources (transcript, image, or manual).
- **Explicitly flag inference**: any step that does not have direct evidence
  from the supplied sources must be marked `is_inferred: true`.
- **Cite evidence with specificity**: transcript citations include timestamps,
  image citations name the specific photo, and manual citations include page
  references.
- **Identify contradictions**: when the audio, images, and manual disagree,
  list those conflicts explicitly in the output rather than silently choosing
  one source.
- **List missing information**: flag any gaps — tools not mentioned, steps not
  shown, warnings absent from all sources.
- **Produce a dependency graph** (optional P2 feature): map which steps depend
  on prior steps, which can run in parallel, and where checkpoints belong.

The output is a **structured JSON object** validated against a Pydantic schema
(`skillcapture/schema.py`). If the model returns invalid JSON or omits required
fields, the application surfaces that error rather than guessing.

#### Why this task demonstrates Gemma 4's capabilities

This is a **reasoning-intensive, evidence-reconciliation task** that exercises:

- **Multimodal understanding**: interpreting spoken explanations, reading
  photographs to understand what physical actions are being performed, and
  parsing technical reference text.
- **Cross-modal evidence grounding**: a step in the generated procedure might
  cite "the speaker mentions tightening at 02:34" (transcript), "visible in
  step3.jpg" (image), and "specified on page 12 of the manual" (PDF).
- **Structured generation**: the model must produce JSON that matches a complex
  schema with nested objects, enums, and strict field requirements.
- **Uncertainty quantification**: the model explicitly reports when it lacks
  evidence, rather than hallucinating confident-sounding steps.
- **Instruction following under constraint**: the model is told to ground every
  claim and flag inferences — and it does so reliably enough that the output is
  usable without a human rewriting it.

The generated procedure is not a summary, not a chatbot answer, not
keyword-stuffed SEO content. It is a **structured, evidence-backed technical
document** that cites its sources and acknowledges its limits — created
end-to-end by Gemma 4 in a single API call.

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
