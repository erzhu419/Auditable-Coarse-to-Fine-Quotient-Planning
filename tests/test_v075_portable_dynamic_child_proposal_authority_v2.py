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
from acfqp import (
    v075_portable_dynamic_child_proposal_authority_v2 as authority,
)


def _id(label: str) -> str:
    return hashlib.sha256(
        b"acfqp:v075-portable-dynamic-child-test:v2\x00"
        + label.encode()
    ).hexdigest()


def _portable_record(
    *,
    role: str,
    schema: str,
    semantic_id: str,
    id_field: str,
    index: int,
    document: dict | None = None,
    dependencies: tuple[str, ...] = (),
):
    artifact = (
        {"schema": schema, id_field: semantic_id}
        if document is None
        else document
    )
    raw = canonical_json_bytes(artifact)
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
        record_id=authority.portable._hash(  # noqa: SLF001
            domain,
            payload,
        ),
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


def test_contract_scope_role_order_and_all_locks_remain_closed() -> None:
    assert authority.PROPOSED_CONTRACT_VERSION == "1.76.0"
    assert authority.ROLE_ORDER == (
        "DYNAMIC_CHILD_CAUSAL_EDGE",
        "DYNAMIC_CHILD_STATE",
        "DYNAMIC_CHILD_DISCOVERY_INTENT",
        "DYNAMIC_CHILD_VALIDATION_TEMPLATE",
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


def test_entry_is_raw_only_and_hardened_175_runs_first(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert tuple(
        inspect.signature(
            authority.replay_v075_portable_dynamic_child_proposal_v2
        ).parameters
    ) == (
        "repository_root",
        "portable_bundle_bytes",
        "public_context_closure_bytes",
    )
    calls: list[str] = []

    def stop_at_upstream(**_kwargs):
        calls.append("1.75")
        raise RuntimeError("sentinel")

    def forbidden_bundle(*_args, **_kwargs):
        calls.append("bundle")
        raise AssertionError("bundle replay ran before hardened 1.75")

    monkeypatch.setattr(
        authority.m2_epoch,
        "replay_v075_portable_live_epoch_v2",
        stop_at_upstream,
    )
    monkeypatch.setattr(
        authority.portable,
        "verify_v075_portable_occurrence_evidence_bundle_bytes_v2",
        forbidden_bundle,
    )
    with pytest.raises(
        authority.V075PortableDynamicChildProposalV2InvariantViolation,
        match="hardened 1.75 replay failed",
    ):
        authority.replay_v075_portable_dynamic_child_proposal_v2(
            repository_root=Path("."),
            portable_bundle_bytes=b"bundle",
            public_context_closure_bytes=b"context",
        )
    assert calls == ["1.75"]


def test_public_entry_wires_exact_full_pipeline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, object]] = []
    source_epoch_id = _id("epoch")
    raw_closure = canonical_json_bytes(
        {
            "schema": authority._ROLE_SCHEMA[  # noqa: SLF001
                "DYNAMIC_CHILD_CLOSURE"
            ],
            "source_model_epoch_id": source_epoch_id,
            "closure_id": _id("closure"),
        }
    )
    upstream = SimpleNamespace(
        bundle_id=_id("bundle"),
        occurrence_id=_id("occurrence"),
        public_context_closure_id=_id("context"),
        dependency_dag=SimpleNamespace(nodes=("upstream-node",)),
    )
    closure_record = SimpleNamespace(role="DYNAMIC_CHILD_CLOSURE")
    verification_record = SimpleNamespace(
        role="DYNAMIC_CHILD_CLOSURE_VERIFICATION"
    )
    bundle = SimpleNamespace(
        bundle_id=upstream.bundle_id,
        occurrence_id=upstream.occurrence_id,
        records=(closure_record, verification_record),
    )
    closure_binding = SimpleNamespace(
        role="DYNAMIC_CHILD_CLOSURE",
        record_id=_id("closure-record"),
        canonical_artifact_bytes=raw_closure,
    )
    verification_binding = SimpleNamespace(
        role="DYNAMIC_CHILD_CLOSURE_VERIFICATION",
        record_id=_id("verification-record"),
    )
    epoch = object()
    namespace = object()
    closure = object()
    verification = object()
    members = object()
    sources = ("source-record",)
    source_bindings = (
        SimpleNamespace(target_record_id=_id("closure-record")),
    )
    typed = SimpleNamespace(_graph_id=_id("typed"))
    dependency_map = {_id("closure-record"): (_id("source"),)}
    binding_map = {_id("closure-record"): _id("binding")}
    nodes = ("node",)
    dag = SimpleNamespace(_dag_id=_id("dag"))
    attestations = ("attestation",)
    closures = ("role-closure",)
    expected_result = object()

    monkeypatch.setattr(
        authority.m2_epoch,
        "replay_v075_portable_live_epoch_v2",
        lambda **kwargs: (
            calls.append(("1.75", kwargs)) or upstream
        ),
    )
    monkeypatch.setattr(
        authority.portable,
        "verify_v075_portable_occurrence_evidence_bundle_bytes_v2",
        lambda raw: calls.append(("bundle", raw)) or bundle,
    )
    binding_values = iter((closure_binding, verification_binding))
    monkeypatch.setattr(
        authority,
        "_binding_from_record",
        lambda record: (
            calls.append(("record", record.role))
            or next(binding_values)
        ),
    )
    monkeypatch.setattr(
        authority,
        "_unique_epoch",
        lambda *args, **kwargs: (
            calls.append(("epoch", (args, kwargs))) or epoch
        ),
    )
    monkeypatch.setattr(
        authority,
        "_namespace",
        lambda *args, **kwargs: (
            calls.append(("namespace", (args, kwargs))) or namespace
        ),
    )

    def producer(**kwargs):
        calls.append(("producer", kwargs))
        return closure, verification

    monkeypatch.setattr(
        authority.dynamic,
        "verify_v075_live_dynamic_child_closure_bytes_v2",
        producer,
    )
    monkeypatch.setattr(
        authority,
        "_expected_target_members",
        lambda *args: calls.append(("members", args)) or members,
    )
    monkeypatch.setattr(
        authority,
        "_validate_target_registry",
        lambda **kwargs: calls.append(("registry", kwargs)),
    )
    monkeypatch.setattr(
        authority,
        "_exact_source_record_bindings",
        lambda **kwargs: calls.append(("sources", kwargs)) or sources,
    )
    monkeypatch.setattr(
        authority,
        "_build_source_bindings",
        lambda **kwargs: (
            calls.append(("source-bindings", kwargs)) or source_bindings
        ),
    )
    monkeypatch.setattr(
        authority,
        "V075PortableDynamicChildProposalTypedGraphV2",
        lambda *args: calls.append(("typed", args)) or typed,
    )
    monkeypatch.setattr(
        authority,
        "_source_dependency_maps",
        lambda value: (
            calls.append(("source-maps", value))
            or (dependency_map, binding_map)
        ),
    )
    monkeypatch.setattr(
        authority,
        "_iterative_dynamic_child_dependency_nodes",
        lambda **kwargs: calls.append(("nodes", kwargs)) or nodes,
    )
    monkeypatch.setattr(
        authority,
        "V075PortableDynamicChildProposalDependencyDAGV2",
        lambda *args: calls.append(("dag", args)) or dag,
    )
    monkeypatch.setattr(
        authority,
        "_build_attestations",
        lambda **kwargs: (
            calls.append(("attestations", kwargs)) or attestations
        ),
    )
    monkeypatch.setattr(
        authority,
        "_build_role_closures",
        lambda **kwargs: (
            calls.append(("closures", kwargs)) or closures
        ),
    )
    monkeypatch.setattr(
        authority,
        "V075PortableDynamicChildProposalReplayV2",
        lambda *args: calls.append(("result", args)) or expected_result,
    )

    actual = authority.replay_v075_portable_dynamic_child_proposal_v2(
        repository_root=Path("/tmp/project"),
        portable_bundle_bytes=b"raw-bundle",
        public_context_closure_bytes=b"raw-context",
    )
    assert actual is expected_result
    assert [item[0] for item in calls] == [
        "1.75",
        "bundle",
        "record",
        "record",
        "epoch",
        "namespace",
        "producer",
        "members",
        "registry",
        "sources",
        "source-bindings",
        "typed",
        "source-maps",
        "nodes",
        "dag",
        "attestations",
        "closures",
        "result",
    ]
    producer_kwargs = calls[6][1]
    assert producer_kwargs == {
        "source_epoch": epoch,
        "namespace": namespace,
        "claimed_bytes": raw_closure,
    }


