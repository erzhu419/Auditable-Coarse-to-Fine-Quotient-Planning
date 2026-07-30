from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import ast
import hashlib
import inspect
from pathlib import Path
from types import SimpleNamespace

import pytest

from acfqp.phase3e_ids import canonical_json_bytes
from acfqp import v075_batched_observer_authority_v2 as lineage
from acfqp import v075_portable_occurrence_evidence_bundle_v2 as portable
from acfqp import v075_portable_public_lineage_authority_v2 as authority


def _id(label: str) -> str:
    return hashlib.sha256(
        b"acfqp:v075-public-lineage-test:v2\x00" + label.encode()
    ).hexdigest()


@dataclass(frozen=True)
class _UpstreamNode:
    record_id: str
    record_index: int
    role: str
    direct_dependency_record_ids: tuple[str, ...]
    local_semantic_authority_resolved: bool
    semantically_resolved: bool


def test_contract_scope_and_all_production_locks_remain_closed() -> None:
    assert authority.PROPOSED_CONTRACT_VERSION == "1.73.0"
    assert authority.ROLE_ORDER == (
        "BATCH_PUBLIC_VERIFICATION",
        "BATCH_SEQUENCE_VERIFICATION",
        "CONSTRUCTION_LINEAGE",
    )
    assert authority.TERMINAL_CLASS == "ATTEMPT_CLOSURE_NONCERTIFICATE"
    assert authority.OFFICIAL_EXECUTION_ALLOWED is False
    assert authority.PRODUCTION_AUTHORIZING is False
    assert authority.SCIENTIFIC_ENDPOINT_CREDIT_ALLOWED is False
    assert authority.SOURCE_AUTHORITY_COMPLETE is False
    assert authority.CODE_PROVENANCE_COMPLETE is False
    assert authority.PORTABLE_SEMANTIC_REGISTRY_COMPLETE is False
    assert authority.FRESH_HELDOUT_ACCESS_ALLOWED is False
    assert authority.PRIVATE_INPUT_CHANNELS_ALLOWED is False
    assert authority.PRIVATE_REPLAY_PERFORMED is False
    assert authority.M1A_PRIVATE_VERIFICATION_CLAIM_CONSUMED is False
    assert authority.PLAN_CERTIFICATE_ISSUANCE_ALLOWED is False
    assert authority.INFEASIBILITY_CERTIFICATE_ISSUANCE_ALLOWED is False
    assert {
        "INFEASIBILITY_CERTIFICATE_ISSUANCE_ALLOWED",
        "MAX_OUTPUT_BYTES",
        "TERMINAL_CLASS",
        "TERMINAL_CODE",
        "TERMINAL_SCOPE",
    } <= set(authority.__all__)


