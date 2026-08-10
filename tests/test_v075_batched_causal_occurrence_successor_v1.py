from __future__ import annotations

from dataclasses import replace
from fractions import Fraction

import pytest

from acfqp import v075_adaptive_acquisition_round_bundle_authority_v1 as control
from acfqp import v075_batched_causal_acquisition_operator_v1 as operator
from acfqp import v075_batched_causal_occurrence_successor_v1 as successor
from acfqp import v075_batch_native_total_lift_authority_v1 as total_lift
from acfqp import v075_multistage_observer_lifecycle_v1 as lifecycle
from acfqp import v075_registered_occurrence_worker_v1 as worker
from tests.test_v075_production_occurrence_authority_v1 import _open


@pytest.fixture(scope="module")
def positive_batched_occurrence():
    laws = tuple(((1, Fraction(1, 1)),) for _ in range(3))
    values = _open(
        "batched-causal-positive",
        scientific_ordinal=0,
        private_laws=laws,
    )
    entry = values[2]
    result = successor.run_v075_batched_causal_occurrence_successor_v1(
        controller=values[5],
        namespace=values[0],
        context=values[0].family.replicate_contexts[entry.context_ordinal],
        arm=entry.arm,
        occurrence_ordinal=entry.occurrence_identity.occurrence_ordinal,
        source_prior_transport=values[1].source_prior_transport,
    )
    sealed = values[5].close_construction_v1(
        authority=values[3],
        private_environment=values[4],
        process_launches=result.counters.process_launches,
        child_intent_count=result.counters.child_action_rows_materialized,
        terminal_code=(
            lifecycle.V075LifecycleTerminalCodeV1
            .COMPLETE_REGISTERED_CHECKPOINT_CLOSED
        ),
    )
    lineage = total_lift.freeze_v075_batch_native_total_lift_lineage_v1(
        backend_result=result.final_backend_result,
        planner_result=result.final_planner_result,
        sealed_lifecycle=sealed,
    )
    exact_replay = (
        total_lift.mint_v075_batch_native_construction_exact_replay_v1(
            lineage=lineage,
            authority=values[3],
            private_environment=values[4],
        )
    )
    lift_verification = (
        total_lift.evaluate_v075_batch_native_construction_total_lift_v1(
            lineage=lineage,
            exact_replay=exact_replay,
        )
    )
    return result, values, sealed, lineage, exact_replay, lift_verification


def test_batched_successor_turns_the_failed_frontier_into_a_positive_candidate(
    positive_batched_occurrence,
) -> None:
    result = positive_batched_occurrence[0]
    assert result.initial_planner_result.status.value == "NO_RISK_FEASIBLE_POLICY"
    assert result.final_planner_result.status.value == (
        "CANDIDATE_CERTIFIED_FOR_EXACT_TOTAL_LIFT"
    )
    assert result.outcome is (
        successor.V075BatchedCausalOccurrenceOutcomeV1
        .CANDIDATE_READY_FOR_EXACT_TOTAL_LIFT
    )
    assert result.ready_for_exact_total_lift is True
    assert result.final_planner_result.diagnostic_failed_frontier_row_ids == ()
    assert len(result.authorization.selected_candidate_ids) > 1
    assert result.counters.incremental_draws <= 160_960
    assert result.counters.child_action_rows_materialized <= 19
    assert result.counters.process_launches == 0


def test_matched_no_operator_control_still_selects_only_one_catalogue(
    positive_batched_occurrence,
) -> None:
    result = positive_batched_occurrence[0]
    baseline = control.authorize_v075_adaptive_round_bundle_v1(result.frontier)
    assert baseline.status is control.V075BundleAuthorizationStatusV1.AUTHORIZED
    assert baseline.selected_candidate_id is not None
    assert len({item.candidate_id for item in baseline.intents}) == 1
    assert len(result.authorization.selected_candidate_ids) > 1
    selected = {
        item.candidate_id: item for item in result.frontier.candidates
    }
    assert result.authorization.incremental_draw_count < sum(
        selected[item].incremental_draw_count
        for item in result.authorization.selected_candidate_ids
    )
    assert operator.NO_OPERATOR_CONTROL_PROFILE == control.PROFILE_KEY


