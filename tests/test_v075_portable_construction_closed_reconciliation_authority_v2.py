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
    v075_portable_construction_closed_reconciliation_authority_v2
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
    authority.V075ConstructionClosedReconciliationSourceBindingV2,
]:
    source_nodes: dict[str, _UpstreamNode] = {}
    for index, role in enumerate(authority.SOURCE_ROLE_ORDER):
        scope = (
            _Scope.FULL_CONSTRUCTION_COMPILER_REPLAY
            if role == "CONSTRUCTION_PLANNING_INPUT"
            else _Scope.FULL_CONSTRUCTION_TRANSITIVE
            if role
            in {
                "CONSTRUCTION_LINEAGE",
                "CONSTRUCTION_LIFECYCLE",
            }
            else _Scope.FULL_PUBLIC
        )
        source_nodes[role] = _node(
            f"source:{role}",
            index,
            role,
            scope=scope,
        )
    # The compiler input already has its exact model dependency in 1.79.
    planning = source_nodes["CONSTRUCTION_PLANNING_INPUT"]
    source_nodes["CONSTRUCTION_PLANNING_INPUT"] = _node(
        "source:CONSTRUCTION_PLANNING_INPUT",
        planning.record_index,
        planning.role,
        (source_nodes["NUMERICAL_MODEL"].record_id,),
        scope=_Scope.FULL_CONSTRUCTION_COMPILER_REPLAY,
    )
    closed = _node(
        "closed",
        len(source_nodes),
        "CLOSED_RECONCILIATION",
        (source_nodes["CONSTRUCTION_PLANNING_INPUT"].record_id,),
        local=False,
        resolved=False,
        scope=_Scope.UNRESOLVED,
    )
    multiround = _node(
        "multiround",
        len(source_nodes) + 1,
        "MULTIROUND_RESULT",
        (closed.record_id,),
        local=False,
        resolved=False,
        scope=_Scope.UNRESOLVED,
    )
    nodes = tuple(
        sorted(
            (*source_nodes.values(), closed, multiround),
            key=lambda item: item.record_index,
        )
    )
    source_records = tuple(
        (role, source_nodes[role].record_id)
        for role in authority.SOURCE_ROLE_ORDER
    )
    binding = authority.V075ConstructionClosedReconciliationSourceBindingV2(
        authority._SOURCE_BINDING_ISSUER,  # noqa: SLF001
        closed.record_id,
        _id("closed-semantic"),
        source_records,
        _id("bundle"),
        _id("occurrence"),
        _id("context"),
        _id("planning-input-replay"),
        _id("schedule"),
        source_nodes["CONTROLLED_JOURNAL_CLOSURE"].record_id,
        _id("control-closure"),
        _id("batch-closure"),
        _id("final-epoch"),
        _id("final-model"),
        _id("final-proof"),
        _id("lineage"),
        _id("lifecycle"),
        _id("planning-input"),
        _id("reconciliation-bytes"),
        8192,
    )
    return nodes, binding


def _replace_node(
    node: _UpstreamNode,
    **changes: object,
) -> _UpstreamNode:
    values = {
        "record_id": node.record_id,
        "record_index": node.record_index,
        "role": node.role,
        "portable_declared_dependency_record_ids": (
            node.portable_declared_dependency_record_ids
        ),
        "authority_local_semantic_dependency_record_ids": (
            node.authority_local_semantic_dependency_record_ids
        ),
        "effective_dependency_record_ids": (
            node.effective_dependency_record_ids
        ),
        "source_binding_id": node.source_binding_id,
        "local_semantic_authority_resolved": (
            node.local_semantic_authority_resolved
        ),
        "semantically_resolved": node.semantically_resolved,
        "authority_scope": node.authority_scope,
    }
    values.update(changes)
    return _UpstreamNode(**values)


def _binding_with(
    original: authority.V075ConstructionClosedReconciliationSourceBindingV2,
    **changes: object,
) -> authority.V075ConstructionClosedReconciliationSourceBindingV2:
    values = {
        item.name: getattr(original, item.name)
        for item in fields(type(original))
        if item.init
    }
    values.update(changes)
    return authority.V075ConstructionClosedReconciliationSourceBindingV2(
        authority._SOURCE_BINDING_ISSUER,  # noqa: SLF001
        **values,
    )


