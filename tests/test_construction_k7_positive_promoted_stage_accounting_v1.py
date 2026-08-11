from __future__ import annotations

import pytest

from acfqp import construction_k7_positive_promoted_stage_accounting_v1 as subject
from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS
from tests.test_construction_k7_positive_promoted_overlay_v1 import positive_promoted
from tests.test_v075_batched_causal_occurrence_successor_v1 import (
    positive_batched_occurrence,
)


@pytest.fixture(scope="module")
def accounted_positive(positive_promoted):
    result = positive_promoted[-1]
    return subject.record_positive_promoted_abstract_route_v1(result)


def test_domain_and_surface_are_additive() -> None:
    assert subject.LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS
    assert len(subject.LOCAL_DOMAINS) == 1
    assert set(subject.__all__) == {
        "CANONICAL_STAGE_PLAN_V1",
        "ConstructionK7PositivePromotedStageAccountingV1Error",
        "LOCAL_DOMAINS",
        "PositivePromotedStageAccountingResultV1",
        "record_positive_promoted_abstract_route_v1",
        "verify_positive_promoted_stage_accounting_v1",
    }


def test_fresh_route_has_five_native_zero_preserving_stage_vectors(
    accounted_positive,
) -> None:
    result = subject.verify_positive_promoted_stage_accounting_v1(
        accounted_positive
    )
    document = result.to_document()
    assert len(result.recorded_stages) == 5
    assert all(len(row.work_vector.records) == 202 for row in result.recorded_stages)
    assert document["stage_local_counter_record_count"] == 1_010
    assert document["fresh_planner_called_exactly_once"] is True
    assert document["promoted_model_reused_without_rebuild"] is True
    assert document["fresh_ground_or_observer_event_count"] == 0
    assert document["local_fallback_rebuild_native_zero"] is True
    assert document["nine_shared_paths_are_stage_placeholders"] is True


def test_only_open_checkpoint_stage_records_fresh_planner_work(
    accounted_positive,
) -> None:
    rows = accounted_positive.recorded_stages
    planner = rows[3]
    values = planner.work_vector.values
    assert planner.operation_events
    assert values["build.open_checkpoint_policy_assignments_evaluated"] == (
        accounted_positive.positive_result.plan.proof.policy_assignments_evaluated
    )
    assert values["build.open_checkpoint_batch_v2_policy_assignment_cap_checks"] == (
        accounted_positive.positive_result.plan.proof.policy_assignments_evaluated
    )
    assert any(
        value > 0
        for path, value in values.items()
        if path.startswith("build.open_checkpoint_")
    )
    for row in rows[:3]:
        assert not row.operation_events
    assert len(rows[4].operation_events) == 1


def test_abstract_route_reconciliation_and_family_exclusivity(
    accounted_positive,
) -> None:
    closed = accounted_positive.recorded_stages[-1].work_vector.values
    assert closed["route.attempts"] == 1
    assert closed["route.successes"] == 1
    assert closed["route.failures"] == 0
    aggregate = {
        path: sum(row.work_vector.values[path] for row in accounted_positive.recorded_stages)
        for path in accounted_positive.recorded_stages[0].work_vector.values
    }
    assert all(
        value == 0
        for path, value in aggregate.items()
        if path.startswith(("local.", "fallback.", "rebuild."))
    )
    assert aggregate["acquisition.incremental_engine_ground_draws"] == 0


def test_shared_paths_remain_explicit_stage_placeholders(accounted_positive) -> None:
    for row in accounted_positive.recorded_stages:
        assert all(
            row.work_vector.values[path] == 0
            for path in subject.SHARED_PLACEHOLDER_PATHS
        )
    document = accounted_positive.to_document()
    assert document["shared_resource_receipts_issued"] is False
    assert document["occurrence_work_vector_issued"] is False
    assert document["terminal_artifact_issued"] is False
    assert document["campaign_occurrence_closed"] is False
    assert document["official_execution_allowed"] is False


def test_stage_reordering_is_rejected(accounted_positive) -> None:
    original = accounted_positive.recorded_stages
    try:
        object.__setattr__(
            accounted_positive,
            "recorded_stages",
            (original[1], original[0], *original[2:]),
        )
        with pytest.raises(
            subject.ConstructionK7PositivePromotedStageAccountingV1Error
        ):
            subject.verify_positive_promoted_stage_accounting_v1(
                accounted_positive
            )
    finally:
        object.__setattr__(accounted_positive, "recorded_stages", original)
