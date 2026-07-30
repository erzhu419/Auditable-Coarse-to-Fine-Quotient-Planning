from __future__ import annotations

from dataclasses import dataclass
import ast
import hashlib
import inspect
from pathlib import Path
import pickle
from types import SimpleNamespace

import pytest

from acfqp.phase3e_ids import canonical_json_bytes
from acfqp import v075_portable_planning_authority_v2 as authority


def _id(label: str) -> str:
    return hashlib.sha256(
        b"acfqp:v075-portable-planning-test:v2\x00" + label.encode()
    ).hexdigest()


def _portable_record(
    *,
    role: str,
    schema: str,
    semantic_id: str,
    id_field: str,
    index: int,
    dependencies: tuple[str, ...] = (),
    document: dict | None = None,
):
    raw = canonical_json_bytes(
        (
            {"schema": schema, id_field: semantic_id}
            if document is None
            else document
        )
    )
    domain = authority.portable._record_domain(role)  # noqa: SLF001
    payload = {
        "schema": "acfqp.v075_portable_evidence_artifact_record.v2",
        "schema_version": authority.portable.SCHEMA_VERSION,
        "profile_key": authority.portable.PROFILE_KEY,
        "index": index,
        "role": role,
        "artifact_schema": schema,
        "artifact_domain_tag": domain,
        "semantic_artifact_id": semantic_id,
        "dependency_record_ids": list(dependencies),
        "canonical_artifact_bytes_hex": raw.hex(),
        "raw_bytes_complete": True,
        "private_material_serialized": False,
        "official_execution_allowed": False,
    }
    return SimpleNamespace(
        record_id=authority.portable._hash(domain, payload),  # noqa: SLF001
        index=index,
        role=role,
        artifact_schema=schema,
        semantic_artifact_id=semantic_id,
        dependency_record_ids=dependencies,
        canonical_artifact_bytes=raw,
    )


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
    unresolved_frontier_record_ids: tuple[str, ...]
    dependency_depth: int


def _node(
    label: str,
    index: int,
    role: str,
    portable: tuple[str, ...] = (),
    semantic: tuple[str, ...] = (),
    *,
    local: bool = True,
    resolved: bool = True,
    frontier: tuple[str, ...] = (),
) -> _UpstreamNode:
    portable = tuple(sorted(portable))
    semantic = tuple(sorted(semantic))
    return _UpstreamNode(
        _id(label),
        index,
        role,
        portable,
        semantic,
        tuple(sorted(set(portable) | set(semantic))),
        local,
        resolved,
        tuple(sorted(frontier)),
        index + 1,
    )


def _source_binding(
    *,
    target: _UpstreamNode,
    target_role: str,
    dependencies: tuple[str, ...],
    label: str,
) -> authority.V075PortablePlanningSourceBindingV2:
    return authority.V075PortablePlanningSourceBindingV2(
        authority._SOURCE_BINDING_ISSUER,  # noqa: SLF001
        target.record_id,
        target_role,
        _id(f"{label}-semantic"),
        _id("occurrence"),
        _id("context"),
        (_id(f"{label}-epoch"),),
        ("ADAPTIVE_QUOTIENT",),
        tuple(sorted(dependencies)),
        (("witness", _id(f"{label}-witness")),),
    )