def test_successor_replays_backend_planner_union_and_append_exactly(
    positive_batched_occurrence,
) -> None:
    result = positive_batched_occurrence[0]
    verification = (
        successor.verify_v075_batched_causal_occurrence_successor_v1(result)
    )
    assert verification.result_id == result.result_id
    assert verification.occurrence_id == result.occurrence_identity.occurrence_id
    assert verification.final_backend_result_id == result.final_backend_result.result_id
    assert verification.final_planner_result_id == result.final_planner_result.result_id
    assert verification.outcome is result.outcome


def test_positive_preclose_result_can_close_the_same_observer_lifecycle(
    positive_batched_occurrence,
) -> None:
    result, values, sealed, *_lift = positive_batched_occurrence
    assert sealed.closure.occurrence_id == result.occurrence_identity.occurrence_id
    assert sealed.closure.batch_ids == tuple(
        item.batch_id for item in values[5].batches
    )
    assert sealed.closure.accepted_draw_count == result.counters.accepted_draws


def test_closed_batched_candidate_passes_exact_h2_total_lift(
    positive_batched_occurrence,
) -> None:
    _result, _values, _sealed, lineage, exact_replay, verification = (
        positive_batched_occurrence
    )
    assert verification.candidate.status is (
        total_lift.V075BatchTotalLiftConstructionStatusV1
        .EXACT_POSITIVE_CONSTRUCTION_CONTROL
    )
    replayed = (
        total_lift.verify_v075_batch_native_construction_total_lift_candidate_v1(
            lineage=lineage,
            exact_replay=exact_replay,
            claimed=verification.candidate,
        )
    )
    assert replayed.candidate.candidate_id == verification.candidate.candidate_id
    assert verification.candidate.to_document()["scientific_endpoint_credit_allowed"] is False


def test_successor_does_not_overclaim_certificate_or_k7_accounting(
    positive_batched_occurrence,
) -> None:
    document = positive_batched_occurrence[0].to_document()
    assert document["scientific_plan_certificate"] is False
    assert document["occurrence_closed"] is False
    assert document["production_integration_ready"] is False
    assert document["k7_counter_records_issued"] == 0
    assert successor.PRODUCTION_INTEGRATION_READY is False


def test_terminal_or_execution_identity_tampering_fails_closed(
    positive_batched_occurrence,
) -> None:
    result = positive_batched_occurrence[0]
    with pytest.raises(
        successor.V075BatchedCausalOccurrenceInvariantViolation,
        match="outcome",
    ):
        replace(
            result,
            outcome=(
                successor.V075BatchedCausalOccurrenceOutcomeV1
                .BATCHED_OPERATOR_NOT_CERTIFIED
            ),
        )
    with pytest.raises(
        successor.V075BatchedCausalOccurrenceInvariantViolation,
        match="identity graph",
    ):
        replace(
            result,
            appended_batch_ids=result.appended_batch_ids[:-1],
        )


def test_successor_rejects_direct_ground_before_observation() -> None:
    values = _open(
        "batched-causal-direct-reject",
        scientific_ordinal=4,
    )
    entry = values[2]
    assert entry.arm is worker.V075WorkerArmV1.MATCHED_DIRECT_GROUND
    with pytest.raises(
        successor.V075BatchedCausalOccurrenceInvariantViolation,
        match="inputs",
    ):
        successor.run_v075_batched_causal_occurrence_successor_v1(
            controller=values[5],
            namespace=values[0],
            context=values[0].family.replicate_contexts[entry.context_ordinal],
            arm=entry.arm,
            occurrence_ordinal=entry.occurrence_identity.occurrence_ordinal,
        )
    assert values[5].batches == ()
    assert values[5].events == ()
