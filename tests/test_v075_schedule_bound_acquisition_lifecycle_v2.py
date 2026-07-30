from __future__ import annotations

from dataclasses import fields, replace
import hashlib
import inspect
from pathlib import Path

import pytest

from acfqp import v075_batch_native_statistical_backend_v1 as identity_backend
from acfqp import v075_batch_occurrence_lifecycle_authority_v2 as lifecycle_v2
from acfqp import v075_batched_observer_authority_v2 as batched_v2
from acfqp import v075_five_arm_acquisition_authority_v2 as acquisition_v2
from acfqp import v075_private_observer_boundary_v2 as observer_v2
from acfqp import v075_public_graph_semantics_v1 as graph
from acfqp import v075_registered_occurrence_worker_v1 as worker
from acfqp import v075_schedule_bound_acquisition_lifecycle_v2 as bound
from tests import test_v075_private_observer_boundary_v2 as observer_fixture


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def _id(label: str) -> str:
    return hashlib.sha256(
        b"acfqp:v075-schedule-bound-lifecycle-test:v2"
        + b"\x00"
        + label.encode("utf-8")
    ).hexdigest()


def _occurrence(namespace, arm):
    context = namespace.family.replicate_contexts[0]
    return (
        identity_backend
        .freeze_v075_batch_native_occurrence_identity_from_namespace_v2(
            namespace=namespace,
            context=context,
            arm=arm,
            occurrence_ordinal=acquisition_v2.ARM_ORDER.index(arm),
            threshold_profile=namespace.workload.threshold_profile,
            cap_profile=namespace.workload.cap_profile,
            source_prior_transport=None,
        )
    )


def _discovery_stream(namespace, row_binding, arm):
    epoch = graph.derive_shared_support_epoch_v1(
        namespace=namespace,
        row_binding=row_binding,
        epoch_index=0,
        evidence=(),
    )
    chain = graph.freeze_shared_support_chain_v1(
        namespace=namespace,
        row_binding=row_binding,
        epochs=(epoch,),
    )
    pairing = graph.freeze_five_arm_pairing_authority_v1(
        namespace=namespace,
        row_binding=row_binding,
        support_chain=chain,
    )
    return graph.derive_transition_stream_identity_v1(
        pairing_authority=pairing,
        arm=arm.value,
    )


def _support_evidence(namespace, signer, discovery, batch):
    representatives = {}
    for outcome in batch.outcomes:
        state = graph.V075SymbolicGraphStateV1(
            discovery.row_binding.context,
            outcome.next_ranks,
            outcome.failure,
        )
        key = (state.state_id, outcome.terminal)
        candidate = (batch.batch_id, batch.request.request_id, outcome.outcome_id)
        current = representatives.get(key)
        if current is None or candidate < current[0]:
            representatives[key] = (candidate, state, outcome)
    result = []
    for candidate, state, outcome in (
        representatives[key] for key in sorted(representatives)
    ):
        batch_id, request_id, outcome_id = candidate
        signing_bytes = (
            graph.batch_aggregate_support_evidence_signing_bytes_v1(
                namespace=namespace,
                row_binding=discovery.row_binding,
                observed_state=state,
                source_observer_epoch_index=0,
                discovery_request_id=request_id,
                discovery_batch_id=batch_id,
                discovery_outcome_id=outcome_id,
                discovery_outcome_count=outcome.count,
            )
        )
        result.append(
            graph.bind_batch_aggregate_support_evidence_v1(
                namespace=namespace,
                row_binding=discovery.row_binding,
                observed_state=state,
                source_observer_epoch_index=0,
                discovery_request_id=request_id,
                discovery_batch_id=batch_id,
                discovery_outcome_id=outcome_id,
                discovery_outcome_count=outcome.count,
                observer_signature_hex=(
                    signer.sign_observer_evidence_v1(signing_bytes)
                ),
            )
        )
    return tuple(result)


