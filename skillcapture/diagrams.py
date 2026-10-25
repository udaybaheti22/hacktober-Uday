"""
Mermaid diagram generators for SkillCapture procedures.

Converts a validated Procedure into:
  - Mermaid flowchart  (TD, top-down linear flow with evidence labels)
  - Mermaid sequence diagram (actor → step interactions where actors are detectable)

Rules:
- Only steps, titles, and source evidence that exist in the Procedure are used.
- No steps, edges, or decision branches are invented.
- Inferred steps are labelled as such.
- Node IDs are sanitised to safe alphanumeric identifiers.
- Every builder returns a (diagram_string, error_string | None) tuple.
  On error the diagram_string is empty and the error describes why.
"""

from __future__ import annotations

import re

from skillcapture.schema import Procedure, ProcedureStep


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _safe_id(step_number: int) -> str:
    """Stable, safe node ID for a step: S1, S2, …"""
    return f"S{step_number}"


def _truncate(text: str, max_len: int = 40) -> str:
    """Truncate a label to keep diagrams readable."""
    text = text.strip()
    return text if len(text) <= max_len else text[: max_len - 1] + "…"


def _mermaid_escape(text: str) -> str:
    """
    Escape characters that break Mermaid node labels inside double quotes.
    Mermaid doesn't allow raw double quotes or backticks in labels.
    """
    text = text.replace('"', "'")
    text = text.replace("`", "'")
    text = text.replace("\n", " ")
    text = re.sub(r"[<>{}]", "", text)
    return text


def _source_badge(step: ProcedureStep) -> str:
    """
    One-line evidence summary for diagram labels.
    Shows the first traceable source, or 'inferred' if all are inferred.
    """
    for src in step.sources:
        if src.kind == "transcript" and src.transcript_timestamp:
            return f"[T {src.transcript_timestamp}]"
        if src.kind == "image" and src.image_id:
            return "[IMG]"
        if src.kind == "manual" and src.page_ref:
            return f"[p.{src.page_ref}]"
    if step.is_inferred:
        return "[inferred]"
    return ""


# ---------------------------------------------------------------------------
# Mermaid flowchart
# ---------------------------------------------------------------------------

def build_mermaid_flowchart(proc: Procedure) -> tuple[str, str | None]:
    """
    Build a top-down Mermaid flowchart from procedure steps.

    Each step becomes a rectangular node. Inferred steps use a parallelogram.
    Steps with warnings get a rounded rectangle. Checkpoints appear as diamond
    side-nodes connected with dashed arrows.

    Returns (mermaid_string, error | None).
    """
    if not proc.steps:
        return "", "No steps to render."

    lines: list[str] = ["flowchart TD"]

    lines.append(f'    START(["{_mermaid_escape(proc.title)}"])')

    prev_id = "START"
    for step in proc.steps:
        node_id = _safe_id(step.step_number)
        label   = _mermaid_escape(f"Step {step.step_number}: {_truncate(step.title)}")
        badge   = _mermaid_escape(_source_badge(step))
        full_label = f"{label}\\n{badge}" if badge else label

        if step.is_inferred:
            lines.append(f'    {node_id}[/"{full_label} ⚠"/]')
        elif step.warnings:
            lines.append(f'    {node_id}("{full_label} ⚠")')
        else:
            lines.append(f'    {node_id}["{full_label}"]')

        lines.append(f"    {prev_id} --> {node_id}")
        prev_id = node_id

        if step.checkpoint:
            cp_id    = f"{node_id}_CP"
            cp_label = _mermaid_escape(_truncate(step.checkpoint, 35))
            lines.append(f'    {cp_id}{{"{cp_label}"}}')
            lines.append(f"    {node_id} -.-> {cp_id}")

    lines.append(f'    END(["✅ Complete"])')
    lines.append(f"    {prev_id} --> END")

    lines.append("    style START fill:#2E4742,color:#F2F2EB,stroke:#3D5F58")
    lines.append("    style END fill:#3D5F58,color:#F2F2EB,stroke:#2E4742")
    for step in proc.steps:
        if step.is_inferred:
            lines.append(
                f"    style {_safe_id(step.step_number)} "
                f"fill:#F5B726,color:#231F20,stroke:#E97B77"
            )

    return "\n".join(lines), None


