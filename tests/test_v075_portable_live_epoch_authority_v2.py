from __future__ import annotations

from dataclasses import dataclass
import ast
import hashlib
import inspect
from pathlib import Path
from types import SimpleNamespace

import pytest

from acfqp.phase3e_ids import canonical_json_bytes
from acfqp import v075_batch_native_planning_backend_v2 as planning
from acfqp import v075_portable_live_epoch_authority_v2 as authority
from acfqp import v075_registered_occurrence_worker_v1 as worker


def _id(label: str) -> str:
    return hashlib.sha256(
        b"acfqp:v075-portable-live-epoch-test:v2\x00" + label.encode()
    ).hexdigest()


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


def test_contract_scope_and_all_locks_remain_closed() -> None:
    assert authority.PROPOSED_CONTRACT_VERSION == "1.75.0"
    assert authority.ROLE_ORDER == (
        "LIVE_ROW_SOURCE_BINDING",
        "LIVE_MODEL_EPOCH",
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
        "PLAN_CERTIFICATE_ISSUANCE_ALLOWED",
        "INFEASIBILITY_CERTIFICATE_ISSUANCE_ALLOWED",
    ):
        assert getattr(authority, name) is False


def test_entry_is_raw_only_and_hardened_174_runs_first(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert tuple(
        inspect.signature(
            authority.replay_v075_portable_live_epoch_v2
        ).parameters
    ) == (
        "repository_root",
        "portable_bundle_bytes",
        "public_context_closure_bytes",
    )
    calls: list[str] = []

    def stop_at_upstream(**_kwargs):
        calls.append("1.74")
        raise RuntimeError("sentinel")

    def forbidden_bundle(*_args, **_kwargs):
        calls.append("bundle")
        raise AssertionError("bundle replay ran before hardened 1.74")

    monkeypatch.setattr(
        authority.m2_life,
        "replay_v075_portable_construction_lifecycle_v2",
        stop_at_upstream,
    )
    monkeypatch.setattr(
        authority.portable,
        "verify_v075_portable_occurrence_evidence_bundle_bytes_v2",
        forbidden_bundle,
    )
    with pytest.raises(
        authority.V075PortableLiveEpochV2InvariantViolation,
        match="hardened 1.74 replay failed",
    ):
        authority.replay_v075_portable_live_epoch_v2(
            repository_root=Path("."),
            portable_bundle_bytes=b"bundle",
            public_context_closure_bytes=b"context",
        )
    assert calls == ["1.74"]


def test_public_entry_wires_the_complete_success_pipeline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, object]] = []
    upstream = SimpleNamespace(
        bundle_id=_id("bundle"),
        occurrence_id=_id("occurrence"),
        public_context_closure_id=_id("context"),
        dependency_dag=SimpleNamespace(nodes=("upstream-node",)),
    )
    target_records = (
        SimpleNamespace(role="LIVE_ROW_SOURCE_BINDING"),
        SimpleNamespace(role="LIVE_MODEL_EPOCH"),
    )
    bundle = SimpleNamespace(
        bundle_id=upstream.bundle_id,
        occurrence_id=upstream.occurrence_id,
        records=target_records
        + (SimpleNamespace(role="UNRELATED_ROLE"),),
    )
    bindings = (
        SimpleNamespace(
            role="LIVE_ROW_SOURCE_BINDING",
            record_id=_id("source-record"),
        ),
        SimpleNamespace(
            role="LIVE_MODEL_EPOCH",
            record_id=_id("epoch-record"),
        ),
    )
    epochs = (SimpleNamespace(model_epoch_id=_id("epoch")),)
    typed = SimpleNamespace(_graph_id=_id("typed-graph"))
    nodes = ("new-node",)
    dag = SimpleNamespace(_dag_id=_id("dag"))
    attestations = ("attestation",)
    closures = ("closure-source", "closure-epoch")
    result = object()

    def upstream_call(**kwargs):
        calls.append(("1.74", kwargs))
        return upstream

    def bundle_call(raw):
        calls.append(("bundle", raw))
        return bundle

    binding_index = {"value": 0}

    def bind(record):
        calls.append(("binding", record.role))
        value = bindings[binding_index["value"]]
        binding_index["value"] += 1
        return value

    def reconstruct(**kwargs):
        calls.append(("reconstruct", kwargs))
        return epochs

    def typed_ctor(*args):
        calls.append(("typed-graph", args))
        return typed

    def replay_dag(**kwargs):
        calls.append(("dependency-replay", kwargs))
        return nodes

    def dag_ctor(*args):
        calls.append(("dag", args))
        return dag

    def attest(**kwargs):
        calls.append(("attestations", kwargs))
        return attestations

    def close(**kwargs):
        calls.append(("closures", kwargs))
        return closures

    def result_ctor(*args):
        calls.append(("result", args))
        return result

    monkeypatch.setattr(
        authority.m2_life,
        "replay_v075_portable_construction_lifecycle_v2",
        upstream_call,
    )
    monkeypatch.setattr(
        authority.portable,
        "verify_v075_portable_occurrence_evidence_bundle_bytes_v2",
        bundle_call,
    )
    monkeypatch.setattr(authority, "_binding_from_record", bind)
    monkeypatch.setattr(authority, "_reconstruct_live_epochs", reconstruct)
    monkeypatch.setattr(
        authority,
        "V075PortableLiveEpochTypedGraphV2",
        typed_ctor,
    )
    monkeypatch.setattr(
        authority,
        "_iterative_live_epoch_dependency_nodes",
        replay_dag,
    )
    monkeypatch.setattr(
        authority,
        "V075PortableLiveEpochDependencyDAGV2",
        dag_ctor,
    )
    monkeypatch.setattr(authority, "_build_attestations", attest)
    monkeypatch.setattr(authority, "_build_role_closures", close)
    monkeypatch.setattr(
        authority,
        "V075PortableLiveEpochReplayV2",
        result_ctor,
    )
    raw_bundle = b"raw-bundle"
    raw_context = b"raw-context"
    actual = authority.replay_v075_portable_live_epoch_v2(
        repository_root=Path("/tmp/project"),
        portable_bundle_bytes=raw_bundle,
        public_context_closure_bytes=raw_context,
    )
    assert actual is result
    assert [item[0] for item in calls] == [
        "1.74",
        "bundle",
        "binding",
        "binding",
        "reconstruct",
        "typed-graph",
        "dependency-replay",
        "dag",
        "attestations",
        "closures",
        "result",
    ]
    upstream_kwargs = calls[0][1]
    assert upstream_kwargs["portable_bundle_bytes"] is raw_bundle
    assert upstream_kwargs["public_context_closure_bytes"] is raw_context
    reconstruct_kwargs = calls[4][1]
    assert reconstruct_kwargs == {
        "upstream": upstream,
        "record_bindings": bindings,
        "_upstream_already_current": True,
    }
    dag_kwargs = calls[6][1]
    assert dag_kwargs["upstream_nodes"] == ("upstream-node",)
    assert dag_kwargs["locally_replayed_record_ids"] == frozenset(
        item.record_id for item in bindings
    )


