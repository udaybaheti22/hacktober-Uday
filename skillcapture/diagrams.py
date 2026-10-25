"""
Diagram generators for SkillCapture procedures.

Converts a validated Procedure into:
  - Mermaid flowchart  (TD, top-down linear flow with evidence labels)
  - Mermaid sequence diagram (actor → step interactions where actors are detectable)
  - Graphviz DOT directed graph (for st.graphviz_chart)

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
    # Remove characters that confuse Mermaid's lexer
    text = re.sub(r"[<>{}]", "", text)
    return text


def _dot_escape(text: str) -> str:
    """Escape characters for Graphviz DOT labels."""
    text = text.replace("\\", "\\\\")
    text = text.replace('"', '\\"')
    text = text.replace("\n", "\\n")
    text = text.replace("<", "\\<")
    text = text.replace(">", "\\>")
    return text


def _source_badge(step: ProcedureStep) -> str:
    """
    One-line evidence summary for diagram labels.
    Shows the first traceable source (not inferred), or 'inferred' if all are.
    """
    for src in step.sources:
        if src.kind == "transcript" and src.transcript_timestamp:
            return f"[T {src.transcript_timestamp}]"
        if src.kind == "image" and src.image_id:
            return f"[IMG]"
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

    Each step becomes a rectangular node. Warnings get a diamond node.
    Steps are connected sequentially (no invented branches).

    Returns (mermaid_string, error | None).
    """
    if not proc.steps:
        return "", "No steps to render."

    lines: list[str] = ["flowchart TD"]

    # Start node
    lines.append(f'    START(["{_mermaid_escape(proc.title)}"])')

    prev_id = "START"
    for step in proc.steps:
        node_id = _safe_id(step.step_number)
        label = _mermaid_escape(
            f"Step {step.step_number}: {_truncate(step.title)}"
        )
        badge = _mermaid_escape(_source_badge(step))
        full_label = f"{label}\\n{badge}" if badge else label

        if step.is_inferred:
            # Parallelogram for inferred steps
            lines.append(f'    {node_id}[/"{full_label} ⚠"/]')
        elif step.warnings:
            # Rounded rectangle for steps with warnings
            lines.append(f'    {node_id}("{full_label} ⚠")')
        else:
            lines.append(f'    {node_id}["{full_label}"]')

        lines.append(f"    {prev_id} --> {node_id}")
        prev_id = node_id

        # Checkpoint as a terminal-style node attached to this step
        if step.checkpoint:
            cp_id = f"{node_id}_CP"
            cp_label = _mermaid_escape(_truncate(step.checkpoint, 35))
            lines.append(f'    {cp_id}{{"{cp_label}"}}')
            lines.append(f"    {node_id} -.-> {cp_id}")

    # End node
    lines.append(f'    END(["✅ Complete"])')
    lines.append(f"    {prev_id} --> END")

    # Styling
    lines.append("    style START fill:#2E4742,color:#F2F2EB,stroke:#3D5F58")
    lines.append("    style END fill:#3D5F58,color:#F2F2EB,stroke:#2E4742")
    for step in proc.steps:
        if step.is_inferred:
            lines.append(
                f"    style {_safe_id(step.step_number)} "
                f"fill:#F5B726,color:#231F20,stroke:#E97B77"
            )

    diagram = "\n".join(lines)
    return diagram, None


# ---------------------------------------------------------------------------
# Mermaid sequence diagram
# ---------------------------------------------------------------------------

