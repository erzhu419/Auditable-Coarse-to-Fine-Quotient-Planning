from __future__ import annotations

import hashlib
import os
from pathlib import Path

import pytest

from acfqp import construction_k7_query_bound_persistent_proof_cache_v1 as cache_v1
from acfqp import construction_k7_recovery_eligible_checkpoint_fixture_v1 as checkpoint_v1
from acfqp import construction_k7_recovery_eligible_world_model_loop_v1 as loop_v1
from acfqp import construction_k7_recovery_overlay_promotion_v1 as subject
from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS, canonical_json_bytes


def _fresh_id(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def test_domains_and_public_surface_are_additive() -> None:
    assert len(subject.LOCAL_DOMAINS) == 4
    assert subject.LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS
    assert set(subject.__all__) == {
        "ConstructionK7RecoveryOverlayPromotionV1Error",
        "LOCAL_DOMAINS",
        "RecoveryOverlayPromotedConsumptionV1",
        "RecoveryOverlayPromotedEpochV1",
        "RecoveryOverlayPromotedQueryV1",
        "RecoveryOverlayPromotionResultV1",
        "consume_recovery_overlay_promoted_epoch_v1",
        "freeze_recovery_overlay_promoted_query_v1",
        "promote_recovery_overlay_epoch_v1",
        "require_recovery_overlay_promoted_epoch_v1",
        "run_recovery_overlay_promotion_v1",
        "verify_recovery_overlay_promotion_bytes_v1",
        "verify_recovery_overlay_promotion_v1",
    }


@pytest.fixture(scope="module")
def real_promotion():
    retained = os.environ.get("ACFQP_RETAINED_PERSISTENT_PROOF_CACHE_INPUTS")
    real = os.environ.get("ACFQP_RUN_REAL_K7_QUERY_BOUND_GROUND") == "1"
    if not retained or not real:
        pytest.skip("real recovery-overlay promotion is disabled")
    root = Path(retained)
    cache = cache_v1.materialize_query_bound_persistent_proof_cache_bytes_v1(
        binding_bytes=(root / "SOURCE_BUNDLE_BINDING.json").read_bytes(),
        snapshot_bytes=(root / "REUSABLE_RAPM_SNAPSHOT.json").read_bytes(),
        transition_bytes=(root / "PROOF_DEPENDENCY_TRANSITION.json").read_bytes(),
    )
    checkpoint = checkpoint_v1.materialize_recovery_eligible_checkpoint_fixture_v1(
        canonical_json_bytes(cache.to_document())
    )
    source_query = checkpoint_v1.freeze_recovery_eligible_checkpoint_query_v1(
        checkpoint,
        logical_occurrence_id=_fresh_id("overlay-promotion-source-occurrence"),
        query_ordinal=2,
    )
    source_consumption = checkpoint_v1.consume_recovery_eligible_checkpoint_v1(
        checkpoint, source_query
    )
    request = checkpoint_v1.prepare_recovery_eligible_recovery_request_v1(
        checkpoint, source_consumption
    )
    transaction = loop_v1.execute_prepared_recovery_eligible_ground_transaction_v1(
        loop_v1.prepare_recovery_eligible_ground_transaction_v1(request)
    )
    source_loop = loop_v1.compile_recovery_eligible_world_model_loop_v1(transaction)
    result = subject.run_recovery_overlay_promotion_v1(
        source_loop,
        logical_occurrence_id=_fresh_id("overlay-promotion-reuse-occurrence"),
        query_ordinal=3,
    )
    return source_loop, result


def test_real_overlay_becomes_one_immutable_query_neutral_epoch(
    real_promotion,
) -> None:
    source_loop, result = real_promotion
    document = result.to_document()
    epoch = document["promoted_epoch"]
    assert epoch["source_recovery_world_model_loop_id"] == source_loop.result_id
    assert epoch["promoted_numerical_model_id"] == source_loop.successor_model.model_id
    assert epoch["promoted_numerical_proof_id"] == source_loop.successor_proof.proof_id
    assert epoch["promoted_row_count"] == 18
    assert epoch["changed_row_count"] == 6
    assert epoch["preserved_row_count"] == 12
    assert epoch["frontier_row_count"] == 7
    assert epoch["requestable_frontier_row_count"] == 0
    assert epoch["cap_blocked_frontier_row_count"] == 7
    assert epoch["immutable_promoted_epoch"] is True
    assert epoch["query_identity_outside_model_and_proof"] is True
    assert epoch["automatic_signed_overlay_compilation_present"] is True
    assert epoch["automatic_coordinate_invention_claimed"] is False


def test_real_fresh_occurrence_reuses_failure_before_any_new_ground(
    real_promotion,
) -> None:
    _source_loop, result = real_promotion
    document = result.to_document()
    consumption = document["promoted_consumption"]
    assert consumption["complete_proof_bytes_reused"] is True
    assert consumption["proof_node_compute_count"] == 0
    assert consumption["full_planner_call_count"] == 0
    assert consumption["model_construction_repeated"] is False
    assert consumption["new_local_support_discovery_draw_count"] == 0
    assert consumption["new_local_validation_draw_count"] == 0
    assert consumption["new_local_ground_draw_count"] == 0
    assert consumption["local_allowed_after_result"] is False
    assert (
        consumption["local_forbidden_reason"]
        == "ALL_PROMOTED_FRONTIER_ROWS_CAP_BLOCKED"
    )
    assert (
        consumption["next_required_action"]
        == "EXECUTE_QUERY_IDENTITY_BOUND_DIRECT_GROUND_FALLBACK"
    )
    assert consumption["plan_certificate_issued"] is False


def test_real_promotion_reduces_only_the_repeated_local_recovery_tax(
    real_promotion,
) -> None:
    _source_loop, result = real_promotion
    document = result.to_document()
    assert document["source_local_ground_draw_count"] == 12_672
    assert document["promoted_query_new_local_ground_draw_count"] == 0
    assert document["two_occurrence_promoted_local_ground_draw_count"] == 12_672
    assert (
        document["counterfactual_repeated_recovery_local_ground_draw_count"]
        == 25_344
    )
    assert (
        document["local_ground_draws_avoided_under_identical_recovery_recipe"]
        == 12_672
    )
    assert document["local_ground_draw_reduction_fraction"] == {
        "numerator": 1,
        "denominator": 2,
    }
    assert document["matched_no_promotion_execution_performed"] is False
    assert document["end_to_end_sample_efficiency_claimed"] is False
    assert document["abstract_plan_certificate_issued"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None
    assert document["official_execution_allowed"] is False


def test_promotion_and_bytes_replay_do_not_reopen_planner_or_ground(
    real_promotion,
    monkeypatch,
) -> None:
    source_loop, result = real_promotion

    def forbidden(*_args, **_kwargs):
        raise AssertionError("promoted consumption reopened planner or ground")

    monkeypatch.setattr(
        loop_v1.fixture_v1,
        "prepare_v075_k7_construction_environment_v1",
        forbidden,
    )
    monkeypatch.setattr(loop_v1.planning_v2, "plan_v075_construction_numerical_model_v2", forbidden)
    repeated = subject.run_recovery_overlay_promotion_v1(
        source_loop,
        logical_occurrence_id=result.consumption.query.logical_occurrence_id,
        query_ordinal=3,
    )
    replayed = subject.verify_recovery_overlay_promotion_bytes_v1(
        source_loop=source_loop,
        result_bytes=canonical_json_bytes(result.to_document()),
    )
    assert repeated.result_id == result.result_id
    assert replayed.result_id == result.result_id


@pytest.mark.parametrize(
    ("path", "replacement"),
    (
        (("promoted_consumption", "new_local_ground_draw_count"), 1),
        (("promoted_consumption", "local_allowed_after_result"), True),
        (("promoted_consumption", "cached_numerical_proof_id"), "f" * 64),
        (("promoted_epoch", "promoted_numerical_model_id"), "e" * 64),
        (("local_ground_draws_avoided_under_identical_recovery_recipe",), 0),
        (("abstract_plan_certificate_issued",), True),
    ),
)
def test_resigned_semantic_or_identity_changes_are_rejected(
    real_promotion,
    path,
    replacement,
) -> None:
    source_loop, result = real_promotion
    document = result.to_document()
    target = document
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = replacement
    with pytest.raises(subject.ConstructionK7RecoveryOverlayPromotionV1Error):
        subject.verify_recovery_overlay_promotion_bytes_v1(
            source_loop=source_loop,
            result_bytes=canonical_json_bytes(document),
        )


def test_query_identity_must_be_fresh_and_next_registered(real_promotion) -> None:
    source_loop, result = real_promotion
    epoch = result.epoch
    with pytest.raises(subject.ConstructionK7RecoveryOverlayPromotionV1Error):
        subject.freeze_recovery_overlay_promoted_query_v1(
            epoch,
            logical_occurrence_id=epoch.source_query.logical_occurrence_id,
            query_ordinal=3,
        )
    with pytest.raises(subject.ConstructionK7RecoveryOverlayPromotionV1Error):
        subject.freeze_recovery_overlay_promoted_query_v1(
            epoch,
            logical_occurrence_id=_fresh_id("wrong-promoted-query-ordinal"),
            query_ordinal=4,
        )


def test_objects_are_not_caller_mintable() -> None:
    with pytest.raises(subject.ConstructionK7RecoveryOverlayPromotionV1Error):
        subject.RecoveryOverlayPromotedEpochV1(object(), object())
    with pytest.raises(subject.ConstructionK7RecoveryOverlayPromotionV1Error):
        subject.RecoveryOverlayPromotedConsumptionV1(object(), object(), object())
    with pytest.raises(subject.ConstructionK7RecoveryOverlayPromotionV1Error):
        subject.RecoveryOverlayPromotionResultV1(object(), object(), object())