def _validation_stream(namespace, discovery, evidence, arm):
    bootstrap = discovery.pairing_authority.support_chain.leaf
    promoted = graph.derive_shared_support_epoch_v1(
        namespace=namespace,
        row_binding=discovery.row_binding,
        epoch_index=1,
        evidence=evidence,
        parent=bootstrap,
    )
    chain = graph.freeze_shared_support_chain_v1(
        namespace=namespace,
        row_binding=discovery.row_binding,
        epochs=(bootstrap, promoted),
    )
    pairing = graph.freeze_five_arm_pairing_authority_v1(
        namespace=namespace,
        row_binding=discovery.row_binding,
        support_chain=chain,
    )
    return graph.derive_transition_stream_identity_v1(
        pairing_authority=pairing,
        arm=arm.value,
    )


def _open_adapter(values, occurrence, marker):
    binding = observer_v2._require_exact_v2_binding(  # noqa: SLF001
        authority=values["authorization"],
        namespace=values["namespace"],
    )
    session = observer_v2._open_private_observer_from_verified_gate_v2(  # noqa: SLF001
        authority=values["authorization"],
        namespace=values["namespace"],
        binding=binding,
        private_salt=values["salt"],
        private_environment=values["generated"].secret_laws_for_commitment(),
        observer_signer=values["signer"],
        session_external_id=_id(marker),
    )
    return batched_v2.bind_v075_construction_occurrence_batched_observer_v2(
        session=session,
        occurrence_identity=occurrence,
    )


def _build_upstream(
    values,
    *,
    arm,
    marker,
    row_order=(0, 1),
    discovery_count=64,
    validation_count=2_048,
):
    namespace = values["namespace"]
    occurrence = _occurrence(namespace, arm)
    schedule = (
        acquisition_v2
        .freeze_v075_occurrence_initial_acquisition_schedule_v2(
            repository_root=REPOSITORY_ROOT,
            namespace=namespace,
            occurrence=occurrence,
        )
    )
    profile = schedule.profile
    slot = profile.occurrence_slot_for(
        context_id=occurrence.context_id,
        arm=arm,
    )
    context = namespace.family.replicate_contexts[0]
    catalogue = graph.root_catalogue_v1(context)
    rows = tuple(
        graph.observation_row_binding_v1(
            context,
            catalogue,
            action,
        )
        for action in catalogue.actions
    )
    discoveries = tuple(
        _discovery_stream(namespace, rows[index], arm)
        for index in row_order
    )
    adapter = _open_adapter(values, occurrence, marker)
    discovery_batches = tuple(
        adapter.observe_batch_v2(
            stream_identity=stream,
            accepted_draw_start=1,
            accepted_draw_count=discovery_count,
            accepted_draw_cap=64,
        )
        for stream in discoveries
    )
    validations = ()
    if arm is not acquisition_v2.DIRECT_ARM:
        validations = tuple(
            _validation_stream(
                namespace,
                stream,
                _support_evidence(
                    namespace,
                    values["signer"],
                    stream,
                    batch,
                ),
                arm,
            )
            for stream, batch in zip(discoveries, discovery_batches)
        )
        for stream in validations:
            adapter.observe_batch_v2(
                stream_identity=stream,
                accepted_draw_start=1,
                accepted_draw_count=validation_count,
                accepted_draw_cap=6_144,
            )
    closure = adapter.close_v2()
    known_streams = (*discoveries, *validations)
    lineage = batched_v2.freeze_v075_construction_batch_occurrence_lineage_v2(
        occurrence_identity=occurrence,
        closure=closure,
        authority=values["authorization"],
        namespace=namespace,
        known_stream_identities=known_streams,
        private_salt=values["salt"],
        private_environment=values["generated"].secret_laws_for_commitment(),
    )
    if arm is acquisition_v2.DIRECT_ARM:
        current = bound.freeze_v075_direct_initial_lifecycle_not_applicable_v2(
            profile=profile,
            expected_slot=slot,
            schedule=schedule,
        )
    else:
        current = (
            lifecycle_v2
            .freeze_v075_construction_batch_occurrence_lifecycle_v2(
                lineage=lineage,
                lineage_bytes=lineage.canonical_bytes,
                batch_closure_bytes=closure.canonical_bytes,
            )
        )
    return {
        "profile": profile,
        "slot": slot,
        "schedule": schedule,
        "lineage": lineage,
        "construction_authority": values["authorization"],
        "current": current,
    }


