from __future__ import annotations

from copy import deepcopy

import pytest

from acfqp.accounting_v1 import (
    KERNEL_TRANSITION_CALLS,
    NONKERNEL_COMPUTE_EVENTS,
    OUTPUT_BYTES,
    PEAK_MOUNTED_BYTES,
    PEAK_WORKING_BYTES,
    PROCESS_LAUNCHES,
    READ_BYTES,
    SHARED_AXES,
    STAGED_BYTES,
    LaneEnum,
    ReducerEnum,
    official_counter_registry_v1,
)
from acfqp.construction_accounting_v2 import (
    EXPECTED_V2_LEAF_COUNT,
    EXPECTED_V2_OPERATIONAL_LEAF_COUNT,
    EXPECTED_V2_REQUIRED_LEAF_COUNT,
    ActualProjectionProfileV2,
    ComparisonProfileV2,
    ConstructionAccountingV2Error,
    ConstructionStageRecorderV2,
    CounterRecordV2,
    CounterRegistryV2,
    StageKindV2,
    StageProfileV2,
    WorkVectorV2,
    derive_actual_projection_v2,
    freeze_construction_accounting_schema_v2,
    official_actual_projection_profile_v2,
    official_comparison_profile_v2,
    official_counter_registry_v2,
    official_stage_profile_v2,
    validate_work_vector_v2,
)
from acfqp.phase3e_ids import (
    CONSTRUCTION_COUNTER_RECORD_V2_DOMAIN,
    CONSTRUCTION_WORK_VECTOR_V2_DOMAIN,
    content_id,
)


SUBJECT_ID = "1" * 64
STAGE_INSTANCE_ID = "2" * 64
OTHER_STAGE_INSTANCE_ID = "3" * 64
COMPLETION_ID = "4" * 64
START_ID = "0" * 64


def _profiles():
    registry = official_counter_registry_v2()
    stage = official_stage_profile_v2(registry)
    comparison = official_comparison_profile_v2(registry)
    actual = official_actual_projection_profile_v2(registry, comparison)
    return registry, stage, comparison, actual


def _recorder(
    stage_kind: StageKindV2,
    *,
    stage_instance_id: str = STAGE_INSTANCE_ID,
) -> ConstructionStageRecorderV2:
    return ConstructionStageRecorderV2(
        subject_id=SUBJECT_ID,
        stage_instance_id=stage_instance_id,
        stage_start_attestation_id=START_ID,
        stage_kind=stage_kind,
        recorder_id="pytest-construction-recorder-v2",
    )


def _replace_record(
    vector: WorkVectorV2,
    path: str,
    value: int,
    *,
    stage_instance_id: str | None = None,
    stage_start_attestation_id: str | None = None,
    stage_kind: StageKindV2 | None = None,
) -> tuple[CounterRecordV2, ...]:
    registry = official_counter_registry_v2()
    replacement = CounterRecordV2.observe(
        registry,
        path,
        value,
        subject_id=vector.subject_id,
        stage_instance_id=stage_instance_id or vector.stage_instance_id,
        stage_start_attestation_id=(
            stage_start_attestation_id
            or vector.stage_start_attestation_id
        ),
        stage_kind=stage_kind or vector.stage_kind,
        recorder_id="pytest-replacement-recorder-v2",
    )
    return tuple(
        sorted(
            (
                replacement if row.path == path else row
                for row in vector.records
            ),
            key=lambda row: row.path,
        )
    )


def test_registry_cardinalities_and_v1_exact_immutable_prefix() -> None:
    v1 = official_counter_registry_v1()
    v2 = official_counter_registry_v2()

    assert len(v2.leaves) == EXPECTED_V2_LEAF_COUNT == 69
    assert (
        len(v2.operational_leaves)
        == EXPECTED_V2_OPERATIONAL_LEAF_COUNT
        == 53
    )
    assert len(v2.required_paths) == EXPECTED_V2_REQUIRED_LEAF_COUNT == 62
    assert v2.base_counter_registry_id == v1.registry_id
    assert len(v2.leaves) - len(v1.leaves) == 20
    assert all(v2.by_path[row.path] == row for row in v1.leaves)
    assert not (
        set(v1.by_path)
        & {row.path for row in v2.leaves if row.path not in v1.by_path}
    )