def test_source_has_only_the_tightly_bound_build_epoch_path() -> None:
    source = inspect.getsource(authority)
    tree = ast.parse(source)
    called_attributes = {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
    }
    forbidden = {
        "freeze_v075_live_incremental_model_epoch_v2",
        "replay_v075_live_incremental_model_epoch_v2",
        "_validate_operational_parent",
        "_register_trusted_same_process_epoch",
        "validate_v075_trusted_owned_open_prefix_v2",
    }
    assert not forbidden & called_attributes
    assert not any(
        isinstance(node, ast.arg)
        and node.arg
        in {
            "private_salt",
            "private_environment",
            "signer",
            "claimed_epoch",
        }
        for node in ast.walk(tree)
    )
    build_calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "_build_epoch"
    ]
    assert len(build_calls) == 1
    keywords = {
        item.arg: item.value for item in build_calls[0].keywords
    }
    assert isinstance(keywords["replay_parent"], ast.Constant)
    assert keywords["replay_parent"].value is False
    assert isinstance(keywords["register_operational"], ast.Constant)
    assert keywords["register_operational"].value is False
    assert isinstance(keywords["portable_prefix_replay"], ast.Constant)
    assert keywords["portable_prefix_replay"].value is True


def _epoch_fixture(monkeypatch: pytest.MonkeyPatch):
    occurrence = SimpleNamespace(
        occurrence_id=_id("occurrence"),
        context_id=_id("context"),
        arm=worker.V075WorkerArmV1.NO_PRIOR,
    )
    receipt = _id("receipt")
    freeze_id = _id("freeze")
    append = SimpleNamespace(
        receipt=SimpleNamespace(receipt_id=receipt),
    )
    freeze = SimpleNamespace(freeze_id=freeze_id)
    prefix = SimpleNamespace(
        verification_id=_id("prefix"),
        receipt_ids=(receipt,),
        support_freeze_ids=(freeze_id,),
        head_ids=(_id("zero-head"), _id("head")),
        zero_head_id=_id("zero-head"),
        current_head_id=_id("head"),
        occurrence_id=occurrence.occurrence_id,
        appends=(append,),
        support_freezes=(freeze,),
    )
    control_graph = SimpleNamespace(
        open_prefixes=(prefix,),
        appends=(append,),
        support_freezes=(freeze,),
    )
    monkeypatch.setattr(
        authority,
        "_control_graph",
        lambda *_args, **_kwargs: control_graph,
    )
    monkeypatch.setattr(
        authority,
        "_m0_graph",
        lambda *_args, **_kwargs: SimpleNamespace(occurrence=occurrence),
    )
    row_source = SimpleNamespace(
        binding_id=_id("row-source"),
        to_document=lambda: {
            "schema": "test.row.source",
            "binding_id": _id("row-source"),
            "source_digest": _id("source-digest"),
        },
    )
    epoch_id = _id("epoch")
    document = {
        "schema": "acfqp.v075_live_incremental_model_epoch.v2",
        "model_epoch_id": epoch_id,
        "occurrence_id": occurrence.occurrence_id,
        "context_id": occurrence.context_id,
        "arm": occurrence.arm.value,
        "route": planning.V075PlanningRouteV2.ADAPTIVE_QUOTIENT.value,
        "head_id": prefix.current_head_id,
        "epoch_index": 1,
        "parent_epoch_id": None,
        "open_prefix_verification_id": prefix.verification_id,
        "append_receipt_ids": [receipt],
        "support_freeze_ids": [freeze_id],
        "row_sources": [
            {
                "binding_id": row_source.binding_id,
                "source_digest": _id("source-digest"),
            }
        ],
        "model": {"model_id": _id("model")},
        "proof": {"proof_id": _id("proof")},
        "numerical_model_id": _id("model"),
        "numerical_proof_id": _id("proof"),
    }
    raw = canonical_json_bytes(document)
    expected = SimpleNamespace(
        model_epoch_id=epoch_id,
        canonical_bytes=raw,
        parent_epoch_id=None,
        open_prefix_verification=prefix,
        row_sources=(row_source,),
    )
    calls = []

    def build_epoch(**kwargs):
        calls.append(kwargs)
        return expected

    monkeypatch.setattr(authority.live_model, "_build_epoch", build_epoch)
    binding = SimpleNamespace(
        role="LIVE_MODEL_EPOCH",
        semantic_artifact_id=epoch_id,
        canonical_artifact_bytes=raw,
        record_index=7,
        _assert_current=lambda: None,
    )
    return binding, document, expected, calls