def _propagation_fixture():
    occurrence = _node("occ-record", 0, "OCCURRENCE_IDENTITY")
    row = _node("row-record", 1, "LIVE_ROW_SOURCE_BINDING")
    prefix = _node(
        "prefix-record",
        2,
        "OPEN_CONTROLLED_PREFIX_VERIFICATION",
    )
    model = _node(
        "model-record",
        3,
        "NUMERICAL_MODEL",
        local=False,
        resolved=False,
        frontier=(_id("model-record"),),
    )
    proof = _node(
        "proof-record",
        4,
        "NUMERICAL_PLANNING_PROOF",
        portable=(model.record_id,),
        local=False,
        resolved=False,
        frontier=(_id("proof-record"),),
    )
    epoch = _node(
        "epoch-record",
        5,
        "LIVE_MODEL_EPOCH",
        portable=(row.record_id, model.record_id, proof.record_id),
        resolved=False,
        frontier=(model.record_id, proof.record_id),
    )
    edge = _node(
        "edge-record",
        6,
        "DYNAMIC_CHILD_CAUSAL_EDGE",
        semantic=(epoch.record_id, model.record_id, proof.record_id),
        resolved=False,
        frontier=(model.record_id, proof.record_id),
    )
    state = _node(
        "state-record",
        7,
        "DYNAMIC_CHILD_STATE",
        portable=(edge.record_id,),
        semantic=(epoch.record_id, model.record_id, proof.record_id),
        resolved=False,
        frontier=(model.record_id, proof.record_id),
    )
    closure = _node(
        "closure-record",
        8,
        "DYNAMIC_CHILD_CLOSURE",
        portable=(state.record_id,),
        semantic=(epoch.record_id, model.record_id, proof.record_id),
        resolved=False,
        frontier=(model.record_id, proof.record_id),
    )
    verification = _node(
        "verification-record",
        9,
        "DYNAMIC_CHILD_CLOSURE_VERIFICATION",
        semantic=(epoch.record_id, model.record_id, proof.record_id),
        resolved=False,
        frontier=(model.record_id, proof.record_id),
    )
    planning_input = _node(
        "input-record",
        10,
        "CONSTRUCTION_PLANNING_INPUT",
        portable=(model.record_id,),
        local=False,
        resolved=False,
        frontier=(_id("input-record"),),
    )
    nodes = (
        occurrence,
        row,
        prefix,
        model,
        proof,
        epoch,
        edge,
        state,
        closure,
        verification,
        planning_input,
    )
    bindings = (
        _source_binding(
            target=model,
            target_role="NUMERICAL_MODEL",
            dependencies=(
                occurrence.record_id,
                row.record_id,
                prefix.record_id,
            ),
            label="model",
        ),
        _source_binding(
            target=proof,
            target_role="NUMERICAL_PLANNING_PROOF",
            dependencies=(occurrence.record_id, model.record_id),
            label="proof",
        ),
    )
    return nodes, bindings


def test_contract_scope_role_order_and_all_locks_remain_closed() -> None:
    assert authority.PROPOSED_CONTRACT_VERSION == "1.77.0"
    assert authority.ROLE_ORDER == (
        "NUMERICAL_MODEL",
        "NUMERICAL_PLANNING_PROOF",
        "CONSTRUCTION_PLANNING_INPUT",
    )
    assert authority.PROPAGATED_ROLE_ORDER == (
        "LIVE_MODEL_EPOCH",
        "DYNAMIC_CHILD_CAUSAL_EDGE",
        "DYNAMIC_CHILD_STATE",
        "DYNAMIC_CHILD_CLOSURE",
        "DYNAMIC_CHILD_CLOSURE_VERIFICATION",
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
        "KERNEL_ACCESS_ALLOWED",
        "J0_ACCESS_ALLOWED",
        "SIGNER_INPUT_ALLOWED",
        "OBSERVER_ACCESS_ALLOWED",
        "OBSERVER_INPUT_ALLOWED",
        "WORKER_ACCESS_ALLOWED",
        "WORKER_INPUT_ALLOWED",
        "PLAN_CERTIFICATE_ISSUANCE_ALLOWED",
        "INFEASIBILITY_CERTIFICATE_ISSUANCE_ALLOWED",
    ):
        assert getattr(authority, name) is False
        assert name in authority.__all__
    assert "DOMAIN_TAGS" in authority.__all__