_NEW_METADATA = {
    "acquisition.initial_observer_accepted_draws": (
        "v075-initial-observer-accepted-draw-v2",
        "v075_private_observer_boundary_v2",
        "accepted_draws",
        LaneEnum.OPERATIONAL,
        "construction_occurrence_initial_acquisition_prefix",
        ReducerEnum.SUM,
        KERNEL_TRANSITION_CALLS,
    ),
    "acquisition.initial_observer_random_word_calls": (
        "v075-initial-observer-random-word-call-v2",
        "v075_private_observer_boundary_v2",
        "random_word_calls",
        LaneEnum.OPERATIONAL,
        "construction_occurrence_initial_acquisition_prefix",
        ReducerEnum.SUM,
        NONKERNEL_COMPUTE_EVENTS,
    ),
    "acquisition.initial_observer_rejections": (
        "v075-initial-observer-rejection-v2",
        "v075_private_observer_boundary_v2",
        "rejections",
        LaneEnum.DIAGNOSTIC,
        "construction_occurrence_initial_acquisition_prefix",
        ReducerEnum.SUM,
        None,
    ),
    "acquisition.initial_outcome_aggregate_rows": (
        "v075-initial-outcome-aggregate-row-materialization-v2",
        "v075_private_observer_boundary_v2",
        "aggregate_rows",
        LaneEnum.OPERATIONAL,
        "construction_occurrence_initial_acquisition_prefix",
        ReducerEnum.SUM,
        NONKERNEL_COMPUTE_EVENTS,
    ),
    "acquisition.initial_signed_batches": (
        "v075-initial-signed-batch-materialization-v2",
        "v075_private_observer_boundary_v2",
        "signed_batches",
        LaneEnum.OPERATIONAL,
        "construction_occurrence_initial_acquisition_prefix",
        ReducerEnum.SUM,
        NONKERNEL_COMPUTE_EVENTS,
    ),
    "acquisition.initial_support_freezes": (
        "v075-initial-support-freeze-materialization-v2",
        "v075_observer_signed_batch_control_authority_v2",
        "support_freezes",
        LaneEnum.OPERATIONAL,
        "construction_occurrence_initial_acquisition_prefix",
        ReducerEnum.SUM,
        NONKERNEL_COMPUTE_EVENTS,
    ),
    "build.initial_interval_log_search_evaluations": (
        "v075-initial-interval-log-search-eval-v2",
        "v075_batch_native_planning_backend_v2",
        "log_search_evaluations",
        LaneEnum.OPERATIONAL,
        "construction_occurrence_initial_build_epoch",
        ReducerEnum.SUM,
        NONKERNEL_COMPUTE_EVENTS,
    ),
    "build.initial_interval_row_evaluations": (
        "v075-initial-interval-row-eval-v2",
        "v075_batch_native_planning_backend_v2",
        "row_behavior_evaluations",
        LaneEnum.OPERATIONAL,
        "construction_occurrence_initial_build_epoch",
        ReducerEnum.SUM,
        NONKERNEL_COMPUTE_EVENTS,
    ),
    "build.initial_model_rows_built": (
        "v075-initial-model-row-build-v2",
        "v075_live_incremental_model_authority_v2",
        "model_rows",
        LaneEnum.OPERATIONAL,
        "construction_occurrence_initial_build_epoch",
        ReducerEnum.SUM,
        NONKERNEL_COMPUTE_EVENTS,
    ),
    "build.initial_policy_assignments_evaluated": (
        "v075-initial-policy-assignment-eval-v2",
        "v075_batch_native_planning_backend_v2",
        "policy_assignments",
        LaneEnum.OPERATIONAL,
        "construction_occurrence_initial_build_epoch",
        ReducerEnum.SUM,
        NONKERNEL_COMPUTE_EVENTS,
    ),
    "build.initial_semantic_record_replays": (
        "v075-initial-semantic-record-replay-v2",
        "v075_semantic_replay_instrumentation_v2",
        "record_replays",
        LaneEnum.OPERATIONAL,
        "construction_occurrence_initial_build_epoch",
        ReducerEnum.SUM,
        NONKERNEL_COMPUTE_EVENTS,
    ),
    "build.initial_semantic_role_closures": (
        "v075-initial-semantic-role-closure-v2",
        "v075_semantic_replay_instrumentation_v2",
        "role_closures",
        LaneEnum.OPERATIONAL,
        "construction_occurrence_initial_build_epoch",
        ReducerEnum.SUM,
        NONKERNEL_COMPUTE_EVENTS,
    ),
    "build.initial_source_units_compiled": (
        "v075-initial-row-source-unit-compile-v2",
        "v075_live_incremental_model_authority_v2",
        "row_source_units",
        LaneEnum.OPERATIONAL,
        "construction_occurrence_initial_build_epoch",
        ReducerEnum.SUM,
        NONKERNEL_COMPUTE_EVENTS,
    ),
    "closure.reconciliation_interval_log_search_evaluations": (
        "v075-closed-reconciliation-interval-log-search-eval-v2",
        "v075_batch_native_planning_backend_v2",
        "log_search_evaluations",
        LaneEnum.OPERATIONAL,
        "construction_occurrence_closed_reconciliation_and_terminalization",
        ReducerEnum.SUM,
        NONKERNEL_COMPUTE_EVENTS,
    ),
    "closure.reconciliation_interval_row_evaluations": (
        "v075-closed-reconciliation-interval-row-eval-v2",
        "v075_batch_native_planning_backend_v2",
        "row_behavior_evaluations",
        LaneEnum.OPERATIONAL,
        "construction_occurrence_closed_reconciliation_and_terminalization",
        ReducerEnum.SUM,
        NONKERNEL_COMPUTE_EVENTS,
    ),
    "closure.reconciliation_model_rows_built": (
        "v075-closed-reconciliation-model-row-build-v2",
        "v075_live_incremental_model_authority_v2",
        "model_rows",
        LaneEnum.OPERATIONAL,
        "construction_occurrence_closed_reconciliation_and_terminalization",
        ReducerEnum.SUM,
        NONKERNEL_COMPUTE_EVENTS,
    ),
    "closure.reconciliation_policy_assignments_evaluated": (
        "v075-closed-reconciliation-policy-assignment-eval-v2",
        "v075_batch_native_planning_backend_v2",
        "policy_assignments",
        LaneEnum.OPERATIONAL,
        "construction_occurrence_closed_reconciliation_and_terminalization",
        ReducerEnum.SUM,
        NONKERNEL_COMPUTE_EVENTS,
    ),
    "closure.reconciliation_semantic_record_replays": (
        "v075-closed-reconciliation-semantic-record-replay-v2",
        "v075_semantic_replay_instrumentation_v2",
        "record_replays",
        LaneEnum.OPERATIONAL,
        "construction_occurrence_closed_reconciliation_and_terminalization",
        ReducerEnum.SUM,
        NONKERNEL_COMPUTE_EVENTS,
    ),
    "closure.reconciliation_semantic_role_closures": (
        "v075-closed-reconciliation-semantic-role-closure-v2",
        "v075_semantic_replay_instrumentation_v2",
        "role_closures",
        LaneEnum.OPERATIONAL,
        "construction_occurrence_closed_reconciliation_and_terminalization",
        ReducerEnum.SUM,
        NONKERNEL_COMPUTE_EVENTS,
    ),
    "closure.reconciliation_source_units_compiled": (
        "v075-closed-reconciliation-row-source-unit-compile-v2",
        "v075_live_incremental_model_authority_v2",
        "row_source_units",
        LaneEnum.OPERATIONAL,
        "construction_occurrence_closed_reconciliation_and_terminalization",
        ReducerEnum.SUM,
        NONKERNEL_COMPUTE_EVENTS,
    ),
}


