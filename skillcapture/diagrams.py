"""
Mermaid diagram generators for SkillCapture procedures.

P2: Primary path uses the validated ProcedureGraph from Gemma 4's response.
    Python generates Mermaid syntax deterministically — Gemma 4 does NOT
    return raw Mermaid code.

Fallback: If no graph is present, builds a linear flowchart from step order.

All builders:
  - Only use data present in the validated Procedure/ProcedureGraph.
  - Sanitise all user-provided labels before embedding in Mermaid syntax.
  - Return (mermaid_string, error | None).
"""

from __future__ import annotations

import re

from skillcapture.schema import GraphEdge, GraphNode, Procedure, ProcedureGraph, ProcedureStep


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _safe_node_id(raw: str) -> str:
    """
    Sanitise a node_id so it is safe as a Mermaid node identifier.
    Keeps alphanumerics and underscores only; replaces everything else with _.
    """
    sanitised = re.sub(r"[^A-Za-z0-9_]", "_", raw)
    if sanitised and sanitised[0].isdigit():
        sanitised = "N" + sanitised
    return sanitised or "NODE"


def _mermaid_escape(text: str) -> str:
    """
    Escape characters that break Mermaid labels inside double quotes.
    Input comes from model-generated or user-provided text — treat as untrusted.
    """
    text = text.replace('"', "'")
    text = text.replace("`", "'")
    text = text.replace("\n", " ")
    # Remove angle brackets, braces — confuse Mermaid's lexer
    text = re.sub(r"[<>{}|]", "", text)
    # Prevent injection of Mermaid directives
    text = re.sub(r"%%.*", "", text)
    return text.strip()


def _truncate(text: str, max_len: int = 40) -> str:
    text = text.strip()
    return text if len(text) <= max_len else text[: max_len - 1] + "…"


def _source_badge(step: ProcedureStep) -> str:
    """One-line evidence badge for fallback flowchart labels."""
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
# P2: Graph-based Mermaid flowchart (primary path)
# ---------------------------------------------------------------------------

def build_flowchart_from_graph(proc: Procedure) -> tuple[str, str | None]:
    """
    Build a Mermaid flowchart from the validated ProcedureGraph embedded in
    the Procedure. This is the primary diagram path (P2).

    Node shapes:
      start/end  → stadium  ([label])
      action     → rectangle  [label]
      decision   → diamond  {label}
      inferred   → parallelogram  [/label/]

    Styling:
      requires_review nodes  → amber fill
      inferred nodes         → yellow fill

    Returns (mermaid_string, error | None).
    """
    if proc.graph is None:
        return "", "No graph data available. Using fallback diagram."

    graph = proc.graph

    # Build lookup: step_id → ProcedureStep (for labels/status)
    step_lookup = {s.step_id: s for s in proc.steps}

    lines: list[str] = ["flowchart TD"]

    # Emit nodes
    for node in graph.nodes:
        nid   = _safe_node_id(node.node_id)
        label = _mermaid_escape(_truncate(node.label, 45))

        # Append evidence badge from linked step if available
        linked_step = step_lookup.get(node.step_id)
        if linked_step and node.node_type == "action":
            badge = _mermaid_escape(_source_badge(linked_step))
            if badge:
                label = f"{label}\\n{badge}"

        review_tag  = " ⚠" if node.requires_review else ""
        inferred_tag = " ∿" if node.is_inferred else ""
        full_label   = f"{label}{review_tag}{inferred_tag}"

        if node.node_type == "start":
            lines.append(f'    {nid}(["{full_label}"])')
        elif node.node_type == "end":
            lines.append(f'    {nid}(["{full_label}"])')
        elif node.node_type == "decision":
            lines.append(f'    {nid}{{"{full_label}"}}')
        elif node.is_inferred:
            lines.append(f'    {nid}[/"{full_label}"/]')
        else:
            lines.append(f'    {nid}["{full_label}"]')

    # Emit edges
    for edge in graph.edges:
        src = _safe_node_id(edge.from_node)
        tgt = _safe_node_id(edge.to_node)
        if edge.label:
            edge_label = _mermaid_escape(_truncate(edge.label, 25))
            arrow = f'-- "{edge_label}" -->'
        else:
            arrow = "-->"
        if edge.is_inferred:
            arrow = arrow.replace("-->", "-.->")
        lines.append(f"    {src} {arrow} {tgt}")

    # Styling
    start_nodes = [n for n in graph.nodes if n.node_type == "start"]
    end_nodes   = [n for n in graph.nodes if n.node_type == "end"]
    for node in start_nodes:
        lines.append(
            f"    style {_safe_node_id(node.node_id)} "
            f"fill:#2E4742,color:#F2F2EB,stroke:#3D5F58"
        )
    for node in end_nodes:
        lines.append(
            f"    style {_safe_node_id(node.node_id)} "
            f"fill:#3D5F58,color:#F2F2EB,stroke:#2E4742"
        )
    for node in graph.nodes:
        nid = _safe_node_id(node.node_id)
        if node.requires_review:
            lines.append(
                f"    style {nid} fill:#F5B726,color:#231F20,stroke:#E97B77"
            )
        elif node.is_inferred:
            lines.append(
                f"    style {nid} fill:#8BB2DE,color:#231F20,stroke:#3D5F58"
            )

    return "\n".join(lines), None


