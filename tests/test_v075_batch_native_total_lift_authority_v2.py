from __future__ import annotations

from dataclasses import fields, replace
import hashlib
import inspect
import json
from pathlib import Path

import pytest

from acfqp.phase3e_ids import canonical_json_bytes
from acfqp import v075_batch_native_statistical_backend_v1 as identity_backend
from acfqp import v075_batch_native_total_lift_authority_v2 as lift
from acfqp import v075_batched_observer_authority_v2 as batched
from acfqp import v075_private_observer_boundary_v2 as observer
from acfqp import v075_production_occurrence_plan_v1 as production_plan
from acfqp import v075_production_occurrence_authority_v2 as occurrence
from acfqp import v075_public_graph_semantics_v1 as graph
from acfqp import v075_registered_occurrence_worker_v1 as worker
from tests import test_v075_private_observer_boundary_v2 as fixture


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
CONSTRUCTION_FIXTURE_DRAWS = 4


def _id(label: str) -> str:
    return hashlib.sha256(
        b"acfqp:v075-v2-total-lift-test:v1"
        + b"\x00"
        + label.encode("utf-8")
    ).hexdigest()


def _self_consistent_fake_source_transport():
    adapter_payload = {
        "schema": "acfqp.v075_source_prior_adapter.v1",
        "profile_key": worker.SOURCE_PRIOR_PROFILE_KEY,
        "source_only": True,
        "proposal_only": True,
        "may_certify": False,
        "source_work_reference_only": True,
        "source_work_embedded": False,
    }
    adapter_id = hashlib.sha256(
        worker.SOURCE_PRIOR_ADAPTER_DOMAIN.encode("utf-8")
        + b"\x00"
        + canonical_json_bytes(adapter_payload)
    ).hexdigest()
    adapter_bytes = canonical_json_bytes(
        {
            **adapter_payload,
            "catalogue": {"caller_authored_but_lightweight_valid": True},
            "adapter_id": adapter_id,
        }
    )
    verification_payload = {
        "schema": "acfqp.v075_source_prior_adapter_verification.v1",
        "profile_key": worker.SOURCE_PRIOR_PROFILE_KEY,
        "adapter_id": adapter_id,
        "recomputed_adapter_id": adapter_id,
        "adapter_bytes_sha256": hashlib.sha256(adapter_bytes).hexdigest(),
        "valid": True,
    }
    verification_id = hashlib.sha256(
        worker.SOURCE_PRIOR_VERIFICATION_DOMAIN.encode("utf-8")
        + b"\x00"
        + canonical_json_bytes(verification_payload)
    ).hexdigest()
    verification_bytes = canonical_json_bytes(
        {**verification_payload, "verification_id": verification_id}
    )
    return worker.V075SourcePriorTransportV1(
        adapter_bytes,
        verification_bytes,
        adapter_id,
        verification_id,
    )


def _walk_keys(value):
    if isinstance(value, dict):
        return tuple(value) + tuple(
            key for child in value.values() for key in _walk_keys(child)
        )
    if isinstance(value, list):
        return tuple(
            key for child in value for key in _walk_keys(child)
        )
    return ()


def _open_session(exact_v2_graph):
    generated, salt, namespace, authorization, signer = exact_v2_graph
    binding = observer._require_exact_v2_binding(  # noqa: SLF001
        authority=authorization,
        namespace=namespace,
    )
    session = observer._open_private_observer_from_verified_gate_v2(  # noqa: SLF001
        authority=authorization,
        namespace=namespace,
        binding=binding,
        private_salt=salt,
        private_environment=generated.secret_laws_for_commitment(),
        observer_signer=signer,
        session_external_id=_id("session"),
    )
    return session


def _discovery_stream(namespace, catalogue, action):
    row = graph.observation_row_binding_v1(
        catalogue.context,
        catalogue,
        action,
    )
    epoch = graph.derive_shared_support_epoch_v1(
        namespace=namespace,
        row_binding=row,
        epoch_index=0,
        evidence=(),
    )
    chain = graph.freeze_shared_support_chain_v1(
        namespace=namespace,
        row_binding=row,
        epochs=(epoch,),
    )
    pairing = graph.freeze_five_arm_pairing_authority_v1(
        namespace=namespace,
        row_binding=row,
        support_chain=chain,
    )
    return graph.derive_transition_stream_identity_v1(
        pairing_authority=pairing,
        arm=worker.V075WorkerArmV1.NO_PRIOR.value,
    )


