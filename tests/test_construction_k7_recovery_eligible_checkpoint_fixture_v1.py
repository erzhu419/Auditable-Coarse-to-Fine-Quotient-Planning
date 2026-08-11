from __future__ import annotations

import hashlib
import os
from pathlib import Path

import pytest

from acfqp import construction_k7_query_bound_persistent_proof_cache_v1 as cache_v1
from acfqp import construction_k7_recovery_eligible_checkpoint_fixture_v1 as subject
from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS, canonical_json_bytes


def _fresh_id(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def test_domains_and_public_surface_are_additive() -> None:
    assert len(subject.LOCAL_DOMAINS) == 5
    assert subject.LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS
    assert set(subject.__all__) == {
        "ConstructionK7RecoveryEligibleCheckpointFixtureV1Error",
        "LOCAL_DOMAINS",
        "RecoveryEligibleCheckpointConsumptionV1",
        "RecoveryEligibleCheckpointQueryV1",
        "RecoveryEligibleCheckpointV1",
        "RecoveryEligibleRecoveryRequestV1",
        "RecoveryEligibleValidationRequestV1",
        "consume_recovery_eligible_checkpoint_v1",
        "freeze_recovery_eligible_checkpoint_query_v1",
        "materialize_recovery_eligible_checkpoint_fixture_v1",
        "prepare_recovery_eligible_recovery_request_v1",
        "require_recovery_eligible_checkpoint_v1",
        "require_recovery_eligible_recovery_request_v1",
    }


@pytest.fixture(scope="module")
def real_recovery_eligible_checkpoint():
    retained = os.environ.get("ACFQP_RETAINED_PERSISTENT_PROOF_CACHE_INPUTS")
    real = os.environ.get("ACFQP_RUN_REAL_K7_QUERY_BOUND_GROUND") == "1"
    if not retained or not real:
        pytest.skip("real recovery-eligible checkpoint fixture is disabled")
    root = Path(retained)
    cache = cache_v1.materialize_query_bound_persistent_proof_cache_bytes_v1(
        binding_bytes=(root / "SOURCE_BUNDLE_BINDING.json").read_bytes(),
        snapshot_bytes=(root / "REUSABLE_RAPM_SNAPSHOT.json").read_bytes(),
        transition_bytes=(root / "PROOF_DEPENDENCY_TRANSITION.json").read_bytes(),
    )
    cache_bytes = canonical_json_bytes(cache.to_document())
    checkpoint = subject.materialize_recovery_eligible_checkpoint_fixture_v1(
        cache_bytes
    )
    return checkpoint


def test_real_as_of_checkpoint_is_recovery_eligible_without_changing_capped_cache(
    real_recovery_eligible_checkpoint,
) -> None:
    checkpoint = real_recovery_eligible_checkpoint
    document = checkpoint.to_document()
    assert document["publication_cut"] == "TRANSACTION_1_REPLANNING_AS_OF_CHECKPOINT"
    assert document["proof_node_count"] == 41
    assert document["frontier_row_count"] == 7
    assert document["requestable_frontier_row_count"] == 6
    assert document["cap_blocked_frontier_row_count"] == 1
    assert document["requested_additional_draw_count"] == 12_288
    assert document["later_target_graph_input_present_in_online_api"] is False
    assert document["deliberately_coarsened_partition_used"] is False
    assert document["production_latest_epoch_selection_authority"] is False
    assert document["construction_fixture"] is True
    assert "target_graph" not in document
    assert document["ground_access_count"] == 0
    assert document["plan_certificate_issued"] is False


def test_cached_failure_freezes_only_minimal_registered_rows_without_planner_or_ground(
    real_recovery_eligible_checkpoint,
    monkeypatch,
) -> None:
    checkpoint = real_recovery_eligible_checkpoint

    def forbidden_planner(*_args, **_kwargs):
        raise AssertionError("online recovery-eligible path called the full planner")

    monkeypatch.setattr(
        subject.planning_v2,
        "plan_v075_construction_numerical_model_v2",
        forbidden_planner,
    )
    query = subject.freeze_recovery_eligible_checkpoint_query_v1(
        checkpoint,
        logical_occurrence_id=_fresh_id("recovery-eligible-fresh-occurrence"),
        query_ordinal=2,
    )
    consumption = subject.consume_recovery_eligible_checkpoint_v1(
        checkpoint,
        query,
    )
    request = subject.prepare_recovery_eligible_recovery_request_v1(
        checkpoint,
        consumption,
    )
    consumption_document = consumption.to_document()
    request_document = request.to_document()
    assert consumption_document["proof_node_reuse_count"] == 41
    assert consumption_document["proof_node_compute_count"] == 0
    assert consumption_document["full_planner_call_count"] == 0
    assert consumption_document["new_ground_access_count"] == 0
    assert consumption_document["query_local_ground_recovery_eligible"] is True
    assert request_document["requested_row_count"] == 6
    assert request_document["cap_blocked_row_count"] == 1
    assert request_document["requested_additional_draw_count"] == 12_288
    assert request_document["activation_state"] == "PREPARED_NO_ACCESS"
    assert request_document["request_frozen_after_exact_cached_certificate_failure"] is True
    assert request_document["ground_access_count"] == 0
    assert request_document["next_required_action"] == (
        "CREATE_FRESH_NAMESPACE_AND_EXECUTE_MINIMAL_RECOVERY"
    )
    assert all(
        item["ground_access_performed"] is False
        for item in request_document["validation_requests"]
    )


def test_source_occurrence_cannot_masquerade_as_fresh_query(
    real_recovery_eligible_checkpoint,
) -> None:
    checkpoint = real_recovery_eligible_checkpoint
    with pytest.raises(
        subject.ConstructionK7RecoveryEligibleCheckpointFixtureV1Error
    ):
        subject.freeze_recovery_eligible_checkpoint_query_v1(
            checkpoint,
            logical_occurrence_id=checkpoint.source_logical_occurrence_id,
            query_ordinal=2,
        )


def test_checkpoint_and_request_are_not_caller_mintable() -> None:
    with pytest.raises(
        subject.ConstructionK7RecoveryEligibleCheckpointFixtureV1Error
    ):
        subject.RecoveryEligibleCheckpointV1(
            object(),
            *("0" * 64 for _ in range(5)),
            b"{}",
            object(),
            object(),
            (),
        )
