"""
Standalone tests for SkillCapture Mermaid diagram generators.

Uses a synthetic 4-step linear procedure with mixed source types.
No Streamlit server, no API calls, no file uploads required.

Tests:
  1.  Mermaid flowchart generated without error
  2.  Flowchart passes structural validation
  3.  Flowchart contains every step ID (S1..S4)
  4.  Inferred step is labelled in flowchart
  5.  Step with checkpoint produces a CP node
  6.  Mermaid sequence diagram generated without error
  7.  Sequence passes structural validation
  8.  Sequence contains correct actor declarations
  9.  Sequence returns error when no traceable sources exist
  10. validate_mermaid_syntax rejects empty string
  11. validate_mermaid_syntax rejects unknown diagram type
  12. Procedure object is not mutated by either diagram builder
"""

from skillcapture.schema import Procedure, ProcedureStep, SourceRef
from skillcapture.diagrams import (
    build_mermaid_flowchart,
    build_mermaid_sequence,
    validate_mermaid_syntax,
)

# ── Synthetic procedure ──────────────────────────────────────────────────────

proc = Procedure(
    title="Make a Cup of Tea",
    overview="A simple four-step procedure for brewing tea.",
    tools_and_materials=["kettle", "mug", "tea bag", "water"],
    steps=[
        ProcedureStep(
            step_id="step_1",
            step_number=1,
            title="Boil water",
            instruction="Fill the kettle and bring to boil.",
            sources=[SourceRef(kind="transcript", transcript_timestamp="00:05",
                               quote="fill the kettle")],
            checkpoint="Water is boiling visibly.",
        ),
        ProcedureStep(
            step_id="step_2",
            step_number=2,
            title="Place tea bag",
            instruction="Put one tea bag in the mug.",
            sources=[SourceRef(kind="image", image_id="step2.jpg")],
            warnings=["Use a fresh tea bag."],
        ),
        ProcedureStep(
            step_id="step_3",
            step_number=3,
            title="Pour water",
            instruction="Pour boiled water over the tea bag.",
            sources=[
                SourceRef(kind="transcript", transcript_timestamp="00:42"),
                SourceRef(kind="manual", page_ref="3"),
            ],
        ),
        ProcedureStep(
            step_id="step_4",
            step_number=4,
            title="Steep and serve",
            instruction="Let steep for 3–5 minutes, remove bag, and serve.",
            sources=[SourceRef(kind="inferred")],
            is_inferred=True,
            uncertainty_note="Steeping time not specified in audio.",
        ),
    ],
    completion_checklist=["Tea is brewed", "Bag is removed"],
)

proc_no_sources = Procedure(
    title="Mystery Procedure",
    overview="All steps are inferred.",
    steps=[
        ProcedureStep(
            step_id="step_1",
            step_number=1,
            title="Do something",
            instruction="Unclear.",
            sources=[SourceRef(kind="inferred")],
            is_inferred=True,
        ),
    ],
)

print("Running Mermaid diagram tests...\n")

# 1. Flowchart generated without error
fc, err = build_mermaid_flowchart(proc)
assert err is None, f"Unexpected flowchart error: {err}"
assert fc.strip(), "Flowchart is empty"
print("✅ Test 1: Mermaid flowchart generated without error")

# 2. Flowchart passes validation
valid, msg = validate_mermaid_syntax(fc)
assert valid, f"Flowchart validation failed: {msg}"
print("✅ Test 2: Mermaid flowchart passes structural validation")

# 3. All step IDs present
for i in range(1, 5):
    assert f"step_{i}" in fc, f"Missing node step_{i}"
print("✅ Test 3: Flowchart contains all step IDs (step_1–step_4)")

# 4. Inferred step labelled
assert "inferred" in fc.lower()
print("✅ Test 4: Inferred step is labelled in flowchart")

# 5. Checkpoint node present
assert "step_1_CP" in fc
print("✅ Test 5: Checkpoint node step_1_CP present")

# 6. Sequence generated without error
seq, err_seq = build_mermaid_sequence(proc)
assert err_seq is None, f"Unexpected sequence error: {err_seq}"
assert seq.strip()
print("✅ Test 6: Mermaid sequence diagram generated without error")

# 7. Sequence passes validation
valid_seq, msg_seq = validate_mermaid_syntax(seq)
assert valid_seq, f"Sequence validation failed: {msg_seq}"
print("✅ Test 7: Mermaid sequence diagram passes structural validation")

# 8. Correct actors declared
assert "participant Operator" in seq
assert "participant Audio" in seq
assert "participant Manual" in seq
assert "participant Photos" in seq
print("✅ Test 8: Sequence diagram declares all expected actors")

# 9. Error for inferred-only procedure
_, err_no_src = build_mermaid_sequence(proc_no_sources)
assert err_no_src is not None and len(err_no_src) > 0
print(f"✅ Test 9: Sequence returns error for inferred-only procedure")

# 10. Validation rejects empty
ok, msg = validate_mermaid_syntax("")
assert not ok
print("✅ Test 10: validate_mermaid_syntax rejects empty string")

# 11. Validation rejects unknown type
ok, msg = validate_mermaid_syntax("unknownDiagram\n  A --> B")
assert not ok
print("✅ Test 11: validate_mermaid_syntax rejects unknown diagram type")

# 12. Procedure not mutated
original = len(proc.steps)
build_mermaid_flowchart(proc)
build_mermaid_sequence(proc)
assert len(proc.steps) == original
print("✅ Test 12: Procedure object not mutated by diagram builders")

print(f"\n✅ All 12 Mermaid diagram tests passed.")
print(f"\nDiagram sizes:")
print(f"  Flowchart:        {len(fc)} chars, {fc.count(chr(10))+1} lines")
print(f"  Sequence diagram: {len(seq)} chars, {seq.count(chr(10))+1} lines")
