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
    v075_portable_construction_planning_input_authority_v2 as authority,
)


def _id(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


class _Scope(str, Enum):
    FULL_PUBLIC = "FULL_PUBLIC"
    FULL_CONSTRUCTION_PRIVATE_REPLAY = (
        "FULL_CONSTRUCTION_PRIVATE_REPLAY"
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
    local: bool = True,
    resolved: bool = True,
    scope: _Scope = _Scope.FULL_PUBLIC,
) -> _UpstreamNode:
    dependencies = tuple(sorted(dependencies))
    return _UpstreamNode(
        _id(label),
        index,
        role,
        dependencies,
        (),
        dependencies,
        _id(f"source:{label}") if local else None,
        local,
        resolved,
        scope,
    )


def _fixture():
    occurrence = _node("occurrence", 0, "OCCURRENCE_IDENTITY")
    schedule = _node("schedule", 1, "INITIAL_ACQUISITION_SCHEDULE")
    model = _node("model", 2, "NUMERICAL_MODEL")
    private_verification = _node(
        "private-verification",
        3,
        "SIGNED_BATCH_JOURNAL_CLOSURE_VERIFICATION",
        scope=_Scope.FULL_CONSTRUCTION_PRIVATE_REPLAY,
    )
    lineage = _node(
        "lineage",
        4,
        "CONSTRUCTION_LINEAGE",
        (private_verification.record_id,),
        scope=_Scope.FULL_CONSTRUCTION_TRANSITIVE,
    )
    lifecycle = _node(
        "lifecycle",
        5,
        "CONSTRUCTION_LIFECYCLE",
        (lineage.record_id,),
        scope=_Scope.FULL_CONSTRUCTION_TRANSITIVE,
    )
    lifecycle_verification = _node(
        "lifecycle-verification",
        6,
        "CONSTRUCTION_LIFECYCLE_VERIFICATION",
        (lifecycle.record_id,),
        scope=_Scope.FULL_CONSTRUCTION_TRANSITIVE,
    )
    planning_input = _node(
        "planning-input",
        7,
        "CONSTRUCTION_PLANNING_INPUT",
        (model.record_id,),
        local=False,
        resolved=False,
        scope=_Scope.UNRESOLVED,
    )
    public_consumer = _node(
        "public-consumer",
        8,
        "PUBLIC_CONSUMER",
        (planning_input.record_id,),
        resolved=False,
        scope=_Scope.UNRESOLVED,
    )
    closed = _node(
        "closed",
        9,
        "CLOSED_RECONCILIATION",
        (planning_input.record_id,),
        local=False,
        resolved=False,
        scope=_Scope.UNRESOLVED,
    )
    result = _node(
        "result",
        10,
        "MULTIROUND_RESULT",
        (closed.record_id,),
        local=False,
        resolved=False,
        scope=_Scope.UNRESOLVED,
    )
    nodes = (
        occurrence,
        schedule,
        model,
        private_verification,
        lineage,
        lifecycle,
        lifecycle_verification,
        planning_input,
        public_consumer,
        closed,
        result,
    )
    records = tuple(
        sorted(
            (
                ("CONSTRUCTION_LIFECYCLE", lifecycle.record_id),
                (
                    "CONSTRUCTION_LIFECYCLE_VERIFICATION",
                    lifecycle_verification.record_id,
                ),
                ("CONSTRUCTION_LINEAGE", lineage.record_id),
                ("INITIAL_ACQUISITION_SCHEDULE", schedule.record_id),
                ("NUMERICAL_MODEL", model.record_id),
                ("OCCURRENCE_IDENTITY", occurrence.record_id),
            )
        )
    )
    values = tuple(_id(f"value:{index}") for index in range(2))
    binding = authority.V075ConstructionPlanningInputSourceBindingV2(
        authority._SOURCE_BINDING_ISSUER,  # noqa: SLF001
        planning_input.record_id,
        _id("planning-input-semantic"),
        records,
        _id("bundle"),
        _id("occurrence-semantic"),
        _id("context"),
        _id("namespace"),
        _id("repository-binding"),
        _id("source-manifest"),
        _id("private-result"),
        _id("planning-result"),
        _id("schedule-semantic"),
        _id("lineage-semantic"),
        _id("lifecycle-semantic"),
        _id("lifecycle-verification-semantic"),
        _id("model-semantic"),
        "ADAPTIVE_QUOTIENT",
        "ADAPTIVE_QUOTIENT",
        values,
        tuple(sorted(_id(f"row:{index}") for index in range(2))),
        tuple(sorted(_id(f"freeze:{index}") for index in range(2))),
        tuple(sorted(_id(f"discovery:{index}") for index in range(2))),
        tuple(sorted(_id(f"validation:{index}") for index in range(2))),
        values,
        _id("compiler-bytes"),
        4096,
    )
    return nodes, binding


def _clone_source(binding, **changes):
    parameters = tuple(
        inspect.signature(
            authority.V075ConstructionPlanningInputSourceBindingV2
        ).parameters
    )
    values = {
        name: getattr(binding, name)
        for name in parameters
        if name != "_issuer"
    }
    values.update(changes)
    return authority.V075ConstructionPlanningInputSourceBindingV2(
        authority._SOURCE_BINDING_ISSUER,  # noqa: SLF001
        **values,
    )


def test_public_entry_and_currentness_are_exactly_five_raw_inputs() -> None:
    assert tuple(
        inspect.signature(
            authority.replay_v075_portable_construction_planning_input_v2
        ).parameters
    ) == (
        "repository_root",
        "portable_bundle_bytes",
        "public_context_closure_bytes",
        "private_generation_seed",
        "private_salt",
    )
    assert tuple(
        inspect.signature(
            authority.V075PortableConstructionPlanningInputReplayV2
            .assert_current
        ).parameters
    ) == (
        "self",
        "repository_root",
        "portable_bundle_bytes",
        "public_context_closure_bytes",
        "private_generation_seed",
        "private_salt",
    )


def test_raw_178_is_first_and_only_work_when_it_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    def raw_178(**_kwargs):
        calls.append("1.78")
        raise RuntimeError("private marker")

    def forbidden(*_args, **_kwargs):
        calls.append("forbidden")
        raise AssertionError("work ran before raw 1.78")

    monkeypatch.setattr(
        authority.private_replay,
        "replay_v075_portable_construction_private_replay_v2",
        raw_178,
    )
    monkeypatch.setattr(
        authority, "_exact_hardened_parts", forbidden
    )
    monkeypatch.setattr(
        authority.planning,
        "compile_v075_construction_planning_input_v2",
        forbidden,
    )
    with pytest.raises(
        authority.V075PortableConstructionPlanningInputV2InvariantViolation
    ) as captured:
        authority.replay_v075_portable_construction_planning_input_v2(
            repository_root=".",
            portable_bundle_bytes=b"bundle",
            public_context_closure_bytes=b"context",
            private_generation_seed=b"seed",
            private_salt=b"salt",
        )
    assert calls == ["1.78"]
    assert str(captured.value) == authority._REPLAY_MISMATCH  # noqa: SLF001
    assert captured.value.__cause__ is None
    assert captured.value.__suppress_context__ is True
    assert "private marker" not in str(captured.value)


def test_scope_dag_closes_input_only_and_propagates_transitively() -> None:
    upstream, binding = _fixture()
    nodes = authority._iterative_dependency_nodes(  # noqa: SLF001
        upstream_nodes=upstream,
        source_binding=binding,
    )
    by_role = {item.role: item for item in nodes}
    scopes = authority.V075ConstructionPlanningInputAuthorityScopeV2
    planning_input = by_role["CONSTRUCTION_PLANNING_INPUT"]
    assert planning_input.semantically_resolved is True
    assert (
        planning_input.authority_scope
        is scopes.FULL_CONSTRUCTION_COMPILER_REPLAY
    )
    assert set(planning_input.effective_dependency_record_ids) == set(
        planning_input.portable_declared_dependency_record_ids
    ) | set(planning_input.authority_local_semantic_dependency_record_ids)
    assert (
        by_role["PUBLIC_CONSUMER"].authority_scope
        is scopes.FULL_CONSTRUCTION_TRANSITIVE
    )
    for role in ("CLOSED_RECONCILIATION", "MULTIROUND_RESULT"):
        item = by_role[role]
        assert item.semantically_resolved is False
        assert item.authority_scope is scopes.UNRESOLVED
        assert item.unresolved_frontier_record_ids == (item.record_id,)
        assert item.unresolved_frontier_roles == (role,)


def test_focus_closures_do_not_authorize_downstream_producers() -> None:
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
    assert tuple(item.role for item in closures) == authority.ROLE_ORDER
    assert {
        item.role: item.status.value for item in closures
    } == {
        "CONSTRUCTION_PLANNING_INPUT": (
            "FULL_CONSTRUCTION_COMPILER_REPLAY"
        ),
        "CLOSED_RECONCILIATION": (
            "STRUCTURAL_ONLY_TRANSITIVE_UNRESOLVED"
        ),
        "MULTIROUND_RESULT": (
            "STRUCTURAL_ONLY_TRANSITIVE_UNRESOLVED"
        ),
    }


@pytest.mark.parametrize("attack", ("target", "source-role"))
def test_source_target_and_exact_source_registry_transplants_fail(
    attack: str,
) -> None:
    upstream, binding = _fixture()
    if attack == "target":
        object.__setattr__(binding, "target_record_id", _id("foreign"))
        expected = "identity is stale"
    else:
        changed = list(binding.source_records)
        changed[0] = ("CONSTRUCTION_LIFECYCLE", _id("foreign"))
        object.__setattr__(binding, "source_records", tuple(changed))
        expected = "identity is stale"
    with pytest.raises(
        authority.V075PortableConstructionPlanningInputV2InvariantViolation,
        match=expected,
    ):
        authority._iterative_dependency_nodes(  # noqa: SLF001
            upstream_nodes=upstream,
            source_binding=binding,
        )


def test_exact_source_metadata_rejects_same_role_model_and_duck_attacks() -> None:
    _upstream, binding = _fixture()
    source_records = tuple(
        (
            role,
            _id("alternate-same-role-model")
            if role == "NUMERICAL_MODEL"
            else record_id,
        )
        for role, record_id in binding.source_records
    )
    alternate_model = _clone_source(
        binding,
        source_records=source_records,
    )
    assert dict(alternate_model.source_records)["NUMERICAL_MODEL"] != (
        dict(binding.source_records)["NUMERICAL_MODEL"]
    )
    for attacked in (
        alternate_model,
        _clone_source(binding, schedule_id=_id("foreign-schedule")),
        SimpleNamespace(to_document=binding.to_document),
    ):
        with pytest.raises(
            authority
            .V075PortableConstructionPlanningInputV2InvariantViolation,
            match="source metadata is stale",
        ):
            authority._assert_exact_source_binding(  # noqa: SLF001
                attacked,
                binding,
            )


def test_exact_target_and_model_bindings_reject_ducks_and_transplants() -> None:
    expected_target = SimpleNamespace(binding_id=_id("target"))
    expected_model = SimpleNamespace(
        _assert_current=lambda: None,
    )
    attacks = (
        (
            SimpleNamespace(binding_id=expected_target.binding_id),
            expected_model,
        ),
        (
            expected_target,
            SimpleNamespace(_assert_current=lambda: None),
        ),
    )
    for target, model in attacks:
        with pytest.raises(
            authority
            .V075PortableConstructionPlanningInputV2InvariantViolation,
            match="record binding is transplanted",
        ):
            authority._assert_exact_record_bindings(  # noqa: SLF001
                target=target,
                expected_target=expected_target,
                model_binding=model,
                expected_model_binding=expected_model,
            )


def test_forward_effective_cycle_and_4097_nodes_are_rejected() -> None:
    upstream, binding = _fixture()
    closed_id = next(
        item.record_id
        for item in upstream
        if item.role == "CLOSED_RECONCILIATION"
    )
    changed = tuple(
        _UpstreamNode(
            item.record_id,
            item.record_index,
            item.role,
            (
                tuple(
                    sorted(
                        set(item.portable_declared_dependency_record_ids)
                        | {closed_id}
                    )
                )
                if item.role == "CONSTRUCTION_PLANNING_INPUT"
                else item.portable_declared_dependency_record_ids
            ),
            item.authority_local_semantic_dependency_record_ids,
            (
                tuple(
                    sorted(
                        set(item.effective_dependency_record_ids)
                        | {closed_id}
                    )
                )
                if item.role == "CONSTRUCTION_PLANNING_INPUT"
                else item.effective_dependency_record_ids
            ),
            item.source_binding_id,
            item.local_semantic_authority_resolved,
            item.semantically_resolved,
            item.authority_scope,
        )
        for item in upstream
    )
    with pytest.raises(
        authority.V075PortableConstructionPlanningInputV2InvariantViolation,
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
        authority.V075PortableConstructionPlanningInputV2InvariantViolation,
        match="bounded exact DAG",
    ):
        authority._iterative_dependency_nodes(  # noqa: SLF001
            upstream_nodes=oversized,
            source_binding=binding,
        )


def test_upstream_effective_lane_corruption_is_rejected_before_recompute() -> None:
    upstream, binding = _fixture()
    changed = list(upstream)
    item = changed[1]
    changed[1] = _UpstreamNode(
        item.record_id,
        item.record_index,
        item.role,
        item.portable_declared_dependency_record_ids,
        item.authority_local_semantic_dependency_record_ids,
        (_id("hidden-effective-edge"),),
        item.source_binding_id,
        item.local_semantic_authority_resolved,
        item.semantically_resolved,
        item.authority_scope,
    )
    with pytest.raises(
        authority.V075PortableConstructionPlanningInputV2InvariantViolation,
        match="dependency lanes changed",
    ):
        authority._iterative_dependency_nodes(  # noqa: SLF001
            upstream_nodes=tuple(changed),
            source_binding=binding,
        )


def test_only_raw_178_and_registered_construction_compiler_are_called() -> None:
    tree = ast.parse(inspect.getsource(authority))
    calls = {
        ast.unparse(item.func)
        for item in ast.walk(tree)
        if isinstance(item, ast.Call)
    }
    assert (
        "private_replay.replay_v075_portable_construction_private_replay_v2"
        in calls
    )
    assert (
        "planning.compile_v075_construction_planning_input_v2" in calls
    )
    forbidden = (
        "freeze_v075_construction_batch_occurrence_lineage",
        "freeze_v075_construction_batch_occurrence_lifecycle",
        "verify_v075_batch_occurrence_lifecycle_bytes",
        "generate_v075_private_environment",
        "seal_v075_generated_private_environment_commitment",
        "kernel",
        "J0",
        "K7",
        "B3",
    )
    for call in calls:
        assert not any(value in call for value in forbidden)


def test_no_secret_fields_hashes_digests_or_pickle_surface() -> None:
    for cls in (
        authority.V075PortableConstructionPlanningInputReplayV2,
        authority.V075ConstructionPlanningInputTypedGraphV2,
        authority.V075ConstructionPlanningInputSourceBindingV2,
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
    _upstream, source = _fixture()
    with pytest.raises(TypeError, match="in-memory-only"):
        pickle.dumps(source)


def test_model_selection_is_role_and_semantic_id_exact_not_arbitrary() -> None:
    source = inspect.getsource(authority._sole_model_binding)  # noqa: SLF001
    assert 'item.role == "NUMERICAL_MODEL"' in source
    assert "item.semantic_artifact_id == model_id" in source
    assert "len(models) != 1" in source
    assert "len(bindings) != 1" in source
    assert "canonical_artifact_bytes != _raw(models[0])" in source
    entry = inspect.getsource(
        authority.replay_v075_portable_construction_planning_input_v2
    )
    assert "target.semantic_artifact_id != compiled.input_id" in entry
    assert "target.canonical_artifact_bytes != _raw(compiled)" in entry
    graph = inspect.getsource(
        authority.V075ConstructionPlanningInputTypedGraphV2._validate
    )
    assert "expected_source_binding = _build_source_binding" in graph
    assert "_assert_exact_record_bindings" in graph


def test_model_registry_rejects_duplicate_or_byte_transplanted_model() -> None:
    model_id = _id("model-id")
    document = {"schema": "model", "model_id": model_id}
    model = SimpleNamespace(
        model_id=model_id,
        to_document=lambda: document,
    )
    exact_raw = authority.canonical_json_bytes(document)
    binding = SimpleNamespace(
        role="NUMERICAL_MODEL",
        semantic_artifact_id=model_id,
        canonical_artifact_bytes=exact_raw,
    )
    hardened = SimpleNamespace(
        typed_graph=SimpleNamespace(
            models=(model,),
            target_record_bindings=(binding,),
        )
    )
    assert authority._sole_model_binding(  # noqa: SLF001
        hardened,
        model_id,
    ) == (model, binding)
    hardened.typed_graph.target_record_bindings = (
        binding,
        SimpleNamespace(
            role="NUMERICAL_MODEL",
            semantic_artifact_id=model_id,
            canonical_artifact_bytes=exact_raw,
        ),
    )
    with pytest.raises(
        authority.V075PortableConstructionPlanningInputV2InvariantViolation,
        match="absent from exact 1.77 registry",
    ):
        authority._sole_model_binding(hardened, model_id)  # noqa: SLF001
    hardened.typed_graph.target_record_bindings = (
        SimpleNamespace(
            role="NUMERICAL_MODEL",
            semantic_artifact_id=model_id,
            canonical_artifact_bytes=b"{}",
        ),
    )
    with pytest.raises(
        authority.V075PortableConstructionPlanningInputV2InvariantViolation,
        match="absent from exact 1.77 registry",
    ):
        authority._sole_model_binding(hardened, model_id)  # noqa: SLF001


def test_row_evidence_batch_freeze_and_lifecycle_transplants_fail() -> None:
    row_id = _id("numerical-row")
    row_binding_id = _id("row-binding")
    lifecycle_id = _id("lifecycle")
    discovery_id = _id("discovery-batch")
    validation_id = _id("validation-batch")
    freeze_id = _id("freeze")

    def batch(batch_id: str, lane: str):
        return SimpleNamespace(
            batch_id=batch_id,
            request=SimpleNamespace(
                stream_identity=SimpleNamespace(
                    row_binding=SimpleNamespace(
                        row_binding_id=row_binding_id
                    ),
                    lane=SimpleNamespace(value=lane),
                    observer_epoch_index=1,
                )
            ),
        )

    evidence = SimpleNamespace(
        numerical_row_id=row_id,
        row_binding_id=row_binding_id,
        support_freeze_id=freeze_id,
        discovery_batch_ids=(discovery_id,),
        latest_validation_batch_ids=(validation_id,),
        latest_validation_epoch_index=1,
        lifecycle_closure_id=lifecycle_id,
    )
    compiled = SimpleNamespace(
        model=SimpleNamespace(rows=(SimpleNamespace(row_id=row_id),)),
        evidence_bindings=(evidence,),
    )
    lineage = SimpleNamespace(
        batches=(
            batch(discovery_id, "DISCOVERY"),
            batch(validation_id, "VALIDATION"),
        )
    )
    lifecycle = SimpleNamespace(
        closure_id=lifecycle_id,
        support_freezes=(
            SimpleNamespace(
                row_binding_id=row_binding_id,
                freeze_id=freeze_id,
                validation_epoch_index=1,
                source_discovery_batch_ids=(discovery_id,),
            ),
        ),
    )
    authority._validate_complete_row_evidence(  # noqa: SLF001
        compiled=compiled,
        lineage=lineage,
        lifecycle=lifecycle,
    )
    for field_name, foreign in (
        ("discovery_batch_ids", (_id("foreign-batch"),)),
        ("support_freeze_id", _id("foreign-freeze")),
        ("lifecycle_closure_id", _id("foreign-lifecycle")),
    ):
        original = getattr(evidence, field_name)
        setattr(evidence, field_name, foreign)
        with pytest.raises(
            authority
            .V075PortableConstructionPlanningInputV2InvariantViolation,
            match="incomplete or stale",
        ):
            authority._validate_complete_row_evidence(  # noqa: SLF001
                compiled=compiled,
                lineage=lineage,
                lifecycle=lifecycle,
            )
        setattr(evidence, field_name, original)


def test_assert_current_reruns_five_raw_inputs_and_detects_change(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict] = []
    original_document = {"result_id": _id("original")}
    fake_self = SimpleNamespace(to_document=lambda: original_document)

    def replayed(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(to_document=lambda: dict(original_document))

    monkeypatch.setattr(
        authority,
        "replay_v075_portable_construction_planning_input_v2",
        replayed,
    )
    kwargs = {
        "repository_root": ".",
        "portable_bundle_bytes": b"bundle",
        "public_context_closure_bytes": b"context",
        "private_generation_seed": b"seed",
        "private_salt": b"salt",
    }
    authority.V075PortableConstructionPlanningInputReplayV2.assert_current(
        fake_self,
        **kwargs,
    )
    assert calls == [kwargs]
    monkeypatch.setattr(
        authority,
        "replay_v075_portable_construction_planning_input_v2",
        lambda **_kwargs: SimpleNamespace(
            to_document=lambda: {"result_id": _id("changed")}
        ),
    )
    with pytest.raises(
        authority.V075PortableConstructionPlanningInputV2InvariantViolation,
        match="currentness check changed",
    ):
        authority.V075PortableConstructionPlanningInputReplayV2.assert_current(
            fake_self,
            **kwargs,
        )


def test_all_production_science_and_certificate_locks_remain_closed() -> None:
    assert authority.CONSTRUCTION_PLANNING_INPUT_COMPILER_REPLAYED is True
    assert authority.CONSTRUCTION_PRIVATE_REPLAY_REQUIRED is True
    assert authority.PRODUCTION_COMPILER_ALLOWED is False
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
    assert authority.PLAN_CERTIFICATE_ISSUANCE_ALLOWED is False
    assert authority.INFEASIBILITY_CERTIFICATE_ISSUANCE_ALLOWED is False
