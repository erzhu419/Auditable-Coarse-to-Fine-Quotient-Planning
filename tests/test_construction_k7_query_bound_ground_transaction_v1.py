from __future__ import annotations

import hashlib
import os
from pathlib import Path

import pytest

from acfqp import construction_k7_query_bound_ground_transaction_v1 as subject
from acfqp import construction_k7_query_bound_recovery_overlay_v1 as overlay_v1
from acfqp import construction_k7_query_bound_recovery_request_v1 as request_v1
from acfqp import construction_k7_reusable_abstract_query_v1 as query_v1
from acfqp import construction_k7_reusable_build_epoch_authority_v1 as build_v1
from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS, canonical_json_bytes, loads_canonical_json


def _id(label: str) -> str:
    return hashlib.sha256(
        b"acfqp:k7-query-bound-ground-test:v1\x00" + label.encode("utf-8")
    ).hexdigest()


def test_domains_and_public_surface_remain_additive() -> None:
    assert subject.LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS
    assert set(subject.__all__) == {
        "ConstructionK7QueryBoundGroundTransactionV1Error",
        "ENVIRONMENT_MARKER",
        "LOCAL_DOMAINS",
        "QueryBoundGroundTransactionV1",
        "QueryBoundNamespaceBindingV1",
        "QueryBoundRowExecutionV1",
        "execute_query_bound_ground_transaction_v1",
        "verify_query_bound_ground_transaction_v1",
    }


@pytest.fixture(scope="module")
def real_query_bound_ground_transaction():
    if os.environ.get("ACFQP_RUN_REAL_K7_QUERY_BOUND_GROUND") != "1":
        pytest.skip("set ACFQP_RUN_REAL_K7_QUERY_BOUND_GROUND=1")
    retained = os.environ.get("ACFQP_CAUSAL_RECOVERY_TRACE")
    if not retained:
        pytest.fail("ACFQP_CAUSAL_RECOVERY_TRACE must name the retained real trace")
    trace_raw = Path(retained).read_bytes()
    envelope = build_v1.replay_reusable_build_epoch_source_v1(trace_raw)
    envelope_bytes = canonical_json_bytes(envelope.to_document())
    query = query_v1.freeze_reusable_abstract_query_spec_v1(
        build_epoch=envelope,
        logical_occurrence_id=_id("fresh-ground-query"),
        query_ordinal=0,
    )
    root_result = query_v1.run_reusable_abstract_query_v1(
        source_trace_bytes=trace_raw,
        build_epoch_envelope_bytes=envelope_bytes,
        query=query,
    )
    root_bytes = canonical_json_bytes(root_result.to_document())
    overlay = overlay_v1.apply_query_bound_cached_recovery_overlay_v1(
        source_trace_bytes=trace_raw,
        build_epoch_envelope_bytes=envelope_bytes,
        root_query_result_bytes=root_bytes,
    )
    overlay_bytes = canonical_json_bytes(overlay.to_document())
    request = request_v1.prepare_query_bound_recovery_request_v1(
        source_trace_bytes=trace_raw,
        build_epoch_envelope_bytes=envelope_bytes,
        root_query_result_bytes=root_bytes,
        overlay_bytes=overlay_bytes,
    )
    transaction = subject.execute_query_bound_ground_transaction_v1(
        source_trace_bytes=trace_raw,
        build_epoch_envelope_bytes=envelope_bytes,
        root_query_result_bytes=root_bytes,
        overlay_bytes=overlay_bytes,
        request_bytes=canonical_json_bytes(request.to_document()),
    )
    return trace_raw, request, transaction


def test_real_fresh_namespace_executes_only_requested_rows(
    real_query_bound_ground_transaction,
) -> None:
    trace_raw, request, transaction = real_query_bound_ground_transaction
    source = loads_canonical_json(trace_raw)
    source_namespace_id = source["causal_recovery_chain"]["final_model_epoch"][
        "target_tape_namespace_id"
    ]
    assert transaction.namespace_binding.target_tape_namespace_id != source_namespace_id
    assert transaction.namespace_binding.logical_occurrence_id == request.logical_occurrence_id
    assert transaction.namespace_binding.recovery_request_id == request.request_id

    assert len(transaction.row_executions) == 6
    assert len(transaction.observer_closure.appends) == 12
    assert len(transaction.observer_closure.support_freezes) == 6
    assert transaction.support_discovery_draw_count == 384
    assert transaction.requested_validation_draw_count == 12_288
    assert transaction.total_ground_draw_count == 12_672
    assert tuple(item.validation_request_id for item in transaction.row_executions) == tuple(
        item.request_id for item in request.requested_rows
    )
    assert tuple(
        append.batch.request.stream_identity.lane.value
        for append in transaction.observer_closure.appends
    ) == ("DISCOVERY", "VALIDATION") * 6
    assert tuple(
        append.batch.request.accepted_draw_count
        for append in transaction.observer_closure.appends
    ) == (64, 2_048) * 6


def test_real_transaction_replays_and_keeps_certificate_boundary(
    real_query_bound_ground_transaction,
) -> None:
    _trace, _request, transaction = real_query_bound_ground_transaction
    assert subject.verify_query_bound_ground_transaction_v1(transaction) is transaction
    document = transaction.to_document()
    assert document["request_verified_before_namespace_creation"] is True
    assert document["namespace_bound_before_ground_access"] is True
    assert document["only_requested_rows_executed"] is True
    assert document["observer_closed_and_exactly_reconciled"] is True
    assert document["fresh_query_observer_namespace_handoff_present"] is True
    assert document["fresh_query_ground_recovery_executed"] is True
    assert document["portable_bundle_present"] is False
    assert document["immutable_overlay_compiled"] is False
    assert document["post_transaction_replanning_performed"] is False
    assert document["plan_certificate_issued"] is False
    assert document["official_execution_allowed"] is False


def test_namespace_binding_is_not_caller_mintable() -> None:
    with pytest.raises(subject.ConstructionK7QueryBoundGroundTransactionV1Error):
        subject.QueryBoundNamespaceBindingV1(
            object(),
            _id("request"),
            _id("logical"),
            _id("namespace"),
            _id("occurrence"),
            _id("generation"),
            _id("context"),
            "NO_PRIOR",
        )