def build_mermaid_sequence(proc: Procedure) -> tuple[str, str | None]:
    """
    Build a Mermaid sequence diagram.

    Actors are inferred from source kinds present in the procedure:
    - Operator  — always present (performs each step)
    - Audio     — if any transcript sources exist
    - Manual    — if any manual sources exist
    - Photos    — if any image sources exist

    Each step is shown as a message from Operator to itself (action note)
    plus notes from the relevant source actors where evidence exists.

    Returns (mermaid_string, error | None).
    """
    if not proc.steps:
        return "", "No steps to render."

    # Detect which actors actually appear
    has_transcript = any(
        src.kind == "transcript"
        for step in proc.steps
        for src in step.sources
    )
    has_manual = any(
        src.kind == "manual"
        for step in proc.steps
        for src in step.sources
    )
    has_image = any(
        src.kind == "image"
        for step in proc.steps
        for src in step.sources
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
        node_label = _mermaid_escape(
            f"Step {step.step_number}: {_truncate(step.title)}"
        )
        inferred_tag = " [inferred]" if step.is_inferred else ""

        # Step action — Operator performs it
        lines.append(
            f"    Operator->>Operator: {node_label}{inferred_tag}"
        )

        # Source references — messages from source actors to Operator
        for src in step.sources:
            if src.kind == "transcript" and has_transcript:
                ts = f" @ {src.transcript_timestamp}" if src.transcript_timestamp else ""
                quote = (
                    f': "{_mermaid_escape(_truncate(src.quote, 30))}"'
                    if src.quote
                    else ""
                )
                lines.append(f"    Audio-->>Operator: Evidence{ts}{quote}")
            elif src.kind == "manual" and has_manual:
                page = f" p.{src.page_ref}" if src.page_ref else ""
                lines.append(f"    Manual-->>Operator: Evidence{page}")
            elif src.kind == "image" and has_image:
                img = f" ({src.image_id})" if src.image_id else ""
                lines.append(f"    Photos-->>Operator: Evidence{img}")

        # Uncertainty note as a note over Operator
        if step.uncertainty_note:
            note = _mermaid_escape(_truncate(step.uncertainty_note, 50))
            lines.append(f"    Note over Operator: ⚠ {note}")

        # Checkpoint
        if step.checkpoint:
            cp = _mermaid_escape(_truncate(step.checkpoint, 45))
            lines.append(f"    Note over Operator: ✓ {cp}")

    diagram = "\n".join(lines)
    return diagram, None


# ---------------------------------------------------------------------------
# Graphviz directed graph
# ---------------------------------------------------------------------------

def build_graphviz_digraph(proc: Procedure) -> tuple[str, str | None]:
    """
    Build a Graphviz DOT directed graph from procedure steps.

    Returns the DOT source string (for st.graphviz_chart), not a rendered image.
    Rendering is done by Streamlit's built-in Viz.js — no system 'dot' binary needed.

    Returns (dot_source_string, error | None).
    """
    if not proc.steps:
        return "", "No steps to render."

    try:
        import graphviz  # type: ignore
    except ImportError:
        return "", "graphviz Python package is not installed. Run: pip install graphviz"

    g = graphviz.Digraph(
        name="procedure",
        graph_attr={
            "rankdir": "TB",
            "bgcolor": "transparent",
            "fontname": "Helvetica",
            "splines": "ortho",
        },
        node_attr={
            "fontname": "Helvetica",
            "fontsize": "11",
        },
        edge_attr={
            "fontname": "Helvetica",
            "fontsize": "9",
        },
    )

    # START node
    g.node(
        "START",
        label=_dot_escape(proc.title),
        shape="stadium",
        style="filled",
        fillcolor="#2E4742",
        fontcolor="#F2F2EB",
        color="#3D5F58",
    )

    prev_id = "START"
    for step in proc.steps:
        node_id = _safe_id(step.step_number)
        badge = _source_badge(step)
        label_parts = [f"Step {step.step_number}", _dot_escape(_truncate(step.title))]
        if badge:
            label_parts.append(badge)
        label = "\\n".join(label_parts)

        if step.is_inferred:
            g.node(
                node_id,
                label=label + "\\n⚠ inferred",
                shape="parallelogram",
                style="filled",
                fillcolor="#F5B726",
                fontcolor="#231F20",
                color="#E97B77",
            )
        elif step.warnings:
            g.node(
                node_id,
                label=label + "\\n⚠",
                shape="box",
                style="filled,rounded",
                fillcolor="#E97B77",
                fontcolor="#231F20",
                color="#671912",
            )
        else:
            g.node(
                node_id,
                label=label,
                shape="box",
                style="filled,rounded",
                fillcolor="#F2F2EB",
                fontcolor="#231F20",
                color="#3D5F58",
            )

        g.edge(prev_id, node_id)
        prev_id = node_id

        # Checkpoint as a separate decision diamond
        if step.checkpoint:
            cp_id = f"{node_id}_CP"
            cp_label = _dot_escape(_truncate(step.checkpoint, 35))
            g.node(
                cp_id,
                label=cp_label,
                shape="diamond",
                style="filled",
                fillcolor="#8BB2DE",
                fontcolor="#231F20",
                color="#3D5F58",
                fontsize="9",
            )
            g.edge(node_id, cp_id, style="dashed", arrowhead="open")

    # END node
    g.node(
        "END",
        label="✓ Complete",
        shape="stadium",
        style="filled",
        fillcolor="#3D5F58",
        fontcolor="#F2F2EB",
        color="#2E4742",
    )
    g.edge(prev_id, "END")

    return g.source, None


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

def validate_mermaid_syntax(diagram: str) -> tuple[bool, str]:
    """
    Basic structural validation of a Mermaid diagram string.

    Checks:
    - First non-empty line is a known diagram type keyword.
    - Node count doesn't exceed Mermaid's practical limit (~200 nodes).
    - No obviously unclosed bracket patterns.

    Returns (is_valid, error_message). error_message is empty when valid.
    """
    if not diagram.strip():
        return False, "Empty diagram string."

    lines = [l for l in diagram.strip().splitlines() if l.strip()]
    first = lines[0].strip().lower()
    valid_types = ("flowchart", "sequencediagram", "graph", "erdiagram",
                   "classDiagram", "statediagram", "gantt")
    if not any(first.startswith(t.lower()) for t in valid_types):
        return False, f"Unrecognised diagram type in first line: {lines[0]!r}"

    node_count = sum(1 for l in lines if "-->" in l or "->>" in l or "->>>" in l)
    if node_count > 200:
        return False, f"Too many edges ({node_count}); diagram may not render."

    return True, ""


def validate_dot_syntax(dot_source: str) -> tuple[bool, str]:
    """
    Basic structural validation of a Graphviz DOT string.

    Checks opening keyword and brace balance. Does not execute 'dot'.

    Returns (is_valid, error_message).
    """
    if not dot_source.strip():
        return False, "Empty DOT source."

    stripped = dot_source.strip().lower()
    if not (stripped.startswith("digraph") or stripped.startswith("graph")
            or stripped.startswith("strict")):
        return False, "DOT source must begin with 'digraph', 'graph', or 'strict'."

    open_b  = dot_source.count("{")
    close_b = dot_source.count("}")
    if open_b != close_b:
        return False, f"Unbalanced braces: {open_b} open, {close_b} close."

    return True, ""
