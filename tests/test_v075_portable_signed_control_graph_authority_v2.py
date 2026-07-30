from __future__ import annotations

import hashlib
import inspect
from types import SimpleNamespace

import pytest

from acfqp import v075_portable_signed_control_graph_authority_v2 as authority
from acfqp import v075_private_observer_boundary_v2 as observer
from tests.test_v075_portable_public_semantic_replay_v2 import (  # noqa: F401
    PROJECT_ROOT,
    real_raw_m0_bundle,
)


def _id(label: str) -> str:
    return hashlib.sha256(
        b"acfqp:v075-m1b-control-test:v2\x00" + label.encode()
    ).hexdigest()


@pytest.fixture(scope="module")
def real_k7_m1b(real_raw_m0_bundle):
    patcher = pytest.MonkeyPatch()

    def forbidden(*_args, **_kwargs):
        raise AssertionError("M1B crossed the private replay boundary")

    patcher.setattr(
        observer,
        "verify_loaded_private_observer_batch_closure_v2",
        forbidden,
    )
    try:
        yield authority.replay_v075_portable_signed_control_graph_v2(
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


@pytest.fixture(scope="module")
def real_k7_document(real_k7_m1b):
    return real_k7_m1b.to_document()


def test_real_k7_root_only_has_three_honest_role_states(
    real_k7_document,
) -> None:
    document = real_k7_document
    statuses = document["role_closure_statuses"]
    for role in (
        *authority.GENERIC_CONTROL_ROLE_ORDER,
        *authority.ROOT_CONTROL_ROLE_ORDER,
    ):
        assert statuses[role] == "FULL_PUBLIC"
    for role in (
        *authority.CHILD_CONTROL_ROLE_ORDER,
        *authority.PROMOTION_CONTROL_ROLE_ORDER,
    ):
        assert statuses[role] == "NOT_PRESENT_IN_OCCURRENCE"

    assert document["control_structure_complete"] is True
    assert document["present_roles_semantically_complete"] is True
    assert document["all_registered_roles_covered"] is False
    assert document[
        "all_registered_roles_semantically_complete"
    ] is False
    assert set(document["absent_roles"]) == {
        *authority.CHILD_CONTROL_ROLE_ORDER,
        *authority.PROMOTION_CONTROL_ROLE_ORDER,
    }
    assert document["not_present_is_not_native_zero"] is True
    assert document["not_present_is_not_completion_evidence"] is True


def test_real_k7_reconstructs_every_present_control_record_once(
    real_raw_m0_bundle,
    real_k7_m1b,
) -> None:
    expected = tuple(
        item
        for item in real_raw_m0_bundle["bundle"].records
        if item.role in authority.CONTROL_ROLE_ORDER
    )
    bindings = real_k7_m1b.typed_graph.record_bindings
    assert tuple(item.record_id for item in bindings) == tuple(
        item.record_id for item in expected
    )
    assert len(real_k7_m1b.attestations) == len(expected)
    assert all(
        item.status
        is authority.V075PortableControlRoleClosureStatusV2.FULL_PUBLIC
        for item in real_k7_m1b.attestations
    )
    graph = real_k7_m1b.typed_graph
    assert len(graph.heads) == len(graph.appends) + 1
    assert tuple(item.entry_count for item in graph.heads) == tuple(
        range(len(graph.heads))
    )
    assert tuple(
        item.receipt.journal_sequence_number for item in graph.appends
    ) == tuple(range(1, len(graph.appends) + 1))


def test_m1a_private_verification_is_unresolved_and_never_consumed(
    real_k7_m1b,
    real_k7_document,
) -> None:
    document = real_k7_document
    verification_records = tuple(
        item
        for item in real_k7_m1b.typed_graph.m1a_result.typed_graph.record_bindings
        if item.role == authority.m1a.M1A_VERIFICATION_ROLE
    )
    assert len(verification_records) == 1
    verification_id = verification_records[0].record_id
    assert all(
        verification_id
        not in item.resolved_direct_dependency_record_ids
        for item in real_k7_m1b.attestations
    )
    assert document["m1a_closure_verification_status"] == (
        "UNRESOLVED_PRIVATE_REPLAY_CLAIM"
    )
    assert document["m1a_private_verification_claim_consumed"] is False
    assert document["private_replay_performed"] is False
    assert document["private_verifier_called"] is False
    parameters = inspect.signature(
        authority.replay_v075_portable_signed_control_graph_v2
    ).parameters
    assert {
        "private_salt",
        "private_environment",
        "verification",
        "signer",
        "observer_session",
    }.isdisjoint(parameters)


def _synthetic_records():
    roles = (
        "UPSTREAM_BASE",
        "CONTROLLED_ROOT_SEMANTIC_AUTHORITY",
        "CONTROLLED_ROOT_INTENT",
        "CONTROLLED_ROOT_APPEND",
        "CONTROLLED_CHILD_SEMANTIC_AUTHORITY",
        "CONTROLLED_CHILD_INTENT",
        "CONTROLLED_CHILD_APPEND",
        "CONTROLLED_PROMOTION_SEMANTIC_AUTHORITY",
        "CONTROLLED_PROMOTION_INTENT",
        "CONTROLLED_PROMOTION_APPEND",
        "SIGNED_CONTROL_JOURNAL_HEAD",
        "SIGNED_APPEND_RECEIPT",
        "CONTROLLED_COMPLETE_SUPPORT_FREEZE",
        "OPEN_CONTROLLED_PREFIX_VERIFICATION",
        "SIGNED_CONTROL_CLOSURE",
        "SIGNED_CONTROL_RECONCILIATION",
        "CONTROLLED_JOURNAL_CLOSURE",
    )
    ids = tuple(_id(f"synthetic-{role}") for role in roles)
    dependencies = (
        (),
        (ids[0],),
        (ids[1],),
        (ids[2],),
        (ids[0],),
        (ids[4],),
        (ids[5],),
        (ids[0],),
        (ids[7],),
        (ids[8],),
        (ids[0],),
        (ids[6],),
        (ids[6],),
        (ids[11], ids[12]),
        (ids[3], ids[6], ids[9], ids[13]),
        (ids[14],),
        (ids[15],),
    )
    return tuple(
        SimpleNamespace(
            record_id=ids[index],
            index=index,
            record_index=index,
            role=role,
            semantic_artifact_id=_id(f"semantic-{role}"),
            dependency_record_ids=tuple(sorted(dependencies[index])),
            canonical_artifact_bytes=b"{}",
        )
        for index, role in enumerate(roles)
    )


def _synthetic_present_role_closures():
    records = _synthetic_records()
    control_ids = frozenset(
        item.record_id
        for item in records
        if item.role in authority.CONTROL_ROLE_ORDER
    )
    nodes = authority._iterative_control_dependency_nodes(  # noqa: SLF001
        records=records,
        upstream_public_record_ids=frozenset({records[0].record_id}),
        structurally_replayed_control_record_ids=control_ids,
        root_semantic_authority_record_ids=frozenset(
            {records[1].record_id}
        ),
    )
    dag = authority.V075PortableControlDependencyDAGV2(
        authority._DAG_ISSUER,  # noqa: SLF001
        _id("synthetic-bundle"),
        _id("synthetic-m1a"),
        _id("synthetic-typed-graph"),
        nodes,
    )
    nodes_by_id = {item.record_id: item for item in nodes}
    records_by_id = {item.record_id: item for item in records}
    attestations = []
    for record in records[1:]:
        node = nodes_by_id[record.record_id]
        resolved = tuple(
            item
            for item in record.dependency_record_ids
            if nodes_by_id[item].semantically_resolved
        )
        unresolved = tuple(
            item
            for item in record.dependency_record_ids
            if not nodes_by_id[item].semantically_resolved
        )
        attestations.append(
            authority.V075PortableControlRecordAttestationV2(
                authority._ATTESTATION_ISSUER,  # noqa: SLF001
                _id("synthetic-bundle"),
                _id("synthetic-typed-graph"),
                dag.dag_id,
                record.record_id,
                record.index,
                record.role,
                record.semantic_artifact_id,
                hashlib.sha256(record.canonical_artifact_bytes).hexdigest(),
                len(record.canonical_artifact_bytes),
                record.dependency_record_ids,
                resolved,
                unresolved,
                tuple(
                    sorted({records_by_id[item].role for item in unresolved})
                ),
                node.resolver_kind,
                (
                    authority.V075PortableControlRoleClosureStatusV2
                    .FULL_PUBLIC
                    if node.semantically_resolved
                    else (
                        authority.V075PortableControlRoleClosureStatusV2
                        .STRUCTURAL_ONLY_TRANSITIVE_UNRESOLVED
                    )
                ),
            )
        )
    closures = authority._build_role_closures(  # noqa: SLF001
        bundle_id=_id("synthetic-bundle"),
        typed_graph_id=_id("synthetic-typed-graph"),
        dependency_dag_id=dag.dag_id,
        records=records,
        attestations=tuple(attestations),
    )
    return records, nodes, dag, tuple(attestations), closures


def test_all_16_present_roles_preserve_opaque_child_promotion_propagation(
) -> None:
    _records, nodes, _dag, attestations, closures = (
        _synthetic_present_role_closures()
    )
    by_role = {item.role: item for item in nodes}
    for role in (
        "CONTROLLED_CHILD_SEMANTIC_AUTHORITY",
        "CONTROLLED_PROMOTION_SEMANTIC_AUTHORITY",
    ):
        assert by_role[role].producer_structure_replayed is True
        assert by_role[role].semantically_resolved is False
        assert by_role[role].resolver_kind.value == (
            "M1B_OPAQUE_SEMANTIC_AUTHORITY"
        )
    for role in (
        "CONTROLLED_CHILD_INTENT",
        "CONTROLLED_CHILD_APPEND",
        "CONTROLLED_PROMOTION_INTENT",
        "CONTROLLED_PROMOTION_APPEND",
        "SIGNED_CONTROL_CLOSURE",
    ):
        assert by_role[role].producer_structure_replayed is True
        assert by_role[role].semantically_resolved is False
    closure_by_role = {item.role: item for item in closures}
    assert set(closure_by_role) == set(authority.CONTROL_ROLE_ORDER)
    assert all(item.present_in_occurrence for item in closures)
    assert all(
        item.status
        is (
            authority.V075PortableControlRoleClosureStatusV2.FULL_PUBLIC
            if item.role
            in {
                *authority.ROOT_CONTROL_ROLE_ORDER,
                "SIGNED_CONTROL_JOURNAL_HEAD",
            }
            else (
                authority.V075PortableControlRoleClosureStatusV2
                .STRUCTURAL_ONLY_TRANSITIVE_UNRESOLVED
            )
        )
        for item in closures
    )
    assert len(attestations) == len(authority.CONTROL_ROLE_ORDER)
    assert not all(
        item.status
        is authority.V075PortableControlRoleClosureStatusV2.FULL_PUBLIC
        for item in closures
    )


def test_opaque_authority_cannot_be_upgraded_as_root() -> None:
    records = _synthetic_records()
    control_ids = frozenset(
        item.record_id
        for item in records
        if item.role in authority.CONTROL_ROLE_ORDER
    )
    child = next(
        item
        for item in records
        if item.role == "CONTROLLED_CHILD_SEMANTIC_AUTHORITY"
    )
    with pytest.raises(
        authority.V075PortableSignedControlGraphV2InvariantViolation,
        match="non-root",
    ):
        authority._iterative_control_dependency_nodes(  # noqa: SLF001
            records=records,
            upstream_public_record_ids=frozenset(
                {records[0].record_id}
            ),
            structurally_replayed_control_record_ids=control_ids,
            root_semantic_authority_record_ids=frozenset(
                {child.record_id}
            ),
        )


@pytest.mark.parametrize("attack", ("wrong_row", "template"))
def test_root_semantic_binding_rejects_signed_wrong_row_or_template(
    real_raw_m0_bundle,
    real_k7_m1b,
    attack,
) -> None:
    graph = real_k7_m1b.typed_graph
    root_appends = tuple(
        item
        for item in graph.appends
        if item.intent.semantic_authority.role
        is (
            authority.control.V075ControlledBatchSemanticAuthorityRoleV2
            .INITIAL_SCHEDULE_ROW_INTENT
        )
    )
    root_records = tuple(
        item
        for item in real_raw_m0_bundle["bundle"].records
        if item.role == "CONTROLLED_ROOT_SEMANTIC_AUTHORITY"
    )
    target_append = root_appends[0]
    if attack == "wrong_row":
        target = target_append.intent
        attribute = "stream_identity"
        original = target.stream_identity
        replacement = next(
            item.intent.stream_identity
            for item in root_appends[1:]
            if (
                item.intent.stream_identity.row_binding
                != original.row_binding
                and item.intent.stream_identity.lane is original.lane
            )
        )
        expected_message = "row/stage/lane"
    else:
        target = target_append.intent.semantic_authority
        attribute = "semantic_artifact_id"
        original = target.semantic_artifact_id
        replacement = next(
            item.intent_id
            for item in graph.m1a_result.typed_graph.m0_result.typed_graph.schedule.intents
            if item.kind
            is (
                authority.acquisition.V075InitialIntentKindV2
                .SUPPORT_PROMOTION_TEMPLATE
            )
        )
        expected_message = "ordered ROOT"
    object.__setattr__(target, attribute, replacement)
    try:
        with pytest.raises(
            authority.V075PortableSignedControlGraphV2InvariantViolation,
            match=expected_message,
        ):
            authority._validate_root_semantic_authority_bindings(  # noqa: SLF001
                authority_records=root_records,
                appends=graph.appends,
                m1a_result=graph.m1a_result,
            )
    finally:
        object.__setattr__(target, attribute, original)
    authority._validate_root_semantic_authority_bindings(  # noqa: SLF001
        authority_records=root_records,
        appends=graph.appends,
        m1a_result=graph.m1a_result,
    )


def test_dependency_resolution_is_iterative_at_full_chain_cap() -> None:
    count = 4096
    ids = tuple(_id(f"cap-{index}") for index in range(count))
    records = tuple(
        SimpleNamespace(
            record_id=ids[index],
            index=index,
            role=(
                "UPSTREAM_BASE"
                if index == 0
                else "SIGNED_CONTROL_JOURNAL_HEAD"
            ),
            dependency_record_ids=(
                () if index == 0 else (ids[index - 1],)
            ),
        )
        for index in range(count)
    )
    nodes = authority._iterative_control_dependency_nodes(  # noqa: SLF001
        records=records,
        upstream_public_record_ids=frozenset({ids[0]}),
        structurally_replayed_control_record_ids=frozenset(ids[1:]),
        root_semantic_authority_record_ids=frozenset(),
    )
    assert len(nodes) == count
    assert nodes[-1].semantically_resolved is True
    assert sum(
        len(item.direct_dependency_record_ids) for item in nodes
    ) == count - 1


@pytest.mark.parametrize("attack", ("signature", "head_recurrence"))
def test_typed_graph_rejects_signature_and_head_recurrence_mutation(
    real_k7_m1b,
    attack,
) -> None:
    head = real_k7_m1b.typed_graph.heads[-1]
    if attack == "signature":
        attribute = "observer_signature_hex"
        original = head.observer_signature_hex
        replacement = "00" * (len(original) // 2)
    else:
        attribute = "total_accepted_draw_count"
        original = head.total_accepted_draw_count
        replacement = original + 1
    object.__setattr__(head, attribute, replacement)
    try:
        with pytest.raises(
            authority.V075PortableSignedControlGraphV2InvariantViolation
        ):
            real_k7_m1b.to_document()
    finally:
        object.__setattr__(head, attribute, original)
    assert getattr(head, attribute) == original


@pytest.mark.parametrize(
    "attack",
    ("binding_dependencies", "dag_node", "attestation", "role_closure", "result"),
)
def test_identity_chain_rejects_stale_mutations(
    real_k7_m1b,
    attack,
) -> None:
    if attack == "binding_dependencies":
        target = next(
            item
            for item in real_k7_m1b.typed_graph.record_bindings
            if item.dependency_record_ids
        )
        attribute = "dependency_record_ids"
        replacement = ()
        checker = real_k7_m1b.typed_graph._assert_current  # noqa: SLF001
    elif attack == "dag_node":
        target = next(
            item
            for item in real_k7_m1b.dependency_dag.nodes
            if item.role in authority.CONTROL_ROLE_ORDER
            and item.semantically_resolved
        )
        attribute = "semantically_resolved"
        replacement = False
        checker = real_k7_m1b.dependency_dag._assert_current  # noqa: SLF001
    elif attack == "attestation":
        target = real_k7_m1b.attestations[0]
        attribute = "semantic_artifact_id"
        replacement = _id("stale-attestation-semantic")
        checker = target.to_document
    elif attack == "role_closure":
        target = real_k7_m1b.role_closures[0]
        attribute = "record_ids"
        replacement = ()
        checker = target.to_document
    else:
        target = real_k7_m1b
        attribute = "_result_id"
        replacement = _id("stale-result")
        checker = real_k7_m1b.to_document
    original = getattr(target, attribute)
    object.__setattr__(target, attribute, replacement)
    try:
        with pytest.raises(
            authority.V075PortableSignedControlGraphV2InvariantViolation
        ):
            checker()
    finally:
        object.__setattr__(target, attribute, original)
    assert getattr(target, attribute) == original


def test_aggregate_recomputes_unresolved_roles_from_dag(
    monkeypatch,
) -> None:
    records, _nodes, dag, attestations, closures = (
        _synthetic_present_role_closures()
    )
    for record in records[1:]:
        record._assert_current = lambda: None
    m1a_result = SimpleNamespace(
        _result_id=_id("synthetic-m1a"),
        typed_graph=SimpleNamespace(
            record_bindings=(
                SimpleNamespace(
                    role=authority.m1a.M1A_VERIFICATION_ROLE,
                    record_id=_id("synthetic-private-verification"),
                ),
            )
        ),
    )
    typed_graph = object.__new__(
        authority.V075PortableSignedControlTypedGraphV2
    )
    for attribute, value in (
        ("bundle_id", _id("synthetic-bundle")),
        ("occurrence_id", _id("synthetic-occurrence")),
        ("public_context_closure_id", _id("synthetic-context")),
        ("m1a_result", m1a_result),
        ("record_bindings", records[1:]),
        ("_graph_id", _id("synthetic-typed-graph")),
    ):
        object.__setattr__(typed_graph, attribute, value)
    monkeypatch.setattr(
        authority.V075PortableSignedControlTypedGraphV2,
        "_assert_current",
        lambda _self: None,
    )

    aggregate = object.__new__(
        authority.V075PortableSignedControlGraphReplayV2
    )
    for attribute, value in (
        ("bundle_id", _id("synthetic-bundle")),
        ("occurrence_id", _id("synthetic-occurrence")),
        ("public_context_closure_id", _id("synthetic-context")),
        ("typed_graph", typed_graph),
        ("dependency_dag", dag),
        ("attestations", attestations),
        ("role_closures", closures),
        ("_result_id", _id("synthetic-result")),
    ):
        object.__setattr__(aggregate, attribute, value)
    aggregate._validate()  # noqa: SLF001

    target = next(
        item
        for item in attestations
        if item.unresolved_direct_dependency_record_ids
    )
    forged = authority.V075PortableControlRecordAttestationV2(
        authority._ATTESTATION_ISSUER,  # noqa: SLF001
        target.bundle_id,
        target.typed_graph_id,
        target.dependency_dag_id,
        target.record_id,
        target.record_index,
        target.role,
        target.semantic_artifact_id,
        target.canonical_artifact_sha256,
        target.canonical_artifact_byte_count,
        target.direct_dependency_record_ids,
        target.resolved_direct_dependency_record_ids,
        target.unresolved_direct_dependency_record_ids,
        ("SIGNED_CONTROL_JOURNAL_HEAD",),
        target.resolver_kind,
        target.status,
    )
    forged_attestations = tuple(
        forged if item.record_id == target.record_id else item
        for item in attestations
    )
    forged_closures = authority._build_role_closures(  # noqa: SLF001
        bundle_id=_id("synthetic-bundle"),
        typed_graph_id=_id("synthetic-typed-graph"),
        dependency_dag_id=dag.dag_id,
        records=records,
        attestations=forged_attestations,
    )
    object.__setattr__(aggregate, "attestations", forged_attestations)
    object.__setattr__(aggregate, "role_closures", forged_closures)
    with pytest.raises(
        authority.V075PortableSignedControlGraphV2InvariantViolation,
        match="graph/DAG reconstruction",
    ):
        aggregate._validate()  # noqa: SLF001


@pytest.mark.parametrize(
    ("component", "attribute"),
    (
        ("typed_graph", "_graph_id"),
        ("dependency_dag", "_dag_id"),
        ("attestation", "_attestation_id"),
        ("role_closure", "_closure_id"),
    ),
)
def test_cached_component_ids_reject_direct_stale_parameter_attack(
    real_k7_m1b,
    component,
    attribute,
) -> None:
    if component == "attestation":
        target = real_k7_m1b.attestations[0]
        checker = target.to_document
    elif component == "role_closure":
        target = real_k7_m1b.role_closures[0]
        checker = target.to_document
    else:
        target = getattr(real_k7_m1b, component)
        checker = target._assert_current  # noqa: SLF001
    original = getattr(target, attribute)
    object.__setattr__(target, attribute, _id(f"stale-{component}-cache"))
    try:
        with pytest.raises(
            authority.V075PortableSignedControlGraphV2InvariantViolation,
            match="identity is stale",
        ):
            checker()
    finally:
        object.__setattr__(target, attribute, original)
    checker()


def test_raw_bundle_attack_fails_before_control_reconstruction(
    real_raw_m0_bundle,
) -> None:
    raw = bytearray(real_raw_m0_bundle["bundle"].canonical_bytes)
    raw[-2] = ord("0") if raw[-2] != ord("0") else ord("1")
    with pytest.raises(
        authority.V075PortableSignedControlGraphV2InvariantViolation,
        match="portable bundle failed raw replay",
    ):
        authority.replay_v075_portable_signed_control_graph_v2(
            repository_root=PROJECT_ROOT,
            portable_bundle_bytes=bytes(raw),
            public_context_closure_bytes=(
                real_raw_m0_bundle["closure"].canonical_bytes
            ),
        )


def test_m1b_locks_and_production_boundary_remain_closed(
    real_k7_document,
) -> None:
    document = real_k7_document
    for key in (
        "source_authority_complete",
        "code_provenance_complete",
        "portable_semantic_registry_complete",
        "observer_opened",
        "fresh_heldout_accessed",
        "official_execution_allowed",
        "production_authorizing",
        "scientific_endpoint_credit_allowed",
        "plan_certificate",
        "infeasibility_certificate",
        "private_material_serialized",
    ):
        assert document[key] is False
    assert document["same_implementation_control_replay_used"] is True
    assert document["independent_control_verifier_provided"] is False
    assert document["opaque_semantic_authority_upgraded"] is False
    assert authority.OFFICIAL_EXECUTION_ALLOWED is False
    assert authority.PRODUCTION_AUTHORIZING is False
    assert authority.SOURCE_AUTHORITY_COMPLETE is False
    assert authority.CODE_PROVENANCE_COMPLETE is False
    assert authority.PORTABLE_SEMANTIC_REGISTRY_COMPLETE is False
    assert authority.FRESH_HELDOUT_ACCESS_ALLOWED is False
    assert authority.PRIVATE_INPUT_CHANNELS_ALLOWED is False
    with pytest.raises(
        authority.V075PortableSignedControlGraphProductionV2NotReady
    ):
        authority.open_v075_production_from_portable_signed_control_graph_v2()
