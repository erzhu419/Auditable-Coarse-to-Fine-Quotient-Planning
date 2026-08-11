from __future__ import annotations

import hashlib
import os
from pathlib import Path

import pytest

from acfqp import construction_k7_query_bound_recovery_overlay_v1 as overlay_v1
from acfqp import construction_k7_query_bound_recovery_request_v1 as subject
from acfqp import construction_k7_reusable_abstract_query_v1 as query_v1
from acfqp import construction_k7_reusable_build_epoch_authority_v1 as build_v1
from acfqp.phase3e_ids import (
    PHASE3E_DOMAIN_TAGS,
    canonical_json_bytes,
    loads_canonical_json,
)


def _id(label: str) -> str:
    return hashlib.sha256(
        b"acfqp:k7-query-bound-request-test:v1\x00" + label.encode("utf-8")
    ).hexdigest()


def test_domains_and_public_surface_remain_additive() -> None:
    assert subject.LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS
    assert set(subject.__all__) == {
        "ConstructionK7QueryBoundRecoveryRequestV1Error",
        "LOCAL_DOMAINS",
        "QueryBoundRecoveryRequestV1",
        "QueryBoundValidationRequestV1",
        "prepare_query_bound_recovery_request_v1",
        "verify_query_bound_recovery_request_bytes_v1",
    }


@pytest.fixture(scope="module")
def real_query_bound_request():
    if os.environ.get("ACFQP_RUN_REAL_K7_QUERY_BOUND_REQUEST") != "1":
        pytest.skip("set ACFQP_RUN_REAL_K7_QUERY_BOUND_REQUEST=1")
    retained = os.environ.get("ACFQP_CAUSAL_RECOVERY_TRACE")
    if not retained:
        pytest.fail("ACFQP_CAUSAL_RECOVERY_TRACE must name the retained real trace")
    trace_raw = Path(retained).read_bytes()
    envelope = build_v1.replay_reusable_build_epoch_source_v1(trace_raw)
    envelope_bytes = canonical_json_bytes(envelope.to_document())
    query = query_v1.freeze_reusable_abstract_query_spec_v1(
        build_epoch=envelope,
        logical_occurrence_id=_id("fresh-query"),
        query_ordinal=0,
    )
    root_result = query_v1.run_reusable_abstract_query_v1(
        source_trace_bytes=trace_raw,
        build_epoch_envelope_bytes=envelope_bytes,
        query=query,
    )
    root_result_bytes = canonical_json_bytes(root_result.to_document())
    overlay = overlay_v1.apply_query_bound_cached_recovery_overlay_v1(
        source_trace_bytes=trace_raw,
        build_epoch_envelope_bytes=envelope_bytes,
        root_query_result_bytes=root_result_bytes,
    )
    overlay_bytes = canonical_json_bytes(overlay.to_document())
    request = subject.prepare_query_bound_recovery_request_v1(
        source_trace_bytes=trace_raw,
        build_epoch_envelope_bytes=envelope_bytes,
        root_query_result_bytes=root_result_bytes,
        overlay_bytes=overlay_bytes,
    )
    return trace_raw, envelope_bytes, root_result_bytes, overlay_bytes, request


def test_real_failed_overlay_freezes_minimal_no_access_request(
    real_query_bound_request,
) -> None:
    _trace, _envelope, _root, _overlay, request = real_query_bound_request
    assert request.transaction_index == 1
    assert len(request.rows) == 7
    assert len(request.requested_rows) == 6
    assert len(request.cap_blocked_rows) == 1
    assert request.requested_additional_draw_count == 12_288
    assert {
        item.requested_additional_draw_count for item in request.requested_rows
    } == {2_048}

    document = request.to_document()
    assert document["activation_state"] == "PREPARED_NO_ACCESS"
    assert document["request_frozen_before_namespace_creation"] is True
    assert document["observer_namespace_id"] is None
    assert document["ground_access_count"] == 0
    assert document["ground_execution_authorized"] is False
    assert document["next_required_action"] == (
        "CREATE_QUERY_BOUND_NAMESPACE_AND_REVERIFY_REQUEST"
    )
    assert document["plan_certificate_issued"] is False
    assert document["official_execution_allowed"] is False


def test_real_request_bytes_replay_and_authority_flip_rejection(
    real_query_bound_request,
) -> None:
    trace, envelope, root, overlay, request = real_query_bound_request
    request_bytes = canonical_json_bytes(request.to_document())
    replayed = subject.verify_query_bound_recovery_request_bytes_v1(
        source_trace_bytes=trace,
        build_epoch_envelope_bytes=envelope,
        root_query_result_bytes=root,
        overlay_bytes=overlay,
        request_bytes=request_bytes,
    )
    assert replayed.request_id == request.request_id

    changed = loads_canonical_json(request_bytes)
    changed["ground_execution_authorized"] = True
    with pytest.raises(subject.ConstructionK7QueryBoundRecoveryRequestV1Error):
        subject.verify_query_bound_recovery_request_bytes_v1(
            source_trace_bytes=trace,
            build_epoch_envelope_bytes=envelope,
            root_query_result_bytes=root,
            overlay_bytes=overlay,
            request_bytes=canonical_json_bytes(changed),
        )
