from __future__ import annotations

import hashlib
import os
from pathlib import Path

import pytest

from acfqp import construction_k7_query_bound_accounted_continuation_v1 as subject
from acfqp import construction_k7_query_bound_recovery_overlay_v1 as overlay_v1
from acfqp import construction_k7_query_bound_recovery_request_v1 as request_v1
from acfqp import construction_k7_reusable_abstract_query_v1 as query_v1
from acfqp import construction_k7_reusable_build_epoch_authority_v1 as build_v1
from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS, canonical_json_bytes


def _id(label: str) -> str:
    return hashlib.sha256(
        b"acfqp:query-bound-accounted-continuation-test:v1\x00"
        + label.encode()
    ).hexdigest()


def test_domain_and_public_surface_remain_additive() -> None:
    assert subject.LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS
    assert set(subject.__all__) == {
        "ConstructionK7QueryBoundAccountedContinuationV1Error",
        "LOCAL_DOMAINS",
        "QueryBoundAccountedContinuationV1",
        "run_query_bound_accounted_continuation_v1",
        "verify_query_bound_accounted_continuation_v1",
    }


@pytest.fixture(scope="module")
def real_accounted_continuation():
    if os.environ.get("ACFQP_RUN_REAL_K7_QUERY_BOUND_ACCOUNTING") != "1":
        pytest.skip("set ACFQP_RUN_REAL_K7_QUERY_BOUND_ACCOUNTING=1")
    retained = os.environ.get("ACFQP_CAUSAL_RECOVERY_TRACE")
    if not retained:
        pytest.fail("ACFQP_CAUSAL_RECOVERY_TRACE must name the retained real trace")
    trace_raw = Path(retained).read_bytes()
    envelope = build_v1.replay_reusable_build_epoch_source_v1(trace_raw)
    envelope_bytes = canonical_json_bytes(envelope.to_document())
    query = query_v1.freeze_reusable_abstract_query_spec_v1(
        build_epoch=envelope,
        logical_occurrence_id=_id("fresh-accounted-query"),
        query_ordinal=0,
    )
    root = query_v1.run_reusable_abstract_query_v1(
        source_trace_bytes=trace_raw,
        build_epoch_envelope_bytes=envelope_bytes,
        query=query,
    )
    root_bytes = canonical_json_bytes(root.to_document())
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
    return subject.run_query_bound_accounted_continuation_v1(
        source_trace_bytes=trace_raw,
        build_epoch_envelope_bytes=envelope_bytes,
        root_query_result_bytes=root_bytes,
        overlay_bytes=overlay_bytes,
        request_bytes=canonical_json_bytes(request.to_document()),
    )


def test_real_continuation_preserves_scientific_and_accounting_chain(
    real_accounted_continuation,
) -> None:
    result = subject.verify_query_bound_accounted_continuation_v1(
        real_accounted_continuation
    )
    document = result.to_document()
    assert document["local_transaction_count"] == 2
    assert document["transaction_3_created"] is False
    assert document["cumulative_local_ground_draw_count"] == 25_344
    assert document["certificate_failure_triggered_only_local_ground_recovery"] is True
    assert document["unrequested_ground_rows_recovered"] == 0
    assert document["immutable_query_local_overlays_compiled"] == 2
    assert document["terminal_class"] == "PLAN_CERTIFICATE"
    assert document["terminal_code"] == "FULL_GROUND_FALLBACK"
    assert document["plan_certificate_issued"] is True
    assert document["stage_local_counter_record_chain_present"] is True
    assert document["stage_local_work_vectors_present"] is True
    assert document["stage_local_comparison_vectors_present"] is True
    assert document["shared_resource_receipts_present"] is False
    assert document["occurrence_work_vector_present"] is False
    assert document["counter_completeness_gate_status"] == "COUNTER_COMPLETENESS_GATE_NOT_RUN"

    stages = result.accounting.recorded_stages
    assert len(stages) == 5
    assert sum(len(row.work_vector.records) for row in stages) == 1_010
    fallback = stages[-1].work_vector.values
    assert fallback["fallback.states_expanded"] == 30
    assert fallback["fallback.actions_evaluated"] == 96
    assert fallback["fallback.ground_steps"] == 96
    assert fallback["fallback.outcome_rows"] == 1_440
    assert fallback["fallback.bellman_backups"] == 102
    assert fallback["route.attempts"] == 1
    assert fallback["route.successes"] == 1
    assert fallback["solver.attempts"] == 1
    assert fallback["solver.successes"] == 1
