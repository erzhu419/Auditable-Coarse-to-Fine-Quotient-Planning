from __future__ import annotations

import pytest

from acfqp import construction_k7_query_bound_second_recovery_request_v1 as subject
from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS
from tests.test_construction_k7_query_bound_ground_transaction_v1 import (
    real_query_bound_ground_transaction,
)
from tests.test_construction_k7_query_bound_overlay_replanning_v1 import (
    real_overlay_replanning,
)


def test_domains_and_public_surface_remain_additive() -> None:
    assert subject.LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS
    assert set(subject.__all__) == {
        "ConstructionK7QueryBoundSecondRecoveryRequestV1Error",
        "LOCAL_DOMAINS",
        "SecondQueryBoundRecoveryRequestV1",
        "SecondQueryBoundValidationRequestV1",
        "prepare_second_query_bound_recovery_request_v1",
        "verify_second_query_bound_recovery_request_v1",
    }


@pytest.fixture(scope="module")
def real_second_request(real_overlay_replanning):
    _trace, _transaction, predecessor = real_overlay_replanning
    request = subject.prepare_second_query_bound_recovery_request_v1(predecessor)
    return predecessor, request


def test_real_second_request_selects_only_final_checkpoint_rows(
    real_second_request,
) -> None:
    predecessor, request = real_second_request
    assert request.predecessor_replanning_id == predecessor.result_id
    assert request.source_model_id == predecessor.successor_model.model_id
    assert request.source_proof_id == predecessor.successor_proof.proof_id
    assert len(request.rows) == 7
    assert len(request.requested_rows) == 6
    assert len(request.cap_blocked_rows) == 1
    assert request.requested_additional_draw_count == 12_288
    assert tuple(item.current_validation_draw_count for item in request.requested_rows) == (
        10_240,
    ) * 6
    assert tuple(item.next_registered_checkpoint for item in request.requested_rows) == (
        12_288,
    ) * 6
    assert tuple(item.requested_additional_draw_count for item in request.requested_rows) == (
        2_048,
    ) * 6
    assert request.cap_blocked_rows[0].current_validation_draw_count == 6_144


def test_real_second_request_replays_and_remains_no_access(
    real_second_request,
) -> None:
    predecessor, request = real_second_request
    replayed = subject.verify_second_query_bound_recovery_request_v1(
        request,
        predecessor=predecessor,
    )
    assert replayed.to_document() == request.to_document()
    document = request.to_document()
    assert document["transaction_index"] == 2
    assert document["maximum_local_transactions_per_logical_occurrence"] == 2
    assert document["activation_state"] == "PREPARED_NO_ACCESS"
    assert document["ground_access_count"] == 0
    assert document["ground_execution_authorized"] is False
    assert document["plan_certificate_issued"] is False
    assert document["official_execution_allowed"] is False


def test_second_row_request_is_not_caller_mintable() -> None:
    with pytest.raises(subject.ConstructionK7QueryBoundSecondRecoveryRequestV1Error):
        subject.SecondQueryBoundValidationRequestV1(
            object(),
            "0" * 64,
            "1" * 64,
            10_240,
            12_288,
            2_048,
            "REQUEST_FINAL_REGISTERED_CHECKPOINT",
        )