def test_all_twenty_new_leaf_metadata_are_exact_and_rejection_is_diagnostic() -> None:
    v1_paths = set(official_counter_registry_v1().by_path)
    registry = official_counter_registry_v2()
    additions = {
        row.path: row for row in registry.leaves if row.path not in v1_paths
    }

    assert len(_NEW_METADATA) == len(additions) == 20
    for path, expected in _NEW_METADATA.items():
        row = additions[path]
        assert (
            row.semantics_id,
            row.owner,
            row.unit,
            row.lane,
            row.scope,
            row.reducer,
            row.comparison_axis,
        ) == expected
        assert row.required is True

    comparison = official_comparison_profile_v2(registry)
    projected_paths = {term.source_leaf for term in comparison.terms}
    assert "acquisition.initial_observer_rejections" not in projected_paths
    assert (
        registry.by_path["acquisition.initial_observer_rejections"].lane
        is LaneEnum.DIAGNOSTIC
    )


def test_comparison_and_actual_profiles_cover_exactly_53_leaves_on_8_axes() -> None:
    registry, _stage, comparison, actual = _profiles()

    assert tuple(axis.name for axis in comparison.axes) == SHARED_AXES
    assert len(comparison.axes) == 8
    assert len(comparison.terms) == 53
    assert actual.terms == comparison.terms
    assert {term.source_leaf for term in comparison.terms} == {
        leaf.path for leaf in registry.operational_leaves
    }
    assert all(term.coefficient == 1 for term in comparison.terms)