def _support_evidence(namespace, signer, stream, batch):
    representatives = {}
    for outcome in batch.outcomes:
        state = graph.V075SymbolicGraphStateV1(
            stream.row_binding.context,
            outcome.next_ranks,
            outcome.failure,
        )
        current = representatives.get(state.state_id)
        if current is None or outcome.outcome_id < current.outcome_id:
            representatives[state.state_id] = outcome
    result = []
    for state_id in sorted(representatives):
        outcome = representatives[state_id]
        state = graph.V075SymbolicGraphStateV1(
            stream.row_binding.context,
            outcome.next_ranks,
            outcome.failure,
        )
        message = graph.batch_aggregate_support_evidence_signing_bytes_v1(
            namespace=namespace,
            row_binding=stream.row_binding,
            observed_state=state,
            source_observer_epoch_index=0,
            discovery_request_id=batch.request.request_id,
            discovery_batch_id=batch.batch_id,
            discovery_outcome_id=outcome.outcome_id,
            discovery_outcome_count=outcome.count,
        )
        result.append(
            graph.bind_batch_aggregate_support_evidence_v1(
                namespace=namespace,
                row_binding=stream.row_binding,
                observed_state=state,
                source_observer_epoch_index=0,
                discovery_request_id=batch.request.request_id,
                discovery_batch_id=batch.batch_id,
                discovery_outcome_id=outcome.outcome_id,
                discovery_outcome_count=outcome.count,
                observer_signature_hex=(
                    signer.sign_observer_evidence_v1(message)
                ),
            )
        )
    return tuple(result)


def _validation_stream(namespace, discovery, evidence):
    row = discovery.row_binding
    bootstrap = discovery.pairing_authority.support_chain.leaf
    promoted = graph.derive_shared_support_epoch_v1(
        namespace=namespace,
        row_binding=row,
        epoch_index=1,
        evidence=evidence,
        parent=bootstrap,
    )
    chain = graph.freeze_shared_support_chain_v1(
        namespace=namespace,
        row_binding=row,
        epochs=(bootstrap, promoted),
    )
    pairing = graph.freeze_five_arm_pairing_authority_v1(
        namespace=namespace,
        row_binding=row,
        support_chain=chain,
    )
    return graph.derive_transition_stream_identity_v1(
        pairing_authority=pairing,
        arm=worker.V075WorkerArmV1.NO_PRIOR.value,
    )


