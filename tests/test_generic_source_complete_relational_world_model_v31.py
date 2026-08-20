import os

import pytest


@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_RELATIONAL_WORLD_MODEL") != "1",
    reason="explicit V31 source-complete relational world model",
)
def test_v31_retains_every_v28_source_row_for_independent_reconstruction():
    from acfqp import construction_k7_combined_model_planning_preregistration_v66 as pre
    from acfqp import true_bit_symmetric_three_domain_campaign_core_v59 as campaign
    from acfqp.construction_k7_residual_factor_library_v62 import (
        freeze_residual_factor_library_v62,
    )
    from acfqp.generic_relational_terminal_program_independent_replay_v32 import (
        verify_source_complete_relational_program_v32,
    )
    from acfqp.generic_source_complete_relational_world_model_v31 import (
        run_source_complete_relational_world_model_episode_v31,
    )

    config = pre.campaign_config_v66()
    adapter = campaign.predecessor.predecessor.prior_ground._adapter(
        "MAINTENANCE_CASCADE", 690_974, config
    )
    partial = campaign.acquire_matched_true_bit_models_v59(
        adapter, pre.previous.previous.previous.FACTOR_LIBRARY, config
    )["ANONYMOUS_FACTOR_PRIOR_ON"]
    library = freeze_residual_factor_library_v62().to_document()["compiled_library"]
    result = run_source_complete_relational_world_model_episode_v31(
        adapter,
        partial["candidate"],
        partial["rows"],
        residual_prior_library=library,
        episode_index=0,
        maximum_abstract_depth=12,
        maximum_execution_steps=96,
    )
    evidence = result["terminal_program_source_evidence"]
    replay = verify_source_complete_relational_program_v32(
        {
            "layout": evidence["layout"],
            "unknown_residual_target_columns": evidence[
                "unknown_residual_target_columns"
            ],
            "raw_transition_rows": evidence["raw_transition_rows"],
        },
        result["predecessor_v30_episode"]["final_relational_terminal_program"],
    )
    assert replay["decision_tree_frontier_rederived"] is True
    assert result["all_v28_source_rows_retained"] is True
    assert result["relational_abstract_plan_used_as_safety_authority"] is False