def test_mutated_closure_stops_at_exact_producer_verifier(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    epoch_id = _id("epoch")
    raw = canonical_json_bytes(
        {
            "schema": authority._ROLE_SCHEMA[  # noqa: SLF001
                "DYNAMIC_CHILD_CLOSURE"
            ],
            "source_model_epoch_id": epoch_id,
            "closure_id": _id("closure"),
        }
    )
    upstream = SimpleNamespace(
        bundle_id=_id("bundle"),
        occurrence_id=_id("occurrence"),
        public_context_closure_id=_id("context"),
    )
    record = SimpleNamespace(role="DYNAMIC_CHILD_CLOSURE")
    bundle = SimpleNamespace(
        bundle_id=upstream.bundle_id,
        occurrence_id=upstream.occurrence_id,
        records=(record,),
    )
    binding = SimpleNamespace(
        role="DYNAMIC_CHILD_CLOSURE",
        record_id=_id("record"),
        canonical_artifact_bytes=raw,
    )
    monkeypatch.setattr(
        authority.m2_epoch,
        "replay_v075_portable_live_epoch_v2",
        lambda **_kwargs: upstream,
    )
    monkeypatch.setattr(
        authority.portable,
        "verify_v075_portable_occurrence_evidence_bundle_bytes_v2",
        lambda _raw: bundle,
    )
    monkeypatch.setattr(
        authority,
        "_binding_from_record",
        lambda _record: binding,
    )
    monkeypatch.setattr(
        authority,
        "_unique_epoch",
        lambda *args, **kwargs: object(),
    )
    monkeypatch.setattr(
        authority,
        "_namespace",
        lambda *args, **kwargs: object(),
    )
    monkeypatch.setattr(
        authority.dynamic,
        "verify_v075_live_dynamic_child_closure_bytes_v2",
        lambda **_kwargs: (_ for _ in ()).throw(
            RuntimeError("mutated")
        ),
    )
    monkeypatch.setattr(
        authority,
        "_expected_target_members",
        lambda *_args: (_ for _ in ()).throw(
            AssertionError("continued after producer rejection")
        ),
    )
    with pytest.raises(
        authority.V075PortableDynamicChildProposalV2InvariantViolation,
        match="exact producer byte replay failed",
    ):
        authority.replay_v075_portable_dynamic_child_proposal_v2(
            repository_root=Path("."),
            portable_bundle_bytes=b"bundle",
            public_context_closure_bytes=b"context",
        )


def test_source_has_no_operational_legacy_or_execution_authority() -> None:
    source = inspect.getsource(authority)
    tree = ast.parse(source)
    called_attributes = {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
    }
    assert "v075_dynamic_child_closure_intent_authority_v2" not in source
    assert not {
        "freeze_v075_live_dynamic_child_closure_v2",
        "_operational_epoch",
        "freeze_v075_live_incremental_model_epoch_v2",
        "_register_trusted_same_process_epoch",
        "step",
        "run_worker",
        "open_observer",
    } & called_attributes
    producer_calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr
        == "verify_v075_live_dynamic_child_closure_bytes_v2"
    ]
    assert len(producer_calls) == 2
    assert not any(
        isinstance(node, ast.arg)
        and node.arg
        in {
            "private_salt",
            "private_environment",
            "signer",
            "observer",
            "worker",
            "claimed_epoch",
        }
        for node in ast.walk(tree)
    )