def test_entry_is_raw_only_and_hardened_176_runs_first(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert tuple(
        inspect.signature(
            authority.replay_v075_portable_planning_authority_v2
        ).parameters
    ) == (
        "repository_root",
        "portable_bundle_bytes",
        "public_context_closure_bytes",
    )
    calls: list[str] = []

    def stop_at_upstream(**_kwargs):
        calls.append("1.76")
        raise RuntimeError("sentinel")

    def forbidden_bundle(*_args, **_kwargs):
        calls.append("bundle")
        raise AssertionError("bundle replay ran before hardened 1.76")

    monkeypatch.setattr(
        authority.m2_child,
        "replay_v075_portable_dynamic_child_proposal_v2",
        stop_at_upstream,
    )
    monkeypatch.setattr(
        authority.portable,
        "verify_v075_portable_occurrence_evidence_bundle_bytes_v2",
        forbidden_bundle,
    )
    with pytest.raises(
        authority.V075PortablePlanningV2InvariantViolation,
        match="hardened 1.76 replay failed",
    ):
        authority.replay_v075_portable_planning_authority_v2(
            repository_root=Path("."),
            portable_bundle_bytes=b"bundle",
            public_context_closure_bytes=b"context",
        )
    assert calls == ["1.76"]


def test_public_entry_wires_the_complete_model_proof_pipeline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    upstream = SimpleNamespace(
        bundle_id=_id("bundle"),
        occurrence_id=_id("occurrence"),
        public_context_closure_id=_id("context"),
        dependency_dag=SimpleNamespace(nodes=("upstream",)),
    )
    bundle = SimpleNamespace(
        bundle_id=upstream.bundle_id,
        occurrence_id=upstream.occurrence_id,
        records=(
            SimpleNamespace(role="NUMERICAL_MODEL"),
            SimpleNamespace(role="NUMERICAL_PLANNING_PROOF"),
            SimpleNamespace(role="CONSTRUCTION_PLANNING_INPUT"),
        ),
    )
    target_bindings = iter(("model-record", "proof-record", "input-record"))
    epochs = ("epoch",)
    models = ("model",)
    proofs = ("proof",)
    sources = ("source",)
    source_bindings = ("source-binding",)
    typed = SimpleNamespace(_graph_id=_id("typed"))
    nodes = ("node",)
    dag = SimpleNamespace(_dag_id=_id("dag"))
    attestations = ("attestation",)
    closures = ("closure",)
    propagated = ("propagated",)
    expected = SimpleNamespace(canonical_bytes=b"result")

    monkeypatch.setattr(
        authority.m2_child,
        "replay_v075_portable_dynamic_child_proposal_v2",
        lambda **_kwargs: calls.append("1.76") or upstream,
    )
    monkeypatch.setattr(
        authority.portable,
        "verify_v075_portable_occurrence_evidence_bundle_bytes_v2",
        lambda _raw: calls.append("bundle") or bundle,
    )
    monkeypatch.setattr(
        authority,
        "_binding_from_record",
        lambda _record: calls.append("record") or next(target_bindings),
    )
    monkeypatch.setattr(
        authority,
        "_epochs",
        lambda *_args, **_kwargs: calls.append("epochs") or epochs,
    )
    monkeypatch.setattr(
        authority,
        "_replay_numerical_registry",
        lambda *_args, **_kwargs: (
            calls.append("producer") or (models, proofs)
        ),
    )
    monkeypatch.setattr(
        authority,
        "_validate_target_registry",
        lambda **_kwargs: calls.append("registry"),
    )
    monkeypatch.setattr(
        authority,
        "_required_source_records",
        lambda **_kwargs: calls.append("sources") or sources,
    )
    monkeypatch.setattr(
        authority,
        "_build_source_bindings",
        lambda **_kwargs: calls.append("bindings") or source_bindings,
    )
    monkeypatch.setattr(
        authority,
        "V075PortablePlanningTypedGraphV2",
        lambda *_args: calls.append("typed") or typed,
    )
    monkeypatch.setattr(
        authority,
        "_iterative_planning_dependency_nodes",
        lambda **_kwargs: calls.append("nodes") or nodes,
    )
    monkeypatch.setattr(
        authority,
        "V075PortablePlanningDependencyDAGV2",
        lambda *_args: calls.append("dag") or dag,
    )
    monkeypatch.setattr(
        authority,
        "_build_attestations",
        lambda **_kwargs: calls.append("attestations") or attestations,
    )
    monkeypatch.setattr(
        authority,
        "_build_role_closures",
        lambda **_kwargs: calls.append("closures") or closures,
    )
    monkeypatch.setattr(
        authority,
        "_build_propagated_role_closures",
        lambda **_kwargs: calls.append("propagated") or propagated,
    )
    monkeypatch.setattr(
        authority,
        "V075PortablePlanningReplayV2",
        lambda *_args: calls.append("result") or expected,
    )
    actual = authority.replay_v075_portable_planning_authority_v2(
        repository_root=Path("."),
        portable_bundle_bytes=b"bundle",
        public_context_closure_bytes=b"context",
    )
    assert actual is expected
    assert calls == [
        "1.76",
        "bundle",
        "record",
        "record",
        "record",
        "epochs",
        "producer",
        "registry",
        "sources",
        "bindings",
        "typed",
        "nodes",
        "dag",
        "attestations",
        "closures",
        "propagated",
        "result",
    ]


def test_all_epoch_proofs_are_rerun_through_public_exact_planner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Artifact:
        def __init__(self, identity: str, key: str):
            setattr(self, key, identity)
            self.identity = identity

        def to_document(self):
            return {"identity": self.identity}

    model_a = Artifact(_id("model-a"), "model_id")
    model_b = Artifact(_id("model-b"), "model_id")
    proof_a = Artifact(_id("proof-a"), "proof_id")
    proof_b = Artifact(_id("proof-b"), "proof_id")
    proof_a.model = model_a
    proof_b.model = model_b
    epochs = (
        SimpleNamespace(
            model=model_a,
            proof=proof_a,
            route=SimpleNamespace(value="ADAPTIVE_QUOTIENT"),
        ),
        SimpleNamespace(
            model=model_b,
            proof=proof_b,
            route=SimpleNamespace(value="MATCHED_DIRECT_GROUND"),
        ),
    )
    calls = []
    monkeypatch.setattr(
        authority,
        "_epochs",
        lambda *_args, **_kwargs: epochs,
    )

    def planner(*, model, route):
        calls.append((model, route))
        return proof_a if model is model_a else proof_b

    monkeypatch.setattr(
        authority.planning,
        "plan_v075_construction_numerical_model_v2",
        planner,
    )
    models, proofs = authority._replay_numerical_registry(  # noqa: SLF001
        object()
    )
    assert {item.model_id for item in models} == {
        model_a.model_id,
        model_b.model_id,
    }
    assert {item.proof_id for item in proofs} == {
        proof_a.proof_id,
        proof_b.proof_id,
    }
    assert calls == [
        (model_a, epochs[0].route),
        (model_b, epochs[1].route),
    ]


def test_public_planner_mismatch_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    model = SimpleNamespace(
        model_id=_id("model"),
        to_document=lambda: {"value": "model"},
    )
    claimed = SimpleNamespace(
        proof_id=_id("proof"),
        model=model,
        to_document=lambda: {"value": "claimed"},
    )
    replayed = SimpleNamespace(
        proof_id=claimed.proof_id,
        model=model,
        to_document=lambda: {"value": "mutated"},
    )
    epoch = SimpleNamespace(
        model=model,
        proof=claimed,
        route=object(),
    )
    monkeypatch.setattr(
        authority,
        "_epochs",
        lambda *_args, **_kwargs: (epoch,),
    )
    monkeypatch.setattr(
        authority.planning,
        "plan_v075_construction_numerical_model_v2",
        lambda **_kwargs: replayed,
    )
    with pytest.raises(
        authority.V075PortablePlanningV2InvariantViolation,
        match="differs from exact replay",
    ):
        authority._replay_numerical_registry(object())  # noqa: SLF001


@pytest.mark.parametrize("role", authority.ROLE_ORDER)
def test_role_schema_id_and_stale_record_are_rejected(role: str) -> None:
    exact = _portable_record(
        role=role,
        schema=authority._ROLE_SCHEMA[role],  # noqa: SLF001
        semantic_id=_id(role),
        id_field=authority._ROLE_ID_FIELD[role],  # noqa: SLF001
        index=0,
    )
    binding = authority._binding_from_record(exact)  # noqa: SLF001
    assert binding.role == role
    object.__setattr__(binding, "semantic_artifact_id", _id("mutated"))
    with pytest.raises(
        authority.V075PortablePlanningV2InvariantViolation
    ):
        binding._assert_current()  # noqa: SLF001


def test_model_and_proof_close_then_propagate_without_closing_input() -> None:
    upstream, bindings = _propagation_fixture()
    result = authority._iterative_planning_dependency_nodes(  # noqa: SLF001
        upstream_nodes=upstream,
        source_bindings=bindings,
    )
    by_role = {item.role: item for item in result}
    assert by_role["NUMERICAL_MODEL"].semantically_resolved
    assert by_role["NUMERICAL_PLANNING_PROOF"].semantically_resolved
    for role in authority.PROPAGATED_ROLE_ORDER:
        assert by_role[role].semantically_resolved
        assert by_role[role].unresolved_frontier_record_ids == ()
    planning_input = by_role["CONSTRUCTION_PLANNING_INPUT"]
    assert not planning_input.local_semantic_authority_resolved
    assert not planning_input.semantically_resolved
    assert planning_input.unresolved_frontier_record_ids == (
        planning_input.record_id,
    )
    proof = by_role["NUMERICAL_PLANNING_PROOF"]
    model_id = by_role["NUMERICAL_MODEL"].record_id
    assert model_id in proof.portable_declared_dependency_record_ids
    assert model_id in proof.authority_local_semantic_dependency_record_ids
    assert proof.effective_dependency_record_ids.count(model_id) == 1


def test_duplicate_target_semantic_id_is_not_collapsed_by_a_dict() -> None:
    model_id = _id("duplicate-model")
    proof_id = _id("proof")
    input_id = _id("input")

    class Artifact:
        def __init__(self, identity: str, key: str, schema: str):
            setattr(self, key, identity)
            self.document = {"schema": schema, key: identity}

        def to_document(self):
            return self.document

    model = Artifact(
        model_id,
        "model_id",
        authority._ROLE_SCHEMA["NUMERICAL_MODEL"],  # noqa: SLF001
    )
    proof = Artifact(
        proof_id,
        "proof_id",
        authority._ROLE_SCHEMA["NUMERICAL_PLANNING_PROOF"],  # noqa: SLF001
    )
    records = (
        _portable_record(
            role="NUMERICAL_MODEL",
            schema=authority._ROLE_SCHEMA["NUMERICAL_MODEL"],  # noqa: SLF001
            semantic_id=model_id,
            id_field="model_id",
            index=0,
            document=model.to_document(),
        ),
        _portable_record(
            role="NUMERICAL_MODEL",
            schema=authority._ROLE_SCHEMA["NUMERICAL_MODEL"],  # noqa: SLF001
            semantic_id=model_id,
            id_field="model_id",
            index=1,
            document=model.to_document(),
        ),
        _portable_record(
            role="NUMERICAL_PLANNING_PROOF",
            schema=authority._ROLE_SCHEMA["NUMERICAL_PLANNING_PROOF"],  # noqa: SLF001
            semantic_id=proof_id,
            id_field="proof_id",
            index=2,
            document=proof.to_document(),
        ),
        _portable_record(
            role="CONSTRUCTION_PLANNING_INPUT",
            schema=authority._ROLE_SCHEMA[  # noqa: SLF001
                "CONSTRUCTION_PLANNING_INPUT"
            ],
            semantic_id=input_id,
            id_field="input_id",
            index=3,
            document={
                "schema": authority._ROLE_SCHEMA[  # noqa: SLF001
                    "CONSTRUCTION_PLANNING_INPUT"
                ],
                "input_id": input_id,
                "numerical_model_id": model_id,
            },
        ),
    )
    bindings = tuple(
        authority._binding_from_record(item)  # noqa: SLF001
        for item in records
    )
    epoch = SimpleNamespace(
        epoch_index=1,
        model=SimpleNamespace(model_id=model_id),
    )
    with pytest.raises(
        authority.V075PortablePlanningV2InvariantViolation,
        match="duplicates one semantic artifact",
    ):
        authority._validate_target_registry(  # noqa: SLF001
            target_bindings=bindings,
            models=(model,),
            proofs=(proof,),
            epochs=(epoch,),
        )


def test_target_registry_rejects_stale_record_dependency_lane() -> None:
    records = tuple(
        _portable_record(
            role=role,
            schema=authority._ROLE_SCHEMA[role],  # noqa: SLF001
            semantic_id=_id(role),
            id_field=authority._ROLE_ID_FIELD[role],  # noqa: SLF001
            index=index,
        )
        for index, role in enumerate(authority.ROLE_ORDER)
    )
    bindings = tuple(
        authority._binding_from_record(item)  # noqa: SLF001
        for item in records
    )
    object.__setattr__(
        bindings[0],
        "dependency_record_ids",
        (_id("foreign-dependency"),),
    )
    with pytest.raises(
        authority.V075PortablePlanningV2InvariantViolation,
        match="stale or rehashed",
    ):
        authority._validate_target_registry(  # noqa: SLF001
            target_bindings=bindings,
            models=(),
            proofs=(),
            epochs=(),
        )


def test_model_reverse_epoch_edge_is_rejected() -> None:
    upstream, bindings = _propagation_fixture()
    epoch = next(item for item in upstream if item.role == "LIVE_MODEL_EPOCH")
    model = next(item for item in upstream if item.role == "NUMERICAL_MODEL")
    bad_model = _source_binding(
        target=model,
        target_role="NUMERICAL_MODEL",
        dependencies=(epoch.record_id,),
        label="bad-model",
    )
    with pytest.raises(
        authority.V075PortablePlanningV2InvariantViolation,
        match="forbidden reverse source edge",
    ):
        authority._iterative_planning_dependency_nodes(  # noqa: SLF001
            upstream_nodes=upstream,
            source_bindings=(bad_model, bindings[1]),
        )


def test_unsorted_inherited_effective_lane_is_rejected() -> None:
    first = _node("first", 0, "FIRST")
    second = _node("second", 1, "SECOND")
    third = _node(
        "third",
        2,
        "THIRD",
        portable=(first.record_id,),
        semantic=(second.record_id,),
    )
    malformed = SimpleNamespace(
        record_id=third.record_id,
        record_index=third.record_index,
        role=third.role,
        portable_declared_dependency_record_ids=(
            third.portable_declared_dependency_record_ids
        ),
        authority_local_semantic_dependency_record_ids=(
            third.authority_local_semantic_dependency_record_ids
        ),
        effective_dependency_record_ids=(
            second.record_id,
            first.record_id,
        ),
        local_semantic_authority_resolved=True,
        semantically_resolved=True,
        unresolved_frontier_record_ids=(),
        dependency_depth=3,
    )
    with pytest.raises(
        authority.V075PortablePlanningV2InvariantViolation,
        match="upstream DAG",
    ):
        authority._iterative_planning_dependency_nodes(  # noqa: SLF001
            upstream_nodes=(first, second, malformed),
            source_bindings=(),
        )


def test_iterative_kahn_supports_4096_nodes_without_recursion() -> None:
    nodes = []
    previous = None
    for index in range(authority.MAX_DEPENDENCY_NODES):
        current = _node(
            f"chain-{index}",
            index,
            "CHAIN_NODE",
            portable=() if previous is None else (previous,),
        )
        nodes.append(current)
        previous = current.record_id
    replayed = authority._iterative_planning_dependency_nodes(  # noqa: SLF001
        upstream_nodes=tuple(nodes),
        source_bindings=(),
    )
    assert len(replayed) == authority.MAX_DEPENDENCY_NODES
    assert replayed[-1].dependency_depth == authority.MAX_DEPENDENCY_NODES


def test_dependency_replay_rejects_cycle_and_4097_nodes() -> None:
    first_id = _id("cycle-first")
    second_id = _id("cycle-second")
    first = _UpstreamNode(
        first_id,
        0,
        "CYCLE",
        (second_id,),
        (),
        (second_id,),
        True,
        True,
        (),
        1,
    )
    second = _UpstreamNode(
        second_id,
        1,
        "CYCLE",
        (first_id,),
        (),
        (first_id,),
        True,
        True,
        (),
        1,
    )
    with pytest.raises(
        authority.V075PortablePlanningV2InvariantViolation,
        match="contains a cycle",
    ):
        authority._iterative_planning_dependency_nodes(  # noqa: SLF001
            upstream_nodes=(first, second),
            source_bindings=(),
        )

    over_cap = tuple(
        _node(f"over-cap-{index}", index, "ROOT")
        for index in range(authority.MAX_DEPENDENCY_NODES + 1)
    )
    with pytest.raises(
        authority.V075PortablePlanningV2InvariantViolation,
        match="bounded nonempty DAG",
    ):
        authority._iterative_planning_dependency_nodes(  # noqa: SLF001
            upstream_nodes=over_cap,
            source_bindings=(),
        )


def test_dependency_replay_is_deterministic() -> None:
    upstream, bindings = _propagation_fixture()
    first = authority._iterative_planning_dependency_nodes(  # noqa: SLF001
        upstream_nodes=upstream,
        source_bindings=bindings,
    )
    second = authority._iterative_planning_dependency_nodes(  # noqa: SLF001
        upstream_nodes=upstream,
        source_bindings=bindings,
    )
    assert tuple(item.to_document() for item in first) == tuple(
        item.to_document() for item in second
    )


def test_source_binding_is_content_addressed_and_caller_mint_is_rejected() -> None:
    upstream, bindings = _propagation_fixture()
    binding = bindings[0]
    assert binding.binding_id == hashlib.sha256(
        authority.DOMAIN_TAGS["source_binding"].encode()
        + b"\x00"
        + canonical_json_bytes(binding._payload())  # noqa: SLF001
    ).hexdigest()
    with pytest.raises(
        authority.V075PortablePlanningV2InvariantViolation,
        match="caller-minted",
    ):
        authority.V075PortablePlanningSourceBindingV2(
            object(),
            binding.target_record_id,
            binding.target_role,
            binding.target_semantic_artifact_id,
            binding.occurrence_id,
            binding.context_id,
            binding.source_epoch_ids,
            binding.route_values,
            binding.source_dependency_record_ids,
            binding.source_commitments,
        )
    object.__setattr__(binding, "route_values", ("MUTATED",))
    with pytest.raises(
        authority.V075PortablePlanningV2InvariantViolation,
        match="identity is stale",
    ):
        _ = binding.binding_id


def test_source_binding_rejects_duplicate_commitment_names() -> None:
    with pytest.raises(
        authority.V075PortablePlanningV2InvariantViolation,
        match="malformed",
    ):
        authority.V075PortablePlanningSourceBindingV2(
            authority._SOURCE_BINDING_ISSUER,  # noqa: SLF001
            _id("target-record"),
            "NUMERICAL_MODEL",
            _id("target-semantic"),
            _id("occurrence"),
            _id("context"),
            (_id("epoch"),),
            ("ADAPTIVE_QUOTIENT",),
            (_id("dependency"),),
            (
                ("same-name", _id("one")),
                ("same-name", _id("two")),
            ),
        )


def test_exact_source_registry_rejects_extra_records(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    occurrence_id = _id("source-occurrence")
    row_id = _id("source-row")
    occurrence = authority._binding_from_record(  # noqa: SLF001
        _portable_record(
            role="OCCURRENCE_IDENTITY",
            schema=authority._SOURCE_ROLE_SCHEMA[  # noqa: SLF001
                "OCCURRENCE_IDENTITY"
            ],
            semantic_id=occurrence_id,
            id_field="occurrence_id",
            index=0,
        )
    )
    row = authority._binding_from_record(  # noqa: SLF001
        _portable_record(
            role="LIVE_ROW_SOURCE_BINDING",
            schema=authority._SOURCE_ROLE_SCHEMA[  # noqa: SLF001
                "LIVE_ROW_SOURCE_BINDING"
            ],
            semantic_id=row_id,
            id_field="binding_id",
            index=1,
        )
    )
    monkeypatch.setattr(
        authority,
        "_expected_source_bytes",
        lambda _epochs: {
            (
                "OCCURRENCE_IDENTITY",
                occurrence_id,
            ): occurrence.canonical_artifact_bytes
        },
    )
    authority._validate_exact_source_record_registry(  # noqa: SLF001
        source_records=(occurrence,),
        epochs=(),
    )
    with pytest.raises(
        authority.V075PortablePlanningV2InvariantViolation,
        match="incomplete or overbroad",
    ):
        authority._validate_exact_source_record_registry(  # noqa: SLF001
            source_records=(occurrence, row),
            epochs=(),
        )
    with pytest.raises(
        authority.V075PortablePlanningV2InvariantViolation,
        match="incomplete or overbroad",
    ):
        authority._validate_exact_source_record_registry(  # noqa: SLF001
            source_records=(),
            epochs=(),
        )
    object.__setattr__(
        occurrence,
        "canonical_artifact_bytes",
        canonical_json_bytes(
            {
                "schema": authority._SOURCE_ROLE_SCHEMA[  # noqa: SLF001
                    "OCCURRENCE_IDENTITY"
                ],
                "occurrence_id": occurrence_id,
                "mutated": True,
            }
        ),
    )
    with pytest.raises(
        authority.V075PortablePlanningV2InvariantViolation,
        match="stale or rehashed",
    ):
        authority._validate_exact_source_record_registry(  # noqa: SLF001
            source_records=(occurrence,),
            epochs=(),
        )


def test_dependency_replay_rejects_duck_typed_source_binding() -> None:
    upstream, bindings = _propagation_fixture()
    exact = bindings[0]
    duck = SimpleNamespace(
        target_record_id=exact.target_record_id,
        target_role=exact.target_role,
        target_semantic_artifact_id=exact.target_semantic_artifact_id,
        occurrence_id=exact.occurrence_id,
        context_id=exact.context_id,
        source_epoch_ids=exact.source_epoch_ids,
        route_values=exact.route_values,
        source_dependency_record_ids=exact.source_dependency_record_ids,
        source_commitments=exact.source_commitments,
        binding_id=exact.binding_id,
        to_document=exact.to_document,
    )
    with pytest.raises(
        authority.V075PortablePlanningV2InvariantViolation,
        match="bounded nonempty DAG",
    ):
        authority._iterative_planning_dependency_nodes(  # noqa: SLF001
            upstream_nodes=upstream,
            source_bindings=(duck, bindings[1]),
        )


@pytest.mark.parametrize("attack", ("upstream", "source-bindings"))
def test_result_rejects_dag_typed_graph_transplant(
    monkeypatch: pytest.MonkeyPatch,
    attack: str,
) -> None:
    upstream = object()
    foreign_upstream = object()
    typed = object.__new__(authority.V075PortablePlanningTypedGraphV2)
    object.__setattr__(typed, "bundle_id", _id("bundle"))
    object.__setattr__(typed, "occurrence_id", _id("occurrence"))
    object.__setattr__(
        typed,
        "public_context_closure_id",
        _id("context"),
    )
    object.__setattr__(typed, "_graph_id", _id("typed-graph"))
    object.__setattr__(typed, "m2_dynamic_child_result", upstream)
    object.__setattr__(typed, "source_bindings", ("typed-source",))
    object.__setattr__(typed, "target_record_bindings", ())

    dag = object.__new__(authority.V075PortablePlanningDependencyDAGV2)
    object.__setattr__(dag, "bundle_id", typed.bundle_id)
    object.__setattr__(dag, "typed_graph_id", typed._graph_id)
    object.__setattr__(dag, "_dag_id", _id("dag"))
    object.__setattr__(
        dag,
        "m2_dynamic_child_result",
        foreign_upstream if attack == "upstream" else upstream,
    )
    object.__setattr__(
        dag,
        "source_bindings",
        (
            ("foreign-source",)
            if attack == "source-bindings"
            else typed.source_bindings
        ),
    )
    object.__setattr__(dag, "nodes", ())

    monkeypatch.setattr(
        authority.V075PortablePlanningTypedGraphV2,
        "_assert_current",
        lambda _self: None,
    )
    monkeypatch.setattr(
        authority.V075PortablePlanningDependencyDAGV2,
        "_assert_current",
        lambda _self: None,
    )

    role_closures = []
    for role in authority.ROLE_ORDER:
        item = object.__new__(authority.V075PortablePlanningRoleClosureV2)
        object.__setattr__(item, "role", role)
        role_closures.append(item)
    propagated = []
    for role in authority.PROPAGATED_ROLE_ORDER:
        item = object.__new__(
            authority.V075PortablePlanningPropagatedRoleClosureV2
        )
        object.__setattr__(item, "role", role)
        propagated.append(item)

    result = object.__new__(authority.V075PortablePlanningReplayV2)
    object.__setattr__(result, "bundle_id", typed.bundle_id)
    object.__setattr__(result, "occurrence_id", typed.occurrence_id)
    object.__setattr__(
        result,
        "public_context_closure_id",
        typed.public_context_closure_id,
    )
    object.__setattr__(result, "typed_graph", typed)
    object.__setattr__(result, "dependency_dag", dag)
    object.__setattr__(result, "attestations", ())
    object.__setattr__(result, "role_closures", tuple(role_closures))
    object.__setattr__(
        result,
        "propagated_role_closures",
        tuple(propagated),
    )

    with pytest.raises(
        authority.V075PortablePlanningV2InvariantViolation,
        match="crossed authority identities",
    ):
        result._validate()  # noqa: SLF001


def test_source_has_no_private_lineage_compiler_or_operational_authority() -> None:
    source = inspect.getsource(authority)
    tree = ast.parse(source)
    called_attributes = {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
    }
    assert "_CONSTRUCTION_LINEAGE_ISSUER" not in source
    assert "_BATCH_CLOSURE_VERIFICATION_ISSUER" not in source
    assert "_replay_numerical_model" not in source
    assert "v075_private_observer_boundary_v2" not in source
    assert not {
        "compile_v075_construction_planning_input_v2",
        "verify_v075_construction_planning_result_bytes_v2",
        "freeze_v075_construction_batch_occurrence_lineage_v2",
        "verify_loaded_private_observer_batch_closure_v2",
        "freeze_v075_live_incremental_model_epoch_v2",
        "_build_epoch",
        "_operational_epoch",
        "step",
        "run_worker",
        "open_observer",
    } & called_attributes
    planner_calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr
        == "plan_v075_construction_numerical_model_v2"
    ]
    assert len(planner_calls) == 1


def test_production_gate_and_pickle_remain_closed() -> None:
    with pytest.raises(
        authority.V075PortablePlanningV2InvariantViolation,
        match="duck-typed",
    ):
        authority.assert_v075_portable_planning_production_gate_v2(object())
    result = object.__new__(authority.V075PortablePlanningReplayV2)
    with pytest.raises(TypeError, match="in-memory-only"):
        pickle.dumps(result)