def test_positive_orchestration_uses_no_operational_path_and_deduplicates_root(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    binding, _document, expected, calls = _epoch_fixture(monkeypatch)
    registry_before = dict(
        authority.live_model._TRUSTED_SAME_PROCESS_EPOCHS  # noqa: SLF001
    )
    monkeypatch.setattr(
        authority.live_model,
        "_validate_operational_parent",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("operational parent path called")
        ),
    )
    monkeypatch.setattr(
        authority.live_model,
        "_register_trusted_same_process_epoch",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("operational registry called")
        ),
    )
    rebuilt = authority._reconstruct_live_epochs(  # noqa: SLF001
        upstream=object(),
        record_bindings=(binding,),
        _upstream_already_current=True,
    )
    assert rebuilt == (expected,)
    assert len(calls) == 1
    assert calls[0]["replay_parent"] is False
    assert calls[0]["register_operational"] is False
    assert calls[0]["portable_prefix_replay"] is True
    assert calls[0]["parent_epoch"] is None
    assert (
        authority.live_model._TRUSTED_SAME_PROCESS_EPOCHS  # noqa: SLF001
        == registry_before
    )


@pytest.mark.parametrize(
    "attack",
    ("byte", "parent", "prefix", "route", "source", "model", "proof"),
)
def test_epoch_byte_parent_prefix_route_source_model_and_proof_attacks_fail(
    monkeypatch: pytest.MonkeyPatch,
    attack: str,
) -> None:
    binding, document, _expected, _calls = _epoch_fixture(monkeypatch)
    attacked = dict(document)
    if attack == "byte":
        attacked["epoch_index"] = 2
    elif attack == "parent":
        attacked["parent_epoch_id"] = _id("foreign-parent")
    elif attack == "prefix":
        attacked["open_prefix_verification_id"] = _id("foreign-prefix")
    elif attack == "route":
        attacked["route"] = (
            planning.V075PlanningRouteV2.MATCHED_DIRECT_GROUND.value
        )
    elif attack == "source":
        attacked["row_sources"] = [
            {
                "binding_id": _id("row-source"),
                "source_digest": _id("mutated-source"),
            }
        ]
    elif attack == "model":
        attacked["model"] = {"model_id": _id("mutated-model")}
    else:
        attacked["proof"] = {"proof_id": _id("mutated-proof")}
    binding.canonical_artifact_bytes = canonical_json_bytes(attacked)
    with pytest.raises(
        authority.V075PortableLiveEpochV2InvariantViolation
    ):
        authority._reconstruct_live_epochs(  # noqa: SLF001
            upstream=object(),
            record_bindings=(binding,),
            _upstream_already_current=True,
        )


