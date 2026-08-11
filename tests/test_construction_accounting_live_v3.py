from __future__ import annotations

from dataclasses import replace
import hashlib

import pytest

from acfqp import construction_accounting_live_v3 as live
from acfqp import construction_accounting_registry_v3 as registry_v3
from acfqp import construction_accounting_registry_v4 as registry_v4
from acfqp.phase3e_ids import (
    CONSTRUCTION_ACTUAL_PROJECTION_PROOF_V3_DOMAIN,
    CONSTRUCTION_COMPARISON_VECTOR_V3_DOMAIN,
    CONSTRUCTION_COUNTER_RECORD_V3_DOMAIN,
    CONSTRUCTION_OPERATION_EVENT_V3_DOMAIN,
    CONSTRUCTION_STAGE_COMPLETION_ATTESTATION_V3_DOMAIN,
    CONSTRUCTION_STAGE_START_ATTESTATION_V3_DOMAIN,
    CONSTRUCTION_WORK_VECTOR_V3_DOMAIN,
    PHASE3E_DOMAIN_TAGS,
)


def _id(label: str) -> str:
    return hashlib.sha256(
        b"acfqp:construction-accounting-live-v3-test\x00"
        + label.encode("utf-8")
    ).hexdigest()


def _profiles():
    registry = registry_v3.official_counter_registry_v3()
    stage = registry_v3.official_stage_profile_v3(registry)
    comparison = registry_v3.official_comparison_profile_v3(registry)
    actual = registry_v3.official_actual_projection_profile_v3(
        registry, comparison
    )
    return registry, stage, comparison, actual


def _verify(recorded: live.RecordedStageWorkV3) -> None:
    registry, stage, comparison, actual = _profiles()
    live.verify_recorded_stage_work_v3(
        recorded, registry, stage, comparison, actual
    )


def test_two_stage_lifecycle_replays_native_zeroes_and_projection() -> None:
    lifecycle = live.open_construction_accounting_lifecycle_v3(
        subject_id=_id("subject"),
        recorder_id="trusted-k7-recorder-v1",
        stage_plan=(
            registry_v3.ConstructionStageKindV3.PREOPEN_COMMON_PREFIX,
            registry_v3.ConstructionStageKindV3.INITIAL_ACQUISITION,
        ),
    )
    preopen = lifecycle.begin_stage(
        registry_v3.ConstructionStageKindV3.PREOPEN_COMMON_PREFIX
    )
    preopen.add(
        "common.protocol_checks",
        2,
        operation_site_id="preopen.protocol-check",
    )
    preopen.add(
        "io.read_bytes", 4, operation_site_id="preopen.read-a"
    )
    preopen.add(
        "io.read_bytes", 6, operation_site_id="preopen.read-b"
    )
    preopen.observe_peak(
        "io.mounted_bytes_peak",
        10,
        operation_site_id="preopen.mount-a",
    )
    preopen.observe_peak(
        "io.mounted_bytes_peak",
        7,
        operation_site_id="preopen.mount-b",
    )
    preopen.observe_peak(
        "memory.working_bytes_peak",
        20,
        operation_site_id="preopen.working-set",
    )
    first = preopen.complete(output_artifact_ids=(_id("preopen-output"),))

    acquisition = lifecycle.begin_stage(
        registry_v3.ConstructionStageKindV3.INITIAL_ACQUISITION
    )
    acquisition.add(
        "acquisition.initial_observer_accepted_draws",
        4224,
        operation_site_id="observer.accepted-draw",
    )
    acquisition.add(
        "acquisition.initial_observer_random_word_calls",
        4300,
        operation_site_id="observer.random-word",
    )
    acquisition.add(
        "acquisition.initial_observer_rejections",
        76,
        operation_site_id="observer.rejection",
    )
    acquisition.add(
        "acquisition.initial_outcome_aggregate_rows",
        4,
        operation_site_id="observer.aggregate-row",
    )
    acquisition.add(
        "acquisition.initial_signed_batches",
        4,
        operation_site_id="observer.signed-batch",
    )
    acquisition.add(
        "acquisition.initial_support_freezes",
        2,
        operation_site_id="observer.support-freeze",
    )
    acquisition.add(
        "acquisition.initial_outcome_projections",
        4,
        operation_site_id="observer.outcome-projection",
    )
    second = acquisition.complete()
    stages = lifecycle.finish()

    assert stages == (first, second)
    assert lifecycle.to_document()["lifecycle_id"] == lifecycle.lifecycle_id
    assert lifecycle.to_document()["stage_plan"] == [
        "PREOPEN_COMMON_PREFIX",
        "INITIAL_ACQUISITION",
    ]
    assert len(first.work_vector.records) == 109
    assert len(second.work_vector.records) == 109
    assert all(row.observed is True for row in first.work_vector.records)
    assert first.work_vector.values[
        "acquisition.initial_observer_accepted_draws"
    ] == 0
    assert second.work_vector.values[
        "acquisition.initial_observer_accepted_draws"
    ] == 4224
    first_axes = dict(first.comparison_vector.values)
    second_axes = dict(second.comparison_vector.values)
    assert first_axes["read_bytes"] == 10
    assert first_axes["peak_mounted_bytes"] == 10
    assert first_axes["peak_working_bytes"] == 20
    assert first_axes["nonkernel_compute_events"] == 2
    assert second_axes["kernel_transition_calls"] == 4224
    assert second.work_vector.values[
        "acquisition.initial_observer_rejections"
    ] == 76
    assert second_axes["kernel_transition_calls"] != 4300
    _verify(first)
    _verify(second)
    registry, stage, comparison, actual = _profiles()
    replayed = live.RecordedStageWorkV3.from_document(
        first.to_document(),
        registry,
        stage,
        comparison,
        actual,
    )
    assert replayed == first

    changed = first.to_document()
    changed["stage_start"]["stage_index"] = 2
    with pytest.raises(live.ConstructionAccountingLiveV3Error):
        live.RecordedStageWorkV3.from_document(
            changed,
            registry,
            stage,
            comparison,
            actual,
        )


