"""
Multimodal procedure synthesis using Gemma 4 via the Gemini API.

Model: gemma-4-26b-a4b-it  (Gemma 4, multimodal, through Google AI Studio)
SDK  : google-genai 2.x  (google.genai)

P1 changes:
- System prompt now instructs cross-modal evidence reconciliation.
- Evidence ledger with evidence_status and support_explanation.
- step_id and requires_review per step.

P2 changes:
- Graph nodes and edges included in the same response.
- Python generates Mermaid from the validated graph — Gemma 4 does NOT return
  raw Mermaid code.
"""

from __future__ import annotations

import json
import os
import re

from pydantic import ValidationError

from skillcapture.schema import Procedure

# ---------------------------------------------------------------------------
# Model name — single source of truth
# ---------------------------------------------------------------------------
GEMMA_MODEL = "gemma-4-26b-a4b-it"


# ---------------------------------------------------------------------------
# Evidence inventory builder
# ---------------------------------------------------------------------------

def _build_evidence_inventory(
    segments: list[dict],
    images: list[tuple[str, bytes]],
    manual_pages: list[dict],
) -> str:
    """
    Build a plain-text inventory of all supplied evidence identifiers.
    Passed to Gemma 4 so it knows exactly which IDs are valid.
    """
    lines = ["=== EVIDENCE INVENTORY ==="]
    lines.append("Use ONLY the identifiers listed below. Do not fabricate any.")
    lines.append("")

    # Transcript timestamps
    if segments:
        lines.append("TRANSCRIPT TIMESTAMPS available:")
        for seg in segments:
            mins = int(seg["start"] // 60)
            secs = int(seg["start"] % 60)
            lines.append(f"  [{mins:02d}:{secs:02d}] {seg['text'][:80]}")
    else:
        lines.append("TRANSCRIPT: full text provided, no segment timestamps.")
    lines.append("")

    # Image IDs
    if images:
        lines.append("IMAGE IDs available (use exact filenames):")
        for filename, _ in images:
            lines.append(f"  {filename}")
    else:
        lines.append("IMAGES: none supplied.")
    lines.append("")

    # Manual pages
    if manual_pages:
        lines.append("MANUAL PAGE REFERENCES available:")
        for page in manual_pages:
            lines.append(f"  Page {page['page']}")
    else:
        lines.append("MANUAL: none supplied.")

    lines.append("")
    lines.append(
        "Any source reference you include MUST use an identifier from the above list. "
        "If you cannot find a matching identifier, use kind='inferred' and set "
        "evidence_status='INSUFFICIENT'."
    )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# System prompt — P1: cross-modal reconciliation
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
You are SkillCapture, an expert at analysing multimodal demonstrations and \
producing rigorous, evidence-grounded procedures.

You will receive:
1. A spoken transcript with timestamps from faster-whisper.
2. Photographs of the demonstration, each with a stable image filename.
3. Extracted reference-manual content with page references.
4. An EVIDENCE INVENTORY listing all valid source identifiers.

═══ CROSS-MODAL REASONING — follow these steps in order ═══

1. RECONSTRUCT: Determine the most likely order of steps from all sources combined.
2. CORRELATE: Match each spoken instruction to a visible action in a photograph \
and/or a manual instruction where possible.
3. AGREE: Identify where transcript, photographs, and manual are consistent.
4. CONFLICT: Identify where sources disagree. Keep all conflicting evidence; \
do not silently pick one side.
5. GAP: Identify missing prerequisites, unclear ordering, ambiguous visual details, \
and any step that appears in only one source.
6. SEPARATE: Distinguish directly supported statements from inferences.
7. UNCERTAINTY: Leave unresolved details explicitly uncertain. Do not invent \
missing instructions to fill gaps.
8. RESTRAINT: Do not add safety instructions, materials, or steps that are not \
supported by the evidence or clearly identified as requiring human review.

═══ EVIDENCE STATUS RULES ═══
- SUPPORTED: at least one source directly shows or states this.
- PARTIALLY_SUPPORTED: one source supports it but others are silent or ambiguous.
- CONFLICTING: sources disagree — keep both sides in sources[], set \
evidence_status="CONFLICTING" on the affected SourceRef, set requires_review=true.
- INSUFFICIENT: no adequate evidence; set requires_review=true, is_inferred=true.

A source reference does not itself prove a step is factually correct. \
Do not present model-generated explanations as independent verification.

═══ GRAPH RULES (for Mermaid diagram, P2) ═══
- Include a graph object with nodes and edges.
- Every action node must reference a step_id from your steps array.
- Include exactly one node with node_type="start" and one with node_type="end".
- Add decision nodes only where the evidence explicitly shows a conditional branch.
- Do not invent dependencies or branches to make the diagram elaborate.
- Every edge must reference valid node_ids from your nodes array.

═══ OUTPUT FORMAT ═══
Output a single raw JSON object — NO markdown fences, NO extra text.

{
  "title": "string",
  "overview": "string",
  "tools_and_materials": ["string"],
  "steps": [
    {
      "step_id": "step_1",
      "step_number": 1,
      "title": "string",
      "instruction": "string",
      "sources": [
        {
          "kind": "transcript|image|manual|inferred",
          "image_id": "exact filename or null",
          "page_ref": "page number or null",
          "transcript_timestamp": "MM:SS or null",
          "quote": "short verbatim excerpt or null",
          "support_explanation": "how this source supports the step",
          "evidence_status": "SUPPORTED|PARTIALLY_SUPPORTED|CONFLICTING|INSUFFICIENT"
        }
      ],
      "warnings": ["string"],
      "checkpoint": "string or null",
      "is_inferred": false,
      "uncertainty_note": "string or null",
      "requires_review": false
    }
  ],
  "general_warnings": ["string"],
  "missing_information": ["string"],
  "contradictions": ["string"],
  "unresolved_questions": ["string"],
  "completion_checklist": ["string"],
  "graph": {
    "nodes": [
      {
        "node_id": "N_START",
        "step_id": "start",
        "label": "Start",
        "node_type": "start",
        "is_inferred": false,
        "requires_review": false
      }
    ],
    "edges": [
      {
        "from_node": "N_START",
        "to_node": "N1",
        "label": null,
        "is_inferred": false,
        "evidence_ref": null
      }
    ]
  }
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
    manual_pages: list[dict] | None = None,
) -> Procedure:
    """
    Call Gemma 4 via the Gemini API to produce a validated Procedure.

    P1: Cross-modal evidence reconciliation with evidence_status per source.
    P2: Graph nodes/edges in the same response for Mermaid generation.

    Parameters
    ----------
    transcript    : plain-text transcript
    segments      : list of {start, end, text} dicts from faster-whisper
    images        : list of (filename, raw_bytes) tuples
    manual_text   : full extracted manual text
    manual_pages  : list of {page, text} dicts from Docling extraction

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

    # ── Build evidence inventory ─────────────────────────────────────────────
    evidence_inventory = _build_evidence_inventory(
        segments, images, manual_pages or []
    )

    # ── Build content parts ──────────────────────────────────────────────────
    parts: list = []

    # 1. Evidence inventory (before transcript so it's seen first)
    parts.append(types.Part.from_text(text=evidence_inventory))

    # 2. Transcript with timestamps
    from skillcapture.transcribe import segments_to_annotated_text
    if segments:
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

    # 3. Images — inline bytes with explicit filename labels
    for filename, img_bytes in images:
        mime = _guess_mime(filename)
        parts.append(types.Part.from_bytes(data=img_bytes, mime_type=mime))
        parts.append(types.Part.from_text(
            text=f"(Image ID / filename: {filename})"
        ))

    # 4. Manual text with page structure
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

    # 5. Final instruction
    parts.append(
        types.Part.from_text(
            text=(
                "Apply the cross-modal reasoning steps in your system prompt. "
                "Produce the single raw JSON object described. "
                "No markdown fences. No extra text before or after the JSON."
            )
        )
    )

    # ── API call ─────────────────────────────────────────────────────────────
    try:
        response = client.models.generate_content(
            model=GEMMA_MODEL,
            contents=parts,
            config=types.GenerateContentConfig(
                system_instruction=_SYSTEM_PROMPT,
                temperature=0.1,       # lower temp for more deterministic evidence grounding
                max_output_tokens=8192,
            ),
        )
    except Exception as exc:
        raise RuntimeError(f"Gemini API call failed: {exc}") from exc

    # ── Extract non-thought parts ─────────────────────────────────────────────
    raw_text = ""
    if response.candidates:
        candidate = response.candidates[0]
        if candidate.content and candidate.content.parts:
            raw_text = "".join(
                p.text
                for p in candidate.content.parts
                if hasattr(p, "text") and p.text and not getattr(p, "thought", False)
            )

    if not raw_text:
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

    # ── Parse JSON ────────────────────────────────────────────────────────────
    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"Model returned non-JSON output.\n"
            f"Parse error: {exc}\n\n"
            f"Raw output (first 600 chars):\n{raw_text[:600]}"
        ) from exc

    # ── Pydantic validation ───────────────────────────────────────────────────
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
