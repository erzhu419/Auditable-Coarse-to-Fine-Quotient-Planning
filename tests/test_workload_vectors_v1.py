from __future__ import annotations

import copy
from dataclasses import replace
from functools import lru_cache
import hashlib

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
    ComparisonVectorV1,
    LaneEnum,
    RouteKindEnum,
    explicit_records_v1,
    official_comparison_profile_v1,
    official_counter_registry_v1,
)
from acfqp.actual_accounting_v1 import (
    ActualWorkScope,
    derive_actual_projection_v1,
    derive_occurrence_work_sum_v1,
    official_actual_projection_profile_v1,
)
from acfqp.routing_v1 import (
    DecisionPointV1,
    RouteDecisionContextV1,
    TransactionV1,
)
from acfqp.workload_vectors_v1 import (
    SCALAR_GATE_NOT_RUN,
    VECTOR_ONLY_COMPLETE_ENUMERATION,
    OccurrenceVectorRefV1,
    PermutationCapExceededError,
    ReplayableOccurrenceAccountingV1,
    VectorPrefixTotalV1,
    WorkloadVectorAnalysisV1,
    WorkloadVectorSpecV1,
    WorkloadVectorV1Error,
    analyze_workload_vectors_v1,
    verify_workload_vector_analysis_v1,
)