def _freeze(upstream):
    return bound.freeze_v075_schedule_bound_initial_acquisition_lifecycle_v2(
        repository_root=REPOSITORY_ROOT,
        profile=upstream["profile"],
        expected_slot=upstream["slot"],
        schedule=upstream["schedule"],
        lineage=upstream["lineage"],
        construction_authority=upstream["construction_authority"],
        current_lifecycle=upstream["current"],
    )


@pytest.fixture(scope="module")
def exact_graph():
    generated, salt, namespace, authorization, signer = (
        observer_fixture._fixture("schedule-bound-acquisition-lifecycle")
    )
    return {
        "generated": generated,
        "salt": salt,
        "namespace": namespace,
        "authorization": authorization,
        "signer": signer,
    }


@pytest.fixture(scope="module")
def valid_adaptive(exact_graph):
    upstream = _build_upstream(
        exact_graph,
        arm=worker.V075WorkerArmV1.NO_PRIOR,
        marker="valid-adaptive",
    )
    return upstream, _freeze(upstream)


@pytest.fixture(scope="module")
def valid_direct(exact_graph):
    upstream = _build_upstream(
        exact_graph,
        arm=worker.V075WorkerArmV1.MATCHED_DIRECT_GROUND,
        marker="valid-direct",
    )
    return upstream, _freeze(upstream)


def test_adaptive_initial_schedule_is_exactly_bound_and_noncertificate(
    valid_adaptive,
):
    upstream, result = valid_adaptive
    document = result.to_document()
    assert result.terminal_code is (
        bound.V075InitialAcquisitionTerminalCodeV2
        .INITIAL_COMPLETE_AWAITING_SOUND_PLANNER
    )
    assert document["terminal_scope"] == "CONSTRUCTION_ONLY"
    assert document["terminal_class"] == "ATTEMPT_CLOSURE_NONCERTIFICATE"
    assert document["proposal_input_bound"] is True
    assert document["proposal_ranking_executed"] is False
    assert document["full_acquisition_complete"] is False
    assert document["dynamic_acquisition_rounds_complete"] is False
    assert document["sound_planner_executed"] is False
    assert document["plan_certificate"] is False
    assert document["infeasibility_certificate"] is False
    assert result.counters.batch_count == 4
    assert result.counters.discovery_batch_count == 2
    assert result.counters.validation_batch_count == 2
    assert result.counters.support_freeze_count == 2
    assert result.counters.lifecycle_event_count == 6
    assert result.counters.intent_match_count == 6
    assert result.counters.pending_intent_count == 0
    assert upstream["lineage"].accepted_draw_count == 2 * (64 + 2_048)
    assert {
        item.accepted_draw_count
        for item in result.intent_matches
        if item.lane == "DISCOVERY"
    } == {64}
    assert {
        item.accepted_draw_count
        for item in result.intent_matches
        if item.lane == "VALIDATION"
    } == {2_048}
    assert all(
        item.proposal_view_id
        == upstream["schedule"].proposal_view.proposal_view_id
        for item in result.intent_matches
    )


def test_direct_is_explicit_typed_na_and_stops_before_child_expansion(
    valid_direct,
):
    upstream, result = valid_direct
    document = result.to_document()
    assert type(result.current_lifecycle) is (
        bound.V075InitialLifecycleNotApplicableV2
    )
    assert result.upstream_lifecycle_verification is None
    assert result.terminal_code is (
        bound.V075InitialAcquisitionTerminalCodeV2
        .ROOT_DISCOVERY_COMPLETE_AWAITING_CHILD_EXPANSION
    )
    assert document["current_lifecycle_kind"] == "NOT_APPLICABLE"
    assert document["proposal_view_id"] is None
    assert result.counters.batch_count == 2
    assert result.counters.discovery_batch_count == 2
    assert result.counters.validation_batch_count == 0
    assert result.counters.support_freeze_count == 0
    assert result.counters.pending_intent_count == 2
    assert upstream["lineage"].accepted_draw_count == 128
    assert {
        item.status for item in result.intent_matches
    } == {
        (
            bound.V075InitialIntentExecutionStatusV2
            .DIRECT_DISCOVERY_BATCH_MATCHED
        ),
        (
            bound.V075InitialIntentExecutionStatusV2
            .PENDING_DIRECT_CHILD_EXPANSION
        ),
    }