def test_public_entrypoint_is_raw_only_and_calls_hardened_m2_first(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert tuple(
        inspect.signature(
            authority.replay_v075_portable_public_lineage_v2
        ).parameters
    ) == (
        "repository_root",
        "portable_bundle_bytes",
        "public_context_closure_bytes",
    )
    calls: list[str] = []

    def stop_at_m2(**_kwargs):
        calls.append("m2")
        raise RuntimeError("sentinel")

    def forbidden_bundle(*_args, **_kwargs):
        calls.append("bundle")
        raise AssertionError("local replay ran before hardened M2")

    monkeypatch.setattr(
        authority.m2,
        "replay_v075_portable_root_boundary_v2",
        stop_at_m2,
    )
    monkeypatch.setattr(
        authority.portable,
        "verify_v075_portable_occurrence_evidence_bundle_bytes_v2",
        forbidden_bundle,
    )
    with pytest.raises(
        authority.V075PortablePublicLineageV2InvariantViolation,
        match="hardened root-boundary replay failed",
    ):
        authority.replay_v075_portable_public_lineage_v2(
            repository_root=Path("."),
            portable_bundle_bytes=b"bundle",
            public_context_closure_bytes=b"context",
        )
    assert calls == ["m2"]


def test_source_has_no_private_replay_call_or_private_input_channel() -> None:
    source = inspect.getsource(authority)
    tree = ast.parse(source)
    called_attributes = {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
    }
    assert "verify_loaded_private_observer_batch_closure_v2" not in (
        called_attributes
    )
    assert "freeze_v075_construction_batch_occurrence_lineage_v2" not in (
        called_attributes
    )
    assert "replay_v075_signed_batch_occurrence_lineage_v2" not in (
        called_attributes
    )
    assert not any(
        isinstance(node, ast.Attribute)
        and node.attr == "closure_verification"
        for node in ast.walk(tree)
    )


def test_iterative_dependency_replay_closes_two_roles_and_keeps_lineage_open(
) -> None:
    root = _id("root")
    batch = _id("signed-batch")
    public = _id("public-verification")
    private = _id("private-verification")
    sequence = _id("sequence-verification")
    construction = _id("construction-lineage")
    nodes = (
        _UpstreamNode(root, 0, "OCCURRENCE_IDENTITY", (), True, True),
        _UpstreamNode(
            batch,
            1,
            "SIGNED_OBSERVATION_BATCH",
            (root,),
            True,
            True,
        ),
        _UpstreamNode(
            public,
            2,
            "BATCH_PUBLIC_VERIFICATION",
            (batch,),
            False,
            False,
        ),
        _UpstreamNode(
            private,
            3,
            "SIGNED_BATCH_JOURNAL_CLOSURE_VERIFICATION",
            (batch,),
            False,
            False,
        ),
        _UpstreamNode(
            sequence,
            4,
            "BATCH_SEQUENCE_VERIFICATION",
            (public,),
            False,
            False,
        ),
        _UpstreamNode(
            construction,
            5,
            "CONSTRUCTION_LINEAGE",
            tuple(sorted((private, sequence))),
            False,
            False,
        ),
    )
    replay = (  # noqa: SLF001
        authority._iterative_public_lineage_dependency_nodes
    )
    replayed = replay(
        upstream_nodes=nodes,
        locally_replayed_record_ids=frozenset(
            {public, sequence, construction}
        ),
    )
    by_id = {item.record_id: item for item in replayed}
    assert by_id[public].semantically_resolved is True
    assert by_id[sequence].semantically_resolved is True
    assert by_id[construction].semantically_resolved is False
    assert by_id[construction].unresolved_frontier_record_ids == (private,)
    assert by_id[construction].unresolved_frontier_roles == (
        "SIGNED_BATCH_JOURNAL_CLOSURE_VERIFICATION",
    )
    assert by_id[construction].resolver_kind is (
        authority.V075PortablePublicLineageResolverKindV2
        .M2_CONSTRUCTION_LINEAGE_PUBLIC_PROJECTION
    )


def test_iterative_dependency_replay_scales_to_4096_depth() -> None:
    count = 4096
    identifiers = tuple(_id(f"deep-{index}") for index in range(count))
    nodes = tuple(
        _UpstreamNode(
            identifiers[index],
            index,
            (
                "BATCH_PUBLIC_VERIFICATION"
                if index == count - 1
                else "UPSTREAM_PUBLIC"
            ),
            (() if index == 0 else (identifiers[index - 1],)),
            index != count - 1,
            index != count - 1,
        )
        for index in range(count)
    )
    replay = (  # noqa: SLF001
        authority._iterative_public_lineage_dependency_nodes
    )
    replayed = replay(
        upstream_nodes=nodes,
        locally_replayed_record_ids=frozenset({identifiers[-1]}),
    )
    assert len(replayed) == count
    assert replayed[-1].dependency_depth == 4096
    assert replayed[-1].semantically_resolved is True
    assert sum(
        len(item.direct_dependency_record_ids) for item in replayed
    ) == count - 1


def _binding(
    *,
    role: str,
    semantic_id: str,
    index: int = 7,
    dependencies: tuple[str, ...] = (),
) -> authority._PublicLineageRecordBindingV2:  # noqa: SLF001
    raw = canonical_json_bytes(
        {
            "schema": authority._ROLE_SCHEMA[role],  # noqa: SLF001
            authority._ROLE_ID_FIELD[role]: semantic_id,  # noqa: SLF001
        }
    )
    domain = portable._record_domain(role)  # noqa: SLF001
    payload = {
        "schema": "acfqp.v075_portable_evidence_artifact_record.v2",
        "schema_version": portable.SCHEMA_VERSION,
        "profile_key": portable.PROFILE_KEY,
        "index": index,
        "role": role,
        "artifact_schema": authority._ROLE_SCHEMA[role],  # noqa: SLF001
        "artifact_domain_tag": domain,
        "semantic_artifact_id": semantic_id,
        "dependency_record_ids": list(dependencies),
        "canonical_artifact_bytes_hex": raw.hex(),
        "raw_bytes_complete": True,
        "private_material_serialized": False,
        "official_execution_allowed": False,
    }
    return authority._PublicLineageRecordBindingV2(  # noqa: SLF001
        authority._BINDING_ISSUER,  # noqa: SLF001
        portable._hash(domain, payload),  # noqa: SLF001
        index,
        role,
        authority._ROLE_SCHEMA[role],  # noqa: SLF001
        semantic_id,
        dependencies,
        raw,
    )


def test_record_binding_rejects_stale_bytes_role_transplant_and_cached_id(
) -> None:
    binding = _binding(
        role="BATCH_PUBLIC_VERIFICATION",
        semantic_id=_id("binding-semantic"),
    )
    assert binding.commitment_document()["record_id"] == binding.record_id

    original_raw = binding.canonical_artifact_bytes
    object.__setattr__(
        binding,
        "canonical_artifact_bytes",
        canonical_json_bytes(
            {
                "schema": authority._ROLE_SCHEMA[  # noqa: SLF001
                    "BATCH_PUBLIC_VERIFICATION"
                ],
                "verification_id": _id("rehash-attack"),
            }
        ),
    )
    try:
        with pytest.raises(
            authority.V075PortablePublicLineageV2InvariantViolation
        ):
            binding._assert_current()  # noqa: SLF001
    finally:
        object.__setattr__(
            binding,
            "canonical_artifact_bytes",
            original_raw,
        )

    original_id = binding.record_id
    object.__setattr__(binding, "record_id", _id("stale-record"))
    try:
        with pytest.raises(
            authority.V075PortablePublicLineageV2InvariantViolation,
            match="stale or rehashed",
        ):
            binding._assert_current()  # noqa: SLF001
    finally:
        object.__setattr__(binding, "record_id", original_id)
    binding._assert_current()  # noqa: SLF001


class _Arm(Enum):
    NO_PRIOR = "NO_PRIOR"


class _Occurrence:
    def __init__(self) -> None:
        self.occurrence_id = _id("occurrence")
        self.target_tape_namespace_id = _id("namespace")
        self.context_id = _id("context")
        self.arm = _Arm.NO_PRIOR

    def to_document(self) -> dict:
        return {
            "schema": "synthetic.occurrence",
            "occurrence_id": self.occurrence_id,
            "target_tape_namespace_id": self.target_tape_namespace_id,
            "context_id": self.context_id,
            "arm": self.arm.value,
        }


class _Namespace:
    def __init__(self, namespace_id: str) -> None:
        self.target_tape_namespace_id = namespace_id

    def to_document(self) -> dict:
        return {
            "schema": "synthetic.namespace",
            "target_tape_namespace_id": self.target_tape_namespace_id,
        }


def test_lineage_public_payload_is_exact_without_private_verification_object(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    occurrence = _Occurrence()
    namespace = _Namespace(occurrence.target_tape_namespace_id)
    binding = SimpleNamespace(
        namespace=namespace,
        binding_id=_id("binding"),
        authorization_id=_id("authorization"),
        private_reveal_attestation_id=_id("reveal"),
        remote_main_anchor_id=_id("anchor"),
    )
    stream = SimpleNamespace(
        stream_id=_id("stream"),
        target_tape_namespace_id=occurrence.target_tape_namespace_id,
        context_id=occurrence.context_id,
        arm=occurrence.arm.value,
    )
    request = SimpleNamespace(
        occurrence_id=occurrence.occurrence_id,
        accepted_draw_count=7,
        stream_identity=stream,
    )
    batch = SimpleNamespace(batch_id=_id("batch"), request=request)
    entry = SimpleNamespace(entry_id=_id("entry"), batch=batch)
    closure_raw = b"synthetic-public-closure"
    closure = SimpleNamespace(
        occurrence_id=occurrence.occurrence_id,
        authority_binding=binding,
        session_public_id=_id("session"),
        closure_id=_id("closure"),
        entries=(entry,),
        canonical_bytes=closure_raw,
    )
    graph = SimpleNamespace(
        m0_result=SimpleNamespace(
            typed_graph=SimpleNamespace(occurrence=occurrence)
        ),
        closure=closure,
        batches=(batch,),
        record_bindings=(
            SimpleNamespace(
                role=authority.m1a.M1A_VERIFICATION_ROLE,
                semantic_artifact_id=_id("private-verification"),
            ),
        ),
    )
    upstream = SimpleNamespace(occurrence_id=occurrence.occurrence_id)
    monkeypatch.setattr(
        authority,
        "_m1a_graph",
        lambda _upstream, **_kwargs: graph,
    )
    public = (
        SimpleNamespace(
            batch_id=batch.batch_id,
            verification_id=_id("public-verification"),
        ),
    )
    sequence = (
        SimpleNamespace(
            stream_id=stream.stream_id,
            verification_id=_id("sequence-verification"),
        ),
    )
    namespace_sha = hashlib.sha256(
        canonical_json_bytes(namespace.to_document())
    ).hexdigest()
    commitments = (
        (
            "PUBLIC_TARGET_TAPE_NAMESPACE",
            occurrence.target_tape_namespace_id,
            namespace_sha,
        ),
        (
            "OBSERVER_OPEN_AUTHORIZATION",
            binding.authorization_id,
            _id("authorization-bytes"),
        ),
        (
            "PRIVATE_REVEAL_VERIFICATION_ATTESTATION",
            binding.private_reveal_attestation_id,
            _id("reveal-bytes"),
        ),
    )
    derive = (  # noqa: SLF001
        authority._expected_construction_lineage_document
    )
    document = derive(
        upstream=upstream,
        public_verifications=public,
        sequence_verifications=sequence,
        context_commitments=commitments,
    )
    assert document["scope"] == "CONSTRUCTION_ONLY"
    assert document["closure_verification_id"] == _id(
        "private-verification"
    )
    assert document["accepted_draw_count"] == 7
    assert document["batch_public_verification_ids"] == [
        _id("public-verification")
    ]
    assert document["batch_sequence_verification_ids"] == [
        _id("sequence-verification")
    ]
    assert document["production_authority_bytes_replayed"] is False
    payload = {
        key: value for key, value in document.items() if key != "lineage_id"
    }
    assert document["lineage_id"] == lineage._hash(  # noqa: SLF001
        "occurrence_lineage",
        payload,
    )
    for owner, field, foreign in (
        (request, "occurrence_id", _id("foreign-occurrence")),
        (
            stream,
            "target_tape_namespace_id",
            _id("foreign-namespace"),
        ),
        (stream, "context_id", _id("foreign-context")),
        (stream, "arm", "FOREIGN_ARM"),
    ):
        original = getattr(owner, field)
        setattr(owner, field, foreign)
        try:
            with pytest.raises(
                authority.V075PortablePublicLineageV2InvariantViolation,
                match="crossed occurrence/context/batch identities",
            ):
                derive(
                    upstream=upstream,
                    public_verifications=public,
                    sequence_verifications=sequence,
                    context_commitments=commitments,
                )
        finally:
            setattr(owner, field, original)


def _attestation(
    *,
    binding: authority._PublicLineageRecordBindingV2,  # noqa: SLF001
    graph_id: str,
    dag_id: str,
    unresolved_frontier: tuple[str, ...],
    unresolved_roles: tuple[str, ...],
) -> authority.V075PortablePublicLineageRecordAttestationV2:
    status = (
        authority.V075PortablePublicLineageRoleStatusV2.FULL_PUBLIC
        if not unresolved_frontier
        else authority.V075PortablePublicLineageRoleStatusV2
        .STRUCTURAL_ONLY_TRANSITIVE_UNRESOLVED
    )
    return authority.V075PortablePublicLineageRecordAttestationV2(
        authority._ATTESTATION_ISSUER,  # noqa: SLF001
        _id("bundle"),
        graph_id,
        dag_id,
        binding.record_id,
        binding.record_index,
        binding.role,
        binding.semantic_artifact_id,
        hashlib.sha256(binding.canonical_artifact_bytes).hexdigest(),
        len(binding.canonical_artifact_bytes),
        binding.dependency_record_ids,
        (),
        binding.dependency_record_ids,
        unresolved_frontier,
        unresolved_roles,
        authority._target_resolver_kind(binding.role),  # noqa: SLF001
        status,
    )


def test_role_closure_preserves_exact_tristate_and_stale_attestation_fails(
) -> None:
    graph_id = _id("graph")
    dag_id = _id("dag")
    private_id = _id("private-frontier")
    public_binding = _binding(
        role="BATCH_PUBLIC_VERIFICATION",
        semantic_id=_id("public"),
        index=1,
    )
    lineage_binding = _binding(
        role="CONSTRUCTION_LINEAGE",
        semantic_id=_id("lineage"),
        index=2,
        dependencies=(private_id,),
    )
    public_attestation = _attestation(
        binding=public_binding,
        graph_id=graph_id,
        dag_id=dag_id,
        unresolved_frontier=(),
        unresolved_roles=(),
    )
    lineage_attestation = _attestation(
        binding=lineage_binding,
        graph_id=graph_id,
        dag_id=dag_id,
        unresolved_frontier=(private_id,),
        unresolved_roles=(
            "SIGNED_BATCH_JOURNAL_CLOSURE_VERIFICATION",
        ),
    )
    closures = authority._build_role_closures(  # noqa: SLF001
        bundle_id=_id("bundle"),
        typed_graph_id=graph_id,
        dependency_dag_id=dag_id,
        bindings=(public_binding, lineage_binding),
        attestations=(public_attestation, lineage_attestation),
    )
    assert tuple(item.status for item in closures) == (
        authority.V075PortablePublicLineageRoleStatusV2.FULL_PUBLIC,
        authority.V075PortablePublicLineageRoleStatusV2
        .NOT_PRESENT_IN_OCCURRENCE,
        authority.V075PortablePublicLineageRoleStatusV2
        .STRUCTURAL_ONLY_TRANSITIVE_UNRESOLVED,
    )

    original = public_attestation._attestation_id  # noqa: SLF001
    object.__setattr__(
        public_attestation,
        "_attestation_id",
        _id("stale-attestation"),
    )
    try:
        with pytest.raises(
            authority.V075PortablePublicLineageV2InvariantViolation,
            match="identity is stale",
        ):
            public_attestation._assert_current()  # noqa: SLF001
    finally:
        object.__setattr__(
            public_attestation,
            "_attestation_id",
            original,
        )
    public_attestation._assert_current()  # noqa: SLF001


def test_production_gate_is_explicitly_closed() -> None:
    with pytest.raises(
        authority.V075PortablePublicLineageProductionV2NotReady
    ):
        authority.open_v075_production_from_portable_public_lineage_v2()