# ---------------------------------------------------------------------------
# Fallback: linear flowchart from step order (used when graph is absent)
# ---------------------------------------------------------------------------

def build_mermaid_flowchart(proc: Procedure) -> tuple[str, str | None]:
    """
    Build a top-down Mermaid flowchart from procedure step order.
    Used as fallback when proc.graph is None.

    Returns (mermaid_string, error | None).
    """
    # Prefer graph-based diagram if available
    if proc.graph is not None:
        return build_flowchart_from_graph(proc)

    if not proc.steps:
        return "", "No steps to render."

    lines: list[str] = ["flowchart TD"]
    lines.append(f'    START(["{_mermaid_escape(proc.title)}"])')

    prev_id = "START"
    for step in proc.steps:
        node_id    = _safe_node_id(step.step_id)
        label      = _mermaid_escape(f"Step {step.step_number}: {_truncate(step.title)}")
        badge      = _mermaid_escape(_source_badge(step))
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
                f"    style {_safe_node_id(step.step_id)} "
                f"fill:#F5B726,color:#231F20,stroke:#E97B77"
            )

    return "\n".join(lines), None


# ---------------------------------------------------------------------------
# Mermaid sequence diagram (unchanged logic, updated to use step_id)
# ---------------------------------------------------------------------------

def build_mermaid_sequence(proc: Procedure) -> tuple[str, str | None]:
    """
    Build a Mermaid sequence diagram from source actor interactions.
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
        node_label   = _mermaid_escape(
            f"Step {step.step_number}: {_truncate(step.title)}"
        )
        review_tag   = " ⚠ review" if step.requires_review else ""
        inferred_tag = " [inferred]" if step.is_inferred else ""
        lines.append(
            f"    Operator->>Operator: {node_label}{inferred_tag}{review_tag}"
        )

        for src in step.sources:
            if src.kind == "transcript" and has_transcript:
                ts    = f" @ {src.transcript_timestamp}" if src.transcript_timestamp else ""
                quote = (
                    f': "{_mermaid_escape(_truncate(src.quote, 30))}"'
                    if src.quote else ""
                )
                status = f" [{src.evidence_status}]"
                lines.append(f"    Audio-->>Operator: Evidence{ts}{quote}{status}")
            elif src.kind == "manual" and has_manual:
                page = f" p.{src.page_ref}" if src.page_ref else ""
                status = f" [{src.evidence_status}]"
                lines.append(f"    Manual-->>Operator: Evidence{page}{status}")
            elif src.kind == "image" and has_image:
                img = f" ({src.image_id})" if src.image_id else ""
                status = f" [{src.evidence_status}]"
                lines.append(f"    Photos-->>Operator: Evidence{img}{status}")

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
    Returns (is_valid, error_message). error_message is empty when valid.
    """
    if not diagram.strip():
        return False, "Empty diagram string."

    lines = [ln for ln in diagram.strip().splitlines() if ln.strip()]
    first = lines[0].strip().lower()
    valid_types = (
        "flowchart", "sequencediagram", "graph", "erdiagram",
        "classdiagram", "statediagram", "gantt",
    )
    if not any(first.startswith(t) for t in valid_types):
        return False, f"Unrecognised diagram type in first line: {lines[0]!r}"

    edge_count = sum(1 for ln in lines if "-->" in ln or "->>" in ln)
    if edge_count > 200:
        return False, f"Too many edges ({edge_count}); diagram may not render."

    return True, ""