def test_sum_max_and_reconciliation_are_replayed_from_events() -> None:
    lifecycle = live.open_construction_accounting_lifecycle_v3(
        subject_id=_id("route-subject"),
        recorder_id="trusted-route-recorder-v1",
        stage_plan=(registry_v3.ConstructionStageKindV3.LOCAL_ATTEMPT,),
    )
    active = lifecycle.begin_stage(
        registry_v3.ConstructionStageKindV3.LOCAL_ATTEMPT
    )
    active.add(
        "process.launches", operation_site_id="worker.process-launch"
    )
    active.add(
        "process.exit_successes",
        operation_site_id="worker.process-success",
    )
    active.add(
        "route.successes", operation_site_id="route.success"
    )
    active.add(
        "solver.successes", operation_site_id="solver.success"
    )
    active.add("io.read_bytes", 3, operation_site_id="worker.read-a")
    active.add("io.read_bytes", 5, operation_site_id="worker.read-b")
    active.observe_peak(
        "memory.working_bytes_peak",
        11,
        operation_site_id="worker.peak-a",
    )
    active.observe_peak(
        "memory.working_bytes_peak",
        9,
        operation_site_id="worker.peak-b",
    )
    recorded = active.complete()
    lifecycle.finish()

    assert recorded.work_vector.values["route.attempts"] == 1
    assert recorded.work_vector.values["solver.attempts"] == 1
    axes = dict(recorded.comparison_vector.values)
    assert axes["process_launches"] == 1
    assert axes["read_bytes"] == 8
    assert axes["peak_working_bytes"] == 11
    _verify(recorded)


def test_stage_order_active_stage_and_one_shot_sealing_fail_closed() -> None:
    lifecycle = live.open_construction_accounting_lifecycle_v3(
        subject_id=_id("ordered-subject"),
        recorder_id="ordered-recorder-v1",
        stage_plan=(
            registry_v3.ConstructionStageKindV3.PREOPEN_COMMON_PREFIX,
            registry_v3.ConstructionStageKindV3.INITIAL_MODEL_BUILD,
        ),
    )
    with pytest.raises(
        live.ConstructionAccountingLiveV3Error,
        match="preregistered stage plan",
    ):
        lifecycle.begin_stage(
            registry_v3.ConstructionStageKindV3.INITIAL_MODEL_BUILD
        )
    first = lifecycle.begin_stage(
        registry_v3.ConstructionStageKindV3.PREOPEN_COMMON_PREFIX
    )
    with pytest.raises(
        live.ConstructionAccountingLiveV3Error, match="active stage"
    ):
        lifecycle.begin_stage(
            registry_v3.ConstructionStageKindV3.PREOPEN_COMMON_PREFIX
        )
    first.complete()
    with pytest.raises(
        live.ConstructionAccountingLiveV3Error, match="every preregistered"
    ):
        lifecycle.finish()
    second = lifecycle.begin_stage(
        registry_v3.ConstructionStageKindV3.INITIAL_MODEL_BUILD
    )
    second.complete()
    with pytest.raises(
        live.ConstructionAccountingLiveV3Error, match="already sealed"
    ):
        second.complete()
    assert len(lifecycle.finish()) == 2
    with pytest.raises(
        live.ConstructionAccountingLiveV3Error, match="closed"
    ):
        lifecycle.begin_stage(
            registry_v3.ConstructionStageKindV3.INITIAL_MODEL_BUILD
        )


