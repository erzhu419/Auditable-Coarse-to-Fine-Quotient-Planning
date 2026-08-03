from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from types import SimpleNamespace

import pytest

from acfqp.phase3e_ids import canonical_json_bytes
from acfqp import v075_portable_occurrence_evidence_bundle_v2 as portable


def _id(label: str) -> str:
    return hashlib.sha256(
        b"acfqp:v075-portable-dependency-optimization-test:v2\x00"
        + label.encode("utf-8")
    ).hexdigest()


def _node(
    label: str,
    document: dict,
    *,
    role: str = "TEST_RECORD",
) -> portable._DependencyNode:  # noqa: SLF001
    return portable._DependencyNode(  # noqa: SLF001
        _id("key-" + label),
        role,
        _id("semantic-" + label),
        canonical_json_bytes(document),
    )


def _fake_nested_record_chain(depth: int) -> tuple[SimpleNamespace, ...]:
    """Build independently parsed records with quadratically many JSON edges."""

    role = "CONTROLLED_ROOT_SEMANTIC_AUTHORITY"
    schema = portable.ROLE_SCHEMA_REGISTRY[role]
    raw_documents: list[bytes] = []
    prior_document: dict | None = None
    for ordinal in range(depth):
        document = {
            "schema": schema,
            "binding_id": _id(f"nested-chain-binding-{ordinal}"),
        }
        if prior_document is None:
            document["leaf"] = {"label": "terminal", "value": 0}
        else:
            document["embedded"] = prior_document
        raw = canonical_json_bytes(document)
        raw_documents.append(raw)
        # The next registered raw contains a complete copy, like independently
        # serialized artifacts.  It does not share Python compound identities.
        prior_document = json.loads(raw.decode("utf-8"))

    records: list[SimpleNamespace] = []
    for ordinal, raw in enumerate(raw_documents):
        records.append(
            SimpleNamespace(
                role=role,
                artifact_schema=schema,
                semantic_artifact_id=_id(
                    f"nested-chain-semantic-{ordinal}"
                ),
                record_id=_id(f"nested-chain-record-{ordinal}"),
                canonical_artifact_bytes=raw,
                artifact_document=json.loads(raw.decode("utf-8")),
            )
        )
    return tuple(records)


def test_exact_structural_interner_matches_complete_canonical_bytes() -> None:
    values = (
        None,
        False,
        True,
        0,
        1,
        -17,
        1.0,
        -0.0,
        0.0,
        1.5,
        "",
        "unicode-雪",
        [],
        {},
        [1, 1.0, True, None, {"x": ["y", -3]}],
        {"b": [2, 3], "a": {"nested": "value"}},
        {"a": {"nested": "changed"}, "b": [2, 3]},
    )
    interner = portable._ExactJSONStructuralInternerV1()  # noqa: SLF001
    node_ids = tuple(interner.intern(deepcopy(value)) for value in values)
    canonical = tuple(canonical_json_bytes(value) for value in values)
    for left in range(len(values)):
        for right in range(len(values)):
            assert (node_ids[left] == node_ids[right]) == (
                canonical[left] == canonical[right]
            )
    assert interner.intern(-0.0) == interner.intern(0.0)
    assert interner.intern(1) != interner.intern(1.0)
    assert interner.intern(True) != interner.intern(1)


def test_exact_structural_interner_deep_shared_and_order_adversaries() -> None:
    interner = portable._ExactJSONStructuralInternerV1()  # noqa: SLF001
    ordered_left = {"z": [3, 2], "a": {"x": "same"}}
    ordered_right = {"a": {"x": "same"}, "z": [3, 2]}
    assert interner.intern(ordered_left) == interner.intern(ordered_right)

    deep_left: dict = {"terminal": [None, False, 0, 0.0]}
    for ordinal in range(240):
        deep_left = {"ordinal": ordinal, "next": deep_left}
    deep_right = deepcopy(deep_left)
    assert interner.intern(deep_left) == interner.intern(deep_right)
    deep_different = deepcopy(deep_left)
    deep_different["next"]["next"]["ordinal"] = -1
    assert interner.intern(deep_left) != interner.intern(deep_different)

    shared = {"payload": [1, {"value": "shared"}]}
    shared_tree = [shared, shared]
    copied_tree = [deepcopy(shared), deepcopy(shared)]
    assert interner.intern(shared_tree) == interner.intern(copied_tree)