def _cid(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _work(route_kind: RouteKindEnum, subject_id: str, values: dict[str, int]):
    registry = official_counter_registry_v1()
    counters = {path: 0 for path in registry.required_paths}
    counters.update(values)
    records = explicit_records_v1(
        registry, counters, recorder_id="workload-native-recorder-v1"
    )
    return registry.materialize(
        subject_id=subject_id, route_kind=route_kind, records=records
    )


def _accounting(
    occurrence_id: str,
    label: str,
    *,
    kernel: int,
    nonkernel: int,
    process: int,
    read: int,
    staged: int,
    output: int,
    mounted_peak: int,
    working_peak: int,
) -> ReplayableOccurrenceAccountingV1:
    registry = official_counter_registry_v1()
    profile = official_comparison_profile_v1(registry)
    actual = official_actual_projection_profile_v1(registry, profile)
    context = RouteDecisionContextV1(
        _cid(f"{label}-preregistration"),
        _cid(f"{label}-protocol"),
        profile.comparison_profile_id,
        registry.registry_id,
        _cid(f"{label}-structural"),
        _cid(f"{label}-query"),
        _cid(f"{label}-plan"),
        _cid(f"{label}-threshold"),
        _cid(f"{label}-epoch"),
        occurrence_id,
        _cid(f"{label}-attempt"),
    )
    prefix_work = _work(
        RouteKindEnum.ABSTRACT_ONLY_CERTIFICATE,
        context.route_attempt_id,
        {},
    )
    prefix_comparison, prefix_proof = derive_actual_projection_v1(
        prefix_work,
        registry,
        profile,
        actual,
        source_lane=LaneEnum.OPERATIONAL,
        work_scope=ActualWorkScope.COMMON_PREFIX,
    )
    decision_point = DecisionPointV1(
        context.route_decision_context_id,
        1,
        _cid(f"{label}-frontier"),
        _cid(f"{label}-causal"),
        prefix_work.work_vector_id,
    )
    transaction = TransactionV1(
        occurrence_id,
        context.route_attempt_id,
        decision_point.decision_point_id,
        1,
        decision_point.frontier_snapshot_id,
        _cid(f"{label}-cap"),
    )
    local_work = _work(RouteKindEnum.LOCAL_ATTEMPT, transaction.transaction_id, {})
    local_comparison, local_proof = derive_actual_projection_v1(
        local_work,
        registry,
        profile,
        actual,
        source_lane=LaneEnum.OPERATIONAL,
        work_scope=ActualWorkScope.MARGINAL_ROUTE_EXECUTION,
    )
    fallback_work = _work(
        RouteKindEnum.DIRECT_FALLBACK,
        context.route_attempt_id,
        {
            "fallback.ground_steps": kernel,
            "fallback.states_expanded": nonkernel,
            "process.launches": process,
            "process.exit_successes": process,
            "io.read_bytes": read,
            "io.staged_bytes": staged,
            "io.output_bytes": output,
            "io.mounted_bytes_peak": mounted_peak,
            "memory.working_bytes_peak": working_peak,
        },
    )
    fallback_comparison, fallback_proof = derive_actual_projection_v1(
        fallback_work,
        registry,
        profile,
        actual,
        source_lane=LaneEnum.OPERATIONAL,
        work_scope=ActualWorkScope.MARGINAL_ROUTE_EXECUTION,
    )
    prefix = (prefix_work, prefix_comparison, prefix_proof)
    local = (local_work, local_comparison, local_proof)
    fallback = (fallback_work, fallback_comparison, fallback_proof)
    occurrence_sum = derive_occurrence_work_sum_v1(
        logical_occurrence_id=occurrence_id,
        route_context=context,
        decision_point=decision_point,
        local_transaction=transaction,
        registry=registry,
        comparison_profile=profile,
        actual_profile=actual,
        common_prefix=prefix,
        local_attempt=local,
        fallback=fallback,
    )
    return ReplayableOccurrenceAccountingV1(
        occurrence_sum,
        context,
        decision_point,
        transaction,
        prefix,
        local,
        fallback,
    )


@lru_cache(maxsize=1)
def _fixture() -> tuple[
    object,
    object,
    object,
    WorkloadVectorSpecV1,
    dict[str, ReplayableOccurrenceAccountingV1],
]:
    registry = official_counter_registry_v1()
    profile = official_comparison_profile_v1(registry)
    actual = official_actual_projection_profile_v1(registry, profile)
    occurrence_a = _cid("occurrence-a")
    occurrence_b = _cid("occurrence-b")
    occurrence_c = _cid("occurrence-c")
    vectors = {
        occurrence_a: _accounting(
            occurrence_a,
            "a",
            kernel=10,
            nonkernel=10,
            process=10,
            read=10,
            staged=10,
            output=10,
            mounted_peak=10,
            working_peak=10,
        ),
        occurrence_b: _accounting(
            occurrence_b,
            "b",
            kernel=5,
            nonkernel=5,
            process=5,
            read=5,
            staged=5,
            output=5,
            mounted_peak=5,
            working_peak=5,
        ),
        occurrence_c: _accounting(
            occurrence_c,
            "c",
            kernel=12,
            nonkernel=1,
            process=1,
            read=1,
            staged=1,
            output=1,
            mounted_peak=12,
            working_peak=12,
        ),
    }
    # The declared order is deliberately not lexical and must remain frozen.
    frozen_order = (occurrence_c, occurrence_b, occurrence_a)
    spec = WorkloadVectorSpecV1(
        profile.comparison_profile_id,
        tuple(
            OccurrenceVectorRefV1(
                occurrence_id, vectors[occurrence_id].occurrence_work_sum_id
            )
            for occurrence_id in frozen_order
        ),
        6,
    )
    return registry, profile, actual, spec, vectors


@lru_cache(maxsize=1)
def _analysis() -> tuple[
    object,
    object,
    object,
    WorkloadVectorSpecV1,
    dict[str, ReplayableOccurrenceAccountingV1],
    WorkloadVectorAnalysisV1,
]:
    registry, profile, actual, spec, vectors = _fixture()
    result = analyze_workload_vectors_v1(
        spec, vectors, registry, profile, actual
    )
    return registry, profile, actual, spec, vectors, result


def test_spec_freezes_declared_logical_occurrence_order_and_null_scalar_state() -> None:
    _, profile, _, spec, vectors = _fixture()
    expected = tuple(ref.logical_occurrence_id for ref in spec.occurrence_vectors)

    assert spec.ordered_logical_occurrence_ids == expected
    assert expected != tuple(sorted(expected))
    assert spec.official_scalar_cost is None
    assert spec.official_N_break_even is None
    assert spec.scalar_gate_status == SCALAR_GATE_NOT_RUN
    assert spec.comparison_profile_id == profile.comparison_profile_id
    assert tuple(ref.occurrence_work_sum_id for ref in spec.occurrence_vectors) == tuple(
        vectors[occurrence_id].occurrence_work_sum_id for occurrence_id in expected
    )
    assert WorkloadVectorSpecV1.from_dict(spec.to_dict()) == spec


def test_exact_order_enumeration_emits_one_canonical_total_per_order_prefix() -> None:
    _, _, _, spec, _, analysis = _analysis()

    assert analysis.ordered_logical_occurrence_ids == spec.ordered_logical_occurrence_ids
    assert analysis.enumerated_order_count == 6
    assert analysis.order_enumeration_complete is True
    assert len(analysis.vector_prefix_totals) == 18
    assert tuple(
        (row.prefix_length, row.full_order)
        for row in analysis.vector_prefix_totals
    ) == tuple(
        sorted(
            (row.prefix_length, row.full_order)
            for row in analysis.vector_prefix_totals
        )
    )
    assert all(
        row.prefix_occurrence_ids == row.full_order[: row.prefix_length]
        for row in analysis.vector_prefix_totals
    )


def test_prefix_totals_use_sum_for_traffic_and_max_for_capacity() -> None:
    _, _, _, spec, _, analysis = _analysis()
    a, b, c = (_cid("occurrence-a"), _cid("occurrence-b"), _cid("occurrence-c"))
    row = next(
        row
        for row in analysis.vector_prefix_totals
        if row.full_order == (a, b, c) and row.prefix_length == 3
    )
    values = dict(row.values)

    assert values[KERNEL_TRANSITION_CALLS] == 27
    assert values[NONKERNEL_COMPUTE_EVENTS] == 16
    assert values[PROCESS_LAUNCHES] == 16
    assert values[READ_BYTES] == 16
    assert values[STAGED_BYTES] == 16
    assert values[OUTPUT_BYTES] == 16
    assert values[PEAK_MOUNTED_BYTES] == 12
    assert values[PEAK_WORKING_BYTES] == 12
    assert row.workload_vector_spec_id == spec.workload_vector_spec_id
    assert VectorPrefixTotalV1.from_dict(row.to_dict()) == row


def test_each_prefix_reports_componentwise_worst_frontier_not_one_scalar_order() -> None:
    _, _, _, _, _, analysis = _analysis()
    a, b, c = (_cid("occurrence-a"), _cid("occurrence-b"), _cid("occurrence-c"))
    prefix_one = analysis.prefix_worst_frontiers[0]

    # B is componentwise cheaper than A and is therefore absent from the
    # larger-is-worse frontier.  A and C trade off, so both must remain.
    assert len(prefix_one.points) == 2
    first_occurrences = {
        point.witness_orders[0][0] for point in prefix_one.points
    }
    assert first_occurrences == {a, c}
    assert all(
        all(order[0] in {a, c} for order in point.witness_orders)
        for point in prefix_one.points
    )
    assert all(len(point.witness_orders) == 2 for point in prefix_one.points)

    # At the full prefix, reducer commutativity gives one vector, but all six
    # complete orders remain explicit witnesses.
    full = analysis.prefix_worst_frontiers[-1]
    assert full.prefix_length == 3
    assert len(full.points) == 1
    assert len(full.points[0].witness_orders) == 6
    assert {order for order in full.points[0].witness_orders} == {
        row.full_order
        for row in analysis.vector_prefix_totals
        if row.prefix_length == 3
    }


def test_permutation_cap_is_fail_closed_and_never_emits_partial_frontier() -> None:
    registry, profile, actual, spec, vectors = _fixture()
    capped = replace(spec, permutation_cap=5)
    with pytest.raises(PermutationCapExceededError) as captured:
        analyze_workload_vectors_v1(capped, vectors, registry, profile, actual)
    assert captured.value.required_permutations == 6
    assert captured.value.permutation_cap == 5


def test_analysis_roundtrip_and_exact_replay() -> None:
    registry, profile, actual, spec, vectors, analysis = _analysis()
    with pytest.raises(WorkloadVectorV1Error, match="requires native occurrence"):
        WorkloadVectorAnalysisV1.from_dict(analysis.to_dict())
    parsed = WorkloadVectorAnalysisV1.from_dict(
        analysis.to_dict(),
        spec=spec,
        occurrence_vectors=vectors,
        registry=registry,
        comparison_profile=profile,
        actual_profile=actual,
    )
    with pytest.raises(WorkloadVectorV1Error, match="native occurrence replay"):
        replace(analysis, _authority=None)

    assert parsed == analysis
    verify_workload_vector_analysis_v1(
        parsed, spec, vectors, registry, profile, actual
    )
    assert analysis.analysis_status == VECTOR_ONLY_COMPLETE_ENUMERATION
    assert analysis.official_scalar_cost is None
    assert analysis.official_N_break_even is None
    assert analysis.scalar_gate_status == SCALAR_GATE_NOT_RUN


def test_tampered_spec_prefix_and_analysis_content_ids_are_rejected() -> None:
    _, _, _, spec, _, analysis = _analysis()

    spec_doc = copy.deepcopy(spec.to_dict())
    spec_doc["occurrence_vectors"][0]["occurrence_work_sum_id"] = _cid("forged")
    with pytest.raises(WorkloadVectorV1Error, match="content ID mismatch"):
        WorkloadVectorSpecV1.from_dict(spec_doc)

    prefix_doc = copy.deepcopy(analysis.vector_prefix_totals[0].to_dict())
    prefix_doc["values"][0]["value"] += 1
    with pytest.raises(WorkloadVectorV1Error, match="content ID mismatch"):
        VectorPrefixTotalV1.from_dict(prefix_doc)

    analysis_doc = copy.deepcopy(analysis.to_dict())
    analysis_doc["prefix_worst_frontiers"][0]["points"][0]["values"][0][
        "value"
    ] += 1
    with pytest.raises(WorkloadVectorV1Error, match="content ID mismatch"):
        WorkloadVectorAnalysisV1.from_dict(analysis_doc)


def test_semantically_re_signed_frontier_tamper_fails_exact_replay() -> None:
    registry, profile, actual, spec, vectors, analysis = _analysis()
    frontier = analysis.prefix_worst_frontiers[0]
    forged = replace(
        analysis,
        prefix_worst_frontiers=(
            replace(frontier, points=frontier.points[:1]),
            *analysis.prefix_worst_frontiers[1:],
        ),
    )
    assert forged.workload_vector_analysis_id != analysis.workload_vector_analysis_id
    with pytest.raises(WorkloadVectorV1Error, match="does not match"):
        verify_workload_vector_analysis_v1(
            forged, spec, vectors, registry, profile, actual
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("official_scalar_cost", 0),
        ("official_scalar_cost", "ops+bytes/4096"),
        ("official_N_break_even", 0),
        ("official_N_break_even", 20),
        ("scalar_gate_status", "PASS"),
    ],
)
def test_null_scalar_and_break_even_lock_cannot_be_replaced(
    field: str, value: object
) -> None:
    _, _, _, spec, _, analysis = _analysis()
    with pytest.raises(WorkloadVectorV1Error):
        replace(spec, **{field: value})
    with pytest.raises(WorkloadVectorV1Error):
        replace(analysis, **{field: value})