# ---------------------------------------------------------------------------
# Mermaid sequence diagram
# ---------------------------------------------------------------------------

def build_mermaid_sequence(proc: Procedure) -> tuple[str, str | None]:
    """
    Build a Mermaid sequence diagram.

    Actors are detected from source kinds present in the procedure:
      Operator — always present (performs each step)
      Audio    — if any transcript sources exist
      Manual   — if any manual sources exist
      Photos   — if any image sources exist

    Returns (mermaid_string, error | None).
    """
    if not proc.steps:
        return "", "No steps to render."

    has_transcript = any(
        src.kind == "transcript"
        for step in proc.steps for src in step.sources
    )
    has_manual = any(
        src.kind == "manual"
        for step in proc.steps for src in step.sources
    )
    has_image = any(
        src.kind == "image"
        for step in proc.steps for src in step.sources
    )

    if not (has_transcript or has_manual or has_image):
        return "", (
            "No source interactions detected. "
            "The sequence diagram requires at least one transcript, manual, or image source."
        )

    lines: list[str] = ["sequenceDiagram"]
    lines.append("    participant Operator")
    if has_transcript:
        lines.append("    participant Audio")
    if has_manual:
        lines.append("    participant Manual")
    if has_image:
        lines.append("    participant Photos")

    for step in proc.steps:
        node_label   = _mermaid_escape(f"Step {step.step_number}: {_truncate(step.title)}")
        inferred_tag = " [inferred]" if step.is_inferred else ""
        lines.append(f"    Operator->>Operator: {node_label}{inferred_tag}")

        for src in step.sources:
            if src.kind == "transcript" and has_transcript:
                ts    = f" @ {src.transcript_timestamp}" if src.transcript_timestamp else ""
                quote = (
                    f': "{_mermaid_escape(_truncate(src.quote, 30))}"'
                    if src.quote else ""
                )
                lines.append(f"    Audio-->>Operator: Evidence{ts}{quote}")
            elif src.kind == "manual" and has_manual:
                page = f" p.{src.page_ref}" if src.page_ref else ""
                lines.append(f"    Manual-->>Operator: Evidence{page}")
            elif src.kind == "image" and has_image:
                img = f" ({src.image_id})" if src.image_id else ""
                lines.append(f"    Photos-->>Operator: Evidence{img}")

        if step.uncertainty_note:
            note = _mermaid_escape(_truncate(step.uncertainty_note, 50))
            lines.append(f"    Note over Operator: ⚠ {note}")

        if step.checkpoint:
            cp = _mermaid_escape(_truncate(step.checkpoint, 45))
            lines.append(f"    Note over Operator: ✓ {cp}")

    return "\n".join(lines), None


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_mermaid_syntax(diagram: str) -> tuple[bool, str]:
    """
    Basic structural validation of a Mermaid diagram string.

    Checks the first non-empty line is a known diagram type and that
    the edge count is within practical limits.

    Returns (is_valid, error_message). error_message is empty when valid.
    """
    if not diagram.strip():
        return False, "Empty diagram string."

    lines = [l for l in diagram.strip().splitlines() if l.strip()]
    first = lines[0].strip().lower()
    valid_types = (
        "flowchart", "sequencediagram", "graph", "erdiagram",
        "classdiagram", "statediagram", "gantt",
    )
    if not any(first.startswith(t) for t in valid_types):
        return False, f"Unrecognised diagram type in first line: {lines[0]!r}"

    edge_count = sum(1 for l in lines if "-->" in l or "->>" in l)
    if edge_count > 200:
        return False, f"Too many edges ({edge_count}); diagram may not render."

    return True, ""
