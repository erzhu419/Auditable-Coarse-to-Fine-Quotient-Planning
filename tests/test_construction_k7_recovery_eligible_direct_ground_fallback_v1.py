from __future__ import annotations

import hashlib
import os
from pathlib import Path

import pytest

from acfqp import construction_k7_query_bound_persistent_proof_cache_v1 as cache_v1
from acfqp import construction_k7_recovery_eligible_checkpoint_fixture_v1 as checkpoint_v1
from acfqp import construction_k7_recovery_eligible_direct_ground_fallback_v1 as subject
from acfqp import construction_k7_recovery_eligible_world_model_loop_v1 as loop_v1
from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS, canonical_json_bytes


def _fresh_id(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def test_domains_and_public_surface_are_additive() -> None:
    assert len(subject.LOCAL_DOMAINS) == 6
    assert subject.LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS
    assert set(subject.__all__) == {
        "ConstructionK7RecoveryEligibleDirectGroundFallbackV1Error",
        "LOCAL_DOMAINS",
        "MAX_FALLBACK_ACTIONS",
        "MAX_FALLBACK_BELLMAN_BACKUPS",
        "MAX_FALLBACK_OUTCOME_ROWS",
        "MAX_FALLBACK_STATES",
        "RecoveryEligibleDirectFallbackVerificationV1",
        "RecoveryEligibleDirectGroundFallbackV1",
        "RecoveryEligibleExactGroundRowV1",
        "RecoveryEligibleFallbackPolicyDecisionV1",
        "RecoveryEligibleFallbackTerminalClassV1",
        "RecoveryEligibleFallbackTerminalCodeV1",
        "RecoveryEligibleFallbackWorkV1",
        "execute_recovery_eligible_direct_ground_fallback_v1",
        "verify_recovery_eligible_direct_ground_fallback_v1",
    }


@pytest.fixture(scope="module")
def real_fallback():
    retained = os.environ.get("ACFQP_RETAINED_PERSISTENT_PROOF_CACHE_INPUTS")
    real = os.environ.get("ACFQP_RUN_REAL_K7_QUERY_BOUND_GROUND") == "1"
    if not retained or not real:
        pytest.skip("real recovery-eligible direct fallback is disabled")
    root = Path(retained)
    cache = cache_v1.materialize_query_bound_persistent_proof_cache_bytes_v1(
        binding_bytes=(root / "SOURCE_BUNDLE_BINDING.json").read_bytes(),
        snapshot_bytes=(root / "REUSABLE_RAPM_SNAPSHOT.json").read_bytes(),
        transition_bytes=(root / "PROOF_DEPENDENCY_TRANSITION.json").read_bytes(),
    )
    checkpoint = checkpoint_v1.materialize_recovery_eligible_checkpoint_fixture_v1(
        canonical_json_bytes(cache.to_document())
    )
    query = checkpoint_v1.freeze_recovery_eligible_checkpoint_query_v1(
        checkpoint,
        logical_occurrence_id=_fresh_id(
            "recovery-eligible-world-model-loop-occurrence-2"
        ),
        query_ordinal=2,
    )
    consumption = checkpoint_v1.consume_recovery_eligible_checkpoint_v1(
        checkpoint, query
    )
    request = checkpoint_v1.prepare_recovery_eligible_recovery_request_v1(
        checkpoint, consumption
    )
    transaction = loop_v1.execute_prepared_recovery_eligible_ground_transaction_v1(
        loop_v1.prepare_recovery_eligible_ground_transaction_v1(request)
    )
    loop = loop_v1.compile_recovery_eligible_world_model_loop_v1(transaction)
    return subject.execute_recovery_eligible_direct_ground_fallback_v1(loop)


def test_exact_fallback_runs_only_after_every_successor_frontier_row_is_capped(
    real_fallback,
) -> None:
    result = real_fallback
    document = result.to_document()
    frontier = result.predecessor.successor_proof.failed_frontier
    assert frontier is not None
    assert all(item.next_registered_checkpoint is None for item in frontier.obligations)
    assert document["local_transaction_count"] == 1
    assert document["maximum_local_transactions_per_logical_occurrence"] == 2
    assert document["second_local_transaction_created"] is False
    assert document["second_local_transaction_forbidden_reason"] == (
        "ALL_SUCCESSOR_FRONTIER_ROWS_CAP_BLOCKED"
    )
    assert document["cumulative_local_ground_draw_count"] == 12_672
    assert document["route"] == "MATCHED_DIRECT_GROUND"


def test_exact_fallback_certifies_full_ground_plan_and_native_work(real_fallback) -> None:
    result = real_fallback
    document = result.to_document()
    assert result.terminal_class is subject.RecoveryEligibleFallbackTerminalClassV1.PLAN_CERTIFICATE
    assert result.terminal_code is subject.RecoveryEligibleFallbackTerminalCodeV1.FULL_GROUND_FALLBACK
    assert len(result.exact_rows) == 96
    assert len(result.policy) == 16
    assert str(result.selected_expected_reward) == "3/64"
    assert str(result.selected_failure_probability) == "346437/12500000"
    assert document["complete_exact_h2_ground_inventory"] is True
    assert document["complete_exact_ground_search"] is True
    assert document["selected_policy_exactly_optimal_under_risk_constraint"] is True
    assert document["plan_certificate_issued"] is True
    assert document["scientific_endpoint_credit_allowed"] is False
    assert document["formal_counter_records_materialized"] is False
    assert document["official_execution_allowed"] is False
    assert result.work.states_expanded == 30
    assert result.work.actions_evaluated == 96
    assert result.work.ground_steps == 96
    assert result.work.outcome_rows == 1_440
    assert result.work.bellman_backups == 102


def test_exact_fallback_verifier_rebuilds_inventory_and_optimum(real_fallback) -> None:
    verification = subject.verify_recovery_eligible_direct_ground_fallback_v1(
        real_fallback
    )
    document = verification.to_document()
    assert document["complete_exact_h2_inventory_rebuilt"] is True
    assert document["constrained_ground_optimum_recomputed"] is True
    assert document["result_bytes_exactly_matched"] is True
    assert document["verification_lane"] == "EVALUATION"
    assert document["verification_work_included_in_operational_fallback_work"] is False
    assert document["valid"] is True


def test_direct_fallback_result_is_not_caller_mintable() -> None:
    with pytest.raises(subject.ConstructionK7RecoveryEligibleDirectGroundFallbackV1Error):
        subject.RecoveryEligibleDirectGroundFallbackV1(
            object(),
            object(),
            object(),
            object(),
            object(),
            (),
            (),
            None,
            None,
            object(),
            object(),
            object(),
        )
