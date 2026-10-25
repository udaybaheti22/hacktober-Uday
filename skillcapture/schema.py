"""
Pydantic models for the SkillCapture structured procedure output.

Every field that could not be directly supported by source evidence is
explicitly flagged so the UI can surface uncertainty to the user.

Priority 1 additions (evidence reconciliation):
- SourceRef: evidence_status, support_explanation
- ProcedureStep: step_id, requires_review

Priority 2 additions (graph for Mermaid generation):
- GraphNode, GraphEdge, ProcedureGraph
- Procedure.graph (optional)
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


# ---------------------------------------------------------------------------
# Evidence status vocabulary
# ---------------------------------------------------------------------------
EvidenceStatus = Literal[
    "SUPPORTED",           # at least one source directly supports this
    "PARTIALLY_SUPPORTED", # sources support it but with gaps or ambiguity
    "CONFLICTING",         # sources disagree about this
    "INSUFFICIENT",        # no adequate evidence; requires human review
]


# ---------------------------------------------------------------------------
# Source reference
# ---------------------------------------------------------------------------

class SourceRef(BaseModel):
    """A traceable reference back to an input source."""

    kind: Literal["transcript", "image", "manual", "inferred"] = Field(
        description=(
            "'transcript' = spoken audio, "
            "'image' = a supplied photograph (use image_id), "
            "'manual' = extracted PDF content (use page_ref), "
            "'inferred' = AI interpretation with no direct source evidence"
        )
    )
    image_id: str | None = Field(
        default=None,
        description="Filename of the photograph this reference comes from, e.g. 'step3.jpg'.",
    )
    page_ref: str | None = Field(
        default=None,
        description="Page number or section identifier from the PDF manual.",
    )

    @field_validator("page_ref", mode="before")
    @classmethod
    def coerce_page_ref(cls, v: object) -> str | None:
        """Model sometimes returns page_ref as an int — coerce to str."""
        if v is None:
            return None
        return str(v)

    transcript_timestamp: str | None = Field(
        default=None,
        description="Approximate timestamp in the audio transcript, e.g. '00:45'.",
    )
    quote: str | None = Field(
        default=None,
        description=(
            "A short verbatim excerpt or visual description that supports this reference. "
            "Leave null for 'inferred' kind."
        ),
    )
    # P1 additions
    support_explanation: str | None = Field(
        default=None,
        description=(
            "Concise explanation of how this source supports the step. "
            "Must be grounded in the actual content of this source. "
            "Do not repeat the instruction text."
        ),
    )
    evidence_status: EvidenceStatus = Field(
        default="SUPPORTED",
        description=(
            "SUPPORTED: source directly supports this step. "
            "PARTIALLY_SUPPORTED: source supports it but with gaps or ambiguity. "
            "CONFLICTING: this source contradicts another source for this step. "
            "INSUFFICIENT: no adequate evidence; step requires human review."
        ),
    )

    @field_validator("evidence_status", mode="before")
    @classmethod
    def normalise_evidence_status(cls, v: object) -> str:
        """Accept lowercase variants from the model."""
        if isinstance(v, str):
            return v.upper()
        return v  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Procedure step
# ---------------------------------------------------------------------------

class ProcedureStep(BaseModel):
    """A single numbered step in the procedure."""

    # P1: stable unique identifier — "step_1", "step_2", etc.
    step_id: str = Field(
        description=(
            "Stable unique step identifier, e.g. 'step_1'. "
            "Used to link graph nodes to procedure steps."
        )
    )
    step_number: int = Field(description="1-based step index.")
    title: str = Field(description="Short imperative title for this step.")
    instruction: str = Field(
        description="Full instruction text. Write in plain, actionable language."
    )
    sources: list[SourceRef] = Field(
        default_factory=list,
        description=(
            "All source references that support this step. "
            "Include at least one; use kind='inferred' when no direct evidence exists."
        ),
    )
    warnings: list[str] = Field(
        default_factory=list,
        description="Safety warnings or cautions specific to this step.",
    )
    checkpoint: str | None = Field(
        default=None,
        description="Observable success condition: how to know this step was done correctly.",
    )
    is_inferred: bool = Field(
        default=False,
        description=(
            "True when this step is primarily an AI interpretation "
            "rather than something explicitly shown or stated in the sources."
        ),
    )
    uncertainty_note: str | None = Field(
        default=None,
        description=(
            "Describe any ambiguity, contradiction, or missing information "
            "relevant to this step. Null when the step is fully supported."
        ),
    )
    # P1: human review flag
    requires_review: bool = Field(
        default=False,
        description=(
            "True when any source for this step has evidence_status CONFLICTING or "
            "INSUFFICIENT, or when is_inferred is True. "
            "Set this automatically based on the evidence; do not override to False "
            "unless all sources are SUPPORTED."
        ),
    )

    @model_validator(mode="after")
    def auto_requires_review(self) -> "ProcedureStep":
        """
        Auto-set requires_review if any source is CONFLICTING/INSUFFICIENT,
        or if the step is inferred. The model may also set it explicitly.
        """
        if self.is_inferred:
            self.requires_review = True
            return self
        for src in self.sources:
            if src.evidence_status in ("CONFLICTING", "INSUFFICIENT"):
                self.requires_review = True
                return self
        return self

    @field_validator("step_id", mode="before")
    @classmethod
    def normalise_step_id(cls, v: object) -> str:
        """Accept step_id as int and coerce to string."""
        if isinstance(v, int):
            return f"step_{v}"
        return str(v)


# ---------------------------------------------------------------------------
# Graph models (P2 — used for Mermaid generation)
# ---------------------------------------------------------------------------

class GraphNode(BaseModel):
    """
    A node in the procedure graph.
    Each node maps back to a ProcedureStep via step_id.
    """
    node_id: str = Field(
        description="Unique node identifier within the graph, e.g. 'N1'."
    )
    step_id: str = Field(
        description="References ProcedureStep.step_id this node represents."
    )
    label: str = Field(
        description="Short display label for this node (≤ 40 chars)."
    )
    node_type: Literal["action", "decision", "start", "end"] = Field(
        default="action",
        description=(
            "'action': a regular procedure step. "
            "'decision': a conditional branch point supported by evidence. "
            "'start'/'end': terminal nodes."
        ),
    )
    is_inferred: bool = Field(
        default=False,
        description="True when this node's step is inferred.",
    )
    requires_review: bool = Field(
        default=False,
        description="True when this node's step requires human review.",
    )


class GraphEdge(BaseModel):
    """A directed edge between two graph nodes."""
    from_node: str = Field(description="node_id of the source node.")
    to_node: str   = Field(description="node_id of the target node.")
    label: str | None = Field(
        default=None,
        description=(
            "Optional edge label, e.g. a condition. "
            "Only include when directly supported by evidence."
        ),
    )
    is_inferred: bool = Field(
        default=False,
        description="True when this ordering relationship is inferred.",
    )
    evidence_ref: str | None = Field(
        default=None,
        description=(
            "Optional: transcript_timestamp, image_id, or page_ref that "
            "supports this ordering relationship."
        ),
    )


class ProcedureGraph(BaseModel):
    """
    Directed graph of procedure steps for Mermaid generation.
    Generated by Gemma 4 in the same response as the procedure.
    """
    nodes: list[GraphNode] = Field(
        description="All graph nodes. Must include exactly one start and one end node."
    )
    edges: list[GraphEdge] = Field(
        description="Directed edges. Every node must be reachable from start."
    )


# ---------------------------------------------------------------------------
# Top-level procedure
# ---------------------------------------------------------------------------

class Procedure(BaseModel):
    """Top-level structured procedure produced by SkillCapture."""

    title: str = Field(description="Short, descriptive title for the procedure.")
    overview: str = Field(
        description=(
            "2–4 sentence summary of what the procedure accomplishes, "
            "who it is for, and any important context."
        )
    )
    tools_and_materials: list[str] = Field(
        default_factory=list,
        description=(
            "All tools, materials, and equipment needed. "
            "Only list items that appear in the sources."
        ),
    )
    steps: list[ProcedureStep] = Field(
        description="Ordered list of procedure steps. Must contain at least one step."
    )
    general_warnings: list[str] = Field(
        default_factory=list,
        description="Warnings that apply to the entire procedure rather than a single step.",
    )
    missing_information: list[str] = Field(
        default_factory=list,
        description=(
            "Information that would be needed for a complete procedure "
            "but was absent from all provided sources."
        ),
    )
    contradictions: list[str] = Field(
        default_factory=list,
        description=(
            "Explicit contradictions found between sources "
            "(e.g. the transcript says 'left' but the photo shows 'right')."
        ),
    )
    unresolved_questions: list[str] = Field(
        default_factory=list,
        description=(
            "Open questions a practitioner would need to resolve "
            "before attempting this procedure safely."
        ),
    )
    completion_checklist: list[str] = Field(
        default_factory=list,
        description=(
            "Verifiable items to confirm the procedure is complete. "
            "Derive these from checkpoints and the final state described in the sources."
        ),
    )
    # P2: graph for Mermaid generation
    graph: ProcedureGraph | None = Field(
        default=None,
        description=(
            "Directed graph of procedure steps for Mermaid diagram generation. "
            "Generated in the same model response as the written procedure."
        ),
    )
