from __future__ import annotations

import ast
from dataclasses import dataclass, fields
import hashlib
import inspect

import pytest

from acfqp import (
    v075_portable_construction_private_replay_authority_v2 as authority,
)


def _id(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class _UpstreamNode:
    record_id: str
    record_index: int
    role: str
    portable_declared_dependency_record_ids: tuple[str, ...]
    authority_local_semantic_dependency_record_ids: tuple[str, ...]
    effective_dependency_record_ids: tuple[str, ...]
    local_semantic_authority_resolved: bool
    semantically_resolved: bool
    source_binding_id: str | None = None


def _source_binding(
    *,
    role: str,
    target_record_id: str,
    source_dependencies: tuple[str, ...],
) -> authority.V075ConstructionPrivateReplaySourceBindingV2:
    return authority.V075ConstructionPrivateReplaySourceBindingV2(
        authority._SOURCE_BINDING_ISSUER,  # noqa: SLF001
        target_record_id,
        role,
        _id(f"semantic:{role}"),
        authority._resolver_for_role(role),  # noqa: SLF001
        tuple(sorted(source_dependencies)),
        tuple(sorted(_id(f"context-record:{index}") for index in range(3))),
        tuple(
            sorted(_id(f"context-semantic:{index}") for index in range(3))
        ),
        _id("context-closure"),
        _id("generation-profile"),
        _id("commitment"),
        _id("authorization"),
        _id("namespace"),
        _id("occurrence"),
        _id("batch-closure"),
        _id(f"producer:{role}"),
        17,
    )


def _scope_fixture():
    root = _id("root")
    lineage = _id("lineage")
    lifecycle = _id("lifecycle")
    lifecycle_verification = _id("lifecycle-verification")
    private_verification = _id("private-verification")
    planning_input = _id("planning-input")
    downstream = _id("downstream")

    def node(
        record_id: str,
        index: int,
        role: str,
        dependencies: tuple[str, ...],
        local: bool,
    ) -> _UpstreamNode:
        dependencies = tuple(sorted(dependencies))
        return _UpstreamNode(
            record_id,
            index,
            role,
            dependencies,
            (),
            dependencies,
            local,
            local and not dependencies,
        )

    # The private verification deliberately comes after its transitive
    # consumers in portable index order.  Kahn, not record order, must govern.
    nodes = (
        node(root, 0, "SIGNED_BATCH_JOURNAL_CLOSURE", (), True),
        node(lineage, 1, "CONSTRUCTION_LINEAGE", (root,), False),
        node(lifecycle, 2, "CONSTRUCTION_LIFECYCLE", (lineage,), True),
        node(
            lifecycle_verification,
            3,
            "CONSTRUCTION_LIFECYCLE_VERIFICATION",
            (lifecycle,),
            True,
        ),
        node(
            private_verification,
            4,
            "SIGNED_BATCH_JOURNAL_CLOSURE_VERIFICATION",
            (root,),
            False,
        ),
        node(
            planning_input,
            5,
            "CONSTRUCTION_PLANNING_INPUT",
            (lifecycle_verification,),
            False,
        ),
        node(
            downstream,
            6,
            "CLOSED_RECONCILIATION",
            (lifecycle_verification,),
            True,
        ),
    )
    bindings = (
        _source_binding(
            role="SIGNED_BATCH_JOURNAL_CLOSURE_VERIFICATION",
            target_record_id=private_verification,
            source_dependencies=(),
        ),
        _source_binding(
            role="CONSTRUCTION_LINEAGE",
            target_record_id=lineage,
            source_dependencies=(private_verification,),
        ),
        _source_binding(
            role="CONSTRUCTION_LIFECYCLE",
            target_record_id=lifecycle,
            source_dependencies=(lineage,),
        ),
        _source_binding(
            role="CONSTRUCTION_LIFECYCLE_VERIFICATION",
            target_record_id=lifecycle_verification,
            source_dependencies=(lifecycle,),
        ),
    )
    return nodes, bindings


def test_public_entry_and_currentness_signatures_are_raw_only() -> None:
    assert tuple(
        inspect.signature(
            authority.replay_v075_portable_construction_private_replay_v2
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
            authority.V075PortableConstructionPrivateReplayV2.assert_current
        ).parameters
    ) == (
        "self",
        "repository_root",
        "portable_bundle_bytes",
        "public_context_closure_bytes",
        "private_generation_seed",
        "private_salt",
    )


def test_hardened_177_runs_before_local_or_private_work(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    def hardened(**_kwargs):
        calls.append("1.77")
        raise RuntimeError("stop")

    def forbidden(*_args, **_kwargs):
        calls.append("forbidden")
        raise AssertionError("local/private work ran before 1.77")

    monkeypatch.setattr(
        authority.m2_planning,
        "replay_v075_portable_planning_authority_v2",
        hardened,
    )
    monkeypatch.setattr(
        authority.portable,
        "verify_v075_portable_occurrence_evidence_bundle_bytes_v2",
        forbidden,
    )
    monkeypatch.setattr(
        authority.generation,
        "generate_v075_private_environment_v1",
        forbidden,
    )
    with pytest.raises(
        authority.V075PortableConstructionPrivateReplayV2InvariantViolation,
        match="hardened 1.77",
    ):
        authority.replay_v075_portable_construction_private_replay_v2(
            repository_root=".",
            portable_bundle_bytes=b"bundle",
            public_context_closure_bytes=b"context",
            private_generation_seed=b"seed",
            private_salt=b"salt",
        )
    assert calls == ["1.77"]


def test_secret_caps_fail_after_hardened_replay_and_before_bundle(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    class _Upstream:
        def _assert_current(self):
            calls.append("upstream-current")

    monkeypatch.setattr(
        authority.m2_planning,
        "replay_v075_portable_planning_authority_v2",
        lambda **_kwargs: (calls.append("1.77") or _Upstream()),
    )
    monkeypatch.setattr(
        authority.portable,
        "verify_v075_portable_occurrence_evidence_bundle_bytes_v2",
        lambda _raw: calls.append("bundle"),
    )
    with pytest.raises(
        authority.V075PortableConstructionPrivateReplayV2InvariantViolation,
        match="registered public context",
    ):
        authority.replay_v075_portable_construction_private_replay_v2(
            repository_root=".",
            portable_bundle_bytes=b"bundle",
            public_context_closure_bytes=b"context",
            private_generation_seed=(
                b"x" * (authority.MAX_PRIVATE_GENERATION_SEED_BYTES + 1)
            ),
            private_salt=b"salt",
        )
    assert calls == ["1.77", "upstream-current"]


def test_private_failure_is_uniform_and_suppresses_sensitive_cause(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _Upstream:
        def _assert_current(self):
            return None

    monkeypatch.setattr(
        authority.m2_planning,
        "replay_v075_portable_planning_authority_v2",
        lambda **_kwargs: _Upstream(),
    )
    monkeypatch.setattr(
        authority.portable,
        "verify_v075_portable_occurrence_evidence_bundle_bytes_v2",
        lambda _raw: object(),
    )
    monkeypatch.setattr(
        authority,
        "_public_context_resolution",
        lambda **_kwargs: (object(), object()),
    )
    marker = "DO_NOT_EXPOSE_PRIVATE_MARKER"

    def fail_generation(**_kwargs):
        raise RuntimeError(marker)

    monkeypatch.setattr(
        authority.generation,
        "generate_v075_private_environment_v1",
        fail_generation,
    )
    with pytest.raises(
        authority.V075PortableConstructionPrivateReplayV2InvariantViolation
    ) as captured:
        authority.replay_v075_portable_construction_private_replay_v2(
            repository_root=".",
            portable_bundle_bytes=b"bundle",
            public_context_closure_bytes=b"context",
            private_generation_seed=bytes(range(32)),
            private_salt=b"s" * 32,
        )
    assert str(captured.value) == authority._PRIVATE_MISMATCH  # noqa: SLF001
    assert marker not in str(captured.value)
    assert captured.value.__cause__ is None
    assert captured.value.__suppress_context__ is True


def test_forward_safe_kahn_propagates_authority_scope_not_full_public() -> None:
    upstream, bindings = _scope_fixture()
    nodes = authority._iterative_dependency_nodes(  # noqa: SLF001
        upstream_nodes=upstream,
        source_bindings=bindings,
    )
    by_role = {item.role: item for item in nodes}
    scope = authority.V075ConstructionPrivateReplayAuthorityScopeV2
    assert (
        by_role["SIGNED_BATCH_JOURNAL_CLOSURE"].authority_scope
        is scope.FULL_PUBLIC
    )
    assert (
        by_role[
            "SIGNED_BATCH_JOURNAL_CLOSURE_VERIFICATION"
        ].authority_scope
        is scope.FULL_CONSTRUCTION_PRIVATE_REPLAY
    )
    for role in (
        "CONSTRUCTION_LINEAGE",
        "CONSTRUCTION_LIFECYCLE",
        "CONSTRUCTION_LIFECYCLE_VERIFICATION",
        "CLOSED_RECONCILIATION",
    ):
        assert (
            by_role[role].authority_scope
            is scope.FULL_CONSTRUCTION_TRANSITIVE
        )
    planning = by_role["CONSTRUCTION_PLANNING_INPUT"]
    assert planning.authority_scope is scope.UNRESOLVED
    assert planning.semantically_resolved is False
    assert planning.unresolved_frontier_record_ids == (planning.record_id,)
    assert planning.unresolved_frontier_roles == (
        "CONSTRUCTION_PLANNING_INPUT",
    )
    assert tuple(item.record_index for item in nodes) == tuple(
        range(len(nodes))
    )


def test_three_dependency_lanes_and_normative_role_statuses() -> None:
    upstream, bindings = _scope_fixture()
    nodes = authority._iterative_dependency_nodes(  # noqa: SLF001
        upstream_nodes=upstream,
        source_bindings=bindings,
    )
    for item in nodes:
        assert set(item.effective_dependency_record_ids) == set(
            item.portable_declared_dependency_record_ids
        ) | set(item.authority_local_semantic_dependency_record_ids)
    closures = authority._build_role_closures(  # noqa: SLF001
        bundle_id=_id("bundle"),
        dependency_dag_id=_id("dag"),
        nodes=nodes,
    )
    statuses = {item.role: item.status.value for item in closures}
    assert statuses == {
        "SIGNED_BATCH_JOURNAL_CLOSURE_VERIFICATION": (
            "FULL_CONSTRUCTION_PRIVATE_REPLAY"
        ),
        "CONSTRUCTION_LINEAGE": "FULL_CONSTRUCTION_TRANSITIVE",
        "CONSTRUCTION_LIFECYCLE": "FULL_CONSTRUCTION_TRANSITIVE",
        "CONSTRUCTION_LIFECYCLE_VERIFICATION": (
            "FULL_CONSTRUCTION_TRANSITIVE"
        ),
        "CONSTRUCTION_PLANNING_INPUT": (
            "STRUCTURAL_ONLY_TRANSITIVE_UNRESOLVED"
        ),
    }


def test_effective_cycle_is_rejected_even_with_forward_record_order() -> None:
    upstream, bindings = _scope_fixture()
    lineage_id = next(
        item.record_id
        for item in upstream
        if item.role == "CONSTRUCTION_LINEAGE"
    )
    changed = []
    for item in upstream:
        if item.role == "SIGNED_BATCH_JOURNAL_CLOSURE_VERIFICATION":
            dependencies = (lineage_id,)
            changed.append(
                _UpstreamNode(
                    item.record_id,
                    item.record_index,
                    item.role,
                    dependencies,
                    (),
                    dependencies,
                    item.local_semantic_authority_resolved,
                    False,
                )
            )
        else:
            changed.append(item)
    with pytest.raises(
        authority.V075PortableConstructionPrivateReplayV2InvariantViolation,
        match="contains a cycle",
    ):
        authority._iterative_dependency_nodes(  # noqa: SLF001
            upstream_nodes=tuple(changed),
            source_bindings=bindings,
        )


def test_dependency_node_cap_is_hard() -> None:
    oversized = tuple(
        _UpstreamNode(
            _id(f"oversized:{index}"),
            index,
            "PUBLIC",
            (),
            (),
            (),
            True,
            True,
        )
        for index in range(authority.MAX_DEPENDENCY_NODES + 1)
    )
    with pytest.raises(
        authority.V075PortableConstructionPrivateReplayV2InvariantViolation,
        match="bounded exact DAG",
    ):
        authority._iterative_dependency_nodes(  # noqa: SLF001
            upstream_nodes=oversized,
            source_bindings=(),
        )


def test_private_verification_rejects_nonpublic_dependency_scope() -> None:
    upstream, bindings = _scope_fixture()
    changed = tuple(
        _UpstreamNode(
            item.record_id,
            item.record_index,
            item.role,
            item.portable_declared_dependency_record_ids,
            item.authority_local_semantic_dependency_record_ids,
            item.effective_dependency_record_ids,
            (
                False
                if item.role == "SIGNED_BATCH_JOURNAL_CLOSURE"
                else item.local_semantic_authority_resolved
            ),
            False,
            item.source_binding_id,
        )
        for item in upstream
    )
    with pytest.raises(
        authority.V075PortableConstructionPrivateReplayV2InvariantViolation,
        match="depends on nonpublic scope",
    ):
        authority._iterative_dependency_nodes(  # noqa: SLF001
            upstream_nodes=changed,
            source_bindings=bindings,
        )


@pytest.mark.parametrize("attack", ("target", "dependency"))
def test_source_target_or_dependency_transplant_is_rejected(
    attack: str,
) -> None:
    upstream, bindings = _scope_fixture()
    changed = list(bindings)
    if attack == "target":
        original = changed[0]
        changed[0] = _source_binding(
            role=original.target_role,
            target_record_id=_id("foreign-target"),
            source_dependencies=original.source_dependency_record_ids,
        )
        expected = "coverage is not exact"
    else:
        original = changed[1]
        root_id = next(
            item.record_id
            for item in upstream
            if item.role == "SIGNED_BATCH_JOURNAL_CLOSURE"
        )
        changed[1] = _source_binding(
            role=original.target_role,
            target_record_id=original.target_record_id,
            source_dependencies=(root_id,),
        )
        expected = "source dependency is transplanted"
    with pytest.raises(
        authority.V075PortableConstructionPrivateReplayV2InvariantViolation,
        match=expected,
    ):
        authority._iterative_dependency_nodes(  # noqa: SLF001
            upstream_nodes=upstream,
            source_bindings=tuple(changed),
        )


def test_source_binding_content_id_detects_public_field_mutation() -> None:
    binding = _source_binding(
        role="CONSTRUCTION_LINEAGE",
        target_record_id=_id("lineage-record"),
        source_dependencies=(_id("verification-record"),),
    )
    original = binding.binding_id
    object.__setattr__(binding, "occurrence_id", _id("foreign-occurrence"))
    with pytest.raises(
        authority.V075PortableConstructionPrivateReplayV2InvariantViolation,
        match="identity is stale",
    ):
        _ = binding.binding_id
    assert type(original) is str and len(original) == 64


def test_lifecycle_schema_registry_is_exact_and_rejects_old_name() -> None:
    assert authority._ROLE_SCHEMA["CONSTRUCTION_LIFECYCLE"] == (  # noqa: SLF001
        "acfqp.v075_batch_occurrence_lifecycle.v2"
    )
    with pytest.raises(
        authority.V075PortableConstructionPrivateReplayV2InvariantViolation,
        match="record binding is malformed",
    ):
        authority.V075ConstructionPrivateReplayRecordBindingV2(
            authority._RECORD_BINDING_ISSUER,  # noqa: SLF001
            _id("record"),
            0,
            "CONSTRUCTION_LIFECYCLE",
            "acfqp.v075_batch_occurrence_lifecycle_closure.v2",
            _id("semantic"),
            (),
            b"{}",
        )


def test_closure_verification_requires_exact_authoritative_type() -> None:
    source = inspect.getsource(
        authority.V075ConstructionPrivateReplayTypedGraphV2._validate
    )
    assert "type(self.closure_verification)" in source
    assert (
        "observer.V075ObserverBatchClosureVerificationV2" in source
    )
    annotation = inspect.get_annotations(
        authority.V075ConstructionPrivateReplayTypedGraphV2,
        eval_str=True,
    )["closure_verification"]
    assert (
        annotation
        is authority.observer.V075ObserverBatchClosureVerificationV2
    )


def test_no_secret_is_retained_or_hashed_by_this_authority() -> None:
    for cls in (
        authority.V075PortableConstructionPrivateReplayV2,
        authority.V075ConstructionPrivateReplayTypedGraphV2,
        authority.V075ConstructionPrivateReplaySourceBindingV2,
        authority.V075ConstructionPrivateReplayRecordBindingV2,
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
    source = inspect.getsource(authority)
    assert '"private_secret_digest_emitted": False' in source
    assert (
        '"private_values_directly_hashed_by_this_authority": False'
        in source
    )
    assert '"private_values_hashed": False' not in source


def test_only_legitimate_public_producers_are_called() -> None:
    tree = ast.parse(inspect.getsource(authority))
    calls = {
        ast.unparse(item.func)
        for item in ast.walk(tree)
        if isinstance(item, ast.Call)
    }
    assert (
        "lineage.freeze_v075_construction_batch_occurrence_lineage_v2"
        in calls
    )
    assert (
        "lifecycle.freeze_v075_construction_batch_occurrence_lifecycle_v2"
        in calls
    )
    assert (
        "lifecycle.verify_v075_batch_occurrence_lifecycle_bytes_v2"
        in calls
    )
    assert (
        "public_context.resolve_v075_portable_public_context_raw_dependencies_v2"
        in calls
    )
    assert not any("compile_v075" in item for item in calls)
    assert not any(
        "ISSUER" in item
        and (
            item.startswith("lineage.")
            or item.startswith("lifecycle.")
            or item.startswith("observer.")
            or item.startswith("generation.")
        )
        for item in calls
    )


def test_toctou_checks_and_transplant_identity_chain_are_explicit() -> None:
    replay_source = inspect.getsource(
        authority.replay_v075_portable_construction_private_replay_v2
    )
    assert replay_source.count("upstream._assert_current()") == 2
    result_source = inspect.getsource(
        authority.V075PortableConstructionPrivateReplayV2
        ._validate_structure
    )
    assert "is not self.typed_graph.hardened_planning_result" in result_source
    assert (
        "!= self.typed_graph.source_bindings" in result_source
    )


def test_all_production_science_and_certificate_locks_remain_closed() -> None:
    assert authority.CONSTRUCTION_EPHEMERAL_PRIVATE_INPUT_REQUIRED is True
    assert authority.PRIVATE_REPLAY_INPUTS_ACCEPTED is True
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
    assert authority.OPERATIONAL_REGISTRIES_ALLOWED is False
    assert authority.PLAN_CERTIFICATE_ISSUANCE_ALLOWED is False
    assert authority.INFEASIBILITY_CERTIFICATE_ISSUANCE_ALLOWED is False
