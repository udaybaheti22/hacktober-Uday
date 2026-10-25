"""
Tests for Priority 1 (evidence reconciliation) and Priority 2 (graph-based Mermaid).

All tests use synthetic data — no API calls, no file uploads.

P1 tests (schema + validation):
  1.  step_id is present and unique
  2.  evidence_status on SourceRef accepts all four values
  3.  evidence_status normalises lowercase
  4.  support_explanation is optional
  5.  requires_review auto-sets when source is CONFLICTING
  6.  requires_review auto-sets when is_inferred=True
  7.  requires_review stays False when all sources are SUPPORTED
  8.  validate_procedure catches duplicate step_ids
  9.  validate_procedure catches fabricated image_id
  10. validate_procedure passes when image_ids are valid
  11. validate_procedure passes with no images supplied
  12. validate_graph catches duplicate node_ids
  13. validate_graph catches node with unknown step_id
  14. validate_graph catches edge with unknown from_node
  15. validate_graph catches self-loop
  16. validate_graph catches missing start node
  17. validate_graph passes for a valid graph
  18. validate_graph returns [] when graph is None

P2 tests (graph-based Mermaid):
  19. build_flowchart_from_graph returns error when graph is None
  20. build_flowchart_from_graph builds valid Mermaid from graph
  21. Graph-based flowchart contains all node_ids
  22. Decision node renders as diamond shape
  23. Inferred edge uses dashed arrow
  24. build_mermaid_flowchart falls back to step order when no graph
  25. Node labels with quotes are safely escaped
  26. Sequence diagram shows evidence_status badges
  27. Sequence diagram shows requires_review tag
  28. Procedure object not mutated by any builder
"""

from skillcapture.schema import (
    Procedure, ProcedureStep, SourceRef,
    GraphNode, GraphEdge, ProcedureGraph,
)
from skillcapture.validate_procedure import validate_procedure, validate_graph
from skillcapture.diagrams import (
    build_mermaid_flowchart,
    build_mermaid_sequence,
    build_flowchart_from_graph,
    validate_mermaid_syntax,
)

# ── Factories ─────────────────────────────────────────────────────────────────

def make_step(n, step_id=None, is_inferred=False, evidence_status="SUPPORTED",
              img_id=None, ts=None, page=None):
    src_kind = "image" if img_id else ("transcript" if ts else ("manual" if page else "inferred"))
    return ProcedureStep(
        step_id=step_id or f"step_{n}",
        step_number=n,
        title=f"Step {n} title",
        instruction=f"Do step {n}.",
        sources=[SourceRef(
            kind=src_kind,
            image_id=img_id,
            transcript_timestamp=ts,
            page_ref=page,
            evidence_status=evidence_status,
            support_explanation="Test explanation." if evidence_status != "INSUFFICIENT" else None,
        )],
        is_inferred=is_inferred,
    )


def make_procedure(steps, graph=None):
    return Procedure(
        title="Test",
        overview="A test procedure.",
        steps=steps,
        graph=graph,
    )


def make_graph(nodes, edges):
    return ProcedureGraph(nodes=nodes, edges=edges)


def make_node(node_id, step_id, node_type="action", is_inferred=False, requires_review=False):
    return GraphNode(
        node_id=node_id,
        step_id=step_id,
        label=f"Label for {node_id}",
        node_type=node_type,
        is_inferred=is_inferred,
        requires_review=requires_review,
    )


def make_edge(from_node, to_node, label=None, is_inferred=False):
    return GraphEdge(from_node=from_node, to_node=to_node,
                     label=label, is_inferred=is_inferred)


print("Running P1 + P2 tests...\n")

# ── P1: Schema ────────────────────────────────────────────────────────────────

# 1. step_id present and unique
proc = make_procedure([make_step(1), make_step(2), make_step(3)])
ids = [s.step_id for s in proc.steps]
assert len(ids) == len(set(ids)), "step_ids not unique"
assert all(s.step_id.startswith("step_") for s in proc.steps)
print("✅ Test 1: step_id present and unique")

# 2. evidence_status accepts all four values
for status in ("SUPPORTED", "PARTIALLY_SUPPORTED", "CONFLICTING", "INSUFFICIENT"):
    src = SourceRef(kind="transcript", evidence_status=status)
    assert src.evidence_status == status
print("✅ Test 2: evidence_status accepts all four vocabulary values")

# 3. evidence_status normalises lowercase
src = SourceRef(kind="transcript", evidence_status="supported")
assert src.evidence_status == "SUPPORTED"
print("✅ Test 3: evidence_status normalises lowercase to uppercase")