@pytest.mark.parametrize(
    "forbidden_field",
    [
        "legacy_scalar_cost",
        "N_break_even",
        "worst_order_N_break_even",
        "crossing_claim",
    ],
)
def test_legacy_scalar_and_crossing_injection_is_rejected(
    forbidden_field: str,
) -> None:
    _, _, _, _, _, analysis = _analysis()
    document = analysis.to_dict()
    document[forbidden_field] = 0
    with pytest.raises(WorkloadVectorV1Error, match="field set mismatch"):
        WorkloadVectorAnalysisV1.from_dict(document)


def test_no_scalar_crossing_or_single_worst_order_claim_exists() -> None:
    _, _, _, _, _, analysis = _analysis()
    document = analysis.to_dict()

    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None
    assert document["scalar_gate_status"] == "NOT_RUN"
    assert "N_break_even" not in document
    assert "worst_order_N_break_even" not in document
    assert "worst_order" not in document
    assert "crossing" not in document
    assert len(document["prefix_worst_frontiers"][0]["points"]) == 2


def test_swapped_or_profile_mismatched_occurrence_vector_is_rejected() -> None:
    registry, profile, actual, spec, vectors = _fixture()
    occurrence_ids = spec.ordered_logical_occurrence_ids
    swapped = dict(vectors)
    swapped[occurrence_ids[0]] = vectors[occurrence_ids[1]]
    with pytest.raises(WorkloadVectorV1Error, match="identity mismatch"):
        analyze_workload_vectors_v1(spec, swapped, registry, profile, actual)

    vector = vectors[occurrence_ids[0]]
    wrong_sum = replace(
        vector.occurrence_sum, comparison_profile_id=_cid("wrong-profile")
    )
    wrong_profile = replace(vector, occurrence_sum=wrong_sum)
    mismatched = dict(vectors)
    mismatched[occurrence_ids[0]] = wrong_profile
    with pytest.raises(WorkloadVectorV1Error, match="reference mismatch"):
        analyze_workload_vectors_v1(
            spec, mismatched, registry, profile, actual
        )


