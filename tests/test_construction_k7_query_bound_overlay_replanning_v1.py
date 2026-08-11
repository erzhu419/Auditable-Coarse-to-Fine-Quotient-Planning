from __future__ import annotations

import os

import pytest

from acfqp import construction_k7_query_bound_overlay_replanning_v1 as subject
from acfqp import v075_batch_native_planning_backend_v2 as planning_v2
from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS, canonical_json_bytes
from tests.test_construction_k7_query_bound_ground_transaction_v1 import (
    real_query_bound_ground_transaction,
)


def test_domain_and_public_surface_remain_additive() -> None:
    assert subject.LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS
    assert set(subject.__all__) == {
        "ConstructionK7QueryBoundOverlayReplanningV1Error",
        "LOCAL_DOMAINS",
        "QueryBoundOverlayReplanningV1",
        "compile_and_replan_query_bound_ground_transaction_v1",
        "verify_query_bound_overlay_replanning_bytes_v1",
        "verify_query_bound_overlay_replanning_v1",
    }
    assert {
        "V075QueryBoundValidationDeltaV2",
        "compile_v075_query_bound_validation_overlay_v2",
        "freeze_v075_query_bound_validation_delta_v2",
    } <= set(planning_v2.__all__)


@pytest.fixture(scope="module")
def real_overlay_replanning(real_query_bound_ground_transaction):
    if os.environ.get("ACFQP_RUN_REAL_K7_QUERY_BOUND_GROUND") != "1":
        pytest.skip("set ACFQP_RUN_REAL_K7_QUERY_BOUND_GROUND=1")
    trace_raw, _request, transaction = real_query_bound_ground_transaction
    result = subject.compile_and_replan_query_bound_ground_transaction_v1(
        source_trace_bytes=trace_raw,
        transaction=transaction,
    )
    return trace_raw, transaction, result


def test_real_signed_deltas_compile_only_requested_rows(
    real_overlay_replanning,
) -> None:
    _trace_raw, transaction, result = real_overlay_replanning
    assert len(result.deltas) == 6
    assert len(result.source_model.rows) == 18
    assert len(result.successor_model.rows) == 18
    assert len(result.changed_row_binding_ids) == 6
    assert len(result.preserved_row_binding_ids) == 12
    assert result.source_validation_draw_count == 49_152
    assert result.added_validation_draw_count == 12_288
    assert result.successor_validation_draw_count == 61_440
    assert tuple(item.source_validation_draw_count for item in result.deltas) == (
        8_192,
    ) * 6
    assert tuple(item.target_validation_draw_count for item in result.deltas) == (
        10_240,
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


def test_real_successor_replans_and_exact_bytes_replay(
    real_overlay_replanning,
) -> None:
    trace_raw, transaction, result = real_overlay_replanning
    assert result.successor_proof.model == result.successor_model
    assert subject.verify_query_bound_overlay_replanning_v1(result) is result
    assert result.successor_proof.route is planning_v2.V075PlanningRouteV2.ADAPTIVE_QUOTIENT
    replayed = subject.verify_query_bound_overlay_replanning_bytes_v1(
        source_trace_bytes=trace_raw,
        transaction=transaction,
        result_bytes=canonical_json_bytes(result.to_document()),
    )
    assert replayed.to_document() == result.to_document()


def test_real_result_keeps_certificate_boundary(real_overlay_replanning) -> None:
    _trace_raw, _transaction, result = real_overlay_replanning
    document = result.to_document()
    frontier = result.successor_proof.failed_frontier
    assert result.successor_proof.outcome is planning_v2.V075NumericalOutcomeV2.FAILED_FRONTIER
    assert frontier is not None
    assert frontier.reason is planning_v2.V075FailedProofReasonV2.RISK_BOUND_FAILED
    assert len(frontier.obligations) == 7
    assert sum(item.next_registered_checkpoint == 12_288 for item in frontier.obligations) == 6
    assert sum(item.next_registered_checkpoint is None for item in frontier.obligations) == 1
    assert document["immutable_query_local_model_compiled"] is True
    assert document["same_query_replanned"] is True
    assert document["ground_access_after_closed_transaction"] == 0
    assert document["fresh_query_recovery_loop_closed_through_replanning"] is True
    assert document["proof_still_failed"] is True
    assert document["next_required_action"] == "FREEZE_TRANSACTION_2_OR_ROUTE_TO_FALLBACK"
    assert document["plan_certificate_issued"] is False
    assert document["campaign_closure_issued"] is False
    assert document["official_execution_allowed"] is False