def test_role_schema_id_and_old_schema_are_rejected() -> None:
    role = "DYNAMIC_CHILD_CLOSURE"
    semantic_id = _id("closure")
    exact = _portable_record(
        role=role,
        schema=authority._ROLE_SCHEMA[role],  # noqa: SLF001
        semantic_id=semantic_id,
        id_field=authority._ROLE_ID_FIELD[role],  # noqa: SLF001
        index=0,
    )
    binding = authority._binding_from_record(exact)  # noqa: SLF001
    assert binding.semantic_artifact_id == semantic_id
    old = SimpleNamespace(
        **{
            **vars(exact),
            "artifact_schema": (
                "acfqp.v075_live_dynamic_child_closure.v1"
            ),
        }
    )
    with pytest.raises(
        authority.V075PortableDynamicChildProposalV2InvariantViolation,
        match="malformed",
    ):
        authority._binding_from_record(old)  # noqa: SLF001
    object.__setattr__(binding, "semantic_artifact_id", _id("mutated"))
    with pytest.raises(
        authority.V075PortableDynamicChildProposalV2InvariantViolation
    ):
        binding._assert_current()  # noqa: SLF001


def test_six_role_registry_includes_exact_empty_roles(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Edge:
        def __init__(self, label: str):
            self.edge_id = _id(label)

        def to_document(self):
            return {
                "schema": authority._ROLE_SCHEMA[  # noqa: SLF001
                    "DYNAMIC_CHILD_CAUSAL_EDGE"
                ],
                "edge_id": self.edge_id,
            }

    class Child:
        def __init__(self, edge: Edge):
            self.child_binding_id = _id("child")
            self.causal_edges = (edge,)

        def to_document(self):
            return {
                "schema": authority._ROLE_SCHEMA[  # noqa: SLF001
                    "DYNAMIC_CHILD_STATE"
                ],
                "child_binding_id": self.child_binding_id,
            }

    class Closure:
        def __init__(self, child: Child):
            self.closure_id = _id("closure")
            self.child_states = (child,)
            self.discovery_intents = ()
            self.validation_templates = ()

        def to_document(self):
            return {
                "schema": authority._ROLE_SCHEMA[  # noqa: SLF001
                    "DYNAMIC_CHILD_CLOSURE"
                ],
                "closure_id": self.closure_id,
            }

    class Verification:
        def __init__(self, closure: Closure):
            self.closure_id = closure.closure_id
            self.verification_id = _id("verification")

        def to_document(self):
            return {
                "schema": authority._ROLE_SCHEMA[  # noqa: SLF001
                    "DYNAMIC_CHILD_CLOSURE_VERIFICATION"
                ],
                "verification_id": self.verification_id,
            }

    monkeypatch.setattr(
        authority.dynamic,
        "V075LiveDynamicChildClosureV2",
        Closure,
    )
    monkeypatch.setattr(
        authority.dynamic,
        "V075LiveDynamicChildClosureVerificationV2",
        Verification,
    )
    edge = Edge("edge")
    child = Child(edge)
    closure = Closure(child)
    verification = Verification(closure)
    members = authority._expected_target_members(  # noqa: SLF001
        closure,
        verification,
    )
    assert tuple(members) == authority.ROLE_ORDER
    assert tuple(members["DYNAMIC_CHILD_DISCOVERY_INTENT"]) == ()
    assert tuple(members["DYNAMIC_CHILD_VALIDATION_TEMPLATE"]) == ()
    assert tuple(members["DYNAMIC_CHILD_CAUSAL_EDGE"]) == (
        edge.edge_id,
    )
    assert tuple(members["DYNAMIC_CHILD_STATE"]) == (
        child.child_binding_id,
    )

    records = []
    for index, role in enumerate(
        (
            "DYNAMIC_CHILD_CAUSAL_EDGE",
            "DYNAMIC_CHILD_STATE",
            "DYNAMIC_CHILD_CLOSURE",
            "DYNAMIC_CHILD_CLOSURE_VERIFICATION",
        )
    ):
        semantic_id, (raw, _value) = next(iter(members[role].items()))
        records.append(
            authority._binding_from_record(  # noqa: SLF001
                _portable_record(
                    role=role,
                    schema=authority._ROLE_SCHEMA[role],  # noqa: SLF001
                    semantic_id=semantic_id,
                    id_field=authority._ROLE_ID_FIELD[role],  # noqa: SLF001
                    index=index,
                    document=authority.loads_canonical_json(raw),
                )
            )
        )
    authority._validate_target_registry(  # noqa: SLF001
        target_bindings=tuple(records),
        expected_members=members,
    )
    with pytest.raises(
        authority.V075PortableDynamicChildProposalV2InvariantViolation,
        match="DISCOVERY_INTENT",
    ):
        extra = authority._binding_from_record(  # noqa: SLF001
            _portable_record(
                role="DYNAMIC_CHILD_DISCOVERY_INTENT",
                schema=authority._ROLE_SCHEMA[  # noqa: SLF001
                    "DYNAMIC_CHILD_DISCOVERY_INTENT"
                ],
                semantic_id=_id("foreign-intent"),
                id_field="intent_id",
                index=4,
            )
        )
        authority._validate_target_registry(  # noqa: SLF001
            target_bindings=tuple((*records, extra)),
            expected_members=members,
        )


def _edge_source_fixture(monkeypatch: pytest.MonkeyPatch):
    class Edge:
        pass

    monkeypatch.setattr(
        authority.dynamic,
        "V075LiveDynamicChildCausalEdgeV2",
        Edge,
    )
    row_id = _id("row")
    row_binding_id = _id("row-binding")
    descriptor_id = _id("descriptor")
    child_state_id = _id("child-state")
    source_id = _id("row-source")
    freeze_id = _id("freeze")
    edge = Edge()
    edge.edge_id = _id("edge")
    edge.child_state_id = child_state_id
    edge.parent_numerical_row_id = row_id
    edge.parent_row_binding_id = row_binding_id
    edge.support_descriptor_id = descriptor_id
    edge.row_source_binding_id = source_id
    edge.support_freeze_id = freeze_id
    descriptor = SimpleNamespace(
        descriptor_id=descriptor_id,
        next_state_id=child_state_id,
        failure=False,
        terminal=False,
    )
    row = SimpleNamespace(
        row_id=row_id,
        row_binding_id=row_binding_id,
        remaining_horizon=2,
        support=(descriptor,),
    )

    class Source:
        def __init__(self):
            self.binding_id = source_id
            self.numerical_row_id = row_id
            self.row_binding_id = row_binding_id
            self.support_freeze_id = freeze_id

        def to_document(self):
            return {
                "schema": authority._SOURCE_ROLE_SCHEMA[  # noqa: SLF001
                    "LIVE_ROW_SOURCE_BINDING"
                ],
                "binding_id": self.binding_id,
                "numerical_row_id": self.numerical_row_id,
                "row_binding_id": self.row_binding_id,
                "support_freeze_id": self.support_freeze_id,
            }

    source = Source()
    record = authority._binding_from_record(  # noqa: SLF001
        _portable_record(
            role="LIVE_ROW_SOURCE_BINDING",
            schema=authority._SOURCE_ROLE_SCHEMA[  # noqa: SLF001
                "LIVE_ROW_SOURCE_BINDING"
            ],
            semantic_id=source_id,
            id_field="binding_id",
            index=0,
            document=source.to_document(),
        )
    )
    epoch = SimpleNamespace(
        model_epoch_id=_id("epoch"),
        model=SimpleNamespace(
            model_id=_id("model"),
            rows=(row,),
        ),
        proof=SimpleNamespace(proof_id=_id("proof")),
        row_sources=(source,),
        support_freezes=(SimpleNamespace(freeze_id=freeze_id),),
    )
    return edge, epoch, (record,)


@pytest.mark.parametrize(
    "field",
    (
        "parent_numerical_row_id",
        "parent_row_binding_id",
        "support_descriptor_id",
        "row_source_binding_id",
        "support_freeze_id",
    ),
)
def test_edge_source_scalar_mutations_fail(
    monkeypatch: pytest.MonkeyPatch,
    field: str,
) -> None:
    edge, epoch, records = _edge_source_fixture(monkeypatch)
    commitment = authority._edge_source_commitment(  # noqa: SLF001
        edge=edge,
        epoch=epoch,
        source_records=records,
    )
    assert commitment.edge_id == edge.edge_id
    setattr(edge, field, _id(f"mutated-{field}"))
    with pytest.raises(
        authority.V075PortableDynamicChildProposalV2InvariantViolation
    ):
        authority._edge_source_commitment(  # noqa: SLF001
            edge=edge,
            epoch=epoch,
            source_records=records,
        )


def test_source_binding_is_content_addressed_caller_guarded_and_stale() -> None:
    args = (
        _id("target-record"),
        "DYNAMIC_CHILD_CLOSURE",
        _id("target-artifact"),
        _id("closure"),
        _id("epoch"),
        _id("epoch-record"),
        _id("model"),
        _id("model-record"),
        _id("proof"),
        _id("proof-record"),
        _id("frontier"),
        _id("head"),
        _id("occurrence"),
        _id("context"),
        None,
        (),
    )
    with pytest.raises(
        authority.V075PortableDynamicChildProposalV2InvariantViolation,
        match="caller-minted",
    ):
        authority.V075PortableDynamicChildSourceBindingV2(
            object(),
            *args,
        )
    binding = authority.V075PortableDynamicChildSourceBindingV2(
        authority._SOURCE_BINDING_ISSUER,  # noqa: SLF001
        *args,
    )
    assert binding.binding_id == binding.binding_id
    object.__setattr__(binding, "source_head_id", _id("mutated-head"))
    with pytest.raises(
        authority.V075PortableDynamicChildProposalV2InvariantViolation,
        match="stale",
    ):
        binding._assert_current()  # noqa: SLF001


def _dependency_fixture():
    edge = _node(
        "edge",
        0,
        "DYNAMIC_CHILD_CAUSAL_EDGE",
        local=False,
        resolved=False,
        frontier=(_id("edge"),),
    )
    state = _node(
        "state",
        1,
        "DYNAMIC_CHILD_STATE",
        portable=(edge.record_id,),
        local=False,
        resolved=False,
        frontier=(_id("state"),),
    )
    closure = _node(
        "closure",
        2,
        "DYNAMIC_CHILD_CLOSURE",
        portable=(state.record_id,),
        local=False,
        resolved=False,
        frontier=(_id("closure"),),
    )
    verification = _node(
        "verification",
        3,
        "DYNAMIC_CHILD_CLOSURE_VERIFICATION",
        local=False,
        resolved=False,
        frontier=(_id("verification"),),
    )
    model = _node(
        "model",
        4,
        "NUMERICAL_MODEL",
        local=False,
        resolved=False,
        frontier=(_id("model"),),
    )
    proof = _node(
        "proof",
        5,
        "NUMERICAL_PLANNING_PROOF",
        portable=(model.record_id,),
        local=False,
        resolved=False,
        frontier=(_id("proof"),),
    )
    epoch = _node(
        "epoch",
        6,
        "LIVE_MODEL_EPOCH",
        portable=(model.record_id, proof.record_id),
        local=True,
        resolved=False,
        frontier=(model.record_id, proof.record_id),
    )
    nodes = (
        edge,
        state,
        closure,
        verification,
        model,
        proof,
        epoch,
    )
    targets = (edge, state, closure, verification)
    source_triple = tuple(
        sorted((epoch.record_id, model.record_id, proof.record_id))
    )
    dependencies = {
        item.record_id: source_triple for item in targets
    }
    binding_ids = {
        item.record_id: _id(f"binding-{item.role}") for item in targets
    }
    return nodes, targets, model, proof, epoch, dependencies, binding_ids


def test_forward_source_edges_preserve_three_lanes_and_exact_frontier() -> None:
    (
        nodes,
        targets,
        model,
        proof,
        epoch,
        dependencies,
        binding_ids,
    ) = _dependency_fixture()
    replayed = authority._iterative_dynamic_child_dependency_nodes(  # noqa: SLF001
        upstream_nodes=nodes,
        locally_replayed_record_ids=frozenset(
            item.record_id for item in targets
        ),
        source_dependency_record_ids_by_target=dependencies,
        source_binding_ids_by_target=binding_ids,
    )
    by_id = {item.record_id: item for item in replayed}
    expected_frontier = tuple(
        sorted((model.record_id, proof.record_id))
    )
    for target in targets:
        item = by_id[target.record_id]
        assert item.local_semantic_authority_resolved is True
        assert item.semantically_resolved is False
        assert item.unresolved_frontier_record_ids == expected_frontier
        assert item.unresolved_frontier_roles == (
            "NUMERICAL_MODEL",
            "NUMERICAL_PLANNING_PROOF",
        )
        assert set(dependencies[target.record_id]) <= set(
            item.authority_local_semantic_dependency_record_ids
        )
        assert set(item.effective_dependency_record_ids) == (
            set(item.portable_declared_dependency_record_ids)
            | set(item.authority_local_semantic_dependency_record_ids)
        )
    assert by_id[epoch.record_id].unresolved_frontier_record_ids == (
        expected_frontier
    )
    assert {
        item.role for item in targets
    } == authority._PRESENT_ROOT_ONLY_ROLES  # noqa: SLF001
    assert not (
        authority._ABSENT_ROOT_ONLY_ROLES  # noqa: SLF001
        & {item.role for item in replayed}
    )


def test_missing_source_edge_and_cycle_are_rejected() -> None:
    (
        nodes,
        targets,
        _model,
        _proof,
        _epoch,
        dependencies,
        binding_ids,
    ) = _dependency_fixture()
    attacked = dict(dependencies)
    attacked[targets[0].record_id] = attacked[
        targets[0].record_id
    ][:-1]
    with pytest.raises(
        authority.V075PortableDynamicChildProposalV2InvariantViolation,
        match="epoch/model/proof",
    ):
        authority._iterative_dynamic_child_dependency_nodes(  # noqa: SLF001
            upstream_nodes=nodes,
            locally_replayed_record_ids=frozenset(
                item.record_id for item in targets
            ),
            source_dependency_record_ids_by_target=attacked,
            source_binding_ids_by_target=binding_ids,
        )

    first, second = nodes[:2]
    cycle_nodes = (
        _UpstreamNode(
            first.record_id,
            first.record_index,
            first.role,
            (second.record_id,),
            (),
            (second.record_id,),
            first.local_semantic_authority_resolved,
            first.semantically_resolved,
            first.unresolved_frontier_record_ids,
            first.dependency_depth,
        ),
        *nodes[1:],
    )
    with pytest.raises(
        authority.V075PortableDynamicChildProposalV2InvariantViolation,
        match="cycle",
    ):
        authority._iterative_dynamic_child_dependency_nodes(  # noqa: SLF001
            upstream_nodes=cycle_nodes,
            locally_replayed_record_ids=frozenset(
                item.record_id for item in targets
            ),
            source_dependency_record_ids_by_target=dependencies,
            source_binding_ids_by_target=binding_ids,
        )


def test_iterative_dependency_replay_scales_to_4096_depth() -> None:
    count = 4096
    identifiers = tuple(_id(f"deep-{index}") for index in range(count))
    nodes = tuple(
        _UpstreamNode(
            identifiers[index],
            index,
            "UPSTREAM_PUBLIC",
            (() if index == 0 else (identifiers[index - 1],)),
            (),
            (() if index == 0 else (identifiers[index - 1],)),
            True,
            True,
            (),
            index + 1,
        )
        for index in range(count)
    )
    replayed = authority._iterative_dynamic_child_dependency_nodes(  # noqa: SLF001
        upstream_nodes=nodes,
        locally_replayed_record_ids=frozenset(),
        source_dependency_record_ids_by_target={},
        source_binding_ids_by_target={},
    )
    assert len(replayed) == count
    assert replayed[-1].dependency_depth == 4096
    assert replayed[-1].semantically_resolved is True


def test_role_closure_tri_state_pickle_determinism_output_cap_and_gate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    status = authority.V075PortableDynamicChildProposalRoleStatusV2
    absent = authority.V075PortableDynamicChildProposalRoleClosureV2(
        authority._ROLE_CLOSURE_ISSUER,  # noqa: SLF001
        _id("bundle"),
        _id("graph"),
        _id("dag"),
        "DYNAMIC_CHILD_DISCOVERY_INTENT",
        status.NOT_PRESENT_IN_OCCURRENCE,
        (),
        (),
        (),
        (),
        (),
        (),
    )
    assert absent.status is status.NOT_PRESENT_IN_OCCURRENCE
    payload = {"b": 2, "a": 1}
    assert authority._hash("aggregate", payload) == authority._hash(  # noqa: SLF001
        "aggregate",
        payload,
    )
    with pytest.raises(TypeError, match="in-memory-only"):
        pickle.dumps(
            object.__new__(
                authority.V075PortableDynamicChildProposalTypedGraphV2
            )
        )
    monkeypatch.setattr(
        authority,
        "canonical_json_bytes",
        lambda _value: b"x" * (authority.MAX_OUTPUT_BYTES + 1),
    )
    fake = SimpleNamespace(to_document=lambda: {})
    with pytest.raises(
        authority.V075PortableDynamicChildProposalV2InvariantViolation,
        match="output byte cap",
    ):
        authority.V075PortableDynamicChildProposalReplayV2.canonical_bytes.fget(
            fake
        )
    with pytest.raises(
        authority.V075PortableDynamicChildProposalProductionV2NotReady
    ):
        authority.open_v075_production_from_portable_dynamic_child_proposal_v2()
