from __future__ import annotations

import ast
from dataclasses import dataclass, fields
import hashlib
import inspect
import pickle
from types import SimpleNamespace

import pytest

from acfqp import v075_portable_semantic_terminal_closure_v2 as authority


def _id(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _overlay(
    *,
    record_index: int = 0,
    role: str = "MULTIROUND_RESULT",
    scope: (
        authority.construction
        .V075ConstructionMultiroundResultAuthorityScopeV2
    ) = (
        authority.construction
        .V075ConstructionMultiroundResultAuthorityScopeV2
        .FULL_CONSTRUCTION_MULTIROUND_RESULT_REPLAY
    ),
) -> authority.V075PortableSemanticTerminalRecordOverlayV2:
    declaration = (
        authority.semantic.freeze_v075_portable_semantic_registry_v2()
        .by_role[role]
    )
    return authority.V075PortableSemanticTerminalRecordOverlayV2(
        authority._OVERLAY_ISSUER,  # noqa: SLF001
        _id("bundle"),
        _id("registry"),
        _id("static"),
        _id("old-set"),
        _id("manifest"),
        _id("replay"),
        _id("graph"),
        _id("dag"),
        declaration.declaration_id,
        _id(f"old:{record_index}"),
        declaration.semantic_replay_status,
        declaration.semantic_replay_status,
        record_index,
        _id(f"record:{record_index}"),
        role,
        declaration.artifact_schema,
        _id(f"semantic:{record_index}"),
        _id(f"artifact:{record_index}"),
        128,
        _id(f"node:{record_index}"),
        _id(f"source:{record_index}"),
        (
            authority.construction
            .V075ConstructionMultiroundResultResolverKindV2
            .CONSTRUCTION_MULTIROUND_RESULT_OWNER_REPLAY
        ),
        (),
        (),
        (),
        scope,
        1,
        (
            authority.V075PortableSemanticTerminalRoleStatusV2
            .FULL_TYPED_REPLAY
        ),
    )


def test_public_entry_currentness_and_byte_verifier_signatures() -> None:
    raw = (
        "repository_root",
        "portable_bundle_bytes",
        "public_context_closure_bytes",
        "private_generation_seed",
        "private_salt",
    )
    assert tuple(
        inspect.signature(
            authority.replay_v075_portable_semantic_terminal_closure_v2
        ).parameters
    ) == raw
    assert tuple(
        inspect.signature(
            authority.V075PortableSemanticTerminalClosureV2.assert_current
        ).parameters
    ) == ("self", *raw)
    assert tuple(
        inspect.signature(
            authority
            .verify_v075_portable_semantic_terminal_closure_bytes_v2
        ).parameters
    ) == ("closure_bytes", *raw)
    assert not hasattr(
        authority,
        "close_v075_portable_semantic_terminal_closure_v2",
    )


def test_raw_181_is_first_and_only_work_when_entry_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    def raw(**_kwargs):
        calls.append("1.81")
        raise RuntimeError("private marker")

    def forbidden(*_args, **_kwargs):
        calls.append("forbidden")
        raise AssertionError("work ran before raw 1.81")

    monkeypatch.setattr(
        authority.construction,
        "replay_v075_portable_construction_multiround_result_v2",
        raw,
    )
    monkeypatch.setattr(authority, "_close_after_raw_181", forbidden)
    with pytest.raises(
        authority.V075PortableSemanticTerminalClosureV2InvariantViolation
    ) as captured:
        authority.replay_v075_portable_semantic_terminal_closure_v2(
            repository_root=".",
            portable_bundle_bytes=b"bundle",
            public_context_closure_bytes=b"context",
            private_generation_seed=b"seed",
            private_salt=b"salt",
        )
    assert calls == ["1.81"]
    assert str(captured.value) == authority._REPLAY_MISMATCH  # noqa: SLF001
    assert captured.value.__cause__ is None
    assert "private marker" not in str(captured.value)


def test_byte_verifier_replays_raw_before_parsing_claim(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    def raw(**_kwargs):
        calls.append("1.81")
        raise RuntimeError("raw failure")

    def forbidden(*_args, **_kwargs):
        calls.append("parse")
        raise AssertionError("claimed bytes parsed before raw 1.81")

    monkeypatch.setattr(
        authority.construction,
        "replay_v075_portable_construction_multiround_result_v2",
        raw,
    )
    monkeypatch.setattr(authority, "_strict_document", forbidden)
    with pytest.raises(
        authority.V075PortableSemanticTerminalClosureV2InvariantViolation
    ):
        authority.verify_v075_portable_semantic_terminal_closure_bytes_v2(
            closure_bytes=b"not-json-and-must-not-be-read",
            repository_root=".",
            portable_bundle_bytes=b"bundle",
            public_context_closure_bytes=b"context",
            private_generation_seed=b"seed",
            private_salt=b"salt",
        )
    assert calls == ["1.81"]


def test_old_registry_remains_two_complete_roles_sixty_five_incomplete() -> None:
    registry = authority.semantic.freeze_v075_portable_semantic_registry_v2()
    complete = tuple(
        item.role
        for item in registry.declarations
        if item.semantic_replay_status
        is authority.semantic.V075PortableSemanticReplayStatusV2.COMPLETE
    )
    incomplete = tuple(
        item.role
        for item in registry.declarations
        if item.semantic_replay_status
        is authority.semantic.V075PortableSemanticReplayStatusV2.INCOMPLETE
    )
    assert complete == ("OCCURRENCE_IDENTITY", "SIGNED_BATCH_OUTCOME")
    assert len(incomplete) == 65
    assert registry.to_document()["semantic_registry_replay_complete"] is False
    source = inspect.getsource(authority)
    assert "semantic.freeze_v075_portable_semantic_registry_v2()" in source
    assert (
        "semantic.attest_v075_portable_occurrence_evidence_bundle_bytes_v2"
        in source
    )
    assert "semantic._REGISTRY_ISSUER" not in source
    assert "semantic._ATTESTATION_ISSUER" not in source


def test_record_overlay_preserves_legacy_status_lanes_and_scope() -> None:
    overlay = _overlay()
    document = overlay.to_document()
    assert document["status"] == "FULL_TYPED_REPLAY"
    assert document["legacy_declaration_replay_status"] == "INCOMPLETE"
    assert document["legacy_attestation_replay_status"] == "INCOMPLETE"
    assert document["legacy_semantic_replay_status_relabelled"] is False
    assert document["effective_lane_is_exact_union"] is True
    assert document["authority_scope"] == (
        "FULL_CONSTRUCTION_MULTIROUND_RESULT_REPLAY"
    )
    assert document["static_surface_used_as_artifact_semantic_evidence"] is False
    object.__setattr__(
        overlay,
        "authority_scope",
        (
            authority.construction
            .V075ConstructionMultiroundResultAuthorityScopeV2
            .FULL_PUBLIC
        ),
    )
    with pytest.raises(
        authority.V075PortableSemanticTerminalClosureV2InvariantViolation,
        match="identity is stale",
    ):
        _ = overlay.overlay_id


def test_present_and_absent_role_closures_bind_exact_evidence() -> None:
    registry = authority.semantic.freeze_v075_portable_semantic_registry_v2()
    present_overlay = _overlay()
    present_declaration = registry.by_role[present_overlay.role]
    present = authority.V075PortableSemanticTerminalRoleClosureV2(
        authority._ROLE_CLOSURE_ISSUER,  # noqa: SLF001
        present_overlay.portable_bundle_id,
        present_overlay.semantic_registry_id,
        present_declaration.declaration_id,
        present_declaration.ordinal,
        present_declaration.role,
        present_declaration.artifact_schema,
        authority.V075PortableSemanticTerminalRoleStatusV2.FULL_TYPED_REPLAY,
        (present_overlay.record_id,),
        (present_overlay.overlay_id,),
        (present_overlay.old_attestation_id,),
        (present_overlay.dependency_node_sha256,),
        ((present_overlay.record_id, present_overlay.authority_scope.value),),
        None,
    )
    assert present.to_document()["absence_evidence_registry_id"]["kind"] == (
        "NOT_APPLICABLE"
    )
    absent_declaration = registry.by_role[
        authority.construction.ROOT_ONLY_EMPTY_ROLE_ORDER[0]
    ]
    empty_registry_id = _id("empty-registry")
    absent = authority.V075PortableSemanticTerminalRoleClosureV2(
        authority._ROLE_CLOSURE_ISSUER,  # noqa: SLF001
        _id("bundle"),
        _id("registry"),
        absent_declaration.declaration_id,
        absent_declaration.ordinal,
        absent_declaration.role,
        absent_declaration.artifact_schema,
        (
            authority.V075PortableSemanticTerminalRoleStatusV2
            .NOT_PRESENT_IN_VERIFIED_OCCURRENCE
        ),
        (),
        (),
        (),
        (),
        (),
        empty_registry_id,
    )
    assert absent.to_document()["absence_evidence_registry_id"] == (
        empty_registry_id
    )
    with pytest.raises(
        authority.V075PortableSemanticTerminalClosureV2InvariantViolation,
        match="malformed",
    ):
        authority.V075PortableSemanticTerminalRoleClosureV2(
            authority._ROLE_CLOSURE_ISSUER,  # noqa: SLF001
            _id("bundle"),
            _id("registry"),
            absent_declaration.declaration_id,
            absent_declaration.ordinal,
            absent_declaration.role,
            absent_declaration.artifact_schema,
            (
                authority.V075PortableSemanticTerminalRoleStatusV2
                .NOT_PRESENT_IN_VERIFIED_OCCURRENCE
            ),
            (),
            (),
            (),
            (),
            (),
            None,
        )


@dataclass(frozen=True)
class _Record:
    index: int
    record_id: str
    role: str


@dataclass(frozen=True)
class _Node:
    record_index: int
    record_id: str
    role: str
    portable_declared_dependency_record_ids: tuple[str, ...]
    authority_local_semantic_dependency_record_ids: tuple[str, ...]
    effective_dependency_record_ids: tuple[str, ...]
    local_semantic_authority_resolved: bool
    semantically_resolved: bool
    authority_scope: object
    unresolved_frontier_record_ids: tuple[str, ...]
    unresolved_frontier_roles: tuple[str, ...]


def _dag_pair() -> tuple[tuple[_Record, ...], tuple[_Node, ...]]:
    first_id = _id("first")
    second_id = _id("second")
    scope = (
        authority.construction
        .V075ConstructionMultiroundResultAuthorityScopeV2.FULL_PUBLIC
    )
    return (
        (
            _Record(0, first_id, "OCCURRENCE_IDENTITY"),
            _Record(1, second_id, "SIGNED_BATCH_OUTCOME"),
        ),
        (
            _Node(0, first_id, "OCCURRENCE_IDENTITY", (), (), (), True, True, scope, (), ()),
            _Node(
                1,
                second_id,
                "SIGNED_BATCH_OUTCOME",
                (first_id,),
                (),
                (first_id,),
                True,
                True,
                scope,
                (),
                (),
            ),
        ),
    )


def test_exact_record_dag_bijection_lanes_cycle_and_cap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        authority.portable,
        "V075PortableEvidenceArtifactRecordV2",
        _Record,
    )
    monkeypatch.setattr(
        authority.construction,
        "V075ConstructionMultiroundResultDependencyNodeV2",
        _Node,
    )
    records, nodes = _dag_pair()
    authority._validate_exact_resolved_dag(  # noqa: SLF001
        records=records,
        nodes=nodes,
    )
    corrupted = (
        nodes[0],
        _Node(
            nodes[1].record_index,
            nodes[1].record_id,
            nodes[1].role,
            nodes[1].portable_declared_dependency_record_ids,
            (),
            (),
            True,
            True,
            nodes[1].authority_scope,
            (),
            (),
        ),
    )
    with pytest.raises(
        authority.V075PortableSemanticTerminalClosureV2InvariantViolation,
        match="exact resolved typed DAG node",
    ):
        authority._validate_exact_resolved_dag(  # noqa: SLF001
            records=records,
            nodes=corrupted,
        )
    cycled = (
        _Node(
            0,
            nodes[0].record_id,
            nodes[0].role,
            (nodes[1].record_id,),
            (),
            (nodes[1].record_id,),
            True,
            True,
            nodes[0].authority_scope,
            (),
            (),
        ),
        nodes[1],
    )
    with pytest.raises(
        authority.V075PortableSemanticTerminalClosureV2InvariantViolation,
        match="cyclic",
    ):
        authority._validate_exact_resolved_dag(  # noqa: SLF001
            records=records,
            nodes=cycled,
        )
    oversized_records = (records[0],) * (
        authority.MAX_DEPENDENCY_NODES + 1
    )
    oversized_nodes = (nodes[0],) * (
        authority.MAX_DEPENDENCY_NODES + 1
    )
    with pytest.raises(
        authority.V075PortableSemanticTerminalClosureV2InvariantViolation,
        match="bounded exact DAG",
    ):
        authority._validate_exact_resolved_dag(  # noqa: SLF001
            records=oversized_records,
            nodes=oversized_nodes,
        )


def test_absent_partition_is_bound_to_fresh_181_empty_registry() -> None:
    source = inspect.getsource(authority._verify_fresh_inputs)  # noqa: SLF001
    assert "replayed.typed_graph.empty_role_registry" in source
    assert "empty_registry.roles != construction.ROOT_ONLY_EMPTY_ROLE_ORDER" in (
        source
    )
    assert "absent_roles != construction.ROOT_ONLY_EMPTY_ROLE_ORDER" in source
    assert "role_counts" in source
    assert len(authority.construction.ROOT_ONLY_EMPTY_ROLE_ORDER) == 18


def test_scope_histogram_includes_native_zero_and_sums_records() -> None:
    scopes = (
        authority.construction
        .V075ConstructionMultiroundResultAuthorityScopeV2
    )
    fake = SimpleNamespace(
        record_overlays=(
            SimpleNamespace(authority_scope=scopes.FULL_PUBLIC),
            SimpleNamespace(
                authority_scope=(
                    scopes.FULL_CONSTRUCTION_MULTIROUND_RESULT_REPLAY
                )
            ),
        )
    )
    histogram = dict(
        authority.V075PortableSemanticTerminalClosureV2
        ._scope_histogram(fake)
    )
    assert set(histogram) == {
        item.value for item in scopes if item is not scopes.UNRESOLVED
    }
    assert histogram[scopes.FULL_PUBLIC.value] == 1
    assert (
        histogram[
            scopes.FULL_CONSTRUCTION_MULTIROUND_RESULT_REPLAY.value
        ]
        == 1
    )
    assert sum(histogram.values()) == 2
    assert 0 in histogram.values()


def test_currentness_uses_only_five_raw_inputs_and_detects_change(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = {"terminal_closure_id": _id("original")}
    fake_self = SimpleNamespace(to_document=lambda: original)
    calls: list[dict[str, object]] = []

    def replayed(**kwargs: object) -> SimpleNamespace:
        calls.append(kwargs)
        return SimpleNamespace(to_document=lambda: dict(original))

    monkeypatch.setattr(
        authority,
        "replay_v075_portable_semantic_terminal_closure_v2",
        replayed,
    )
    kwargs = {
        "repository_root": ".",
        "portable_bundle_bytes": b"bundle",
        "public_context_closure_bytes": b"context",
        "private_generation_seed": b"seed",
        "private_salt": b"salt",
    }
    authority.V075PortableSemanticTerminalClosureV2.assert_current(
        fake_self,
        **kwargs,
    )
    assert calls == [kwargs]
    monkeypatch.setattr(
        authority,
        "replay_v075_portable_semantic_terminal_closure_v2",
        lambda **_kwargs: SimpleNamespace(
            to_document=lambda: {"terminal_closure_id": _id("changed")}
        ),
    )
    with pytest.raises(
        authority.V075PortableSemanticTerminalClosureV2InvariantViolation,
        match="currentness check changed",
    ):
        authority.V075PortableSemanticTerminalClosureV2.assert_current(
            fake_self,
            **kwargs,
        )


def test_secret_pickle_and_all_nonconstruction_gates_remain_locked() -> None:
    for cls in (
        authority.V075PortableSemanticTerminalRecordOverlayV2,
        authority.V075PortableSemanticTerminalRoleClosureV2,
        authority.V075PortableSemanticTerminalClosureV2,
    ):
        names = {item.name for item in fields(cls)}
        assert "private_generation_seed" not in names
        assert "private_salt" not in names
        assert "private_environment" not in names
        assert "__reduce__" in cls.__dict__
    with pytest.raises(TypeError, match="in-memory-only"):
        pickle.dumps(_overlay())
    true_flags = {
        name
        for name, value in vars(authority).items()
        if name.isupper() and type(value) is bool and value
    }
    assert true_flags == {
        "CONSTRUCTION_SEMANTIC_TERMINAL_OVERLAY_COMPLETE",
        "CONSTRUCTION_PRESENT_RECORD_TYPED_REPLAY_COMPLETE",
        "CONSTRUCTION_DECLARED_ROLE_CLOSURE_COMPLETE",
        "CONSTRUCTION_PORTABLE_SEMANTIC_REGISTRY_COMPLETE",
        "CONSTRUCTION_DEPENDENCY_AWARE_TYPED_OBJECT_REPLAY_COMPLETE",
        "CONSTRUCTION_COMPLETE_OCCURRENCE_BUNDLE_SEMANTIC_REPLAY_COMPLETE",
    }
    for name in (
        "OFFICIAL_EXECUTION_ALLOWED",
        "PRODUCTION_AUTHORIZING",
        "SCIENTIFIC_ENDPOINT_CREDIT_ALLOWED",
        "FRESH_HELDOUT_ACCESS_ALLOWED",
        "SOURCE_AUTHORITY_COMPLETE",
        "CODE_PROVENANCE_COMPLETE",
        "ACCOUNTING_GATE_PASSED",
        "SEMANTIC_REGISTRY_REPLAY_COMPLETE",
        "DEPENDENCY_AWARE_TYPED_OBJECT_REPLAY_COMPLETE",
        "COMPLETE_OCCURRENCE_BUNDLE_SEMANTIC_REPLAY_COMPLETE",
        "PLAN_CERTIFICATE_ISSUANCE_ALLOWED",
        "INFEASIBILITY_CERTIFICATE_ISSUANCE_ALLOWED",
    ):
        assert getattr(authority, name) is False