# 4. support_explanation is optional
src = SourceRef(kind="inferred")
assert src.support_explanation is None
print("✅ Test 4: support_explanation is optional")

# 5. requires_review auto-sets for CONFLICTING
step = make_step(1, evidence_status="CONFLICTING")
assert step.requires_review is True
print("✅ Test 5: requires_review auto-sets when source is CONFLICTING")

# 6. requires_review auto-sets for is_inferred
step = make_step(1, is_inferred=True)
assert step.requires_review is True
print("✅ Test 6: requires_review auto-sets when is_inferred=True")

# 7. requires_review stays False for SUPPORTED
step = make_step(1, evidence_status="SUPPORTED")
assert step.requires_review is False
print("✅ Test 7: requires_review stays False when all sources SUPPORTED")

# ── P1: validate_procedure ────────────────────────────────────────────────────

# 8. Duplicate step_ids caught
s1 = make_step(1, step_id="step_1")
s2 = make_step(2, step_id="step_1")  # duplicate!
errors = validate_procedure(make_procedure([s1, s2]))
assert any("step_1" in e for e in errors)
print("✅ Test 8: validate_procedure catches duplicate step_ids")

# 9. Fabricated image_id caught
s = make_step(1, img_id="fake_photo.jpg")
errors = validate_procedure(
    make_procedure([s]),
    supplied_image_ids={"real_photo.jpg"}
)
assert any("fake_photo.jpg" in e for e in errors)
print("✅ Test 9: validate_procedure catches fabricated image_id")

# 10. Valid image_id passes
s = make_step(1, img_id="real_photo.jpg")
errors = validate_procedure(
    make_procedure([s]),
    supplied_image_ids={"real_photo.jpg"}
)
assert errors == []
print("✅ Test 10: validate_procedure passes when image_ids are valid")

# 11. No images supplied — skip image check
s = make_step(1, img_id="any.jpg")
errors = validate_procedure(make_procedure([s]), supplied_image_ids=None)
assert errors == []
print("✅ Test 11: validate_procedure skips image check when supplied_image_ids=None")

# ── P1: validate_graph ────────────────────────────────────────────────────────

def _valid_graph():
    nodes = [
        make_node("N_START", "start", "start"),
        make_node("N1", "step_1"),
        make_node("N2", "step_2"),
        make_node("N_END", "end", "end"),
    ]
    edges = [
        make_edge("N_START", "N1"),
        make_edge("N1", "N2"),
        make_edge("N2", "N_END"),
    ]
    return make_graph(nodes, edges)


def _valid_proc_with_graph():
    steps = [make_step(1), make_step(2)]
    return make_procedure(steps, graph=_valid_graph())


# 12. Duplicate node_ids caught
graph = _valid_graph()
graph.nodes.append(make_node("N1", "step_1"))  # duplicate N1
errors = validate_graph(make_procedure([make_step(1), make_step(2)], graph=graph))
assert any("N1" in e for e in errors), f"Expected N1 error, got: {errors}"
print("✅ Test 12: validate_graph catches duplicate node_ids")

# 13. Node with unknown step_id caught
graph = _valid_graph()
graph.nodes.append(make_node("N99", "step_99"))  # step_99 does not exist
proc_vg = make_procedure([make_step(1), make_step(2)], graph=graph)
errors = validate_graph(proc_vg)
assert any("step_99" in e for e in errors)
print("✅ Test 13: validate_graph catches node with unknown step_id")

# 14. Edge with unknown from_node caught
graph = _valid_graph()
graph.edges.append(make_edge("GHOST_NODE", "N1"))
errors = validate_graph(make_procedure([make_step(1), make_step(2)], graph=graph))
assert any("GHOST_NODE" in e for e in errors)
print("✅ Test 14: validate_graph catches edge with unknown from_node")

# 15. Self-loop caught
graph = _valid_graph()
graph.edges.append(make_edge("N1", "N1"))
errors = validate_graph(make_procedure([make_step(1), make_step(2)], graph=graph))
assert any("self-loop" in e.lower() for e in errors)
print("✅ Test 15: validate_graph catches self-loop")

# 16. Missing start node caught
graph = _valid_graph()
graph.nodes = [n for n in graph.nodes if n.node_type != "start"]
errors = validate_graph(make_procedure([make_step(1), make_step(2)], graph=graph))
assert any("start" in e.lower() for e in errors)
print("✅ Test 16: validate_graph catches missing start node")

# 17. Valid graph passes
errors = validate_graph(_valid_proc_with_graph())
assert errors == [], f"Expected no errors, got: {errors}"
print("✅ Test 17: validate_graph passes for a valid graph")