@pytest.fixture(scope="module")
def exact_v2_total_lift_graph():
    generated, salt, namespace, authorization, signer = fixture._fixture(
        "v2-total-lift"
    )
    context = namespace.family.replicate_contexts[1]
    occurrence_identity = (
        identity_backend
        .freeze_v075_batch_native_occurrence_identity_from_namespace_v2(
            namespace=namespace,
            context=context,
            arm=worker.V075WorkerArmV1.NO_PRIOR,
            occurrence_ordinal=0,
            threshold_profile=namespace.workload.threshold_profile,
            cap_profile=namespace.workload.cap_profile,
            source_prior_transport=None,
        )
    )
    session = _open_session(
        (generated, salt, namespace, authorization, signer)
    )
    adapter = batched.bind_v075_construction_occurrence_batched_observer_v2(
        session=session,
        occurrence_identity=occurrence_identity,
    )
    streams = []

    def observe_catalogues(catalogues):
        evidence_by_row = []
        for catalogue in catalogues:
            for action in catalogue.actions:
                discovery = _discovery_stream(
                    namespace,
                    catalogue,
                    action,
                )
                discovery_batch = adapter.observe_batch_v2(
                    stream_identity=discovery,
                    accepted_draw_start=1,
                    accepted_draw_count=CONSTRUCTION_FIXTURE_DRAWS,
                    accepted_draw_cap=CONSTRUCTION_FIXTURE_DRAWS,
                )
                evidence = _support_evidence(
                    namespace,
                    signer,
                    discovery,
                    discovery_batch,
                )
                validation = _validation_stream(
                    namespace,
                    discovery,
                    evidence,
                )
                adapter.observe_batch_v2(
                    stream_identity=validation,
                    accepted_draw_start=1,
                    accepted_draw_count=CONSTRUCTION_FIXTURE_DRAWS,
                    accepted_draw_cap=CONSTRUCTION_FIXTURE_DRAWS,
                )
                streams.extend((discovery, validation))
                evidence_by_row.append(evidence)
        return tuple(evidence_by_row)

    root_supports = observe_catalogues((graph.root_catalogue_v1(context),))
    child_states = {
        item.observed_state.state_id: item.observed_state
        for evidence in root_supports
        for item in evidence
        if not item.observed_state.failure
    }
    child_catalogues = tuple(
        graph.V075LegalActionCatalogueV1(
            context,
            child_states[state_id],
            1,
            graph.legal_action_triples_v1(
                context,
                child_states[state_id].ranks,
                child_states[state_id].failure,
            ),
        )
        for state_id in sorted(child_states)
    )
    observe_catalogues(child_catalogues)
    closure = adapter.close_v2()
    lineage = batched.freeze_v075_construction_batch_occurrence_lineage_v2(
        occurrence_identity=occurrence_identity,
        closure=closure,
        authority=authorization,
        namespace=namespace,
        known_stream_identities=tuple(streams),
        private_salt=salt,
        private_environment=generated.secret_laws_for_commitment(),
    )
    backend, total_lift, occurrence_control = (
        occurrence.execute_v075_construction_occurrence_v2(
            lineage=lineage,
            private_salt=salt,
            private_environment=generated.secret_laws_for_commitment(),
        )
    )
    return {
        "generated": generated,
        "salt": salt,
        "namespace": namespace,
        "authorization": authorization,
        "streams": tuple(streams),
        "closure": closure,
        "lineage": lineage,
        "backend": backend,
        "total_lift": total_lift,
        "occurrence_control": occurrence_control,
    }


def test_aggregate_backend_reaches_exact_total_lift_without_per_draw_expansion(
    exact_v2_total_lift_graph,
) -> None:
    backend = exact_v2_total_lift_graph["backend"]
    result = exact_v2_total_lift_graph["total_lift"]

    assert backend.structurally_complete is True
    assert backend.readiness_reason == "READY_FOR_EXACT_TOTAL_LIFT"
    assert backend.policy
    assert result.status is not lift.V075V2TotalLiftStatus.STATISTICAL_BACKEND_INCOMPLETE
    assert result.selected_policy_signature
    assert result.selected_failure_probability == (
        result.environment_failure_probability
        + result.policy_abort_failure_probability
    )
    assert backend.to_document()["per_draw_capability_count"] == 0
    assert result.to_document()["per_draw_capability_expansion"] is False
    assert result.to_document()["official_execution_allowed"] is False
    assert backend.to_document()["policy_source"] == (
        "AGGREGATE_V2_EVIDENCE_ONLY"
    )
    assert backend.to_document()["compiler_role"] == (
        "POST_ACQUISITION_GENERIC"
    )
    assert (
        backend.to_document()["arm_specific_acquisition_semantics_claimed"]
        is False
    )
    assert backend.to_document()["exact_private_environment_accessed"] is False
    assert result.to_document()["execution_lane"] == (
        "POST_PLAN_INDEPENDENT_EVALUATION"
    )
    assert result.to_document()["policy_selection_reopened"] is False
    assert result.environment_commitment_id == (
        exact_v2_total_lift_graph["namespace"]
        .environment_commitment.commitment_id
    )
    assert result.to_document()["environment_reveal_verification_id"]
    assert "optimal_policy_signature" not in _walk_keys(
        result.to_document()
    )
    assert "optimal_policy_signature" not in (
        lift.V075V2TotalLiftResult.__annotations__
    )