def test_entry_owner_and_currentness_signatures_are_exact() -> None:
    expected = (
        "repository_root",
        "portable_bundle_bytes",
        "public_context_closure_bytes",
        "private_generation_seed",
        "private_salt",
    )
    assert tuple(
        inspect.signature(
            authority
            .replay_v075_portable_construction_closed_reconciliation_v2
        ).parameters
    ) == expected
    assert tuple(
        inspect.signature(
            authority
            .V075PortableConstructionClosedReconciliationReplayV2
            .assert_current
        ).parameters
    ) == ("self", *expected)
    assert tuple(
        inspect.signature(
            authority.owner
            .freeze_v075_construction_closed_reconciliation_v2
        ).parameters
    ) == (
        "repository_root",
        "schedule",
        "final_epoch",
        "controlled_closure",
        "lineage",
        "lifecycle",
    )
    currentness = inspect.getsource(
        authority
        .V075PortableConstructionClosedReconciliationReplayV2
        .assert_current
    )
    for name in expected:
        assert f"{name}={name}" in currentness


def test_raw_179_is_first_and_only_work_when_it_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    def raw_179(**_kwargs):
        calls.append("1.79")
        raise RuntimeError("private marker")

    def forbidden(*_args, **_kwargs):
        calls.append("forbidden")
        raise AssertionError("work ran before raw 1.79")

    monkeypatch.setattr(
        authority.input_authority,
        "replay_v075_portable_construction_planning_input_v2",
        raw_179,
    )
    monkeypatch.setattr(authority, "_exact_chain", forbidden)
    monkeypatch.setattr(
        authority.portable,
        "verify_v075_portable_occurrence_evidence_bundle_bytes_v2",
        forbidden,
    )
    monkeypatch.setattr(
        authority.owner,
        "freeze_v075_construction_closed_reconciliation_v2",
        forbidden,
    )
    with pytest.raises(
        authority
        .V075PortableConstructionClosedReconciliationV2InvariantViolation
    ) as captured:
        authority.replay_v075_portable_construction_closed_reconciliation_v2(
            repository_root=".",
            portable_bundle_bytes=b"bundle",
            public_context_closure_bytes=b"context",
            private_generation_seed=b"seed",
            private_salt=b"salt",
        )
    assert calls == ["1.79"]
    assert str(captured.value) == authority._REPLAY_MISMATCH  # noqa: SLF001
    assert captured.value.__cause__ is None
    assert captured.value.__suppress_context__ is True
    assert "private marker" not in str(captured.value)


def test_owner_api_is_the_only_closed_reconciliation_producer() -> None:
    tree = ast.parse(inspect.getsource(authority))
    calls = {
        ast.unparse(item.func)
        for item in ast.walk(tree)
        if isinstance(item, ast.Call)
    }
    assert (
        "input_authority."
        "replay_v075_portable_construction_planning_input_v2"
        in calls
    )
    assert (
        "owner.freeze_v075_construction_closed_reconciliation_v2"
        in calls
    )
    assert (
        "portable."
        "verify_v075_portable_occurrence_evidence_bundle_bytes_v2"
        in calls
    )
    forbidden_calls = (
        "owner.V075ObserverSignedClosedReconciliationV2",
        "_CLOSED_RECONCILIATION_ISSUER",
        "_close_and_reconcile",
        "compile_v075_construction_planning_input_v2",
        "plan_v075_construction_numerical_model_v2",
        "kernel",
        "J0",
        "K7",
        "B3",
    )
    for call in calls:
        assert not any(token in call for token in forbidden_calls)


def test_exact_multi_record_selection_never_takes_first_record() -> None:
    wanted = _id("wanted")
    values = (
        SimpleNamespace(model_id=_id("other"), marker="first"),
        SimpleNamespace(model_id=wanted, marker="wanted"),
        SimpleNamespace(model_id=_id("third"), marker="third"),
    )
    selected = authority._unique_by_semantic_id(  # noqa: SLF001
        values,
        semantic_id=wanted,
        identity_attribute="model_id",
        label="model",
    )
    assert selected.marker == "wanted"
    with pytest.raises(
        authority
        .V075PortableConstructionClosedReconciliationV2InvariantViolation,
        match="absent or duplicated",
    ):
        authority._unique_by_semantic_id(  # noqa: SLF001
            (*values, SimpleNamespace(model_id=wanted)),
            semantic_id=wanted,
            identity_attribute="model_id",
            label="model",
        )


