"""
Pydantic models for the SkillCapture structured procedure output.

Every field that could not be directly supported by source evidence is
explicitly flagged so the UI can surface uncertainty to the user.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


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


class ProcedureStep(BaseModel):
    """A single numbered step in the procedure."""

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