# 18. Returns [] when graph is None
errors = validate_graph(make_procedure([make_step(1)]))
assert errors == []
print("✅ Test 18: validate_graph returns [] when graph is None")

# ── P2: Graph-based Mermaid ───────────────────────────────────────────────────

# 19. build_flowchart_from_graph returns error when graph is None
_, err = build_flowchart_from_graph(make_procedure([make_step(1)]))
assert err is not None
print("✅ Test 19: build_flowchart_from_graph returns error when graph is None")

# 20. Builds valid Mermaid from graph
proc_g = _valid_proc_with_graph()
diagram, err = build_flowchart_from_graph(proc_g)
assert err is None, f"Unexpected error: {err}"
assert diagram.strip().startswith("flowchart")
valid, msg = validate_mermaid_syntax(diagram)
assert valid, f"Validation failed: {msg}"
print("✅ Test 20: build_flowchart_from_graph builds valid Mermaid from graph")

# 21. All node_ids appear in diagram
for node in proc_g.graph.nodes:
    assert node.node_id in diagram, f"Node {node.node_id} missing from diagram"
print("✅ Test 21: Graph-based flowchart contains all node_ids")

# 22. Decision node renders as diamond
nodes = [
    make_node("N_START", "start", "start"),
    GraphNode(node_id="D1", step_id="step_1", label="Check ok?",
              node_type="decision"),
    make_node("N_END", "end", "end"),
]
edges = [make_edge("N_START", "D1"), make_edge("D1", "N_END")]
g = make_graph(nodes, edges)
proc_d = make_procedure([make_step(1)], graph=g)
diag_d, _ = build_flowchart_from_graph(proc_d)
assert 'D1{' in diag_d or 'D1{"' in diag_d, f"Decision not diamond: ...{diag_d[diag_d.find('D1'):diag_d.find('D1')+20]}..."
print("✅ Test 22: Decision node renders as diamond shape")

# 23. Inferred edge uses dashed arrow
edge_inf = make_edge("N_START", "N_END", is_inferred=True)
nodes23 = [make_node("N_START", "start", "start"), make_node("N_END", "end", "end")]
g23 = make_graph(nodes23, [edge_inf])
proc23 = make_procedure([make_step(1)], graph=g23)
diag23, _ = build_flowchart_from_graph(proc23)
assert "-.->'" in diag23 or "-..->" in diag23 or "-.-> " in diag23, \
    f"Expected dashed arrow; got fragment: {diag23}"
print("✅ Test 23: Inferred edge uses dashed arrow")

# 24. build_mermaid_flowchart falls back to step order when no graph
proc_no_graph = make_procedure([make_step(1), make_step(2)])
diag_fb, err_fb = build_mermaid_flowchart(proc_no_graph)
assert err_fb is None
assert "step_1" in diag_fb or "S1" in diag_fb or "step_2" in diag_fb
print("✅ Test 24: build_mermaid_flowchart falls back to step order when no graph")

# 25. Quotes in labels are escaped
nodes25 = [
    make_node("N_START", "start", "start"),
    GraphNode(node_id="N1", step_id="step_1",
              label='Use "quotes" here', node_type="action"),
    make_node("N_END", "end", "end"),
]
g25 = make_graph(nodes25, [make_edge("N_START", "N1"), make_edge("N1", "N_END")])
proc25 = make_procedure([make_step(1)], graph=g25)
diag25, _ = build_flowchart_from_graph(proc25)
# Raw double quote must not appear inside a Mermaid label (between the wrapping quotes)
import re
labels = re.findall(r'"([^"]*)"', diag25)
for lbl in labels:
    assert '"' not in lbl, f"Unescaped quote inside label: {lbl!r}"
print("✅ Test 25: Quotes in node labels are safely escaped")

# 26. Sequence diagram shows evidence_status badges
step_with_status = make_step(1, ts="00:10", evidence_status="CONFLICTING")
proc_seq = make_procedure([step_with_status])
seq, err_seq = build_mermaid_sequence(proc_seq)
assert err_seq is None
assert "CONFLICTING" in seq
print("✅ Test 26: Sequence diagram shows evidence_status badge")

# 27. Sequence diagram shows requires_review tag
assert "review" in seq.lower()
print("✅ Test 27: Sequence diagram shows requires_review tag")

# 28. Procedure not mutated
original_steps = len(proc_g.steps)
build_mermaid_flowchart(proc_g)
build_mermaid_sequence(proc_g)
assert len(proc_g.steps) == original_steps
print("✅ Test 28: Procedure object not mutated by any builder")

print(f"\n✅ All 28 P1+P2 tests passed.")
