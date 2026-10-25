"""
Multimodal procedure synthesis using Gemma 4 via the Gemini API.

Model: gemma-4-26b-a4b-it  (Gemma 4, multimodal, through Google AI Studio)
SDK  : google-genai 2.x  (google.genai)

The function takes:
  - transcript text (with optional timestamps)
  - a list of (filename, image_bytes) tuples
  - extracted manual text (may be empty)

It returns a validated Procedure instance or raises a descriptive RuntimeError.
"""

from __future__ import annotations

import json
import os
import re

from pydantic import ValidationError

from skillcapture.schema import Procedure

# ---------------------------------------------------------------------------
# Model name — single source of truth, referenced in README
# ---------------------------------------------------------------------------
GEMMA_MODEL = "gemma-4-26b-a4b-it"


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------
_SYSTEM_PROMPT = """\
You are SkillCapture, an expert at analysing multimodal demonstrations and \
producing clear, evidence-grounded procedures.

You will receive:
1. A spoken transcript (possibly with timestamps) of someone explaining a process.
2. One or more photographs showing steps in that process.
3. Optional extracted text from a reference manual.

Your task is to synthesise these sources into a structured procedure.

STRICT RULES:
- Ground every step in the evidence supplied. If a step is your interpretation \
rather than something explicitly shown or stated, set is_inferred=true and \
explain in uncertainty_note.
- Never fabricate tools, materials, warnings, or safety information that do not \
appear in the sources.
- If information is missing, list it in missing_information.
- If sources contradict each other, list the contradiction explicitly.
- For each step, cite the relevant source(s): transcript timestamp, image \
filename, or manual page reference.
- Do NOT include markdown code fences in your JSON response. Output raw JSON only.

Output a single JSON object matching this schema exactly:
{
  "title": "string",
  "overview": "string",
  "tools_and_materials": ["string"],
  "steps": [
    {
      "step_number": 1,
      "title": "string",
      "instruction": "string",
      "sources": [
        {
          "kind": "transcript|image|manual|inferred",
          "image_id": "filename or null",
          "page_ref": "page number or null",
          "transcript_timestamp": "MM:SS or null",
          "quote": "short excerpt or null"
        }
      ],
      "warnings": ["string"],
      "checkpoint": "string or null",
      "is_inferred": false,
      "uncertainty_note": "string or null"
    }
  ],
  "general_warnings": ["string"],
  "missing_information": ["string"],
  "contradictions": ["string"],
  "unresolved_questions": ["string"],
  "completion_checklist": ["string"]
}
"""


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def synthesize_procedure(
    transcript: str,
    segments: list[dict],
    images: list[tuple[str, bytes]],
    manual_text: str,
) -> Procedure:
    """
    Call Gemma 4 via the Gemini API to produce a validated Procedure.

    Parameters
    ----------
    transcript   : plain-text transcript
    segments     : list of {start, end, text} dicts from faster-whisper
    images       : list of (filename, raw_bytes) tuples
    manual_text  : full extracted manual text (empty string if no PDF)

    Returns
    -------
    Procedure (validated Pydantic model)

    Raises
    ------
    RuntimeError  with a descriptive message on any failure
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not set. "
            "Add it to your .env file and restart the app."
        )

    try:
        from google import genai  # type: ignore
        from google.genai import types  # type: ignore
    except ImportError:
        raise RuntimeError(
            "google-genai is not installed. Run: pip install google-genai"
        )

    client = genai.Client(api_key=api_key)

    # -----------------------------------------------------------------------
    # Build the content parts list
    # -----------------------------------------------------------------------
    parts: list = []

    # 1. Transcript
    if segments:
        from skillcapture.transcribe import segments_to_annotated_text
        transcript_block = segments_to_annotated_text(segments)
    else:
        transcript_block = transcript

    parts.append(
        types.Part.from_text(
            text=(
                f"=== SPOKEN TRANSCRIPT ===\n{transcript_block}\n"
                if transcript_block.strip()
                else "=== SPOKEN TRANSCRIPT ===\n(no audio provided)\n"
            )
        )
    )

    # 2. Images — inline bytes
    for filename, img_bytes in images:
        mime = _guess_mime(filename)
        parts.append(
            types.Part.from_bytes(data=img_bytes, mime_type=mime)
        )
        parts.append(
            types.Part.from_text(text=f"(Image filename: {filename})")
        )

    # 3. Manual text
    if manual_text.strip():
        parts.append(
            types.Part.from_text(
                text=f"=== REFERENCE MANUAL ===\n{manual_text[:12000]}\n"
            )
        )
    else:
        parts.append(
            types.Part.from_text(
                text="=== REFERENCE MANUAL ===\n(no manual provided)\n"
            )
        )

    # 4. Final instruction
    parts.append(
        types.Part.from_text(
            text=(
                "Using only the sources above, produce the JSON procedure. "
                "Output raw JSON only — no markdown fences, no extra text."
            )
        )
    )

    # -----------------------------------------------------------------------
    # API call — google-genai 2.x style
    # -----------------------------------------------------------------------
    try:
        response = client.models.generate_content(
            model=GEMMA_MODEL,
            contents=parts,
            config=types.GenerateContentConfig(
                system_instruction=_SYSTEM_PROMPT,
                temperature=0.2,
                max_output_tokens=8192,
            ),
        )
    except Exception as exc:
        raise RuntimeError(f"Gemini API call failed: {exc}") from exc

    # -----------------------------------------------------------------------
    # Parse and validate
    # -----------------------------------------------------------------------
    raw_text = ""
    if response.candidates:
        candidate = response.candidates[0]
        if candidate.content and candidate.content.parts:
            # Gemma 4 returns chain-of-thought parts with thought=True.
            # Only the non-thought parts contain the actual answer.
            raw_text = "".join(
                p.text
                for p in candidate.content.parts
                if hasattr(p, "text") and p.text and not getattr(p, "thought", False)
            )

    if not raw_text:
        # Fallback: try .text shortcut — returns None if only thought parts exist
        try:
            raw_text = response.text or ""
        except Exception:
            pass

    if not raw_text:
        raise RuntimeError(
            "The Gemini API returned an empty response. "
            "Check your API key, quota, and that the model name is correct."
        )

    raw_text = _strip_code_fences(raw_text)

    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"Model returned non-JSON output.\n"
            f"Parse error: {exc}\n\n"
            f"Raw output (first 600 chars):\n{raw_text[:600]}"
        ) from exc

    try:
        procedure = Procedure.model_validate(data)
    except ValidationError as exc:
        raise RuntimeError(
            f"Model output failed schema validation:\n{exc}\n\n"
            f"Raw JSON (first 600 chars):\n{raw_text[:600]}"
        ) from exc

    return procedure


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _guess_mime(filename: str) -> str:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return {
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "gif": "image/gif",
        "webp": "image/webp",
        "bmp": "image/bmp",
        "tiff": "image/tiff",
        "tif": "image/tiff",
    }.get(ext, "image/jpeg")


def _strip_code_fences(text: str) -> str:
    """Remove ```json ... ``` or ``` ... ``` wrapping if the model adds it."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()
