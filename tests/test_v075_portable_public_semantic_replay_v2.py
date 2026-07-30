from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, replace
import hashlib
from pathlib import Path
from types import SimpleNamespace

import pytest

from acfqp.phase3e_ids import canonical_json_bytes
from acfqp import v075_observer_signed_batch_control_authority_v2 as control
from acfqp import (
    v075_observer_signed_multiround_occurrence_runner_v2 as multiround,
)
from acfqp import v075_portable_occurrence_evidence_bundle_v2 as portable
from acfqp import v075_portable_public_context_closure_v2 as context
from acfqp import v075_portable_public_semantic_replay_v2 as replay
from acfqp import v075_preopen_target_authorization_v2 as preopen
from acfqp import v075_public_graph_semantics_v1 as graph
from acfqp import v075_remote_main_anchor_verifier_v2 as remote
from acfqp import v075_five_arm_acquisition_authority_v2 as acquisition
from tests import test_v075_private_observer_boundary_v2 as observer_fixture
from tests.test_v075_observer_signed_multiround_occurrence_runner_v2 import (
    _exact_schedule,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BUNDLE_BYTES = b"strict-test-portable-bundle-bytes"


def _id(label: str) -> str:
    return hashlib.sha256(
        b"acfqp:v075-portable-public-semantic-test:v2"
        + b"\x00"
        + label.encode("utf-8")
    ).hexdigest()


def _manifest() -> context.V075PortablePublicContextSourceManifestV2:
    return context.V075PortablePublicContextSourceManifestV2(
        (
            context.V075PortablePublicContextSourceManifestEntryV2(
                "acfqp.phase3e_ids",
                "acfqp/phase3e_ids.py",
                _id("phase3e-source"),
                101,
            ),
            context.V075PortablePublicContextSourceManifestEntryV2(
                "acfqp.v075_portable_occurrence_evidence_bundle_v2",
                "acfqp/v075_portable_occurrence_evidence_bundle_v2.py",
                _id("bundle-source"),
                202,
            ),
        )
    )


@dataclass(frozen=True)
class _Record:
    index: int
    role: str
    semantic_artifact_id: str
    record_id: str
    dependency_record_ids: tuple[str, ...]
    canonical_artifact_bytes: bytes

    @property
    def artifact_schema(self) -> str:
        return portable.ROLE_SCHEMA_REGISTRY[self.role]

    @property
    def artifact_document(self) -> dict:
        value = portable._strict_json_document(  # noqa: SLF001
            self.canonical_artifact_bytes,
            label="M0 synthetic portable record",
        )
        assert type(value) is dict
        return value


def _semantic_id(role: str, value, ordinal: int) -> str:
    fields = {
        "OCCURRENCE_IDENTITY": "occurrence_id",
        "INITIAL_ROW_INTENT": "intent_id",
        "INITIAL_ACQUISITION_SCHEDULE": "schedule_id",
        "INITIAL_ACQUISITION_VERIFICATION": "verification_id",
        "SYMBOLIC_GRAPH_STATE": "state_id",
        "LEGAL_ACTION_CATALOGUE": "catalogue_id",
        "OBSERVATION_ROW_BINDING": "row_binding_id",
        "OBSERVER_SIGNED_SUPPORT_EVIDENCE": "evidence_id",
        "SHARED_SUPPORT_EPOCH": "epoch_id",
        "SHARED_SUPPORT_CHAIN": "chain_id",
        "PAIRING_AUTHORITY": "pairing_authority_id",
        "TRANSITION_STREAM": "stream_id",
        "SIGNED_BATCH_REQUEST": "request_id",
        "SIGNED_OBSERVATION_BATCH": "batch_id",
    }
    field = fields.get(role)
    if field is not None:
        return getattr(value, field)
    return _id(f"{role}-{ordinal}")


def _records(
    values: list[tuple[str, object]],
) -> tuple[_Record, ...]:
    provisional = []
    for index, (role, value) in enumerate(values):
        provisional.append(
            _Record(
                index,
                role,
                _semantic_id(role, value, index),
                _id(f"record-{index}-{role}"),
                (),
                canonical_json_bytes(value.to_document()),
            )
        )
    dependencies = portable._derive_dependency_graph(  # noqa: SLF001
        tuple(
            portable._DependencyNode(  # noqa: SLF001
                item.record_id,
                item.role,
                item.semantic_artifact_id,
                item.canonical_artifact_bytes,
            )
            for item in provisional
        )
    )
    by_id = {item.record_id: item for item in provisional}
    remaining = set(by_id)
    emitted = set()
    ordered = []
    while remaining:
        ready = sorted(
            item
            for item in remaining
            if dependencies[item] <= emitted
        )
        assert ready
        ordered.extend(ready)
        emitted.update(ready)
        remaining.difference_update(ready)
    return tuple(
        replace(
            by_id[record_id],
            index=index,
            dependency_record_ids=tuple(
                sorted(dependencies[record_id])
            ),
        )
        for index, record_id in enumerate(ordered)
    )


def _dedupe(values, identity):
    result = {}
    for value in values:
        result[identity(value)] = value
    return tuple(result[key] for key in sorted(result))


@pytest.fixture
def m0_graph(monkeypatch: pytest.MonkeyPatch):
    generated, salt, namespace, authorization, signer = (
        observer_fixture._fixture("portable-public-semantic-m0")
    )
    anchor = namespace.anchor
    original_to_document = remote.V075RemoteMainAnchorAttestationV2.to_document

    def ready_document(
        self: remote.V075RemoteMainAnchorAttestationV2,
    ) -> dict:
        value = original_to_document(self)
        value["preopen_v2_migration_status"] = "READY"
        return value

    monkeypatch.setattr(
        remote.V075RemoteMainAnchorAttestationV2,
        "to_document",
        ready_document,
    )
    monkeypatch.setattr(
        remote,
        "verify_v075_remote_main_anchor_independently_v2",
        lambda _root: anchor,
    )
    monkeypatch.setattr(
        preopen,
        "_verify_tracked_blob_closure_v2",
        lambda **_kwargs: (
            authorization.tracked_blobs,
            authorization.opaque_environment_commitment,
        ),
    )
    closure = context.freeze_v075_portable_public_context_evidence_closure_v2(
        repository_root=PROJECT_ROOT,
        source_manifest_bytes=_manifest().canonical_bytes,
        namespace_bytes=namespace.canonical_bytes,
        observer_open_authorization_bytes=authorization.canonical_bytes,
        private_reveal_verification_attestation_bytes=(
            authorization.private_reveal_attestation.canonical_bytes
        ),
    )
    schedule, verification = _exact_schedule(namespace, context_index=0)
    discovery = next(
        item
        for item in schedule.intents
        if item.kind is acquisition.V075InitialIntentKindV2.ROOT_DISCOVERY
    )
    bootstrap_epoch = graph.derive_shared_support_epoch_v1(
        namespace=namespace,
        row_binding=discovery.row_binding,
        epoch_index=0,
        evidence=(),
    )
    bootstrap_chain = graph.freeze_shared_support_chain_v1(
        namespace=namespace,
        row_binding=discovery.row_binding,
        epochs=(bootstrap_epoch,),
    )
    bootstrap_pairing = graph.freeze_five_arm_pairing_authority_v1(
        namespace=namespace,
        row_binding=discovery.row_binding,
        support_chain=bootstrap_chain,
    )
    discovery_stream = graph.derive_transition_stream_identity_v1(
        pairing_authority=bootstrap_pairing,
        arm=schedule.occurrence.arm.value,
    )
    controller = (
        control.open_v075_construction_controlled_private_observer_v2(
            authority=authorization,
            namespace=namespace,
            private_salt=salt,
            private_environment=generated.secret_laws_for_commitment(),
            observer_signer=signer,
            session_external_id=_id("session"),
            occurrence_identity=schedule.occurrence,
        )
    )
    intent = controller.prepare_batch_intent_v2(
        stream_identity=discovery_stream,
        semantic_authority_role=(
            control.V075ControlledBatchSemanticAuthorityRoleV2
            .INITIAL_SCHEDULE_ROW_INTENT
        ),
        semantic_authority_schema=(
            control.V075ControlledBatchSemanticAuthoritySchemaV2
            .INITIAL_SCHEDULE_ROW_INTENT
        ),
        semantic_artifact_id=discovery.intent_id,
        semantic_verification_id=verification.verification_id,
        stage=control.V075ControlledBatchStageV2.ROOT_DISCOVERY,
        round_index=0,
        support_freeze_id=None,
        accepted_draw_start=discovery.accepted_draw_start,
        accepted_draw_count=discovery.accepted_draw_count,
        accepted_draw_cap=discovery.accepted_draw_cap,
    )
    append = controller.execute_batch_intent_v2(intent)
    support = controller.freeze_complete_support_v2(
        discovery_append=append,
    )
    validation_stream = (
        control.derive_v075_controlled_validation_stream_v2(
            support_freeze=support,
        )
    )

    row_bindings = _dedupe(
        [item.row_binding for item in schedule.intents],
        lambda item: item.row_binding_id,
    )
    states = _dedupe(
        [
            *(item.catalogue.state for item in row_bindings),
            *(item.observed_state for item in support.evidence),
        ],
        lambda item: item.state_id,
    )
    catalogues = _dedupe(
        [item.catalogue for item in row_bindings],
        lambda item: item.catalogue_id,
    )
    streams = _dedupe(
        [discovery_stream, validation_stream],
        lambda item: item.stream_id,
    )
    pairings = _dedupe(
        [item.pairing_authority for item in streams],
        lambda item: item.pairing_authority_id,
    )
    chains = _dedupe(
        [item.support_chain for item in pairings],
        lambda item: item.chain_id,
    )
    epochs = _dedupe(
        [epoch for chain in chains for epoch in chain.epochs],
        lambda item: item.epoch_id,
    )
    values = [
        ("OCCURRENCE_IDENTITY", schedule.occurrence),
        *(("INITIAL_ROW_INTENT", item) for item in schedule.intents),
        ("INITIAL_ACQUISITION_SCHEDULE", schedule),
        ("INITIAL_ACQUISITION_VERIFICATION", verification),
        *(("SYMBOLIC_GRAPH_STATE", item) for item in states),
        *(("LEGAL_ACTION_CATALOGUE", item) for item in catalogues),
        *(("OBSERVATION_ROW_BINDING", item) for item in row_bindings),
        *(
            ("OBSERVER_SIGNED_SUPPORT_EVIDENCE", item)
            for item in support.evidence
        ),
        *(("SHARED_SUPPORT_EPOCH", item) for item in epochs),
        *(("SHARED_SUPPORT_CHAIN", item) for item in chains),
        *(("PAIRING_AUTHORITY", item) for item in pairings),
        *(("TRANSITION_STREAM", item) for item in streams),
        ("SIGNED_BATCH_REQUEST", append.batch.request),
        *(("SIGNED_BATCH_OUTCOME", item) for item in append.batch.outcomes),
        ("SIGNED_OBSERVATION_BATCH", append.batch),
    ]
    records = _records(values)
    fake_bundle = SimpleNamespace(
        records=records,
        bundle_id=_id("bundle"),
        occurrence_id=schedule.occurrence.occurrence_id,
    )

    def run(candidate_records=records, *, bundle_bytes=BUNDLE_BYTES):
        candidate = SimpleNamespace(
            records=candidate_records,
            bundle_id=fake_bundle.bundle_id,
            occurrence_id=fake_bundle.occurrence_id,
        )

        def verify(raw):
            if raw != bundle_bytes:
                raise ValueError("foreign bundle bytes")
            return candidate

        monkeypatch.setattr(
            portable,
            "verify_v075_portable_occurrence_evidence_bundle_bytes_v2",
            verify,
        )
        return replay.replay_v075_portable_public_semantics_v2(
            repository_root=PROJECT_ROOT,
            portable_bundle_bytes=bundle_bytes,
            public_context_closure_bytes=closure.canonical_bytes,
        )

    return {
        "run": run,
        "records": records,
        "closure": closure,
    }


def test_minimal_m0_replays_all_eleven_roles_and_keeps_locks_closed(
    m0_graph,
) -> None:
    result = m0_graph["run"]()
    document = result.to_document()
    assert set(item.role for item in result.attestations) == set(
        replay.M0_ROLE_ORDER
    )
    assert document["m0_role_count"] == 11
    assert document["typed_object_reconstruction_complete"] is True
    assert document["declared_dependency_semantics_complete"] is False
    assert document["m0_role_semantics_complete"] is False
    assert document["all_m0_records_dependency_replayed"] is False
    assert document["all_registered_arms_complete"] is False
    assert document["code_provenance_complete"] is False
    assert document["source_authority_complete"] is False
    assert document["portable_semantic_registry_complete"] is False
    assert document["overall_production_complete"] is False
    assert document["fresh_heldout_accessed"] is False
    assert document["official_execution_allowed"] is False
    assert all(
        item.to_document()["typed_object_reconstruction_complete"] is True
        for item in result.attestations
    )
    assert any(
        item.to_document()["semantic_replay_status"] == "INCOMPLETE"
        for item in result.attestations
    )
    assert {
        "SIGNED_BATCH_REQUEST",
        "SIGNED_BATCH_OUTCOME",
        "SIGNED_OBSERVATION_BATCH",
    } <= set(document["unresolved_dependency_roles"])
    assert document["unresolved_dependency_record_ids"]


def _mint_typed_graph(
    source: replay.V075PortablePublicM0TypedGraphV2,
    *,
    issuer,
    **changes,
):
    values = {
        "bundle_id": source.bundle_id,
        "public_context_closure_id": source.public_context_closure_id,
        "occurrence_id": source.occurrence_id,
        "target_tape_namespace_id": source.target_tape_namespace_id,
        "occurrence": source.occurrence,
        "schedule": source.schedule,
        "verification": source.verification,
        "intents": source.intents,
        "states": source.states,
        "catalogues": source.catalogues,
        "rows": source.rows,
        "support_evidence": source.support_evidence,
        "epochs": source.epochs,
        "chains": source.chains,
        "pairings": source.pairings,
        "transition_streams": source.transition_streams,
    }
    values.update(changes)
    return replay.V075PortablePublicM0TypedGraphV2(
        issuer,
        **values,
    )


def test_m0_typed_graph_is_honestly_consumable_and_not_serialized(
    m0_graph,
) -> None:
    result = m0_graph["run"]()
    typed_graph = result.typed_graph
    document = result.to_document()

    assert type(typed_graph) is replay.V075PortablePublicM0TypedGraphV2
    assert typed_graph.occurrence is typed_graph.schedule.occurrence
    assert typed_graph.namespace is typed_graph.schedule.profile.namespace
    assert typed_graph.intents == typed_graph.schedule.intents
    assert typed_graph.verification.schedule is typed_graph.schedule
    assert typed_graph.transition_streams
    assert all(
        item.arm == typed_graph.occurrence.arm.value
        for item in typed_graph.transition_streams
    )
    assert tuple(typed_graph.states_by_id) == tuple(
        item.state_id for item in typed_graph.states
    )
    assert tuple(typed_graph.catalogues_by_id) == tuple(
        item.catalogue_id for item in typed_graph.catalogues
    )
    assert tuple(typed_graph.rows_by_id) == tuple(
        item.row_binding_id for item in typed_graph.rows
    )
    assert tuple(typed_graph.evidence_by_id) == tuple(
        item.evidence_id for item in typed_graph.support_evidence
    )
    assert tuple(typed_graph.epochs_by_id) == tuple(
        item.epoch_id for item in typed_graph.epochs
    )
    assert tuple(typed_graph.chains_by_id) == tuple(
        item.chain_id for item in typed_graph.chains
    )
    assert tuple(typed_graph.pairings_by_id) == tuple(
        item.pairing_authority_id for item in typed_graph.pairings
    )
    assert tuple(typed_graph.streams_by_id) == tuple(
        item.stream_id for item in typed_graph.transition_streams
    )
    with pytest.raises(TypeError):
        typed_graph.states_by_id["foreign"] = typed_graph.states[0]
    assert all(
        type(ids) is tuple
        for ids in typed_graph.ordered_typed_ids.values()
    )
    assert all(
        type(ids) is tuple
        for ids in typed_graph.role_semantic_ids.values()
    )
    with pytest.raises(TypeError):
        typed_graph.ordered_typed_ids["state_ids"] = ()
    assert document["m0_typed_graph_id"] == typed_graph.graph_id
    assert document["m0_ordered_typed_ids"] == {
        key: list(ids)
        for key, ids in typed_graph.ordered_typed_ids.items()
    }
    assert document["m0_role_semantic_ids"] == {
        key: list(ids)
        for key, ids in typed_graph.role_semantic_ids.items()
    }
    assert document["m0_typed_graph_in_memory_only"] is True
    assert document["m0_typed_graph_issuer_gate_semantics"] == (
        "CONSTRUCTION_API_DISCIPLINE_ONLY"
    )
    assert (
        document["m0_typed_graph_python_process_security_boundary"]
        is False
    )
    assert document["m0_typed_objects_serialized"] is False
    assert document["source_artifacts_serialized"] is False
    assert not hasattr(typed_graph, "to_document")
    assert not hasattr(typed_graph, "canonical_bytes")
    assert "V075InitialAcquisitionScheduleV2" not in repr(result)


def test_m0_typed_graph_rejects_caller_mint_and_exact_typed_transplant(
    m0_graph,
) -> None:
    source = m0_graph["run"]().typed_graph
    with pytest.raises(
        replay.V075PortablePublicSemanticReplayV2InvariantViolation,
        match="caller-minted",
    ):
        _mint_typed_graph(source, issuer=object())

    namespace = source.schedule.profile.namespace
    foreign_context = namespace.family.replicate_contexts[1]
    foreign_catalogue = graph.root_catalogue_v1(foreign_context)
    foreign_row = graph.observation_row_binding_v1(
        foreign_context,
        foreign_catalogue,
        foreign_catalogue.actions[0],
    )
    transplanted_rows = tuple(
        sorted(
            (*source.rows[1:], foreign_row),
            key=lambda item: item.row_binding_id,
        )
    )
    with pytest.raises(
        replay.V075PortablePublicSemanticReplayV2InvariantViolation,
        match="row|schedule intent",
    ):
        _mint_typed_graph(
            source,
            issuer=replay._M0_TYPED_GRAPH_ISSUER,  # noqa: SLF001
            rows=transplanted_rows,
        )


def test_m0_typed_graph_rejects_ordered_id_permutation(
    m0_graph,
) -> None:
    source = m0_graph["run"]().typed_graph
    assert len(source.states) >= 2
    with pytest.raises(
        replay.V075PortablePublicSemanticReplayV2InvariantViolation,
        match="canonical ID order",
    ):
        _mint_typed_graph(
            source,
            issuer=replay._M0_TYPED_GRAPH_ISSUER,  # noqa: SLF001
            states=tuple(reversed(source.states)),
        )


def test_result_rejects_self_consistent_graph_with_missing_leaf_role_id(
    m0_graph,
) -> None:
    source_result = m0_graph["run"]()
    source = source_result.typed_graph
    assert len(source.transition_streams) >= 2
    reduced_graph = _mint_typed_graph(
        source,
        issuer=replay._M0_TYPED_GRAPH_ISSUER,  # noqa: SLF001
        transition_streams=source.transition_streams[:-1],
    )
    assert reduced_graph.graph_id != source.graph_id
    with pytest.raises(
        replay.V075PortablePublicSemanticReplayV2InvariantViolation,
        match="role semantic IDs differ",
    ):
        replay.V075PortablePublicSemanticReplayResultV2(
            replay._RESULT_ISSUER,  # noqa: SLF001
            source_result.bundle_id,
            source_result.occurrence_id,
            source_result.public_context_closure_id,
            source_result.repository_binding_id,
            source_result.source_manifest_id,
            source_result.target_tape_namespace_id,
            source_result.namespace_public_key_id,
            source_result.verified_arm,
            reduced_graph,
            source_result.attestations,
        )
    object.__setattr__(source_result, "_typed_graph", reduced_graph)
    try:
        with pytest.raises(
            replay.V075PortablePublicSemanticReplayV2InvariantViolation,
            match="role semantic IDs differ",
        ):
            _ = source_result.typed_graph
        with pytest.raises(
            replay.V075PortablePublicSemanticReplayV2InvariantViolation,
            match="role semantic IDs differ",
        ):
            source_result.to_document()
    finally:
        object.__setattr__(source_result, "_typed_graph", source)


def test_m0_typed_graph_rejects_stale_signed_leaf_and_graph_id_rehash(
    m0_graph,
) -> None:
    # This mutates one signed observed-state leaf, clears memoized descendant
    # IDs, restores canonical tuple order, and rehashes the graph ID.  It does
    # not construct a producer-valid replacement successor chain.
    source = m0_graph["run"]().typed_graph
    victim = source.support_evidence[0].observed_state
    original_ranks = victim.ranks
    original_failure = victim.failure
    original_graph_id = source.graph_id
    original_sequences = {
        name: getattr(source, name)
        for name in (
            "states",
            "catalogues",
            "rows",
            "support_evidence",
            "epochs",
            "chains",
            "pairings",
            "transition_streams",
        )
    }
    existing_state_ids = {item.state_id for item in source.states}
    candidate = None
    for vertex in range(len(victim.ranks)):
        for rank in range(victim.context.rank_cap + 1):
            ranks = list(victim.ranks)
            ranks[vertex] = rank
            if tuple(ranks) == victim.ranks:
                continue
            failure = not graph.legal_action_triples_v1(
                victim.context,
                tuple(ranks),
                False,
            )
            try:
                proposed = graph.V075SymbolicGraphStateV1(
                    victim.context,
                    tuple(ranks),
                    failure,
                )
            except graph.V075PublicGraphSemanticsInvariantViolation:
                continue
            if proposed.state_id not in existing_state_ids:
                candidate = proposed
                break
        if candidate is not None:
            break
    assert candidate is not None

    try:
        object.__setattr__(victim, "ranks", candidate.ranks)
        object.__setattr__(victim, "failure", candidate.failure)
        with graph._MEMOIZED_VALUES_LOCK:  # noqa: SLF001
            graph._MEMOIZED_VALUES.clear()  # noqa: SLF001
        for name, identity_name in (
            ("states", "state_id"),
            ("catalogues", "catalogue_id"),
            ("rows", "row_binding_id"),
            ("support_evidence", "evidence_id"),
            ("epochs", "epoch_id"),
            ("chains", "chain_id"),
            ("pairings", "pairing_authority_id"),
            ("transition_streams", "stream_id"),
        ):
            object.__setattr__(
                source,
                name,
                tuple(
                    sorted(
                        getattr(source, name),
                        key=lambda item: getattr(item, identity_name),
                    )
                ),
            )
        object.__setattr__(
            source,
            "_graph_id",
            replay._hash(  # noqa: SLF001
                "typed_graph",
                source._identity_payload(),  # noqa: SLF001
            ),
        )
        with pytest.raises(
            replay.V075PortablePublicSemanticReplayV2InvariantViolation,
            match="producer replay|transplanted|parent",
        ):
            source._assert_content_id()  # noqa: SLF001
    finally:
        object.__setattr__(victim, "ranks", original_ranks)
        object.__setattr__(victim, "failure", original_failure)
        for name, values in original_sequences.items():
            object.__setattr__(source, name, values)
        with graph._MEMOIZED_VALUES_LOCK:  # noqa: SLF001
            graph._MEMOIZED_VALUES.clear()  # noqa: SLF001
        object.__setattr__(source, "_graph_id", original_graph_id)


def _mutate_record(records, role, mutation):
    mutable = list(records)
    index = next(
        position
        for position, item in enumerate(mutable)
        if item.role == role
    )
    record = mutable[index]
    document = deepcopy(record.artifact_document)
    mutation(document)
    mutable[index] = replace(
        record,
        canonical_artifact_bytes=canonical_json_bytes(document),
    )
    return tuple(mutable)


def _rehash_real_bundle(document: dict) -> bytes:
    """Rehash every record and all later wrapper dependency references."""

    prior_to_current = {}
    for record in document["artifact_records"]:
        record["dependency_record_ids"] = sorted(
            prior_to_current.get(item, item)
            for item in record["dependency_record_ids"]
        )
        prior_id = record["record_id"]
        record["record_id"] = portable._hash(  # noqa: SLF001
            record["artifact_domain_tag"],
            {
                key: value
                for key, value in record.items()
                if key != "record_id"
            },
        )
        prior_to_current[prior_id] = record["record_id"]
    for binding in document["root_bindings"]:
        binding["record_ids"] = [
            prior_to_current.get(item, item)
            for item in binding["record_ids"]
        ]
    document["bundle_id"] = portable._hash(  # noqa: SLF001
        portable.DOMAIN_TAGS["bundle"],
        {
            key: value
            for key, value in document.items()
            if key != "bundle_id"
        },
    )
    return canonical_json_bytes(document)


def _record_document(document: dict, role: str) -> tuple[dict, dict]:
    record = next(
        item for item in document["artifact_records"] if item["role"] == role
    )
    artifact = portable._strict_json_document(  # noqa: SLF001
        bytes.fromhex(record["canonical_artifact_bytes_hex"]),
        label=f"real M0 {role} attack",
    )
    assert type(artifact) is dict
    return record, artifact


@pytest.fixture(scope="module")
def real_raw_m0_bundle():
    """One honest upstream K7 freeze; only external anchor facts are stubbed."""

    patcher = pytest.MonkeyPatch()
    original_to_document = (
        remote.V075RemoteMainAnchorAttestationV2.to_document
    )

    def ready_document(
        self: remote.V075RemoteMainAnchorAttestationV2,
    ) -> dict:
        value = original_to_document(self)
        value["preopen_v2_migration_status"] = "READY"
        return value

    patcher.setattr(
        remote.V075RemoteMainAnchorAttestationV2,
        "to_document",
        ready_document,
    )
    generated, salt, namespace, authorization, signer = (
        observer_fixture._fixture(
            "portable-observer-signed-multiround-capped"
        )
    )
    patcher.setattr(
        remote,
        "verify_v075_remote_main_anchor_independently_v2",
        lambda _root: namespace.anchor,
    )
    patcher.setattr(
        preopen,
        "_verify_tracked_blob_closure_v2",
        lambda **_kwargs: (
            authorization.tracked_blobs,
            authorization.opaque_environment_commitment,
        ),
    )
    schedule, verification = _exact_schedule(namespace, context_index=0)
    captured = {}

    def sink(roots):
        captured.update(roots)

    result = (
        multiround
        .run_v075_construction_observer_signed_multiround_occurrence_v2(
            repository_root=PROJECT_ROOT,
            namespace=namespace,
            schedule=schedule,
            schedule_verification=verification,
            authority=authorization,
            private_salt=salt,
            private_environment=generated.secret_laws_for_commitment(),
            observer_signer=signer,
            session_external_id=_id("real-k7-session"),
            evidence_sink=sink,
        )
    )
    assert result is captured["multiround_result"]
    artifact = portable.freeze_v075_portable_occurrence_evidence_bundle_v2(
        evidence_roots=captured,
    )
    closure = context.freeze_v075_portable_public_context_evidence_closure_v2(
        repository_root=PROJECT_ROOT,
        source_manifest_bytes=_manifest().canonical_bytes,
        namespace_bytes=namespace.canonical_bytes,
        observer_open_authorization_bytes=authorization.canonical_bytes,
        private_reveal_verification_attestation_bytes=(
            authorization.private_reveal_attestation.canonical_bytes
        ),
    )
    try:
        yield {
            "bundle": artifact,
            "closure": closure,
        }
    finally:
        patcher.undo()


@pytest.mark.parametrize(
    ("role", "mutation"),
    [
        (
            "INITIAL_ROW_INTENT",
            lambda value: value.__setitem__(
                "accepted_draw_count",
                value["accepted_draw_count"] + 1,
            ),
        ),
        (
            "INITIAL_ACQUISITION_SCHEDULE",
            lambda value: value["intents"].reverse(),
        ),
        (
            "INITIAL_ACQUISITION_SCHEDULE",
            lambda value: value.__setitem__(
                "target_tape_namespace_id",
                _id("foreign-namespace"),
            ),
        ),
        (
            "INITIAL_ACQUISITION_VERIFICATION",
            lambda value: value.__setitem__(
                "canonical_bytes_exact",
                False,
            ),
        ),
        (
            "SYMBOLIC_GRAPH_STATE",
            lambda value: value.__setitem__(
                "failure",
                not value["failure"],
            ),
        ),
        (
            "LEGAL_ACTION_CATALOGUE",
            lambda value: value["actions"].pop(),
        ),
        (
            "OBSERVATION_ROW_BINDING",
            lambda value: value["action"].__setitem__(
                0,
                value["action"][0] + 100,
            ),
        ),
        (
            "OBSERVER_SIGNED_SUPPORT_EVIDENCE",
            lambda value: value.__setitem__(
                "observer_signature_hex",
                ("00" + value["observer_signature_hex"][2:]),
            ),
        ),
        (
            "OBSERVER_SIGNED_SUPPORT_EVIDENCE",
            lambda value: value.__setitem__(
                "observer_signer_key_id",
                _id("foreign-key"),
            ),
        ),
        (
            "SHARED_SUPPORT_EPOCH",
            lambda value: value.__setitem__(
                "parent_epoch_id",
                _id("foreign-parent"),
            ),
        ),
        (
            "SHARED_SUPPORT_CHAIN",
            lambda value: value.__setitem__(
                "leaf_epoch_id",
                _id("foreign-leaf"),
            ),
        ),
        (
            "PAIRING_AUTHORITY",
            lambda value: value["arms"].reverse(),
        ),
        (
            "TRANSITION_STREAM",
            lambda value: value.__setitem__(
                "arm",
                (
                    "NO_PRIOR"
                    if value["arm"] != "NO_PRIOR"
                    else "OOD_ABSTENTION"
                ),
            ),
        ),
    ],
)
def test_m0_rejects_typed_reconstruction_mutations_after_raw_gate_stub(
    m0_graph,
    role,
    mutation,
) -> None:
    forged = _mutate_record(m0_graph["records"], role, mutation)
    with pytest.raises(
        replay.V075PortablePublicSemanticReplayV2InvariantViolation
    ):
        m0_graph["run"](forged)


@pytest.mark.parametrize("operation", ("missing", "extra"))
def test_m0_independently_rejects_declared_m0_dependency_edge_attacks(
    m0_graph,
    operation,
) -> None:
    records = list(m0_graph["records"])
    by_id = {item.record_id: item for item in records}
    target_index = next(
        index
        for index, item in enumerate(records)
        if item.role == "INITIAL_ACQUISITION_SCHEDULE"
    )
    target = records[target_index]
    if operation == "missing":
        changed = list(target.dependency_record_ids)
        removed = next(
            dependency_id
            for dependency_id in changed
            if by_id[dependency_id].role in replay.M0_ROLE_ORDER
        )
        changed.remove(removed)
    else:
        injected = next(
            item.record_id
            for item in records[:target.index]
            if item.role in replay.M0_ROLE_ORDER
            and item.record_id not in target.dependency_record_ids
        )
        changed = [*target.dependency_record_ids, injected]
    records[target_index] = replace(
        target,
        dependency_record_ids=tuple(sorted(changed)),
    )
    with pytest.raises(
        replay.V075PortablePublicSemanticReplayV2InvariantViolation,
        match="declared M0 dependencies",
    ):
        m0_graph["run"](tuple(records))


def test_m0_crosses_both_raw_gates_and_rejects_context_mutation(
    m0_graph,
) -> None:
    with pytest.raises(
        replay.V075PortablePublicSemanticReplayV2InvariantViolation,
        match="bundle or public-context raw replay",
    ):
        replay.replay_v075_portable_public_semantics_v2(
            repository_root=PROJECT_ROOT,
            portable_bundle_bytes=b"foreign",
            public_context_closure_bytes=(
                m0_graph["closure"].canonical_bytes
            ),
        )

    raw = bytearray(m0_graph["closure"].canonical_bytes)
    raw[-2] = ord("0") if raw[-2] != ord("0") else ord("1")
    with pytest.raises(
        replay.V075PortablePublicSemanticReplayV2InvariantViolation,
        match="bundle or public-context raw replay",
    ):
        replay.replay_v075_portable_public_semantics_v2(
            repository_root=PROJECT_ROOT,
            portable_bundle_bytes=BUNDLE_BYTES,
            public_context_closure_bytes=bytes(raw),
        )


def test_real_raw_k7_bundle_and_real_context_closure_cross_both_verifiers(
    real_raw_m0_bundle,
) -> None:
    result = replay.replay_v075_portable_public_semantics_v2(
        repository_root=PROJECT_ROOT,
        portable_bundle_bytes=real_raw_m0_bundle["bundle"].canonical_bytes,
        public_context_closure_bytes=(
            real_raw_m0_bundle["closure"].canonical_bytes
        ),
    )
    document = result.to_document()
    assert type(result.typed_graph) is (
        replay.V075PortablePublicM0TypedGraphV2
    )
    assert document["m0_typed_graph_id"] == result.typed_graph.graph_id
    assert result.typed_graph.streams_by_id
    assert document["verified_arm"] == "NO_PRIOR"
    assert document["supported_arm_coverage"] == ["NO_PRIOR"]
    assert document["typed_object_reconstruction_complete"] is True
    assert document["declared_dependency_semantics_complete"] is False
    assert document["all_registered_arms_complete"] is False
    assert document["code_provenance_complete"] is False
    assert document["unresolved_dependency_record_ids"]
    assert {
        "SIGNED_BATCH_REQUEST",
        "SIGNED_BATCH_OUTCOME",
        "SIGNED_OBSERVATION_BATCH",
    } <= set(document["unresolved_dependency_roles"])


def test_real_k7_disambiguates_cross_batch_shared_outcome_id_by_nested_bytes(
    real_raw_m0_bundle,
) -> None:
    records = real_raw_m0_bundle["bundle"].records
    outcome_records = tuple(
        item for item in records if item.role == "SIGNED_BATCH_OUTCOME"
    )
    outcome_records_by_public_id = {}
    for item in outcome_records:
        outcome_records_by_public_id.setdefault(
            item.artifact_document["outcome_id"],
            [],
        ).append(item)
    shared_ids = {
        outcome_id
        for outcome_id, items in outcome_records_by_public_id.items()
        if len(items) >= 2
        and len(
            {item.canonical_artifact_bytes for item in items}
        )
        >= 2
    }
    assert shared_ids

    support_record = next(
        item
        for item in records
        if item.role == "OBSERVER_SIGNED_SUPPORT_EVIDENCE"
        and item.artifact_document["discovery_outcome_id"] in shared_ids
    )
    support = support_record.artifact_document
    batch_record = next(
        item
        for item in records
        if item.role == "SIGNED_OBSERVATION_BATCH"
        and item.artifact_document["batch_id"]
        == support["discovery_batch_id"]
    )
    nested = tuple(
        item
        for item in batch_record.artifact_document["outcomes"]
        if item["outcome_id"] == support["discovery_outcome_id"]
        and item["count"] == support["discovery_outcome_count"]
    )
    assert len(nested) == 1
    expected_outcome_record = next(
        item
        for item in outcome_records
        if item.canonical_artifact_bytes
        == canonical_json_bytes(nested[0])
    )

    result = replay.replay_v075_portable_public_semantics_v2(
        repository_root=PROJECT_ROOT,
        portable_bundle_bytes=real_raw_m0_bundle["bundle"].canonical_bytes,
        public_context_closure_bytes=(
            real_raw_m0_bundle["closure"].canonical_bytes
        ),
    )
    support_attestation = next(
        item
        for item in result.attestations
        if item.record_id == support_record.record_id
    )
    same_public_id_record_ids = {
        item.record_id
        for item in outcome_records_by_public_id[
            support["discovery_outcome_id"]
        ]
    }
    assert (
        set(support_attestation.raw_field_checked_dependency_record_ids)
        & same_public_id_record_ids
    ) == {expected_outcome_record.record_id}


@pytest.mark.parametrize(
    "operation",
    (
        "missing",
        "extra",
        "role_mismatch",
        "stale_semantic_under_wrapper_rehash",
    ),
)
def test_real_raw_k7_rejects_wrapper_and_topology_rehash_attacks(
    real_raw_m0_bundle,
    operation,
) -> None:
    # `_rehash_real_bundle` recomputes transport record IDs, dependency
    # ancestry, roots, and the bundle ID only.  It deliberately does not
    # recompute the internal semantic descendant closure.
    attacked = deepcopy(real_raw_m0_bundle["bundle"].to_document())
    if operation == "missing":
        dependency_id = next(
            dependency_id
            for record in attacked["artifact_records"]
            if record["role"] in replay.M0_ROLE_ORDER
            for dependency_id in record["dependency_record_ids"]
        )
        attacked["artifact_records"] = [
            item
            for item in attacked["artifact_records"]
            if item["record_id"] != dependency_id
        ]
        for index, record in enumerate(attacked["artifact_records"]):
            record["index"] = index
        attacked["artifact_count"] = len(attacked["artifact_records"])
    elif operation == "extra":
        source = next(
            item
            for item in attacked["artifact_records"]
            if item["role"] == "SYMBOLIC_GRAPH_STATE"
        )
        duplicate = deepcopy(source)
        duplicate["index"] = len(attacked["artifact_records"])
        duplicate["record_id"] = _id("extra-record-placeholder")
        attacked["artifact_records"].append(duplicate)
        attacked["artifact_count"] += 1
    elif operation == "role_mismatch":
        record = next(
            item
            for item in attacked["artifact_records"]
            if item["role"] == "INITIAL_ROW_INTENT"
        )
        record["role"] = "TRANSITION_STREAM"
        record["artifact_schema"] = portable.ROLE_SCHEMA_REGISTRY[
            "TRANSITION_STREAM"
        ]
        record["artifact_domain_tag"] = (
            portable.DOMAIN_TAGS["record"] + ":transition_stream"
        )
    else:
        record, document = _record_document(
            attacked,
            "SYMBOLIC_GRAPH_STATE",
        )
        document["failure"] = not document["failure"]
        record["canonical_artifact_bytes_hex"] = (
            canonical_json_bytes(document).hex()
        )

    rehashed = _rehash_real_bundle(attacked)
    assert rehashed != real_raw_m0_bundle["bundle"].canonical_bytes
    with pytest.raises(
        replay.V075PortablePublicSemanticReplayV2InvariantViolation,
        match="bundle or public-context raw replay",
    ):
        replay.replay_v075_portable_public_semantics_v2(
            repository_root=PROJECT_ROOT,
            portable_bundle_bytes=rehashed,
            public_context_closure_bytes=(
                real_raw_m0_bundle["closure"].canonical_bytes
            ),
        )


def test_m0_production_remains_structurally_closed() -> None:
    assert replay.M0_ROLE_SEMANTICS_COMPLETE is False
    assert replay.ALL_REGISTERED_ARMS_COMPLETE is False
    assert replay.CODE_PROVENANCE_COMPLETE is False
    assert replay.SOURCE_AUTHORITY_COMPLETE is False
    assert replay.PORTABLE_SEMANTIC_REGISTRY_COMPLETE is False
    with pytest.raises(
        replay.V075PortablePublicSemanticReplayProductionV2NotReady,
        match="source authority",
    ):
        replay.open_v075_production_from_portable_public_semantics_v2()