@pytest.mark.parametrize("fixture_name", ["valid_adaptive", "valid_direct"])
def test_exact_canonical_verifier_replays_all_typed_witnesses(
    fixture_name,
    request,
):
    upstream, result = request.getfixturevalue(fixture_name)
    replayed = (
        bound
        .verify_v075_schedule_bound_initial_acquisition_lifecycle_bytes_v2(
            repository_root=REPOSITORY_ROOT,
            profile=upstream["profile"],
            expected_slot=upstream["slot"],
            schedule=upstream["schedule"],
            lineage=upstream["lineage"],
            construction_authority=upstream["construction_authority"],
            current_lifecycle=upstream["current"],
            raw=result.canonical_bytes,
        )
    )
    assert replayed.result_id == result.result_id
    with pytest.raises(
        bound.V075ScheduleBoundAcquisitionLifecycleV2InvariantViolation
    ):
        (
            bound
            .verify_v075_schedule_bound_initial_acquisition_lifecycle_bytes_v2(
                repository_root=REPOSITORY_ROOT,
                profile=upstream["profile"],
                expected_slot=upstream["slot"],
                schedule=upstream["schedule"],
                lineage=upstream["lineage"],
                construction_authority=upstream["construction_authority"],
                current_lifecycle=upstream["current"],
                raw=result.canonical_bytes + b" ",
            )
        )


def _object_clone(value):
    forged = object.__new__(type(value))
    for item in fields(type(value)):
        if hasattr(value, item.name):
            object.__setattr__(forged, item.name, getattr(value, item.name))
    return forged


def _lineage_with_entries(upstream, entries):
    closure = _object_clone(upstream["lineage"].closure)
    object.__setattr__(closure, "entries", entries)
    lineage = _object_clone(upstream["lineage"])
    object.__setattr__(lineage, "closure", closure)
    attacked = dict(upstream)
    attacked["lineage"] = lineage
    return attacked


def test_omitted_reordered_and_wrong_count_aggregates_are_rejected(
    valid_adaptive,
):
    upstream, _result = valid_adaptive
    entries = upstream["lineage"].closure.entries
    omitted = _lineage_with_entries(upstream, entries[:-1])
    reordered = _lineage_with_entries(
        upstream,
        (entries[1], entries[0], *entries[2:]),
    )

    wrong_entry = _object_clone(entries[0])
    wrong_batch = _object_clone(entries[0].batch)
    wrong_request = _object_clone(entries[0].batch.request)
    object.__setattr__(
        wrong_request,
        "accepted_draw_count",
        wrong_request.accepted_draw_count - 1,
    )
    object.__setattr__(wrong_batch, "request", wrong_request)
    object.__setattr__(wrong_entry, "batch", wrong_batch)
    wrong_count = _lineage_with_entries(
        upstream,
        (wrong_entry, *entries[1:]),
    )
    for value in (omitted, reordered, wrong_count):
        with pytest.raises(
            bound.V075ScheduleBoundAcquisitionLifecycleV2InvariantViolation
        ):
            _freeze(value)


