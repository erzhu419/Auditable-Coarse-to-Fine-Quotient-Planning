from __future__ import annotations

import pytest

from acfqp import construction_k7_query_bound_final_local_replanning_v1 as subject
from acfqp import v075_batch_native_planning_backend_v2 as planning_v2
from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS
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


def test_domain_and_public_surface_remain_additive() -> None:
    assert subject.LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS
    assert set(subject.__all__) == {
        "ConstructionK7QueryBoundFinalLocalReplanningV1Error",
        "LOCAL_DOMAINS",
        "QueryBoundFinalLocalReplanningV1",
        "compile_and_replan_final_local_transaction_v1",
        "require_query_bound_final_local_replanning_v1",
        "verify_query_bound_final_local_replanning_v1",
    }


@pytest.fixture(scope="module")
def real_final_local_replanning(real_second_ground_transaction):
    _predecessor, _request, transaction = real_second_ground_transaction
    result = subject.compile_and_replan_final_local_transaction_v1(transaction)
    return transaction, result


def test_real_final_local_overlay_updates_only_requested_rows(
    real_final_local_replanning,
) -> None:
    transaction, result = real_final_local_replanning
    assert len(result.deltas) == 6
    assert len(result.source_model.rows) == 18
    assert len(result.successor_model.rows) == 18
    assert len(result.changed_row_binding_ids) == 6
    assert len(result.preserved_row_binding_ids) == 12
    assert sum(item.source_validation_draw_count for item in result.deltas) == 61_440
    assert sum(item.additional_validation_draw_count for item in result.deltas) == 12_288
    assert sum(item.target_validation_draw_count for item in result.deltas) == 73_728
    assert tuple(item.source_validation_draw_count for item in result.deltas) == (
        10_240,
    ) * 6
    assert tuple(item.target_validation_draw_count for item in result.deltas) == (
        12_288,
    ) * 6
    assert {
        item.signed_batch.batch_id for item in result.deltas
    } == {
        item.validation_batch_id for item in transaction.row_executions
    }

    source = {item.row_binding_id: item for item in result.source_model.rows}
    successor = {
        item.row_binding_id: item for item in result.successor_model.rows
    }
    for binding_id in result.preserved_row_binding_ids:
        assert source[binding_id].to_document() == successor[binding_id].to_document()
    for binding_id in result.changed_row_binding_ids:
        assert source[binding_id].row_id != successor[binding_id].row_id
        assert [item.to_document() for item in source[binding_id].support] == [
            item.to_document() for item in successor[binding_id].support
        ]


def test_real_final_local_result_replans_and_routes_soundly(
    real_final_local_replanning,
) -> None:
    _transaction, result = real_final_local_replanning
    replayed = subject.verify_query_bound_final_local_replanning_v1(result)
    assert replayed.to_document() == result.to_document()
    assert result.successor_proof.model == result.successor_model
    assert result.successor_proof.route is planning_v2.V075PlanningRouteV2.ADAPTIVE_QUOTIENT
    document = result.to_document()
    assert document["transaction_1_ground_draw_count"] == 12_672
    assert document["transaction_2_ground_draw_count"] == 12_672
    assert document["cumulative_local_ground_draw_count"] == 25_344
    assert document["local_transaction_count"] == 2
    assert document["maximum_local_transactions_per_logical_occurrence"] == 2
    assert document["local_allowed_after_result"] is False
    assert document["local_forbidden_reason"] == "LOCAL_TRANSACTION_BUDGET_EXHAUSTED"
    assert document["ground_access_after_closed_transaction_2"] == 0
    assert document["plan_certificate_issued"] is False
    assert document["official_execution_allowed"] is False
    failed = result.successor_proof.failed_frontier is not None
    assert document["proof_still_failed"] is failed
    assert document["direct_fallback_required"] is failed
    assert document["next_required_action"] == (
        "DIRECT_GROUND_FALLBACK"
        if failed
        else "INDEPENDENT_TOTAL_LIFT_AND_PLAN_CERTIFICATE_AUDIT"
    )
    frontier = result.successor_proof.failed_frontier
    assert result.successor_proof.outcome is planning_v2.V075NumericalOutcomeV2.FAILED_FRONTIER
    assert frontier is not None
    assert frontier.reason is planning_v2.V075FailedProofReasonV2.RISK_BOUND_FAILED
    assert len(frontier.obligations) == 7
    assert all(item.next_registered_checkpoint is None for item in frontier.obligations)
    assert sorted(item.current_validation_draw_count for item in frontier.obligations) == [
        6_144,
        12_288,
        12_288,
        12_288,
        12_288,
        12_288,
        12_288,
    ]
    assert result.successor_model.model_id == (
        "5d3f39d2af0adf28e6e946117ceeb0866b9f9d6ce97934277e8be010a99abd68"
    )
    assert result.successor_proof.proof_id == (
        "46a2d7a5450a85709ba26b751876f4b8900e5efe666b3af607e3b2993760c009"
    )
    assert result.result_id == (
        "b0dc038c405d14c5bc599377589dcaa1d23aec90d3ce001b2b5c46cfa9e68932"
    )


def test_final_local_result_is_not_caller_mintable() -> None:
    with pytest.raises(subject.ConstructionK7QueryBoundFinalLocalReplanningV1Error):
        subject.QueryBoundFinalLocalReplanningV1(
            object(),
            object(),
            object(),
            object(),
            (),
            object(),
            object(),
        )
