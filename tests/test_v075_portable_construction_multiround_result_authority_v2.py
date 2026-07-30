from __future__ import annotations

import ast
from dataclasses import dataclass, fields
from enum import Enum
import hashlib
import inspect
import pickle
from types import SimpleNamespace

import pytest

from acfqp import (
    v075_portable_construction_multiround_result_authority_v2
    as authority,
)


def _id(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


class _Scope(str, Enum):
    FULL_PUBLIC = "FULL_PUBLIC"
    FULL_CONSTRUCTION_PRIVATE_REPLAY = (
        "FULL_CONSTRUCTION_PRIVATE_REPLAY"
    )
    FULL_CONSTRUCTION_COMPILER_REPLAY = (
        "FULL_CONSTRUCTION_COMPILER_REPLAY"
    )
    FULL_CONSTRUCTION_CLOSED_RECONCILIATION_REPLAY = (
        "FULL_CONSTRUCTION_CLOSED_RECONCILIATION_REPLAY"
    )
    FULL_CONSTRUCTION_TRANSITIVE = "FULL_CONSTRUCTION_TRANSITIVE"
    UNRESOLVED = "UNRESOLVED"


@dataclass(frozen=True)
class _UpstreamNode:
    record_id: str
    record_index: int
    role: str
    portable_declared_dependency_record_ids: tuple[str, ...]
    authority_local_semantic_dependency_record_ids: tuple[str, ...]
    effective_dependency_record_ids: tuple[str, ...]
    source_binding_id: str | None
    local_semantic_authority_resolved: bool
    semantically_resolved: bool
    authority_scope: _Scope


def _node(
    label: str,
    index: int,
    role: str,
    dependencies: tuple[str, ...] = (),
    *,
    local_dependencies: tuple[str, ...] = (),
    local: bool = True,
    resolved: bool = True,
    scope: _Scope = _Scope.FULL_PUBLIC,
) -> _UpstreamNode:
    portable_lane = tuple(sorted(dependencies))
    local_lane = tuple(sorted(local_dependencies))
    effective = tuple(sorted(set(portable_lane) | set(local_lane)))
    return _UpstreamNode(
        _id(label),
        index,
        role,
        portable_lane,
        local_lane,
        effective,
        _id(f"source:{label}") if local else None,
        local,
        resolved,
        scope,
    )


def _fixture() -> tuple[
    tuple[_UpstreamNode, ...],
    authority.V075ConstructionMultiroundResultSourceBindingV2,
]:
    source_nodes = {
        role: _node(f"source:{role}", index, role)
        for index, role in enumerate(authority.SOURCE_ROLE_ORDER)
    }
    planning_index = len(source_nodes)
    planning = _node(
        "planning",
        planning_index,
        "CONSTRUCTION_PLANNING_INPUT",
        (source_nodes["NUMERICAL_MODEL"].record_id,),
        scope=_Scope.FULL_CONSTRUCTION_COMPILER_REPLAY,
    )
    closed_original = source_nodes["CLOSED_RECONCILIATION"]
    source_nodes["CLOSED_RECONCILIATION"] = _node(
        "source:CLOSED_RECONCILIATION",
        closed_original.record_index,
        "CLOSED_RECONCILIATION",
        (planning.record_id,),
        scope=_Scope.FULL_CONSTRUCTION_CLOSED_RECONCILIATION_REPLAY,
    )
    target = _node(
        "target",
        planning_index + 1,
        "MULTIROUND_RESULT",
        (source_nodes["CLOSED_RECONCILIATION"].record_id,),
        local=False,
        resolved=False,
        scope=_Scope.UNRESOLVED,
    )
    nodes = tuple(
        sorted(
            (*source_nodes.values(), planning, target),
            key=lambda item: item.record_index,
        )
    )
    source_records = tuple(
        (role, source_nodes[role].record_id)
        for role in authority.SOURCE_ROLE_ORDER
    )
    binding = authority.V075ConstructionMultiroundResultSourceBindingV2(
        authority._SOURCE_BINDING_ISSUER,  # noqa: SLF001
        target_record_id=target.record_id,
        target_semantic_artifact_id=_id("target-semantic"),
        source_records=source_records,
        portable_bundle_id=_id("bundle"),
        occurrence_id=_id("occurrence"),
        public_context_closure_id=_id("context"),
        closed_replay_result_id=_id("closed-replay"),
        empty_role_registry_id=_id("empty-registry"),
        target_tape_namespace_id=_id("namespace"),
        schedule_id=_id("schedule"),
        schedule_verification_id=_id("schedule-verification"),
        controlled_root_prefix_verification_id=_id("root-prefix"),
        root_execution_id=_id("root-execution"),
        root_model_epoch_id=_id("root-epoch"),
        child_closure_id=_id("child-closure"),
        child_closure_verification_id=_id("child-verification"),
        final_numerical_model_id=_id("model"),
        final_proof_id=_id("proof"),
        closed_reconciliation_id=_id("reconciliation"),
        producer_artifact_sha256=_id("result-bytes"),
        producer_artifact_byte_count=8192,
    )
    return nodes, binding


def _replace_node(
    node: _UpstreamNode,
    **changes: object,
) -> _UpstreamNode:
    values = {
        item.name: getattr(node, item.name)
        for item in fields(type(node))
    }
    values.update(changes)
    return _UpstreamNode(**values)


def _binding_with(
    original: authority.V075ConstructionMultiroundResultSourceBindingV2,
    **changes: object,
) -> authority.V075ConstructionMultiroundResultSourceBindingV2:
    values = {
        item.name: getattr(original, item.name)
        for item in fields(type(original))
        if item.init
    }
    values.update(changes)
    return authority.V075ConstructionMultiroundResultSourceBindingV2(
        authority._SOURCE_BINDING_ISSUER,  # noqa: SLF001
        **values,
    )


def test_entry_owner_and_currentness_signatures_are_exact() -> None:
    raw = (
        "repository_root",
        "portable_bundle_bytes",
        "public_context_closure_bytes",
        "private_generation_seed",
        "private_salt",
    )
    assert tuple(
        inspect.signature(
            authority
            .replay_v075_portable_construction_multiround_result_v2
        ).parameters
    ) == raw
    assert tuple(
        inspect.signature(
            authority
            .V075PortableConstructionMultiroundResultReplayV2
            .assert_current
        ).parameters
    ) == ("self", *raw)
    assert tuple(
        inspect.signature(
            authority.owner.replay_v075_construction_root_execution_v2
        ).parameters
    ) == (
        "repository_root",
        "namespace",
        "schedule",
        "schedule_verification",
        "controlled_root_prefix",
        "root_execution_bytes",
    )
    assert tuple(
        inspect.signature(
            authority.owner.freeze_v075_construction_multiround_result_v2
        ).parameters
    ) == (
        "repository_root",
        "namespace",
        "schedule",
        "schedule_verification",
        "controlled_root_prefix",
        "root_execution_bytes",
        "root_epoch",
        "child_closure",
        "child_closure_verification",
        "final_epoch",
        "reconciliation",
        "child_execution_ledger",
        "child_execution_verification",
        "child_replanning_barrier",
        "child_replanning_barrier_verification",
        "promotion_decisions",
        "promotion_decision_verifications",
        "promotion_replanning_barriers",
        "promotion_replanning_barrier_verifications",
    )
    currentness = inspect.getsource(
        authority
        .V075PortableConstructionMultiroundResultReplayV2
        .assert_current
    )
    for name in raw:
        assert f"{name}={name}" in currentness


def test_raw_180_is_first_and_only_work_when_it_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    def raw_180(**_kwargs):
        calls.append("1.80")
        raise RuntimeError("private marker")

    def forbidden(*_args, **_kwargs):
        calls.append("forbidden")
        raise AssertionError("work ran before raw 1.80")

    monkeypatch.setattr(
        authority.closed_authority,
        "replay_v075_portable_construction_closed_reconciliation_v2",
        raw_180,
    )
    monkeypatch.setattr(authority, "_exact_chain", forbidden)
    monkeypatch.setattr(
        authority.portable,
        "verify_v075_portable_occurrence_evidence_bundle_bytes_v2",
        forbidden,
    )
    monkeypatch.setattr(
        authority.owner,
        "replay_v075_construction_root_execution_v2",
        forbidden,
    )
    monkeypatch.setattr(
        authority.owner,
        "freeze_v075_construction_multiround_result_v2",
        forbidden,
    )
    with pytest.raises(
        authority
        .V075PortableConstructionMultiroundResultV2InvariantViolation
    ) as captured:
        authority.replay_v075_portable_construction_multiround_result_v2(
            repository_root=".",
            portable_bundle_bytes=b"bundle",
            public_context_closure_bytes=b"context",
            private_generation_seed=b"seed",
            private_salt=b"salt",
        )
    assert calls == ["1.80"]
    assert str(captured.value) == authority._REPLAY_MISMATCH  # noqa: SLF001
    assert captured.value.__cause__ is None
    assert captured.value.__suppress_context__ is True
    assert "private marker" not in str(captured.value)


def test_only_public_owner_apis_produce_root_and_multiround_result() -> None:
    tree = ast.parse(inspect.getsource(authority))
    calls = {
        ast.unparse(item.func)
        for item in ast.walk(tree)
        if isinstance(item, ast.Call)
    }
    for expected in (
        (
            "closed_authority."
            "replay_v075_portable_construction_closed_reconciliation_v2"
        ),
        (
            "portable."
            "verify_v075_portable_occurrence_evidence_bundle_bytes_v2"
        ),
        "owner.replay_v075_construction_root_execution_v2",
        "owner.freeze_v075_construction_multiround_result_v2",
    ):
        assert expected in calls
    forbidden = (
        "owner.V075ObserverSignedRootExecutionV2",
        "owner.V075ObserverSignedMultiroundResultV2",
        "_ROOT_EXECUTION_ISSUER",
        "_MULTIROUND_RESULT_ISSUER",
        "_execute_initial_root_schedule",
        "_freeze_multiround_result",
        "compile_v075_construction_planning_input_v2",
        "plan_v075_construction_numerical_model_v2",
        "kernel",
        "J0",
        "K7",
        "B3",
    )
    for call in calls:
        assert not any(token in call for token in forbidden)


def test_owner_result_is_frozen_before_target_is_read() -> None:
    source = inspect.getsource(
        authority.replay_v075_portable_construction_multiround_result_v2
    )
    owner_freeze = source.index(
        "owner.freeze_v075_construction_multiround_result_v2"
    )
    target_read = source.index('role="MULTIROUND_RESULT"')
    assert owner_freeze < target_read
    freeze_call = next(
        item
        for item in ast.walk(ast.parse(source))
        if isinstance(item, ast.Call)
        and ast.unparse(item.func)
        == "owner.freeze_v075_construction_multiround_result_v2"
    )
    keywords = {item.arg: ast.unparse(item.value) for item in freeze_call.keywords}
    assert keywords["child_execution_ledger"] == "None"
    assert keywords["child_execution_verification"] == "None"
    assert keywords["child_replanning_barrier"] == "None"
    assert keywords["child_replanning_barrier_verification"] == "None"
    assert keywords["promotion_decisions"] == "()"
    assert keywords["promotion_decision_verifications"] == "()"
    assert keywords["promotion_replanning_barriers"] == "()"
    assert keywords["promotion_replanning_barrier_verifications"] == "()"


def test_namespace_comes_from_fresh_resolution_and_is_cross_checked() -> None:
    source = inspect.getsource(authority._exact_chain)  # noqa: SLF001
    assert (
        "private_result.typed_graph.public_context_resolution.namespace"
        in source
    )
    assert "controlled_namespace.target_tape_namespace_id" in source
    assert "namespace.canonical_bytes != controlled_namespace.canonical_bytes" in (
        source
    )


def test_root_only_empty_roles_are_fresh_bundle_facts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _Bundle:
        def __init__(self, records: tuple[object, ...]) -> None:
            self.bundle_id = _id("bundle")
            self.records = records

    monkeypatch.setattr(
        authority.portable,
        "V075PortableOccurrenceEvidenceBundleV2",
        _Bundle,
    )
    empty = _Bundle(())
    registry = authority._freeze_empty_role_registry(  # noqa: SLF001
        bundle=empty
    )
    assert registry.roles == authority.ROOT_ONLY_EMPTY_ROLE_ORDER
    assert registry.role_counts == tuple(
        (role, 0) for role in authority.ROOT_ONLY_EMPTY_ROLE_ORDER
    )
    attacked = _Bundle(
        (
            SimpleNamespace(
                role=authority.ROOT_ONLY_EMPTY_ROLE_ORDER[0]
            ),
        )
    )
    with pytest.raises(
        authority
        .V075PortableConstructionMultiroundResultV2InvariantViolation,
        match="contains child or promotion work",
    ):
        authority._freeze_empty_role_registry(  # noqa: SLF001
            bundle=attacked
        )


def test_portable_record_binds_role_semantic_identity_and_bytes() -> None:
    wanted = _id("wanted")
    raw = b'{"schema":"test"}\n'
    records = (
        SimpleNamespace(
            role="MULTIROUND_RESULT",
            semantic_artifact_id=_id("other"),
            canonical_artifact_bytes=b"other",
        ),
        SimpleNamespace(
            role="ROOT_EXECUTION",
            semantic_artifact_id=wanted,
            canonical_artifact_bytes=raw,
        ),
        SimpleNamespace(
            role="MULTIROUND_RESULT",
            semantic_artifact_id=wanted,
            canonical_artifact_bytes=raw,
        ),
    )
    selected = authority._portable_record(  # noqa: SLF001
        records,
        role="MULTIROUND_RESULT",
        semantic_id=wanted,
        expected_raw=raw,
        label="result",
    )
    assert selected is records[2]
    with pytest.raises(
        authority
        .V075PortableConstructionMultiroundResultV2InvariantViolation,
        match="bytes differ",
    ):
        authority._portable_record(  # noqa: SLF001
            records,
            role="MULTIROUND_RESULT",
            semantic_id=wanted,
            expected_raw=b"transplanted",
            label="result",
        )


def test_dag_closes_target_and_preserves_all_three_dependency_lanes() -> None:
    upstream, binding = _fixture()
    nodes = authority._iterative_dependency_nodes(  # noqa: SLF001
        upstream_nodes=upstream,
        source_binding=binding,
    )
    by_role = {item.role: item for item in nodes}
    scopes = authority.V075ConstructionMultiroundResultAuthorityScopeV2
    assert (
        by_role["CONSTRUCTION_PLANNING_INPUT"].authority_scope
        is scopes.FULL_CONSTRUCTION_COMPILER_REPLAY
    )
    assert (
        by_role["CLOSED_RECONCILIATION"].authority_scope
        is scopes.FULL_CONSTRUCTION_CLOSED_RECONCILIATION_REPLAY
    )
    target = by_role["MULTIROUND_RESULT"]
    assert target.semantically_resolved is True
    assert (
        target.authority_scope
        is scopes.FULL_CONSTRUCTION_MULTIROUND_RESULT_REPLAY
    )
    assert set(binding.source_dependency_record_ids) <= set(
        target.authority_local_semantic_dependency_record_ids
    )
    assert set(target.effective_dependency_record_ids) == set(
        target.portable_declared_dependency_record_ids
    ) | set(target.authority_local_semantic_dependency_record_ids)
    assert target.unresolved_frontier_record_ids == ()
    assert target.unresolved_frontier_roles == ()


def test_all_three_role_closures_are_exact() -> None:
    upstream, binding = _fixture()
    nodes = authority._iterative_dependency_nodes(  # noqa: SLF001
        upstream_nodes=upstream,
        source_binding=binding,
    )
    closures = authority._build_role_closures(  # noqa: SLF001
        bundle_id=_id("bundle"),
        dependency_dag_id=_id("dag"),
        nodes=nodes,
    )
    assert {
        item.role: item.status.value for item in closures
    } == {
        "CONSTRUCTION_PLANNING_INPUT": (
            "FULL_CONSTRUCTION_COMPILER_REPLAY"
        ),
        "CLOSED_RECONCILIATION": (
            "FULL_CONSTRUCTION_CLOSED_RECONCILIATION_REPLAY"
        ),
        "MULTIROUND_RESULT": (
            "FULL_CONSTRUCTION_MULTIROUND_RESULT_REPLAY"
        ),
    }


def test_aggregate_frontier_is_derived_from_dag_nodes() -> None:
    record_id = _id("frontier")
    fake = SimpleNamespace(
        dependency_dag=SimpleNamespace(
            nodes=(
                SimpleNamespace(
                    unresolved_frontier_record_ids=(),
                    unresolved_frontier_roles=(),
                ),
                SimpleNamespace(
                    unresolved_frontier_record_ids=(record_id,),
                    unresolved_frontier_roles=("UNRESOLVED_ROLE",),
                ),
            )
        )
    )
    assert (
        authority.V075PortableConstructionMultiroundResultReplayV2
        ._remaining_unresolved_frontier_record_ids(fake)
    ) == (record_id,)
    assert (
        authority.V075PortableConstructionMultiroundResultReplayV2
        ._remaining_unresolved_frontier_roles(fake)
    ) == ("UNRESOLVED_ROLE",)


def test_source_target_role_transplants_are_rejected() -> None:
    upstream, binding = _fixture()
    with pytest.raises(
        authority
        .V075PortableConstructionMultiroundResultV2InvariantViolation,
        match="target is transplanted",
    ):
        authority._iterative_dependency_nodes(  # noqa: SLF001
            upstream_nodes=upstream,
            source_binding=_binding_with(
                binding,
                target_record_id=_id("foreign-target"),
            ),
        )
    target = next(
        item for item in upstream if item.role == "MULTIROUND_RESULT"
    )
    changed_sources = tuple(
        (
            role,
            target.record_id if role == "NUMERICAL_MODEL" else record_id,
        )
        for role, record_id in binding.source_records
    )
    with pytest.raises(
        authority
        .V075PortableConstructionMultiroundResultV2InvariantViolation,
        match="source registry is transplanted",
    ):
        authority._iterative_dependency_nodes(  # noqa: SLF001
            upstream_nodes=upstream,
            source_binding=_binding_with(
                binding,
                source_records=changed_sources,
            ),
        )


def test_upstream_dependency_lane_corruption_is_rejected() -> None:
    upstream, binding = _fixture()
    index = next(
        index
        for index, item in enumerate(upstream)
        if item.role == "CONSTRUCTION_PLANNING_INPUT"
    )
    corrupted = _replace_node(
        upstream[index],
        effective_dependency_record_ids=(),
    )
    changed = tuple(
        corrupted if position == index else item
        for position, item in enumerate(upstream)
    )
    with pytest.raises(
        authority
        .V075PortableConstructionMultiroundResultV2InvariantViolation,
        match="upstream DAG lanes are malformed",
    ):
        authority._iterative_dependency_nodes(  # noqa: SLF001
            upstream_nodes=changed,
            source_binding=binding,
        )


def test_effective_cycle_and_4097_nodes_are_rejected() -> None:
    upstream, binding = _fixture()
    target = next(
        item for item in upstream if item.role == "MULTIROUND_RESULT"
    )
    index = next(
        index
        for index, item in enumerate(upstream)
        if item.role == "CONSTRUCTION_PLANNING_INPUT"
    )
    planning = upstream[index]
    portable_lane = tuple(
        sorted(
            set(planning.portable_declared_dependency_record_ids)
            | {target.record_id}
        )
    )
    cycled = _replace_node(
        planning,
        portable_declared_dependency_record_ids=portable_lane,
        effective_dependency_record_ids=tuple(
            sorted(
                set(portable_lane)
                | set(
                    planning
                    .authority_local_semantic_dependency_record_ids
                )
            )
        ),
    )
    changed = tuple(
        cycled if position == index else item
        for position, item in enumerate(upstream)
    )
    with pytest.raises(
        authority
        .V075PortableConstructionMultiroundResultV2InvariantViolation,
        match="contains a cycle",
    ):
        authority._iterative_dependency_nodes(  # noqa: SLF001
            upstream_nodes=changed,
            source_binding=binding,
        )
    oversized = tuple(
        _node(f"oversized:{index}", index, "PUBLIC")
        for index in range(authority.MAX_DEPENDENCY_NODES + 1)
    )
    with pytest.raises(
        authority
        .V075PortableConstructionMultiroundResultV2InvariantViolation,
        match="bounded exact DAG",
    ):
        authority._iterative_dependency_nodes(  # noqa: SLF001
            upstream_nodes=oversized,
            source_binding=binding,
        )


def test_binding_mutation_invalidates_content_identity() -> None:
    _upstream, binding = _fixture()
    object.__setattr__(binding, "root_execution_id", _id("stale"))
    with pytest.raises(
        authority
        .V075PortableConstructionMultiroundResultV2InvariantViolation,
        match="source identity is stale",
    ):
        _ = binding.binding_id


def test_assert_current_reruns_all_five_inputs_and_detects_change(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict[str, object]] = []
    original = {"result_id": _id("original")}
    fake_self = SimpleNamespace(to_document=lambda: original)

    def replayed(**kwargs: object) -> SimpleNamespace:
        calls.append(kwargs)
        return SimpleNamespace(to_document=lambda: dict(original))

    monkeypatch.setattr(
        authority,
        "replay_v075_portable_construction_multiround_result_v2",
        replayed,
    )
    kwargs = {
        "repository_root": ".",
        "portable_bundle_bytes": b"bundle",
        "public_context_closure_bytes": b"context",
        "private_generation_seed": b"seed",
        "private_salt": b"salt",
    }
    (
        authority.V075PortableConstructionMultiroundResultReplayV2
        .assert_current(fake_self, **kwargs)
    )
    assert calls == [kwargs]
    monkeypatch.setattr(
        authority,
        "replay_v075_portable_construction_multiround_result_v2",
        lambda **_kwargs: SimpleNamespace(
            to_document=lambda: {"result_id": _id("changed")}
        ),
    )
    with pytest.raises(
        authority
        .V075PortableConstructionMultiroundResultV2InvariantViolation,
        match="currentness check changed",
    ):
        (
            authority.V075PortableConstructionMultiroundResultReplayV2
            .assert_current(fake_self, **kwargs)
        )


def test_secret_fields_hashes_digests_and_pickle_are_forbidden() -> None:
    for cls in (
        authority.V075PortableConstructionMultiroundResultReplayV2,
        authority.V075ConstructionMultiroundResultTypedGraphV2,
        authority.V075ConstructionMultiroundResultSourceBindingV2,
    ):
        names = {item.name for item in fields(cls)}
        assert "private_generation_seed" not in names
        assert "private_salt" not in names
        assert "generated_environment" not in names
        assert "private_environment" not in names
    tree = ast.parse(inspect.getsource(authority))
    for call in (
        item for item in ast.walk(tree) if isinstance(item, ast.Call)
    ):
        if (
            isinstance(call.func, ast.Attribute)
            and call.func.attr in {"sha256", "hexdigest", "digest"}
        ) or (
            isinstance(call.func, ast.Name) and call.func.id == "_hash"
        ):
            rendered = " ".join(
                ast.unparse(argument) for argument in call.args
            )
            assert "private_generation_seed" not in rendered
            assert "private_salt" not in rendered
    for cls in (
        authority.V075ConstructionRootOnlyEmptyRoleRegistryV2,
        authority.V075ConstructionMultiroundResultSourceBindingV2,
        authority.V075ConstructionMultiroundResultTypedGraphV2,
        authority.V075ConstructionMultiroundResultDependencyDAGV2,
        authority.V075ConstructionMultiroundResultRoleClosureV2,
        authority.V075PortableConstructionMultiroundResultReplayV2,
    ):
        assert "__reduce__" in cls.__dict__
    _upstream, binding = _fixture()
    with pytest.raises(TypeError, match="in-memory-only"):
        pickle.dumps(binding)


def test_all_production_science_certificate_and_accounting_locks_closed() -> None:
    assert authority.CONSTRUCTION_MULTIROUND_RESULT_REPLAYED is True
    assert authority.CONSTRUCTION_ROOT_EXECUTION_REPLAYED is True
    assert authority.ROOT_ONLY_CAP_PROFILE_REPLAYED is True
    assert (
        authority.CONSTRUCTION_CLOSED_RECONCILIATION_REPLAY_REQUIRED is True
    )
    assert authority.CONSTRUCTION_EPHEMERAL_PRIVATE_INPUT_REQUIRED is True
    assert authority.PRODUCTION_MULTIROUND_RESULT_ALLOWED is False
    assert authority.PRODUCTION_PRIVATE_INPUT_CHANNEL_ALLOWED is False
    assert authority.OFFICIAL_EXECUTION_ALLOWED is False
    assert authority.PRODUCTION_AUTHORIZING is False
    assert authority.SCIENTIFIC_ENDPOINT_CREDIT_ALLOWED is False
    assert authority.SOURCE_AUTHORITY_COMPLETE is False
    assert authority.CODE_PROVENANCE_COMPLETE is False
    assert authority.PORTABLE_SEMANTIC_REGISTRY_COMPLETE is False
    assert authority.FRESH_HELDOUT_ACCESS_ALLOWED is False
    assert authority.B3_INPUT_ALLOWED is False
    assert authority.K7_INPUT_ALLOWED is False
    assert authority.KERNEL_ACCESS_ALLOWED is False
    assert authority.J0_ACCESS_ALLOWED is False
    assert authority.OBSERVER_OPEN_ALLOWED is False
    assert authority.WORKER_LAUNCH_ALLOWED is False
    assert authority.OPERATIONAL_REGISTRIES_ALLOWED is False
    assert authority.ACCOUNTING_GATE_PASSED is False
    assert authority.PLAN_CERTIFICATE_ISSUANCE_ALLOWED is False
    assert authority.INFEASIBILITY_CERTIFICATE_ISSUANCE_ALLOWED is False
    assert len(authority.DOMAIN_TAGS) == len(
        set(authority.DOMAIN_TAGS.values())
    )