def test_object_new_closure_with_rehashed_invalid_signature_is_rejected(
    valid_direct,
):
    upstream, _result = valid_direct
    closure = _object_clone(upstream["lineage"].closure)
    signature = closure.observer_signature_hex
    object.__setattr__(
        closure,
        "observer_signature_hex",
        ("0" if signature[0] != "0" else "1") + signature[1:],
    )
    batches = tuple(entry.batch for entry in closure.entries)
    binding = closure.authority_binding
    verification = observer_v2.V075ObserverBatchClosureVerificationV2(
        observer_v2._BATCH_CLOSURE_VERIFICATION_ISSUER,
        closure.closure_id,
        closure.occurrence_id,
        tuple(batch.batch_id for batch in batches),
        binding.binding_id,
        binding.authorization_id,
        binding.private_reveal_attestation_id,
        binding.remote_main_anchor_id,
        binding.namespace.target_tape_namespace_id,
        len(batches),
        sum(batch.request.accepted_draw_count for batch in batches),
        len(
            {
                batch.request.stream_identity.stream_id
                for batch in batches
            }
        ),
    )
    source = upstream["lineage"]
    forged_lineage = batched_v2.V075BatchOccurrenceLineageV2(
        batched_v2._CONSTRUCTION_LINEAGE_ISSUER,
        source.scope,
        source.occurrence_identity,
        closure,
        verification,
        source.public_verifications,
        source.sequence_verifications,
        source.private_reveal_attestation_bytes_sha256,
        source.authorization_bytes_sha256,
        source.namespace_bytes_sha256,
        hashlib.sha256(closure.canonical_bytes).hexdigest(),
    )
    attacked = dict(upstream)
    attacked["lineage"] = forged_lineage
    with pytest.raises(
        bound.V075ScheduleBoundAcquisitionLifecycleV2InvariantViolation
    ):
        _freeze(attacked)


@pytest.mark.parametrize(
    "digest_field",
    [
        "private_reveal_attestation_bytes_sha256",
        "authorization_bytes_sha256",
    ],
)
def test_resealed_foreign_construction_authority_digest_is_rejected(
    valid_direct,
    digest_field,
):
    upstream, _result = valid_direct
    source = upstream["lineage"]
    values = {
        "private_reveal_attestation_bytes_sha256": (
            source.private_reveal_attestation_bytes_sha256
        ),
        "authorization_bytes_sha256": source.authorization_bytes_sha256,
    }
    values[digest_field] = _id(f"foreign-{digest_field}")
    forged_lineage = batched_v2.V075BatchOccurrenceLineageV2(
        batched_v2._CONSTRUCTION_LINEAGE_ISSUER,
        source.scope,
        source.occurrence_identity,
        source.closure,
        source.closure_verification,
        source.public_verifications,
        source.sequence_verifications,
        values["private_reveal_attestation_bytes_sha256"],
        values["authorization_bytes_sha256"],
        source.namespace_bytes_sha256,
        source.closure_bytes_sha256,
    )
    attacked = dict(upstream)
    attacked["lineage"] = forged_lineage
    with pytest.raises(
        bound.V075ScheduleBoundAcquisitionLifecycleV2InvariantViolation
    ):
        _freeze(attacked)


def test_wrong_support_foreign_proposal_and_lifecycle_object_new_fail(
    exact_graph,
    valid_adaptive,
):
    upstream, _result = valid_adaptive
    current = upstream["current"]
    freezes = current.support_freezes
    foreign_batch_id = next(
        batch.batch_id
        for batch in upstream["lineage"].batches[:2]
        if batch.batch_id not in freezes[0].source_discovery_batch_ids
    )
    wrong_freeze = replace(
        freezes[0],
        source_discovery_batch_ids=(foreign_batch_id,),
    )
    wrong_support = replace(
        current,
        support_freezes=(wrong_freeze, *freezes[1:]),
    )
    attacked = dict(upstream)
    attacked["current"] = wrong_support
    with pytest.raises(
        bound.V075ScheduleBoundAcquisitionLifecycleV2InvariantViolation
    ):
        _freeze(attacked)

    wrong_occurrence = _occurrence(
        exact_graph["namespace"],
        worker.V075WorkerArmV1.WRONG_CONSENSUS_PRIOR,
    )
    wrong_schedule = (
        acquisition_v2
        .freeze_v075_occurrence_initial_acquisition_schedule_v2(
            repository_root=REPOSITORY_ROOT,
            namespace=exact_graph["namespace"],
            occurrence=wrong_occurrence,
        )
    )
    forged_schedule = object.__new__(
        acquisition_v2.V075InitialAcquisitionScheduleV2
    )
    for item in fields(acquisition_v2.V075InitialAcquisitionScheduleV2):
        if hasattr(upstream["schedule"], item.name):
            object.__setattr__(
                forged_schedule,
                item.name,
                getattr(upstream["schedule"], item.name),
            )
    object.__setattr__(
        forged_schedule,
        "proposal_view",
        wrong_schedule.proposal_view,
    )
    attacked = dict(upstream)
    attacked["schedule"] = forged_schedule
    with pytest.raises(
        bound.V075ScheduleBoundAcquisitionLifecycleV2InvariantViolation
    ):
        _freeze(attacked)

    forged_lifecycle = object.__new__(
        lifecycle_v2.V075BatchOccurrenceLifecycleClosureV2
    )
    for item in fields(lifecycle_v2.V075BatchOccurrenceLifecycleClosureV2):
        if hasattr(current, item.name):
            object.__setattr__(
                forged_lifecycle,
                item.name,
                getattr(current, item.name),
            )
    object.__setattr__(
        forged_lifecycle,
        "accepted_draw_count",
        current.accepted_draw_count + 1,
    )
    attacked = dict(upstream)
    attacked["current"] = forged_lifecycle
    with pytest.raises(
        bound.V075ScheduleBoundAcquisitionLifecycleV2InvariantViolation
    ):
        _freeze(attacked)


