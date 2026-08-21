from acfqp import construction_k7_persistent_multi_residual_preregistration_v96 as v96_pre
from acfqp.generic_dual_budget_adapter_v119 import dual_budget_config_v119
from acfqp.source_unseen_residual_campaign_core_v119 import (
    build_source_unseen_residual_occurrence_v119,
)


def test_v119_development_occurrence_keeps_partial_claim_boundary():
    row = build_source_unseen_residual_occurrence_v119(
        dual_budget_config_v119(),
        seed=1_031_001,
        episode_indices=(260, 261, 262),
        factor_library=(
            v96_pre.previous.previous.previous.previous.previous.FACTOR_LIBRARY
        ),
    )
    assert row["registered_gate"]["passed"] is True
    assert row["registered_gate"][
        "partial_candidate_retains_unknown_higher_order_residual"
    ] is True
    assert row["strict_no_prior_complete_model_control"]["attempt_count"] == 1
    assert row["accounting"]["same_epoch_genesis_authorized_cache_hits"] > 0
    assert row["complete_ground_world_model_synthesized"] is False
    assert row["official_scalar_cost"] is None
