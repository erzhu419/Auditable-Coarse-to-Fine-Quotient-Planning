from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
import ast
import hashlib
import inspect
from pathlib import Path
from types import SimpleNamespace

import pytest

from acfqp.phase3e_ids import canonical_json_bytes
from acfqp import v075_portable_construction_lifecycle_authority_v2 as authority


def _id(label: str) -> str:
    return hashlib.sha256(
        b"acfqp:v075-construction-lifecycle-test:v2\x00"
        + label.encode()
    ).hexdigest()


@dataclass(frozen=True)
class _UpstreamNode:
    record_id: str
    record_index: int
    role: str
    direct_dependency_record_ids: tuple[str, ...]
    local_semantic_authority_resolved: bool
    semantically_resolved: bool
    unresolved_frontier_record_ids: tuple[str, ...]
    dependency_depth: int

    def _assert_current(self) -> None:
        return None


def _node(
    label: str,
    index: int,
    role: str,
    dependencies: tuple[str, ...] = (),
    *,
    local: bool = True,
    resolved: bool = True,
    frontier: tuple[str, ...] = (),
    depth: int | None = None,
) -> _UpstreamNode:
    return _UpstreamNode(
        _id(label),
        index,
        role,
        tuple(sorted(dependencies)),
        local,
        resolved,
        tuple(sorted(frontier)),
        index + 1 if depth is None else depth,
    )


def test_contract_scope_and_all_locks_remain_closed() -> None:
    assert authority.PROPOSED_CONTRACT_VERSION == "1.74.0"
    assert authority.ROLE_ORDER == (
        "LIFECYCLE_SUPPORT_EVIDENCE",
        "LIFECYCLE_SUPPORT_FREEZE",
        "LIFECYCLE_EVENT",
        "CONSTRUCTION_LIFECYCLE",
        "CONSTRUCTION_LIFECYCLE_VERIFICATION",
    )
    assert authority.TERMINAL_CLASS == "ATTEMPT_CLOSURE_NONCERTIFICATE"
    for name in (
        "OFFICIAL_EXECUTION_ALLOWED",
        "PRODUCTION_AUTHORIZING",
        "SCIENTIFIC_ENDPOINT_CREDIT_ALLOWED",
        "SOURCE_AUTHORITY_COMPLETE",
        "CODE_PROVENANCE_COMPLETE",
        "PORTABLE_SEMANTIC_REGISTRY_COMPLETE",
        "FRESH_HELDOUT_ACCESS_ALLOWED",
        "PRIVATE_INPUT_CHANNELS_ALLOWED",
        "PRIVATE_REPLAY_PERFORMED",
        "B3_INPUT_ALLOWED",
        "K7_INPUT_ALLOWED",
        "M1A_PRIVATE_VERIFICATION_CLAIM_CONSUMED",
        "PLAN_CERTIFICATE_ISSUANCE_ALLOWED",
        "INFEASIBILITY_CERTIFICATE_ISSUANCE_ALLOWED",
    ):
        assert getattr(authority, name) is False