def test_row_source_union_is_keyed_by_binding_id_not_row_or_numerical_id(
) -> None:
    first = SimpleNamespace(
        binding_id=_id("source-a"),
        row_binding_id=_id("same-row"),
        numerical_row_id=_id("same-numerical-row"),
        to_document=lambda: {
            "binding_id": _id("source-a"),
            "row_binding_id": _id("same-row"),
        },
    )
    second = SimpleNamespace(
        binding_id=_id("source-b"),
        row_binding_id=_id("same-row"),
        numerical_row_id=_id("same-numerical-row"),
        to_document=lambda: {
            "binding_id": _id("source-b"),
            "row_binding_id": _id("same-row"),
        },
    )
    union = authority._expected_row_source_bytes(  # noqa: SLF001
        (
            SimpleNamespace(row_sources=(first,)),
            SimpleNamespace(row_sources=(second,)),
        )
    )
    assert tuple(union) == tuple(sorted((first.binding_id, second.binding_id)))
    conflicting = SimpleNamespace(
        binding_id=first.binding_id,
        to_document=lambda: {
            "binding_id": first.binding_id,
            "row_binding_id": _id("foreign-row"),
        },
    )
    with pytest.raises(
        authority.V075PortableLiveEpochV2InvariantViolation,
        match="different exact bytes",
    ):
        authority._expected_row_source_bytes(  # noqa: SLF001
            (
                SimpleNamespace(row_sources=(first,)),
                SimpleNamespace(row_sources=(conflicting,)),
            )
        )


def _dependency_fixture():
    base = _node("base", 0, "OBSERVATION_ROW_BINDING")
    inherited = _node(
        "inherited",
        1,
        "LIFECYCLE_SUPPORT_EVIDENCE",
        semantic=(base.record_id,),
    )
    source = _node(
        "source",
        2,
        "LIVE_ROW_SOURCE_BINDING",
        portable=(inherited.record_id,),
        local=False,
        resolved=False,
        frontier=(_id("source"),),
    )
    model = _node(
        "model",
        3,
        "NUMERICAL_MODEL",
        local=False,
        resolved=False,
        frontier=(_id("model"),),
    )
    proof = _node(
        "proof",
        4,
        "NUMERICAL_PLANNING_PROOF",
        local=False,
        resolved=False,
        frontier=(_id("proof"),),
    )
    epoch = _node(
        "epoch",
        5,
        "LIVE_MODEL_EPOCH",
        portable=(source.record_id, model.record_id, proof.record_id),
        local=False,
        resolved=False,
        frontier=(_id("epoch"),),
    )
    return (base, inherited, source, model, proof, epoch)


