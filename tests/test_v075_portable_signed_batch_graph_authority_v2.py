from __future__ import annotations

import hashlib
from types import SimpleNamespace

import pytest

from acfqp import v075_portable_signed_batch_graph_authority_v2 as authority
from acfqp import v075_private_observer_boundary_v2 as observer
from tests.test_v075_portable_public_semantic_replay_v2 import (  # noqa: F401
    PROJECT_ROOT,
    real_raw_m0_bundle,
)


@pytest.fixture(scope="module")
def real_k7_m1a(real_raw_m0_bundle):
    patcher = pytest.MonkeyPatch()

    def forbidden(*_args, **_kwargs):
        raise AssertionError("M1A crossed a private replay channel")

    patcher.setattr(
        observer,
        "verify_loaded_private_observer_batch_closure_v2",
        forbidden,
    )
    try:
        yield authority.replay_v075_portable_signed_batch_graph_v2(
            repository_root=PROJECT_ROOT,
            portable_bundle_bytes=(
                real_raw_m0_bundle["bundle"].canonical_bytes
            ),
            public_context_closure_bytes=(
                real_raw_m0_bundle["closure"].canonical_bytes
            ),
        )
    finally:
        patcher.undo()


def test_real_k7_replays_six_public_roles_and_keeps_verification_incomplete(
    real_k7_m1a,
) -> None:
    document = real_k7_m1a.to_document()
    attestations = real_k7_m1a.attestations
    for role in authority.M1A_COMPLETE_ROLE_ORDER:
        assert {
            item.status
            for item in attestations
            if item.role == role
        } == {authority.V075PortableM1ARoleReplayStatusV2.COMPLETE}
    assert {
        item.status
        for item in attestations
        if item.role == authority.M1A_VERIFICATION_ROLE
    } == {
        authority.V075PortableM1ARoleReplayStatusV2
        .UNRESOLVED_PRIVATE_REPLAY_CLAIM
    }
    assert document["six_public_role_semantics_complete"] is True
    assert document[
        "signed_batch_journal_closure_verification_status"
    ] == "UNRESOLVED_PRIVATE_REPLAY_CLAIM"
    assert document[
        "closure_verification_private_native_replay_complete"
    ] is False
    assert document["m1a_role_semantics_complete"] is False
    assert document["joined_m0_m1a_dependency_discharge_complete"] is True
    assert document["m0_unresolved_dependency_record_ids_before_join"]
    assert document["m0_unresolved_dependency_record_ids_after_join"] == []
    assert document[
        "all_m1a_declared_dependency_frontiers_resolved"
    ] is True
    assert document["transitive_closure_materialized"] is False
    assert document["dependency_proof_shape"] == (
        "ITERATIVE_TOPOLOGICAL_DIRECT_EDGE_DAG"
    )
    # Public typed views remain independently replayable without the private
    # verifier or its salt/environment inputs.
    assert real_k7_m1a.typed_graph.verification_projection[
        "verification_result"
    ] == "EXACT_BATCH_NATIVE_V2_REPLAY_VERIFIED"


def test_real_k7_maps_all_records_once_and_never_uniquifies_outcome_id(
    real_raw_m0_bundle,
    real_k7_m1a,
) -> None:
    graph = real_k7_m1a.typed_graph
    expected_records = tuple(
        item
        for item in real_raw_m0_bundle["bundle"].records
        if item.role in authority.M1A_ROLE_ORDER
    )
    assert tuple(
        item.record_id for item in graph.record_bindings
    ) == tuple(item.record_id for item in expected_records)
    assert len({item.record_id for item in graph.record_bindings}) == len(
        graph.record_bindings
    )

    diagnostic = graph.outcome_records_by_outcome_id
    shared = {
        outcome_id: record_ids
        for outcome_id, record_ids in diagnostic.items()
        if len(record_ids) > 1
    }
    assert shared
    record_by_id = {
        item.record_id: item for item in graph.record_bindings
    }
    for record_ids in shared.values():
        raws = {
            record_by_id[record_id].canonical_artifact_bytes
            for record_id in record_ids
        }
        assert len(raws) == len(record_ids)
    assert real_k7_m1a.to_document()["outcome_record_key"] == (
        "NESTED_CANONICAL_BYTES"
    )
    assert (
        real_k7_m1a.to_document()["outcome_id_is_unique_record_key"]
        is False
    )


def test_compact_dependency_dag_handles_full_4096_entry_chain() -> None:
    record_count = 4096
    record_ids = tuple(
        hashlib.sha256(f"M1A-cap-node-{index}".encode()).hexdigest()
        for index in range(record_count)
    )
    records = tuple(
        SimpleNamespace(
            record_id=record_id,
            index=index,
            role="CAP_CHAIN_TEST",
            dependency_record_ids=(
                () if index == 0 else (record_ids[index - 1],)
            ),
        )
        for index, record_id in enumerate(record_ids)
    )
    nodes = authority._iterative_dependency_resolution_nodes(  # noqa: SLF001
        records=records,
        m0_authority_record_ids=frozenset(record_ids),
        m1a_authority_record_ids=frozenset(),
    )
    assert len(nodes) == record_count
    assert nodes[-1].jointly_resolved is True
    assert sum(
        len(item.direct_dependency_record_ids) for item in nodes
    ) == record_count - 1