def test_entry_is_raw_only_and_hardened_173_runs_first(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert tuple(
        inspect.signature(
            authority.replay_v075_portable_construction_lifecycle_v2
        ).parameters
    ) == (
        "repository_root",
        "portable_bundle_bytes",
        "public_context_closure_bytes",
    )
    calls: list[str] = []

    def stop_at_upstream(**_kwargs):
        calls.append("1.73")
        raise RuntimeError("sentinel")

    def forbidden_bundle(*_args, **_kwargs):
        calls.append("bundle")
        raise AssertionError("bundle verifier ran before hardened 1.73")

    monkeypatch.setattr(
        authority.m2_lineage,
        "replay_v075_portable_public_lineage_v2",
        stop_at_upstream,
    )
    monkeypatch.setattr(
        authority.portable,
        "verify_v075_portable_occurrence_evidence_bundle_bytes_v2",
        forbidden_bundle,
    )
    with pytest.raises(
        authority.V075PortableConstructionLifecycleV2InvariantViolation,
        match="hardened 1.73 replay failed",
    ):
        authority.replay_v075_portable_construction_lifecycle_v2(
            repository_root=Path("."),
            portable_bundle_bytes=b"bundle",
            public_context_closure_bytes=b"context",
        )
    assert calls == ["1.73"]


def test_synthetic_full_entry_wiring_and_lifecycle_byte_mutation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    trace: list[str] = []
    seen: dict[str, object] = {}
    bundle_id = _id("entry-bundle")
    occurrence_id = _id("entry-occurrence")
    context_id = _id("entry-context")
    repository_root = Path(".")
    bundle_bytes = b"synthetic-bundle"
    context_bytes = b"synthetic-context"
    upstream_nodes = ("upstream-node",)
    upstream = SimpleNamespace(
        bundle_id=bundle_id,
        occurrence_id=occurrence_id,
        public_context_closure_id=context_id,
        dependency_dag=SimpleNamespace(nodes=upstream_nodes),
    )
    bindings = tuple(
        SimpleNamespace(
            role=role,
            record_id=_id(f"entry-{role}-record"),
            canonical_artifact_bytes=(
                b"lifecycle-raw"
                if role == "CONSTRUCTION_LIFECYCLE"
                else role.encode()
            ),
        )
        for role in authority.ROLE_ORDER
    )

    def replay_upstream(**kwargs):
        trace.append("1.73")
        seen["upstream"] = kwargs
        return upstream

    def verify_bundle(raw):
        trace.append("bundle")
        seen["bundle_raw"] = raw
        current = []
        for binding in bindings:
            if (
                binding.role == "CONSTRUCTION_LIFECYCLE"
                and raw == b"mutated-bundle"
            ):
                binding = SimpleNamespace(
                    **{
                        **binding.__dict__,
                        "canonical_artifact_bytes": b"mutated-lifecycle",
                    }
                )
            current.append(SimpleNamespace(role=binding.role, binding=binding))
        return SimpleNamespace(
            bundle_id=bundle_id,
            occurrence_id=occurrence_id,
            records=tuple(current),
        )

    lifecycle_closure = SimpleNamespace()
    lifecycle_verification = SimpleNamespace()

    def replay_lifecycle(**kwargs):
        trace.append("lifecycle")
        seen["lifecycle"] = kwargs
        lifecycle_bytes = kwargs["lifecycle_bytes"]
        if lifecycle_bytes != b"lifecycle-raw":
            raise authority.V075PortableConstructionLifecycleV2InvariantViolation(
                "mutated lifecycle bytes"
            )
        return lifecycle_closure, lifecycle_verification

    typed_graph = SimpleNamespace(_graph_id=_id("entry-typed-graph"))
    dag = SimpleNamespace(_dag_id=_id("entry-dag"))
    graph = object()
    support_sources = ("source-binding",)
    source_edges = {"evidence": ("source",)}
    nodes = ("node",)
    attestations = ("attestation",)
    role_closures = ("closure",)
    final = SimpleNamespace(result_id=_id("entry-result"))

    def bind(record):
        trace.append("binding")
        return record.binding

    def get_graph(*args, **kwargs):
        trace.append("m1a")
        seen["m1a"] = (args, kwargs)
        return graph

    def derive_sources(**kwargs):
        trace.append("sources")
        seen["sources"] = kwargs
        return support_sources

    def build_typed_graph(*args):
        trace.append("typed_graph")
        seen["typed_graph"] = args
        return typed_graph

    def add_source_edges(sources):
        trace.append("source_edges")
        seen["source_edges"] = sources
        return source_edges

    def build_nodes(**kwargs):
        trace.append("nodes")
        seen["nodes"] = kwargs
        return nodes

    def build_dag(*args):
        trace.append("dag")
        seen["dag"] = args
        return dag

    def build_attestations(**kwargs):
        trace.append("attestations")
        seen["attestations"] = kwargs
        return attestations

    def build_closures(**kwargs):
        trace.append("closures")
        seen["closures"] = kwargs
        return role_closures

    def build_result(*args):
        trace.append("result")
        seen["result"] = args
        return final

    monkeypatch.setattr(
        authority.m2_lineage,
        "replay_v075_portable_public_lineage_v2",
        replay_upstream,
    )
    monkeypatch.setattr(
        authority.portable,
        "verify_v075_portable_occurrence_evidence_bundle_bytes_v2",
        verify_bundle,
    )
    monkeypatch.setattr(
        authority,
        "_binding_from_record",
        bind,
    )
    monkeypatch.setattr(authority, "_replay_lifecycle", replay_lifecycle)
    monkeypatch.setattr(authority, "_m1a_graph", get_graph)
    monkeypatch.setattr(
        authority,
        "_derive_support_source_bindings",
        derive_sources,
    )
    monkeypatch.setattr(
        authority,
        "V075PortableConstructionLifecycleTypedGraphV2",
        build_typed_graph,
    )
    monkeypatch.setattr(
        authority,
        "_additional_source_edges",
        add_source_edges,
    )
    monkeypatch.setattr(
        authority,
        "_iterative_construction_lifecycle_dependency_nodes",
        build_nodes,
    )
    monkeypatch.setattr(
        authority,
        "V075PortableConstructionLifecycleDependencyDAGV2",
        build_dag,
    )
    monkeypatch.setattr(
        authority,
        "_build_attestations",
        build_attestations,
    )
    monkeypatch.setattr(
        authority,
        "_build_role_closures",
        build_closures,
    )
    monkeypatch.setattr(
        authority,
        "V075PortableConstructionLifecycleReplayV2",
        build_result,
    )

    result = authority.replay_v075_portable_construction_lifecycle_v2(
        repository_root=repository_root,
        portable_bundle_bytes=bundle_bytes,
        public_context_closure_bytes=context_bytes,
    )
    assert result is final
    assert trace == [
        "1.73",
        "bundle",
        *(["binding"] * len(authority.ROLE_ORDER)),
        "lifecycle",
        "m1a",
        "sources",
        "typed_graph",
        "source_edges",
        "nodes",
        "dag",
        "attestations",
        "closures",
        "result",
    ]
    assert seen["upstream"] == {
        "repository_root": repository_root,
        "portable_bundle_bytes": bundle_bytes,
        "public_context_closure_bytes": context_bytes,
    }
    assert seen["bundle_raw"] == bundle_bytes
    assert seen["lifecycle"] == {
        "upstream": upstream,
        "lifecycle_bytes": b"lifecycle-raw",
        "_upstream_already_current": True,
    }
    assert seen["m1a"] == (
        (upstream,),
        {"_upstream_already_current": True},
    )
    assert seen["sources"] == {
        "graph": graph,
        "closure": lifecycle_closure,
        "target_bindings": bindings,
    }
    assert seen["typed_graph"] == (
        authority._TYPED_GRAPH_ISSUER,  # noqa: SLF001
        bundle_id,
        context_id,
        occurrence_id,
        upstream,
        lifecycle_closure,
        lifecycle_verification,
        support_sources,
        bindings,
    )
    assert seen["source_edges"] is support_sources
    local_ids = tuple(sorted(item.record_id for item in bindings))
    assert seen["nodes"] == {
        "upstream_nodes": upstream_nodes,
        "locally_replayed_record_ids": frozenset(local_ids),
        "authority_local_source_edges": source_edges,
    }
    assert seen["dag"] == (
        authority._DAG_ISSUER,  # noqa: SLF001
        bundle_id,
        upstream,
        typed_graph._graph_id,
        support_sources,
        local_ids,
        nodes,
    )
    assert seen["attestations"] == {
        "bundle_id": bundle_id,
        "typed_graph_id": typed_graph._graph_id,
        "dag": dag,
        "bindings": bindings,
    }
    assert seen["closures"] == {
        "bundle_id": bundle_id,
        "typed_graph_id": typed_graph._graph_id,
        "dependency_dag_id": dag._dag_id,
        "bindings": bindings,
        "attestations": attestations,
    }
    assert seen["result"] == (
        authority._RESULT_ISSUER,  # noqa: SLF001
        bundle_id,
        occurrence_id,
        context_id,
        typed_graph,
        dag,
        attestations,
        role_closures,
    )

    trace.clear()
    seen.clear()
    with pytest.raises(
        authority.V075PortableConstructionLifecycleV2InvariantViolation,
        match="mutated lifecycle bytes",
    ):
        authority.replay_v075_portable_construction_lifecycle_v2(
            repository_root=Path("."),
            portable_bundle_bytes=b"mutated-bundle",
            public_context_closure_bytes=context_bytes,
        )
    assert trace == [
        "1.73",
        "bundle",
        *(["binding"] * len(authority.ROLE_ORDER)),
        "lifecycle",
    ]


def test_source_has_no_private_b3_production_or_freeze_authority() -> None:
    source = inspect.getsource(authority)
    tree = ast.parse(source)
    called_attributes = {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
    }
    assert (
        "freeze_v075_construction_batch_occurrence_lifecycle_v2"
        not in called_attributes
    )
    assert (
        "verify_v075_production_batch_occurrence_lifecycle_v2"
        not in called_attributes
    )
    assert not any(
        isinstance(node, (ast.Import, ast.ImportFrom))
        and "b3" in str(getattr(node, "module", "")).lower()
        for node in ast.walk(tree)
    )
    assert not any(
        isinstance(node, ast.arg)
        and node.arg in {"private_salt", "private_environment"}
        for node in ast.walk(tree)
    )


def _support_fixture():
    occurrence_id = _id("occurrence")
    evidence_id = _id("evidence")
    request_id = _id("request")
    batch_id = _id("batch")
    outcome_id = _id("outcome")
    request_raw = canonical_json_bytes({"request_id": request_id})
    batch_raw = canonical_json_bytes({"batch_id": batch_id})
    outcome_document = {
        "outcome_id": outcome_id,
        "count": 7,
        "reward_sum": {"numerator": 5, "denominator": 3},
    }
    outcome_raw = canonical_json_bytes(outcome_document)
    request_record = SimpleNamespace(
        role="SIGNED_BATCH_REQUEST",
        semantic_artifact_id=request_id,
        canonical_artifact_bytes=request_raw,
        record_id=_id("request-record"),
    )
    batch_record = SimpleNamespace(
        role="SIGNED_OBSERVATION_BATCH",
        semantic_artifact_id=batch_id,
        canonical_artifact_bytes=batch_raw,
        record_id=_id("batch-record"),
    )
    outcome_record = SimpleNamespace(
        role="SIGNED_BATCH_OUTCOME",
        semantic_artifact_id=outcome_id,
        canonical_artifact_bytes=outcome_raw,
        record_id=_id("outcome-record"),
    )
    outcome = SimpleNamespace(
        outcome_id=outcome_id,
        count=7,
        reward_sum=Fraction(5, 3),
        to_document=lambda: outcome_document,
    )
    batch = SimpleNamespace(
        batch_id=batch_id,
        request=SimpleNamespace(request_id=request_id),
        outcomes=(outcome,),
    )
    source_document = {
        "schema": "acfqp.v075_batch_support_source_aggregate.v2",
        "discovery_batch_id": batch_id,
        "discovery_request_id": request_id,
        "discovery_outcome_id": outcome_id,
        "discovery_outcome_count": 7,
        "discovery_reward_sum": {"numerator": 5, "denominator": 3},
    }
    source = SimpleNamespace(
        discovery_batch_id=batch_id,
        discovery_request_id=request_id,
        discovery_outcome_id=outcome_id,
        discovery_outcome_count=7,
        discovery_reward_sum=Fraction(5, 3),
        to_document=lambda: source_document,
    )
    evidence = SimpleNamespace(
        evidence_id=evidence_id,
        occurrence_id=occurrence_id,
        source_aggregates=(source,),
    )
    graph = SimpleNamespace(
        record_bindings=(
            request_record,
            batch_record,
            outcome_record,
        ),
        batches=(batch,),
    )
    closure = SimpleNamespace(support_evidence=(evidence,))
    target = SimpleNamespace(
        role="LIFECYCLE_SUPPORT_EVIDENCE",
        semantic_artifact_id=evidence_id,
        record_id=_id("evidence-record"),
    )
    return graph, closure, (target,)


def test_support_sources_bind_exact_request_batch_and_derived_outcome() -> None:
    graph, closure, targets = _support_fixture()
    bindings = authority._derive_support_source_bindings(  # noqa: SLF001
        graph=graph,
        closure=closure,
        target_bindings=targets,
    )
    assert len(bindings) == 1
    binding = bindings[0]
    assert binding.discovery_outcome_count == 7
    assert (
        binding.discovery_reward_numerator,
        binding.discovery_reward_denominator,
    ) == (5, 3)
    assert binding.semantic_source_record_ids == tuple(
        sorted(
            (
                _id("request-record"),
                _id("batch-record"),
                _id("outcome-record"),
            )
        )
    )


@pytest.mark.parametrize("attack", ("omit", "transplant", "count", "reward"))
def test_support_source_omission_transplant_count_and_reward_fail(
    attack: str,
) -> None:
    graph, closure, targets = _support_fixture()
    if attack == "omit":
        graph.record_bindings = graph.record_bindings[:-1]
    elif attack == "transplant":
        source = closure.support_evidence[0].source_aggregates[0]
        source.discovery_request_id = _id("foreign-request")
    elif attack == "count":
        closure.support_evidence[0].source_aggregates[
            0
        ].discovery_outcome_count = 8
    else:
        closure.support_evidence[0].source_aggregates[
            0
        ].discovery_reward_sum = Fraction(2)
    with pytest.raises(
        authority.V075PortableConstructionLifecycleV2InvariantViolation
    ):
        authority._derive_support_source_bindings(  # noqa: SLF001
            graph=graph,
            closure=closure,
            target_bindings=targets,
        )


def test_support_source_reorder_and_stale_binding_fail() -> None:
    graph, closure, targets = _support_fixture()
    first = authority._derive_support_source_bindings(  # noqa: SLF001
        graph=graph,
        closure=closure,
        target_bindings=targets,
    )[0]
    second = authority.V075LifecycleSupportSourceBindingV2(  # noqa: SLF001
        authority._SOURCE_BINDING_ISSUER,
        first.support_evidence_record_id,
        first.support_evidence_id,
        1,
        first.discovery_batch_id,
        first.discovery_request_id,
        first.discovery_outcome_id,
        first.discovery_outcome_count,
        first.discovery_reward_numerator,
        first.discovery_reward_denominator,
        _id("request-record-2"),
        _id("batch-record-2"),
        _id("outcome-record-2"),
        first.signed_request_sha256,
        first.signed_batch_sha256,
        first.signed_outcome_sha256,
        first.source_aggregate_sha256,
    )
    with pytest.raises(
        authority.V075PortableConstructionLifecycleV2InvariantViolation,
        match="reordered",
    ):
        authority._assert_exact_support_source_bindings(  # noqa: SLF001
            claimed=(second, first),
            expected=(first, second),
        )
    object.__setattr__(first, "discovery_outcome_count", 8)
    with pytest.raises(
        authority.V075PortableConstructionLifecycleV2InvariantViolation,
        match="stale",
    ):
        first._assert_current()  # noqa: SLF001


def _lifecycle_nodes() -> tuple[
    tuple[_UpstreamNode, ...],
    dict[str, str],
]:
    root = _node("root", 0, "OCCURRENCE_IDENTITY")
    evidence = _node(
        "evidence",
        1,
        "LIFECYCLE_SUPPORT_EVIDENCE",
        (root.record_id,),
        local=False,
        resolved=False,
        frontier=(_id("evidence"),),
    )
    request = _node("request", 2, "SIGNED_BATCH_REQUEST")
    batch = _node(
        "batch",
        3,
        "SIGNED_OBSERVATION_BATCH",
        (request.record_id,),
    )
    outcome = _node(
        "outcome",
        4,
        "SIGNED_BATCH_OUTCOME",
        (batch.record_id,),
    )
    private = _node(
        "private",
        5,
        "SIGNED_BATCH_JOURNAL_CLOSURE_VERIFICATION",
        local=False,
        resolved=False,
        frontier=(_id("private"),),
    )
    lineage = _node(
        "lineage",
        6,
        "CONSTRUCTION_LINEAGE",
        (private.record_id,),
        local=True,
        resolved=False,
        frontier=(private.record_id,),
    )
    freeze = _node(
        "freeze",
        7,
        "LIFECYCLE_SUPPORT_FREEZE",
        (evidence.record_id,),
        local=False,
        resolved=False,
        frontier=(_id("freeze"),),
    )
    event = _node(
        "event",
        8,
        "LIFECYCLE_EVENT",
        (freeze.record_id,),
        local=False,
        resolved=False,
        frontier=(_id("event"),),
    )
    closure = _node(
        "closure",
        9,
        "CONSTRUCTION_LIFECYCLE",
        (event.record_id, lineage.record_id),
        local=False,
        resolved=False,
        frontier=(_id("closure"),),
    )
    verification = _node(
        "verification",
        10,
        "CONSTRUCTION_LIFECYCLE_VERIFICATION",
        (closure.record_id, lineage.record_id),
        local=False,
        resolved=False,
        frontier=(_id("verification"),),
    )
    names = {
        item.role: item.record_id
        for item in (
            evidence,
            request,
            batch,
            outcome,
            private,
            lineage,
            freeze,
            event,
            closure,
            verification,
        )
    }
    return (
        (
            root,
            evidence,
            request,
            batch,
            outcome,
            private,
            lineage,
            freeze,
            event,
            closure,
            verification,
        ),
        names,
    )


def test_iterative_lifecycle_replay_has_three_full_and_two_structural_roles(
) -> None:
    nodes, names = _lifecycle_nodes()
    local = frozenset(
        names[role] for role in authority.ROLE_ORDER
    )
    source_edges = {
        names["LIFECYCLE_SUPPORT_EVIDENCE"]: tuple(
            sorted(
                (
                    names["SIGNED_BATCH_REQUEST"],
                    names["SIGNED_OBSERVATION_BATCH"],
                    names["SIGNED_BATCH_OUTCOME"],
                )
            )
        )
    }
    replayed = (
        authority._iterative_construction_lifecycle_dependency_nodes
    )(
        upstream_nodes=nodes,
        locally_replayed_record_ids=local,
        authority_local_source_edges=source_edges,
    )
    by_id = {item.record_id: item for item in replayed}
    for role in authority.ROLE_ORDER[:3]:
        assert by_id[names[role]].semantically_resolved is True
    for role in authority.ROLE_ORDER[3:]:
        assert by_id[names[role]].semantically_resolved is False
        assert by_id[names[role]].unresolved_frontier_record_ids == (
            names["SIGNED_BATCH_JOURNAL_CLOSURE_VERIFICATION"],
        )
    evidence = by_id[names["LIFECYCLE_SUPPORT_EVIDENCE"]]
    upstream_evidence = nodes[1]
    assert evidence.portable_declared_dependency_record_ids == (
        upstream_evidence.direct_dependency_record_ids
    )
    assert (
        evidence.authority_local_semantic_dependency_record_ids
        == source_edges[evidence.record_id]
    )


def test_missing_authority_local_edge_fails_while_portable_dag_is_valid(
) -> None:
    nodes, names = _lifecycle_nodes()
    with pytest.raises(
        authority.V075PortableConstructionLifecycleV2InvariantViolation,
        match="omitted",
    ):
        authority._iterative_construction_lifecycle_dependency_nodes(
            upstream_nodes=nodes,
            locally_replayed_record_ids=frozenset(
                names[role] for role in authority.ROLE_ORDER
            ),
            authority_local_source_edges={},
        )


def test_iterative_dependency_replay_scales_to_4096_depth() -> None:
    count = 4096
    identifiers = tuple(_id(f"deep-{index}") for index in range(count))
    nodes = tuple(
        _UpstreamNode(
            identifiers[index],
            index,
            (
                "LIFECYCLE_EVENT"
                if index == count - 1
                else "UPSTREAM_PUBLIC"
            ),
            (() if index == 0 else (identifiers[index - 1],)),
            index != count - 1,
            index != count - 1,
            (() if index != count - 1 else (identifiers[-1],)),
            index + 1,
        )
        for index in range(count)
    )
    replayed = (
        authority._iterative_construction_lifecycle_dependency_nodes
    )(
        upstream_nodes=nodes,
        locally_replayed_record_ids=frozenset({identifiers[-1]}),
        authority_local_source_edges={},
    )
    assert len(replayed) == count
    assert replayed[-1].dependency_depth == 4096
    assert replayed[-1].semantically_resolved is True


def test_construction_verification_is_explicitly_nonproduction() -> None:
    source = inspect.getsource(
        authority.V075PortableConstructionLifecycleTypedGraphV2._validate
    )
    assert "CONSTRUCTION_ONLY" in source
    assert "upstream_production_lineage_verification_id" in source
    assert "typed_public_streams_semantically_replayed" in source


def test_role_closure_preserves_exact_tri_state() -> None:
    status = authority.V075PortableConstructionLifecycleRoleStatusV2
    common = (
        authority._ROLE_CLOSURE_ISSUER,  # noqa: SLF001
        _id("bundle"),
        _id("graph"),
        _id("dag"),
    )
    absent = authority.V075PortableConstructionLifecycleRoleClosureV2(
        *common,
        "LIFECYCLE_EVENT",
        status.NOT_PRESENT_IN_OCCURRENCE,
        (),
        (),
        (),
        (),
        (),
    )
    full = authority.V075PortableConstructionLifecycleRoleClosureV2(
        *common,
        "LIFECYCLE_SUPPORT_EVIDENCE",
        status.FULL_PUBLIC,
        (_id("full-record"),),
        (_id("full-attestation"),),
        (),
        (),
        (),
    )
    structural = authority.V075PortableConstructionLifecycleRoleClosureV2(
        *common,
        "CONSTRUCTION_LIFECYCLE",
        status.STRUCTURAL_ONLY_TRANSITIVE_UNRESOLVED,
        (_id("structural-record"),),
        (_id("structural-attestation"),),
        (_id("structural-record"),),
        (_id("private-frontier"),),
        ("SIGNED_BATCH_JOURNAL_CLOSURE_VERIFICATION",),
    )
    assert absent.status is status.NOT_PRESENT_IN_OCCURRENCE
    assert full.status is status.FULL_PUBLIC
    assert structural.status is (
        status.STRUCTURAL_ONLY_TRANSITIVE_UNRESOLVED
    )
    with pytest.raises(
        authority.V075PortableConstructionLifecycleV2InvariantViolation,
        match="inconsistent",
    ):
        authority.V075PortableConstructionLifecycleRoleClosureV2(
            *common,
            "LIFECYCLE_EVENT",
            status.FULL_PUBLIC,
            (),
            (),
            (),
            (),
            (),
        )


def test_production_gate_is_closed() -> None:
    with pytest.raises(
        authority.V075PortableConstructionLifecycleProductionV2NotReady
    ):
        authority.open_v075_production_from_portable_construction_lifecycle_v2()
