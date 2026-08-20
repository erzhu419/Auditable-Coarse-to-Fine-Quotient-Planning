import os

import pytest

from acfqp.generic_multi_residual_abstract_planner_v25 import (
    GenericMultiResidualAbstractPlannerV25Error,
    plan_multi_residual_abstract_program_v25,
)


def test_v25_rejects_fewer_than_two_residual_proposals_before_search():
    with pytest.raises(GenericMultiResidualAbstractPlannerV25Error):
        plan_multi_residual_abstract_program_v25(
            object(),
            (),
            (),
            (),
            {"schema": "wrong", "compilable_candidates": []},
            maximum_depth=1,
        )


@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_MULTI_RESIDUAL") != "1",
    reason="explicit V25 joint multi-residual abstract planning development",
)
def test_v25_jointly_compiles_two_residual_proposals_without_ground_access():
    from acfqp import construction_k7_combined_model_planning_preregistration_v66 as pre
    from acfqp import true_bit_symmetric_three_domain_campaign_core_v59 as campaign
    from acfqp.construction_k7_residual_factor_library_v62 import (
        freeze_residual_factor_library_v62,
    )
    from acfqp.generic_certificate_guided_partial_planner_v16 import (
        run_certificate_guided_partial_episode_v16,
    )
    from acfqp.generic_multi_residual_acquisition_v24 import (
        acquire_multi_residual_factors_v24,
    )

    config = pre.campaign_config_v66()
    adapter = campaign.predecessor.predecessor.prior_ground._adapter(
        "MAINTENANCE_CASCADE", 690_974, config
    )
    partial = campaign.acquire_matched_true_bit_models_v59(
        adapter, pre.previous.previous.previous.FACTOR_LIBRARY, config
    )["ANONYMOUS_FACTOR_PRIOR_ON"]
    episode = run_certificate_guided_partial_episode_v16(
        adapter,
        partial["candidate"],
        partial["rows"],
        episode_index=0,
        maximum_abstract_depth=12,
        maximum_execution_steps=96,
    )
    candidate_document = partial["candidate"].public_document
    evidence = {
        "layout": candidate_document["layout"],
        "unknown_residual_target_columns": candidate_document[
            "unknown_residual_target_columns"
        ],
        "raw_transition_rows": episode["raw_local_transition_rows"],
    }
    library = freeze_residual_factor_library_v62().to_document()["compiled_library"]
    acquisition = acquire_multi_residual_factors_v24(
        evidence, prior_library=library
    )
    assert acquisition["compilable_candidate_count"] == 2

    plan = plan_multi_residual_abstract_program_v25(
        partial["candidate"],
        partial["rows"],
        adapter.catalogue,
        adapter.encode(adapter.initial()),
        acquisition,
        maximum_depth=12,
        maximum_support_branch_evaluations=1_000_000,
        support_feasible_beam_width=16,
    )
    assert plan["residual_proposal_count"] == 2
    assert plan["remaining_unknown_target_columns"] == []
    assert plan["multiple_residual_proposals_jointly_compiled"] is True
    assert plan["ground_transition_accessed_during_abstract_search"] is False
    assert plan["abstract_plan_used_as_safety_authority"] is False
    assert plan["complete_world_model_claimed"] is False