def test_exact_structural_interner_rejects_cycle_and_non_string_key() -> None:
    cyclic: dict = {}
    cyclic["self"] = cyclic
    with pytest.raises(
        portable.V075PortableOccurrenceEvidenceV2InvariantViolation,
        match="cyclic JSON value",
    ):
        portable._ExactJSONStructuralInternerV1().intern(cyclic)  # noqa: SLF001
    with pytest.raises(
        portable.V075PortableOccurrenceEvidenceV2InvariantViolation,
        match="non-string object key",
    ):
        portable._ExactJSONStructuralInternerV1().intern(  # noqa: SLF001
            {1: "not-json"}
        )


def _fake_registered_record(
    ordinal: int,
    document: dict,
) -> SimpleNamespace:
    raw = canonical_json_bytes(document)
    role = "CONTROLLED_ROOT_SEMANTIC_AUTHORITY"
    return SimpleNamespace(
        role=role,
        artifact_schema=portable.ROLE_SCHEMA_REGISTRY[role],
        semantic_artifact_id=_id(f"exact-child-semantic-{ordinal}"),
        record_id=_id(f"exact-child-record-{ordinal}"),
        canonical_artifact_bytes=raw,
        artifact_document=json.loads(raw.decode("utf-8")),
    )


def test_nested_binding_exact_child_passes_same_identity_mutation_fails() -> None:
    role = "CONTROLLED_ROOT_SEMANTIC_AUTHORITY"
    schema = portable.ROLE_SCHEMA_REGISTRY[role]
    child_document = {
        "schema": schema,
        "binding_id": _id("exact-child-binding"),
        "payload": {"value": 7, "type_guard": [True, 1, 1.0]},
    }
    child = _fake_registered_record(0, child_document)
    exact_owner = _fake_registered_record(
        1,
        {
            "schema": schema,
            "binding_id": _id("exact-owner-binding"),
            "embedded": child_document,
        },
    )
    portable._verify_nested_registered_document_bindings(  # noqa: SLF001
        (child, exact_owner)
    )

    mutated_child = deepcopy(child_document)
    # Preserve schema and primary semantic identity; only a complete value
    # differs.  Primary-ID or shape matching must not launder this mutation.
    mutated_child["payload"]["value"] = 8
    attacked_owner = _fake_registered_record(
        2,
        {
            "schema": schema,
            "binding_id": _id("attacked-owner-binding"),
            "embedded": mutated_child,
        },
    )
    with pytest.raises(
        portable.V075PortableOccurrenceEvidenceV2InvariantViolation,
        match="canonical bytes differ from its unique record",
    ):
        portable._verify_nested_registered_document_bindings(  # noqa: SLF001
            (child, attacked_owner)
        )


