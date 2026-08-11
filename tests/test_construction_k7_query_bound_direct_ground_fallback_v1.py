from __future__ import annotations

from fractions import Fraction
import os

import pytest

from acfqp import construction_k7_query_bound_direct_ground_fallback_v1 as subject
from acfqp import v075_registered_occurrence_worker_v1 as worker_v1
from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS
from tests.test_construction_k7_query_bound_final_local_replanning_v1 import (
    real_final_local_replanning,
)
from tests.test_construction_k7_query_bound_ground_transaction_v1 import (
    real_query_bound_ground_transaction,
)
from tests.test_construction_k7_query_bound_overlay_replanning_v1 import (
    real_overlay_replanning,
)
from tests.test_construction_k7_query_bound_second_ground_transaction_v1 import (
    real_second_ground_transaction,
)
from tests.test_construction_k7_query_bound_second_recovery_request_v1 import (
    real_second_request,
)


def test_domains_and_public_surface_remain_additive() -> None:
    assert subject.LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS
    assert set(subject.__all__) == {
        "ConstructionK7QueryBoundDirectGroundFallbackV1Error",
        "LOCAL_DOMAINS",
        "MAX_FALLBACK_ACTIONS",
        "MAX_FALLBACK_BELLMAN_BACKUPS",
        "MAX_FALLBACK_OUTCOME_ROWS",
        "MAX_FALLBACK_STATES",
        "QueryBoundDirectFallbackTerminalClassV1",
        "QueryBoundDirectFallbackTerminalCodeV1",
        "QueryBoundDirectFallbackWorkV1",
        "QueryBoundDirectGroundFallbackV1",
        "QueryBoundDirectGroundFallbackVerificationV1",
        "QueryBoundExactGroundPolicyDecisionV1",
        "QueryBoundExactGroundRowV1",
        "execute_query_bound_direct_ground_fallback_v1",
        "verify_query_bound_direct_ground_fallback_v1",
    }


@pytest.fixture(scope="module")
def real_direct_ground_fallback(real_final_local_replanning):
    if os.environ.get("ACFQP_RUN_REAL_K7_QUERY_BOUND_GROUND") != "1":
        pytest.skip("set ACFQP_RUN_REAL_K7_QUERY_BOUND_GROUND=1")
    _transaction, predecessor = real_final_local_replanning
    result = subject.execute_query_bound_direct_ground_fallback_v1(predecessor)
    return predecessor, result


def test_real_fallback_uses_one_fresh_direct_identity(
    real_direct_ground_fallback,
) -> None:
    predecessor, result = real_direct_ground_fallback
    first = predecessor.transaction.predecessor.transaction
    second = predecessor.transaction
    assert result.occurrence_identity.arm is (
        worker_v1.V075WorkerArmV1.MATCHED_DIRECT_GROUND
    )
    assert result.occurrence_identity.context_id == (
        predecessor.successor_model.context.context_id
    )
    assert result.occurrence_identity.target_tape_namespace_id not in {
        first.native_occurrence.target_tape_namespace_id,
        second.native_occurrence.target_tape_namespace_id,
    }
    document = result.to_document()
    assert document["final_local_replanning_id"] == predecessor.result_id
    assert document["logical_occurrence_id"] == (
        predecessor.transaction.request.logical_occurrence_id
    )
    assert document["local_transaction_count"] == 2
    assert document["maximum_local_transactions_per_logical_occurrence"] == 2
    assert document["transaction_3_created"] is False
    assert document["cumulative_local_ground_draw_count"] == 25_344


def test_real_fallback_completely_enumerates_and_solves_exact_ground_h2(
    real_direct_ground_fallback,
) -> None:
    _predecessor, result = real_direct_ground_fallback
    assert len(result.exact_rows) == 96
    assert sum(len(item.atoms) for item in result.exact_rows) == 1_440
    assert len(result.policy) == 16
    assert result.selected_expected_reward == Fraction(3, 64)
    assert result.selected_failure_probability == Fraction(346_437, 12_500_000)
    assert result.selected_failure_probability <= Fraction(1, 20)
    assert result.terminal_class is (
        subject.QueryBoundDirectFallbackTerminalClassV1.PLAN_CERTIFICATE
    )
    assert result.terminal_code is (
        subject.QueryBoundDirectFallbackTerminalCodeV1.FULL_GROUND_FALLBACK
    )
    assert result.work.states_expanded == 30
    assert result.work.actions_evaluated == 96
    assert result.work.ground_steps == 96
    assert result.work.outcome_rows == 1_440
    assert result.work.bellman_backups == 102
    row_ids = {item.row_id for item in result.exact_rows}
    assert len(row_ids) == 96
    assert {item.exact_ground_row_id for item in result.policy} <= row_ids
    assert sum(item.remaining_horizon == 2 for item in result.policy) == 1
    assert sum(item.remaining_horizon == 1 for item in result.policy) == 15


def test_real_fallback_terminal_and_native_work_are_honest(
    real_direct_ground_fallback,
) -> None:
    _predecessor, result = real_direct_ground_fallback
    document = result.to_document()
    assert document["private_environment_reveal_matched"] is True
    assert document["private_law_accessed_by_fallback"] is True
    assert document["private_law_serialized"] is False
    assert document["complete_exact_h2_ground_inventory"] is True
    assert document["complete_exact_ground_search"] is True
    assert document["selected_policy_exactly_optimal_under_risk_constraint"] is True
    assert document["full_ground_infeasibility_proved"] is False
    assert document["plan_certificate_issued"] is True
    assert document["infeasibility_certificate_issued"] is False
    assert document["construction_only"] is True
    assert document["scientific_endpoint_credit_allowed"] is False
    assert document["formal_counter_records_materialized"] is False
    assert document["campaign_closure_issued"] is False
    assert document["official_execution_allowed"] is False
    assert document["next_required_action"] == (
        "MATERIALIZE_K7_COUNTER_RECORDS_AND_OCCURRENCE_CLOSURE"
    )
    assert document["work"]["counters"] == {
        "fallback.actions_evaluated": 96,
        "fallback.bellman_backups": 102,
        "fallback.ground_steps": 96,
        "fallback.outcome_rows": 1_440,
        "fallback.states_expanded": 30,
    }


def test_real_fallback_is_recomputed_by_semantic_verifier(
    real_direct_ground_fallback,
) -> None:
    _predecessor, result = real_direct_ground_fallback
    verification = subject.verify_query_bound_direct_ground_fallback_v1(result)
    assert verification.fallback_result_id == result.result_id
    assert verification.exact_ground_inventory_id == result.inventory_id
    assert verification.fallback_work_id == result.work.work_id
    document = verification.to_document()
    assert document["complete_exact_h2_inventory_rebuilt"] is True
    assert document["constrained_ground_optimum_recomputed"] is True
    assert document["verification_work_included_in_operational_fallback_work"] is False


def test_direct_fallback_result_is_not_caller_mintable() -> None:
    with pytest.raises(subject.ConstructionK7QueryBoundDirectGroundFallbackV1Error):
        subject.QueryBoundDirectGroundFallbackV1(
            object(),
            object(),
            object(),
            object(),
            object(),
            (),
            (),
            None,
            None,
            object(),
            subject.QueryBoundDirectFallbackTerminalClassV1.INFEASIBILITY_CERTIFICATE,
            subject.QueryBoundDirectFallbackTerminalCodeV1.FULL_GROUND_EXACT_INFEASIBLE,
        )