def test_portable_record_selection_binds_role_semantic_id_and_bytes() -> None:
    wanted = _id("wanted")
    raw = b'{"schema":"test"}\n'
    records = (
        SimpleNamespace(
            role="NUMERICAL_MODEL",
            semantic_artifact_id=_id("other"),
            canonical_artifact_bytes=b"other",
        ),
        SimpleNamespace(
            role="NUMERICAL_PLANNING_PROOF",
            semantic_artifact_id=wanted,
            canonical_artifact_bytes=raw,
        ),
        SimpleNamespace(
            role="NUMERICAL_MODEL",
            semantic_artifact_id=wanted,
            canonical_artifact_bytes=raw,
        ),
    )
    selected = authority._portable_record(  # noqa: SLF001
        records,
        role="NUMERICAL_MODEL",
        semantic_id=wanted,
        expected_raw=raw,
        label="model",
    )
    assert selected is records[2]
    with pytest.raises(
        authority
        .V075PortableConstructionClosedReconciliationV2InvariantViolation,
        match="bytes differ",
    ):
        authority._portable_record(  # noqa: SLF001
            records,
            role="NUMERICAL_MODEL",
            semantic_id=wanted,
            expected_raw=b"transplanted",
            label="model",
        )
    with pytest.raises(
        authority
        .V075PortableConstructionClosedReconciliationV2InvariantViolation,
        match="absent, duplicated, or role-transplanted",
    ):
        authority._portable_record(  # noqa: SLF001
            (*records, records[2]),
            role="NUMERICAL_MODEL",
            semantic_id=wanted,
            expected_raw=raw,
            label="model",
        )


def test_dag_closes_closed_reconciliation_only_and_preserves_scopes() -> None:
    upstream, binding = _fixture()
    nodes = authority._iterative_dependency_nodes(  # noqa: SLF001
        upstream_nodes=upstream,
        source_binding=binding,
    )
    by_role = {item.role: item for item in nodes}
    scopes = authority.V075ConstructionClosedReconciliationAuthorityScopeV2
    planning = by_role["CONSTRUCTION_PLANNING_INPUT"]
    closed = by_role["CLOSED_RECONCILIATION"]
    result = by_role["MULTIROUND_RESULT"]
    assert planning.semantically_resolved is True
    assert planning.authority_scope is scopes.FULL_CONSTRUCTION_COMPILER_REPLAY
    assert closed.semantically_resolved is True
    assert (
        closed.authority_scope
        is scopes.FULL_CONSTRUCTION_CLOSED_RECONCILIATION_REPLAY
    )
    assert set(closed.authority_local_semantic_dependency_record_ids) >= set(
        binding.source_dependency_record_ids
    )
    assert set(closed.effective_dependency_record_ids) == set(
        closed.portable_declared_dependency_record_ids
    ) | set(closed.authority_local_semantic_dependency_record_ids)
    assert result.semantically_resolved is False
    assert result.authority_scope is scopes.UNRESOLVED
    assert result.unresolved_frontier_record_ids == (result.record_id,)
    assert result.unresolved_frontier_roles == ("MULTIROUND_RESULT",)


def test_role_closures_keep_multiround_unresolved() -> None:
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
            "STRUCTURAL_ONLY_TRANSITIVE_UNRESOLVED"
        ),
    }


def test_source_target_role_transplant_and_reverse_result_edge_fail() -> None:
    upstream, binding = _fixture()
    foreign_target = _binding_with(
        binding,
        target_record_id=_id("foreign-target"),
    )
    with pytest.raises(
        authority
        .V075PortableConstructionClosedReconciliationV2InvariantViolation,
        match="target is transplanted",
    ):
        authority._iterative_dependency_nodes(  # noqa: SLF001
            upstream_nodes=upstream,
            source_binding=foreign_target,
        )

    result = next(
        item for item in upstream if item.role == "MULTIROUND_RESULT"
    )
    changed_sources = tuple(
        (
            role,
            result.record_id if role == "NUMERICAL_MODEL" else record_id,
        )
        for role, record_id in binding.source_records
    )
    reverse = _binding_with(binding, source_records=changed_sources)
    with pytest.raises(
        authority
        .V075PortableConstructionClosedReconciliationV2InvariantViolation,
        match="source registry is transplanted",
    ):
        authority._iterative_dependency_nodes(  # noqa: SLF001
            upstream_nodes=upstream,
            source_binding=reverse,
        )