def test_schema_documents_round_trip_and_tamper_fail_closed() -> None:
    registry, stage, comparison, actual = _profiles()
    documents = freeze_construction_accounting_schema_v2()

    assert (
        CounterRegistryV2.from_document(documents["counter_registry"])
        == registry
    )
    assert (
        StageProfileV2.from_document(
            documents["stage_profile"], registry
        )
        == stage
    )
    assert (
        ComparisonProfileV2.from_document(
            documents["comparison_profile"], registry
        )
        == comparison
    )
    assert (
        ActualProjectionProfileV2.from_document(
            documents["actual_projection_profile"], registry, comparison
        )
        == actual
    )

    decoders = (
        (
            "counter_registry",
            lambda value: CounterRegistryV2.from_document(value),
            "counter_registry_id",
        ),
        (
            "stage_profile",
            lambda value: StageProfileV2.from_document(value, registry),
            "stage_profile_id",
        ),
        (
            "comparison_profile",
            lambda value: ComparisonProfileV2.from_document(value, registry),
            "comparison_profile_id",
        ),
        (
            "actual_projection_profile",
            lambda value: ActualProjectionProfileV2.from_document(
                value, registry, comparison
            ),
            "actual_projection_profile_id",
        ),
    )
    for key, decode, id_field in decoders:
        forged = deepcopy(documents[key])
        forged[id_field] = "f" * 64
        with pytest.raises(ConstructionAccountingV2Error):
            decode(forged)

        unknown = deepcopy(documents[key])
        unknown["undeclared"] = True
        with pytest.raises(ConstructionAccountingV2Error):
            decode(unknown)


@pytest.mark.parametrize(
    ("stage_kind", "allowed_path", "forbidden_path"),
    (
        (
            StageKindV2.INITIAL_ACQUISITION,
            "acquisition.initial_signed_batches",
            "build.initial_model_rows_built",
        ),
        (
            StageKindV2.INITIAL_MODEL_BUILD,
            "build.initial_model_rows_built",
            "closure.reconciliation_model_rows_built",
        ),
        (
            StageKindV2.CLOSED_RECONCILIATION_AND_TERMINALIZATION,
            "closure.reconciliation_model_rows_built",
            "acquisition.initial_signed_batches",
        ),
        (
            StageKindV2.LOCAL_ATTEMPT,
            "local.causal_candidate_evaluations",
            "fallback.states_expanded",
        ),
        (
            StageKindV2.DIRECT_FALLBACK,
            "fallback.states_expanded",
            "local.causal_candidate_evaluations",
        ),
        (
            StageKindV2.REBUILD,
            "rebuild.ground_steps",
            "common.abstract_bellman_backups",
        ),
    ),
)
def test_stage_nonzero_exclusivity_is_enforced_at_recording_boundary(
    stage_kind: StageKindV2,
    allowed_path: str,
    forbidden_path: str,
) -> None:
    recorder = _recorder(stage_kind)
    recorder.add(allowed_path)
    with pytest.raises(ConstructionAccountingV2Error, match="outside"):
        recorder.add(forbidden_path)


