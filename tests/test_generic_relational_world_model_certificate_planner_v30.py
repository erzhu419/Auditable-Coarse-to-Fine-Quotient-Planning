import os

import pytest

from acfqp.generic_relational_world_model_certificate_planner_v30 import (
    GenericRelationalWorldModelCertificatePlannerV30Error,
    run_relational_world_model_certificate_episode_v30,
)


def test_v30_rejects_nonpositive_caps():
    with pytest.raises(GenericRelationalWorldModelCertificatePlannerV30Error):
        run_relational_world_model_certificate_episode_v30(
            object(),
            object(),
            (),
            residual_prior_library=None,
            episode_index=0,
            maximum_abstract_depth=0,
            maximum_execution_steps=1,
        )


@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_RELATIONAL_WORLD_MODEL") != "1",
    reason="explicit V30 online relational world-model development",
)
def test_v30_online_relational_model_only_orders_certified_local_recovery():
    from acfqp import construction_k7_combined_model_planning_preregistration_v66 as pre
    from acfqp import true_bit_symmetric_three_domain_campaign_core_v59 as campaign
    from acfqp.construction_k7_residual_factor_library_v62 import (
        freeze_residual_factor_library_v62,
    )

    config = pre.campaign_config_v66()
    adapter = campaign.predecessor.predecessor.prior_ground._adapter(
        "MAINTENANCE_CASCADE", 690_974, config
    )
    partial = campaign.acquire_matched_true_bit_models_v59(
        adapter, pre.previous.previous.previous.FACTOR_LIBRARY, config
    )["ANONYMOUS_FACTOR_PRIOR_ON"]
    library = freeze_residual_factor_library_v62().to_document()["compiled_library"]
    episode = run_relational_world_model_certificate_episode_v30(
        adapter,
        partial["candidate"],
        partial["rows"],
        residual_prior_library=library,
        episode_index=0,
        maximum_abstract_depth=12,
        maximum_execution_steps=96,
    )
    assert episode["success"] is True
    assert episode["relational_abstract_plan_success_count"] > 0
    assert episode["terminal_program_candidate_rejection_count"] > 0
    assert episode["all_observed_state_coordinates_represented_when_model_active"] is True
    assert episode["all_ground_queries_followed_failed_certificates"] is True
    assert episode["query_local_exact_overlay_exclusively_used_for_safety"] is True
    assert episode["relational_abstract_plan_used_as_safety_authority"] is False
    assert episode["complete_world_model_synthesized"] is False