def test_aborted_stage_retains_exact_partial_work_and_stops_lifecycle() -> None:
    lifecycle = live.open_construction_accounting_lifecycle_v3(
        subject_id=_id("abort-subject"),
        recorder_id="abort-recorder-v1",
        stage_plan=(
            registry_v3.ConstructionStageKindV3.PREOPEN_COMMON_PREFIX,
            registry_v3.ConstructionStageKindV3.INITIAL_ACQUISITION,
        ),
    )
    active = lifecycle.begin_stage(
        registry_v3.ConstructionStageKindV3.PREOPEN_COMMON_PREFIX
    )
    active.add(
        "common.integrity_checks",
        3,
        operation_site_id="preopen.integrity-before-abort",
    )
    recorded = active.abort(failure_evidence_ids=(_id("failure"),))
    assert recorded.stage_completion.outcome is (
        live.StageCompletionOutcomeV3.ABORTED
    )
    assert recorded.work_vector.values["common.integrity_checks"] == 3
    assert lifecycle.aborted is True
    assert lifecycle.finish() == (recorded,)
    with pytest.raises(
        live.ConstructionAccountingLiveV3Error, match="closed"
    ):
        lifecycle.begin_stage(
            registry_v3.ConstructionStageKindV3.INITIAL_ACQUISITION
        )
    _verify(recorded)


def test_wrong_stage_optional_peak_and_derived_total_events_are_rejected() -> None:
    lifecycle = live.open_construction_accounting_lifecycle_v3(
        subject_id=_id("rejection-subject"),
        recorder_id="rejection-recorder-v1",
        stage_plan=(
            registry_v3.ConstructionStageKindV3.PREOPEN_COMMON_PREFIX,
        ),
    )
    active = lifecycle.begin_stage(
        registry_v3.ConstructionStageKindV3.PREOPEN_COMMON_PREFIX
    )
    with pytest.raises(live.ConstructionAccountingLiveV3Error, match="outside"):
        active.add(
            "acquisition.initial_observer_accepted_draws",
            operation_site_id="wrong.stage",
        )
    with pytest.raises(live.ConstructionAccountingLiveV3Error, match="optional"):
        active.add("branch.evaluations", operation_site_id="optional.leaf")
    with pytest.raises(live.ConstructionAccountingLiveV3Error, match="observe_peak"):
        active.add(
            "memory.working_bytes_peak",
            operation_site_id="wrong.reducer",
        )
    with pytest.raises(live.ConstructionAccountingLiveV3Error, match="must use add"):
        active.observe_peak(
            "common.protocol_checks",
            1,
            operation_site_id="wrong.reducer",
        )
    active.complete()

    route = live.open_construction_accounting_lifecycle_v3(
        subject_id=_id("derived-subject"),
        recorder_id="derived-recorder-v1",
        stage_plan=(registry_v3.ConstructionStageKindV3.LOCAL_ATTEMPT,),
    ).begin_stage(registry_v3.ConstructionStageKindV3.LOCAL_ATTEMPT)
    with pytest.raises(live.ConstructionAccountingLiveV3Error, match="derived"):
        route.add("route.attempts", operation_site_id="forged.total")


def test_process_reconciliation_rejects_unclosed_launch() -> None:
    lifecycle = live.open_construction_accounting_lifecycle_v3(
        subject_id=_id("process-subject"),
        recorder_id="process-recorder-v1",
        stage_plan=(registry_v3.ConstructionStageKindV3.LOCAL_ATTEMPT,),
    )
    active = lifecycle.begin_stage(
        registry_v3.ConstructionStageKindV3.LOCAL_ATTEMPT
    )
    active.add("process.launches", operation_site_id="process.launch")
    with pytest.raises(
        live.ConstructionAccountingLiveV3Error,
        match="process launch and exit reconciliation",
    ):
        active.complete()


def test_missing_native_zero_and_event_tamper_fail_replay() -> None:
    lifecycle = live.open_construction_accounting_lifecycle_v3(
        subject_id=_id("tamper-subject"),
        recorder_id="tamper-recorder-v1",
        stage_plan=(
            registry_v3.ConstructionStageKindV3.PREOPEN_COMMON_PREFIX,
        ),
    )
    active = lifecycle.begin_stage(
        registry_v3.ConstructionStageKindV3.PREOPEN_COMMON_PREFIX
    )
    active.add(
        "common.protocol_checks",
        operation_site_id="tamper.protocol",
    )
    recorded = active.complete()
    registry, stage, comparison, actual = _profiles()
    missing = replace(
        recorded.work_vector,
        records=recorded.work_vector.records[:-1],
    )
    with pytest.raises(
        live.ConstructionAccountingLiveV3Error,
        match="every required leaf",
    ):
        live.validate_work_vector_v3(missing, registry, stage)

    attacked_event = replace(
        recorded.operation_events[0],
        _issuer=live._EVENT_ISSUER,  # noqa: SLF001
        value=2,
    )
    attacked = replace(recorded, operation_events=(attacked_event,))
    with pytest.raises(
        live.ConstructionAccountingLiveV3Error,
        match="start, transcript, and completion",
    ):
        live.verify_recorded_stage_work_v3(
            attacked, registry, stage, comparison, actual
        )