def test_missing_or_extra_occurrence_input_is_rejected() -> None:
    registry, profile, actual, spec, vectors = _fixture()
    missing = dict(vectors)
    missing.pop(spec.ordered_logical_occurrence_ids[0])
    with pytest.raises(WorkloadVectorV1Error, match="input set"):
        analyze_workload_vectors_v1(spec, missing, registry, profile, actual)

    extra = dict(vectors)
    extra[_cid("unregistered-occurrence")] = next(iter(vectors.values()))
    with pytest.raises(WorkloadVectorV1Error, match="input set"):
        analyze_workload_vectors_v1(spec, extra, registry, profile, actual)


def test_self_signed_comparison_vector_cannot_enter_workload_analysis() -> None:
    registry, profile, actual, spec, vectors = _fixture()
    occurrence_id = spec.ordered_logical_occurrence_ids[0]
    self_signed = ComparisonVectorV1(
        profile.comparison_profile_id,
        _cid("invented-work-vector"),
        occurrence_id,
        RouteKindEnum.DIRECT_FALLBACK,
        tuple((axis, 0) for axis in SHARED_AXES),
    )
    attacked = dict(vectors)
    attacked[occurrence_id] = self_signed  # type: ignore[assignment]
    with pytest.raises(WorkloadVectorV1Error, match="self-signed"):
        analyze_workload_vectors_v1(
            spec, attacked, registry, profile, actual  # type: ignore[arg-type]
        )


def test_cross_occurrence_native_work_splice_fails_replay() -> None:
    registry, profile, actual, spec, vectors = _fixture()
    first_id, second_id = spec.ordered_logical_occurrence_ids[:2]
    first = vectors[first_id]
    second = vectors[second_id]
    spliced = replace(first, local_attempt=second.local_attempt)
    attacked = dict(vectors)
    attacked[first_id] = spliced
    with pytest.raises(WorkloadVectorV1Error, match="native accounting replay failed"):
        analyze_workload_vectors_v1(spec, attacked, registry, profile, actual)