def test_direct_rejects_missing_or_adaptive_lifecycle(valid_direct, valid_adaptive):
    direct, _result = valid_direct
    adaptive, _adaptive_result = valid_adaptive
    attacked = dict(direct)
    attacked["current"] = adaptive["current"]
    with pytest.raises(
        bound.V075ScheduleBoundAcquisitionLifecycleV2InvariantViolation
    ):
        _freeze(attacked)
    with pytest.raises(
        bound.V075ScheduleBoundAcquisitionLifecycleV2InvariantViolation
    ):
        bound.freeze_v075_schedule_bound_initial_acquisition_lifecycle_v2(
            repository_root=REPOSITORY_ROOT,
            profile=direct["profile"],
            expected_slot=direct["slot"],
            schedule=direct["schedule"],
            lineage=direct["lineage"],
            construction_authority=direct["construction_authority"],
            current_lifecycle=None,  # type: ignore[arg-type]
        )


def test_result_replace_and_object_new_witnesses_do_not_gain_authority(
    valid_adaptive,
):
    _upstream, result = valid_adaptive
    with pytest.raises(
        bound.V075ScheduleBoundAcquisitionLifecycleV2InvariantViolation
    ):
        replace(
            result,
            terminal_code=(
                bound.V075InitialAcquisitionTerminalCodeV2
                .ROOT_DISCOVERY_COMPLETE_AWAITING_CHILD_EXPANSION
            ),
        )
    forged = object.__new__(
        bound.V075ScheduleBoundInitialAcquisitionLifecycleV2
    )
    for item in fields(
        bound.V075ScheduleBoundInitialAcquisitionLifecycleV2
    ):
        if hasattr(result, item.name):
            object.__setattr__(forged, item.name, getattr(result, item.name))
    object.__setattr__(forged, "_result_id", _id("forged-result-id"))
    assert forged.canonical_bytes != result.canonical_bytes


def test_counters_are_aggregate_only_and_production_is_unconditionally_locked(
    valid_adaptive,
):
    _upstream, result = valid_adaptive
    counters = result.counters.to_document()
    assert counters["asymptotic_replay_work"] == (
        "O(BATCH_COUNT+OUTCOME_AGGREGATE_COUNT)"
    )
    assert counters["per_draw_records_read"] == 0
    assert counters["private_records_read"] == 0
    assert counters["target_calls"] == 0
    assert counters["kernel_calls"] == 0
    assert counters["j0_calls"] == 0
    assert counters["planner_calls"] == 0
    with pytest.raises(
        bound.V075ScheduleBoundAcquisitionProductionV2NotReady
    ):
        (
            bound
            .open_v075_production_schedule_bound_initial_acquisition_lifecycle_v2(
                object(),
                result=result,
            )
        )
    source = inspect.getsource(bound)
    assert ".observe_" not in source
    assert "SignedObservationRecord" not in source
    assert "kernel.step" not in source
    assert "j0_calls\": 0" in source
    assert "run_j0" not in source.lower()
    assert bound.PROPOSED_CONTRACT_VERSION == "1.48.0"
    assert bound.FRONTIER_RANKING_EXECUTED is False
    assert bound.DYNAMIC_ACQUISITION_ROUNDS_COMPLETE is False