def test_dependency_replay_preserves_three_lanes_and_exact_frontier() -> None:
    nodes = _dependency_fixture()
    source, model, proof, epoch = nodes[2:]
    replayed = authority._iterative_live_epoch_dependency_nodes(  # noqa: SLF001
        upstream_nodes=nodes,
        locally_replayed_record_ids=frozenset(
            {source.record_id, epoch.record_id}
        ),
    )
    by_id = {item.record_id: item for item in replayed}
    assert by_id[source.record_id].semantically_resolved is True
    assert by_id[epoch.record_id].semantically_resolved is False
    assert by_id[epoch.record_id].local_semantic_authority_resolved is True
    assert by_id[epoch.record_id].unresolved_frontier_record_ids == tuple(
        sorted((model.record_id, proof.record_id))
    )
    assert by_id[epoch.record_id].unresolved_frontier_roles == (
        "NUMERICAL_MODEL",
        "NUMERICAL_PLANNING_PROOF",
    )
    inherited_replay = by_id[nodes[1].record_id]
    assert (
        inherited_replay.portable_declared_dependency_record_ids
        == nodes[1].portable_declared_dependency_record_ids
    )
    assert (
        inherited_replay.authority_local_semantic_dependency_record_ids
        == nodes[1].authority_local_semantic_dependency_record_ids
    )
    assert (
        inherited_replay.effective_dependency_record_ids
        == nodes[1].effective_dependency_record_ids
    )


def test_dropping_authority_local_lane_is_rejected() -> None:
    nodes = list(_dependency_fixture())
    victim = nodes[1]
    nodes[1] = _UpstreamNode(
        victim.record_id,
        victim.record_index,
        victim.role,
        victim.portable_declared_dependency_record_ids,
        victim.authority_local_semantic_dependency_record_ids,
        (),
        victim.local_semantic_authority_resolved,
        victim.semantically_resolved,
        victim.unresolved_frontier_record_ids,
        victim.dependency_depth,
    )
    with pytest.raises(
        authority.V075PortableLiveEpochV2InvariantViolation,
        match="lane split",
    ):
        authority._iterative_live_epoch_dependency_nodes(  # noqa: SLF001
            upstream_nodes=tuple(nodes),
            locally_replayed_record_ids=frozenset(
                {nodes[2].record_id, nodes[-1].record_id}
            ),
        )


def test_iterative_dependency_replay_scales_to_4096_depth() -> None:
    count = 4096
    identifiers = tuple(_id(f"deep-{index}") for index in range(count))
    nodes = tuple(
        _UpstreamNode(
            identifiers[index],
            index,
            (
                "LIVE_ROW_SOURCE_BINDING"
                if index == count - 1
                else "UPSTREAM_PUBLIC"
            ),
            (() if index == 0 else (identifiers[index - 1],)),
            (),
            (() if index == 0 else (identifiers[index - 1],)),
            index != count - 1,
            index != count - 1,
            (() if index != count - 1 else (identifiers[-1],)),
            index + 1,
        )
        for index in range(count)
    )
    replayed = authority._iterative_live_epoch_dependency_nodes(  # noqa: SLF001
        upstream_nodes=nodes,
        locally_replayed_record_ids=frozenset({identifiers[-1]}),
    )
    assert len(replayed) == count
    assert replayed[-1].dependency_depth == 4096
    assert replayed[-1].semantically_resolved is True


def test_role_closure_tri_state_and_production_gate() -> None:
    status = authority.V075PortableLiveEpochRoleStatusV2
    absent = authority.V075PortableLiveEpochRoleClosureV2(  # noqa: SLF001
        authority._ROLE_CLOSURE_ISSUER,
        _id("bundle"),
        _id("graph"),
        _id("dag"),
        "LIVE_MODEL_EPOCH",
        status.NOT_PRESENT_IN_OCCURRENCE,
        (),
        (),
        (),
        (),
        (),
    )
    assert absent.status is status.NOT_PRESENT_IN_OCCURRENCE
    with pytest.raises(
        authority.V075PortableLiveEpochProductionV2NotReady
    ):
        authority.open_v075_production_from_portable_live_epoch_v2()