def test_upstream_lane_corruption_is_rejected() -> None:
    upstream, binding = _fixture()
    planning_index = next(
        index
        for index, item in enumerate(upstream)
        if item.role == "CONSTRUCTION_PLANNING_INPUT"
    )
    planning = upstream[planning_index]
    corrupted = _replace_node(
        planning,
        effective_dependency_record_ids=(),
    )
    changed = tuple(
        corrupted if index == planning_index else item
        for index, item in enumerate(upstream)
    )
    with pytest.raises(
        authority
        .V075PortableConstructionClosedReconciliationV2InvariantViolation,
        match="upstream DAG lanes are malformed",
    ):
        authority._iterative_dependency_nodes(  # noqa: SLF001
            upstream_nodes=changed,
            source_binding=binding,
        )


def test_effective_cycle_and_4097_node_graph_are_rejected() -> None:
    upstream, binding = _fixture()
    closed = next(
        item for item in upstream if item.role == "CLOSED_RECONCILIATION"
    )
    planning_index = next(
        index
        for index, item in enumerate(upstream)
        if item.role == "CONSTRUCTION_PLANNING_INPUT"
    )
    planning = upstream[planning_index]
    portable_lane = tuple(
        sorted(
            set(planning.portable_declared_dependency_record_ids)
            | {closed.record_id}
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
        cycled if index == planning_index else item
        for index, item in enumerate(upstream)
    )
    with pytest.raises(
        authority
        .V075PortableConstructionClosedReconciliationV2InvariantViolation,
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
        .V075PortableConstructionClosedReconciliationV2InvariantViolation,
        match="bounded exact DAG",
    ):
        authority._iterative_dependency_nodes(  # noqa: SLF001
            upstream_nodes=oversized,
            source_binding=binding,
        )


def test_binding_mutation_invalidates_content_identity() -> None:
    _upstream, binding = _fixture()
    object.__setattr__(binding, "final_model_epoch_id", _id("stale"))
    with pytest.raises(
        authority
        .V075PortableConstructionClosedReconciliationV2InvariantViolation,
        match="source identity is stale",
    ):
        _ = binding.binding_id


def test_assert_current_reruns_all_five_inputs_and_detects_change(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict[str, object]] = []
    original_document = {"result_id": _id("original")}
    fake_self = SimpleNamespace(to_document=lambda: original_document)

    def replayed(**kwargs: object) -> SimpleNamespace:
        calls.append(kwargs)
        return SimpleNamespace(
            to_document=lambda: dict(original_document)
        )

    monkeypatch.setattr(
        authority,
        "replay_v075_portable_construction_closed_reconciliation_v2",
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
        authority
        .V075PortableConstructionClosedReconciliationReplayV2
        .assert_current(fake_self, **kwargs)
    )
    assert calls == [kwargs]
    monkeypatch.setattr(
        authority,
        "replay_v075_portable_construction_closed_reconciliation_v2",
        lambda **_kwargs: SimpleNamespace(
            to_document=lambda: {"result_id": _id("changed")}
        ),
    )
    with pytest.raises(
        authority
        .V075PortableConstructionClosedReconciliationV2InvariantViolation,
        match="currentness check changed",
    ):
        (
            authority
            .V075PortableConstructionClosedReconciliationReplayV2
            .assert_current(fake_self, **kwargs)
        )


def test_secret_fields_hashes_digests_and_pickle_are_forbidden() -> None:
    for cls in (
        authority.V075PortableConstructionClosedReconciliationReplayV2,
        authority.V075ConstructionClosedReconciliationTypedGraphV2,
        authority.V075ConstructionClosedReconciliationSourceBindingV2,
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
        authority.V075PortableConstructionClosedReconciliationReplayV2,
        authority.V075ConstructionClosedReconciliationTypedGraphV2,
        authority.V075ConstructionClosedReconciliationDependencyDAGV2,
        authority.V075ConstructionClosedReconciliationRoleClosureV2,
        authority.V075ConstructionClosedReconciliationSourceBindingV2,
    ):
        assert "__reduce__" in cls.__dict__
    _upstream, binding = _fixture()
    with pytest.raises(TypeError, match="in-memory-only"):
        pickle.dumps(binding)


def test_all_production_science_certificate_and_accounting_locks_closed() -> None:
    assert authority.CONSTRUCTION_CLOSED_RECONCILIATION_REPLAYED is True
    assert authority.CONSTRUCTION_PLANNING_INPUT_REPLAY_REQUIRED is True
    assert authority.CONSTRUCTION_EPHEMERAL_PRIVATE_INPUT_REQUIRED is True
    assert authority.PRODUCTION_RECONCILIATION_ALLOWED is False
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