def test_object_new_backend_and_transplanted_lineage_cannot_enter_lift(
    exact_v2_total_lift_graph,
) -> None:
    original = exact_v2_total_lift_graph["backend"]
    forged = object.__new__(lift.V075V2StatisticalBackendResult)
    for name in (
        "_issuer",
        "scope",
        "occurrence_identity",
        "lineage_id",
        "rows",
        "policy",
        "structurally_complete",
        "readiness_reason",
        "_backend_id",
    ):
        object.__setattr__(forged, name, getattr(original, name))
    object.__setattr__(forged, "_issuer", object())
    with pytest.raises(lift.V075BatchNativeTotalLiftV2InvariantViolation):
        lift.evaluate_v075_construction_total_lift_v2(
            backend=forged,
            lineage=exact_v2_total_lift_graph["lineage"],
            private_salt=exact_v2_total_lift_graph["salt"],
            private_environment=(
                exact_v2_total_lift_graph["generated"]
                .secret_laws_for_commitment()
            ),
        )
    foreign = replace(
        original,
        lineage_id=_id("foreign-lineage"),
    )
    with pytest.raises(lift.V075BatchNativeTotalLiftV2InvariantViolation):
        lift.evaluate_v075_construction_total_lift_v2(
            backend=foreign,
            lineage=exact_v2_total_lift_graph["lineage"],
            private_salt=exact_v2_total_lift_graph["salt"],
            private_environment=(
                exact_v2_total_lift_graph["generated"]
                .secret_laws_for_commitment()
            ),
        )