def test_work_vector_rejects_missing_unknown_unobserved_and_cross_stage_rows() -> None:
    registry, stage, _comparison, _actual = _profiles()
    recorded = _recorder(StageKindV2.INITIAL_ACQUISITION).seal(
        stage_completion_attestation_id=COMPLETION_ID
    )
    vector = recorded.work_vector

    missing = WorkVectorV2(
        vector.counter_registry_id,
        vector.stage_profile_id,
        vector.subject_id,
        vector.stage_instance_id,
        vector.stage_start_attestation_id,
        vector.stage_completion_attestation_id,
        vector.stage_kind,
        vector.records[1:],
    )
    with pytest.raises(ConstructionAccountingV2Error, match="omits required"):
        validate_work_vector_v2(missing, registry, stage)

    with pytest.raises(ConstructionAccountingV2Error, match="unknown"):
        CounterRecordV2.observe(
            registry,
            "acquisition.not_registered",
            1,
            subject_id=SUBJECT_ID,
            stage_instance_id=STAGE_INSTANCE_ID,
            stage_start_attestation_id=START_ID,
            stage_kind=StageKindV2.INITIAL_ACQUISITION,
            recorder_id="pytest-recorder",
        )

    row = vector.records[0]
    with pytest.raises(ConstructionAccountingV2Error, match="unobserved"):
        CounterRecordV2(
            row.counter_registry_id,
            row.subject_id,
            row.stage_instance_id,
            row.stage_start_attestation_id,
            row.stage_kind,
            row.path,
            row.value,
            False,
            row.recorder_id,
            row.semantics_id,
            row.owner,
            row.unit,
            row.lane,
            row.scope,
            row.reducer,
        )

    foreign_rows = _replace_record(
        vector,
        vector.records[0].path,
        vector.records[0].value,
        stage_instance_id=OTHER_STAGE_INSTANCE_ID,
    )
    spliced = WorkVectorV2(
        vector.counter_registry_id,
        vector.stage_profile_id,
        vector.subject_id,
        vector.stage_instance_id,
        vector.stage_start_attestation_id,
        vector.stage_completion_attestation_id,
        vector.stage_kind,
        foreign_rows,
    )
    with pytest.raises(
        ConstructionAccountingV2Error, match="foreign counter record"
    ):
        validate_work_vector_v2(spliced, registry, stage)

    foreign_start_rows = _replace_record(
        vector,
        vector.records[0].path,
        vector.records[0].value,
        stage_start_attestation_id="9" * 64,
    )
    start_spliced = WorkVectorV2(
        vector.counter_registry_id,
        vector.stage_profile_id,
        vector.subject_id,
        vector.stage_instance_id,
        vector.stage_start_attestation_id,
        vector.stage_completion_attestation_id,
        vector.stage_kind,
        foreign_start_rows,
    )
    with pytest.raises(
        ConstructionAccountingV2Error, match="foreign counter record"
    ):
        validate_work_vector_v2(start_spliced, registry, stage)


def test_work_vector_and_counter_record_round_trip_and_tamper_fail_closed() -> None:
    registry, stage, _comparison, _actual = _profiles()
    vector = _recorder(StageKindV2.INITIAL_MODEL_BUILD).seal(
        stage_completion_attestation_id=COMPLETION_ID
    ).work_vector

    row = vector.records[0]
    assert CounterRecordV2.from_document(row.to_document()) == row
    assert WorkVectorV2.from_document(
        vector.to_document(), registry, stage
    ) == vector

    forged_row = row.to_document()
    forged_row["value"] += 1
    with pytest.raises(ConstructionAccountingV2Error, match="content ID"):
        CounterRecordV2.from_document(forged_row)

    forged_vector = vector.to_document()
    forged_vector["stage_completion_attestation_id"] = "e" * 64
    with pytest.raises(ConstructionAccountingV2Error, match="content ID"):
        WorkVectorV2.from_document(forged_vector, registry, stage)


def test_projection_uses_sum_for_traffic_and_max_for_peak_axes() -> None:
    recorder = _recorder(StageKindV2.INITIAL_ACQUISITION)
    recorder.add("acquisition.initial_observer_accepted_draws", 7)
    recorder.add("acquisition.initial_observer_random_word_calls", 3)
    recorder.add("io.read_bytes", 5)
    recorder.add("io.read_bytes", 2)
    recorder.add("io.staged_bytes", 13)
    recorder.add("io.output_bytes", 11)
    recorder.observe_peak("io.mounted_bytes_peak", 100)
    recorder.observe_peak("io.mounted_bytes_peak", 80)
    recorder.observe_peak("memory.working_bytes_peak", 40)
    recorder.observe_peak("memory.working_bytes_peak", 50)
    recorder.set_reconciliation(process_exit_successes=1)
    result = recorder.seal(
        stage_completion_attestation_id=COMPLETION_ID
    )

    values = dict(result.comparison_vector.values)
    assert values == {
        KERNEL_TRANSITION_CALLS: 7,
        NONKERNEL_COMPUTE_EVENTS: 3,
        OUTPUT_BYTES: 11,
        PEAK_MOUNTED_BYTES: 100,
        PEAK_WORKING_BYTES: 50,
        PROCESS_LAUNCHES: 1,
        READ_BYTES: 7,
        STAGED_BYTES: 13,
    }
    assert len(result.actual_projection_proof.counter_record_ids) == 62