def test_nested_binding_verifier_never_reserializes_candidate_subtrees(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    records = _fake_nested_record_chain(48)
    original = portable.canonical_json_bytes
    calls = 0

    def counted(value):
        nonlocal calls
        calls += 1
        return original(value)

    monkeypatch.setattr(portable, "canonical_json_bytes", counted)
    portable._verify_nested_registered_document_bindings(records)  # noqa: SLF001
    # The complete full-value equality authority is now the type-aware tree
    # interner.  A call here would reintroduce subtree-size-dependent work.
    assert calls == 0


def _reference_dependency_graph(
    nodes: tuple[portable._DependencyNode, ...],  # noqa: SLF001
) -> dict[object, frozenset[object]]:
    """Frozen pre-optimization formula used only as a bit-exact oracle."""

    keys_by_semantic_id: dict[str, set[object]] = {}
    keys_by_raw: dict[bytes, set[object]] = {}
    append_keys_by_receipt_id: dict[str, set[object]] = {}
    documents: dict[object, dict] = {}
    for node in nodes:
        keys_by_semantic_id.setdefault(
            node.semantic_artifact_id,
            set(),
        ).add(node.key)
        keys_by_raw.setdefault(node.raw, set()).add(node.key)
        document = portable._strict_json_document(  # noqa: SLF001
            node.raw,
            label=node.role,
        )
        documents[node.key] = document
        if node.role in {
            "CONTROLLED_ROOT_APPEND",
            "CONTROLLED_CHILD_APPEND",
            "CONTROLLED_PROMOTION_APPEND",
        }:
            receipt_id = portable._cid(  # noqa: SLF001
                document.get("append_receipt_id"),
                "controlled append receipt",
            )
            append_keys_by_receipt_id.setdefault(receipt_id, set()).add(
                node.key
            )
    dependencies: dict[object, frozenset[object]] = {}
    append_reference_excluded_roles = {
        "SIGNED_APPEND_RECEIPT",
        "CONTROLLED_ROOT_APPEND",
        "CONTROLLED_CHILD_APPEND",
        "CONTROLLED_PROMOTION_APPEND",
    }
    for node in nodes:
        document = documents[node.key]
        referenced: set[object] = set()
        content_ids = portable._content_ids(document)  # noqa: SLF001
        for semantic_id in content_ids:
            referenced.update(keys_by_semantic_id.get(semantic_id, ()))
        for nested in portable._nested_documents(document):  # noqa: SLF001
            nested_raw = portable.canonical_json_bytes(nested)
            referenced.update(keys_by_raw.get(nested_raw, ()))
        if node.role not in append_reference_excluded_roles:
            for semantic_id in content_ids:
                referenced.update(
                    append_keys_by_receipt_id.get(semantic_id, ())
                )
        referenced.discard(node.key)
        dependencies[node.key] = frozenset(referenced)
    return dependencies


def test_optimized_dependency_graph_is_bit_exact_to_reference() -> None:
    child_document = {
        "schema": "acfqp.test_child.v1",
        "name": "child",
        "value": 7,
    }
    child = _node("child", child_document)
    semantic_child = _node(
        "semantic-child",
        {"schema": "acfqp.test_semantic_child.v1", "value": 3},
    )
    parent = _node(
        "parent",
        {
            "embedded": child_document,
            "semantic_reference": semantic_child.semantic_artifact_id,
            "unrelated": {
                "different": [1, 2, {"shape": "not-a-record"}],
            },
        },
    )
    nodes = (child, semantic_child, parent)
    optimized = portable._derive_dependency_graph(nodes)  # noqa: SLF001
    reference = _reference_dependency_graph(nodes)
    assert optimized == reference
    assert optimized[parent.key] == frozenset(
        {child.key, semantic_child.key}
    )


def test_equal_shape_different_value_requires_complete_byte_equality() -> None:
    child_document = {
        "schema": "acfqp.test_equal_shape.v1",
        "label": "registered",
        "value": 11,
    }
    child = _node("equal-shape-child", child_document)
    different = deepcopy(child_document)
    different["label"] = "adversarial"
    different["value"] = 12
    parent = _node(
        "equal-shape-parent",
        {
            "schema": "acfqp.test_equal_shape_parent.v1",
            "embedded": different,
        },
    )
    dependencies = portable._derive_dependency_graph(  # noqa: SLF001
        (child, parent)
    )
    assert child.key not in dependencies[parent.key]
    assert dependencies == _reference_dependency_graph((child, parent))


def test_schema_less_complete_document_is_still_discovered() -> None:
    child_document = {"kind": "schema-less-child", "value": 19}
    child = _node("schema-less-child", child_document)
    parent = _node(
        "schema-less-parent",
        {
            "schema": "acfqp.test_schema_less_parent.v1",
            "embedded": child_document,
        },
    )
    dependencies = portable._derive_dependency_graph(  # noqa: SLF001
        (child, parent)
    )
    assert dependencies[parent.key] == frozenset({child.key})
    assert dependencies == _reference_dependency_graph((child, parent))


def test_nested_full_document_mutation_removes_only_the_exact_edge() -> None:
    child_document = {
        "schema": "acfqp.test_nested_full_document.v1",
        "payload": {"items": [1, 2, 3]},
        "status": "frozen",
    }
    child = _node("nested-full-child", child_document)
    exact_parent = _node(
        "nested-full-parent",
        {
            "schema": "acfqp.test_nested_full_parent.v1",
            "embedded": child_document,
        },
    )
    exact = portable._derive_dependency_graph(  # noqa: SLF001
        (child, exact_parent)
    )
    assert exact[exact_parent.key] == frozenset({child.key})

    mutated_document = deepcopy(child_document)
    mutated_document["payload"]["items"][1] = 999
    mutated_parent = _node(
        "nested-mutated-parent",
        {
            "schema": "acfqp.test_nested_full_parent.v1",
            "embedded": mutated_document,
        },
    )
    mutated = portable._derive_dependency_graph(  # noqa: SLF001
        (child, mutated_parent)
    )
    assert child.key not in mutated[mutated_parent.key]
    assert mutated == _reference_dependency_graph((child, mutated_parent))


def test_candidate_filter_skips_nonrecord_nested_shapes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    child_document = {
        "schema": "acfqp.test_filter_child.v1",
        "value": 1,
    }
    chain: dict = {"terminal": True}
    for ordinal in range(80):
        chain = {"ordinal": ordinal, "next": chain}
    child = _node("filter-child", child_document)
    parent = _node(
        "filter-parent",
        {
            "schema": "acfqp.test_filter_parent.v1",
            "embedded": child_document,
            "unrelated_chain": chain,
        },
    )
    original = portable.canonical_json_bytes
    calls = 0

    def counted(value):
        nonlocal calls
        calls += 1
        return original(value)

    monkeypatch.setattr(portable, "canonical_json_bytes", counted)
    optimized = portable._derive_dependency_graph((child, parent))  # noqa: SLF001
    optimized_calls = calls
    calls = 0
    reference = _reference_dependency_graph((child, parent))
    reference_calls = calls
    assert optimized == reference
    assert optimized_calls < 10
    assert reference_calls > 80


def test_non_string_schema_and_primitive_type_adversaries_are_bit_exact() -> None:
    child_document = {
        "schema": ["deliberately", {"not": "a string"}],
        "bool_value": True,
        "float_value": 1.0,
        "int_value": 1,
        "null_value": None,
        "payload": {"nested": [0, False, "value"]},
    }
    child = _node("adversarial-schema-child", child_document)
    exact_parent = _node(
        "adversarial-schema-exact-parent",
        {
            "schema": "acfqp.test_adversarial_schema_parent.v1",
            "embedded": child_document,
        },
    )
    different_document = deepcopy(child_document)
    different_document["bool_value"] = 1
    different_document["int_value"] = True
    different_parent = _node(
        "adversarial-schema-different-parent",
        {
            "schema": "acfqp.test_adversarial_schema_parent.v1",
            "embedded": different_document,
        },
    )
    nodes = (child, exact_parent, different_parent)
    optimized = portable._derive_dependency_graph(nodes)  # noqa: SLF001
    assert optimized == _reference_dependency_graph(nodes)
    assert child.key in optimized[exact_parent.key]
    assert child.key not in optimized[different_parent.key]


def test_duplicate_complete_raws_preserve_every_exact_raw_edge() -> None:
    shared_document = {
        "schema": "acfqp.test_duplicate_complete_raw.v1",
        "payload": {"value": 23},
    }
    first = _node("duplicate-first", shared_document)
    second = _node("duplicate-second", shared_document)
    parent = _node(
        "duplicate-parent",
        {
            "schema": "acfqp.test_duplicate_parent.v1",
            "embedded": shared_document,
        },
    )
    nodes = (first, second, parent)
    optimized = portable._derive_dependency_graph(nodes)  # noqa: SLF001
    assert optimized == _reference_dependency_graph(nodes)
    # The frozen formula treats complete canonical bytes as evidence.  It
    # therefore retains both records when their bytes are identical.
    assert optimized[parent.key] == frozenset({first.key, second.key})
    assert optimized[first.key] == frozenset({second.key})
    assert optimized[second.key] == frozenset({first.key})


def test_append_receipt_edges_and_excluded_roles_match_reference() -> None:
    receipt_id = _id("append-receipt")
    receipt = portable._DependencyNode(  # noqa: SLF001
        _id("key-append-receipt"),
        "SIGNED_APPEND_RECEIPT",
        receipt_id,
        canonical_json_bytes(
            {
                "kind": "signed-append-receipt",
                "receipt_marker": "frozen",
            }
        ),
    )
    controlled_append = portable._DependencyNode(  # noqa: SLF001
        _id("key-controlled-append"),
        "CONTROLLED_ROOT_APPEND",
        _id("semantic-controlled-append"),
        canonical_json_bytes(
            {
                "append_receipt_id": receipt_id,
                "kind": "controlled-root-append",
            }
        ),
    )
    consumer = _node(
        "append-consumer",
        {
            "kind": "ordinary-consumer",
            "receipt_reference": receipt_id,
        },
    )
    nodes = (receipt, controlled_append, consumer)
    optimized = portable._derive_dependency_graph(nodes)  # noqa: SLF001
    assert optimized == _reference_dependency_graph(nodes)
    assert optimized[controlled_append.key] == frozenset({receipt.key})
    assert optimized[consumer.key] == frozenset(
        {receipt.key, controlled_append.key}
    )
    # Exclusion prevents receipt/append records from acquiring the synthetic
    # reverse edge from receipt ID to the controlled append itself.
    assert controlled_append.key not in optimized[receipt.key]


def test_self_references_are_discarded_after_all_edge_sources() -> None:
    semantic_id = _id("self-semantic")
    document = {
        "kind": "self-referencing-record",
        "semantic_reference": semantic_id,
    }
    node = portable._DependencyNode(  # noqa: SLF001
        _id("key-self-reference"),
        "TEST_RECORD",
        semantic_id,
        canonical_json_bytes(document),
    )
    optimized = portable._derive_dependency_graph((node,))  # noqa: SLF001
    assert optimized == _reference_dependency_graph((node,))
    assert optimized[node.key] == frozenset()


@pytest.mark.parametrize(
    "raw",
    (
        b"[]",
        b'{"a":1,"a":2}',
        b'{"a":NaN}',
        b'{"b":1,"a":2}',
        b'{"a":1 }',
        b"\xff",
    ),
)
def test_malformed_artifacts_fail_before_candidate_filtering(raw: bytes) -> None:
    node = portable._DependencyNode(  # noqa: SLF001
        _id("key-malformed-" + raw.hex()),
        "MALFORMED_TEST_RECORD",
        _id("semantic-malformed-" + raw.hex()),
        raw,
    )
    with pytest.raises(
        portable.V075PortableOccurrenceEvidenceV2InvariantViolation
    ) as optimized_error:
        portable._derive_dependency_graph((node,))  # noqa: SLF001
    with pytest.raises(
        portable.V075PortableOccurrenceEvidenceV2InvariantViolation
    ) as reference_error:
        _reference_dependency_graph((node,))
    assert str(optimized_error.value) == str(reference_error.value)
