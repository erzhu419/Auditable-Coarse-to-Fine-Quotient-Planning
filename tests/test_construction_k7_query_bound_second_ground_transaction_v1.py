from __future__ import annotations

import pytest

from acfqp import construction_k7_query_bound_second_ground_transaction_v1 as subject
from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS
from tests.test_construction_k7_query_bound_ground_transaction_v1 import (
    real_query_bound_ground_transaction,
)
from tests.test_construction_k7_query_bound_overlay_replanning_v1 import (
    real_overlay_replanning,
)
from tests.test_construction_k7_query_bound_second_recovery_request_v1 import (
    real_second_request,
)


def test_domains_and_public_surface_remain_additive() -> None:
    assert subject.LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS
    assert set(subject.__all__) == {
        "ConstructionK7QueryBoundSecondGroundTransactionV1Error",
        "ENVIRONMENT_MARKER",
        "LOCAL_DOMAINS",
        "SecondQueryBoundGroundTransactionV1",
        "SecondQueryBoundNamespaceBindingV1",
        "SecondQueryBoundRowExecutionV1",
        "execute_second_query_bound_ground_transaction_v1",
        "verify_second_query_bound_ground_transaction_v1",
    }


@pytest.fixture(scope="module")
def real_second_ground_transaction(real_second_request):
    predecessor, request = real_second_request
    transaction = subject.execute_second_query_bound_ground_transaction_v1(
        predecessor=predecessor,
        request=request,
    )
    return predecessor, request, transaction


def test_real_final_local_transaction_executes_only_requested_rows(
    real_second_ground_transaction,
) -> None:
    predecessor, request, transaction = real_second_ground_transaction
    assert transaction.namespace_binding.target_tape_namespace_id != (
        predecessor.transaction.namespace_binding.target_tape_namespace_id
    )
    assert transaction.namespace_binding.recovery_request_id == request.request_id
    assert len(transaction.row_executions) == 6
    assert len(transaction.observer_closure.appends) == 12
    assert len(transaction.observer_closure.support_freezes) == 6
    assert transaction.support_discovery_draw_count == 384
    assert transaction.requested_validation_draw_count == 12_288
    assert transaction.total_ground_draw_count == 12_672
    assert tuple(
        item.batch.request.stream_identity.lane.value
        for item in transaction.observer_closure.appends
    ) == ("DISCOVERY", "VALIDATION") * 6
    assert tuple(
        item.batch.request.accepted_draw_count
        for item in transaction.observer_closure.appends
    ) == (64, 2_048) * 6


def test_real_final_local_transaction_replays_and_keeps_boundary(
    real_second_ground_transaction,
) -> None:
    _predecessor, _request, transaction = real_second_ground_transaction
    assert subject.verify_second_query_bound_ground_transaction_v1(transaction) is transaction
    document = transaction.to_document()
    assert document["transaction_index"] == 2
    assert document["maximum_local_transactions_per_logical_occurrence"] == 2
    assert document["final_local_transaction_executed"] is True
    assert document["local_transaction_budget_exhausted_after_this_attempt"] is True
    assert document["immutable_overlay_compiled"] is False
    assert document["post_transaction_replanning_performed"] is False
    assert document["plan_certificate_issued"] is False
    assert document["official_execution_allowed"] is False


def test_second_namespace_binding_is_not_caller_mintable() -> None:
    with pytest.raises(subject.ConstructionK7QueryBoundSecondGroundTransactionV1Error):
        subject.SecondQueryBoundNamespaceBindingV1(
            object(),
            "0" * 64,
            "1" * 64,
            "2" * 64,
            "3" * 64,
            "4" * 64,
            "5" * 64,
            "6" * 64,
            "NO_PRIOR",
        )
