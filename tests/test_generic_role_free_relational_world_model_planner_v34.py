import os

import pytest


@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_ROLE_FREE_RELATIONAL") != "1",
    reason="explicit V34 cross-occurrence relational planning development",
)
def test_v34_reuses_role_free_terminal_template_in_abstract_planning():
    from acfqp import construction_k7_combined_model_planning_preregistration_v66 as pre
    from acfqp import true_bit_symmetric_three_domain_campaign_core_v59 as campaign
    from acfqp.construction_k7_residual_factor_library_v62 import (
        freeze_residual_factor_library_v62,
    )
    from acfqp.generic_role_free_relational_template_v33 import (
        compile_role_free_relational_template_library_v33,
    )
    from acfqp.generic_role_free_relational_world_model_planner_v34 import (
        plan_role_free_relational_world_model_v34,
    )
    from acfqp.generic_source_complete_relational_world_model_v31 import (
        run_source_complete_relational_world_model_episode_v31,
    )

    config = pre.campaign_config_v66()
    library = freeze_residual_factor_library_v62().to_document()["compiled_library"]

    def run(seed):
        adapter = campaign.predecessor.predecessor.prior_ground._adapter(
            "MAINTENANCE_CASCADE", seed, config
        )
        partial = campaign.acquire_matched_true_bit_models_v59(
            adapter, pre.previous.previous.previous.FACTOR_LIBRARY, config
        )["ANONYMOUS_FACTOR_PRIOR_ON"]
        episode = run_source_complete_relational_world_model_episode_v31(
            adapter,
            partial["candidate"],
            partial["rows"],
            residual_prior_library=library,
            episode_index=0,
            maximum_abstract_depth=12,
            maximum_execution_steps=96,
        )
        return adapter, partial, episode

    _source_adapter, _source_partial, source = run(690_974)
    target_adapter, target_partial, target = run(690_975)
    source_program = source["predecessor_v30_episode"][
        "final_relational_terminal_program"
    ]
    template_library = compile_role_free_relational_template_library_v33(
        (source_program,)
    )
    evidence = target["terminal_program_source_evidence"]
    target_source = {
        "layout": evidence["layout"],
        "unknown_residual_target_columns": evidence[
            "unknown_residual_target_columns"
        ],
        "raw_transition_rows": evidence["raw_transition_rows"],
    }
    result = plan_role_free_relational_world_model_v34(
        target_partial["candidate"],
        target_partial["rows"],
        target_adapter.catalogue,
        target_adapter.encode(target_adapter.initial()),
        target["predecessor_v30_episode"]["final_batch_exact_residual_support"],
        template_library,
        target_source,
        maximum_depth=12,
    )
    assert result["cross_occurrence_role_free_template_reused"] is True
    assert result["target_instantiation"]["binding_evaluation_count"] > 0
    assert result["abstract_plan"]["support_feasible_receding_plan_found"] is True
    assert result["abstract_plan_used_as_safety_authority"] is False