@pytest.mark.parametrize(
    ("path", "value", "message"),
    (
        ("route.attempts", 2, "route.attempts"),
        ("solver.attempts", 2, "solver.attempts"),
        ("process.launches", 2, "process launch"),
    ),
)
def test_reconciliation_mismatches_are_rejected(
    path: str, value: int, message: str
) -> None:
    registry, stage, _comparison, _actual = _profiles()
    recorder = _recorder(StageKindV2.LOCAL_ATTEMPT)
    recorder.set_reconciliation(
        route_successes=1,
        solver_failures=1,
        process_exit_successes=1,
    )
    vector = recorder.seal(
        stage_completion_attestation_id=COMPLETION_ID
    ).work_vector
    forged = WorkVectorV2(
        vector.counter_registry_id,
        vector.stage_profile_id,
        vector.subject_id,
        vector.stage_instance_id,
        vector.stage_start_attestation_id,
        vector.stage_completion_attestation_id,
        vector.stage_kind,
        _replace_record(vector, path, value),
    )
    with pytest.raises(ConstructionAccountingV2Error, match=message):
        validate_work_vector_v2(forged, registry, stage)


def test_derived_reconciliation_rows_cannot_be_recorded_as_operations() -> None:
    recorder = _recorder(StageKindV2.LOCAL_ATTEMPT)
    with pytest.raises(ConstructionAccountingV2Error, match="reconciled"):
        recorder.add("route.successes")
    with pytest.raises(ConstructionAccountingV2Error, match="reconciled"):
        recorder.add("process.exit_successes")


def test_nonzero_forbidden_path_is_rejected_even_if_records_are_forged() -> None:
    registry, stage, _comparison, _actual = _profiles()
    vector = _recorder(StageKindV2.DIRECT_FALLBACK).seal(
        stage_completion_attestation_id=COMPLETION_ID
    ).work_vector
    forged = WorkVectorV2(
        vector.counter_registry_id,
        vector.stage_profile_id,
        vector.subject_id,
        vector.stage_instance_id,
        vector.stage_start_attestation_id,
        vector.stage_completion_attestation_id,
        vector.stage_kind,
        _replace_record(vector, "local.causal_candidate_evaluations", 1),
    )
    with pytest.raises(ConstructionAccountingV2Error, match="exclusivity"):
        validate_work_vector_v2(forged, registry, stage)


def test_recorder_rejects_writes_and_identity_rebinding_after_seal() -> None:
    recorder = _recorder(StageKindV2.INITIAL_MODEL_BUILD)
    recorder.add("build.initial_model_rows_built", 3)
    first = recorder.seal(stage_completion_attestation_id=COMPLETION_ID)
    second = recorder.seal(stage_completion_attestation_id=COMPLETION_ID)

    assert second is first
    assert (
        first.work_vector.stage_completion_attestation_id == COMPLETION_ID
    )
    with pytest.raises(ConstructionAccountingV2Error, match="cannot be rebound"):
        recorder.seal(stage_completion_attestation_id="5" * 64)
    with pytest.raises(ConstructionAccountingV2Error, match="already sealed"):
        recorder.add("build.initial_model_rows_built")
    with pytest.raises(ConstructionAccountingV2Error, match="already sealed"):
        recorder.observe_peak("io.mounted_bytes_peak", 10)
    with pytest.raises(ConstructionAccountingV2Error, match="already sealed"):
        recorder.set_reconciliation()


def test_derived_projection_replay_is_exact_and_defines_no_scalar_cost() -> None:
    registry, stage, comparison, actual = _profiles()
    recorded = _recorder(StageKindV2.INITIAL_MODEL_BUILD).seal(
        stage_completion_attestation_id=COMPLETION_ID
    )
    replayed_vector, replayed_proof = derive_actual_projection_v2(
        recorded.work_vector,
        registry,
        stage,
        comparison,
        actual,
    )

    assert replayed_vector == recorded.comparison_vector
    assert replayed_proof == recorded.actual_projection_proof
    proof_document = replayed_proof.to_document()
    assert proof_document["scalar_cost_defined"] is False
    assert not hasattr(replayed_vector, "scalar_cost")
    assert not hasattr(recorded.work_vector, "scalar_cost")
    assert "official_scalar_cost" not in proof_document


def test_v2_content_ids_are_domain_separated_for_identical_payloads() -> None:
    payload = {"same": "canonical-payload", "value": 7}
    record_id = content_id(CONSTRUCTION_COUNTER_RECORD_V2_DOMAIN, payload)
    vector_id = content_id(CONSTRUCTION_WORK_VECTOR_V2_DOMAIN, payload)

    assert record_id != vector_id
    assert len(record_id) == len(vector_id) == 64