def test_counter_and_work_vector_round_trip_and_content_tamper_reject() -> None:
    lifecycle = live.open_construction_accounting_lifecycle_v3(
        subject_id=_id("round-trip-subject"),
        recorder_id="round-trip-recorder-v1",
        stage_plan=(
            registry_v3.ConstructionStageKindV3.PREOPEN_COMMON_PREFIX,
        ),
    )
    active = lifecycle.begin_stage(
        registry_v3.ConstructionStageKindV3.PREOPEN_COMMON_PREFIX
    )
    active.add(
        "common.hash_invocations",
        2,
        operation_site_id="round-trip.hash",
    )
    recorded = active.complete()
    registry, stage, _comparison, _actual = _profiles()
    row = recorded.work_vector.records[0]
    assert live.CounterRecordV3.from_document(row.to_document()) == row
    assert live.WorkVectorV3.from_document(
        recorded.work_vector.to_document(), registry, stage
    ) == recorded.work_vector

    attacked = row.to_document()
    attacked["value"] += 1
    with pytest.raises(
        live.ConstructionAccountingLiveV3Error, match="content ID mismatch"
    ):
        live.CounterRecordV3.from_document(attacked)


def test_caller_minted_start_and_event_are_rejected() -> None:
    lifecycle = live.open_construction_accounting_lifecycle_v3(
        subject_id=_id("issuer-subject"),
        recorder_id="issuer-recorder-v1",
        stage_plan=(
            registry_v3.ConstructionStageKindV3.PREOPEN_COMMON_PREFIX,
        ),
    )
    active = lifecycle.begin_stage(
        registry_v3.ConstructionStageKindV3.PREOPEN_COMMON_PREFIX
    )
    with pytest.raises(
        live.ConstructionAccountingLiveV3Error, match="caller-minted"
    ):
        replace(active.start, _issuer=object())
    event = active.add(
        "common.protocol_checks", operation_site_id="issuer.event"
    )
    with pytest.raises(
        live.ConstructionAccountingLiveV3Error, match="caller-minted"
    ):
        replace(event, _issuer=object())


def test_all_live_v3_evidence_domains_are_registered_and_distinct() -> None:
    domains = (
        CONSTRUCTION_STAGE_START_ATTESTATION_V3_DOMAIN,
        CONSTRUCTION_OPERATION_EVENT_V3_DOMAIN,
        CONSTRUCTION_STAGE_COMPLETION_ATTESTATION_V3_DOMAIN,
        CONSTRUCTION_COUNTER_RECORD_V3_DOMAIN,
        CONSTRUCTION_WORK_VECTOR_V3_DOMAIN,
        CONSTRUCTION_COMPARISON_VECTOR_V3_DOMAIN,
        CONSTRUCTION_ACTUAL_PROJECTION_PROOF_V3_DOMAIN,
    )
    assert len(set(domains)) == len(domains)
    assert set(domains) <= PHASE3E_DOMAIN_TAGS


def test_mechanics_accept_an_exact_additive_registry_profile_adapter() -> None:
    registry = registry_v4.official_counter_registry_v4()
    stage = registry_v4.official_stage_profile_v4(registry)
    comparison = registry_v4.official_comparison_profile_v4(registry)
    actual = registry_v4.official_actual_projection_profile_v4(
        registry, comparison
    )
    lifecycle = live.open_construction_accounting_lifecycle_v3(
        subject_id=_id("v4-adapter-subject"),
        recorder_id="v4-adapter-recorder-v1",
        stage_plan=(
            registry_v4.ConstructionStageKindV4.PREOPEN_COMMON_PREFIX,
        ),
        registry=registry,
        stage_profile=stage,
        comparison_profile=comparison,
        actual_projection_profile=actual,
    )
    recorded = lifecycle.begin_stage(
        registry_v4.ConstructionStageKindV4.PREOPEN_COMMON_PREFIX
    ).complete()
    lifecycle.finish()
    assert len(recorded.work_vector.records) == 117
    assert recorded.work_vector.counter_registry_id == registry.registry_id
    live.verify_recorded_stage_work_v3(
        recorded, registry, stage, comparison, actual
    )