def test_backend_rejects_object_new_invalid_closure_signature(
    exact_v2_total_lift_graph,
) -> None:
    lineage = exact_v2_total_lift_graph["lineage"]
    closure = lineage.closure
    forged_closure = object.__new__(
        observer.V075ObserverBatchJournalClosureV2
    )
    for item in fields(observer.V075ObserverBatchJournalClosureV2):
        object.__setattr__(
            forged_closure,
            item.name,
            (
                "00" * (len(closure.observer_signature_hex) // 2)
                if item.name == "observer_signature_hex"
                else getattr(closure, item.name)
            ),
        )
    forged_lineage = object.__new__(
        batched.V075BatchOccurrenceLineageV2
    )
    for item in fields(batched.V075BatchOccurrenceLineageV2):
        object.__setattr__(
            forged_lineage,
            item.name,
            (
                forged_closure
                if item.name == "closure"
                else getattr(lineage, item.name)
            ),
        )
    with pytest.raises(
        lift.V075BatchNativeTotalLiftV2InvariantViolation,
        match="full-graph reconstruction failed",
    ):
        lift.compile_v075_construction_statistical_backend_v2(
            lineage=forged_lineage
        )


def test_altered_claimed_bytes_and_private_environment_are_rejected(
    exact_v2_total_lift_graph,
) -> None:
    backend = exact_v2_total_lift_graph["backend"]
    total_lift = exact_v2_total_lift_graph["total_lift"]
    with pytest.raises(lift.V075BatchNativeTotalLiftV2InvariantViolation):
        lift.verify_v075_construction_total_lift_bytes_v2(
            lineage=exact_v2_total_lift_graph["lineage"],
            private_salt=exact_v2_total_lift_graph["salt"],
            private_environment=(
                exact_v2_total_lift_graph["generated"]
                .secret_laws_for_commitment()
            ),
            claimed_backend_bytes=backend.canonical_bytes + b" ",
            claimed_total_lift_bytes=total_lift.canonical_bytes,
        )
    environment = list(
        exact_v2_total_lift_graph["generated"].secret_laws_for_commitment()
    )
    environment[1] = environment[0]
    with pytest.raises(
        lift.V075BatchNativeTotalLiftV2InvariantViolation,
        match="differs from the namespace commitment",
    ):
        lift.evaluate_v075_construction_total_lift_v2(
            backend=backend,
            lineage=exact_v2_total_lift_graph["lineage"],
            private_salt=exact_v2_total_lift_graph["salt"],
            private_environment=tuple(environment),
        )


def test_v2_leaf_has_no_legacy_authority_projection_or_per_draw_path() -> None:
    source = inspect.getsource(lift)
    assert "v075_private_observer_boundary_v1" not in source
    assert "v075_batched_observer_authority_v1" not in source
    assert "v075_public_target_tape_namespace_v1" not in source
    assert "V075SignedObservationRecordV2" not in source
    assert ".observe_v2(" not in source
    assert lift.PER_DRAW_CAPABILITY_EXPANSION_ALLOWED is False
    assert lift.LEGACY_OBSERVER_AUTHORITY_PROJECTION_ALLOWED is False
    assert lift.LEGACY_TARGET_NAMESPACE_PROJECTION_ALLOWED is False
    assert lift.OFFICIAL_EXECUTION_ALLOWED is False
    assert (
        lift.EXACT_TOTAL_LIFT_IS_POST_PLAN_INDEPENDENT_EVALUATION
        is True
    )
    assert lift.EXACT_PRIVATE_ROWS_AVAILABLE_TO_BACKEND_POLICY is False
    assert (
        lift.EXACT_TOTAL_LIFT_COUNTS_AS_OPERATIONAL_ABSTRACT_PLANNING
        is False
    )
    backend_signature = inspect.signature(
        lift.compile_v075_construction_statistical_backend_v2
    )
    assert tuple(backend_signature.parameters) == ("lineage",)
    assert "private_environment" not in backend_signature.parameters
    assert canonical_json_bytes(
        {"scientific_endpoint_credit_allowed": False}
    )


def test_compact_stream_registry_and_occurrence_closure_replay(
    exact_v2_total_lift_graph,
) -> None:
    registry_bytes = occurrence.freeze_v075_compact_stream_registry_bytes_v2(
        occurrence_identity=(
            exact_v2_total_lift_graph["lineage"].occurrence_identity
        ),
        streams=exact_v2_total_lift_graph["streams"],
    )
    replayed_streams, registry_verification = (
        occurrence.load_v075_compact_stream_registry_bytes_v2(
            namespace=exact_v2_total_lift_graph["namespace"],
            occurrence_identity=(
                exact_v2_total_lift_graph["lineage"].occurrence_identity
            ),
            raw=registry_bytes,
        )
    )
    assert tuple(item.stream_id for item in replayed_streams) == tuple(
        sorted(
            item.stream_id
            for item in exact_v2_total_lift_graph["streams"]
        )
    )
    assert registry_verification.to_document()[
        "per_draw_support_evidence_used"
    ] is False

    backend = exact_v2_total_lift_graph["backend"]
    total_lift_result = exact_v2_total_lift_graph["total_lift"]
    result = exact_v2_total_lift_graph["occurrence_control"]
    replayed, verification = (
        occurrence.verify_v075_construction_occurrence_bytes_v2(
            lineage=exact_v2_total_lift_graph["lineage"],
            private_salt=exact_v2_total_lift_graph["salt"],
            private_environment=(
                exact_v2_total_lift_graph["generated"]
                .secret_laws_for_commitment()
            ),
            claimed_backend_bytes=backend.canonical_bytes,
            claimed_total_lift_bytes=total_lift_result.canonical_bytes,
            claimed_occurrence_bytes=result.canonical_bytes,
        )
    )
    assert replayed.control_id == result.control_id
    assert verification.occurrence_control_id == result.control_id
    assert result.to_document()["occurrence_identity"] == (
        exact_v2_total_lift_graph["lineage"]
        .occurrence_identity.to_document()
    )
    assert result.to_document()["lineage_bound"] is True
    assert result.to_document()["backend_bound"] is True
    assert result.to_document()["exact_total_lift_bound"] is True
    assert result.to_document()["upstream_v2_lifecycle_bound"] is False
    assert result.to_document()["five_arm_campaign_ready"] is False
    assert result.terminal_class is (
        occurrence.V075OccurrenceTerminalClassV2
        .ATTEMPT_CLOSURE_NONCERTIFICATE
    )
    assert result.terminal_code is (
        occurrence.V075OccurrenceTerminalCodeV2
        .CONSTRUCTION_CONTROL_ONLY
    )
    assert result.to_document()["schema"] == (
        "acfqp.v075_v2_construction_occurrence_control.v1"
    )
    assert tuple(item.value for item in occurrence.V075OccurrenceTerminalClassV2) == (
        "ATTEMPT_CLOSURE_NONCERTIFICATE",
    )
    assert tuple(item.value for item in occurrence.V075OccurrenceTerminalCodeV2) == (
        "CONSTRUCTION_CONTROL_ONLY",
    )
    forbidden = {
        "private_environment",
        "private_salt",
        "secret_law",
        "spawn_law",
        "law_probability",
    }
    assert forbidden.isdisjoint(_walk_keys(result.to_document()))
    assert forbidden.isdisjoint(_walk_keys(backend.to_document()))
    assert forbidden.isdisjoint(_walk_keys(total_lift_result.to_document()))


def test_public_occurrence_identity_byte_loader_replays_and_requires_source_transport(
    exact_v2_total_lift_graph,
    monkeypatch,
) -> None:
    identity = (
        exact_v2_total_lift_graph["lineage"].occurrence_identity
    )
    raw = canonical_json_bytes(identity.to_document())
    replayed = (
        identity_backend
        .load_v075_batch_native_occurrence_identity_bytes_from_namespace_v2(
            repository_root=REPOSITORY_ROOT,
            namespace=exact_v2_total_lift_graph["namespace"],
            raw=raw,
            expected_arm=worker.V075WorkerArmV1.NO_PRIOR,
            source_prior_transport_bytes=None,
        )
    )
    assert replayed.occurrence_id == identity.occurrence_id

    document = json.loads(raw)
    document["arm"] = "SOURCE_CONSENSUS_PRIOR"
    document["source_transport_id"] = _id("unverified-source-transport")
    with pytest.raises(
        identity_backend.V075BatchNativeBackendInvariantViolation,
        match="source-prior occurrence requires",
    ):
        identity_backend.load_v075_batch_native_occurrence_identity_bytes_from_namespace_v2(
            repository_root=REPOSITORY_ROOT,
            namespace=exact_v2_total_lift_graph["namespace"],
            raw=canonical_json_bytes(document),
            expected_arm=worker.V075WorkerArmV1.SOURCE_CONSENSUS_PRIOR,
            source_prior_transport_bytes=None,
        )

    transport = production_plan.load_tracked_v075_source_prior_transport_v1(
        REPOSITORY_ROOT
    )
    source_identity = (
        identity_backend
        .freeze_v075_batch_native_occurrence_identity_from_namespace_v2(
            namespace=exact_v2_total_lift_graph["namespace"],
            context=(
                exact_v2_total_lift_graph["namespace"]
                .family.replicate_contexts[1]
            ),
            arm=worker.V075WorkerArmV1.SOURCE_CONSENSUS_PRIOR,
            occurrence_ordinal=0,
            threshold_profile=(
                exact_v2_total_lift_graph["namespace"]
                .workload.threshold_profile
            ),
            cap_profile=(
                exact_v2_total_lift_graph["namespace"].workload.cap_profile
            ),
            source_prior_transport=transport,
        )
    )
    valid_transport_bytes = canonical_json_bytes(transport.to_document())
    valid_source = (
        identity_backend
        .load_v075_batch_native_occurrence_identity_bytes_from_namespace_v2(
            repository_root=REPOSITORY_ROOT,
            namespace=exact_v2_total_lift_graph["namespace"],
            raw=canonical_json_bytes(source_identity.to_document()),
            expected_arm=worker.V075WorkerArmV1.SOURCE_CONSENSUS_PRIOR,
            source_prior_transport_bytes=valid_transport_bytes,
        )
    )
    assert valid_source.occurrence_id == source_identity.occurrence_id
    fake_transport = _self_consistent_fake_source_transport()
    fake_transport_bytes = canonical_json_bytes(fake_transport.to_document())
    assert type(fake_transport) is worker.V075SourcePriorTransportV1
    assert fake_transport.transport_id != transport.transport_id
    with pytest.raises(
        identity_backend.V075BatchNativeBackendInvariantViolation,
        match="differs from complete tracked authority replay",
    ):
        identity_backend.load_v075_batch_native_occurrence_identity_bytes_from_namespace_v2(
            repository_root=REPOSITORY_ROOT,
            namespace=exact_v2_total_lift_graph["namespace"],
            raw=canonical_json_bytes(source_identity.to_document()),
            expected_arm=worker.V075WorkerArmV1.SOURCE_CONSENSUS_PRIOR,
            source_prior_transport_bytes=fake_transport_bytes,
        )
    with pytest.raises(
        identity_backend.V075BatchNativeBackendInvariantViolation,
        match="non-source occurrence rejects",
    ):
        identity_backend.load_v075_batch_native_occurrence_identity_bytes_from_namespace_v2(
            repository_root=REPOSITORY_ROOT,
            namespace=exact_v2_total_lift_graph["namespace"],
            raw=raw,
            expected_arm=worker.V075WorkerArmV1.NO_PRIOR,
            source_prior_transport_bytes=fake_transport_bytes,
        )
    source_reads = 0

    def forbidden_source_read(_repository_root):
        nonlocal source_reads
        source_reads += 1
        raise AssertionError("unverified arm triggered SOURCE authority read")

    monkeypatch.setattr(
        production_plan,
        "load_tracked_v075_source_prior_transport_v1",
        forbidden_source_read,
    )
    with pytest.raises(
        identity_backend.V075BatchNativeBackendInvariantViolation,
        match="expected arm",
    ):
        identity_backend.load_v075_batch_native_occurrence_identity_bytes_from_namespace_v2(
            repository_root=REPOSITORY_ROOT,
            namespace=exact_v2_total_lift_graph["namespace"],
            raw=raw,
            expected_arm=worker.V075WorkerArmV1.SOURCE_CONSENSUS_PRIOR,
            source_prior_transport_bytes=None,
        )
    assert source_reads == 0


def test_stream_registry_tamper_and_occurrence_byte_attack_fail(
    exact_v2_total_lift_graph,
) -> None:
    streams = exact_v2_total_lift_graph["streams"]
    registry_bytes = occurrence.freeze_v075_compact_stream_registry_bytes_v2(
        occurrence_identity=(
            exact_v2_total_lift_graph["lineage"].occurrence_identity
        ),
        streams=streams,
    )
    with pytest.raises(occurrence.V075ProductionOccurrenceV2InvariantViolation):
        occurrence.load_v075_compact_stream_registry_bytes_v2(
            namespace=exact_v2_total_lift_graph["namespace"],
            occurrence_identity=(
                exact_v2_total_lift_graph["lineage"].occurrence_identity
            ),
            raw=registry_bytes + b" ",
        )
    foreign_arm_stream = graph.derive_transition_stream_identity_v1(
        pairing_authority=streams[0].pairing_authority,
        arm=worker.V075WorkerArmV1.WRONG_CONSENSUS_PRIOR.value,
    )
    with pytest.raises(
        occurrence.V075ProductionOccurrenceV2InvariantViolation,
        match="mixed",
    ):
        occurrence.freeze_v075_compact_stream_registry_bytes_v2(
            occurrence_identity=(
                exact_v2_total_lift_graph["lineage"].occurrence_identity
            ),
            streams=(streams[0], foreign_arm_stream),
        )
    with pytest.raises(
        occurrence.V075ProductionOccurrenceV2InvariantViolation,
        match="occurrence-transplanted",
    ):
        occurrence.freeze_v075_compact_stream_registry_bytes_v2(
            occurrence_identity=(
                exact_v2_total_lift_graph["lineage"].occurrence_identity
            ),
            streams=(foreign_arm_stream,),
        )
    backend = exact_v2_total_lift_graph["backend"]
    total_lift_result = exact_v2_total_lift_graph["total_lift"]
    result = exact_v2_total_lift_graph["occurrence_control"]
    with pytest.raises(occurrence.V075ProductionOccurrenceV2InvariantViolation):
        occurrence.verify_v075_construction_occurrence_bytes_v2(
            lineage=exact_v2_total_lift_graph["lineage"],
            private_salt=exact_v2_total_lift_graph["salt"],
            private_environment=(
                exact_v2_total_lift_graph["generated"]
                .secret_laws_for_commitment()
            ),
            claimed_backend_bytes=backend.canonical_bytes,
            claimed_total_lift_bytes=total_lift_result.canonical_bytes,
            claimed_occurrence_bytes=result.canonical_bytes + b" ",
        )


def test_same_row_latest_epoch_cannot_mix_stream_or_support_identity() -> None:
    generated, salt, namespace, authorization, signer = fixture._fixture(
        "v2-mixed-latest-support"
    )
    context = namespace.family.replicate_contexts[1]
    identity = (
        identity_backend
        .freeze_v075_batch_native_occurrence_identity_from_namespace_v2(
            namespace=namespace,
            context=context,
            arm=worker.V075WorkerArmV1.NO_PRIOR,
            occurrence_ordinal=0,
            threshold_profile=namespace.workload.threshold_profile,
            cap_profile=namespace.workload.cap_profile,
            source_prior_transport=None,
        )
    )
    session = _open_session(
        (generated, salt, namespace, authorization, signer)
    )
    adapter = batched.bind_v075_construction_occurrence_batched_observer_v2(
        session=session,
        occurrence_identity=identity,
    )
    root = graph.root_catalogue_v1(context)
    discovery = _discovery_stream(namespace, root, root.actions[0])
    discovery_batch = adapter.observe_batch_v2(
        stream_identity=discovery,
        accepted_draw_start=1,
        accepted_draw_count=64,
        accepted_draw_cap=64,
    )
    evidence = _support_evidence(
        namespace,
        signer,
        discovery,
        discovery_batch,
    )
    assert len(evidence) >= 2
    validation_full = _validation_stream(
        namespace,
        discovery,
        evidence,
    )
    validation_subset = _validation_stream(
        namespace,
        discovery,
        evidence[:-1],
    )
    assert validation_full.support_epoch_id != (
        validation_subset.support_epoch_id
    )
    for validation in (validation_full, validation_subset):
        adapter.observe_batch_v2(
            stream_identity=validation,
            accepted_draw_start=1,
            accepted_draw_count=64,
            accepted_draw_cap=64,
        )
    closure = adapter.close_v2()
    lineage = batched.freeze_v075_construction_batch_occurrence_lineage_v2(
        occurrence_identity=identity,
        closure=closure,
        authority=authorization,
        namespace=namespace,
        known_stream_identities=(
            discovery,
            validation_full,
            validation_subset,
        ),
        private_salt=salt,
        private_environment=generated.secret_laws_for_commitment(),
    )
    with pytest.raises(
        lift.V075BatchNativeTotalLiftV2InvariantViolation,
        match="mixes stream or support identities",
    ):
        lift.compile_v075_construction_statistical_backend_v2(
            lineage=lineage
        )


def test_production_occurrence_entry_is_bytes_only_and_currently_locked(
    monkeypatch,
) -> None:
    signature = inspect.signature(
        occurrence.execute_v075_production_occurrence_bytes_v2
    )
    portable = {
        "private_reveal_attestation_bytes",
        "claimed_authorization_bytes",
        "namespace_bytes",
        "occurrence_identity_bytes",
        "compact_stream_registry_bytes",
        "batch_closure_bytes",
    }
    assert portable <= set(signature.parameters)
    assert not {
        "lineage",
        "backend",
        "total_lift",
        "known_stream_identities",
    } & set(signature.parameters)
    assert {"private_salt", "private_environment"} <= set(
        signature.parameters
    )
    assert {
        "verified_acquisition_terminal_bytes",
        "verified_lifecycle_bytes",
        "verified_lifecycle_verification_bytes",
    } <= set(signature.parameters)
    assert occurrence.PRODUCTION_ENTRY_PORTABLE_INPUTS_BYTES_ONLY is True
    assert occurrence.OFFICIAL_EXECUTION_ALLOWED is False
    assert not hasattr(occurrence, "_PRODUCTION_RESULT_ISSUER")
    assert not hasattr(lift, "compile_v075_production_statistical_backend_v2")
    assert not hasattr(lift, "evaluate_v075_production_total_lift_v2")
    assert tuple(lift.V075V2BackendScope) == (
        lift.V075V2BackendScope.CONSTRUCTION_ONLY,
    )
    assert not hasattr(occurrence, "V075ProductionOccurrenceResultV2")

    monkeypatch.setattr(occurrence, "OFFICIAL_EXECUTION_ALLOWED", True)
    with pytest.raises(
        occurrence.V075ProductionOccurrenceV2NotReady,
        match=occurrence.PRODUCTION_BLOCKER,
    ):
        occurrence.execute_v075_production_occurrence_bytes_v2(
            repository_root=REPOSITORY_ROOT,
            private_reveal_attestation_bytes=b"untrusted",
            claimed_authorization_bytes=b"untrusted",
            namespace_bytes=b"untrusted",
            occurrence_identity_bytes=b"untrusted",
            source_prior_transport_bytes=None,
            compact_stream_registry_bytes=b"untrusted",
            batch_closure_bytes=b"untrusted",
            verified_acquisition_terminal_bytes=b"not-yet-bound",
            verified_lifecycle_bytes=b"not-yet-bound",
            verified_lifecycle_verification_bytes=b"not-yet-bound",
            private_salt=b"untrusted",
            private_environment=object(),
        )
    assert not hasattr(
        occurrence,
        "freeze_v075_private_environment_input_bytes_v2",
    )
