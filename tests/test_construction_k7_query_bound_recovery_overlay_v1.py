from __future__ import annotations

import hashlib
import os
from pathlib import Path

import pytest

from acfqp import construction_k7_query_bound_recovery_overlay_v1 as subject
from acfqp import construction_k7_reusable_abstract_query_v1 as query_v1
from acfqp import construction_k7_reusable_build_epoch_authority_v1 as build_v1
from acfqp import v075_batch_native_planning_backend_v2 as planning_v2
from acfqp.phase3e_ids import (
    PHASE3E_DOMAIN_TAGS,
    canonical_json_bytes,
    loads_canonical_json,
)


def _id(label: str) -> str:
    return hashlib.sha256(
        b"acfqp:k7-query-bound-overlay-test:v1\x00" + label.encode("utf-8")
    ).hexdigest()


def test_domain_and_public_surface_remain_additive() -> None:
    assert subject.LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS
    assert set(subject.__all__) == {
        "ConstructionK7QueryBoundRecoveryOverlayV1Error",
        "LOCAL_DOMAINS",
        "QueryBoundRecoveryOverlayV1",
        "apply_query_bound_cached_recovery_overlay_v1",
        "verify_query_bound_cached_recovery_overlay_bytes_v1",
    }


@pytest.fixture(scope="module")
def real_query_bound_overlays():
    if os.environ.get("ACFQP_RUN_REAL_K7_QUERY_BOUND_OVERLAY") != "1":
        pytest.skip("set ACFQP_RUN_REAL_K7_QUERY_BOUND_OVERLAY=1")
    retained = os.environ.get("ACFQP_CAUSAL_RECOVERY_TRACE")
    if not retained:
        pytest.fail("ACFQP_CAUSAL_RECOVERY_TRACE must name the retained real trace")
    trace_raw = Path(retained).read_bytes()
    envelope = build_v1.replay_reusable_build_epoch_source_v1(trace_raw)
    envelope_bytes = canonical_json_bytes(envelope.to_document())

    results = []
    for ordinal in range(2):
        query = query_v1.freeze_reusable_abstract_query_spec_v1(
            build_epoch=envelope,
            logical_occurrence_id=_id(f"fresh-query-{ordinal}"),
            query_ordinal=ordinal,
        )
        root_result = query_v1.run_reusable_abstract_query_v1(
            source_trace_bytes=trace_raw,
            build_epoch_envelope_bytes=envelope_bytes,
            query=query,
        )
        root_result_bytes = canonical_json_bytes(root_result.to_document())
        overlay = subject.apply_query_bound_cached_recovery_overlay_v1(
            source_trace_bytes=trace_raw,
            build_epoch_envelope_bytes=envelope_bytes,
            root_query_result_bytes=root_result_bytes,
        )
        results.append((root_result, root_result_bytes, overlay))
    return trace_raw, envelope_bytes, tuple(results)


def test_real_two_fresh_queries_apply_one_verified_cached_overlay(
    real_query_bound_overlays,
) -> None:
    _trace_raw, _envelope_bytes, results = real_query_bound_overlays
    first_root, _first_root_bytes, first = results[0]
    second_root, _second_root_bytes, second = results[1]

    assert first_root.numerical_proof.outcome is planning_v2.V075NumericalOutcomeV2.FAILED_FRONTIER
    assert first_root.numerical_proof.failed_frontier is not None
    assert first_root.numerical_proof.proof_id == second_root.numerical_proof.proof_id
    assert first_root.query.query_id != second_root.query.query_id
    assert first_root.result_id != second_root.result_id

    assert first.overlay_id != second.overlay_id
    assert first.overlay_model_id == second.overlay_model_id
    assert first.overlay_proof_id == second.overlay_proof_id
    assert first.root_row_count == 2
    assert first.overlay_row_count == 18
    assert first.introduced_row_count == 16
    assert first.preserved_root_row_count == 1
    assert first.updated_root_row_count == 1

    document = first.to_document()
    assert document["activation_condition"] == "CURRENT_QUERY_EXACT_ROOT_PROOF_FAILED"
    assert document["ground_distinction_restore_mode"] == "VERIFIED_CACHED_OVERLAY"
    assert document["root_failure_verified_before_overlay_activation"] is True
    assert document["cached_overlay_lineage_exactly_replayed"] is True
    assert document["post_overlay_replanning_exactly_recomputed"] is True
    assert document["new_ground_access_count"] == 0
    assert document["fresh_query_ground_recovery_executed"] is False
    assert document["fresh_query_observer_namespace_handoff_present"] is False
    assert document["next_ground_transaction_required"] is True
    assert document["plan_certificate_issued"] is False
    assert document["official_execution_allowed"] is False


def test_real_overlay_bytes_replay_and_claim_flip_rejection(
    real_query_bound_overlays,
) -> None:
    trace_raw, envelope_bytes, results = real_query_bound_overlays
    _root, root_bytes, overlay = results[0]
    overlay_bytes = canonical_json_bytes(overlay.to_document())
    replayed = subject.verify_query_bound_cached_recovery_overlay_bytes_v1(
        source_trace_bytes=trace_raw,
        build_epoch_envelope_bytes=envelope_bytes,
        root_query_result_bytes=root_bytes,
        overlay_bytes=overlay_bytes,
    )
    assert replayed.overlay_id == overlay.overlay_id

    changed = loads_canonical_json(overlay_bytes)
    changed["new_ground_access_count"] = 1
    with pytest.raises(subject.ConstructionK7QueryBoundRecoveryOverlayV1Error):
        subject.verify_query_bound_cached_recovery_overlay_bytes_v1(
            source_trace_bytes=trace_raw,
            build_epoch_envelope_bytes=envelope_bytes,
            root_query_result_bytes=root_bytes,
            overlay_bytes=canonical_json_bytes(changed),
        )