def test_attestation_names_only_the_declared_dependency_frontier() -> None:
    def identifier(label: str) -> str:
        return hashlib.sha256(label.encode()).hexdigest()

    attestation = authority.V075PortableM1ARecordSemanticAttestationV2(
        authority._ATTESTATION_ISSUER,  # noqa: SLF001
        identifier("bundle"),
        identifier("graph"),
        identifier("dag"),
        identifier("record"),
        0,
        "SIGNED_BATCH_REQUEST",
        identifier("semantic"),
        identifier("raw"),
        1,
        (),
        (),
        (),
        (),
        authority.V075PortableM1ARoleReplayStatusV2.COMPLETE,
    )
    document = attestation.to_document()
    assert document["declared_direct_dependency_frontier_resolved"] is True
    assert "dependency_subgraph_jointly_resolved" not in document


@pytest.mark.parametrize("attack", ("entry_order", "signature", "record_raw"))
def test_typed_graph_rejects_order_signature_and_raw_cache_attacks(
    real_k7_m1a,
    attack,
) -> None:
    typed_graph = real_k7_m1a.typed_graph
    closure = typed_graph.closure
    if attack == "entry_order":
        original = closure.entries
        assert len(original) > 1
        object.__setattr__(closure, "entries", tuple(reversed(original)))
        target, attribute, restore = closure, "entries", original
    elif attack == "signature":
        original = closure.observer_signature_hex
        replacement = "00" * (len(original) // 2)
        object.__setattr__(
            closure,
            "observer_signature_hex",
            replacement,
        )
        target, attribute, restore = (
            closure,
            "observer_signature_hex",
            original,
        )
    else:
        binding = next(
            item
            for item in typed_graph.record_bindings
            if item.role == "SIGNED_BATCH_JOURNAL_CLOSURE"
        )
        original = binding.canonical_artifact_bytes
        replacement = original[:-1] + (
            b"0" if original[-1:] != b"0" else b"1"
        )
        object.__setattr__(
            binding,
            "canonical_artifact_bytes",
            replacement,
        )
        target, attribute, restore = (
            binding,
            "canonical_artifact_bytes",
            original,
        )
    try:
        with pytest.raises(
            authority.V075PortableSignedBatchGraphV2InvariantViolation
        ):
            typed_graph._assert_current()  # noqa: SLF001
    finally:
        object.__setattr__(target, attribute, restore)
    typed_graph._assert_current()  # noqa: SLF001


@pytest.mark.parametrize(
    "attack",
    ("semantic_id", "record_index", "direct_dependencies"),
)
def test_typed_graph_full_record_commitment_rejects_mutation(
    real_k7_m1a,
    attack,
) -> None:
    typed_graph = real_k7_m1a.typed_graph
    binding = next(
        item
        for item in reversed(typed_graph.record_bindings)
        if item.role != authority.M1A_VERIFICATION_ROLE
    )
    if attack == "semantic_id":
        attribute = "semantic_artifact_id"
        original = binding.semantic_artifact_id
        replacement = hashlib.sha256(
            b"M1A-mutated-semantic-artifact"
        ).hexdigest()
    elif attack == "record_index":
        attribute = "record_index"
        original = binding.record_index
        replacement = original + len(typed_graph.record_bindings) + 1
    else:
        attribute = "dependency_record_ids"
        original = binding.dependency_record_ids
        foreign_dependency = hashlib.sha256(
            b"M1A-mutated-direct-dependency"
        ).hexdigest()
        assert foreign_dependency not in original
        replacement = tuple(sorted((*original, foreign_dependency)))
    object.__setattr__(binding, attribute, replacement)
    try:
        with pytest.raises(
            authority.V075PortableSignedBatchGraphV2InvariantViolation
        ):
            typed_graph._assert_current()  # noqa: SLF001
        with pytest.raises(
            authority.V075PortableSignedBatchGraphV2InvariantViolation
        ):
            real_k7_m1a.to_document()
    finally:
        object.__setattr__(binding, attribute, original)
    typed_graph._assert_current()  # noqa: SLF001


def test_attestation_mutation_and_fresh_transplant_are_rejected(
    real_k7_m1a,
) -> None:
    original = next(
        item
        for item in real_k7_m1a.attestations
        if item.role != authority.M1A_VERIFICATION_ROLE
    )
    foreign_semantic_id = hashlib.sha256(
        b"M1A-foreign-attestation-semantic"
    ).hexdigest()

    object.__setattr__(
        original,
        "semantic_artifact_id",
        foreign_semantic_id,
    )
    try:
        with pytest.raises(
            authority.V075PortableSignedBatchGraphV2InvariantViolation,
            match="attestation content identity is stale",
        ):
            original.to_document()
        with pytest.raises(
            authority.V075PortableSignedBatchGraphV2InvariantViolation
        ):
            real_k7_m1a.to_document()
    finally:
        object.__setattr__(
            original,
            "semantic_artifact_id",
            next(
                item.semantic_artifact_id
                for item in real_k7_m1a.typed_graph.record_bindings
                if item.record_id == original.record_id
            ),
        )
    real_k7_m1a._assert_current()  # noqa: SLF001

    forged = authority.V075PortableM1ARecordSemanticAttestationV2(
        authority._ATTESTATION_ISSUER,  # noqa: SLF001
        original.bundle_id,
        original.typed_graph_id,
        original.dependency_resolution_dag_id,
        original.record_id,
        original.record_index,
        original.role,
        foreign_semantic_id,
        original.canonical_artifact_sha256,
        original.canonical_artifact_byte_count,
        original.declared_direct_dependency_record_ids,
        original.joint_authority_resolved_direct_dependency_record_ids,
        original.unresolved_dependency_frontier_record_ids,
        original.unresolved_dependency_roles,
        original.status,
    )
    forged_attestations = tuple(
        forged if item.record_id == original.record_id else item
        for item in real_k7_m1a.attestations
    )
    with pytest.raises(
        authority.V075PortableSignedBatchGraphV2InvariantViolation,
        match="differs from graph record",
    ):
        authority.V075PortableSignedBatchGraphReplayV2(
            authority._RESULT_ISSUER,  # noqa: SLF001
            real_k7_m1a.bundle_id,
            real_k7_m1a.occurrence_id,
            real_k7_m1a.public_context_closure_id,
            real_k7_m1a.typed_graph,
            real_k7_m1a.dependency_resolution_dag,
            forged_attestations,
            real_k7_m1a.m0_unresolved_dependency_record_ids_before_join,
            real_k7_m1a.m0_dependency_record_ids_discharged,
            real_k7_m1a.m0_unresolved_dependency_record_ids_after_join,
        )


def test_dependency_dag_mutation_is_rejected(real_k7_m1a) -> None:
    node = real_k7_m1a.dependency_resolution_dag.nodes[-1]
    original = node.jointly_resolved
    object.__setattr__(node, "jointly_resolved", not original)
    try:
        with pytest.raises(
            authority.V075PortableSignedBatchGraphV2InvariantViolation,
            match="dependency resolution is inconsistent",
        ):
            real_k7_m1a.to_document()
    finally:
        object.__setattr__(node, "jointly_resolved", original)
    real_k7_m1a._assert_current()  # noqa: SLF001


def test_raw_gates_and_graph_identity_reject_transplants(
    real_raw_m0_bundle,
    real_k7_m1a,
) -> None:
    raw = bytearray(real_raw_m0_bundle["bundle"].canonical_bytes)
    raw[-2] = ord("0") if raw[-2] != ord("0") else ord("1")
    with pytest.raises(
        authority.V075PortableSignedBatchGraphV2InvariantViolation,
        match="portable bundle failed raw replay",
    ):
        authority.replay_v075_portable_signed_batch_graph_v2(
            repository_root=PROJECT_ROOT,
            portable_bundle_bytes=bytes(raw),
            public_context_closure_bytes=(
                real_raw_m0_bundle["closure"].canonical_bytes
            ),
        )

    typed_graph = real_k7_m1a.typed_graph
    original = typed_graph.occurrence_id
    foreign = hashlib.sha256(b"foreign-occurrence").hexdigest()
    object.__setattr__(typed_graph, "occurrence_id", foreign)
    try:
        with pytest.raises(
            authority.V075PortableSignedBatchGraphV2InvariantViolation,
            match="crossed bundle/context identities",
        ):
            typed_graph._assert_current()  # noqa: SLF001
    finally:
        object.__setattr__(typed_graph, "occurrence_id", original)
    typed_graph._assert_current()  # noqa: SLF001


def test_m1a_locks_and_production_boundary_remain_closed(
    real_k7_m1a,
) -> None:
    document = real_k7_m1a.to_document()
    for key in (
        "source_authority_complete",
        "code_provenance_complete",
        "portable_semantic_registry_complete",
        "observer_opened",
        "private_input_channels_allowed",
        "fresh_heldout_accessed",
        "official_execution_allowed",
        "production_authorizing",
        "scientific_endpoint_credit_allowed",
        "plan_certificate",
        "infeasibility_certificate",
        "private_material_serialized",
    ):
        assert document[key] is False
    assert authority.M1A_ROLE_SEMANTICS_COMPLETE is False
    assert authority.OFFICIAL_EXECUTION_ALLOWED is False
    assert authority.PRODUCTION_AUTHORIZING is False
    assert authority.PRIVATE_INPUT_CHANNELS_ALLOWED is False
    with pytest.raises(
        authority.V075PortableSignedBatchGraphProductionV2NotReady
    ):
        authority.open_v075_production_from_portable_signed_batch_graph_v2()
