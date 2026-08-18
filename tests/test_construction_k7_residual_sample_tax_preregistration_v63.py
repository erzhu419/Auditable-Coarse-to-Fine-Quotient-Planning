import hashlib

from acfqp.construction_k7_residual_sample_tax_preregistration_v63 import (
    BALANCED_TARGET_SEEDS,
    COUPLED_TARGET_SEEDS,
    MAINTENANCE_TARGET_SEEDS,
    campaign_config_v63,
    freeze_residual_sample_tax_preregistration_v63,
    verify_residual_sample_tax_preregistration_v63,
)


def test_v63_preregistration_is_outcome_free_and_fresh():
    value = verify_residual_sample_tax_preregistration_v63(
        freeze_residual_sample_tax_preregistration_v63()
    )
    document = value.to_document()
    assert document["fresh_registered_outcome_execution_performed"] is False
    assert document["claim_boundary"]["registered_outcome_observed"] is False
    assert document["matched_ablation_contract"]["prior_does_not_filter_strict_candidates"] is True
    assert document["query_and_safety_contract"]["reachable_frontier_exhaustion_stop_available"] is False
    assert document["claim_boundary"]["official_N_break_even"] is None
    seeds = BALANCED_TARGET_SEEDS + COUPLED_TARGET_SEEDS + MAINTENANCE_TARGET_SEEDS
    assert len(seeds) == len(set(seeds)) == 12
    assert min(seeds) > 600_000
    assert campaign_config_v63()["worker_count"] == 4
    assert len(value.canonical_bytes) > 0
    assert len(hashlib.sha256(value.canonical_bytes).hexdigest()) == 64
